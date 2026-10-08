"""Where things are: the kit, the repo, and what git says about a path.

Git is only ever asked questions here (rev-parse, ls-files, check-ignore).
Nothing in this package runs a git command that changes the repo.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
HOME_REL = ".ai-sdlc"
KIT_REL = ".ai-sdlc/kit"
USER_REL = ".ai-sdlc/USER.md"
STATE_REL = ".ai-sdlc/state.json"
# The person's own files, named like the kit's so git hides them, but never written,
# replaced or deleted by the kit (the deceneus skill writes them, with approval).
PERSONAL_NOTES_REL = ".github/instructions/ai-sdlc-personal.instructions.md"
PERSONAL_SKILLS_REL = ".agents/skills/ai-sdlc-personal-"


def is_personal(rel: str) -> bool:
    """Is `rel` the person's own notes file, or inside one of their personal skills?"""
    return rel == PERSONAL_NOTES_REL or (rel.startswith(PERSONAL_SKILLS_REL) and "/" in
                                         rel[len(PERSONAL_SKILLS_REL):])


def git(root, *args):
    """Run a read-only git command in `root`. None when git cannot run at all."""
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True,
                              text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None


def repo_root(start) -> tuple[Path, bool]:
    """(root, is_git). Outside a git repo the folder itself is the root."""
    start = Path(start).resolve()
    r = git(start, "rev-parse", "--show-toplevel")
    if r is not None and r.returncode == 0 and r.stdout.strip():
        return Path(r.stdout.strip()).resolve(), True
    return start, False


def kit_version(kit) -> str:
    text = read_text(Path(kit) / "VERSION")
    return text.strip() if text else "0.0.0"


def tracked(root, rels) -> set[str]:
    """The paths in `rels` that git tracks. The kit never writes to those."""
    rels = sorted(rels)
    if not rels:
        return set()
    r = git(root, "ls-files", "-z", "--", *rels)
    if r is None or r.returncode != 0:
        return set()
    return {p for p in r.stdout.split("\0") if p}


def ignored(root, rels) -> set[str]:
    """The paths in `rels` that git ignores (our exclude block, or the team's rules)."""
    rels = sorted(rels)
    if not rels:
        return set()
    r = git(root, "check-ignore", "--", *rels)
    if r is None or r.returncode not in (0, 1):
        return set()
    return {line for line in r.stdout.splitlines() if line}


def read_text(path) -> str | None:
    """The file's text, byte-faithful (undecodable bytes survive a write back)."""
    p = Path(path)
    if not p.is_file():
        return None
    return p.read_bytes().decode("utf-8", "surrogateescape")


def write_atomic(path, data) -> None:
    """Write through a temp file in the same folder, then rename: never half a file.

    The temp name starts with the target's name, so it matches the same exclude
    pattern if a crash leaves it behind.
    """
    path = Path(path)
    if isinstance(data, str):
        data = data.encode("utf-8", "surrogateescape")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
