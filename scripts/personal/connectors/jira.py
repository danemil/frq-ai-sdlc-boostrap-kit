"""Jira (Cloud and Data Center), read-only: who you are, JQL search, one issue (with its
links and change history), and a board's sprints.

Cloud (*.atlassian.net) uses REST v3 with Basic email:API-token; Data Center uses REST v2
with a personal access token (Bearer). Agile (boards, sprints) is /rest/agile/1.0 on both.
Every item carries the browser `url` it came from.
"""
from __future__ import annotations

import urllib.parse
from datetime import datetime

from personal.connectors import http, text
from personal.connectors.registry import Command, Field, Result

TITLE = "Jira"

MAX_LIMIT = 1000
DESCRIPTION_CHARS = 4000
BASE_FIELDS = ["summary", "issuetype", "status", "assignee", "priority", "updated"]
ISSUE_FIELDS = ["summary", "issuetype", "status", "assignee", "reporter", "priority", "labels",
                "created", "updated", "resolution", "parent", "description", "components",
                "fixVersions", "issuelinks"]


def _is_cloud_url(values) -> bool:
    return http.atlassian_kind(values.get("url", "")) == "cloud"


FIELDS = [
    Field("url", "Jira URL, e.g. https://jira.example.com or https://example.atlassian.net"),
    Field("email", "Atlassian account email", identity=True, when=_is_cloud_url),
    Field("token", "API token (Cloud) or personal access token (Data Center)", secret=True),
]


def kind(values) -> str:
    return http.atlassian_kind(values.get("url", ""))


def auth(values) -> http.Auth:
    if kind(values) == "cloud":
        return http.basic(values.get("email", ""), values.get("token", ""))
    return http.bearer(values.get("token", ""))


# --- helpers -------------------------------------------------------------------------

def _cloud(ctx) -> bool:
    return ctx.kind == "cloud"


def _api(ctx) -> str:
    return "/rest/api/3" if _cloud(ctx) else "/rest/api/2"


def _q(segment) -> str:
    return urllib.parse.quote(str(segment), safe="")


def _limit(n) -> int:
    return max(1, min(int(n), MAX_LIMIT))


def _name(obj, key="name"):
    """obj[key] when obj is a dict (status, priority, ...), else None."""
    return obj.get(key) if isinstance(obj, dict) else None


def _person(obj):
    if not isinstance(obj, dict):
        return None
    return obj.get("displayName") or obj.get("name") or obj.get("accountId")


def _issue_url(ctx, key) -> str:
    return ctx.client.web_url(f"browse/{key}")


def _when(stamp):
    """A sort key for Jira times ('2026-09-01T10:00:00.000+0000'); unparsable last."""
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return (0, datetime.strptime(str(stamp), fmt).timestamp(), "")
        except (TypeError, ValueError):
            continue
    return (1, 0.0, str(stamp))


# --- whoami ---------------------------------------------------------------------------

def _whoami(ctx, args) -> Result:
    me = ctx.client.get_json(f"{_api(ctx)}/myself") or {}
    if _cloud(ctx):
        user = me.get("accountId") or ""
        url = ctx.client.web_url("jira/people/" + urllib.parse.quote(user, safe=":"))
    else:
        user = me.get("name") or me.get("key") or ""
        url = ctx.client.web_url("secure/ViewProfile.jspa?name=" + urllib.parse.quote(user))
    return Result(item={"user": user, "display_name": me.get("displayName") or user,
                        "email": me.get("emailAddress") or None, "kind": ctx.kind or "dc",
                        "url": url})


# --- search ---------------------------------------------------------------------------

def _search_args(p):
    p.add_argument("jql", help="a JQL query, e.g. 'project = ABC ORDER BY updated DESC'")
    p.add_argument("--limit", type=int, default=50, help="most issues to return (max 1000)")
    p.add_argument("--fields", default="", help="extra field ids, comma-separated "
                   "(e.g. customfield_10016,duedate)")


def _search(ctx, args) -> Result:
    extra = [f.strip() for f in (args.fields or "").split(",") if f.strip()]
    fields = BASE_FIELDS + [f for f in extra if f not in BASE_FIELDS]
    params = {"jql": args.jql, "fields": ",".join(fields)}
    if _cloud(ctx):
        # /search/jql pages with a cursor and ignores startAt: never mix the two styles.
        raw, truncated = ctx.client.paginate("/rest/api/3/search/jql", params, items="issues",
                                             paging=http.TokenPaging(),
                                             limit=_limit(args.limit), page_size=100)
    else:
        params["startAt"] = 0
        raw, truncated = ctx.client.paginate("/rest/api/2/search", params, items="issues",
                                             paging=http.Offset(), limit=_limit(args.limit),
                                             page_size=100)
    items = []
    for issue in raw:
        f = issue.get("fields") or {}
        item = {"key": issue.get("key"), "summary": f.get("summary"),
                "type": _name(f.get("issuetype")), "status": _name(f.get("status")),
                "assignee": _person(f.get("assignee")), "priority": _name(f.get("priority")),
                "updated": f.get("updated"), "url": _issue_url(ctx, issue.get("key"))}
        if extra:
            item["fields"] = {k: f.get(k) for k in extra}
        items.append(item)
    return Result(items=items, truncated=truncated)


