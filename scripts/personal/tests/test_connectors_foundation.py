#!/usr/bin/env python3
"""Connectors foundation: store, http client, registry, connect/connections/disconnect,
and the connectors.py CLI, against tests/fakeserver.py (no network)."""
import argparse
import base64
import contextlib
import io
import json
import os
import socket
import ssl
import stat
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import helpers
from fakeserver import ConnectorTestCase, Reply, Seq, free_port
from personal.connectors import http, manage, registry, store, text

sys.path.insert(0, str(helpers.KIT))
import connectors as connectors_cli  # noqa: E402  the kit-root connectors.py

STUB_FILE = Path(__file__).resolve().parent / "stub_connector.py"
NAME = "stub_connector"
SECRET = "s3cr3t-T0KEN-value-42"
ME = {"login": "ana", "name": "Ana Pop"}


def stub_registry():
    return registry.discover(extra=[STUB_FILE])


class Base(ConnectorTestCase):
    """Each test gets its own config folder and an environment with no AI_SDLC_* or proxy."""

    def setUp(self):
        super().setUp()
        self.connectors = stub_registry()
        self.stub = self.connectors[NAME]

    def save_stub(self, url, **extra):
        return store.save(NAME, {"url": url, "token": SECRET, **extra})

    def connect(self, *answers, secret=SECRET, isatty=True, test_only=False):
        """Run connect with scripted answers; returns (code, lines, everything shown)."""
        shown, queue = [], list(answers)

        def ask(prompt):
            shown.append(prompt)
            return queue.pop(0) if queue else ""

        def ask_secret(prompt):
            shown.append(prompt)
            return secret

        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code, lines = manage.connect(NAME, test_only=test_only, connectors=self.connectors,
                                         isatty=isatty, ask=ask, ask_secret=ask_secret,
                                         say=shown.append)
        return code, lines, "\n".join(shown + lines) + out.getvalue()


# --- store ---------------------------------------------------------------------------

class TestStore(Base):
    def test_save_makes_a_private_folder_and_file(self):
        self.addCleanup(os.umask, os.umask(0o022))
        path = self.save_stub("https://x.example")
        self.assertEqual(path, self.base / "config/connectors" / f"{NAME}.json")
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        self.assertEqual(json.loads(path.read_text())["values"]["token"], SECRET)

    def test_save_tightens_an_existing_loose_folder(self):
        folder = self.base / "config/connectors"
        folder.mkdir(parents=True, mode=0o755)
        os.chmod(folder, 0o755)
        self.save_stub("https://x.example")
        self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)

    def test_save_is_atomic_and_leaves_no_temp_file(self):
        path = self.save_stub("https://one.example")
        with mock.patch.object(store.json, "dump", side_effect=RuntimeError("disk full")):
            with self.assertRaises(RuntimeError):
                self.save_stub("https://two.example")
        self.assertEqual(json.loads(path.read_text())["values"]["url"], "https://one.example")
        self.assertEqual([p.name for p in path.parent.iterdir()], [path.name])

    def test_save_keeps_the_last_test(self):
        self.save_stub("https://x.example")
        store.record_test(NAME, True, "OK", "ana")
        self.save_stub("https://y.example")
        self.assertTrue(store.read_file(NAME)["last_test"]["ok"])

    def test_xdg_config_home_when_no_override(self):
        del os.environ["AI_SDLC_CONFIG_DIR"]
        os.environ["XDG_CONFIG_HOME"] = str(self.base / "xdg")
        self.assertEqual(store.connectors_dir(), self.base / "xdg/ai-sdlc/connectors")
        del os.environ["XDG_CONFIG_HOME"]
        self.assertEqual(store.connectors_dir(), Path.home() / ".config/ai-sdlc/connectors")

    def test_env_overrides_the_file(self):
        self.save_stub("https://file.example")
        os.environ["AI_SDLC_STUB_CONNECTOR_URL"] = "https://env.example"
        values = store.load(NAME, self.stub.keys)
        self.assertEqual(values, {"url": "https://env.example", "token": SECRET})
        self.assertEqual(store.source(NAME, self.stub.keys), "file+env")

    def test_env_alone_is_enough(self):
        os.environ["AI_SDLC_STUB_CONNECTOR_URL"] = "https://env.example"
        os.environ["AI_SDLC_STUB_CONNECTOR_TOKEN"] = SECRET
        self.assertEqual(store.load(NAME, self.stub.keys)["token"], SECRET)
        self.assertEqual(store.source(NAME, self.stub.keys), "env")
        self.assertFalse(store.file_for(NAME).exists())

    def test_bad_names_are_refused(self):
        for bad in ("../x", "Jira", "", "a/b"):
            with self.assertRaises(ValueError):
                store.file_for(bad)


# --- http client -------------------------------------------------------------------------

