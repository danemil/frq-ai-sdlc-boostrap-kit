"""Bitbucket Data Center (REST 1.0), read-only: who you are, pull requests, branches.

Auth is `Bearer <HTTP access token>` (personal, project or repository token).
Bitbucket Cloud (bitbucket.org) is refused by `check`: it is out of scope.
Repositories are named `<project>/<repo>`, pull requests `<project>/<repo>/<id>`.
Times come from epoch milliseconds as ISO-8601 UTC.
"""
from __future__ import annotations

import argparse
import urllib.parse

from personal.connectors import http, text
from personal.connectors.registry import Command, Field, Result

TITLE = "Bitbucket"
FIELDS = [
    Field("url", "Bitbucket URL, e.g. https://bitbucket.example.com"),
    Field("token", "HTTP access token (personal, project or repository)", secret=True),
]

API = "/rest/api/1.0"
MAX_LIMIT = 1000
STATES = ("OPEN", "MERGED", "DECLINED", "ALL")
CLOUD_MESSAGE = ("Bitbucket Cloud is not supported yet; this connector is for Bitbucket "
                 "Data Center.")


def kind(values) -> str:
    return "dc"


def auth(values) -> http.Auth:
    return http.bearer(values["token"])


def check(values):
    host = (urllib.parse.urlsplit(values.get("url") or "").hostname or "").lower()
    if host == "bitbucket.org" or host.endswith(".bitbucket.org"):
        return CLOUD_MESSAGE
    return None


# --- helpers ------------------------------------------------------------------

def _q(segment) -> str:
    return urllib.parse.quote(str(segment), safe="")


def _parse(ref, with_id=False):
    """(project, repo) or (project, repo, id) from 'P/r' or 'P/r/id'."""
    parts = (ref or "").strip().split("/")
    want = 3 if with_id else 2
    form = "<project>/<repo>/<id>" if with_id else "<project>/<repo>"
    if len(parts) != want or not all(parts) or (with_id and not parts[2].isdigit()):
        raise http.ConnectorError(f"'{ref}' is not of the form {form} "
                                  f"(e.g. {'PRJ/my-repo/42' if with_id else 'PRJ/my-repo'}).",
                                  "config")
    return tuple(parts[:2]) + ((int(parts[2]),) if with_id else ())


def _prefix(project, repo) -> str:
    return f"{API}/projects/{_q(project)}/repos/{_q(repo)}"


def _name(user):
    user = user or {}
    return user.get("displayName") or user.get("name") or None


def _pr_url(ctx, raw, project, repo):
    links = ((raw.get("links") or {}).get("self") or [{}])
    href = (links[0] or {}).get("href") if links else None
    return href or ctx.client.web_url(
        f"projects/{_q(project)}/repos/{_q(repo)}/pull-requests/{raw.get('id')}")


def _pr(ctx, raw, project, repo) -> dict:
    return {
        "id": raw.get("id"),
        "title": raw.get("title"),
        "state": raw.get("state"),
        "author": _name((raw.get("author") or {}).get("user")),
        "reviewers": [{"name": _name(r.get("user")), "status": r.get("status")}
                      for r in raw.get("reviewers") or []],
        "from_branch": (raw.get("fromRef") or {}).get("displayId"),
        "to_branch": (raw.get("toRef") or {}).get("displayId"),
        "created": text.iso_from_ms(raw.get("createdDate")),
        "updated": text.iso_from_ms(raw.get("updatedDate")),
        "url": _pr_url(ctx, raw, project, repo),
    }


def _limit(value) -> int:
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number") from None
    if not 1 <= n <= MAX_LIMIT:
        raise argparse.ArgumentTypeError(f"must be between 1 and {MAX_LIMIT}")
    return n


def _positive(value) -> int:
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number") from None
    if n < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return n


# --- commands -------------------------------------------------------------------

def _whoami(ctx, args) -> Result:
    resp = ctx.client.get(f"{API}/projects", {"limit": 1})
    slug = (resp.headers.get("X-AUSERNAME") or "").strip() if resp.headers else ""
    if not slug:
        raise http.ConnectorError(
            f"Bitbucket did not say who you are ({ctx.client.host} sent no X-AUSERNAME "
            "header): the token may be missing, expired or not accepted.", "unauthorized")
    try:
        me = ctx.client.get_json(f"{API}/users/{_q(slug)}") or {}
    except http.ConnectorError as exc:
        if exc.kind != "not_found":
            raise
        me = {}
    return Result(item={
        "user": slug,
        "display_name": me.get("displayName") or slug,
        "email": me.get("emailAddress") or None,
        "url": ctx.client.web_url(f"users/{_q(slug)}"),
    })


