"""Artifactory (read-only): which versions the company mirror has, for Maven, npm and Go.

Auth is `Authorization: Bearer <token>` (an access token or an identity token). Only
GET requests are sent; AQL is never used, because an AQL search is a POST.

- `whoami` reads the user name from the token itself when it is a JWT (its `sub` claim,
  `jfrt@<service>/users/<name>`), then confirms the token with `GET /api/system/version`.
  A reference token (not a JWT) gives no user name but still passes when the GET passes.
- `versions` reads `maven-metadata.xml` with the standard library's XML parser; a file
  with a DOCTYPE or an entity declaration is refused (no entity expansion, ever).
- The repository is `--repo`, else the saved default (`maven_repo`, `npm_repo`,
  `go_repo`), else a plain error.
- Item links point at the web UI, which lives at the host root:
  `<host>/ui/repos/tree/General/<repo>/<path>` (the saved URL without `/artifactory`).
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import xml.etree.ElementTree as ET

from . import http
from .registry import Command, Field, Result

TITLE = "Artifactory"
FIELDS = [
    Field("url", "Artifactory URL with /artifactory, e.g. "
                 "https://artifactory.example.com/artifactory"),
    Field("token", "Access token or identity token (your profile → Generate an Identity "
                   "Token)", secret=True),
    Field("maven_repo", "Default Maven repository key, e.g. maven-virtual (Enter to skip)",
          required=False),
    Field("npm_repo", "Default npm repository key, e.g. npm-virtual (Enter to skip)",
          required=False),
    Field("go_repo", "Default Go repository key, e.g. go-virtual (Enter to skip)",
          required=False),
]

CONTEXT = "/artifactory"
MAX_LIMIT = 1000
METADATA_BYTES = 2_000_000
NO_REPO = ("Give --repo, or save a default with connect artifactory "
           "(the repo key, e.g. maven-virtual).")
BAD_COORDS = "Give group:artifact, e.g. org.apache.commons:commons-text"

_NAME = re.compile(r"^[A-Za-z0-9_.\-]+$")
_NPM = re.compile(r"^(@[A-Za-z0-9_.\-~]+/)?[A-Za-z0-9_.\-~]+$")
_GO_SEG = re.compile(r"^[A-Za-z0-9_.\-~+]+$")
_SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.\-]+))?(?:\+[0-9A-Za-z.\-]+)?$")
_UNRESERVED = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


def auth(values) -> http.Auth:
    return http.bearer(values["token"])


def kind(values) -> str:
    return ""


def check(values) -> str | None:
    """Nothing to refuse: a URL without /artifactory is allowed (some set-ups have no
    context path); `whoami` hints at it when the server answers 404."""
    return None


# --- helpers ------------------------------------------------------------------------

def _limit(value) -> int:
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {value}") from None
    if n < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return min(n, MAX_LIMIT)


def _quote(value, safe="/") -> str:
    """Percent-encode `value` for a URL path (RFC 3986 unreserved and `safe` kept)."""
    keep = _UNRESERVED | frozenset(safe.encode("ascii"))
    return "".join(chr(b) if b in keep else f"%{b:02X}" for b in str(value).encode("utf-8"))


def _jwt_user(token) -> str | None:
    """The user name in a JWT access token's `sub` claim (the part after `/users/`), or
    None when the token is not a JWT. Returns only that name, never any other part."""
    try:
        parts = str(token or "").split(".")
        if len(parts) != 3 or not parts[1]:
            return None
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8"))
        sub = claims.get("sub") if isinstance(claims, dict) else None
        if not isinstance(sub, str) or not sub:
            return None
        return sub.rsplit("/users/", 1)[-1] or None
    except Exception:  # noqa: BLE001  anything unreadable is "not a JWT"
        return None


def _ui_root(ctx) -> str:
    base = ctx.client.base_url
    if base.endswith(CONTEXT):
        base = base[:-len(CONTEXT)]
    return base + "/ui/"


def _ui(ctx, repo, path="") -> str:
    """The web UI link for `repo` (and a path in it)."""
    target = repo + ("/" + path.strip("/") if path else "")
    return _ui_root(ctx) + "repos/tree/General/" + _quote(target, safe="/@")


def _repo(ctx, args, key) -> str:
    repo = getattr(args, "repo", None) or ctx.values.get(key)
    if not repo:
        raise http.ConnectorError(NO_REPO, "config")
    if not _NAME.match(repo) or repo in (".", ".."):
        raise http.ConnectorError(f"Not a repository key: {repo!r} (letters, digits, . _ -).",
                                  "config")
    return repo


def _coords(value) -> tuple[str, str, str]:
    """(group, artifact, 'group/as/path/artifact') from `group:artifact`."""
    group, sep, artifact = str(value).partition(":")
    segs = group.split(".")
    if not sep or not _NAME.match(group) or not _NAME.match(artifact) \
            or any(s == "" for s in segs) or artifact in (".", ".."):
        raise http.ConnectorError(BAD_COORDS, "config")
    return group, artifact, "/".join(segs) + "/" + artifact


def _go_escape(module) -> str:
    """The Go module proxy's case encoding: each upper-case letter X becomes !x."""
    return "".join("!" + ch.lower() if "A" <= ch <= "Z" else ch for ch in module)