class TestHttp(Base):
    def test_bearer_header(self):
        srv = self.server({"/api/me": ME})
        http.Client(srv.url, http.bearer(SECRET)).get_json("/api/me")
        self.assertEqual(srv.requests[0].headers["Authorization"], f"Bearer {SECRET}")

    def test_basic_header(self):
        srv = self.server({"/api/me": ME})
        http.Client(srv.url, http.basic("ana@x.example", SECRET)).get_json("/api/me")
        want = base64.b64encode(f"ana@x.example:{SECRET}".encode()).decode()
        self.assertEqual(srv.requests[0].headers["Authorization"], f"Basic {want}")

    def test_oauth_client_credentials_then_bearer(self):
        srv = self.server({"/rest/oauth/token": {"access_token": "tok-123", "expires_in": 3600},
                           "/rest/v1/users/current": {"data": {"username": "ana"}}})
        c = http.Client(srv.url, http.oauth_client_credentials("cid", SECRET))
        c.get_json("/rest/v1/users/current")
        c.get_json("/rest/v1/users/current")
        token_req, call, call2 = srv.requests
        self.assertEqual((token_req.method, token_req.path), ("POST", "/rest/oauth/token"))
        self.assertEqual(token_req.body, b"grant_type=client_credentials")
        self.assertEqual(token_req.headers["Authorization"],
                         "Basic " + base64.b64encode(f"cid:{SECRET}".encode()).decode())
        self.assertEqual(call.headers["Authorization"], "Bearer tok-123")
        self.assertEqual(call2.headers["Authorization"], "Bearer tok-123")  # token reused

    def test_oauth_bad_client_secret_is_plain(self):
        srv = self.server({"/rest/oauth/token": Reply(401, {"error": "invalid_client"})})
        c = http.Client(srv.url, http.oauth_client_credentials("cid", SECRET))
        with self.assertRaises(http.ConnectorError) as cm:
            c.get_json("/x")
        self.assertIn("client ID or client secret was not accepted", str(cm.exception))

    def test_only_get_requests_are_sent(self):
        c = http.Client("https://x.example", http.bearer(SECRET))
        with self.assertRaises(http.ConnectorError) as cm:
            c._send("POST", c.url("/x"), {}, b"{}", "application/json")
        self.assertIn("read-only", str(cm.exception))

    def test_retries_429_then_succeeds(self):
        srv = self.server({"/api/me": Seq(Reply(429, {}, {"Retry-After": "2"}), Reply(200, ME))})
        waits = []
        data = http.Client(srv.url, http.bearer(SECRET), sleep=waits.append).get_json("/api/me")
        self.assertEqual(data, ME)
        self.assertEqual(len(srv.requests), 2)
        self.assertEqual(waits, [2.0])

    def test_retries_5xx_with_backoff_then_gives_up_plainly(self):
        srv = self.server({"/api/me": Reply(503, {})})
        waits = []
        c = http.Client(srv.url, http.bearer(SECRET), sleep=waits.append, retries=2, backoff=0.5)
        with self.assertRaises(http.ConnectorError) as cm:
            c.get_json("/api/me")
        self.assertEqual(waits, [0.5, 1.0])
        self.assertEqual((cm.exception.kind, cm.exception.status), ("server", 503))

    def test_retry_after_is_capped(self):
        srv = self.server({"/x": Seq(Reply(429, {}, {"Retry-After": "3600"}), Reply(200, {}))})
        waits = []
        http.Client(srv.url, http.bearer(SECRET), sleep=waits.append).get_json("/x")
        self.assertEqual(waits, [http.MAX_WAIT])

    def test_plain_errors_for_401_403_404(self):
        srv = self.server({"/a": Reply(401, {}), "/b": Reply(403, {"message": "no"}),
                           "/c": Reply(404, {})})
        c = http.Client(srv.url, http.bearer(SECRET))
        for path, kind, words in (("/a", "unauthorized", "credentials were not accepted"),
                                  ("/b", "forbidden", "may not read it"),
                                  ("/c", "not_found", "check the id")):
            with self.assertRaises(http.ConnectorError) as cm:
                c.get_json(path)
            self.assertEqual(cm.exception.kind, kind)
            self.assertIn(words, str(cm.exception))

    def test_a_secret_echoed_by_the_server_is_scrubbed(self):
        srv = self.server({"/a": Reply(400, {"message": f"bad token {SECRET}"})})
        with self.assertRaises(http.ConnectorError) as cm:
            http.Client(srv.url, http.bearer(SECRET)).get_json("/a")
        self.assertNotIn(SECRET, str(cm.exception))
        self.assertIn("<redacted>", str(cm.exception))

    def test_connection_refused_is_plain(self):
        c = http.Client(f"http://127.0.0.1:{free_port()}", http.bearer(SECRET))
        with self.assertRaises(http.ConnectorError) as cm:
            c.get_json("/x")
        self.assertEqual(cm.exception.kind, "refused")
        self.assertIn("connection refused", str(cm.exception))

    def test_tls_dns_and_proxy_failures_are_plain(self):
        c = http.Client("https://jira.example.com", http.bearer(SECRET))
        url = c.url("/x")
        cert = ssl.SSLCertVerificationError(1, "certificate verify failed")
        cert.verify_message = "self-signed certificate in certificate chain"
        e = c._net_error(urllib.error.URLError(cert), url)
        self.assertEqual(e.kind, "tls")
        self.assertIn("AI_SDLC_CA_BUNDLE", str(e))
        self.assertIn("never switched off", str(e))
        e = c._net_error(urllib.error.URLError(socket.gaierror(8, "nodename nor servname")), url)
        self.assertEqual((e.kind, "DNS" in str(e)), ("dns", True))
        e = c._net_error(OSError("Tunnel connection failed: 407 Proxy Authentication Required"),
                         url)
        self.assertEqual((e.kind, e.status), ("proxy", 407))
        e = c._net_error(urllib.error.URLError(socket.timeout("timed out")), url)
        self.assertEqual(e.kind, "timeout")

    def test_refused_proxy_is_named_without_its_credentials(self):
        os.environ["HTTPS_PROXY"] = os.environ["https_proxy"] = \
            f"http://bob:pw@127.0.0.1:{free_port()}"
        del os.environ["NO_PROXY"], os.environ["no_proxy"]
        c = http.Client("https://jira.example.com", http.bearer(SECRET))
        with self.assertRaises(http.ConnectorError) as cm:
            c.get_json("/x")
        self.assertEqual(cm.exception.kind, "proxy")
        self.assertIn("127.0.0.1", str(cm.exception))
        self.assertNotIn("pw", str(cm.exception))

    def test_http_proxy_env_is_used(self):
        srv = self.server({"/api/me": ME})
        os.environ["HTTP_PROXY"] = os.environ["http_proxy"] = srv.url
        del os.environ["NO_PROXY"], os.environ["no_proxy"]
        c = http.Client("http://jira.example.invalid", http.bearer(SECRET), allow_http=True)
        self.assertEqual(c.get_json("/api/me"), ME)
        self.assertEqual(srv.requests[0].target, "http://jira.example.invalid/api/me")

    def test_no_proxy_bypasses_the_proxy(self):
        srv = self.server({"/api/me": ME})
        os.environ["HTTP_PROXY"] = os.environ["http_proxy"] = f"http://127.0.0.1:{free_port()}"
        self.assertEqual(http.Client(srv.url, http.bearer(SECRET)).get_json("/api/me"), ME)
        self.assertEqual(srv.requests[0].target, "/api/me")

    def test_ca_bundle_goes_to_create_default_context(self):
        bundle = self.base / "corp.pem"
        bundle.write_text("pem")
        env_bundle = self.base / "env.pem"
        env_bundle.write_text("pem")
        with mock.patch.object(http.ssl, "create_default_context") as cdc:
            http.ssl_context(str(bundle))
            cdc.assert_called_with(cafile=str(bundle))
            cdc.return_value.load_default_certs.assert_called_with()  # system CAs kept
            os.environ["SSL_CERT_FILE"] = str(env_bundle)
            http.ssl_context(None)
            cdc.assert_called_with(cafile=str(env_bundle))
            os.environ["AI_SDLC_CA_BUNDLE"] = str(bundle)
            http.ssl_context(None)
            cdc.assert_called_with(cafile=str(bundle))
            del os.environ["AI_SDLC_CA_BUNDLE"], os.environ["SSL_CERT_FILE"]
            http.ssl_context(None)
            cdc.assert_called_with()

    def test_connector_ca_bundle_reaches_the_client(self):
        bundle = self.base / "corp.pem"
        bundle.write_text("pem")
        ctx = registry.open_context(self.stub, {"url": "https://x.example", "token": SECRET,
                                                "ca_bundle": str(bundle)})
        with mock.patch.object(http.ssl, "create_default_context") as cdc:
            ctx.client.opener()
        cdc.assert_called_with(cafile=str(bundle))

    def test_missing_ca_bundle_is_plain_and_verification_stays_on(self):
        with self.assertRaises(http.ConnectorError) as cm:
            http.ssl_context(str(self.base / "nope.pem"))
        self.assertIn("does not exist", str(cm.exception))
        self.assertEqual(http.ssl_context(None).verify_mode, ssl.CERT_REQUIRED)

    def test_https_is_required_except_on_loopback(self):
        with self.assertRaises(http.ConnectorError) as cm:
            http.Client("http://jira.example.com", http.bearer(SECRET))
        self.assertIn("https://", str(cm.exception))
        with self.assertRaises(http.ConnectorError):
            http.Client("https://ana:pw@jira.example.com")
        http.Client("http://127.0.0.1:8080")  # tests and local tools

    def test_links_to_another_host_are_refused(self):
        c = http.Client("https://jira.example.com", http.bearer(SECRET))
        self.assertEqual(c.url("https://jira.example.com/a?b=1", {"c": 2}),
                         "https://jira.example.com/a?b=1&c=2")
        with self.assertRaises(http.ConnectorError):
            c.url("https://evil.example.net/steal")

    def test_debug_output_redacts_authorization(self):
        srv = self.server({"/api/me": ME})
        err = io.StringIO()
        http.Client(srv.url, http.basic("ana", SECRET), debug=True, stderr=err).get_json("/api/me")
        self.assertIn("> Authorization: <redacted>", err.getvalue())
        self.assertNotIn(SECRET, err.getvalue())
        self.assertNotIn(base64.b64encode(f"ana:{SECRET}".encode()).decode(), err.getvalue())

    def test_paging_presets(self):
        pages = {"0": {"values": [1, 2], "total": 5}, "2": {"values": [3, 4], "total": 5},
                 "4": {"values": [5], "total": 5}}
        srv = self.server({"/o": lambda r: pages[r.query.get("startAt", ["0"])[0]],
                           "/b": lambda r: {"values": ["a"], "isLastPage": "start" in r.query,
                                            "nextPageStart": 7},
                           "/t": lambda r: {"issues": [r.query.get("nextPageToken", ["-"])[0]],
                                            "nextPageToken": None if "nextPageToken" in r.query
                                            else "abc"},
                           "/l": lambda r: {"results": [r.query.get("cursor", ["-"])[0]],
                                            "_links": {"base": srv.url, "next":
                                                       None if "cursor" in r.query
                                                       else "/l?cursor=z"}}})
        c = http.Client(srv.url, http.bearer(SECRET))
        self.assertEqual(c.paginate("/o", page_size=2, limit=10), ([1, 2, 3, 4, 5], False))
        self.assertEqual(c.paginate("/o", page_size=2, limit=3), ([1, 2, 3], True))
        self.assertEqual(c.paginate("/b", paging=http.BitbucketPaging()), (["a", "a"], False))
        self.assertEqual(c.paginate("/t", items="issues", paging=http.TokenPaging()),
                         (["-", "abc"], False))
        self.assertEqual(c.paginate("/l", items="results", paging=http.LinkPaging()),
                         (["-", "z"], False))

    def test_atlassian_kind(self):
        self.assertEqual(http.atlassian_kind("https://acme.atlassian.net"), "cloud")
        self.assertEqual(http.atlassian_kind("https://jira.acme.example/jira"), "dc")
        self.assertEqual(http.atlassian_kind("https://atlassian.net.evil.example"), "dc")


