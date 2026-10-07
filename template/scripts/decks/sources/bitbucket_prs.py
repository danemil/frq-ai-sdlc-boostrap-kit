#!/usr/bin/env python3
"""Bitbucket pull requests for decks (Cloud API 2.0 or Data Center REST 1.0).

Design: docs/roadmap/2026-10-01-deck-builder-design.md §3.1 (kit repo).

One adapter, two deployments, mirroring scripts/jira/export_jira.py:
  cloud       GET {base}/2.0/repositories/{workspace}/{repo}/pullrequests
              paging: follow `next`; base defaults to https://api.bitbucket.org
  datacenter  GET {base}/rest/api/1.0/projects/{project}/repos/{repo}/pull-requests
              paging: `start` = `nextPageStart` until `isLastPage`
Endpoints and paging follow Atlassian's public REST docs as of 2026-10-01;
re-check them against the live instance when wiring a real project.

Window rule: a PR belongs to [since, until] (whole days, UTC) when it was
created or closed inside it, or is still open and was created by `until`.
Cloud lists no close time, so a merged/declined PR's `updated_on` stands in.

Auth is env-only: BITBUCKET_TOKEN (Bearer: Cloud access token or DC personal
access token), else BITBUCKET_USER + BITBUCKET_APP_PASSWORD (Basic). Stdlib only.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import SourceUnavailable

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "git"))
from commit_msg_ticket import BRANCH_KEY_RE, KEY_RE  # noqa: E402  (one key rule kit-wide)

CLOUD_API = "https://api.bitbucket.org"
CLOUD_STATES = ("MERGED", "OPEN", "DECLINED", "SUPERSEDED")
PAGE_SIZE = 50
DEFAULT_MAX_PAGES = 20
RETRY_STATUSES = {429, 500, 502, 503, 504}


def extract_keys(title: str, branch: str) -> list[str]:
    keys = set(KEY_RE.findall(title or "")) | set(BRANCH_KEY_RE.findall(branch or ""))
    return sorted(keys, key=_natural)


def _natural(key: str):
    prefix, _, num = key.rpartition("-")
    return (prefix, int(num) if num.isdigit() else 0)


def _iso(value) -> str:
    """Cloud ISO strings or DC epoch milliseconds -> 'YYYY-MM-DDTHH:MM:SSZ' (UTC)."""
    if value in (None, ""):
        return ""
    if isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value / 1000, timezone.utc)
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_pr(raw: dict, deployment: str, repo: str) -> dict:
    """One PR -> the snapshot `pull_requests` shape (design §3.2)."""
    if deployment == "cloud":
        state = raw.get("state", "")
        state = "DECLINED" if state == "SUPERSEDED" else state
        source = ((raw.get("source") or {}).get("branch") or {}).get("name", "")
        target = ((raw.get("destination") or {}).get("branch") or {}).get("name", "")
        updated = _iso(raw.get("updated_on"))
        pr = {"author": (raw.get("author") or {}).get("display_name", ""),
              "created": _iso(raw.get("created_on")), "updated": updated,
              "closed": updated if state in ("MERGED", "DECLINED") else "",
              "url": ((raw.get("links") or {}).get("html") or {}).get("href", "")}
    else:
        state = raw.get("state", "")
        source = (raw.get("fromRef") or {}).get("displayId", "")
        target = (raw.get("toRef") or {}).get("displayId", "")
        self_links = (raw.get("links") or {}).get("self") or [{}]
        pr = {"author": ((raw.get("author") or {}).get("user") or {}).get("displayName", ""),
              "created": _iso(raw.get("createdDate")), "updated": _iso(raw.get("updatedDate")),
              "closed": _iso(raw.get("closedDate")) if state in ("MERGED", "DECLINED") else "",
              "url": self_links[0].get("href", "")}
    title = raw.get("title", "") or ""
    return {"repo": repo, "id": raw.get("id"), "title": title, "state": state,
            "source_branch": source, "target_branch": target,
            "keys": extract_keys(title, source), **pr}


def in_window(pr: dict, since: str, until: str) -> bool:
    def inside(ts):
        return bool(ts) and since <= ts[:10] <= until
    if inside(pr["created"]) or inside(pr["closed"]):
        return True
    return pr["state"] == "OPEN" and bool(pr["created"]) and pr["created"][:10] <= until


def _http_get(url, headers, opener=urllib.request.urlopen, sleep=time.sleep, timeout=30):
    """GET JSON with one bounded retry on 429/5xx (honours Retry-After)."""
    for attempt in (1, 2):
        try:
            with opener(urllib.request.Request(url, headers=headers), timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in RETRY_STATUSES and attempt == 1:
                try:
                    wait = float(exc.headers.get("Retry-After") or 2)
                except (TypeError, ValueError):
                    wait = 2.0
                sleep(min(wait, 30.0))
                continue
            raise SourceUnavailable(f"bitbucket: HTTP {exc.code} for {url}") from exc
        except urllib.error.URLError as exc:
            raise SourceUnavailable(f"bitbucket: cannot reach {url}: {exc.reason}") from exc
    raise SourceUnavailable(f"bitbucket: gave up on {url}")  # pragma: no cover


def _auth_headers(env) -> dict:
    token = env.get("BITBUCKET_TOKEN")
    if token:
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    user, password = env.get("BITBUCKET_USER"), env.get("BITBUCKET_APP_PASSWORD")
    if user and password:
        basic = base64.b64encode(f"{user}:{password}".encode()).decode()
        return {"Authorization": f"Basic {basic}", "Accept": "application/json"}
    raise SourceUnavailable("bitbucket: set BITBUCKET_TOKEN, or BITBUCKET_USER + BITBUCKET_APP_PASSWORD")


def _pages(cfg: dict, base: str, repo: str, since: str, http_get, headers, max_pages: int):
    if cfg["deployment"] == "cloud":
        params = [("state", s) for s in CLOUD_STATES] + [
            ("pagelen", PAGE_SIZE), ("q", f"updated_on >= {since}T00:00:00+00:00")]
        url = (f"{base}/2.0/repositories/{urllib.parse.quote(cfg['workspace'])}/"
               f"{urllib.parse.quote(repo)}/pullrequests?{urllib.parse.urlencode(params)}")
        for _ in range(max_pages):
            page = http_get(url, headers)
            yield page.get("values", [])
            url = page.get("next")
            if not url:
                return
    else:
        start = 0
        for _ in range(max_pages):
            qs = urllib.parse.urlencode({"state": "ALL", "order": "NEWEST", "limit": PAGE_SIZE, "start": start})
            page = http_get(f"{base}/rest/api/1.0/projects/{urllib.parse.quote(cfg['project'])}/repos/"
                            f"{urllib.parse.quote(repo)}/pull-requests?{qs}", headers)
            yield page.get("values", [])
            if page.get("isLastPage", True) or page.get("nextPageStart") is None:
                return
            start = page["nextPageStart"]


def fetch(deck_cfg: dict, since: str, until: str, http_get=None, env=None):
    """PRs in [since, until] across the configured repos. Returns (prs, source_meta)."""
    cfg = deck_cfg.get("bitbucket") or {}
    deployment = cfg.get("deployment")
    if deployment not in ("cloud", "datacenter") or not cfg.get("repos"):
        raise SourceUnavailable("bitbucket: no deployment/repos in decks.config.json")
    owner_key = "workspace" if deployment == "cloud" else "project"
    if not cfg.get(owner_key):
        raise SourceUnavailable(f"bitbucket: `{owner_key}` missing in decks.config.json")
    env = os.environ if env is None else env
    headers = _auth_headers(env)
    # Cloud only reads a base-URL variable when the config names one explicitly,
    # so a Data Center BITBUCKET_BASE_URL in the same shell can't redirect it.
    base_env = cfg.get("base_url_env") or ("" if deployment == "cloud" else "BITBUCKET_BASE_URL")
    base = (env.get(base_env) if base_env else "") or (CLOUD_API if deployment == "cloud" else "")
    if not base:
        raise SourceUnavailable(f"bitbucket: set {base_env} to the Data Center base URL")
    base = base.rstrip("/")
    http_get = http_get or _http_get
    max_pages = int(cfg.get("max_pages", DEFAULT_MAX_PAGES))
    prs = []
    for repo in cfg["repos"]:
        for values in _pages(cfg, base, repo, since, http_get, headers, max_pages):
            prs += [p for p in (normalize_pr(v, deployment, repo) for v in values)
                    if in_window(p, since, until)]
    prs.sort(key=lambda p: (p["repo"], p["id"] if isinstance(p["id"], int) else 0))
    return prs, {"tier": "script", "deployment": deployment, "repos": list(cfg["repos"]),
                 "count": len(prs), "window": [since, until]}
