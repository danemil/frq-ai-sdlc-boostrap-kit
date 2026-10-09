"""`check`: is the personal setup whole, hidden, current, and alone?

Each finding is (id, text). Ids are stable, so ONBOARDING.md can map them to fixes:
    missing:<path>     a file the kit placed is gone
    unknown:<path>     an ai-sdlc* file the kit did not write (Copilot may have made it);
                       the person's own notes and personal skills (paths.is_personal) are not
    unexcluded:<path>  an ai-sdlc* file git does not hide
    stale-kit          the kit folder and state.json disagree on the version
    kit-copy:<dir>     another kit folder in the repo that git does not hide (newer: it waits
                       for "update the kit"; same version: update from it or delete it;
                       older: delete it)
    and the team-file warnings from conflicts.py that are not acknowledged.

Notices and problems. A notice is for reading, nothing is broken: the team-… and
skill-clash:… warnings, and kit-copy:… (a kit folder waiting for "update the kit", or
one to delete). Everything else (missing, unknown, unexcluded, stale-kit, not-set-up)
is a problem to fix. `check` exits 0 when it found notices only, 1 for any problem.
"""
from __future__ import annotations

from pathlib import Path

from . import conflicts, paths, place, reuse, state

SCAN = (".github/instructions", ".github/hooks", ".github/skills", ".agents/skills", ".claude/skills")
NOTICES = ("team-", "skill-clash:", "kit-copy:")


def is_notice(fid: str) -> bool:
    """A finding to read, not a problem to fix (see the module docstring)."""
    return fid.startswith(NOTICES)


def is_bytecode(rel: str) -> bool:
    """Python leaves __pycache__/ and *.pyc behind when a skill's script runs: not a kit file."""
    return rel.endswith(".pyc") or "__pycache__" in rel.split("/")


def ai_sdlc_files(root) -> list[str]:
    """Every file named ai-sdlc* (or inside an ai-sdlc* folder) where Copilot looks,
    leaving out Python bytecode."""
    root = Path(root)
    out = []
    for d in SCAN:
        for p in sorted((root / d).glob("ai-sdlc*")) if (root / d).is_dir() else []:
            files = [p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file())
            out += [r for r in (q.relative_to(root).as_posix() for q in files) if not is_bytecode(r)]
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
        if rel not in st["files"] and not rel.endswith(".tmp") and not paths.is_personal(rel):
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
            elif version_key(v) == version_key(st["kit_version"]):
                text = (f"Another copy of the kit (same version {v}) is in {d}. "
                        'If you copied it in to update, say "update the kit"; otherwise delete it.')
            else:
                text = f"{d} is a copy of the kit that git does not hide. Delete it."
            found.append((f"kit-copy:{d}", text))
    kv = paths.kit_version(root / paths.KIT_REL)
    if kv != st["kit_version"]:
        found.append(("stale-kit", f"The kit folder is {kv} but this setup is {st['kit_version']}. "
                                   'Say "update the kit".'))
    return st, found + conflicts.active(root, st)


def hook_context(line: str, ok: bool) -> str:
    """What the session hook adds to the conversation."""
    text = ("AI-SDLC session check (run by the kit's session hook at the start of this session; "
            f"no need to run it again): {line}")
    if not ok:
        text += " In your first reply, mention what it found, in the person's language."
    return text


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