def _prs_args(p):
    p.add_argument("repo", help="<project>/<repo>")
    p.add_argument("--state", type=str.upper, choices=STATES, default="OPEN")
    p.add_argument("--limit", type=_limit, default=25, help="at most this many (max 1000)")


def _prs(ctx, args) -> Result:
    project, repo = _parse(args.repo)
    raw, truncated = ctx.client.paginate(
        f"{_prefix(project, repo)}/pull-requests", {"state": args.state, "order": "NEWEST"},
        items="values", paging=http.BitbucketPaging(), limit=args.limit)
    return Result(items=[_pr(ctx, r, project, repo) for r in raw], truncated=truncated)


def _pr_args(p):
    p.add_argument("ref", help="<project>/<repo>/<id>")
    p.add_argument("--diff", action="store_true", help="include the raw diff")
    p.add_argument("--comments", action="store_true", help="include the comments")
    p.add_argument("--max-diff-bytes", type=_positive, default=200000,
                   help="clip the diff at this many bytes (default 200000)")


def _comment(raw_act, pr_url) -> dict:
    c = raw_act.get("comment") or {}
    anchor = raw_act.get("commentAnchor") or c.get("anchor") or {}
    return {
        "id": c.get("id"),
        "author": _name(c.get("author") or raw_act.get("user")),
        "text": c.get("text"),
        "created": text.iso_from_ms(c.get("createdDate") or raw_act.get("createdDate")),
        "path": anchor.get("path") or None,
        "line": anchor.get("line") if anchor.get("line") is not None else None,
        "url": f"{pr_url}/overview?commentId={c.get('id')}",
    }


def _pr_cmd(ctx, args) -> Result:
    project, repo, pr_id = _parse(args.ref, with_id=True)
    base = f"{_prefix(project, repo)}/pull-requests/{pr_id}"
    raw = ctx.client.get_json(base) or {}
    item = _pr(ctx, raw, project, repo)
    item["description"] = raw.get("description") or None
    if args.diff:
        diff, cut = ctx.client.get_text(f"{base}.diff", accept="text/plain",
                                        max_bytes=args.max_diff_bytes)
        item["diff"], item["diff_truncated"] = diff, cut
    if args.comments:
        acts, cut = ctx.client.paginate(f"{base}/activities", items="values",
                                        paging=http.BitbucketPaging(), limit=500)
        item["comments"] = [_comment(a, item["url"]) for a in acts
                            if a.get("action") == "COMMENTED" and a.get("comment")]
        item["comments_truncated"] = cut
    return Result(item=item)


def _branches_args(p):
    p.add_argument("repo", help="<project>/<repo>")
    p.add_argument("--filter", default=None, help="only branches whose name contains this")
    p.add_argument("--limit", type=_limit, default=50, help="at most this many (max 1000)")


def _branches(ctx, args) -> Result:
    project, repo = _parse(args.repo)
    raw, truncated = ctx.client.paginate(
        f"{_prefix(project, repo)}/branches",
        {"filterText": args.filter or None, "orderBy": "MODIFICATION"},
        items="values", paging=http.BitbucketPaging(), limit=args.limit)
    items = [{
        "name": b.get("displayId"),
        "id": b.get("id"),
        "latest_commit": b.get("latestCommit"),
        "is_default": bool(b.get("isDefault")),
        "url": ctx.client.web_url(f"projects/{_q(project)}/repos/{_q(repo)}/browse"
                                  f"?at={_q(b.get('id') or '')}"),
    } for b in raw]
    return Result(items=items, truncated=truncated)


WHOAMI = Command("who you are signed in as", run=_whoami)
COMMANDS = {
    "prs": Command("pull requests of a repository (newest first)", run=_prs, args=_prs_args),
    "pr": Command("one pull request, optionally with its diff and comments", run=_pr_cmd,
                  args=_pr_args),
    "branches": Command("branches of a repository (recently changed first)", run=_branches,
                        args=_branches_args),
}
