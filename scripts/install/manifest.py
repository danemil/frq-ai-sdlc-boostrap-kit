#!/usr/bin/env python3
"""Install manifest — the record that makes re-running the installer safe.

Without a manifest the installer cannot tell "the kit changed this file" from
"the operator changed this file", so every re-run is a guess and there is no
upgrade path. The manifest stores, per managed path, the class it was installed
under and the SHA-256 of exactly what the installer last wrote. Comparing that
against what is on disk yields one of six states, which is all the decision
logic the planner needs.

Lives at .ai-sdlc/manifest.json in the target repo. Stdlib only.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_REL = ".ai-sdlc/manifest.json"
SCHEMA = 1

# --- file states -----------------------------------------------------------
NEW = "new"            # unmanaged, absent            -> create
FOREIGN = "foreign"    # unmanaged, present           -> pre-existing; conflict
IDENTICAL = "identical"  # unmanaged/managed, byte-equal to the kit -> adopt silently
CLEAN = "clean"        # managed, untouched since install -> safe to overwrite
MODIFIED = "modified"  # managed, operator edited it  -> conflict
MISSING = "missing"    # managed, operator deleted it -> recreate


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    return sha256_bytes(p.read_bytes())


def new_manifest(kit_version: str = "0.0.0") -> dict:
    return {
        "schema": SCHEMA,
        "kit_version": kit_version,
        "installed_at": None,
        "profile": None,
        "harnesses": [],
        "files": {},
    }


def load(root, kit_version: str = "0.0.0") -> dict:
    """Read the manifest, or return a fresh one if absent/corrupt."""
    path = Path(root) / MANIFEST_REL
    if not path.is_file():
        return new_manifest(kit_version)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return new_manifest(kit_version)
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        return new_manifest(kit_version)
    data.setdefault("files", {})
    data.setdefault("harnesses", [])
    return data


def save(root, manifest: dict) -> Path:
    path = Path(root) / MANIFEST_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest["schema"] = SCHEMA
    manifest["installed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def record(manifest: dict, rel: str, cls: str, written: bytes | str) -> None:
    """Note that `rel` now holds exactly `written`, installed under class `cls`."""
    if isinstance(written, str):
        written = written.encode("utf-8")
    manifest["files"][rel] = {"class": cls, "sha256": sha256_bytes(written)}


def forget(manifest: dict, rel: str) -> None:
    manifest["files"].pop(rel, None)


def state(root, manifest: dict, rel: str, kit_bytes: bytes | None = None) -> str:
    """Classify `rel` in the target repo. See the state constants above."""
    entry = manifest["files"].get(rel)
    disk = sha256_file(Path(root) / rel)

    if entry is None:
        if disk is None:
            return NEW
        if kit_bytes is not None and disk == sha256_bytes(kit_bytes):
            return IDENTICAL
        return FOREIGN

    if disk is None:
        return MISSING
    if kit_bytes is not None and disk == sha256_bytes(kit_bytes):
        return IDENTICAL
    return CLEAN if disk == entry["sha256"] else MODIFIED


def managed(manifest: dict, cls: str | None = None) -> list[str]:
    """Paths the installer manages, optionally filtered to one class."""
    return sorted(
        rel for rel, e in manifest["files"].items()
        if cls is None or e.get("class") == cls
    )
