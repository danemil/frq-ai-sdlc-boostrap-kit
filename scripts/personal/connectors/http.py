"""A small read-only HTTP client for connectors. Stdlib only (urllib, ssl, json).

- GET only. The only POSTs are token exchanges (Jama OAuth, Black Duck), made by
  `TokenExchange` itself through `Client._exchange`, and only to the auth's own
  `token_path`; connector code has no way to send a write.
- Auth per kind: `bearer(token)`, `basic(user, secret)`, `token_as_user(token)`,
  `oauth_client_credentials(client_id, client_secret)`, `blackduck_token(api_token)`.
- TLS is always verified. A CA bundle comes from the connector's `ca_bundle`, else
  AI_SDLC_CA_BUNDLE, else SSL_CERT_FILE; it is added to the system's trusted CAs.
- Proxies: HTTPS_PROXY / HTTP_PROXY / NO_PROXY, through urllib's ProxyHandler.
- Retries 429 and 5xx answers with backoff (Retry-After honoured, capped).
- Errors are `ConnectorError`s in plain words (401, 403, TLS, proxy, DNS, refused,
  timeout); no secret ever appears in one. AI_SDLC_DEBUG=1 prints each request to
  stderr with the Authorization header redacted.
"""
from __future__ import annotations

import base64
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

RETRY_STATUSES = (429, 500, 502, 503, 504)
MAX_WAIT = 30.0
REDACTED = "<redacted>"
READ_ONLY = "Connectors are read-only: only GET requests are sent."
SECRET_HEADERS = ("authorization", "proxy-authorization", "cookie")


class ConnectorError(Exception):
    """A plain-language reason a request failed. `kind` is a short machine-readable tag:
    unauthorized, forbidden, not_found, rate_limited, server, http, tls, dns, refused,
    proxy, timeout, network, bad_response, config."""

    def __init__(self, message, kind="http", status=None):
        super().__init__(message)
        self.kind = kind
        self.status = status


# --- auth ---------------------------------------------------------------------

class Auth:
    kind = "none"

    def headers(self, client) -> dict:
        return {}

    def secrets(self) -> list[str]:
        return []


class Bearer(Auth):
    kind = "bearer"

    def __init__(self, token):
        self._token = token

    def headers(self, client) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    def secrets(self) -> list[str]:
        return [self._token]


class Basic(Auth):
    kind = "basic"

    def __init__(self, user, secret):
        self._user, self._secret = user, secret
        self._encoded = base64.b64encode(f"{user}:{secret}".encode("utf-8")).decode("ascii")

    def headers(self, client) -> dict:
        return {"Authorization": f"Basic {self._encoded}"}

    def secrets(self) -> list[str]:
        return [self._secret, self._encoded]


class TokenAsUser(Auth):
    """A token sent as the Basic user name with an empty password (SonarQube). Unlike
    `basic(token, "")`, `secrets()` lists the token itself, so an error that quotes it
    is scrubbed."""
    kind = "basic"

    def __init__(self, token):
        self._token = token
        self._encoded = base64.b64encode(f"{token}:".encode("utf-8")).decode("ascii")

    def headers(self, client) -> dict:
        return {"Authorization": f"Basic {self._encoded}"}

    def secrets(self) -> list[str]:
        return [self._token, self._encoded]


