#!/usr/bin/env python3
"""AI-SDLC personal setup. Copilot runs this while following ONBOARDING.md.

  python3 <kit>/setup.py setup --protect-only
  python3 .ai-sdlc/kit/setup.py setup --name "Ana" --roles po,sm --lang de
  python3 .ai-sdlc/kit/setup.py change --lang en --add-skill skill-creator
  python3 <newer kit>/setup.py update
  python3 .ai-sdlc/kit/setup.py check [--quiet]
  python3 .ai-sdlc/kit/setup.py ack <warning-id> [<warning-id> ...]
  python3 .ai-sdlc/kit/setup.py remove
  python3 .ai-sdlc/kit/setup.py connect <connector> [--test]   (in your own terminal)
  python3 .ai-sdlc/kit/setup.py connections
  python3 .ai-sdlc/kit/setup.py disconnect <connector>

Run it from the repo root. Stdlib only; needs Python 3.9 or newer.
"""
import sys

if sys.version_info < (3, 9):
    sys.exit("AI-SDLC needs Python 3.9 or newer. Please ask your IT support to install it.")
sys.dont_write_bytecode = True  # keep the kit folder free of __pycache__

import argparse  # noqa: E402
from pathlib import Path  # noqa: E402

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT / "scripts"))

from personal import commands, packs  # noqa: E402


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="setup.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True, metavar="command")

    s = sub.add_parser("setup", help="hide and move the kit, then place your files")
    s.add_argument("--protect-only", action="store_true",
                   help="only hide the kit from git and move it to .ai-sdlc/kit")
    s.add_argument("--name")
    s.add_argument("--roles", help="comma-separated role ids, e.g. po,sm")
    s.add_argument("--lang", help="en, ro or de")

    c = sub.add_parser("change", help="change your choices; only affected files change")
    c.add_argument("--name")
    c.add_argument("--roles")
    c.add_argument("--lang")
    c.add_argument("--git-comfort", choices=[*packs.GIT_LEVELS, "default"])
    c.add_argument("--rituals", choices=[*packs.RITUALS, "default"])
    c.add_argument("--add-skill", action="append", default=[], metavar="SKILL")
    c.add_argument("--drop-skill", action="append", default=[], metavar="SKILL")

    sub.add_parser("update", help="run from a newer kit copy: refresh the kit and your files")
    k = sub.add_parser("check", help="files present and hidden, kit current, team overlaps")
    k.add_argument("--quiet", action="store_true", help="one line, for the start of a session")
    a = sub.add_parser("ack", help="note that you have seen a warning")
    a.add_argument("ids", nargs="+", metavar="warning-id")
    sub.add_parser("remove", help="take the kit out; the repo ends as it was")

    n = sub.add_parser("connect", help="save your login for a connector; run it in your own "
                                       "terminal, it asks for secrets hidden")
    n.add_argument("name", metavar="connector")
    n.add_argument("--test", action="store_true",
                   help="only check the saved login with one read-only call")
    sub.add_parser("connections", help="list connectors: URL, user, kind, last test (no secrets)")
    d = sub.add_parser("disconnect", help="delete a connector's saved login")
    d.add_argument("name", metavar="connector")
    return ap


def main(argv=None, cwd=None, kit=KIT) -> int:
    args = parser().parse_args(argv)
    try:
        code, lines = commands.run(args, cwd=Path(cwd or Path.cwd()), kit=Path(kit))
    except commands.SetupError as exc:
        code, lines = 2, [str(exc)]
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
