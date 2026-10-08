"""state.json: what personal setup placed in this repo, and what the person chose.

Every command writes it last, atomically, so an interrupted run leaves the old
state or the new one, never a mix. Its `files` map has the shape of the Phase 0
install manifest ({path: {class, sha256}}), so manifest.state() classifies our
files as NEW, IDENTICAL, CLEAN, MODIFIED, MISSING or FOREIGN.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import paths

SCHEMA = 1


def new(kit_version: str) -> dict:
    return {
        "schema": SCHEMA,
        "kit_version": kit_version,
        "updated_at": None,
        "choices": {"name": "", "roles": [], "lang": "en", "git_comfort": None,
                    "rituals": None, "add_skills": [], "drop_skills": []},
        "files": {},          # {path: {"class": "kit", "sha256": ...}}
        "created_dirs": [],   # folders setup made, removed again when empty
        "acks": {},           # {warning id: fingerprint of the team file when acknowledged}
    }


def load(root) -> dict | None:
    """The saved state, or None when this repo is not set up (or the file is unreadable)."""
    text = paths.read_text(Path(root) / paths.STATE_REL)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        return None
    st = new(data.get("kit_version", "0.0.0"))
    choices = {**st["choices"], **data.get("choices", {})}
    st.update(data)
    st["choices"] = choices
    return st


def save(root, st: dict) -> Path:
    st["schema"] = SCHEMA
    st["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = Path(root) / paths.STATE_REL
    paths.write_atomic(path, json.dumps(st, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return path
