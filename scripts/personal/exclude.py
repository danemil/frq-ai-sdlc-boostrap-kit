"""The kit's block in .git/info/exclude: it hides every personal-setup path from git.

Removing the block gives back the file byte for byte. The header line records the
one change add() made outside the block, if any: it created the file, or it added
a newline to an unterminated last line. strip() undoes exactly that.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import paths

BEGIN = "# >>> ai-sdlc personal setup (managed by .ai-sdlc/kit/setup.py) >>>"
END = "# <<< ai-sdlc personal setup <<<"
CREATED, NEWLINE = " [created]", " [newline]"
PATTERNS = (
    "/.ai-sdlc/",
    "/.github/instructions/ai-sdlc-*",
    "/.agents/skills/ai-sdlc-*/",
)
_BLOCK = re.compile(re.escape(BEGIN) + r"(?P<note>[^\n]*)\n.*?^" + re.escape(END) + r"\n?",
                    re.M | re.S)


def render(note: str = "", patterns=PATTERNS) -> str:
    return "\n".join([BEGIN + note, *patterns, END]) + "\n"


def add(text: str | None, patterns=PATTERNS) -> str:
    """The exclude file with our block in it. `text` is None when the file is absent."""
    if text is None:
        return render(CREATED, patterns)
    m = _BLOCK.search(text)
    if m:
        return text[:m.start()] + render(m.group("note"), patterns) + text[m.end():]
    if text and not text.endswith("\n"):
        return text + "\n" + render(NEWLINE, patterns)
    return text + render("", patterns)


def strip(text: str) -> str | None:
    """The file as it was before add(). None means add() created it: delete it."""
    m = _BLOCK.search(text)
    if not m:
        return text
    before, after = text[:m.start()], text[m.end():]
    if m.group("note") == NEWLINE and before.endswith("\n"):
        before = before[:-1]
    out = before + after
    return None if m.group("note") == CREATED and not out else out


def exclude_file(root) -> Path | None:
    """This repo's info/exclude (shared by every worktree). None outside git."""
    r = paths.git(root, "rev-parse", "--git-path", "info/exclude")
    if r is None or r.returncode != 0 or not r.stdout.strip():
        return None
    p = Path(r.stdout.strip())
    return p if p.is_absolute() else Path(root) / p


def protect(root) -> bool:
    """Add or refresh the block. False when `root` is not a git repo (nothing to hide from)."""
    path = exclude_file(root)
    if path is None:
        return False
    text = paths.read_text(path)
    new = add(text)
    if new != text:
        paths.write_atomic(path, new)
    return True


def unprotect(root) -> None:
    path = exclude_file(root)
    text = paths.read_text(path) if path else None
    if text is None:
        return
    out = strip(text)
    if out is None:
        path.unlink()
    elif out != text:
        paths.write_atomic(path, out)
