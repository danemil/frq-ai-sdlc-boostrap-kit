"""Jama Connect (read-only): items, search, relationships and test runs over REST v1.

Auth is OAuth2 client credentials: an API client's ID and secret are exchanged once per
run for an access token (POST <url>/rest/oauth/token, inside http.OAuthClientCredentials),
then every read is a GET with that bearer token. Lists page with startAt/maxResults
(50 at most per page) and meta.pageInfo.totalResults.

Item links follow Jama's documented form <url>/perspective.req#/items/<id>?projectId=<p>.
Test-run field names (testRunStatus, testCase, testCycle, executionDate, assignedTo)
can be renamed per Jama configuration: confirm them on a live instance.
"""
from __future__ import annotations

import argparse

from . import http, text
from .registry import Command, Field, Result

TITLE = "Jama"
FIELDS = [
    Field("url", "Jama URL, e.g. https://example.jamacloud.com"),
    Field("client_id", "API client ID", identity=True),
    Field("client_secret", "API client secret", secret=True),
]

API = "/rest/v1"
PAGE = 50                     # Jama's maximum page size
MAX_LIMIT = 1000
DESCRIPTION_CHARS = 4000
PAGING = http.Offset(start="startAt", size="maxResults", total="meta.pageInfo.totalResults")


def auth(values) -> http.Auth:
    return http.oauth_client_credentials(values["client_id"], values["client_secret"])


def kind(values) -> str:
    return ""


# --- helpers ------------------------------------------------------------------------

def _limit(value) -> int:
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {value}") from None
    if n < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return min(n, MAX_LIMIT)


def _item_url(ctx, item_id, project=None) -> str:
    path = f"perspective.req#/items/{item_id}"
    if project not in (None, ""):
        path += f"?projectId={project}"
    return ctx.client.web_url(path)


def _name(raw) -> str | None:
    return http.dig(raw, "fields.name")


def _list(ctx, path, params, limit):
    return ctx.client.paginate(path, {PAGING.start: 0, **params}, items="data", paging=PAGING,
                               limit=limit, page_size=PAGE)


def _pages_with_linked(ctx, path, params, limit):
    """(rows, linked items by id, truncated): like Client.paginate, but keeps each page's
    `linked.items` (what `include=` adds), which paginate does not return."""
    params = {PAGING.start: 0, **params}
    rows, linked = [], {}
    while True:
        params[PAGING.size] = max(1, min(PAGE, limit - len(rows)))
        data = ctx.client.get_json(path, params)
        if not isinstance(data, dict):
            return rows, linked, False
        batch = data.get("data") or []
        linked.update(http.dig(data, "linked.items") or {})
        room = limit - len(rows)
        rows.extend(batch[:room])
        nxt = PAGING.next(data, params, len(batch))
        if len(rows) >= limit:
            return rows, linked, bool(nxt) or len(batch) > room
        if not nxt or not batch:
            return rows, linked, False
        params = nxt[1]


# --- commands -----------------------------------------------------------------------

def _whoami(ctx, args) -> Result:
    me = ctx.client.get_json(f"{API}/users/current").get("data") or {}
    name = " ".join(p for p in (me.get("firstName"), me.get("lastName")) if p)
    return Result(item={"user": me.get("username", ""), "display_name": name,
                        "email": me.get("email"), "id": me.get("id"),
                        "url": ctx.client.base_url})


def _id_arg(p):
    p.add_argument("id", help="the item's API id (the number in its URL)")


def _item(ctx, args) -> Result:
    raw = ctx.client.get_json(f"{API}/items/{args.id}").get("data") or {}
    fields = raw.get("fields") or {}
    desc = text.clip(text.html_to_text(fields.get("description")), DESCRIPTION_CHARS)
    return Result(item={
        "id": raw.get("id"), "key": raw.get("documentKey"), "global_id": raw.get("globalId"),
        "name": fields.get("name"), "type_id": raw.get("itemType"),
        "project_id": raw.get("project"), "created": raw.get("createdDate"),
        "modified": raw.get("modifiedDate"), "description": desc,
        "fields": {k: v for k, v in fields.items() if k not in ("name", "description")},
        "url": _item_url(ctx, raw.get("id", args.id), raw.get("project"))})