# --- registry ------------------------------------------------------------------------------

class TestRegistry(Base):
    def test_discovers_the_stub(self):
        self.assertIn(NAME, self.connectors)
        self.assertEqual(self.stub.title, "Stub")
        self.assertEqual(self.stub.keys, ["url", "user", "token", "ca_bundle"])
        self.assertEqual(list(self.stub.commands), ["things"])

    def test_the_glob_skips_foundation_and_private_modules(self):
        found = registry.names()
        for name in ("__init__", "store", "http", "registry", "manage", "text"):
            self.assertNotIn(name, found)
        self.assertFalse([n for n in found if n.startswith("_")])
        registry.discover()  # every shipped connector module loads and validates

    def test_a_folder_with_a_new_module_is_found_without_touching_shared_files(self):
        folder = self.base / "pkg"
        folder.mkdir()
        (folder / "store.py").write_text("")
        (folder / "_helper.py").write_text("")
        (folder / "newthing.py").write_text("")
        self.assertEqual(registry.names(folder), ["newthing"])

    def test_a_broken_module_is_refused_plainly(self):
        bad = type(sys)("bad")
        bad.TITLE = "Bad"
        bad.FIELDS = [registry.Field("token", "Token", secret=True)]
        with self.assertRaises(ValueError) as cm:
            registry.from_module("bad", bad)
        for words in ("first field must be 'url'", "auth(values)", "WHOAMI", "COMMANDS"):
            self.assertIn(words, str(cm.exception))

    def test_a_forced_kind_reaches_auth_not_only_the_context(self):
        seen = []
        mod = type(sys)("kinded")
        mod.TITLE, mod.WHOAMI, mod.COMMANDS = "Kinded", self.stub.whoami, {}
        mod.FIELDS = [registry.Field("url", "URL"), registry.Field("token", "T", secret=True)]
        mod.kind = lambda values: "dc"                      # what the URL rule says

        def auth(values, kind=None):
            seen.append(kind)
            return http.basic("me", values["token"]) if kind == "cloud" else \
                http.bearer(values["token"])
        mod.auth = auth
        c = registry.from_module("kinded", mod)
        values = {"url": "http://127.0.0.1:1", "token": SECRET}
        forced = registry.open_context(c, values, kind="cloud")
        self.assertEqual((forced.kind, seen[-1]), ("cloud", "cloud"))
        self.assertTrue(forced.client.auth.headers(None)["Authorization"].startswith("Basic "))
        plain = registry.open_context(c, values)
        self.assertEqual((plain.kind, seen[-1]), ("dc", "dc"))
        self.assertEqual(plain.client.auth.headers(None)["Authorization"], f"Bearer {SECRET}")
        # A module whose auth takes only the values still works with a forced kind.
        ctx = registry.open_context(self.stub, values, kind="cloud")
        self.assertEqual(ctx.kind, "cloud")
        self.assertEqual(ctx.client.auth.headers(None)["Authorization"], f"Bearer {SECRET}")


