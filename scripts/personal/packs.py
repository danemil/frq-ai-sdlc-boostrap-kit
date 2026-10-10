"""Role packs: roles/<id>/role.json + instructions.md, and what a set of roles adds up to.

Every pack has one format, including the always-on `core` pack, so role discovery
(v2) can generate packs without a migration. Skills come from the kit's skill
library (template/.claude/skills) and are placed with an `ai-sdlc-` prefix.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from string import Template

from . import reuse
from .connectors import registry

ROLES_REL = "roles"
SKILLS_REL = "template/.claude/skills"
CONNECTORS_REL = "scripts/personal/connectors"
CORE = "core"
PREFIX = "ai-sdlc-"
GIT_LEVELS = ("git-native", "guided", "hidden")   # least to most guided
RITUALS = ("none", "status")                      # least to most guided
LANGUAGES = {"en": "English", "ro": "Romanian (română)", "de": "German (Deutsch)"}
KEYS = {"id", "label", "source", "skills", "defaults", "connectors"}
UNSUPPORTED_SKILLS = {"git-verbs": "it drives the team-mode session scripts, which personal setup does not place"}
MAX_LINES = 60
RESERVED = "personal"                             # paths.is_personal: the person's own files
_ID = re.compile(r"^[a-z][a-z0-9-]*$")

GIT_TEXT = {
    "git-native": "They use git themselves. Suggest commands when useful; run a git command "
                  "that changes history or the remote only when they ask.",
    "guided": "Do git for them when they ask (\"save my work\", \"get the latest\", \"send for "
              "review\"). Say in one line what you are doing, and ask before every commit and push.",
    "hidden": "Do git for them in plain words (\"Saved.\"), without git jargon. Ask before every "
              "commit and push. Never commit to main, master or another protected branch; "
              "use a personal branch.",
}
RITUAL_TEXT = {  # optional habits; the check --quiet line is always on (roles/core/instructions.md)
    "status": "After the check, give a one-line summary of where the work stands.",
    "none": "No other session-start habit.",
}
HEADER = ("<!-- AI-SDLC personal setup, from roles/{id}/instructions.md. If you edit this file, "
          "the kit keeps your edit and puts its newer copy next to it as .kit-new. -->")


def load(kit) -> dict:
    """{id: pack} for every roles/<id>/role.json; each pack also gets its 'instructions' text."""
    out = {}
    for f in sorted((Path(kit) / ROLES_REL).glob("*/role.json")):
        pack = json.loads(f.read_text(encoding="utf-8"))
        md = f.parent / "instructions.md"
        pack["instructions"] = md.read_text(encoding="utf-8") if md.is_file() else ""
        out[f.parent.name] = pack
    return out


def selectable(all_packs) -> list[str]:
    return [pid for pid in all_packs if pid != CORE]


def available_skills(kit) -> list[str]:
    """Skills a person can have: the kit's library minus the ones personal setup cannot place."""
    root = Path(kit) / SKILLS_REL
    return sorted(p.parent.name for p in root.glob("*/SKILL.md")
                  if p.parent.name not in UNSUPPORTED_SKILLS)


def available_connectors(kit) -> list[str]:
    """Connector names in the kit (registry discovery: one module per connector)."""
    folder = Path(kit) / CONNECTORS_REL
    return registry.names(folder) if folder.is_dir() else []


def role_connectors(all_packs, roles) -> list[str]:
    """The connectors the chosen roles usually need, in role order, without repeats.
    Defaults only drive suggestions: any person can connect any connector."""
    return list(dict.fromkeys(c for r in roles for c in all_packs[r]["connectors"]))


def _most_guided(values, order):
    return max(values, key=order.index)


def combine(all_packs, choices) -> dict:
    """What the person gets: skills (union, then their own + and -), git comfort, rituals."""
    chosen = [all_packs[CORE]] + [all_packs[r] for r in choices["roles"]]
    skills = {s for p in chosen for s in p["skills"]}
    skills = (skills | set(choices["add_skills"])) - set(choices["drop_skills"])
    return {
        "skills": sorted(skills),
        "git_comfort": choices["git_comfort"] or _most_guided(
            [p["defaults"]["git_comfort"] for p in chosen], GIT_LEVELS),
        "rituals": choices["rituals"] or _most_guided(
            [p["defaults"]["rituals"] for p in chosen], RITUALS),
    }


def core_values(all_packs, choices, combined) -> dict:
    """The $placeholders of roles/core/instructions.md."""
    return {
        "name": choices["name"],
        "language": LANGUAGES[choices["lang"]],
        "roles": ", ".join(all_packs[r]["label"] for r in choices["roles"]) or "no role chosen yet",
        "git_comfort": GIT_TEXT[combined["git_comfort"]],
        "rituals": RITUAL_TEXT[combined["rituals"]],
    }


def instructions_file(pack, values) -> tuple[str, str]:
    """(repo path, text) of a pack's Copilot instructions file. Only core is a template."""
    body = pack["instructions"]
    if pack["id"] == CORE:
        body = Template(body).substitute(values)
    rel = f".github/instructions/{PREFIX}{pack['id']}.instructions.md"
    return rel, f"---\napplyTo: '**'\n---\n{HEADER.format(id=pack['id'])}\n\n{body}"