def _go_module(value) -> str:
    segs = str(value).strip().split("/")
    if not value or any(not _GO_SEG.match(s) or s in (".", "..") for s in segs):
        raise http.ConnectorError("Give a Go module path, e.g. github.com/org/module.",
                                  "config")
    return "/".join(segs)


def _semver_key(version):
    """A sort key: (major, minor, patch, release-after-prerelease, prerelease parts)."""
    m = _SEMVER.match(version)
    if not m:
        return None
    pre = m.group(4)
    parts = tuple((0, int(p), "") if p.isdigit() else (1, 0, p)
                  for p in (pre.split(".") if pre else ()))
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), 0 if pre else 1, parts)


def _semver_sorted(versions) -> list[str]:
    """Newest first; a pre-release comes after its release; unparsable ones last, as listed."""
    good = [v for v in versions if _semver_key(v) is not None]
    bad = [v for v in versions if _semver_key(v) is None]
    return sorted(good, key=_semver_key, reverse=True) + bad


def _iso_stamp(value) -> str | None:
    """`20260901123045` (Maven's lastUpdated, UTC) → `2026-09-01T12:30:45Z`."""
    v = (value or "").strip()
    if not re.fullmatch(r"\d{14}", v):
        return None
    return f"{v[0:4]}-{v[4:6]}-{v[6:8]}T{v[8:10]}:{v[10:12]}:{v[12:14]}Z"


def _parse_metadata(doc) -> dict:
    """versions (as listed), latest, release, updated from a maven-metadata.xml text.
    A DOCTYPE or entity declaration is refused before parsing (no entity expansion)."""
    upper = (doc or "").upper()
    if "<!DOCTYPE" in upper or "<!ENTITY" in upper:
        raise http.ConnectorError("The maven-metadata.xml answer has a DOCTYPE or entity "
                                  "declaration; it is refused (never parsed).", "bad_response")
    try:
        root = ET.fromstring(doc)
    except ET.ParseError:
        raise http.ConnectorError("The answer is not a readable maven-metadata.xml (a login "
                                  "page or a proxy page?). Check the URL and the repository.",
                                  "bad_response") from None

    def one(path):
        el = root.find(path)
        return (el.text or "").strip() or None if el is not None else None

    versions = [(el.text or "").strip() for el in root.findall("versioning/versions/version")]
    return {"versions": [v for v in versions if v], "latest": one("versioning/latest"),
            "release": one("versioning/release"),
            "updated": _iso_stamp(one("versioning/lastUpdated"))}


def _not_found(exc, what, repo):
    if exc.kind == "not_found":
        return http.ConnectorError(f"The repository {repo} has no {what} (404). Check the "
                                   "name and the repository key.", "not_found", 404)
    return exc


def _version_lines(title, item, truncated) -> list[str]:
    lines = [f"{title} in {item['repo']}: {item['count']} versions", f"url: {item['url']}"]
    lines += [f"- {v}" for v in item["versions"]]
    if truncated:
        lines.append(f"({len(item['versions'])} shown, more exist: raise --limit)")
    return lines


# --- commands -----------------------------------------------------------------------

def _whoami(ctx, args) -> Result:
    try:
        data = ctx.client.get_json("/api/system/version")
    except http.ConnectorError as exc:
        if exc.kind != "not_found":
            raise
        base = ctx.client.base_url
        hint = "check the URL." if base.endswith(CONTEXT) else \
            "does the URL need /artifactory at the end?"
        raise http.ConnectorError(f"Nothing at {base}/api/system/version: {hint}",
                                  "not_found", 404) from None
    user = _jwt_user(ctx.values.get("token"))
    version = data.get("version") if isinstance(data, dict) else None
    return Result(item={"user": user, "display_name": user or "unknown (not a JWT token)",
                        "server_version": version or None, "url": _ui_root(ctx)})


def _repos_args(p):
    p.add_argument("--type", help="package type, e.g. maven, npm, go")
    p.add_argument("--limit", type=_limit, default=200)


def _repos(ctx, args) -> Result:
    data = ctx.client.get_json("/api/repositories", {"packageType": args.type})
    rows = data if isinstance(data, list) else []
    items = [{"key": r.get("key"), "type": r.get("type"), "package_type": r.get("packageType"),
              "description": r.get("description") or None,
              "url": _ui(ctx, r.get("key") or "")} for r in rows if isinstance(r, dict)]
    return Result(items=items[:args.limit], truncated=len(items) > args.limit)


def _coords_args(p):
    p.add_argument("coords", help="group:artifact, e.g. org.apache.commons:commons-text")
    p.add_argument("--repo", help="repository key (default: the saved maven_repo)")


def _versions_args(p):
    _coords_args(p)
    p.add_argument("--limit", type=_limit, default=200)