# --- setup.py connect / connections / disconnect -----------------------------------------

class TestManage(Base):
    def test_connect_asks_saves_and_tests(self):
        srv = self.server({"/api/me": ME})
        code, lines, shown = self.connect(srv.url, "")
        self.assertEqual(code, 0, lines)
        self.assertIn("OK: signed in to 127.0.0.1 as Ana Pop.", shown)
        values = store.read_file(NAME)["values"]
        self.assertEqual(values, {"url": srv.url, "token": SECRET})
        self.assertNotIn(SECRET, shown)
        self.assertTrue(store.read_file(NAME)["last_test"]["ok"])

    def test_connect_again_keeps_values_on_enter(self):
        srv = self.server({"/api/me": ME})
        self.connect(srv.url, "ana")
        code, _, shown = self.connect("", "", secret="")
        self.assertEqual(code, 0)
        self.assertEqual(store.read_file(NAME)["values"],
                         {"url": srv.url, "user": "ana", "token": SECRET})
        self.assertIn("Enter keeps the saved one", shown)

    def test_connect_refuses_without_a_terminal(self):
        code, lines, shown = self.connect("https://x.example", isatty=False)
        self.assertEqual(code, 2)
        self.assertIn("runs only in your own terminal", lines[0])
        # no hint at environment variables an assistant could fill with a pasted secret
        self.assertNotIn("AI_SDLC_", "\n".join(lines))
        self.assertFalse(store.file_for(NAME).exists())

    def test_the_environment_hint_is_in_the_help(self):
        sys.path.insert(0, str(helpers.KIT))
        import setup  # the kit-root setup.py
        action = next(a for a in setup.parser()._actions
                      if isinstance(a, argparse._SubParsersAction))
        self.assertIn("AI_SDLC_<NAME>_<FIELD>", action.choices["connect"].format_help())

    def test_connect_as_root_warns_that_the_login_is_shared(self):
        srv = self.server({"/api/me": ME})
        with mock.patch.object(manage, "_is_root", return_value=True):
            code, lines, shown = self.connect(srv.url, "")
        self.assertEqual(code, 0, lines)
        warning = [x for x in shown.splitlines() if x.startswith("Warning: you are running as root")]
        self.assertTrue(warning, shown)
        self.assertIn("everyone who uses root on this computer", warning[0])
        with mock.patch.object(manage, "_is_root", return_value=False):
            _, _, shown = self.connect(srv.url, "")
        self.assertNotIn("running as root", shown)

    def test_connect_without_a_terminal_works_when_env_has_every_value(self):
        srv = self.server({"/api/me": ME})
        os.environ["AI_SDLC_STUB_CONNECTOR_URL"] = srv.url
        os.environ["AI_SDLC_STUB_CONNECTOR_TOKEN"] = SECRET
        code, lines, shown = self.connect(isatty=False)
        self.assertEqual(code, 0, lines)
        self.assertNotIn(SECRET, shown)

    def test_connect_refuses_a_plain_http_url_and_saves_nothing(self):
        code, lines, _ = self.connect("http://jira.example.com", "")
        self.assertEqual(code, 2)
        self.assertIn("https://", lines[0])
        self.assertFalse(store.file_for(NAME).exists())

    def test_connector_check_can_refuse(self):
        code, lines, _ = self.connect("https://forbidden.example", "")
        self.assertEqual((code, lines), (2, ["The stub does not support that host."]))

    def test_unknown_connector(self):
        code, lines = manage.connect("nosuch", connectors=self.connectors)
        self.assertEqual(code, 2)
        self.assertIn("There is no connector 'nosuch'", lines[0])

    def test_test_reports_401_403_and_refused_plainly(self):
        srv = self.server({"/api/me": Reply(401, {"message": f"token {SECRET} expired"})})
        self.save_stub(srv.url)
        code, lines, shown = self.connect(test_only=True)
        self.assertEqual(code, 1)
        self.assertIn("401 Unauthorized", lines[0])
        self.assertNotIn(SECRET, shown)
        self.assertFalse(store.read_file(NAME)["last_test"]["ok"])

        srv.routes["/api/me"] = Reply(403, {})
        self.assertIn("403 Forbidden", self.connect(test_only=True)[1][0])

        self.save_stub(f"http://127.0.0.1:{free_port()}")
        code, lines, _ = self.connect(test_only=True)
        self.assertIn("connection refused", lines[0])

    def test_test_when_not_connected(self):
        code, lines, _ = self.connect(test_only=True)
        self.assertEqual(code, 1)
        self.assertIn("setup.py connect stub_connector", lines[0])

    def test_connections_lists_without_secrets(self):
        srv = self.server({"/api/me": ME})
        self.connect(srv.url, "ana")
        code, lines = manage.connections(self.connectors)
        text = "\n".join(lines)
        self.assertEqual(code, 0)
        self.assertIn(f"- {NAME}: {srv.url} · Data Center · user ana · last test OK", text)
        self.assertIn("from file", text)
        self.assertNotIn(SECRET, text)

    def test_connections_for_an_env_login_points_at_the_test(self):
        """Copilot re-test 2026-10-10 (N3): an env login has no known user; say how to check."""
        os.environ["AI_SDLC_STUB_CONNECTOR_URL"] = "https://env.example"
        os.environ["AI_SDLC_STUB_CONNECTOR_TOKEN"] = SECRET
        text = "\n".join(manage.connections(self.connectors)[1])
        self.assertIn(f"- {NAME}: https://env.example · Data Center · from environment (run python3 "
                      f".ai-sdlc/kit/setup.py connect {NAME} --test to check)", text)
        self.assertNotIn("user ?", text)
        self.assertNotIn(SECRET, text)

    def test_connections_shows_not_connected_and_loose_files(self):
        self.assertIn("not connected", "\n".join(manage.connections(self.connectors)[1]))
        path = self.save_stub("https://x.example")
        os.chmod(path, 0o644)
        self.assertIn("can be read by other users",
                      "\n".join(manage.connections(self.connectors)[1]))

    def test_disconnect_deletes_the_file(self):
        self.save_stub("https://x.example")
        code, lines = manage.disconnect(NAME, self.connectors, yes=True)
        self.assertEqual((code, lines), (0, ["Removed the saved Stub connection."]))
        self.assertFalse(store.file_for(NAME).exists())
        os.environ["AI_SDLC_STUB_CONNECTOR_TOKEN"] = SECRET
        _, lines = manage.disconnect(NAME, self.connectors, yes=True)
        self.assertIn("There was no saved Stub connection.", lines)
        self.assertIn("still apply", lines[1])

    def test_disconnect_without_yes_asks_and_keeps_the_file(self):
        path = self.save_stub("https://x.example")
        code, lines = manage.disconnect(NAME, self.connectors)
        text = "\n".join(lines)
        self.assertEqual(code, 2, text)
        self.assertTrue(path.is_file())
        self.assertIn("Nothing was deleted yet.", text)
        self.assertIn(str(path), text)
        self.assertIn("Delete your saved Stub login?", text)
        self.assertIn(f"python3 .ai-sdlc/kit/setup.py disconnect {NAME} --yes", text)

    def test_disconnect_with_nothing_saved_needs_no_yes(self):
        code, lines = manage.disconnect(NAME, self.connectors)
        self.assertEqual((code, lines), (0, ["There was no saved Stub connection."]))

    def test_setup_py_has_the_three_commands(self):
        root = helpers.make_repo(self.base / "repo")
        code, out = helpers.cli(root, helpers.KIT, "connect", "nosuch")
        self.assertEqual(code, 2)
        self.assertIn("There is no connector 'nosuch'", out)
        code, out = helpers.cli(root, helpers.KIT, "connections")
        self.assertEqual(code, 0)
        self.assertIn(str(self.base / "config/connectors"), out)
        self.assertEqual(helpers.cli(root, helpers.KIT, "disconnect", "nosuch")[0], 0)


