"""Put the kit's files in place, and take back the ones no longer wanted.

One reconcile serves setup, change, update and remove. For each file the person's
choices call for, manifest.state() compares what we last wrote (state.json), what
is on disk, and what the kit would write now:

    NEW, MISSING   write it
    IDENTICAL      record it (an interrupted run had already written it)
    CLEAN          replace it with the kit's newer copy
    MODIFIED       keep the person's edit; if the kit's copy changed, write it
                   next to it as <file>.kit-new
    FOREIGN        not ours: leave it alone and report it

A placed file that is no longer wanted is deleted while unedited, and kept (and
reported) once edited. A path git tracks is never written or deleted.

A placed skill's relative links that leave its folder are pointed at the same
file inside .ai-sdlc/kit/ (rewrite_links), so they still resolve after the move.
"""
from __future__ import annotations

import posixpath
import re
import shutil
from pathlib import Path

from . import packs, paths, reuse

KIT_CLASS = "kit"
SIDECAR = ".kit-new"
_LINK = re.compile(r"\]\(([^)\s]+)\)")              # ](target) of a Markdown link
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")  # http:, https:, mailto:, …


def rewrite_links(text, skill_dir, placed_dir, exists) -> tuple[str, list[str]]:
    """Point relative links that leave the skill's folder at the same file in .ai-sdlc/kit/.

    skill_dir is the skill's folder in the kit (template/.claude/skills/<skill>),
    placed_dir its folder in the repo (.agents/skills/ai-sdlc-<skill>), and
    exists(kit_rel) says whether a kit path exists. Links inside the skill's
    folder, URLs, root-absolute paths and #anchors are left alone. Returns the new
    text and the links whose target is not in the kit, which are left as they are.
    Pure and deterministic: the same input always renders the same bytes.
    """
    missing = []

    def fix(m):
        target = m.group(1)
        if _SCHEME.match(target) or target.startswith(("#", "/")):
            return m.group(0)
        path, hash_, anchor = target.partition("#")
        kit_rel = posixpath.normpath(posixpath.join(skill_dir, path))
        if kit_rel == skill_dir or kit_rel.startswith(skill_dir + "/"):
            return m.group(0)
        if kit_rel == ".." or kit_rel.startswith("../") or not exists(kit_rel):
            missing.append(target)
            return m.group(0)
        new = posixpath.relpath(posixpath.join(paths.KIT_REL, kit_rel), placed_dir)
        if path.endswith("/"):
            new += "/"
        return f"]({new}{hash_}{anchor})"

    return _LINK.sub(fix, text), missing


def user_md(all_packs, choices, combined) -> str:
    extra = ", ".join(choices["add_skills"]) or "none"
    fewer = ", ".join(choices["drop_skills"]) or "none"
    return (
        "# AI-SDLC: about me\n\n"
        f"- **Name:** {choices['name']}\n"
        f"- **Roles:** {', '.join(all_packs[r]['label'] for r in choices['roles'])}\n"
        f"- **Language:** {packs.LANGUAGES[choices['lang']]}\n"
        f"- **Git comfort:** {combined['git_comfort']}\n"
        f"- **Session summary:** {'on' if combined['rituals'] == 'status' else 'off'}\n"
        f"- **Extra skills:** {extra}\n"
        f"- **Skills left out:** {fewer}\n\n"
        "Written by the kit. To change it, say \"change my preferences\".\n"
    )


def placed_skill(kit, skill, missing=None) -> tuple[str, str]:
    """(repo path, text) of a library skill as setup places it: prefixed name, links into the kit.

    Links with no target in the kit are appended to `missing` when a list is given
    (validate_packs.py reports them); setup itself places the text either way.
    """
    src_dir = f"{packs.SKILLS_REL}/{skill}"
    dest_dir = f".agents/skills/{packs.PREFIX}{skill}"
    text = packs.prefixed_skill((Path(kit) / src_dir / "SKILL.md").read_text(encoding="utf-8"), skill)
    text, lost = rewrite_links(text, src_dir, dest_dir, lambda rel: (Path(kit) / rel).exists())
    if missing is not None:
        missing += lost
    return f"{dest_dir}/SKILL.md", text


