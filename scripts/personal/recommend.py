"""Skill suggestions from the repo's files, and the list of the other skills.

Read-only and deterministic (design 2026-10-09 §5): the same repo and the same choices
always give the same list, in the same order (adds first, then drops, each by skill).
The repo is read through the kit's own copy of maven-via-artifactory/scripts/detect_stack.py
(one detector, also used by Copilot through that skill), never the person's home folder.

Rules and the catalogue are data, in roles/recommend.json, so a client can add rules
without code. An `add` rule fires when one of its `when` signals is found, the person has
one of its `roles`, and the skill is not theirs yet. A `drop` rule fires when the repo has
code, none of its `unless` signals is found, and the skill is theirs (not one they added
themselves). The person's explicit choice always wins: a skill they left out is never
suggested back, a skill they added is never suggested for dropping. Nothing here places
or changes anything; accepted suggestions go through `change --add-skill`.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

from . import packs

RULES_REL = "roles/recommend.json"
DETECT_REL = f"{packs.SKILLS_REL}/maven-via-artifactory/scripts/detect_stack.py"
SIGNALS = ("java", "maven", "javafx", "go", "node", "jest", "react", "web", "sonar", "blackduck", "code")
CODE = ("java", "go", "node")
ACTIONS = ("add", "drop")
RULE_KEYS = {"skill", "action", "when", "unless", "roles", "reason"}
ROLE_PLAYBOOKS = "Role playbooks"
OTHER = "Other"
MAX_REASON = 120
MAX_SUMMARY = 100


def load(kit) -> dict:
    """{"rules": [...], "groups": [...], "catalogue": {...}} from roles/recommend.json."""
    data = json.loads((Path(kit) / RULES_REL).read_text(encoding="utf-8"))
    return {"rules": data.get("rules", []), "groups": data.get("groups", [OTHER]),
            "catalogue": data.get("catalogue", {})}


def _detector(kit):
    path = Path(kit) / DETECT_REL
    spec = importlib.util.spec_from_file_location("ai_sdlc_detect_stack", path)
    mod = importlib.util.module_from_spec(spec)
    dont = sys.dont_write_bytecode
    sys.dont_write_bytecode = True              # no __pycache__ in the kit copy
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = dont
    return mod


def signals(root, kit) -> dict[str, list[str]]:
    """{signal: repo paths that show it} for every signal found in the repo (design §5.2)."""
    result = _detector(kit).scan(Path(root))          # never home=: only the repo counts
    found = {k: sorted(set(v)) for k, v in result["files"].items() if v and k in SIGNALS}
    code = sorted({e for k in CODE for e in found.get(k, [])})
    if code:
        found["code"] = code
    return found


def compute(kit, root, st, all_packs) -> list[dict]:
    """The suggestions for this repo and these choices, declined ones included (marked)."""
    found = signals(root, kit)
    c = st["choices"]
    have = set(packs.combine(all_packs, c)["skills"])
    roles = set(c["roles"])
    declined = set(st.get("declined_recommendations", []))
    out = []
    for r in sorted(load(kit)["rules"], key=lambda r: (r["action"] != "add", r["skill"])):
        sid = f"{r['action']}:{r['skill']}"
        if r.get("roles") and not roles & set(r["roles"]):
            continue
        if r["action"] == "add":
            hit = [s for s in r["when"] if s in found]
            fires = bool(hit) and r["skill"] not in have and r["skill"] not in c["drop_skills"]
            evidence = sorted({e for s in hit for e in found[s]})
        else:
            fires = ("code" in found and not any(s in found for s in r["unless"])
                     and r["skill"] in have and r["skill"] not in c["add_skills"])
            evidence = []
        if fires:
            out.append({"id": sid, "action": r["action"], "skill": r["skill"],
                        "reason": r["reason"], "evidence": evidence[:3],
                        "declined": sid in declined})
    return out


def open_items(items) -> list[dict]:
    """Suggestions not declined yet."""
    return [i for i in items if not i["declined"]]


def _description(kit, skill) -> str:
    text = (Path(kit) / packs.SKILLS_REL / skill / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r"(?ms)\A---\n(.*?)\n---", text)
    front = m.group(1) if m else ""
    m = re.search(r"(?m)^description:[ \t]*(.*)$", front)
    if not m:
        return ""
    value = m.group(1).strip()
    if value in ("", ">", "|", ">-", "|-"):
        rest = front[m.end():].splitlines()
        value = " ".join(line.strip() for line in rest[1:] if line.startswith((" ", "\t")))
    return value.strip().strip("'\"")


def summary_of(kit, skill) -> str:
    """The first sentence of the skill's description, cut to 100 characters."""
    desc = " ".join(_description(kit, skill).split())
    m = re.match(r"(.+?[.!?])(\s|$)", desc)
    first = m.group(1) if m else desc
    if len(first) > MAX_SUMMARY:
        first = first[:MAX_SUMMARY - 1].rstrip() + "…"
    return first or skill


