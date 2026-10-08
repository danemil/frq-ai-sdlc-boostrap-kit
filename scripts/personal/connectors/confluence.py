"""Confluence (Cloud and Data Center), read-only: who you are, a page, a CQL or text search.

Cloud (`*.atlassian.net`) signs in with email + API token (Basic) and lives under
`/wiki`; Data Center signs in with a personal access token (Bearer) under the saved
URL, which may carry a context path such as `/confluence`. Cloud reads pages with the
v2 API, Data Center with the content API; search is CQL on both.
"""
from __future__ import annotations

import re

from personal.connectors import http, text
from personal.connectors.registry import Command, Field, Result

TITLE = "Confluence"
FIELDS = [
    Field("url", "Confluence URL, e.g. https://confluence.example.com or "
                 "https://example.atlassian.net/wiki"),
    Field("email", "Atlassian account email", identity=True,
          when=lambda values: http.atlassian_kind(values.get("url", "")) == "cloud"),
    Field("token", "API token (Cloud) or personal access token (Data Center)", secret=True),
]

PAGE_MAX_CHARS = 20000
EXCERPT_CHARS = 300
_CQL_MARKERS = ("=", "~", " AND ", " OR ", " ORDER BY ", " IN (")
_ORDER_BY = re.compile(r"\s+ORDER\s+BY\s+", re.IGNORECASE)
_HIGHLIGHT = re.compile(r"@@@(end)?hl@@@")


def kind(values) -> str:
    return http.atlassian_kind(values.get("url", ""))


def auth(values) -> http.Auth:
    if kind(values) == "cloud":
        return http.basic(values.get("email", ""), values["token"])
    return http.bearer(values["token"])


# --- helpers ------------------------------------------------------------------------

def _root(ctx) -> str:
    """The API root, relative to the saved URL: "/wiki" on Cloud unless the URL already
    ends in /wiki; "" on Data Center (the saved URL holds any context path)."""
    if ctx.kind == "cloud" and not ctx.client.base_url.endswith("/wiki"):
        return "/wiki"
    return ""


def _site(ctx) -> str:
    """The site's browser root (with /wiki on Cloud)."""
    return ctx.client.base_url + _root(ctx)


def _web(ctx, links, base=None) -> str | None:
    """A browser link from `_links`: its base (or `base`, else the site root) + webui."""
    links = links or {}
    webui = links.get("webui")
    root = (links.get("base") or base or _site(ctx)).rstrip("/")
    if not webui:
        return root
    if webui.startswith(("http://", "https://")):
        return webui
    return root + "/" + webui.lstrip("/")


def _quote(value) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _is_cql(query) -> bool:
    upper = query.upper()
    return any(m in upper for m in _CQL_MARKERS)


def build_cql(query, space=None) -> str:
    """`query` as is when it looks like CQL, else a page text search; `space` narrows it."""
    query = (query or "").strip()
    if not _is_cql(query):
        cql = f"text ~ {_quote(query)} AND type = page"
        return cql + (f" AND space = {_quote(space)}" if space else "")
    if not space:
        return query
    # The space goes before any ORDER BY, and the user's CQL is kept as one group.
    head, order = (_ORDER_BY.split(query, maxsplit=1) + [""])[:2]
    cql = f"({head.strip()}) AND space = {_quote(space)}"
    return cql + (f" ORDER BY {order.strip()}" if order else "")


# --- commands -----------------------------------------------------------------------

def _whoami(ctx, args) -> Result:
    me = ctx.client.get_json(f"{_root(ctx)}/rest/api/user/current")
    if not isinstance(me, dict) or me.get("type") == "anonymous":
        raise http.ConnectorError(f"{ctx.client.host} treated you as anonymous: the "
                                  "credentials were not accepted.", "unauthorized", 401)
    user = me.get("accountId") if ctx.kind == "cloud" else me.get("username")
    return Result(item={"user": user or "", "display_name": me.get("displayName") or "",
                        "email": me.get("email") or None, "kind": ctx.kind,
                        "url": _site(ctx)})