class TokenExchange(Auth):
    """Base for auths that trade a long-lived secret for a short-lived bearer token.

    A subclass sets `token_path` (the one path this auth may POST to) and overrides
    `exchange_request()`, `parse(data)`, `unauthorized_message(host)` and
    `long_secrets()`; it may override `no_token_message(host)`. The base fetches the
    token through `client._exchange(self)` when there is none or it is about to
    expire (30 s early), caches it, and sends `Authorization: Bearer <token>`.
    """
    kind = "exchange"
    token_path = ""

    def __init__(self):
        self._token = None
        self._expires = 0.0

    # -- what a subclass says --
    def exchange_request(self):
        """(headers, body bytes, content type or None, accept) of the token request."""
        raise NotImplementedError

    def parse(self, data):
        """(token or None, seconds it lives) from the token answer's JSON."""
        raise NotImplementedError

    def unauthorized_message(self, host) -> str:
        return f"401 Unauthorized from {host}: the login was not accepted."

    def no_token_message(self, host) -> str:
        return f"{host} gave no token for the login."

    def long_secrets(self) -> list[str]:
        """The long-lived secrets (and any encoded form) to scrub."""
        return []

    # -- shared --
    def headers(self, client) -> dict:
        if not self._token or time.time() >= self._expires:
            self._fetch(client)
        return {"Authorization": f"Bearer {self._token}"}

    def _fetch(self, client):
        try:
            resp = client._exchange(self)
        except ConnectorError as exc:
            if exc.kind == "unauthorized":
                raise ConnectorError(self.unauthorized_message(client.host),
                                     "unauthorized", 401) from None
            raise
        data = resp.json()
        token, life = self.parse(data if isinstance(data, dict) else {})
        if not token:
            raise ConnectorError(self.no_token_message(client.host), "bad_response")
        self._token = token
        self._expires = time.time() + max(30, int(life) - 30)

    def secrets(self) -> list[str]:
        return self.long_secrets() + ([self._token] if self._token else [])


class OAuthClientCredentials(TokenExchange):
    """OAuth2 client credentials (Jama): POST <base><token_path>, then Bearer."""
    kind = "oauth"

    def __init__(self, client_id, client_secret, token_path="/rest/oauth/token"):
        super().__init__()
        self._basic = Basic(client_id, client_secret)
        self.token_path = token_path

    def exchange_request(self):
        return (self._basic.headers(None), b"grant_type=client_credentials",
                "application/x-www-form-urlencoded", "application/json")

    def parse(self, data):
        return data.get("access_token"), float(data.get("expires_in") or 3600)

    def unauthorized_message(self, host) -> str:
        return (f"401 Unauthorized from {host}: the client ID or client secret was "
                "not accepted (check them, and that the API client is still active).")

    def no_token_message(self, host) -> str:
        return f"{host} gave no access token for the client credentials."

    def long_secrets(self) -> list[str]:
        return self._basic.secrets()


class BlackDuckToken(TokenExchange):
    """Black Duck: POST /api/tokens/authenticate with `Authorization: token <API token>`,
    then the `bearerToken` (lives about two hours) as Bearer."""

    token_path = "/api/tokens/authenticate"
    ACCEPT = "application/vnd.blackducksoftware.user-4+json"

    def __init__(self, api_token):
        super().__init__()
        self._api_token = api_token

    def exchange_request(self):
        return {"Authorization": f"token {self._api_token}"}, b"", None, self.ACCEPT

    def parse(self, data):
        ms = data.get("expiresInMilliseconds")
        try:
            life = float(ms) / 1000 if ms is not None else 3600.0
        except (TypeError, ValueError):
            life = 3600.0
        return data.get("bearerToken"), life

    def unauthorized_message(self, host) -> str:
        return (f"401 Unauthorized from {host}: the API token was not accepted (check it, "
                "and that it is not expired or revoked).")

    def long_secrets(self) -> list[str]:
        return [self._api_token]


token_exchange = TokenExchange


def bearer(token) -> Auth:
    return Bearer(token)


def basic(user, secret) -> Auth:
    return Basic(user, secret)


def token_as_user(token) -> Auth:
    return TokenAsUser(token)


def oauth_client_credentials(client_id, client_secret, token_path="/rest/oauth/token") -> Auth:
    return OAuthClientCredentials(client_id, client_secret, token_path)


def blackduck_token(api_token) -> TokenExchange:
    return BlackDuckToken(api_token)


# --- helpers ------------------------------------------------------------------

