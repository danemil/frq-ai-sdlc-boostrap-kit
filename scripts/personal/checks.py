"""`check`: is the personal setup whole, hidden, current, and alone?

Each finding is (id, text). Ids are stable, so ONBOARDING.md can map them to fixes:
    missing:<path>     a file the kit placed is gone
    unknown:<path>     an ai-sdlc* file the kit did not write (Copilot may have made it)
    unexcluded:<path>  an ai-sdlc* file git does not hide
    stale-kit          the kit folder and state.json disagree on the version
    kit-copy:<dir>     another kit folder in the repo that git does not hide
"""
from __future__ import annotations

from pathlib import Path

from . import paths, place, reuse, state

SCAN = (".github/instructions", ".github/skills", ".agents/skills", ".claude/skills")


def ai_sdlc_files(root) -> list[str]:
    """Every file named ai-sdlc* (or inside an ai-sdlc* folder) where Copilot looks."""
    root = Path(root)
    out = []
    for d in SCAN:
        for p in sorted((root / d).glob("ai-sdlc*")) if (root / d).is_dir() else []:
            files = [p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file())
            out += [q.relative_to(root).as_posix() for q in files]
    return out


def version_key(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def _dirs(top: Path, depth: int):
    yield top
    if depth:
        for child in sorted(p for p in top.iterdir() if p.is_dir()):
            yield from _dirs(child, depth - 1)


def kit_copies(root) -> list[str]:
    """Kit folders (up to two levels inside an untracked folder) that git does not hide."""
    r = paths.git(root, "ls-files", "--others", "--exclude-standard", "--directory", "-z")
    if r is None or r.returncode != 0:
        return []
    found = []
    for entry in r.stdout.split("\0"):
        if entry.endswith("/"):
            found += [d.relative_to(root).as_posix() for d in _dirs(Path(root) / entry, 2)
                      if place.is_kit(d)]
    return found


def run(root) -> tuple[dict | None, list[tuple[str, str]]]:
    root = Path(root)
    st = state.load(root)
    if st is None:
        return None, [("not-set-up", 'The kit is not set up in this repo. Say "do the onboarding".')]
    found = []
    for rel in sorted(st["files"]):
        if reuse.file_state(root, st, rel) == reuse.MISSING:
            found.append((f"missing:{rel}", f"{rel} is missing."))
    present = ai_sdlc_files(root)
    for rel in present:
        if rel not in st["files"] and not rel.endswith(".tmp"):
            found.append((f"unknown:{rel}", f"{rel} looks like a kit file, but the kit did not write it."))
    if paths.repo_root(root)[1]:
        on_disk = sorted(set(present) | {r for r in st["files"] if (root / r).is_file()})
        hidden, tracked = paths.ignored(root, on_disk), paths.tracked(root, on_disk)
        for rel in on_disk:
            if rel not in hidden and rel not in tracked:
                found.append((f"unexcluded:{rel}", f"{rel} is not hidden from git."))
        for d in kit_copies(root):
            if d == paths.KIT_REL:
                found.append((f"unexcluded:{d}", f"The kit folder {d} is not hidden from git."))
                continue
            v = paths.kit_version(root / d)
            if version_key(v) > version_key(st["kit_version"]):
                text = f'A newer kit ({v}) is waiting in {d}. Say "update the kit".'
            else:
                text = f"{d} is a copy of the kit that git does not hide. Delete it."
            found.append((f"kit-copy:{d}", text))
    kv = paths.kit_version(root / paths.KIT_REL)
    if kv != st["kit_version"]:
        found.append(("stale-kit", f"The kit folder is {kv} but this setup is {st['kit_version']}. "
                                   'Say "update the kit".'))
    return st, found


def quiet_line(root, st, found) -> str:
    if st is None:
        return found[0][1]
    c = st["choices"]
    head = f"AI-SDLC {st['kit_version']} · roles: {', '.join(r.upper() for r in c['roles'])} · {c['lang']}"
    if not paths.repo_root(root)[1]:
        head += " · not a git repo"
    if not found:
        return head + " · ok"
    return head + f" · {len(found)} to look at: " + " ".join(text for _, text in found)