class TestRemoveKeepsCredentials(Base):
    def test_remove_leaves_the_credentials_folder(self):
        path = self.save_stub("https://x.example")
        root = helpers.make_repo(self.base / "repo", {"README.md": "team\n"})
        copy = helpers.copy_kit(root / "ai-sdlc-kit")
        kit = root / ".ai-sdlc/kit"
        helpers.cli(root, copy, "setup", "--protect-only")
        helpers.cli(root, kit, "setup", "--name", "Ana", "--roles", "dev", "--lang", "en")
        code, out = helpers.cli(root, kit, "remove", "--yes")
        self.assertEqual(code, 0, out)
        self.assertTrue(path.is_file())
        self.assertEqual(json.loads(path.read_text())["values"]["token"], SECRET)

    def test_remove_never_touches_the_default_home_folder(self):
        home = self.base / "home"
        home.mkdir()
        env = {"HOME": str(home)}
        with mock.patch.dict(os.environ, env):
            for k in ("AI_SDLC_CONFIG_DIR", "XDG_CONFIG_HOME"):
                os.environ.pop(k, None)
            path = self.save_stub("https://x.example")
            folder = home / ".config/ai-sdlc/connectors"
            self.assertEqual(path.parent, folder)

            def snap():   # every entry's bytes, mtime and mode, the folder's own included
                return {p.name: (p.read_bytes() if p.is_file() else None, p.stat().st_mtime_ns,
                                 stat.S_IMODE(p.stat().st_mode))
                        for p in [folder, *folder.iterdir()]}
            before = snap()
            root = helpers.make_repo(self.base / "repo", {"README.md": "team\n"})
            copy = helpers.copy_kit(root / "ai-sdlc-kit")
            kit = root / ".ai-sdlc/kit"
            helpers.cli(root, copy, "setup", "--protect-only")
            helpers.cli(root, kit, "setup", "--name", "Ana", "--roles", "dev", "--lang", "en")
            code, out = helpers.cli(root, kit, "remove", "--yes")
            self.assertEqual(code, 0, out)
            self.assertEqual(snap(), before)
            self.assertNotIn(SECRET, out)


