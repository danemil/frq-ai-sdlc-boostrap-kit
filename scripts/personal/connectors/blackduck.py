"""Black Duck (read-only): projects, versions, vulnerabilities, components and policy status.

Auth: the person's API token is exchanged once per run for a bearer token that lives
about two hours (inside http.BlackDuckToken, the only request that is not a GET); every
read is then a GET with that bearer token and the vendor media type of its endpoint.

Projects and versions are given by name: the project is found among the `q=name:`
results (exact name, case-insensitive), the version among its `q=versionName:` results;
then the connector follows the `_meta.links` hrefs the server gave. Lists page with
offset/limit and totalCount, items under `items`.

`vulns` reads each vulnerable component version's upgrade guidance (once per distinct
component version, at most MAX_GUIDANCE per run) for `fixed_in`. The media types, field
names and browser links are to be confirmed on a live server (see the test file).
"""
from __future__ import annotations

import argparse

from . import http
from .registry import Command, Field, Result

TITLE = "Black Duck"
FIELDS = [
    Field("url", "Black Duck URL, e.g. https://blackduck.example.com"),
    Field("token", "API token (your name → My Access Tokens → Create New Token; read access)",
          secret=True),
]

_VND = "application/vnd.blackducksoftware."
USER = _VND + "user-4+json"
PROJECT = _VND + "project-detail-4+json"
VERSION = _VND + "project-detail-5+json"
BOM = _VND + "bill-of-materials-6+json"
COMPONENT = _VND + "component-detail-5+json"

PAGE = 100
MAX_LIMIT = 1000
MAX_GUIDANCE = 50
SEVERITIES = ("critical", "high", "medium", "low")
PAGING = http.Offset(start="offset", size="limit", total="totalCount")


def auth(values) -> http.Auth:
    return http.blackduck_token(values["token"])


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


def _severities(value) -> list:
    vals = [v.strip().lower() for v in str(value).split(",") if v.strip()]
    bad = [v for v in vals if v not in SEVERITIES]
    if bad or not vals:
        raise argparse.ArgumentTypeError(
            f"not a severity: {', '.join(bad) or value!r} (use {', '.join(SEVERITIES)}, "
            "comma-separated)")
    return vals


def _get(ctx, path, params, accept):
    data = ctx.client.get(path, params, accept=accept).json()
    return data if isinstance(data, dict) else {}


def _paged(ctx, href, params, accept, limit, keep=None):
    """(items, truncated): like Client.paginate with offset/limit, but with the endpoint's
    own Accept, and an optional client-side filter `keep` (the limit counts kept items)."""
    params = {PAGING.start: 0, **(params or {})}
    out = []
    while True:
        params[PAGING.size] = PAGE if keep else max(1, min(PAGE, limit - len(out)))
        data = _get(ctx, href, params, accept)
        batch = data.get("items") or []
        nxt = PAGING.next(data, params, len(batch))
        kept = [b for b in batch if keep is None or keep(b)]
        room = limit - len(out)
        out.extend(kept[:room])
        if len(out) >= limit:
            return out, bool(nxt) or len(kept) > room
        if not nxt or not batch:
            return out, False
        params = nxt[1]


def _href(obj):
    return http.dig(obj, "_meta.href")


def _link(obj, rel, what):
    for link in http.dig(obj, "_meta.links") or []:
        if isinstance(link, dict) and link.get("rel") == rel and link.get("href"):
            return link["href"]
    raise http.ConnectorError(f"Black Duck gave no '{rel}' link for {what}; this server's "
                              "API may differ from the one the connector knows.",
                              "bad_response")


def _one(rows, key, name):
    """(the row whose `key` equals `name` ignoring case or None, exact matches)."""
    exact = [r for r in rows if str(r.get(key) or "").lower() == name.lower()]
    return (exact[0] if len(exact) == 1 else None), exact


def _project(ctx, name):
    data = _get(ctx, "/api/projects", {"q": f"name:{name}", "limit": PAGE}, PROJECT)
    rows = data.get("items") or []
    found, exact = _one(rows, "name", name)
    if found:
        return found
    if exact:
        listed = ", ".join(f"'{r.get('name')}' ({_href(r)})" for r in exact)
        raise http.ConnectorError(f"Several Black Duck projects are named '{name}': {listed}. "
                                  "Ask the person which one is meant.", "config")
    close = [str(r.get("name")) for r in rows if r.get("name")][:10]
    hint = f" Close matches: {', '.join(close)}." if close else ""
    raise http.ConnectorError(f"No Black Duck project named '{name}'.{hint} Try: connectors.py "
                              "blackduck projects <part of the name>", "not_found", 404)


