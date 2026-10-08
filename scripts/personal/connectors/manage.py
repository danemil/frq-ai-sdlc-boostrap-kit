"""The person's side: setup.py connect | connections | disconnect.

Each function returns (exit code, lines to print). `connect` asks its questions
itself (secrets through getpass), so the AI never sees a secret: it refuses to run
when stdin is not a terminal, unless every value is already in the environment.
"""
from __future__ import annotations

import getpass
import sys

from . import http, registry, store

SETUP = "python3 .ai-sdlc/kit/setup.py"
KIND_LABEL = {"cloud": "Cloud", "dc": "Data Center"}
MAX_TRIES = 3


class Refused(Exception):
    """A plain reason connect stopped; nothing was saved."""


def _get(name, connectors):
    connectors = registry.discover() if connectors is None else connectors
    if name not in connectors:
        known = ", ".join(connectors) or "none yet"
        raise Refused(f"There is no connector {name!r}. Available: {known}.")
    return connectors[name]


def _scrub(text, values, connector) -> str:
    text = str(text)
    for f in connector.fields:
        secret = values.get(f.key)
        if f.secret and secret and len(secret) >= 4:
            text = text.replace(secret, http.REDACTED)
    return text


def _kind_label(connector, values) -> str:
    try:
        return KIND_LABEL.get(connector.kind(values), connector.kind(values) or "")
    except Exception:  # noqa: BLE001  a label must never stop a listing
        return ""


def test(connector, values, **client_kwargs) -> tuple[bool, str, str | None]:
    """One read-only identity call: (ok, plain message, user or None). Never raises."""
    try:
        ctx = registry.open_context(connector, values, **client_kwargs)
        item = connector.whoami.run(ctx, None).item or {}
        user = item.get("user") or ""
        who = item.get("display_name") or user or "an unnamed account"
        return True, f"OK: signed in to {ctx.client.host} as {who}.", user or None
    except http.ConnectorError as exc:
        return False, _scrub(exc, values, connector), None
    except Exception as exc:  # noqa: BLE001  report, never leak a traceback with values
        return False, _scrub(f"unexpected error ({type(exc).__name__}): {exc}", values,
                             connector), None


def _validate(connector, values):
    try:
        http.Client(values.get("url", ""), None)
    except http.ConnectorError as exc:
        raise Refused(str(exc)) from None
    reason = connector.check(values)
    if reason:
        raise Refused(reason)


def _ask_all(connector, current, ask, ask_secret, say):
    values = {}
    for f in connector.fields:
        if f.when is not None and not f.when({**current, **values}):
            continue
        have = current.get(f.key)
        if f.help:
            say(f.help)
        for _ in range(MAX_TRIES):
            if f.secret:
                answer = ask_secret(f"{f.prompt}" + (" (Enter keeps the saved one)" if have
                                                     else "") + ": ")
            else:
                answer = ask(f"{f.prompt}" + (f" [{have}]" if have else "") + ": ")
            answer = (answer or "").strip()
            if answer:
                values[f.key] = answer
                break
            if have:
                values[f.key] = have
                break
            if not f.required:
                break
            say(f"{f.prompt} is needed.")
        else:
            raise Refused(f"Stopped: no {f.prompt.lower()} given. Nothing was saved.")
    return values


def connect(name, *, test_only=False, connectors=None, isatty=None, ask=input,
            ask_secret=getpass.getpass, say=print, client_kwargs=None):
    """setup.py connect <name> [--test]."""
    client_kwargs = client_kwargs or {}
    try:
        connector = _get(name, connectors)
    except Refused as exc:
        return 2, [str(exc)]
    title = connector.title

    if test_only:
        values = registry.load_values(connector)
        if not values:
            return 1, [f"{title} is not connected. Run, in your own terminal: "
                       f"{SETUP} connect {name}"]
        ok, message, user = test(connector, values, **client_kwargs)
        store.record_test(name, ok, message, user)
        return (0 if ok else 1), [f"{title}: {message}"]

    tty = sys.stdin.isatty() if isatty is None else isatty
    env = store.env_values(name, connector.keys)
    try:
        if not tty:
            missing = [f for f in connector.missing(env)]
            if missing:
                env_names = ", ".join(store.env_name(name, f.key) for f in missing)
                return 2, [f"connect asks for secrets, so it runs only in your own terminal, "
                           f"never through an assistant. Open a terminal and run: "
                           f"{SETUP} connect {name}",
                           f"(For scripts: set every value in the environment first; "
                           f"missing: {env_names}.)"]
            values = {k: v for k, v in env.items()}
        else:
            current = {**((store.read_file(name) or {}).get("values") or {}), **env}
            say(f"Connect {title}. Secrets are typed hidden and saved only on this "
                f"computer, in {store.file_for(name)}.")
            values = _ask_all(connector, current, ask, ask_secret, say)
        _validate(connector, values)
    except Refused as exc:
        return 2, [_scrub(exc, {**env}, connector)]

    path = store.save(name, values)
    ok, message, user = test(connector, values, **client_kwargs)
    store.record_test(name, ok, message, user)
    kind = _kind_label(connector, values)
    lines = [f"Saved {title}{f' ({kind})' if kind else ''} at {values.get('url')} in {path}.",
             f"Test: {message}"]
    if not ok:
        lines.append(f"The settings are saved; fix the problem and run {SETUP} connect {name} "
                     f"again, or check with {SETUP} connect {name} --test")
    return (0 if ok else 1), lines


def connections(connectors=None):
    """setup.py connections: what is configured, never a secret."""
    connectors = registry.discover() if connectors is None else connectors
    lines = []
    for name, c in connectors.items():
        src = store.source(name, c.keys)
        if src is None:
            lines.append(f"- {name}: not connected ({SETUP} connect {name})")
            continue
        values = registry.load_values(c) or {}
        doc = store.read_file(name) or {}
        last = doc.get("last_test") or {}
        user = c.identity(values) or last.get("user") or "?"
        kind = _kind_label(c, values)
        parts = [values.get("url", "?")] + ([kind] if kind else []) + [f"user {user}"]
        if last:
            parts.append(f"last test {'OK' if last.get('ok') else 'FAILED'} {last.get('at', '')}")
        else:
            parts.append("not tested yet")
        parts.append(f"from {src}")
        lines.append(f"- {name}: " + " · ".join(parts))
        if store.loose_permissions(name):
            lines.append(f"  Warning: {store.file_for(name)} can be read by other users; run "
                         f"chmod 600 on it, or connect again.")
    unknown = [n for n in store.saved() if n not in connectors]
    for n in unknown:
        lines.append(f"- {n}: saved, but this kit has no {n} connector")
    head = f"Connectors (saved in {store.connectors_dir()}):"
    return 0, [head] + (lines or ["- none available in this kit yet"])


def disconnect(name, connectors=None):
    """setup.py disconnect <name>: delete the saved file."""
    connectors = registry.discover() if connectors is None else connectors
    title = connectors[name].title if name in connectors else name
    try:
        removed = store.delete(name)
    except ValueError:
        return 2, [f"There is no connector {name!r}."]
    lines = [f"Removed the saved {title} connection." if removed else
             f"There was no saved {title} connection."]
    keys = connectors[name].keys if name in connectors else []
    if store.env_values(name, keys):
        lines.append(f"Values in AI_SDLC_{name.upper()}_* environment variables still apply; "
                     "unset them to disconnect fully.")
    return 0, lines
