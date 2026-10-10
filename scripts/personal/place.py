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
file recorded in state.json like any other. Text files are handled as str; a file
that is not UTF-8 (a .pptx template, a .png logo) is carried as bytes and written
byte for byte. Its SKILL.md's relative links that
leave its folder are pointed at the same file inside .ai-sdlc/kit/
(rewrite_links), so they still resolve after the move.

A skill may keep files in the kit copy only: its `.kit-only` file lists globs
(one per line, relative to the skill folder, `#` comments; `*` stays inside one
folder). Matching files are never placed; a Markdown link to one, in any of the
skill's .md files, is pointed at the same file in .ai-sdlc/kit/ (design
2026-10-09 §8.7). The brand skill keeps its big binaries there this way.
"""
from __future__ import annotations

import fnmatch
import json
import posixpath
import re
import shutil
from pathlib import Path

from . import packs, paths, reuse

KIT_CLASS = "kit"
SIDECAR = ".kit-new"
KIT_ONLY_FILE = ".kit-only"
_LINK = re.compile(r"\]\(([^)\s]+)\)")              # ](target) of a Markdown link
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")  # http:, https:, mailto:, …


def rewrite_links(text, skill_dir, placed_dir, exists, kit_only=frozenset(), sub="",
                  outside=True) -> tuple[str, list[str]]:
    """Point relative links that leave the skill's folder, or that name a kit-only file,
    at the same file in .ai-sdlc/kit/.

    skill_dir is the skill's folder in the kit (template/.claude/skills/<skill>),
    placed_dir its folder in the repo (.agents/skills/ai-sdlc-<skill>), and
    exists(kit_rel) says whether a kit path exists. kit_only holds the kit paths
    of the files that stay in the kit copy; sub is the folder of this Markdown file
    inside the skill ("" for SKILL.md); outside=False leaves links that leave the
    folder alone. Other links inside the skill's folder, URLs, root-absolute paths
    and #anchors are left alone. Returns the new text and the links whose target is
    not in the kit, which are left as they are.
    Pure and deterministic: the same input always renders the same bytes.
    """
    missing = []
    base = posixpath.join(skill_dir, sub) if sub else skill_dir
    placed_base = posixpath.join(placed_dir, sub) if sub else placed_dir

    def fix(m):
        target = m.group(1)
        if _SCHEME.match(target) or target.startswith(("#", "/")):
            return m.group(0)
        path, hash_, anchor = target.partition("#")
        kit_rel = posixpath.normpath(posixpath.join(base, path))
        if kit_rel == skill_dir or kit_rel.startswith(skill_dir + "/"):
            if kit_rel not in kit_only:
                return m.group(0)
        elif not outside:
            return m.group(0)
        elif kit_rel == ".." or kit_rel.startswith("../") or not exists(kit_rel):
            missing.append(target)
            return m.group(0)
        new = posixpath.relpath(posixpath.join(paths.KIT_REL, kit_rel), placed_base)
        if path.endswith("/"):
            new += "/"
        return f"]({new}{hash_}{anchor})"

    return _LINK.sub(fix, text), missing


def kit_only_patterns(kit, skill) -> list[str]:
    """The globs in a skill's .kit-only file ([] when it has none)."""
    f = Path(kit) / packs.SKILLS_REL / skill / KIT_ONLY_FILE
    if not f.is_file():
        return []
    return [line.strip() for line in f.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def _glob_match(rel, pattern) -> bool:
    """One pattern segment per path segment, so `*` never crosses a `/`."""
    a, b = rel.split("/"), pattern.split("/")
    return len(a) == len(b) and all(fnmatch.fnmatchcase(x, y) for x, y in zip(a, b))


def _skill_files(src: Path) -> list[str]:
    """A skill folder's files that setup may place: no dotfiles, caches or symlinks."""
    out = []
    for p in sorted(src.rglob("*")):
        sub = p.relative_to(src)
        if (p.is_symlink() or not p.is_file()
                or any(part.startswith(".") or part == "__pycache__" for part in sub.parts)):
            continue
        out.append(sub.as_posix())
    return out


def kit_only(kit, skill) -> list[str]:
    """Skill-relative paths its .kit-only keeps in the kit copy, sorted; [] when none."""
    patterns = kit_only_patterns(kit, skill)
    if not patterns:
        return []
    src = Path(kit) / packs.SKILLS_REL / skill
    return [rel for rel in _skill_files(src) if any(_glob_match(rel, p) for p in patterns)]


def kit_asset_rel(skill, rel) -> str:
    """Repo path of a skill's file inside the kit copy (where a kit-only file lives)."""
    return f"{paths.KIT_REL}/{packs.SKILLS_REL}/{skill}/{rel}"


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


def placed_skill(kit, skill, missing=None, kit_only_set=None) -> tuple[str, str]:
    """(repo path, text) of a library skill as setup places it: prefixed name, links into the kit.

    Links with no target in the kit are appended to `missing` when a list is given
    (validate_packs.py reports them); setup itself places the text either way.
    """
    src_dir = f"{packs.SKILLS_REL}/{skill}"
    dest_dir = f".agents/skills/{packs.PREFIX}{skill}"
    if kit_only_set is None:
        kit_only_set = {f"{src_dir}/{rel}" for rel in kit_only(kit, skill)}
    text = packs.prefixed_skill((Path(kit) / src_dir / "SKILL.md").read_text(encoding="utf-8"), skill)
    text, lost = rewrite_links(text, src_dir, dest_dir, lambda rel: (Path(kit) / rel).exists(),
                               kit_only_set)
    if missing is not None:
        missing += lost
    return f"{dest_dir}/SKILL.md", text


def placed_skill_files(kit, skill, missing=None) -> dict[str, str | bytes]:
    """{repo path: text or bytes} of a library skill's whole folder as setup places it.

    SKILL.md goes through placed_skill; the skill's other files (references/,
    assets/, LICENSE, …) are copied byte for byte, at the same relative path:
    UTF-8 files as str, any other file (a template, an image) as bytes.
    Dotfiles, caches, symlinks and the files its .kit-only keeps in the kit copy are
    skipped; in its other .md files, links to those files point into .ai-sdlc/kit/.
    """
    src = Path(kit) / packs.SKILLS_REL / skill
    src_dir = f"{packs.SKILLS_REL}/{skill}"
    held = kit_only(kit, skill)
    held_set = {f"{src_dir}/{rel}" for rel in held}
    rel, text = placed_skill(kit, skill, missing, held_set)
    files = {rel: text}
    dest_dir = posixpath.dirname(rel)
    for sub in _skill_files(src):
        if sub == "SKILL.md" or sub in held:
            continue
        data = (src / sub).read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            files[f"{dest_dir}/{sub}"] = data       # binary: placed as is
            continue
        if held_set and sub.endswith(".md"):
            text, _ = rewrite_links(text, src_dir, dest_dir, lambda r: (Path(kit) / r).exists(),
                                    held_set, sub=posixpath.dirname(sub), outside=False)
        files[f"{dest_dir}/{sub}"] = text
    return files


def wanted_files(kit, all_packs, choices) -> dict[str, str | bytes]:
    """{repo path: text, or bytes for a binary skill file} of every file these choices call for."""
    combined = packs.combine(all_packs, choices)
    values = packs.core_values(all_packs, choices, combined)
    files = dict(packs.instructions_file(all_packs[pid], values)
                 for pid in [packs.CORE, *choices["roles"]])
    for skill in combined["skills"]:
        files.update(placed_skill_files(kit, skill))
    files[paths.SESSION_HOOK_REL] = session_hook()
    files[paths.USER_REL] = user_md(all_packs, choices, combined)
    return files


def kit_only_wanted(kit, all_packs, choices) -> list[str]:
    """Repo paths (under .ai-sdlc/kit) of the files these choices' skills keep in the kit
    copy only; state.json records them so check can report one that went missing."""
    return sorted(kit_asset_rel(skill, rel) for skill in packs.combine(all_packs, choices)["skills"]
                  for rel in kit_only(kit, skill))


HOOK_COMMAND = "python3 .ai-sdlc/kit/setup.py check --quiet --hook"


def session_hook() -> str:
    """The repo hook Copilot CLI runs once at session start (repo hooks load only in a
    folder the person trusted); its output adds the session check to the conversation."""
    entry = {"type": "command", "bash": HOOK_COMMAND, "powershell": HOOK_COMMAND,
             "cwd": ".", "timeoutSec": 15}
    return json.dumps({"version": 1, "hooks": {"sessionStart": [entry]}}, indent=2) + "\n"


def _write(root, st, rel, data: bytes) -> None:
    for parent in reversed(list(Path(rel).parents)[:-1]):
        if not (root / parent).exists():
            st["created_dirs"].append(parent.as_posix())
    paths.write_atomic(root / rel, data)
    reuse.record(st, rel, KIT_CLASS, data)


def _drop_bytecode(folder: Path) -> None:
    for p in folder.iterdir():
        if p.is_file() and p.suffix == ".pyc":
            p.unlink()
        elif p.name == "__pycache__" and p.is_dir() and not p.is_symlink():
            if all(q.is_file() and q.suffix == ".pyc" for q in p.iterdir()):
                for q in p.iterdir():
                    q.unlink()
                p.rmdir()


def prune_dirs(root, st) -> None:
    """Remove folders setup created once they are empty again (deepest first). Python
    bytecode a skill's script left there (__pycache__/, *.pyc) goes with them."""
    for d in sorted(st["created_dirs"], key=lambda p: p.count("/"), reverse=True):
        path = Path(root) / d
        if path.is_dir():
            _drop_bytecode(path)
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
        if not path.exists():
            st["created_dirs"].remove(d)


def apply(root, st, wanted: dict[str, str | bytes]) -> dict[str, list[str]]:
    """Make the repo hold `wanted`; returns what was written, kept, skipped and removed."""
    root = Path(root)
    report = {"written": [], "kept": [], "skipped": [], "removed": []}
    tracked = paths.tracked(root, set(wanted) | set(st["files"]))
    keep = set(wanted)
    for rel, text in sorted(wanted.items()):
        data = text if isinstance(text, bytes) else text.encode("utf-8")
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
            f"{packs.ROLES_REL}/{packs.CORE}/role.json", f"{packs.ROLES_REL}/recommend.json",
            f"{packs.SKILLS_REL}/maven-via-artifactory/scripts/detect_stack.py")


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


def _kit_only_problems(kit, skill) -> list[str]:
    """A .kit-only pattern that matches no file is a mistake (a renamed folder, a typo)."""
    patterns = kit_only_patterns(kit, skill)
    if not patterns:
        return []
    files = _skill_files(Path(kit) / packs.SKILLS_REL / skill)
    return [f".kit-only pattern matches nothing: {packs.SKILLS_REL}/{skill}: {p}"
            for p in patterns if not any(_glob_match(rel, p) for rel in files)]


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
                problems += _kit_only_problems(kit, skill)
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