def dig(data, dotted, default=None):
    """data['a']['b'] for 'a.b'; `default` when any step is missing."""
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def atlassian_kind(url) -> str:
    """'cloud' for *.atlassian.net, else 'dc' (Data Center / Server)."""
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return "cloud" if host == "atlassian.net" or host.endswith(".atlassian.net") else "dc"


def redact_headers(headers) -> dict:
    return {k: (REDACTED if k.lower() in SECRET_HEADERS else v) for k, v in headers.items()}


def ca_bundle_path(explicit=None) -> str | None:
    """The CA bundle to add: the connector's, else AI_SDLC_CA_BUNDLE, else SSL_CERT_FILE."""
    return explicit or os.environ.get("AI_SDLC_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE") or None


def ssl_context(ca_bundle=None) -> ssl.SSLContext:
    """A verifying context: the system's CAs, plus the bundle when one is set."""
    bundle = ca_bundle_path(ca_bundle)
    if not bundle:
        return ssl.create_default_context()
    path = os.path.expanduser(bundle)
    if not os.path.isfile(path):
        raise ConnectorError(f"The CA bundle {path} does not exist. Fix the path in ca_bundle "
                             "(run connect again) or in AI_SDLC_CA_BUNDLE / SSL_CERT_FILE.",
                             "config")
    try:
        ctx = ssl.create_default_context(cafile=path)
    except (ssl.SSLError, OSError) as exc:
        raise ConnectorError(f"The CA bundle {path} could not be read as PEM certificates "
                             f"({type(exc).__name__}).", "config") from None
    ctx.load_default_certs()
    return ctx


def proxy_for(url) -> str | None:
    """host:port of the proxy urllib will use for `url`, or None (no proxy, or NO_PROXY)."""
    parts = urllib.parse.urlsplit(url)
    proxy = urllib.request.getproxies().get(parts.scheme)
    if not proxy or urllib.request.proxy_bypass(parts.netloc.rsplit("@", 1)[-1]):
        return None
    p = urllib.parse.urlsplit(proxy if "://" in proxy else "http://" + proxy)
    return f"{p.hostname}:{p.port}" if p.port else (p.hostname or "the proxy")


def _origin(url):
    p = urllib.parse.urlsplit(url)
    return (p.hostname or "").lower(), p.port or (443 if p.scheme == "https" else 80)


def _loopback(host) -> bool:
    return host in ("localhost", "127.0.0.1", "::1")


class Response:
    def __init__(self, status, headers, body, url):
        self.status, self.headers, self.body, self.url = status, headers, body, url

    def json(self):
        try:
            return json.loads(self.body.decode("utf-8") or "null")
        except ValueError:
            host = urllib.parse.urlsplit(self.url).hostname
            raise ConnectorError(f"{host} answered with something that is not JSON (a login page "
                                 "or a proxy page?). Check the URL.", "bad_response") from None

    def text(self) -> str:
        return self.body.decode("utf-8", "replace")


