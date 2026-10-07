#!/usr/bin/env python3
"""git fallback for decks: merge commits as PR-like rows, and release tags.

Design: docs/roadmap/2026-10-01-deck-builder-design.md §3.1 (kit repo).

Used when Bitbucket isn't configured. A merge commit stands in for a merged
PR: the PR number and source branch are read from the host's merge message
(Bitbucket Cloud "Merged in <branch> (pull request #N)", Data Center
"Pull request #N: …" + "Merge in P/r from <branch> to …", GitHub "Merge pull
request #N from <owner>/<branch>"). Squash or rebase merges leave no merge
commit, so they are not counted. That's why Bitbucket stays the preferred
source. Only merged work is visible here: no open or declined PRs. Stdlib only.
"""
from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import SourceUnavailable
from .bitbucket_prs import extract_keys

_PR_NUMBER = re.compile(r"pull request #(\d+)", re.IGNORECASE)
_BRANCH_PATTERNS = [
    re.compile(r"^Merged in (\S+)"),                              # Bitbucket Cloud
    re.compile(r"^Merge in \S+ from (\S+) to ", re.MULTILINE),     # Bitbucket Data Center
    re.compile(r"^Merge pull request #\d+ from [^/\s]+/(\S+)"),   # GitHub
    re.compile(r"^Merge branch '([^']+)'"),                       # plain git
]
FIELD, RECORD = "\x1f", "\x1e"


def _git(cwd, *args) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise SourceUnavailable(f"git: {detail.strip()[:200]}") from exc
    return out.stdout


def _utc(iso: str) -> str:
    if not iso:
        return ""
    return datetime.fromisoformat(iso).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _source_branch(subject: str, body: str) -> str:
    message = f"{subject}\n{body}"
    for rx in _BRANCH_PATTERNS:
        m = rx.search(message)
        if m:
            return m.group(1)
    return ""


def merges(since: str, until: str, cwd=".") -> list[dict]:
    """Merge commits committed in [since, until] (whole days, UTC), oldest first."""
    repo = Path(_git(cwd, "rev-parse", "--show-toplevel").strip()).name
    fmt = FIELD.join(["%H", "%an", "%cI", "%s", "%b"]) + RECORD
    # Filter dates here, not with --since: git stops walking at the first commit
    # older than --since, so a backdated or rebased HEAD hides newer merges.
    out = _git(cwd, "log", "--merges", f"--format={fmt}")
    rows = []
    for record in out.split(RECORD):
        record = record.strip("\n")
        if not record:
            continue
        sha, author, date, subject, body = (record.split(FIELD) + [""] * 5)[:5]
        number = _PR_NUMBER.search(f"{subject}\n{body}")
        branch = _source_branch(subject, body)
        closed = _utc(date)
        if not since <= closed[:10] <= until:
            continue
        rows.append({"repo": repo, "id": int(number.group(1)) if number else None,
                     "title": subject, "state": "MERGED", "author": author,
                     "source_branch": branch, "target_branch": "", "created": "",
                     "updated": closed, "closed": closed,
                     "keys": extract_keys(f"{subject}\n{body}", branch),
                     "url": "", "commit": sha, "source": "git"})
    rows.sort(key=lambda r: (r["closed"], r["commit"]))
    return rows


def tags(cwd=".") -> list[dict]:
    """Tags newest first, each with its date (tagger date, or commit date) and commit."""
    fmt = FIELD.join(["%(refname:short)", "%(creatordate:iso-strict)", "%(*objectname)", "%(objectname)"])
    out = _git(cwd, "for-each-ref", "--sort=-creatordate", f"--format={fmt}", "refs/tags")
    result = []
    for line in out.splitlines():
        if not line.strip():
            continue
        name, date, peeled, obj = (line.split(FIELD) + [""] * 4)[:4]
        result.append({"name": name, "date": _utc(date), "commit": peeled or obj})
    return result
