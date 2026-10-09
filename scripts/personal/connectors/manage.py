"""The person's side: setup.py connect [--suggested] | connections | disconnect.

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


def is_connected(connector) -> bool:
    """Every needed value is saved (file or environment). Never raises."""
    try:
        values = registry.load_values(connector)
        return bool(values) and not connector.missing(values)
    except Exception:  # noqa: BLE001  an unreadable file counts as not connected
        return False


def _choice(ask, say, prompt):
    """y, s or a (Enter = s), or None when there are no more answers (EOF, Ctrl-C)."""
    for _ in range(MAX_TRIES):
        try:
            answer = (ask(prompt) or "").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None
        if answer in ("", "s", "skip", "n", "no"):
            return "s"
        if answer in ("y", "yes"):
            return "y"
        if answer in ("a", "all"):
            return "a"
        say("Please answer y, s or a.")
    return "s"


def suggest(defaults, *, connectors=None, isatty=None, ask=input, ask_secret=getpass.getpass,
            say=print, client_kwargs=None):
    """setup.py connect --suggested: offer the role connectors (`defaults`) one at a time,
    then any other tool by name. `y` runs connect() exactly as `connect <name>` does.

    Returns (exit code, closing lines, {"connected": [...], "skipped": [...]}). Only the
    role connectors the person skipped (s, Enter, or a) are in "skipped"; the caller
    remembers them. Without a terminal it asks nothing and changes nothing."""
    connectors = registry.discover() if connectors is None else connectors
    result = {"connected": [], "skipped": []}
    tty = sys.stdin.isatty() if isatty is None else isatty
    if not tty:
        return 0, ["connect --suggested asks questions (and secrets), so it runs only in your "
                   "own terminal, never through an assistant. Nothing was connected or skipped. "
                   f"Open a terminal in this repo and run: {SETUP} connect --suggested"], result

    def run_connect(name):
        """True when there are no more answers (stop the walk)."""
        try:
            code, lines = connect(name, connectors=connectors, isatty=True, ask=ask,
                                  ask_secret=ask_secret, say=say, client_kwargs=client_kwargs)
        except (EOFError, KeyboardInterrupt):
            say(f"Stopped connecting {connectors[name].title}. Nothing more was saved.")
            return True
        for line in lines:
            say(line)
        if code in (0, 1):                     # saved (1: saved, but its test failed)
            result["connected"].append(name)
        return False

    todo = [n for n in dict.fromkeys(defaults) if n in connectors]
    stopped = False
    if todo:
        say("Connect the tools your roles usually use, one at a time. Logins are typed here, "
            "secrets hidden, and saved only on this computer.")
    for i, name in enumerate(todo):
        title = connectors[name].title
        if is_connected(connectors[name]):
            say(f"- {title}: already connected.")
            continue
        answer = _choice(ask, say, f"Connect {title} now? [y = yes, s = skip, a = skip all "
                                   f"the rest; Enter = skip]: ")
        if answer is None:
            say("No more answers; skipping the rest for now.")
            stopped = True
            break
        if answer == "a":
            result["skipped"] += [n for n in todo[i:] if not is_connected(connectors[n])]
            stopped = True
            break
        if answer == "s":
            result["skipped"].append(name)
            continue
        if run_connect(name):
            stopped = True
            break

    tries = 0
    while not stopped and tries < MAX_TRIES:
        others = [n for n in connectors if n not in todo and not is_connected(connectors[n])]
        if not others:
            break
        try:
            answer = (ask(f"Connect another tool? Available: {', '.join(others)} "
                          f"(type its name; Enter = done): ") or "").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if not answer:
            break
        if answer not in connectors or is_connected(connectors[answer]):
            tries += 1
            say(f"There is no tool {answer!r} to connect here." if answer not in connectors
                else f"{connectors[answer].title} is already connected.")
            continue
        tries = 0
        if run_connect(answer):
            break

    lines = []
    if result["connected"]:
        lines.append(f"Connected: {', '.join(result['connected'])}.")
    if result["skipped"]:
        lines.append(f"Skipped: {', '.join(result['skipped'])}. They are no longer suggested; "
                     f"connect one any time with {SETUP} connect <name>")
    if not lines:
        lines.append("Nothing was connected.")
    return 0, lines, result


def connections(connectors=None, skipped=()):
    """setup.py connections: what is configured, never a secret. `skipped`: the connectors
    the person chose to skip in connect --suggested, shown as such."""
    connectors = registry.discover() if connectors is None else connectors
    lines = []
    for name, c in connectors.items():
        src = store.source(name, c.keys)
        if src is None:
            lines.append(f"- {name}: not connected, skipped ({SETUP} connect {name} when you "
                         f"want it)" if name in skipped else
                         f"- {name}: not connected ({SETUP} connect {name})")
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


def disconnect(name, connectors=None, yes=False):
    """setup.py disconnect <name> [--yes]: delete the saved file. Without yes, say what would
    be deleted and ask; nothing changes."""
    connectors = registry.discover() if connectors is None else connectors
    title = connectors[name].title if name in connectors else name
    try:
        path = store.file_for(name)
    except ValueError:
        return 2, [f"There is no connector {name!r}."]
    if not yes and path.exists():
        return 2, [f"Nothing was deleted yet. disconnect deletes your saved {title} login on "
                   f"this computer ({path}); every repo on this computer uses it.",
                   f"Delete your saved {title} login? Only after a yes: "
                   f"{SETUP} disconnect {name} --yes"]
    removed = store.delete(name)
    lines = [f"Removed the saved {title} connection." if removed else
             f"There was no saved {title} connection."]
    keys = connectors[name].keys if name in connectors else []
    if store.env_values(name, keys):
        lines.append(f"Values in AI_SDLC_{name.upper()}_* environment variables still apply; "
                     "unset them to disconnect fully.")
    return 0, lines
