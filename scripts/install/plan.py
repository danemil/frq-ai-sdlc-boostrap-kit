#!/usr/bin/env python3
"""Build the action plan: what the installer would do, before it does anything.

Separating "decide" from "apply" is what makes --dry-run truthful and --yes
safe: the same plan object is printed, or executed, or diffed. Nothing in this
module touches the filesystem except to read.

Stdlib only.
"""
from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path

import manifest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "template/scripts/harness"))
import merge

CLASS_OWN, CLASS_SEED, CLASS_MERGE = "own", "seed", "merge"

# actions
CREATE, UPDATE, MERGE, SKIP, CONFLICT, SIDECAR, SYMLINK = (
    "create", "update", "merge", "skip", "conflict", "sidecar", "symlink")


class Action:
    __slots__ = ("rel", "cls", "kind", "reason", "payload", "resolution")

    def __init__(self, rel, cls, kind, reason, payload=None):
        self.rel, self.cls, self.kind = rel, cls, kind
        self.reason, self.payload = reason, payload
        self.resolution = None

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"<{self.kind} {self.rel} ({self.cls}) {self.reason}>"


def load_classes(path=None) -> dict:
    path = Path(path) if path else Path(__file__).with_name("file-classes.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _matches(rel: str, patterns) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(rel, pat):
            return True
        if pat.endswith("/**") and (rel == pat[:-3] or rel.startswith(pat[:-2])):
            return True
    return False


def classify(rel: str, spec: dict) -> str:
    classes = spec.get("classes", {})
    for cls in (CLASS_MERGE, CLASS_SEED):
        if _matches(rel, classes.get(cls, [])):
            return cls
    return CLASS_OWN


def profile_patterns(spec: dict, profile: str) -> list[str]:
    """Expand a profile, following @inherits references."""
    profiles = spec.get("profiles", {})
    if profile not in profiles:
        raise KeyError(f"unknown profile: {profile}")
    out, seen = [], set()

    def expand(name):
        if name in seen:
            return
        seen.add(name)
        for pat in profiles[name]:
            if pat.startswith("@"):
                expand(pat[1:])
            else:
                out.append(pat)

    expand(profile)
    return out


def template_files(template_root) -> list[str]:
    """Every regular file in the template, as repo-relative POSIX paths."""
    root = Path(template_root)
    skip_dirs = {".git", "__pycache__", "node_modules", ".venv", ".index"}
    rels = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        parts = set(path.relative_to(root).parts)
        if parts & skip_dirs or path.suffix == ".pyc":
            continue
        rels.append(path.relative_to(root).as_posix())
    return sorted(rels)


def ci_gates(spec: dict) -> list[str]:
    """Every governance gate the kit can install (`install.sh --ci`)."""
    return sorted(spec.get("ci", {}))


def ci_patterns(spec: dict, ci=None) -> list[str]:
    """Patterns of the chosen CI gates. None means every gate (the default)."""
    gates = spec.get("ci", {})
    out = []
    for name in (ci_gates(spec) if ci is None else ci):
        if name not in gates:
            raise KeyError(f"unknown CI gate: {name}")
        out.extend(gates[name])
    return out


def selected_files(template_root, spec: dict, profile: str, ci=None) -> list[str]:
    patterns = profile_patterns(spec, profile) + ci_patterns(spec, ci)
    return [rel for rel in template_files(template_root) if _matches(rel, patterns)]


def unselected_ci_files(template_root, spec: dict, ci) -> list[str]:
    """Template files that belong to a CI gate not in `ci`."""
    dropped = [g for g in ci_gates(spec) if g not in ci]
    if not dropped:
        return []
    patterns = ci_patterns(spec, dropped)
    return [rel for rel in template_files(template_root) if _matches(rel, patterns)]


def build(template_root, target_root, spec: dict, profile: str,
          man: dict, render=None, ci=None) -> list[Action]:
    """Decide an action for every selected template file. Reads only."""
    template_root, target_root = Path(template_root), Path(target_root)
    actions: list[Action] = []

    for rel in selected_files(template_root, spec, profile, ci):
        cls = classify(rel, spec)
        kit_bytes = (template_root / rel).read_bytes()
        if render is not None:
            kit_bytes = render(rel, kit_bytes)
        st = manifest.state(target_root, man, rel, kit_bytes)

        # An operator who chose "keep mine" is not asked again until the kit's
        # own version of the file changes (the pacman/.pacnew contract).
        if man.get("deferred", {}).get(rel) == manifest.sha256_bytes(kit_bytes):
            actions.append(Action(rel, cls, SKIP, "deferred by you earlier", kit_bytes))
            continue

        if st in (manifest.NEW, manifest.MISSING):
            actions.append(Action(rel, cls, CREATE, st, kit_bytes))
        elif st == manifest.IDENTICAL:
            actions.append(Action(rel, cls, SKIP, "already identical", kit_bytes))
        elif cls == CLASS_MERGE:
            actions.append(Action(rel, cls, MERGE, st, kit_bytes))
        elif cls == CLASS_SEED:
            actions.append(Action(rel, cls, SKIP, f"seed file, {st} — yours to own", kit_bytes))
        elif st == manifest.CLEAN:
            actions.append(Action(rel, cls, UPDATE, "kit-owned, unmodified", kit_bytes))
        else:  # FOREIGN or MODIFIED on a kit-owned file
            actions.append(Action(rel, cls, CONFLICT, st, kit_bytes))

    return actions


def merge_preview(target_root, action: Action, spec: dict) -> tuple[str, list[str]]:
    """Compute the merged text for a MERGE action without writing it."""
    path = Path(target_root) / action.rel
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    kit_text = action.payload.decode("utf-8")
    fmt = spec.get("merge_formats", {}).get(action.rel, "json")

    if fmt == "json":
        return merge.merge_json(existing, kit_text)
    if fmt == "json-hooks":
        return merge.merge_json_hooks(existing, kit_text)
    if fmt == "lines":
        return merge.merge_lines(existing, kit_text), []
    if fmt == "toml-block":
        return merge.merge_toml_block(existing, kit_text), []
    raise ValueError(f"unknown merge format for {action.rel}: {fmt}")


def summarize(actions: list[Action]) -> dict:
    counts: dict[str, int] = {}
    for a in actions:
        counts[a.kind] = counts.get(a.kind, 0) + 1
    return counts