def wanted_files(kit, all_packs, choices) -> dict[str, str]:
    """{repo path: text} of every file these choices call for."""
    combined = packs.combine(all_packs, choices)
    values = packs.core_values(all_packs, choices, combined)
    files = dict(packs.instructions_file(all_packs[pid], values)
                 for pid in [packs.CORE, *choices["roles"]])
    for skill in combined["skills"]:
        rel, text = placed_skill(kit, skill)
        files[rel] = text
    files[paths.USER_REL] = user_md(all_packs, choices, combined)
    return files


def _write(root, st, rel, data: bytes) -> None:
    for parent in reversed(list(Path(rel).parents)[:-1]):
        if not (root / parent).exists():
            st["created_dirs"].append(parent.as_posix())
    paths.write_atomic(root / rel, data)
    reuse.record(st, rel, KIT_CLASS, data)


def prune_dirs(root, st) -> None:
    """Remove folders setup created once they are empty again (deepest first)."""
    for d in sorted(st["created_dirs"], key=lambda p: p.count("/"), reverse=True):
        path = Path(root) / d
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
        if not path.exists():
            st["created_dirs"].remove(d)


def apply(root, st, wanted: dict[str, str]) -> dict[str, list[str]]:
    """Make the repo hold `wanted`; returns what was written, kept, skipped and removed."""
    root = Path(root)
    report = {"written": [], "kept": [], "skipped": [], "removed": []}
    tracked = paths.tracked(root, set(wanted) | set(st["files"]))
    keep = set(wanted)
    for rel, text in sorted(wanted.items()):
        data = text.encode("utf-8")
        if rel in tracked:
            report["skipped"].append(f"{rel} (the team's git tracks this path)")
            continue
        state = reuse.file_state(root, st, rel, data)
        if state in (reuse.NEW, reuse.MISSING, reuse.CLEAN):
            _write(root, st, rel, data)
            report["written"].append(rel)
        elif state == reuse.IDENTICAL:
            reuse.record(st, rel, KIT_CLASS, data)
        elif state == reuse.MODIFIED:
            report["kept"].append(rel)
            if reuse.sha256_bytes(data) != st["files"][rel]["sha256"]:
                keep.add(rel + SIDECAR)
                _write(root, st, rel + SIDECAR, data)
                report["written"].append(rel + SIDECAR)
        else:
            report["skipped"].append(f"{rel} (a file the kit did not write is already there)")
    for rel in sorted(set(st["files"]) - keep):
        if rel not in tracked and reuse.file_state(root, st, rel) == reuse.CLEAN:
            (root / rel).unlink()
            report["removed"].append(rel)
        elif reuse.file_state(root, st, rel) == reuse.MODIFIED:
            report["kept"].append(rel)
        reuse.forget(st, rel)
    prune_dirs(root, st)
    return report


def is_kit(path) -> bool:
    path = Path(path)
    return all((path / p).exists() for p in ("setup.py", "VERSION", packs.ROLES_REL))


def replace_kit(root, kit) -> Path:
    """Swap .ai-sdlc/kit for the newer copy at `kit` (update). Interrupted, a re-run finishes it."""
    dest = Path(root) / paths.KIT_REL
    if dest.exists():
        if not is_kit(dest):
            raise FileExistsError(dest)
        shutil.rmtree(dest)
    return move_kit(root, kit)


def move_kit(root, kit) -> Path:
    """Move the copied kit folder to .ai-sdlc/kit (nothing to do when it is already there).

    shutil.move renames within one filesystem and copies then deletes across two.
    """
    root, kit = Path(root).resolve(), Path(kit).resolve()
    dest = root / paths.KIT_REL
    if kit == dest:
        return dest
    if root not in kit.parents:
        raise ValueError(f"the kit folder must be inside the repo: {kit} is not in {root}")
    if dest.exists():
        raise FileExistsError(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(kit), str(dest))
    return dest
