"""Precise warnings about the team's own AI files, and acknowledging them.

The kit never edits a team file. It says where the team's instructions and the
kit's meet, so the person (and Copilot) can look for real contradictions. Each
warning has a stable id built from the team file's path and carries that file's
fingerprint; `ack` stores the fingerprint, and the warning returns only when the
file changes.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import packs, reuse

TEAM_BRIEFS = {"AGENTS.md": "team-agents-md",
               ".github/copilot-instructions.md": "team-copilot-instructions"}
TEAM_RULE_DIRS = ()                          # Copilot ignores .claude/rules (Task 0 check 10)
SKILL_DIRS = (".claude/skills", ".github/skills", ".agents/skills")
KIT_APPLY_TO = ("**",)                       # every kit instructions file applies everywhere


def _apply_to(front: str) -> list[str]:
    for line in front.splitlines():
        m = re.match(r"^applyTo:\s*(.*)$", line)
        if m:
            return [g.strip() for g in reuse.unquote(m.group(1)).split(",") if g.strip()]
    return []


def _literal_prefix(glob: str) -> str:
    cut = min([glob.find(c) for c in "*?[{" if c in glob] or [len(glob)])
    return glob[:cut]


def overlaps(a: str, b: str) -> bool:
    """Could globs `a` and `b` match the same file? Errs on the side of yes."""
    pa, pb = _literal_prefix(a), _literal_prefix(b)
    return pa.startswith(pb) or pb.startswith(pa)


def _shared(globs) -> list[str]:
    return [g for g in globs if any(overlaps(g, k) for k in KIT_APPLY_TO)]


def warnings(root, st) -> list[tuple[str, str, str]]:
    """(id, text, fingerprint of the team file) for every place team and kit meet."""
    root = Path(root)
    ours = set(st["files"])
    out = []
    for rel, wid in TEAM_BRIEFS.items():
        fp = reuse.sha256_file(root / rel)
        if fp:
            out.append((wid, f"The team has its own {rel}. Copilot reads it together with the "
                             "kit's instructions.", fp))
    inst = root / ".github/instructions"
    for p in sorted(inst.glob("*.instructions.md")) if inst.is_dir() else []:
        rel = p.relative_to(root).as_posix()
        if p.name.startswith(packs.PREFIX) or rel in ours:
            continue
        front, _ = reuse.split_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        shared = _shared(_apply_to(front))
        if shared:
            out.append((f"team-instructions:{rel}", f"The team's {rel} also applies to "
                        f"{', '.join(shared)}, where the kit's instructions apply too.",
                        reuse.sha256_file(p)))
    for d in TEAM_RULE_DIRS:
        for p in sorted((root / d).glob("*.md")) if (root / d).is_dir() else []:
            rel = p.relative_to(root).as_posix()
            front, _ = reuse.split_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
            try:
                globs = reuse.rule_paths(front, rel) or ["**"]
            except ValueError:
                globs = ["**"]
            out.append((f"team-rules:{rel}", f"The team's rule {rel} applies to "
                        f"{', '.join(_shared(globs))}, where the kit's instructions apply too.",
                        reuse.sha256_file(p)))
    placed = {Path(rel).parent.name for rel in ours if rel.startswith(".agents/skills/")}
    names = placed | {n[len(packs.PREFIX):] for n in placed}
    for d in SKILL_DIRS:
        for skill in sorted((root / d).glob("*/SKILL.md")) if (root / d).is_dir() else []:
            rel = skill.relative_to(root).as_posix()
            if rel in ours or skill.parent.name not in names:
                continue
            out.append((f"skill-clash:{skill.parent.relative_to(root).as_posix()}",
                        f"The team has a skill {skill.parent.name} ({rel}); the kit adds "
                        f"{packs.PREFIX}{skill.parent.name.removeprefix(packs.PREFIX)}. "
                        "Copilot sees both.", reuse.sha256_file(skill)))
    return out


def active(root, st) -> list[tuple[str, str]]:
    """The warnings not yet acknowledged, or whose team file changed since."""
    return [(wid, text) for wid, text, fp in warnings(root, st) if st["acks"].get(wid) != fp]