# --- connectors.py --------------------------------------------------------------------------

class TestConnectorsCli(Base):
    def run_cli(self, *argv, **kw):
        out, err = io.StringIO(), io.StringIO()
        code = connectors_cli.main(list(argv), connectors=self.connectors, out=out, err=err, **kw)
        return code, out.getvalue(), err.getvalue()

    def test_lists_connectors_and_commands(self):
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn(f"- {NAME} (Stub): whoami, things", out)

    def test_whoami_and_paged_list_as_json(self):
        things = [{"id": i, "name": f"t{i}"} for i in range(1, 6)]
        srv = self.server({"/api/me": ME, "/api/things": lambda r: {
            "values": things[int(r.query.get("startAt", ["0"])[0]):][
                :int(r.query["maxResults"][0])], "total": 5}})
        self.save_stub(srv.url)
        code, out, err = self.run_cli(NAME, "whoami", "--json")
        self.assertEqual(code, 0, err)
        doc = json.loads(out)
        self.assertEqual(doc["item"]["user"], "ana")
        self.assertEqual((doc["connector"], doc["command"], doc["source"]),
                         (NAME, "whoami", srv.url))
        code, out, _ = self.run_cli(NAME, "things", "--limit", "3", "--json")
        doc = json.loads(out)
        self.assertEqual([t["id"] for t in doc["items"]], [1, 2, 3])
        self.assertEqual((doc["count"], doc["truncated"]), (3, True))
        self.assertTrue(all(t["url"].startswith(srv.url + "/things/") for t in doc["items"]))
        code, out, _ = self.run_cli(NAME, "things")
        self.assertIn(f"- t1  {srv.url}/things/1", out)
        self.assertIn("(5 shown)", out)
        self.assertTrue(all(r.method == "GET" for r in srv.requests))

    def test_not_connected_points_at_setup_connect(self):
        code, _, err = self.run_cli(NAME, "whoami")
        self.assertEqual(code, connectors_cli.EXIT_NOT_CONNECTED)
        self.assertIn("setup.py connect stub_connector", err)
        self.assertIn("never through the assistant", err)

    def test_errors_are_plain_and_never_carry_a_secret(self):
        srv = self.server({"/api/me": Reply(401, {"message": f"bad {SECRET}"})})
        self.save_stub(srv.url, user="ana")
        debug = io.StringIO()
        with contextlib.redirect_stderr(debug):
            code, out, err = self.run_cli(NAME, "whoami", "--json", client_kwargs={"debug": True})
        self.assertEqual(code, connectors_cli.EXIT_ERROR)
        self.assertIn("401 Unauthorized", err)
        self.assertIn("setup.py connect stub_connector", err)
        self.assertIn("> Authorization: <redacted>", debug.getvalue())
        self.assertNotIn(SECRET, out + err + debug.getvalue())

    def test_unexpected_errors_are_scrubbed(self):
        self.save_stub("https://x.example")
        boom = registry.Command("boom", run=lambda ctx, a: (_ for _ in ()).throw(
            RuntimeError(f"leak {SECRET}")))
        self.connectors[NAME].commands["boom"] = boom
        code, out, err = self.run_cli(NAME, "boom")
        self.assertEqual(code, connectors_cli.EXIT_ERROR)
        self.assertIn("unexpected error (RuntimeError)", err)
        self.assertNotIn(SECRET, out + err)


class TestTestingHelpers(Base):
    """The ConnectorTestCase helpers the B tasks use."""

    def test_run_command_and_run_cli(self):
        srv = self.server({"/api/me": ME, "/api/things": {"values": [{"id": 1, "name": "a"}],
                                                          "total": 1}})
        ctx = self.context(self.stub, {"url": srv.url, "token": SECRET}, kind="cloud")
        self.assertEqual(ctx.kind, "cloud")
        self.assertEqual(self.run_command(self.stub, ctx, ["whoami"]).item["user"], "ana")
        result = self.run_command(self.stub, ctx, ["things", "--limit", "1"])
        self.assertEqual((len(result.items), result.truncated), (1, False))
        code, out, err = self.run_cli(self.stub, ["things", "--json"],
                                      values={"url": srv.url, "token": SECRET})
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["items"][0]["name"], "a")