def _page_args(p):
    p.add_argument("id", help="the page id (the number in the page's URL)")
    p.add_argument("--format", choices=("text", "storage"), default="text",
                   help="readable text (default) or the raw storage format")
    p.add_argument("--max-chars", type=int, default=PAGE_MAX_CHARS,
                   help=f"clip the body to this many characters (default {PAGE_MAX_CHARS})")


def _page(ctx, args) -> Result:
    if ctx.kind == "cloud":
        data = ctx.client.get_json(f"{_root(ctx)}/api/v2/pages/{args.id}",
                                   {"body-format": "storage"})
        space = data.get("spaceId")
        updated = http.dig(data, "version.createdAt")
    else:
        data = ctx.client.get_json(f"/rest/api/content/{args.id}",
                                   {"expand": "body.storage,version,space"})
        space = http.dig(data, "space.key")
        updated = http.dig(data, "version.when")
    storage = http.dig(data, "body.storage.value") or ""
    body = text.html_to_text(storage) if args.format == "text" else storage
    limit = max(1, args.max_chars)
    truncated = len(body) > limit
    body = body[:limit] if truncated else body
    item = {"id": str(data.get("id", args.id)), "title": data.get("title"),
            "space": space, "version": http.dig(data, "version.number"), "updated": updated,
            "body": body, "body_truncated": truncated, "url": _web(ctx, data.get("_links"))}
    head = [f"{item['title']}  {item['url']}",
            f"space: {space or ''}  version: {item['version'] or ''}  "
            f"updated: {updated or ''}", ""]
    tail = ["", f"(body clipped at {limit} characters: raise --max-chars)"] if truncated else []
    return Result(item=item, lines=head + body.splitlines() + tail)


def _search_args(p):
    p.add_argument("query", help='CQL (e.g. \'space = ENG AND title ~ "release"\') or plain '
                                 'words to find in pages')
    p.add_argument("--space", metavar="KEY", help="only this space")
    p.add_argument("--limit", type=int, default=25, help="at most this many results "
                                                         "(default 25, max 1000)")


def _excerpt(raw) -> str | None:
    if not raw:
        return None
    return text.clip(text.html_to_text(_HIGHLIGHT.sub("", raw)), EXCERPT_CHARS)


def _search(ctx, args) -> Result:
    cql = build_cql(args.query, args.space)
    limit = max(1, min(args.limit, 1000))
    if ctx.kind == "cloud":
        path = f"{_root(ctx)}/rest/api/search"
        params = {"cql": cql, "expand": "content.space,content.version"}
    else:
        path = "/rest/api/content/search"
        params = {"cql": cql, "expand": "space,version"}
    # Paging follows _links.next; the base of each page is the site root.
    raw, truncated = ctx.client.paginate(path, params, items="results",
                                         paging=http.LinkPaging(), limit=limit, page_size=50)
    items = []
    for r in raw:
        content = r.get("content") if ctx.kind == "cloud" and isinstance(r.get("content"),
                                                                            dict) else r
        updated = (r.get("lastModified") if ctx.kind == "cloud" else None) \
            or http.dig(content, "version.when")
        links = dict(content.get("_links") or {})
        if not links.get("webui") and r.get("url"):
            links["webui"] = r["url"]
        items.append({"id": str(content.get("id")) if content.get("id") is not None else None,
                      "type": content.get("type") or r.get("entityType"),
                      "title": content.get("title") or r.get("title"),
                      "space": http.dig(content, "space.key"),
                      "updated": updated,
                      "excerpt": _excerpt(r.get("excerpt")) if ctx.kind == "cloud" else None,
                      "url": _web(ctx, links)})
    return Result(items=items, truncated=truncated, extra={"cql": cql})


WHOAMI = Command("who you are signed in as", run=_whoami)
COMMANDS = {
    "page": Command("one page as readable text (or raw storage format)", run=_page,
                    args=_page_args),
    "search": Command("find pages with CQL or plain words", run=_search, args=_search_args),
}