def others(kit, st, all_packs, items) -> list[dict]:
    """Every skill the person can add that is not theirs, not suggested and not declined,
    grouped by the catalogue (groups order, then skill)."""
    data = load(kit)
    groups, catalogue = data["groups"], data["catalogue"]
    have = set(packs.combine(all_packs, st["choices"])["skills"])
    taken = have | {i["skill"] for i in items}
    out = []
    for skill in packs.available_skills(kit):
        if skill in taken:
            continue
        entry = catalogue.get(skill)
        if entry:
            group, summary = entry["group"], entry["summary"]
        else:
            group = ROLE_PLAYBOOKS if skill.startswith("playbook-") else OTHER
            summary = summary_of(kit, skill)
        out.append({"skill": skill, "group": group, "summary": summary})
    rank = {g: n for n, g in enumerate(groups)}
    return sorted(out, key=lambda o: (rank.get(o["group"], len(groups)), o["skill"]))


# --- validation (kit CI and tests; packs.validate calls it) -----------------------

def validate(kit) -> list[str]:
    """Readable problems in roles/recommend.json; [] means valid."""
    kit = Path(kit)
    try:
        data = json.loads((kit / RULES_REL).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"not readable ({exc})"]
    if not isinstance(data, dict):
        return ["must be a JSON object"]
    errs = []
    known = set(packs.available_skills(kit))
    all_packs = packs.load(kit)
    roles = set(packs.selectable(all_packs))
    in_packs = {s for p in all_packs.values() for s in p.get("skills", [])}
    rules = data.get("rules", [])
    if not isinstance(rules, list):
        return ["rules must be a list"]
    seen = set()
    for n, r in enumerate(rules, 1):
        if not isinstance(r, dict):
            errs.append(f"rule {n} must be an object")
            continue
        where = f"rule {n} ({r.get('action')}:{r.get('skill')})"
        errs += [f"{where}: unknown key {k}" for k in sorted(set(r) - RULE_KEYS)]
        skill, action = r.get("skill"), r.get("action")
        if skill not in known:
            errs.append(f"{where}: skill {skill!r} is not in {packs.SKILLS_REL}")
        if action not in ACTIONS:
            errs.append(f"{where}: action must be add or drop")
            continue
        sid = f"{action}:{skill}"
        if sid in seen:
            errs.append(f"{where}: a second rule for {sid}; one rule per id")
        seen.add(sid)
        want, other = ("when", "unless") if action == "add" else ("unless", "when")
        sigs = r.get(want)
        if not isinstance(sigs, list) or not sigs:
            errs.append(f"{where}: {action} needs a non-empty {want} list")
        else:
            errs += [f"{where}: unknown signal {s!r} (known: {', '.join(SIGNALS)})"
                     for s in sigs if s not in SIGNALS]
        if other in r:
            errs.append(f"{where}: {action} takes {want}, not {other}")
        rr = r.get("roles")
        if action == "add" and (not isinstance(rr, list) or not rr):
            errs.append(f"{where}: add needs a non-empty roles list")
        elif rr is not None:
            if not isinstance(rr, list):
                errs.append(f"{where}: roles must be a list")
            else:
                errs += [f"{where}: unknown role {x!r}" for x in rr if x not in roles]
        reason = r.get("reason")
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= MAX_REASON \
                or len(reason) > MAX_REASON:
            errs.append(f"{where}: reason must be 1 to {MAX_REASON} characters")
        if action == "add" and skill in in_packs:
            errs.append(f"{where}: {skill} is in a role pack already; add rules are for library skills")
    groups = data.get("groups", [])
    if not isinstance(groups, list) or OTHER not in groups:
        errs.append(f"groups must be a list that includes {OTHER!r}")
        groups = [OTHER]
    catalogue = data.get("catalogue", {})
    if not isinstance(catalogue, dict):
        return errs + ["catalogue must be an object"]
    for skill, entry in sorted(catalogue.items()):
        where = f"catalogue {skill}"
        if skill not in known:
            errs.append(f"{where}: skill {skill!r} is not in {packs.SKILLS_REL}")
        if not isinstance(entry, dict):
            errs.append(f"{where}: must be an object with group and summary")
            continue
        if entry.get("group") not in groups:
            errs.append(f"{where}: unknown group {entry.get('group')!r} (known: {', '.join(groups)})")
        s = entry.get("summary")
        if not isinstance(s, str) or not 1 <= len(s.strip()) or len(s) > MAX_SUMMARY:
            errs.append(f"{where}: summary must be 1 to {MAX_SUMMARY} characters")
    return errs