# --- 0.10.0: token as user, token exchange, the POST gate ------------------------------------

BD_API = "bd-API-token-9876"
BD_BEARER = "BEARER-1-very-secret"
BD_USER = "application/vnd.blackducksoftware.user-4+json"
TOKEN_PATH = "/api/tokens/authenticate"


def _bd_routes(expires_ms=7199000, bearer=BD_BEARER):
    return {TOKEN_PATH: {"bearerToken": bearer, "expiresInMilliseconds": expires_ms},
            "/api/current-user": {}}


class TestTokenAsUser(Base):
    def test_header_is_basic_token_colon_empty(self):
        srv = self.server({"/api/me": ME})
        http.Client(srv.url, http.token_as_user(SECRET)).get_json("/api/me")
        want = base64.b64encode(f"{SECRET}:".encode()).decode()
        self.assertEqual(srv.requests[0].headers["Authorization"], f"Basic {want}")
        self.assertEqual(http.token_as_user(SECRET).secrets(), [SECRET, want])

    def test_the_token_is_scrubbed(self):
        srv = self.server({"/api/me": Reply(400, {"message": f"bad token {SECRET}"})})
        err = io.StringIO()
        c = http.Client(srv.url, http.token_as_user(SECRET), debug=True, stderr=err)
        with self.assertRaises(http.ConnectorError) as cm:
            c.get_json("/api/me")
        self.assertIn("<redacted>", str(cm.exception))
        self.assertNotIn(SECRET, str(cm.exception))
        self.assertNotIn(SECRET, err.getvalue())
        self.assertNotIn(base64.b64encode(f"{SECRET}:".encode()).decode(), err.getvalue())


class TestErrorBody(Base):
    def test_blackduck_error_message_field_is_shown_and_scrubbed(self):
        # Black Duck puts its reason in `errorMessage` (with `errorCode`).
        srv = self.server({"/api/x": Reply(404, {"errorMessage": f"No version {SECRET}",
                                                 "errorCode": "{central.constraint_violation}"})})
        with self.assertRaises(http.ConnectorError) as cm:
            http.Client(srv.url, http.bearer(SECRET)).get_json("/api/x")
        self.assertIn("server says: No version <redacted>", str(cm.exception))
        self.assertNotIn(SECRET, str(cm.exception))


class TestTokenExchange(Base):
    def test_blackduck_exchange_once_then_bearer(self):
        srv = self.server(_bd_routes())
        c = http.Client(srv.url, http.blackduck_token(BD_API))
        c.get_json("/api/current-user")
        c.get_json("/api/current-user")
        posts = [r for r in srv.requests if r.method == "POST"]
        gets = [r for r in srv.requests if r.method == "GET"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].path, TOKEN_PATH)
        self.assertEqual(posts[0].headers["Authorization"], f"token {BD_API}")
        self.assertEqual(posts[0].headers["Accept"], BD_USER)
        self.assertEqual(posts[0].body, b"")
        self.assertEqual([g.headers["Authorization"] for g in gets],
                         [f"Bearer {BD_BEARER}"] * 2)

    def test_refreshes_when_expired(self):
        srv = self.server(_bd_routes(expires_ms=1000))
        now = [1000.0]
        clock = mock.Mock()
        clock.time = lambda: now[0]
        clock.sleep = lambda s: None
        with mock.patch.object(http, "time", clock):
            c = http.Client(srv.url, http.blackduck_token(BD_API))
            c.get_json("/api/current-user")
            c.get_json("/api/current-user")
            self.assertEqual(sum(r.method == "POST" for r in srv.requests), 1)
            now[0] += 31  # past the 30 s floor of a short-lived token
            c.get_json("/api/current-user")
        self.assertEqual(sum(r.method == "POST" for r in srv.requests), 2)

    def test_401_on_exchange_says_api_token_not_accepted(self):
        srv = self.server({TOKEN_PATH: Reply(401, {"errorMessage": f"bad {BD_API}"})})
        c = http.Client(srv.url, http.blackduck_token(BD_API))
        with self.assertRaises(http.ConnectorError) as cm:
            c.get_json("/api/current-user")
        self.assertIn("API token was not accepted", str(cm.exception))
        self.assertEqual(cm.exception.kind, "unauthorized")
        self.assertNotIn(BD_API, str(cm.exception))

    def test_no_bearer_in_answer_is_bad_response(self):
        srv = self.server({TOKEN_PATH: {"expiresInMilliseconds": 1000}})
        c = http.Client(srv.url, http.blackduck_token(BD_API))
        with self.assertRaises(http.ConnectorError) as cm:
            c.get_json("/api/current-user")
        self.assertEqual(cm.exception.kind, "bad_response")
        self.assertFalse(any(r.method == "GET" for r in srv.requests))

    def test_bearer_token_never_printed(self):
        srv = self.server({**_bd_routes(),
                           "/api/fail": Reply(400, {"errorMessage": f"echo {BD_BEARER}"})})
        os.environ["AI_SDLC_DEBUG"] = "1"
        err = io.StringIO()
        c = http.Client(srv.url, http.blackduck_token(BD_API), stderr=err)
        c.get_json("/api/current-user")
        with self.assertRaises(http.ConnectorError) as cm:
            c.get_json("/api/fail")
        self.assertIn("> Authorization: <redacted>", err.getvalue())
        for secret in (BD_API, BD_BEARER):
            self.assertNotIn(secret, err.getvalue())
            self.assertNotIn(secret, str(cm.exception))

    def test_jama_oauth_is_a_token_exchange(self):
        self.assertIsInstance(http.oauth_client_credentials("i", "s"), http.TokenExchange)
        self.assertIsInstance(http.blackduck_token("t"), http.TokenExchange)
        self.assertIs(http.token_exchange, http.TokenExchange)
        self.assertEqual(http.blackduck_token("t").token_path, TOKEN_PATH)


