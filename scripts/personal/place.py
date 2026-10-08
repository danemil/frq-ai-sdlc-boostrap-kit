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

A placed skill is its whole folder (SKILL.md plus references/, assets/, …), each
file recorded in state.json like any other. Its SKILL.md's relative links that
leave its folder are pointed at the same file inside .ai-sdlc/kit/
(rewrite_links), so they still resolve after the move.
"""
from __future__ import annotations

import json
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


def placed_skill_files(kit, skill, missing=None) -> dict[str, str]:
    """{repo path: text} of a library skill's whole folder as setup places it.

    SKILL.md goes through placed_skill; the skill's other files (references/,
    assets/, LICENSE, …) are copied byte for byte, at the same relative path.
    Dotfiles, caches and symlinks are skipped. Skill files must be UTF-8 text.
    """
    src = Path(kit) / packs.SKILLS_REL / skill
    rel, text = placed_skill(kit, skill, missing)
    files = {rel: text}
    dest_dir = posixpath.dirname(rel)
    for p in sorted(src.rglob("*")):
        sub = p.relative_to(src)
        if (p.is_symlink() or not p.is_file() or sub.as_posix() == "SKILL.md"
                or any(part.startswith(".") or part == "__pycache__" for part in sub.parts)):
            continue
        try:
            files[f"{dest_dir}/{sub.as_posix()}"] = p.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"{skill}/{sub.as_posix()} is not UTF-8 text; "
                             "a placed skill holds text files only") from None
    return files


def wanted_files(kit, all_packs, choices) -> dict[str, str]:
    """{repo path: text} of every file these choices call for."""
    combined = packs.combine(all_packs, choices)
    values = packs.core_values(all_packs, choices, combined)
    files = dict(packs.instructions_file(all_packs[pid], values)
                 for pid in [packs.CORE, *choices["roles"]])
    for skill in combined["skills"]:
        files.update(placed_skill_files(kit, skill))
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


REQUIRED = ("setup.py", "VERSION", "ONBOARDING.md", "connectors.py",
            f"{packs.ROLES_REL}/{packs.CORE}/role.json")


def _link_problems(kit, skill) -> list[str]:
    """Kit files a skill's SKILL.md links to (inside its folder or out) that are not there."""
    skill_dir = f"{packs.SKILLS_REL}/{skill}"
    text = (Path(kit) / skill_dir / "SKILL.md").read_text(encoding="utf-8")
    out = []
    for m in _LINK.finditer(text):
        target = m.group(1)
        if _SCHEME.match(target) or target.startswith(("#", "/")):
            continue
        rel = posixpath.normpath(posixpath.join(skill_dir, target.partition("#")[0]))
        if rel != ".." and not rel.startswith("../") and not (Path(kit) / rel).exists():
            out.append(f"missing {rel} (linked from {skill}/SKILL.md)")
    return out


def validate_kit(kit) -> list[str]:
    """What keeps this kit folder from setting anyone up; [] means it is whole.

    setup and update call it before they move or replace anything. It loads every
    role pack, resolves every skill the packs or the library name (each SKILL.md,
    and every kit file it links to), checks the connectors the packs suggest, and
    renders every file for all roles and all library skills, writing nothing. Each
    problem is a short phrase; most read "missing <kit path>".
    """
    kit = Path(kit)
    problems = [f"missing {rel}" for rel in REQUIRED if not (kit / rel).is_file()]
    version = (paths.read_text(kit / "VERSION") or "").strip()
    if (kit / "VERSION").is_file() and not re.fullmatch(r"\d+(\.\d+)*", version):
        problems.append("VERSION is empty or not a version number")
    all_packs = {}
    for f in sorted((kit / packs.ROLES_REL).glob("*/role.json")):
        where = f.relative_to(kit).as_posix()
        try:
            pack = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(f"{where} is not readable ({exc})")
            continue
        if not (isinstance(pack, dict) and isinstance(pack.get("skills"), list)
                and isinstance(pack.get("connectors"), list)):
            problems.append(f"{where} is not readable (no skills or connectors list)")
            continue
        md = f.parent / "instructions.md"
        if not md.is_file():
            problems.append(f"missing {md.relative_to(kit).as_posix()}")
        source = pack.get("source")
        if isinstance(source, str) and not (kit / source).is_file():
            problems.append(f"missing {source}")
        all_packs[f.parent.name] = pack
    connectors = set(packs.available_connectors(kit))
    for name in sorted({c for p in all_packs.values() for c in p["connectors"]} - connectors):
        problems.append(f"missing {packs.CONNECTORS_REL}/{name}.py")
    library = set(packs.available_skills(kit))
    named = {s for p in all_packs.values() for s in p["skills"]} - set(packs.UNSUPPORTED_SKILLS)
    for skill in sorted(named | library):
        if skill not in library:
            problems.append(f"missing {packs.SKILLS_REL}/{skill}/SKILL.md")
        else:
            try:
                problems += _link_problems(kit, skill)
            except (OSError, ValueError) as exc:
                problems.append(f"{packs.SKILLS_REL}/{skill}/SKILL.md is not readable ({exc})")
    if problems:
        return problems
    try:  # the dry run: every file setup could place, for all roles and all library skills
        loaded = packs.load(kit)
        everything = {"name": "x", "roles": packs.selectable(loaded), "lang": "en",
                      "git_comfort": None, "rituals": None,
                      "add_skills": sorted(library), "drop_skills": []}
        wanted_files(kit, loaded, everything)
    except Exception as exc:  # noqa: BLE001  any failure here would have stopped a setup
        problems.append(f"the files cannot be prepared ({type(exc).__name__}: {exc})")
    return problems


def replace_kit(root, kit) -> Path:
    """Swap .ai-sdlc/kit for the newer copy at `kit` (update). Interrupted, a re-run finishes it."""
    dest = Path(root) / paths.KIT_REL
    if Path(root).resolve() not in Path(kit).resolve().parents:   # checked before the old kit goes
        raise ValueError(f"the kit folder must be inside the repo: {kit} is not in {root}")
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