def _version(ctx, project, name):
    pname = project.get("name")
    href = _link(project, "versions", f"project '{pname}'")
    data = _get(ctx, href, {"q": f"versionName:{name}", "limit": PAGE}, VERSION)
    rows = data.get("items") or []
    found, exact = _one(rows, "versionName", name)
    if found:
        return found
    if exact:
        listed = ", ".join(f"'{r.get('versionName')}'" for r in exact)
        raise http.ConnectorError(f"Project '{pname}' has several versions named '{name}': "
                                  f"{listed}. Ask the person which one is meant.", "config")
    close = [str(r.get("versionName")) for r in rows if r.get("versionName")][:10]
    hint = f" Close matches: {', '.join(close)}." if close else ""
    raise http.ConnectorError(f"Project '{pname}' has no version named '{name}'.{hint} Try: "
                              f"connectors.py blackduck versions {pname}", "not_found", 404)


def _resolve(ctx, args):
    project = _project(ctx, args.project)
    return project, _version(ctx, project, args.version)


def _components_url(version):
    href = _href(version)
    return href.rstrip("/") + "/components" if href else None


def _severity(row):
    sev = http.dig(row, "vulnerabilityWithRemediation.severity")
    return str(sev).lower() if sev else None


def _related(v):
    rel = v.get("relatedVulnerability")
    if isinstance(rel, dict):
        return rel.get("vulnerabilityName") or rel.get("name")
    if isinstance(rel, str) and rel.strip():
        return rel.rstrip("/").rsplit("/", 1)[-1]
    return None


def _fix_versions(ctx, rows, skip):
    """({componentVersion href: fixed_in}, read, skipped) from upgrade guidance."""
    hrefs = []
    for r in rows:
        h = r.get("componentVersion")
        if isinstance(h, str) and h and h not in hrefs:
            hrefs.append(h)
    if skip:
        return {}, 0, len(hrefs)
    out = {}
    for h in hrefs[:MAX_GUIDANCE]:
        try:
            g = _get(ctx, h.rstrip("/") + "/upgrade-guidance", None, COMPONENT)
        except http.ConnectorError as exc:
            if exc.kind != "not_found":
                raise
            out[h] = None
            continue
        short, long = http.dig(g, "shortTerm.versionName"), http.dig(g, "longTerm.versionName")
        out[h] = {"short_term": short, "long_term": long} if (short or long) else None
    return out, min(len(hrefs), MAX_GUIDANCE), max(0, len(hrefs) - MAX_GUIDANCE)


# --- commands -----------------------------------------------------------------------

def _whoami(ctx, args) -> Result:
    me = _get(ctx, "/api/current-user", None, USER)
    user = me.get("userName") or ""
    name = " ".join(p for p in (me.get("firstName"), me.get("lastName")) if p)
    return Result(item={"user": user, "display_name": name or user, "email": me.get("email"),
                        "url": ctx.client.base_url})


def _projects_args(p):
    p.add_argument("text", help="part of the project name")
    p.add_argument("--limit", type=_limit, default=25)


def _projects(ctx, args) -> Result:
    rows, truncated = _paged(ctx, "/api/projects", {"q": f"name:{args.text}"}, PROJECT,
                             args.limit)
    items = [{"name": r.get("name"), "description": r.get("description"),
              "updated": r.get("updatedAt"), "url": _href(r)} for r in rows]
    return Result(items=items, truncated=truncated)


def _versions_args(p):
    p.add_argument("project", help="the project's name")
    p.add_argument("--limit", type=_limit, default=50)


def _versions(ctx, args) -> Result:
    project = _project(ctx, args.project)
    href = _link(project, "versions", f"project '{project.get('name')}'")
    rows, truncated = _paged(ctx, href, {"sort": "updatedAt desc"}, VERSION, args.limit)
    items = [{"name": r.get("versionName"), "phase": r.get("phase"),
              "distribution": r.get("distribution"),
              "updated": r.get("settingUpdatedAt") or r.get("updatedAt"),
              "url": _components_url(r)} for r in rows]
    return Result(items=items, truncated=truncated)


def _pv_args(p):
    p.add_argument("project", help="the project's name")
    p.add_argument("version", help="the version's name")


def _vulns_args(p):
    _pv_args(p)
    p.add_argument("--severity", type=_severities,
                   help="only these severities: critical, high, medium, low (comma-separated)")
    p.add_argument("--limit", type=_limit, default=100)
    p.add_argument("--no-fix-versions", action="store_true",
                   help="skip the upgrade guidance (fixed_in stays null)")


