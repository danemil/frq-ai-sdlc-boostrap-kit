#!/usr/bin/env python3
"""Deck snapshot: the normalised, git-ignored input every deck metric reads.

Design: docs/roadmap/2026-10-01-deck-builder-design.md §3.2 (kit repo).

A snapshot records *what was fetched, from where, and how trustworthy it is*:
each source carries a tier (`script` > `agent-sourced` > `unavailable`), and a
metric later takes the weakest tier among its inputs. Stdlib only.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

SCHEMA = 1
TIERS = ("script", "agent-sourced", "unavailable")  # strongest -> weakest
LISTS = ("sources", "work_items", "pull_requests", "commits", "requirements", "docs")
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_snapshot(run_id: str, scope: dict) -> dict:
    snap = {"schema": SCHEMA, "run_id": run_id, "scope": dict(scope)}
    for key in LISTS:
        snap[key] = []
    return snap


def add_source(snap: dict, name: str, tier: str, **meta) -> None:
    """Record (or replace) a source; `fetched_at` is stamped in UTC."""
    if tier not in TIERS:
        raise ValueError(f"unknown tier {tier!r}; expected one of {TIERS}")
    entry = {"name": name, "tier": tier, "fetched_at": _now(), **meta}
    snap["sources"] = [s for s in snap["sources"] if s.get("name") != name] + [entry]


def source_tier(snap: dict, name: str) -> str:
    for s in snap.get("sources", []):
        if s.get("name") == name:
            return s.get("tier", "unavailable")
    return "unavailable"


def weakest(tiers: Iterable[str]) -> str:
    tiers = list(tiers)
    if not tiers:
        return "unavailable"
    return max(tiers, key=lambda t: TIERS.index(t) if t in TIERS else len(TIERS))


def validate(snap: dict) -> list[str]:
    """Return a list of problems; [] means the snapshot is valid."""
    errors: list[str] = []
    if snap.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}, got {snap.get('schema')!r}")
    if not isinstance(snap.get("run_id"), str) or not snap.get("run_id"):
        errors.append("run_id must be a non-empty string")
    if not isinstance(snap.get("scope"), dict):
        errors.append("scope must be a mapping")
    for key in LISTS:
        if not isinstance(snap.get(key), list):
            errors.append(f"{key} must be a list")
    for i, s in enumerate(snap.get("sources") or []):
        if not isinstance(s, dict) or not s.get("name"):
            errors.append(f"sources[{i}] needs a name")
        elif s.get("tier") not in TIERS:
            errors.append(f"sources[{i}] ({s['name']}) has unknown tier {s.get('tier')!r}")
    for key in ("work_items", "requirements"):
        for i, item in enumerate(snap.get(key) or []):
            if not isinstance(item, dict) or not item.get("key"):
                errors.append(f"{key}[{i}] needs a key")
    return errors


def dumps(obj) -> str:
    """Canonical JSON: stable key order, 2-space indent, trailing newline."""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def write_json(obj, path) -> None:
    """Atomic write: temp file in the target dir, then os.replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(dumps(obj))
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def save(snap: dict, path) -> None:
    errors = validate(snap)
    if errors:
        raise ValueError("invalid snapshot: " + "; ".join(errors))
    write_json(snap, path)


def load(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_dir(run_id: str, repo_root) -> Path:
    """Where a run's snapshot.json and metrics.json live (git-ignored)."""
    if not _RUN_ID_RE.match(run_id):
        raise ValueError(f"invalid run id {run_id!r}")
    return Path(repo_root) / ".ai-sdlc" / "decks" / run_id
