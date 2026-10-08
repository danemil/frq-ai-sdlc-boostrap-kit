#!/usr/bin/env python3
"""Validate the kit's role packs (kit CI; needs PyYAML for the skill check).

  python3 scripts/personal/validate_packs.py

Checks every roles/<id>/role.json (packs.validate), then renders each skill a
pack uses exactly as setup.py places it (prefixed name, prefixed folder) and runs
template/scripts/validate-skills.py on the result. Exit 0 when all is valid.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from personal import packs  # noqa: E402

KIT = Path(__file__).resolve().parents[2]


def skill_errors(kit) -> list[str]:
    kit = Path(kit)
    spec = importlib.util.spec_from_file_location(
        "validate_skills", kit / "template/scripts/validate-skills.py")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except SystemExit:
        return ["PyYAML is required for the skill check: pip install pyyaml"]
    errors = []
    used = sorted({s for p in packs.load(kit).values() for s in p["skills"]})
    with tempfile.TemporaryDirectory() as tmp:
        for skill in used:
            src = kit / packs.SKILLS_REL / skill / "SKILL.md"
            dest = Path(tmp) / f"{packs.PREFIX}{skill}" / "SKILL.md"
            dest.parent.mkdir()
            dest.write_text(packs.prefixed_skill(src.read_text(encoding="utf-8"), skill),
                            encoding="utf-8")
            errors += [f"{packs.PREFIX}{skill}: {e}" for e in module.validate_file(dest)]
    return errors


def main() -> int:
    errors = packs.validate(KIT)
    if not errors:
        errors = skill_errors(KIT)
    for e in errors:
        print(f"FAIL  {e}")
    if errors:
        return 1
    print(f"ok    {len(packs.load(KIT))} role pack(s) valid; their skills pass validate-skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