def prefixed_skill(text: str, skill: str) -> str:
    """SKILL.md with `name:` prefixed to match its placed folder (agentskills.io: name == folder)."""
    front, body = reuse.split_frontmatter(text)
    new_front, n = re.subn(r"(?m)^name:.*$", f"name: {PREFIX}{skill}", front, count=1)
    if not front or n != 1:
        raise ValueError(f"{skill}/SKILL.md has no frontmatter name: line")
    return f"---\n{new_front}\n---\n\n{body.replace('<PROJECT_NAME>', 'this project')}"


# --- validation (kit CI and tests; setup.py never calls it) ------------------

def validate(kit) -> list[str]:
    """Every role pack is well-formed, its source exists, its skills exist. [] means valid."""
    kit = Path(kit)
    errors = []
    if not (kit / ROLES_REL / CORE / "role.json").is_file():
        errors.append(f"{ROLES_REL}/{CORE}/role.json is missing: the core pack is required")
    known = set(available_skills(kit))
    known_connectors = available_connectors(kit)
    for f in sorted((kit / ROLES_REL).glob("*/role.json")):
        where = f.relative_to(kit).as_posix()
        try:
            pack = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{where}: not valid JSON ({exc})")
            continue
        errors += [f"{where}: {e}" for e in _pack_errors(kit, f.parent, pack, known,
                                                         known_connectors)]
    rules = kit / ROLES_REL / "recommend.json"     # place.REQUIRED makes it required for setup
    if rules.is_file():
        from . import recommend
        errors += [f"{ROLES_REL}/recommend.json: {e}" for e in recommend.validate(kit)]
    return errors


def _pack_errors(kit, folder, pack, known, known_connectors=()) -> list[str]:
    if not isinstance(pack, dict):
        return ["must be a JSON object"]
    errs = [f"missing key: {k}" for k in sorted(KEYS - set(pack))]
    errs += [f"unknown key: {k}" for k in sorted(set(pack) - KEYS)]
    if errs:
        return errs
    if pack["id"] != folder.name or not _ID.match(str(pack["id"])):
        errs.append(f"id {pack['id']!r} must be lowercase and equal its folder name")
    elif pack["id"] == RESERVED:
        errs.append(f"id {RESERVED!r} is reserved: ai-sdlc-{RESERVED}.instructions.md "
                    "is the person's own notes file")
    if not isinstance(pack["label"], str) or not pack["label"].strip():
        errs.append("label must be a non-empty string")
    if not isinstance(pack["source"], str) or not (kit / pack["source"]).is_file():
        errs.append(f"source {pack['source']!r} does not exist in the kit")
    if not isinstance(pack["skills"], list):
        errs.append("skills must be a list")
    else:
        for s in pack["skills"]:
            if str(s).startswith(RESERVED + "-"):
                errs.append(f"skill {s!r}: names starting {RESERVED}- are the person's own skills")
            elif s in UNSUPPORTED_SKILLS:
                errs.append(f"skill {s!r} cannot be placed: {UNSUPPORTED_SKILLS[s]}")
            elif s not in known:
                errs.append(f"skill {s!r} is not in {SKILLS_REL}")
    d = pack["defaults"]
    if (not isinstance(d, dict) or set(d) != {"git_comfort", "rituals"}
            or d["git_comfort"] not in GIT_LEVELS or d["rituals"] not in RITUALS):
        errs.append(f"defaults must be {{\"git_comfort\": {'|'.join(GIT_LEVELS)}, "
                    f"\"rituals\": {'|'.join(RITUALS)}}}")
    errs += _connector_errors(pack["connectors"], known_connectors)
    md = folder / "instructions.md"
    text = md.read_text(encoding="utf-8") if md.is_file() else ""
    if not text.strip():
        errs.append("instructions.md is missing or empty")
    elif text.startswith("---"):
        errs.append("instructions.md must not have frontmatter: setup adds applyTo")
    elif len(text.splitlines()) > MAX_LINES:
        errs.append(f"instructions.md has {len(text.splitlines())} lines; keep it to {MAX_LINES}")
    elif pack["id"] == CORE:
        sample = {k: "x" for k in ("name", "language", "roles", "git_comfort", "rituals")}
        try:
            Template(text).substitute(sample)
        except (KeyError, ValueError) as exc:
            errs.append(f"instructions.md has an unknown or broken placeholder: {exc}")
    return errs


def _connector_errors(value, known) -> list[str]:
    """`connectors`: a list of connector names the kit has (the role's suggested defaults)."""
    if not isinstance(value, list) or not all(isinstance(c, str) for c in value):
        return ["connectors must be a list of connector names"]
    errs = [f"connector {c!r} is not in {CONNECTORS_REL} (known: "
            f"{', '.join(known) or 'none'})" for c in value if c not in known]
    if len(set(value)) != len(value):
        errs.append("connectors must not repeat a name")
    return errs
