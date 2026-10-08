#!/usr/bin/env python3
"""AI-SDLC connectors: read-only data from Jira, Confluence, Bitbucket, Jama and Jenkins.

  python3 .ai-sdlc/kit/connectors.py                          # what is available
  python3 .ai-sdlc/kit/connectors.py <connector> whoami
  python3 .ai-sdlc/kit/connectors.py <connector> <command> [args] [--json]

Plain text by default; --json gives {"connector", "command", "source", "item" or
"items"/"count"/"truncated"}. Every item carries the "url" it came from.
Credentials are set by the person, in their own terminal, with
  python3 .ai-sdlc/kit/setup.py connect <connector>
This script never asks for, prints or stores a secret. Stdlib only; Python 3.9+.
"""
import sys

if sys.version_info < (3, 9):
    sys.exit("AI-SDLC needs Python 3.9 or newer. Please ask your IT support to install it.")
sys.dont_write_bytecode = True

import argparse  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT / "scripts"))

from personal.connectors import http, registry  # noqa: E402

SETUP = "python3 .ai-sdlc/kit/setup.py"
EXIT_ERROR, EXIT_USAGE, EXIT_NOT_CONNECTED = 1, 2, 3


def parser(connectors) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="connectors.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="connector", metavar="connector")
    for name, c in connectors.items():
        cp = sub.add_parser(name, help=f"{c.title} (read-only)")
        csub = cp.add_subparsers(dest="command", metavar="command", required=True)
        for cmd_name, cmd in {"whoami": c.whoami, **c.commands}.items():
            p = csub.add_parser(cmd_name, help=cmd.help, description=cmd.help)
            if cmd.args:
                cmd.args(p)
            p.add_argument("--json", action="store_true", help="structured output")
    return ap


def _scalar(v) -> bool:
    return v is None or isinstance(v, (str, int, float, bool))


def render_text(result) -> list[str]:
    """A generic plain-text form, used when a command gives no `lines`."""
    if result.lines is not None:
        return list(result.lines)
    out = []
    if result.item is not None:
        for k, v in result.item.items():
            if _scalar(v):
                out.append(f"{k}: {'' if v is None else v}")
            else:
                out.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
    if result.items is not None:
        for it in result.items:
            label = next((str(it[k]) for k in ("key", "title", "name", "summary", "id")
                          if isinstance(it, dict) and it.get(k) not in (None, "")), "?")
            url = it.get("url", "") if isinstance(it, dict) else ""
            out.append(f"- {label}" + (f"  {url}" if url else ""))
        out.append(f"({len(result.items)} shown" + (", more exist: raise --limit)"
                                                    if result.truncated else ")"))
    return out


def envelope(name, command, ctx, result) -> dict:
    doc = {"connector": name, "command": command, "source": ctx.client.base_url}
    if result.item is not None:
        doc["item"] = result.item
    if result.items is not None:
        doc.update(items=result.items, count=len(result.items), truncated=result.truncated)
    doc.update(result.extra)
    return doc


def main(argv=None, connectors=None, out=None, err=None, client_kwargs=None) -> int:
    out, err = out or sys.stdout, err or sys.stderr
    connectors = registry.discover() if connectors is None else connectors
    ap = parser(connectors)
    args = ap.parse_args(argv)
    if not args.connector:
        print("Connectors (read-only):", file=out)
        for name, c in connectors.items():
            cmds = ", ".join(["whoami", *c.commands])
            print(f"- {name} ({c.title}): {cmds}", file=out)
        if not connectors:
            print("- none available in this kit yet", file=out)
        print(f"Set one up, in your own terminal: {SETUP} connect <connector>", file=out)
        return 0
    c = connectors[args.connector]
    cmd = c.whoami if args.command == "whoami" else c.commands[args.command]
    values = registry.load_values(c)
    if not values or c.missing(values):
        print(f"{c.title} is not connected. Ask the person to run, in their own terminal "
              f"(never through the assistant): {SETUP} connect {args.connector}", file=err)
        return EXIT_NOT_CONNECTED
    secrets = [values[f.key] for f in c.fields if f.secret and values.get(f.key)]

    def scrub(text):
        text = str(text)
        for s in secrets:
            if len(s) >= 4:
                text = text.replace(s, http.REDACTED)
        return text

    try:
        ctx = registry.open_context(c, values, **(client_kwargs or {}))
        result = cmd.run(ctx, args)
    except http.ConnectorError as exc:
        print(f"{c.title}: {scrub(exc)}", file=err)
        if exc.kind == "unauthorized":
            print(f"Ask the person to run, in their own terminal: {SETUP} connect "
                  f"{args.connector}", file=err)
        return EXIT_ERROR
    except Exception as exc:  # noqa: BLE001  never a traceback that could carry values
        print(f"{c.title}: unexpected error ({type(exc).__name__}): {scrub(exc)}", file=err)
        return EXIT_ERROR
    if args.json:
        print(json.dumps(envelope(args.connector, args.command, ctx, result),
                         ensure_ascii=False, indent=2), file=out)
    else:
        print("\n".join(render_text(result)), file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