class _SameHostRedirects(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only to the same host (credentials never go elsewhere)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        if (new.hostname or "").lower() != (old.hostname or "").lower() or \
                new.scheme not in (old.scheme, "https"):
            raise ConnectorError(f"{old.hostname} redirected to {new.hostname or newurl}; the "
                                 "connector does not follow it. Use the final URL in connect.",
                                 "config")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# --- paging ---------------------------------------------------------------------

class Offset:
    """startAt/maxResults style (Jira DC search, Jira changelog, Jama, Confluence DC)."""

    def __init__(self, start="startAt", size="maxResults", total="total", last=None):
        self.start, self.size, self.total, self.last = start, size, total, last

    def next(self, data, params, got):
        if got == 0:
            return None
        if self.last and dig(data, self.last) is True:
            return None
        start = int(params.get(self.start) or 0) + got
        total = dig(data, self.total) if self.total else None
        if self.last is None and isinstance(total, int) and start >= total:
            return None
        return None, {**params, self.start: start}


class BitbucketPaging:
    """start/limit with isLastPage and nextPageStart (Bitbucket Data Center)."""
    size = "limit"

    def next(self, data, params, got):
        if data.get("isLastPage", True) or data.get("nextPageStart") is None:
            return None
        return None, {**params, "start": data["nextPageStart"]}


class TokenPaging:
    """A cursor token in the body, sent back as a parameter (Jira Cloud /search/jql)."""

    def __init__(self, key="nextPageToken", param="nextPageToken", size="maxResults"):
        self.key, self.param, self.size = key, param, size

    def next(self, data, params, got):
        token = dig(data, self.key)
        return (None, {**params, self.param: token}) if token else None


class LinkPaging:
    """A next link in the body (Confluence `_links.next`, relative to `_links.base`)."""

    def __init__(self, key="_links.next", base="_links.base", size="limit"):
        self.key, self.base, self.size = key, base, size

    def next(self, data, params, got):
        link = dig(data, self.key)
        if not link:
            return None
        base = dig(data, self.base) if self.base else None
        if base and not link.startswith(("http://", "https://")):
            link = base.rstrip("/") + "/" + link.lstrip("/")
        return link, {}


# --- the client -------------------------------------------------------------------

class Client:
    def __init__(self, base_url, auth=None, *, ca_bundle=None, timeout=30.0, retries=3,
                 backoff=1.0, sleep=time.sleep, debug=None, allow_http=False, stderr=None):
        base_url = (base_url or "").strip().rstrip("/")
        parts = urllib.parse.urlsplit(base_url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ConnectorError(f"{base_url or 'The URL'} is not a web address; it should start "
                                 "with https://", "config")
        if parts.username or parts.password:
            raise ConnectorError("The URL must not contain a user name or password; connect "
                                 "asks for those separately.", "config")
        if parts.scheme == "http" and not (allow_http or _loopback(parts.hostname)):
            raise ConnectorError(f"Use an https:// URL for {parts.hostname}: credentials are "
                                 "never sent over plain http.", "config")
        self.base_url = base_url
        self.host = parts.hostname
        self.auth = auth or Auth()
        self.timeout, self.retries, self.backoff, self._sleep = timeout, retries, backoff, sleep
        self.debug = (os.environ.get("AI_SDLC_DEBUG", "") not in ("", "0")) if debug is None \
            else debug
        self._stderr = stderr
        self._ca_bundle = ca_bundle
        self._opener = None

    # -- urls --
    def url(self, path, params=None) -> str:
        """Absolute URL for `path` (relative to the base URL, or absolute on the same host)."""
        if path.startswith(("http://", "https://")):
            if _origin(path)[0] != _origin(self.base_url)[0]:
                raise ConnectorError(f"Refusing to follow a link from {self.host} to another "
                                     f"host ({urllib.parse.urlsplit(path).hostname}).", "config")
            url = path
        else:
            url = self.base_url + "/" + path.lstrip("/")
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        if clean:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(clean, doseq=True)
        return url

    def web_url(self, path) -> str:
        """A browser link under the base URL, for the `url` of an item."""
        return self.base_url + "/" + path.lstrip("/")

    # -- reads --
    def get(self, path, params=None, *, accept="application/json") -> Response:
        return self._send("GET", self.url(path, params), self.auth.headers(self), None, None,
                          accept)

    def get_json(self, path, params=None):
        return self.get(path, params).json()

    def get_text(self, path, params=None, *, accept="text/plain", max_bytes=None):
        """(text, truncated): the body as text, cut at `max_bytes` when given."""
        body = self.get(path, params, accept=accept).body
        if max_bytes is not None and len(body) > max_bytes:
            return body[:max_bytes].decode("utf-8", "replace"), True
        return body.decode("utf-8", "replace"), False

    def paginate(self, path, params=None, *, items="values", paging=None, limit=50,
                 page_size=50):
        """(items, truncated): up to `limit` items across pages."""
        paging = paging or Offset()
        params = dict(params or {})
        out = []
        while True:
            size = getattr(paging, "size", None)
            if size and not path.startswith(("http://", "https://")):
                params[size] = max(1, min(page_size, limit - len(out)))
            data = self.get_json(path, params)
            batch = (data if isinstance(data, list) else dig(data, items)) or []
            room = limit - len(out)
            out.extend(batch[:room])
            nxt = paging.next(data, params, len(batch)) if isinstance(data, dict) else None
            if len(out) >= limit:
                return out, bool(nxt) or len(batch) > room
            if not nxt or not batch:
                return out, False
            new_path, params = nxt
            path = new_path or path

    # -- transport --
    def opener(self):
        if self._opener is None:
            self._opener = urllib.request.build_opener(
                urllib.request.ProxyHandler(),
                urllib.request.HTTPSHandler(context=ssl_context(self._ca_bundle)),
                _SameHostRedirects())
        return self._opener

    def scrub(self, text) -> str:
        text = str(text)
        for secret in self.auth.secrets():
            if secret and len(secret) >= 4:
                text = text.replace(secret, REDACTED)
        return text

    def _log(self, line):
        if self.debug:
            print(line, file=self._stderr or sys.stderr)

    def _exchange(self, auth) -> Response:
        """The token request of the client's own token-exchange auth: the only POST."""
        if auth is not self.auth or not isinstance(auth, TokenExchange):
            raise ConnectorError(READ_ONLY, "config")
        headers, body, ctype, accept = auth.exchange_request()
        return self._send("POST", self.url(auth.token_path), headers, body, ctype, accept,
                          _exchange=auth)

    def _post_allowed(self, method, url, auth) -> bool:
        return (method == "POST" and auth is not None and auth is self.auth
                and isinstance(auth, TokenExchange) and bool(auth.token_path)
                and urllib.parse.urlsplit(url).path
                == urllib.parse.urlsplit(self.url(auth.token_path)).path)

    def _send(self, method, url, auth_headers, data, content_type, accept="application/json",
              *, _exchange=None):
        if method != "GET" and not self._post_allowed(method, url, _exchange):
            raise ConnectorError(READ_ONLY, "config")
        headers = {"Accept": accept, "User-Agent": "ai-sdlc-connectors/1"}
        headers.update(auth_headers)
        if content_type:
            headers["Content-Type"] = content_type
        for attempt in range(self.retries + 1):
            self._log(f"> {method} {url}")
            for k, v in redact_headers(headers).items():
                self._log(f"> {k}: {v}")
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with self.opener().open(req, timeout=self.timeout) as resp:
                    body = resp.read()
                    self._log(f"< {resp.status}")
                    return Response(resp.status, resp.headers, body, url)
            except urllib.error.HTTPError as exc:
                self._log(f"< {exc.code}")
                if exc.code in RETRY_STATUSES and attempt < self.retries:
                    self._sleep(self._wait(exc.headers, attempt))
                    continue
                raise self._http_error(exc, url, attempt) from None
            except ConnectorError:
                raise
            except (urllib.error.URLError, OSError, ssl.SSLError) as exc:
                raise self._net_error(exc, url) from None
        raise AssertionError("unreachable")

    def _wait(self, headers, attempt) -> float:
        try:
            wait = float(headers.get("Retry-After"))
        except (TypeError, ValueError):
            wait = self.backoff * (2 ** attempt)
        return max(0.0, min(wait, MAX_WAIT))

    def _http_error(self, exc, url, attempt) -> ConnectorError:
        code, host = exc.code, self.host
        path = urllib.parse.urlsplit(url).path
        detail = ""
        try:
            raw = exc.read(4000).decode("utf-8", "replace")
            data = json.loads(raw)
            msgs = (data.get("errorMessages") or data.get("errors") or data.get("message")
                    or data.get("error_description") or data.get("error"))
            if isinstance(msgs, list):
                msgs = "; ".join(str(m.get("message", m) if isinstance(m, dict) else m)
                                 for m in msgs)
            elif isinstance(msgs, dict):
                msgs = "; ".join(f"{k}: {v}" for k, v in msgs.items())
            detail = self.scrub(str(msgs or ""))[:200]
        except Exception:  # noqa: BLE001  the body is only a hint
            detail = ""
        tail = f" (server says: {detail})" if detail else ""
        if code == 401:
            return ConnectorError(f"401 Unauthorized from {host}: the credentials were not "
                                  "accepted (wrong or expired token, or the wrong user or "
                                  "email).", "unauthorized", 401)
        if code == 403:
            return ConnectorError(f"403 Forbidden from {host} for {path}: you are signed in, but "
                                  "this account may not read it. Ask for read access (after "
                                  "failed logins some servers want one browser sign-in first)."
                                  + tail, "forbidden", 403)
        if code == 404:
            return ConnectorError(f"404 Not Found from {host} for {path}: check the id, key or "
                                  "path, and that this account can see it." + tail,
                                  "not_found", 404)
        if code == 407:
            return ConnectorError(f"The proxy {proxy_for(url) or ''} asks for credentials (407 "
                                  "Proxy Authentication Required). Ask IT how to set the proxy.",
                                  "proxy", 407)
        if code == 429:
            return ConnectorError(f"429 Too Many Requests from {host}, still after {attempt} "
                                  "retries: wait a minute and try again.", "rate_limited", 429)
        if code >= 500:
            return ConnectorError(f"{code} from {host}: the server had a problem; try again "
                                  "later." + tail, "server", code)
        return ConnectorError(f"{code} from {host} for {path}." + tail, "http", code)

    def _net_error(self, exc, url) -> ConnectorError:
        reason = getattr(exc, "reason", exc)
        host = self.host
        port = urllib.parse.urlsplit(url).port or (443 if url.startswith("https") else 80)
        proxy = proxy_for(url)
        text = self.scrub(str(reason))
        if isinstance(reason, ssl.SSLCertVerificationError):
            return ConnectorError(
                f"The TLS certificate of {host} could not be verified "
                f"({self.scrub(getattr(reason, 'verify_message', '') or text)}). If your company "
                "uses its own certificate authority, set ca_bundle (run connect again) or "
                "AI_SDLC_CA_BUNDLE to its PEM file. Verification is never switched off.", "tls")
        if isinstance(reason, ssl.SSLError):
            return ConnectorError(f"The TLS handshake with {host} failed ({text}).", "tls")
        if "Tunnel connection failed" in text:
            if "407" in text:
                return ConnectorError(f"The proxy {proxy or ''} asks for credentials (407 Proxy "
                                      "Authentication Required). Ask IT how to set the proxy.",
                                      "proxy", 407)
            return ConnectorError(f"The proxy {proxy or ''} could not open a connection to {host} "
                                  f"({text}). Check HTTPS_PROXY, or add {host} to NO_PROXY.",
                                  "proxy")
        if isinstance(reason, socket.gaierror):
            if proxy:
                return ConnectorError(f"The proxy {proxy} could not be found (DNS). Check "
                                      "HTTPS_PROXY / HTTP_PROXY.", "proxy")
            return ConnectorError(f"The name {host} could not be found (DNS). Check the URL, "
                                  "and whether you need the VPN.", "dns")
        if isinstance(reason, ConnectionRefusedError):
            if proxy:
                return ConnectorError(f"The proxy {proxy} refused the connection. Check "
                                      f"HTTPS_PROXY / HTTP_PROXY, or add {host} to NO_PROXY.",
                                      "proxy")
            return ConnectorError(f"Nothing answered at {host}:{port} (connection refused). "
                                  "Check the URL and the port.", "refused")
        if isinstance(reason, (socket.timeout, TimeoutError)):
            via = f" through the proxy {proxy}" if proxy else ""
            return ConnectorError(f"{host} did not answer within {self.timeout:g}s{via} "
                                  "(timeout). Check the VPN or proxy.", "timeout")
        return ConnectorError(f"Could not reach {host}" + (f" through the proxy {proxy}"
                              if proxy else "") + f": {text}", "network")