def _posting_command(ctx, args):
    ctx.client._send("POST", ctx.client.url("/x"), {}, b"", None)
    return registry.Result(item={"user": "", "display_name": "", "url": ""})


class TestPostGate(Base):
    def assert_refused(self, fn, srv):
        with self.assertRaises(http.ConnectorError) as cm:
            fn()
        self.assertEqual(cm.exception.kind, "config")
        self.assertIn("read-only", str(cm.exception))
        self.assertEqual(srv.requests, [])

    def test_a_command_cannot_post(self):
        srv = self.server({**_bd_routes(), "/x": {}})
        self.connectors[NAME].commands["post"] = registry.Command("post", run=_posting_command)
        for auth in (http.bearer(SECRET), http.blackduck_token(BD_API)):
            ctx = registry.Context(NAME, http.Client(srv.url, auth), {}, "")
            self.assert_refused(lambda: self.connectors[NAME].commands["post"].run(ctx, None),
                                srv)

    def test_exchange_only_by_the_clients_own_auth(self):
        srv = self.server(_bd_routes())
        c = http.Client(srv.url, http.blackduck_token(BD_API))
        self.assert_refused(lambda: c._exchange(http.blackduck_token("other-token")), srv)
        g = http.Client(srv.url, http.bearer(SECRET))
        self.assert_refused(lambda: g._exchange(g.auth), srv)

    def test_exchange_only_to_its_token_path(self):
        srv = self.server({**_bd_routes(), "/other": {}})
        c = http.Client(srv.url, http.blackduck_token(BD_API))
        self.assert_refused(lambda: c._send("POST", c.url("/other"), {}, b"", None,
                                            _exchange=c.auth), srv)
        self.assert_refused(lambda: c._send("POST", c.url(TOKEN_PATH), {}, b"", None), srv)

    def test_put_patch_delete_refused(self):
        srv = self.server(_bd_routes())
        c = http.Client(srv.url, http.blackduck_token(BD_API))
        for method in ("PUT", "PATCH", "DELETE", "HEAD"):
            self.assert_refused(lambda: c._send(method, c.url(TOKEN_PATH), {}, b"", None,
                                                _exchange=c.auth), srv)

    def test_connector_modules_never_post(self):
        files = [registry.HERE / f"{n}.py" for n in registry.names()] + [STUB_FILE]
        self.assertGreaterEqual(len(files), 6)
        for path in files:
            with self.subTest(module=path.name):
                self.assertEqual(scan_for_writes(path.read_text(encoding="utf-8")), [])

    def test_the_scan_finds_what_it_must(self):
        bad = ("import urllib.request\nfrom urllib import error\nimport http.client\n"
               "from http import client\nimport urllib.parse\nx.client._send('GET')\n"
               "c._exchange(a)\nm = 'POST'\nurllib.request.urlopen(u)\n")
        found = scan_for_writes(bad)
        for want in ("urllib.request", "urllib.error", "http.client", "_send", "_exchange",
                     "'POST'"):
            self.assertTrue(any(want in f for f in found), (want, found))
        self.assertEqual(scan_for_writes("import urllib.parse\nurllib.parse.quote('a')\n"
                                         "from . import http\n"), [])


FORBIDDEN_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def scan_for_writes(source) -> list:
    """What in a connector module's source could send a write. `urllib.parse` (quoting)
    is allowed; any other urllib part, http.client, `_send`, `_exchange` and a method
    name as a string are not."""
    import ast
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for a in node.names:
                if (a.name == "urllib" or a.name.startswith("urllib.")) \
                        and a.name != "urllib.parse":
                    found.append(f"import {a.name}")
                if a.name == "http" or a.name.startswith("http."):
                    found.append(f"import {a.name}")
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mod = node.module
            if mod == "urllib":
                found += [f"from urllib import {a.name} (urllib.{a.name})"
                          for a in node.names if a.name != "parse"]
            elif mod.startswith("urllib.") and mod != "urllib.parse":
                found.append(f"from {mod}")
            elif mod == "http" or mod.startswith("http."):
                found.append(f"from {mod} (http.client)" if mod == "http" else f"from {mod}")
        elif isinstance(node, ast.Attribute):
            if node.attr in ("_send", "_exchange"):
                found.append(f".{node.attr}")
            if isinstance(node.value, ast.Name) and node.value.id == "urllib" \
                    and node.attr != "parse":
                found.append(f"urllib.{node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and node.value.upper() in FORBIDDEN_METHODS:
            found.append(repr(node.value))
    return found


class TestText(unittest.TestCase):
    def test_html_to_text(self):
        html = "<h1>Title</h1><p>One &amp; <b>two</b></p><script>x()</script><ul><li>a</li></ul>"
        self.assertEqual(text.html_to_text(html), "Title\nOne & two\na")
        self.assertEqual(text.html_to_text(html, max_chars=5), "Title")
        self.assertEqual(text.html_to_text(None), "")

    def test_adf_to_text(self):
        adf = {"type": "doc", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Hello"}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "world"}]}]}
        self.assertEqual(text.adf_to_text(adf), "Hello\nworld")

    def test_iso_from_ms_and_clip(self):
        self.assertEqual(text.iso_from_ms(1791451800000), "2026-10-08T09:30:00Z")
        self.assertIsNone(text.iso_from_ms(None))
        self.assertEqual(text.clip("abcdef", 4), "abc…")


if __name__ == "__main__":
    unittest.main()
