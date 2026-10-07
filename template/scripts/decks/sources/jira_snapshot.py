#!/usr/bin/env python3
"""Jira work items for decks: the ledger exporter's adapter plus deck fields.

Design: docs/roadmap/2026-10-01-deck-builder-design.md §3.1/§3.3 (kit repo).

Reuses scripts/jira/export_jira.py for config, auth, Cloud/DC search and
pagination, so there is one Jira client in the kit. This module only widens
the field list, scopes the JQL, and normalises the extra fields deck metrics
need (links, components, fix versions, sub-tasks, AC, doc update, Jama
traces). The committed CSV ledger is not touched. Stdlib only.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from . import SourceUnavailable

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "jira"))
import export_jira  # noqa: E402

LEDGER_CONFIG = "docs/product/jira/config.json"
EXTRA_FIELDS = ["issuelinks", "components", "fixVersions", "subtasks", "resolutiondate", "status"]
_MODES = ("description:", "label:")
_HEADING_MARKUP = re.compile(r"^(h[1-6]\.\s*|#{1,6}\s*|[*_]+\s*)")
_TRAILING_MARKUP = re.compile(r"[\s:*_]+$")


def _deck_fields(deck_cfg: dict) -> dict:
    return (deck_cfg.get("jira") or {}).get("fields") or {}


def _quote(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def scoped_jql(scope: dict, default_project: str) -> str:
    """JQL for a deck scope. An explicit `jql` in the scope wins verbatim."""
    if scope.get("jql"):
        return scope["jql"]
    projects = scope.get("projects") or [default_project]
    clauses = [f"project in ({', '.join(_quote(p) for p in projects)})"]
    if scope.get("sprint"):
        clauses.append(f"sprint = {_quote(scope['sprint'])}")
    if scope.get("release"):
        clauses.append(f"fixVersion = {_quote(scope['release'])}")
    if scope.get("since"):
        clauses.append(f"updated >= {_quote(scope['since'])}")
    if scope.get("until"):
        clauses.append(f"updated <= {_quote(scope['until'])}")
    return " AND ".join(clauses) + " ORDER BY key ASC"


def deck_jira_config(ledger_cfg: dict, deck_cfg: dict, scope: dict) -> dict:
    """Ledger config + extra fields + scoped JQL. The ledger dict is not mutated.

    export_jira.fetch_all requests every value in cfg["fields"], so extra
    fields ride along under deck-private keys; the ledger's own keys
    (sprint, epic_link, story_points) keep their meaning for normalize_issue.
    """
    cfg = dict(ledger_cfg)
    fields = dict(ledger_cfg.get("fields") or {})
    for name in EXTRA_FIELDS:
        fields[f"deck_{name}"] = name
    for key, value in _deck_fields(deck_cfg).items():
        if value and not str(value).startswith(_MODES):
            fields[f"deck_{key}"] = value
    cfg["fields"] = fields
    cfg["jql"] = scoped_jql(scope, ledger_cfg.get("project", ""))
    return cfg


def _text(value) -> str:
    if isinstance(value, dict):
        return export_jira.adf_to_text(value)
    if isinstance(value, list):
        return "\n".join(_text(v) for v in value)
    return "" if value is None else str(value)


def _heading_has_content(description, heading: str) -> bool:
    """True when `heading` appears as its own line and real text follows it."""
    want = heading.strip().lower()
    lines = [_TRAILING_MARKUP.sub("", _HEADING_MARKUP.sub("", ln.strip())).lower()
             for ln in _text(description).splitlines()]
    for i, line in enumerate(lines):
        if line == want:
            return any(rest for rest in lines[i + 1:])
    return False


def _acceptance_criteria(fields: dict, deck_fields: dict):
    spec = deck_fields.get("acceptance_criteria")
    if not spec:
        return None  # unconfigured: unknown, never reported as missing
    if spec.startswith("description:"):
        return _heading_has_content(fields.get("description"), spec.split(":", 1)[1])
    return bool(_text(fields.get(spec)).strip())


def _option_text(value) -> str:
    if isinstance(value, dict):
        return str(value.get("value") or value.get("name") or "")
    if isinstance(value, list):
        return ";".join(t for t in (_option_text(v) for v in value) if t)
    return "" if value is None else str(value).strip()


def _doc_update(fields: dict, deck_fields: dict) -> str:
    spec = deck_fields.get("doc_update")
    if not spec:
        return "n/a"
    if spec.startswith("label:"):
        return "done" if spec.split(":", 1)[1] in (fields.get("labels") or []) else "missing"
    return _option_text(fields.get(spec)) or "missing"


def _sprints(fields: dict, cfg: dict) -> list[str]:
    raw = fields.get((cfg.get("fields") or {}).get("sprint", "")) or []
    names = []
    for entry in raw if isinstance(raw, list) else []:
        if isinstance(entry, dict):
            name = entry.get("name", "")
        else:
            m = re.search(r"name=([^,\]]+)", str(entry))  # DC greenhopper string
            name = m.group(1) if m else str(entry)
        if name:
            names.append(name)
    return names


def _points(value):
    if value in (None, ""):
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return int(num) if num.is_integer() else num


def _links(fields: dict) -> list[dict]:
    links = []
    for link in fields.get("issuelinks") or []:
        for direction in ("inward", "outward"):
            other = link.get(f"{direction}Issue")
            if other:
                status = ((other.get("fields") or {}).get("status") or {})
                links.append({"type": (link.get("type") or {}).get("name", ""),
                              "direction": direction, "key": other.get("key", ""),
                              "status_category": (status.get("statusCategory") or {}).get("key", "")})
    return sorted(links, key=lambda l: (l["type"], l["direction"], export_jira.natural_key(l["key"])))


def _requirement_links(links: list[dict], deck_cfg: dict):
    pattern = (deck_cfg.get("jama") or {}).get("link_match")
    if not pattern:
        return None  # no Jama trace convention configured: unknown
    rx = re.compile(pattern)
    keys = {l["key"] for l in links if rx.search(l["type"]) or rx.search(l["key"])}
    return sorted(keys, key=export_jira.natural_key)


def normalize_work_item(raw: dict, cfg: dict, deck_cfg: dict, base_url: str) -> dict:
    """One Jira issue -> the snapshot `work_items` shape (design §3.2)."""
    base = export_jira.normalize_issue(raw, cfg, base_url)
    f = raw.get("fields") or {}
    deck_fields = _deck_fields(deck_cfg)
    links = _links(f)
    return {
        "key": base["key"], "type": base["type"], "title": base["title"],
        "status": base["status"],
        "status_category": ((f.get("status") or {}).get("statusCategory") or {}).get("key", ""),
        "assignee": base["assignee"], "sprints": _sprints(f, cfg),
        "epic": base["epic"], "parent": base["parent"],
        "story_points": _points(f.get((cfg.get("fields") or {}).get("story_points", ""))),
        "components": sorted(c.get("name", "") for c in f.get("components") or []),
        "fix_versions": sorted(v.get("name", "") for v in f.get("fixVersions") or []),
        "labels": sorted(f.get("labels") or []),
        "subtask_count": len(f.get("subtasks") or []),
        "links": links,
        "acceptance_criteria": _acceptance_criteria(f, deck_fields),
        "doc_update": _doc_update(f, deck_fields),
        "requirement_links": _requirement_links(links, deck_cfg),
        "created": base["created"], "updated": base["updated"],
        "resolved": f.get("resolutiondate") or "", "url": base["url"],
    }


def fetch(deck_cfg: dict, scope: dict, ledger_cfg: dict | None = None, fetch_all=None):
    """Fetch scoped work items. Returns (work_items, source_meta).

    Raises SourceUnavailable when config or auth is missing or Jira is
    unreachable (export_jira reports those via sys.exit; we convert them).
    """
    if ledger_cfg is None:
        path = REPO_ROOT / (deck_cfg.get("jira") or {}).get("config", LEDGER_CONFIG)
        try:
            ledger_cfg = export_jira.load_config(path)
        except (OSError, ValueError) as exc:
            raise SourceUnavailable(f"jira: cannot read ledger config {path}: {exc}") from exc
    cfg = deck_jira_config(ledger_cfg, deck_cfg, scope)
    try:
        base_url, raw = (fetch_all or export_jira.fetch_all)(cfg)
    except SystemExit as exc:
        raise SourceUnavailable(f"jira: {exc.code}") from exc
    items = [normalize_work_item(r, cfg, deck_cfg, base_url) for r in raw]
    items.sort(key=lambda i: export_jira.natural_key(i["key"]))
    return items, {"tier": "script", "query": cfg["jql"], "count": len(items),
                   "deployment": cfg.get("deployment", "")}
