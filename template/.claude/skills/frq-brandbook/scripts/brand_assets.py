#!/usr/bin/env python3
"""Find a file of the brand skill: the placed folder first, then the kit copy.

The big files of this skill (both templates, layout previews, examples, key visuals,
background JPEGs, logo PNGs) are listed in ../.kit-only: setup keeps them in the kit copy,
.ai-sdlc/kit/template/.claude/skills/frq-brandbook/, and never places them in
.agents/skills/ai-sdlc-frq-brandbook/ (design 2026-10-09 §8.7). check_brand.py,
frq_pptx.py and new_deck.py load this module by path and ask it for every file.

    python3 brand_assets.py templates/frq-master.pptx     # prints the path, or exit 2

Order: (1) this skill's own folder (the placed folder, or the kit copy when the script
runs from there, as in the kit's tests); (2) the kit copy, found by walking up from the
current folder, then from this script, to the repo root. If none has the file:
AssetMissing, a plain message with the expected path. Python 3.9+, standard library only.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True                         # no __pycache__ in the placed skill

from pathlib import Path

SKILL = "frq-brandbook"
KIT_SKILL_REL = ".ai-sdlc/kit/template/.claude/skills/" + SKILL
HERE = Path(__file__).resolve().parent.parent          # this skill's folder


class AssetMissing(FileNotFoundError):
    """A file of the brand skill is in neither the placed folder nor the kit copy."""


def _ancestors(start: Path):
    """start and its parents, up to and including the first folder that holds .git."""
    for folder in (start, *start.parents):
        yield folder
        if (folder / ".git").exists():
            return


def find(rel: str, start=None) -> Path:
    """The path of `rel` (relative to the skill folder, e.g. 'brand-tokens.json')."""
    rel = rel.replace("\\", "/").lstrip("/")
    if ".." in rel.split("/"):
        raise AssetMissing(f"{rel}: not a path inside the brand skill")
    own = HERE / rel
    if own.is_file():
        return own
    seen = set()
    for origin in (Path(start or Path.cwd()).resolve(), HERE):
        for folder in _ancestors(origin):
            candidate = folder / KIT_SKILL_REL / rel
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate.is_file():
                return candidate
    raise AssetMissing(f"{KIT_SKILL_REL}/{rel} is missing, and the placed skill does not have it "
                       "either. The kit folder (.ai-sdlc/kit) is incomplete: say 'check the kit'.")


def asset_path(rel: str, start=None) -> Path:
    """The path of an asset, `rel` relative to assets/ (e.g. 'templates/frq-master.pptx')."""
    rel = rel.replace("\\", "/").lstrip("/")
    return find(rel if rel.startswith("assets/") else "assets/" + rel, start)


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: brand_assets.py <path under assets/>", file=sys.stderr)
        return 2
    try:
        print(asset_path(args[0]))
    except AssetMissing as exc:
        print(f"brand_assets: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