def _search_args(p):
    p.add_argument("text", help="words the items contain")
    p.add_argument("--project", help="project id")
    p.add_argument("--type", help="item type id")
    p.add_argument("--limit", type=_limit, default=50)


def _search(ctx, args) -> Result:
    params = {"contains": args.text, "project": args.project, "itemType": args.type}
    raw, truncated = _list(ctx, f"{API}/abstractitems", params, args.limit)
    items = [{"id": r.get("id"), "key": r.get("documentKey"), "name": _name(r),
              "type_id": r.get("itemType"), "project_id": r.get("project"),
              "modified": r.get("modifiedDate"),
              "url": _item_url(ctx, r.get("id"), r.get("project"))} for r in raw]
    return Result(items=items, truncated=truncated)


def _relationships_args(p):
    _id_arg(p)
    p.add_argument("--direction", choices=("up", "down", "both"), default="both")
    p.add_argument("--limit", type=_limit, default=200)


def _end(ctx, item_id, linked) -> dict:
    raw = linked.get(str(item_id)) or {}
    return {"id": item_id, "key": raw.get("documentKey"), "name": _name(raw),
            "url": _item_url(ctx, item_id, raw.get("project"))}


def _relationships(ctx, args) -> Result:
    wanted = {"up": ["upstream"], "down": ["downstream"],
              "both": ["upstream", "downstream"]}[args.direction]
    params = {"include": ["data.fromItem", "data.toItem"]}
    items, truncated = [], False
    for direction in wanted:
        room = args.limit - len(items)
        if room <= 0:
            truncated = True              # the other direction was not read
            break
        rows, linked, more = _pages_with_linked(
            ctx, f"{API}/items/{args.id}/{direction}relationships", params, room)
        truncated = truncated or more
        for r in rows:
            frm, to = _end(ctx, r.get("fromItem"), linked), _end(ctx, r.get("toItem"), linked)
            other = frm if direction == "upstream" else to
            items.append({"id": r.get("id"), "direction": direction,
                          "type_id": r.get("relationshipType"), "suspect": r.get("suspect"),
                          "from": frm, "to": to, "url": other["url"]})
    return Result(items=items, truncated=truncated)


def _testruns_args(p):
    which = p.add_mutually_exclusive_group(required=True)
    which.add_argument("--cycle", help="test cycle id")
    which.add_argument("--plan", help="test plan id (all its cycles)")
    p.add_argument("--limit", type=_limit, default=200)


def _run_item(ctx, r) -> dict:
    f = r.get("fields") or {}
    return {"id": r.get("id"), "key": r.get("documentKey"), "name": f.get("name"),
            "status": f.get("testRunStatus"), "test_case_id": f.get("testCase"),
            "cycle_id": f.get("testCycle"), "executed": f.get("executionDate"),
            "assigned_to": f.get("assignedTo"),
            "url": _item_url(ctx, r.get("id"), r.get("project"))}


def _testruns(ctx, args) -> Result:
    if args.cycle:
        cycles = [args.cycle]
    else:
        raw, _ = _list(ctx, f"{API}/testplans/{args.plan}/testcycles", {}, MAX_LIMIT)
        cycles = [c.get("id") for c in raw]
    runs, truncated = [], False
    for cycle in cycles:
        room = args.limit - len(runs)
        if room <= 0:
            truncated = True              # cycles left unread
            break
        raw, more = _list(ctx, f"{API}/testcycles/{cycle}/testruns", {}, room)
        runs.extend(raw)
        if more:
            truncated = True
            break
    return Result(items=[_run_item(ctx, r) for r in runs], truncated=truncated)


WHOAMI = Command("who you are signed in as (the API client's user)", run=_whoami)
COMMANDS = {
    "item": Command("one item: fields, description and link", run=_item, args=_id_arg),
    "search": Command("items containing some text", run=_search, args=_search_args),
    "relationships": Command("an item's upstream and downstream relationships",
                             run=_relationships, args=_relationships_args),
    "testruns": Command("test runs of a test cycle or of a test plan's cycles",
                        run=_testruns, args=_testruns_args),
}