def _versions(ctx, args) -> Result:
    group, artifact, path = _coords(args.coords)
    repo = _repo(ctx, args, "maven_repo")
    try:
        doc, cut = ctx.client.get_text(f"/{repo}/{path}/maven-metadata.xml",
                                       accept="application/xml", max_bytes=METADATA_BYTES)
    except http.ConnectorError as exc:
        raise _not_found(exc, f"maven-metadata.xml for {group}:{artifact}", repo) from None
    if cut:
        raise http.ConnectorError(f"The maven-metadata.xml for {group}:{artifact} is larger "
                                  f"than {METADATA_BYTES} bytes; it is not read.",
                                  "bad_response")
    meta = _parse_metadata(doc)
    newest = list(reversed(meta["versions"]))
    item = {"group": group, "artifact": artifact, "repo": repo,
            "versions": newest[:args.limit], "latest": meta["latest"],
            "release": meta["release"], "updated": meta["updated"], "count": len(newest),
            "url": _ui(ctx, repo, path)}
    truncated = len(newest) > args.limit
    lines = _version_lines(f"{group}:{artifact}", item, truncated)
    lines[1:1] = [f"latest: {item['latest'] or ''}  release: {item['release'] or ''}  "
                  f"updated: {item['updated'] or ''}"]
    return Result(item=item, truncated=truncated, lines=lines)


def _latest(ctx, args) -> Result:
    group, artifact, path = _coords(args.coords)
    repo = _repo(ctx, args, "maven_repo")
    try:
        body, _ = ctx.client.get_text("/api/search/latestVersion",
                                      {"g": group, "a": artifact, "repos": repo})
        version = body.strip() or None
    except http.ConnectorError as exc:
        if exc.kind != "not_found":
            raise
        version = None
    return Result(item={"group": group, "artifact": artifact, "repo": repo,
                        "version": version,
                        "url": _ui(ctx, repo, path + (f"/{version}" if version else ""))})


def _npm_args(p):
    p.add_argument("package", help="package name, e.g. left-pad or @scope/name")
    p.add_argument("--repo", help="repository key (default: the saved npm_repo)")
    p.add_argument("--limit", type=_limit, default=200)


def _npm(ctx, args) -> Result:
    name = str(args.package).strip()
    if not _NPM.match(name):
        raise http.ConnectorError("Give an npm package name, e.g. left-pad or @scope/name.",
                                  "config")
    repo = _repo(ctx, args, "npm_repo")
    encoded = _quote(name, safe="@").replace("%2F", "%2f")
    try:
        data = ctx.client.get_json(f"/api/npm/{repo}/{encoded}")
    except http.ConnectorError as exc:
        raise _not_found(exc, f"npm package {name}", repo) from None
    data = data if isinstance(data, dict) else {}
    listed = [v for v in (data.get("versions") or {})]
    times = data.get("time") if isinstance(data.get("time"), dict) else {}
    if listed and all(isinstance(times.get(v), str) for v in listed):
        ordered = sorted(listed, key=lambda v: times[v], reverse=True)
    else:
        ordered = listed
    shown = ordered[:args.limit]
    item = {"package": name, "repo": repo,
            "dist_tags": dict(data.get("dist-tags") or {}), "versions": shown,
            "published": {v: times[v] for v in shown if isinstance(times.get(v), str)},
            "count": len(ordered), "url": _ui(ctx, repo, name)}
    truncated = len(ordered) > args.limit
    lines = _version_lines(name, item, truncated)
    lines[1:1] = ["dist-tags: " + ", ".join(f"{k}={v}" for k, v in item["dist_tags"].items())]
    return Result(item=item, truncated=truncated, lines=lines)


def _go_args(p):
    p.add_argument("module", help="module path, e.g. github.com/org/module")
    p.add_argument("--repo", help="repository key (default: the saved go_repo)")
    p.add_argument("--limit", type=_limit, default=200)


def _go(ctx, args) -> Result:
    module = _go_module(args.module)
    repo = _repo(ctx, args, "go_repo")
    escaped = _quote(_go_escape(module), safe="/!")
    try:
        body, _ = ctx.client.get_text(f"/api/go/{repo}/{escaped}/@v/list")
    except http.ConnectorError as exc:
        raise _not_found(exc, f"Go module {module}", repo) from None
    ordered = _semver_sorted([line.strip() for line in body.splitlines() if line.strip()])
    item = {"module": module, "repo": repo, "versions": ordered[:args.limit],
            "count": len(ordered), "url": _ui(ctx, repo, module)}
    truncated = len(ordered) > args.limit
    return Result(item=item, truncated=truncated,
                  lines=_version_lines(module, item, truncated))


WHOAMI = Command("who you are signed in as (from the token), and the server version",
                 run=_whoami)
COMMANDS = {
    "repos": Command("the repositories you can read (--type maven, npm, go, …)", run=_repos,
                     args=_repos_args),
    "versions": Command("the versions of a Maven artifact in a repository "
                        "(from maven-metadata.xml)", run=_versions, args=_versions_args),
    "latest": Command("the latest version of a Maven artifact, as the server reports it",
                      run=_latest, args=_coords_args),
    "npm": Command("the versions and dist-tags of an npm package", run=_npm, args=_npm_args),
    "go": Command("the versions of a Go module", run=_go, args=_go_args),
}