# --- issue ----------------------------------------------------------------------------

def _issue_args(p):
    p.add_argument("key", help="issue key, e.g. ABC-123")
    p.add_argument("--changelog", action="store_true", help="add the change history")
    p.add_argument("--links", action="store_true", help="add the linked issues")


def _description(value):
    if value in (None, ""):
        return None
    flat = text.adf_to_text(value) if isinstance(value, dict) else str(value)
    return text.clip(flat, DESCRIPTION_CHARS)


def _links(ctx, raw_links) -> list:
    out = []
    for link in raw_links or []:
        kind_ = link.get("type") or {}
        if link.get("outwardIssue"):
            direction, other = "outward", link["outwardIssue"]
        elif link.get("inwardIssue"):
            direction, other = "inward", link["inwardIssue"]
        else:
            continue
        f = other.get("fields") or {}
        out.append({"type": kind_.get("name"), "direction": direction,
                    "relation": kind_.get(direction), "key": other.get("key"),
                    "summary": f.get("summary"), "status": _name(f.get("status")),
                    "url": _issue_url(ctx, other.get("key"))})
    return out


def _changes(histories) -> list:
    entries = []
    for h in sorted(histories or [], key=lambda h: _when(h.get("created"))):
        for change in h.get("items") or []:
            entries.append({"at": h.get("created"), "author": _person(h.get("author")),
                            "field": change.get("field"), "from": change.get("fromString"),
                            "to": change.get("toString")})
    return entries


def _issue(ctx, args) -> Result:
    key = args.key.strip()
    path = f"{_api(ctx)}/issue/{_q(key)}"
    params = {"fields": ",".join(ISSUE_FIELDS)}
    if args.changelog and not _cloud(ctx):
        params["expand"] = "changelog"
    raw = ctx.client.get_json(path, params) or {}
    f = raw.get("fields") or {}
    key = raw.get("key") or key
    item = {"key": key, "summary": f.get("summary"), "type": _name(f.get("issuetype")),
            "status": _name(f.get("status")), "assignee": _person(f.get("assignee")),
            "reporter": _person(f.get("reporter")), "priority": _name(f.get("priority")),
            "labels": list(f.get("labels") or []),
            "components": [c.get("name") for c in f.get("components") or []],
            "fix_versions": [v.get("name") for v in f.get("fixVersions") or []],
            "created": f.get("created"), "updated": f.get("updated"),
            "resolution": _name(f.get("resolution")), "parent": _name(f.get("parent"), "key"),
            "description": _description(f.get("description")),
            "url": _issue_url(ctx, key)}
    if args.links:
        item["links"] = _links(ctx, f.get("issuelinks"))
    if args.changelog:
        if _cloud(ctx):
            histories, _ = ctx.client.paginate(f"{path}/changelog", items="values",
                                               paging=http.Offset(last="isLast"),
                                               limit=MAX_LIMIT, page_size=100)
        else:
            histories = http.dig(raw, "changelog.histories") or []
        item["changelog"] = _changes(histories)
    return Result(item=item)


# --- sprints --------------------------------------------------------------------------

def _sprints_args(p):
    p.add_argument("board", type=int, help="board id (the rapidView number in a board URL)")
    p.add_argument("--state", default="active,future",
                   help="comma-separated: active, future, closed (default active,future)")
    p.add_argument("--limit", type=int, default=50, help="most sprints to return (max 1000)")


def _sprints(ctx, args) -> Result:
    params = {"state": args.state, "startAt": 0}
    raw, truncated = ctx.client.paginate(f"/rest/agile/1.0/board/{args.board}/sprint", params,
                                         items="values", paging=http.Offset(last="isLast"),
                                         limit=_limit(args.limit), page_size=50)
    items = [{"id": s.get("id"), "name": s.get("name"), "state": s.get("state"),
              "start": s.get("startDate"), "end": s.get("endDate"),
              "complete": s.get("completeDate"), "goal": s.get("goal") or None,
              "board": args.board,
              "url": ctx.client.web_url(f"secure/RapidBoard.jspa?rapidView={args.board}"
                                        f"&sprint={s.get('id')}")}
             for s in raw]
    return Result(items=items, truncated=truncated)


WHOAMI = Command("who you are signed in as", run=_whoami)
COMMANDS = {
    "search": Command("issues matching a JQL query", run=_search, args=_search_args),
    "issue": Command("one issue, optionally with its links and change history", run=_issue,
                     args=_issue_args),
    "sprints": Command("a board's sprints (active and future by default)", run=_sprints,
                       args=_sprints_args),
}
