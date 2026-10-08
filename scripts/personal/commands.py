"""The six commands behind setup.py. Each returns (exit code, lines to print).

The lines are short and plain: Copilot relays them to the person as they are.
"""
from __future__ import annotations


class SetupError(Exception):
    """A plain-language reason to stop. Raised before anything else is changed."""


def not_built(args, cwd, kit):
    return 3, [f"setup.py {args.command}: not built yet"]


HANDLERS = {}


def run(args, cwd, kit):
    return HANDLERS.get(args.command, not_built)(args, cwd, kit)