def _vulns(ctx, args) -> Result:
    project, version = _resolve(ctx, args)
    href = _link(version, "vulnerable-components", f"version '{version.get('versionName')}'")
    keep = None
    if args.severity:
        wanted = set(args.severity)
        keep = lambda r: _severity(r) in wanted  # noqa: E731
    rows, truncated = _paged(ctx, href, None, BOM, args.limit, keep)
    fixes, read, skipped = _fix_versions(ctx, rows, args.no_fix_versions)
    vhref = _href(version)
    url = vhref.rstrip("/") + "/vulnerability-bom" if vhref else None
    items = []
    for r in rows:
        v = r.get("vulnerabilityWithRemediation") or {}
        score = v.get("overallScore")
        items.append({
            "id": v.get("vulnerabilityName"), "source": v.get("source"),
            "severity": _severity(r), "score": score if score is not None else v.get("baseScore"),
            "remediation": v.get("remediationStatus"), "component": r.get("componentName"),
            "component_version": r.get("componentVersionName"),
            "origin": r.get("componentVersionOriginId"), "related": _related(v),
            "fixed_in": fixes.get(r.get("componentVersion")), "url": url})
    lines = []
    for i in items:
        fix = i["fixed_in"]
        tail = ""
        if fix:
            tail = " — fixed in " + ", ".join(
                f"{fix[k]} ({k.replace('_', ' ')})" for k in ("short_term", "long_term")
                if fix[k])
        lines.append(f"- {i['id']} [{i['severity']}] {i['component']} "
                     f"{i['component_version']}{tail}  {i['url'] or ''}".rstrip())
    lines.append(f"({len(items)} shown" + (", more exist: raise --limit)" if truncated else ")"))
    if skipped and not args.no_fix_versions:
        lines.append(f"(fix versions read for {read} component versions; {skipped} skipped)")
    return Result(items=items, truncated=truncated, lines=lines,
                  extra={"fix_versions_read": read, "fix_versions_skipped": skipped})


def _components_args(p):
    _pv_args(p)
    p.add_argument("--violations", action="store_true",
                   help="only components that violate a policy")
    p.add_argument("--limit", type=_limit, default=100)


def _components(ctx, args) -> Result:
    project, version = _resolve(ctx, args)
    href = _link(version, "components", f"version '{version.get('versionName')}'")
    params = {"filter": "bomPolicy:in_violation"} if args.violations else None
    rows, truncated = _paged(ctx, href, params, BOM, args.limit)
    items = []
    for r in rows:
        origins = [o.get("externalId") for o in r.get("origins") or []
                   if isinstance(o, dict) and o.get("externalId")]
        licenses = [lic.get("licenseDisplay") or lic.get("licenseName")
                    for lic in r.get("licenses") or [] if isinstance(lic, dict)
                    and (lic.get("licenseDisplay") or lic.get("licenseName"))]
        cv = r.get("componentVersion")
        items.append({"name": r.get("componentName"), "version": r.get("componentVersionName"),
                      "origins": origins, "licenses": licenses,
                      "policy_status": r.get("policyStatus"),
                      "review_status": r.get("reviewStatus"),
                      "url": cv if isinstance(cv, str) and cv else href})
    return Result(items=items, truncated=truncated)


def _policy(ctx, args) -> Result:
    project, version = _resolve(ctx, args)
    data = _get(ctx, _link(version, "policy-status", f"version '{version.get('versionName')}'"),
                None, BOM)
    counts = {c.get("name"): c.get("value") for c in data.get("componentVersionStatusCounts") or []
              if isinstance(c, dict) and c.get("name")}
    return Result(item={"project": project.get("name"), "version": version.get("versionName"),
                        "status": data.get("overallStatus"), "counts": counts,
                        "url": _link(version, "components",
                                     f"version '{version.get('versionName')}'")})


WHOAMI = Command("who you are signed in as", run=_whoami)
COMMANDS = {
    "projects": Command("projects whose name contains some text", run=_projects,
                        args=_projects_args),
    "versions": Command("a project's versions, newest first", run=_versions,
                        args=_versions_args),
    "vulns": Command("a version's vulnerabilities, with the fix version where known",
                     run=_vulns, args=_vulns_args),
    "components": Command("a version's components (--violations: policy violations only)",
                          run=_components, args=_components_args),
    "policy": Command("a version's policy status and counts", run=_policy, args=_pv_args),
}
