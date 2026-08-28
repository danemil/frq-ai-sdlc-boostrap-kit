#!/usr/bin/env python3
"""Format-aware mergers for the `merge` file class.

A single strategy cannot combine a JSON object, a hook array, a .gitignore and
a config.toml. Each format gets the narrowest merger that does the job, and all
of them obey one rule:

    the operator's content is never dropped.

Where the kit and the operator disagree on the same key, the operator wins and
the disagreement is reported so the planner can prompt.

Stdlib only. TOML is read with tomllib (verification) but written as a sentinel
block, so no TOML serializer dependency is needed.
"""
from __future__ import annotations

import json

try:  # 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - older interpreters
    tomllib = None

BEGIN = "# >>> ai-sdlc >>>"
END = "# <<< ai-sdlc <<<"
TAG = "_aiSdlc"


# --- JSON objects ----------------------------------------------------------

def merge_json(existing_text: str, kit_text: str) -> tuple[str, list[str]]:
    """Deep-union two JSON objects. Operator wins every scalar disagreement.

    Returns (merged_text, conflicts) where conflicts are dotted key paths that
    the kit wanted to set differently.
    """
    try:
        existing = json.loads(existing_text) if existing_text.strip() else {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"existing file is not valid JSON: {exc}") from exc
    kit = json.loads(kit_text) if kit_text.strip() else {}

    conflicts: list[str] = []
    merged = _deep_union(existing, kit, "", conflicts)
    return json.dumps(merged, indent=2, sort_keys=False) + "\n", conflicts


def _deep_union(existing, kit, path: str, conflicts: list[str]):
    if not isinstance(existing, dict) or not isinstance(kit, dict):
        if existing != kit:
            conflicts.append(path or "<root>")
        return existing  # operator wins
    out = dict(existing)
    for key, kit_val in kit.items():
        here = f"{path}.{key}" if path else key
        if key.startswith("$"):        # $comment / $note are documentation
            out.setdefault(key, kit_val)
        elif key not in out:
            out[key] = kit_val
        else:
            out[key] = _deep_union(out[key], kit_val, here, conflicts)
    return out


# --- Claude Code / Codex hook arrays ---------------------------------------

def merge_json_hooks(existing_text: str, kit_text: str, tag: str = TAG) -> tuple[str, list[str]]:
    """Union two settings files, replacing only *our* previously-tagged hooks.

    Kit hook groups are stamped with `_aiSdlc: true`. On re-run every tagged
    group is dropped and re-added, so the merge is idempotent; untagged groups
    (the operator's own hooks, or another tool's) are never touched.
    """
    try:
        existing = json.loads(existing_text) if existing_text.strip() else {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"existing file is not valid JSON: {exc}") from exc
    kit = json.loads(kit_text) if kit_text.strip() else {}

    conflicts: list[str] = []
    merged = _deep_union(
        {k: v for k, v in existing.items() if k != "hooks"},
        {k: v for k, v in kit.items() if k != "hooks"},
        "", conflicts,
    )

    events = dict(existing.get("hooks") or {})
    for event, kit_groups in (kit.get("hooks") or {}).items():
        kept = [g for g in events.get(event, []) if not (isinstance(g, dict) and g.get(tag))]
        stamped = []
        for group in kit_groups:
            group = dict(group)
            group[tag] = True
            stamped.append(group)
        events[event] = kept + stamped
    if events:
        merged["hooks"] = events
    return json.dumps(merged, indent=2) + "\n", conflicts


# --- sentinel blocks (.gitignore, .codex/config.toml) ----------------------

def extract_block(text: str, begin: str = BEGIN, end: str = END) -> str | None:
    """Return the body between the sentinels, or None if there is no block."""
    start = text.find(begin)
    if start == -1:
        return None
    stop = text.find(end, start)
    if stop == -1:
        return None
    return text[start + len(begin):stop].strip("\n")


def merge_block(existing_text: str, block: str,
                begin: str = BEGIN, end: str = END) -> str:
    """Replace the sentinel block if present, else append one. Idempotent."""
    block = block.strip("\n")
    payload = f"{begin}\n{block}\n{end}\n"

    start = existing_text.find(begin)
    if start != -1:
        stop = existing_text.find(end, start)
        if stop != -1:
            tail = existing_text[stop + len(end):].lstrip("\n")
            head = existing_text[:start]
            return f"{head}{payload}" + (f"\n{tail}" if tail else "")

    if existing_text and not existing_text.endswith("\n"):
        existing_text += "\n"
    sep = "\n" if existing_text else ""
    return f"{existing_text}{sep}{payload}"


def merge_toml_block(existing_text: str, block: str,
                     begin: str = BEGIN, end: str = END) -> str:
    """Sentinel-merge into a TOML file, then verify the result still parses."""
    merged = merge_block(existing_text, block, begin, end)
    if tomllib is not None:
        try:
            tomllib.loads(merged)
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"merged TOML would be invalid: {exc}") from exc
    return merged


def set_toml_root_key(text: str, key: str, value) -> str:
    """Set a top-level TOML key, keeping it in the document's root region.

    A bare key appended to the end of a TOML file belongs to whatever table
    header came last, not to the root — so it must be written above the first
    `[table]`, which is what this does. Idempotent; verifies the result.
    """
    line = f"{toml_key(key)} = {toml_value(value)}"
    lines = text.splitlines()

    # The root region ends at the first [table] — and at our own generated
    # block, so a hand-maintained key never lands inside "do not edit" territory.
    first_table = len(lines)
    for i, raw in enumerate(lines):
        stripped = raw.lstrip()
        if stripped.startswith("[") or stripped.startswith(BEGIN):
            first_table = i
            break

    prefix = f"{toml_key(key)} "
    for i in range(first_table):
        stripped = lines[i].lstrip()
        if stripped.startswith(prefix) and "=" in stripped:
            if lines[i] == line:
                return text
            lines[i] = line
            break
    else:
        at = first_table
        while at > 0 and not lines[at - 1].strip():
            at -= 1
        lines.insert(at, line)

    merged = "\n".join(lines)
    if not merged.endswith("\n"):
        merged += "\n"
    if tomllib is not None:
        try:
            tomllib.loads(merged)
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"setting {key} would break the TOML: {exc}") from exc
    return merged


# --- line files (.gitignore) ----------------------------------------------

def merge_lines(existing_text: str, kit_text: str,
                begin: str = BEGIN, end: str = END) -> str:
    """Append only the kit lines the file does not already carry."""
    have = {ln.strip() for ln in existing_text.splitlines() if ln.strip()}
    block_body = extract_block(existing_text, begin, end) or ""
    have -= {ln.strip() for ln in block_body.splitlines() if ln.strip()}

    wanted = [ln for ln in kit_text.splitlines()
              if ln.strip() and ln.strip() not in have]
    if not wanted:
        wanted = ["# (nothing to add)"]
    return merge_block(existing_text, "\n".join(wanted), begin, end)


# --- TOML emission ---------------------------------------------------------

def toml_value(value) -> str:
    """Serialize a scalar/array/table-free value as TOML. Enough for MCP entries."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value)
    if isinstance(value, str):
        return json.dumps(value)          # JSON strings are valid TOML basic strings
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(toml_value(v) for v in value) + "]"
    raise TypeError(f"unsupported TOML value: {type(value).__name__}")


def toml_key(key: str) -> str:
    """Bare key when possible, quoted otherwise (MCP names may contain '-')."""
    if key and all(c.isalnum() or c in "_-" for c in key):
        return key
    return json.dumps(key)
