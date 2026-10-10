"""SonarQube, read-only: who you are, a project's quality gate, its open issues,
security hotspots, measures, and one rule's text.

Auth is a user token sent as the Basic user name with an empty password
(`Authorization: Basic base64("<token>:")`), which SonarQube 9.x to 2025.x accept.
Only GET requests are sent; nothing in SonarQube is ever marked or changed.

The server version is read once per run (`GET /api/server/version`). SonarQube 10.2
replaced the issue fields `severity` and `type` with `impacts` and
`cleanCodeAttribute`; both shapes map to one output, and the `--severity` / `--type`
filters are translated per version. What was sent is in `filter_sent`. Issue search
pages with `p` / `ps` and never returns more than 10,000 issues for one search.
"""
from __future__ import annotations

import argparse
import base64
import re
import urllib.parse

from . import http, text
from .registry import Command, Field, Result

TITLE = "SonarQube"
FIELDS = [
    Field("url", "SonarQube URL, e.g. https://sonar.example.com"),
    Field("token", "User token (My Account → Security → Generate Tokens; type User)",
          secret=True),
]

PAGE = 100                     # SonarQube allows ps up to 500
CAP = 10000                    # SonarQube's search cap (p * ps)
MAX_LIMIT = 1000
RULE_CHARS = 8000
DEFAULT_METRICS = ("bugs,vulnerabilities,code_smells,security_hotspots,coverage,"
                   "duplicated_lines_density,ncloc,reliability_rating,security_rating,"
                   "sqale_rating,new_coverage,new_duplicated_lines_density,new_violations")

NEW_API = (10, 2)              # impacts and cleanCodeAttribute
IMPACT_BLOCKER_INFO = (2025, 1)

# --severity value → (below 10.2: severities=, 10.2+: impactSeverities=, 2025.1+)
SEVERITIES = {
    "blocker": ("BLOCKER", "HIGH", "BLOCKER"),
    "critical": ("CRITICAL", "HIGH", "HIGH"),
    "major": ("MAJOR", "MEDIUM", "MEDIUM"),
    "minor": ("MINOR", "LOW", "LOW"),
    "info": ("INFO", "LOW", "INFO"),
    "high": ("BLOCKER,CRITICAL", "HIGH", "HIGH"),
    "medium": ("MAJOR", "MEDIUM", "MEDIUM"),
    "low": ("MINOR,INFO", "LOW", "LOW"),
}
# --type value → (below 10.2: types=, 10.2+: impactSoftwareQualities=)
TYPES = {
    "bug": ("BUG", "RELIABILITY"),
    "reliability": ("BUG", "RELIABILITY"),
    "vulnerability": ("VULNERABILITY", "SECURITY"),
    "security": ("VULNERABILITY", "SECURITY"),
    "code_smell": ("CODE_SMELL", "MAINTAINABILITY"),
    "maintainability": ("CODE_SMELL", "MAINTAINABILITY"),
}


# --- auth -----------------------------------------------------------------------------

class _TokenAsUser(http.Auth):
    """The token as the Basic user name, empty password. Unlike `http.basic(token, "")`,
    `secrets()` lists the token itself, so an error that quotes it is scrubbed."""
    kind = "basic"

    def __init__(self, token):
        self._token = token
        self._encoded = base64.b64encode(f"{token}:".encode("utf-8")).decode("ascii")

    def headers(self, client) -> dict:
        return {"Authorization": f"Basic {self._encoded}"}

    def secrets(self) -> list[str]:
        return [self._token, self._encoded]


def auth(values) -> http.Auth:
    # The foundation's `http.token_as_user` (0.10.0 Task A1) when present; the local
    # class otherwise. Both send the same header and list the same secrets.
    make = getattr(http, "token_as_user", None) or _TokenAsUser
    return make(values["token"])


def kind(values) -> str:
    return ""


# --- helpers --------------------------------------------------------------------------

def _limit(value) -> int:
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {value}") from None
    if n < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return min(n, MAX_LIMIT)


def _choices(allowed):
    """An argparse type for a comma list whose values must all be in `allowed`."""
    def parse(value):
        vals = [v.strip().lower() for v in str(value).split(",") if v.strip()]
        bad = [v for v in vals if v not in allowed]
        if bad or not vals:
            raise argparse.ArgumentTypeError(
                f"unknown value {', '.join(bad) or repr(value)}; use one or more of: "
                + ", ".join(allowed))
        return vals
    return parse


def parse_version(raw) -> tuple[int, int] | None:
    """(major, minor) from `/api/server/version` ("10.6.0.92116"); None when unreadable.
    Community Build numbers (24.12, 25.1, ...) are read as 2024.12, 2025.1."""
    m = re.fullmatch(r"\s*(\d+)\.(\d+)(?:\.[0-9A-Za-z.\-]*)?\s*", str(raw or ""))
    if not m:
        return None
    major, minor = int(m.group(1)), int(m.group(2))
    if 24 <= major < 100:
        major += 2000
    return major, minor


def _version(ctx):
    """The server version, read once per run and kept on the Context."""
    if not hasattr(ctx, "_sonar_version"):
        try:
            raw, _ = ctx.client.get_text("/api/server/version", max_bytes=200)
            ver = parse_version(raw)
        except http.ConnectorError:
            ver = None
        setattr(ctx, "_sonar_version", ver)
    return getattr(ctx, "_sonar_version")


def _version_text(ver) -> str | None:
    return None if ver is None else f"{ver[0]}.{ver[1]}"


def _is_new(ver) -> bool:
    return ver is None or ver >= NEW_API


def _join(values) -> str:
    out = []
    for v in values:
        for part in v.split(","):
            if part not in out:
                out.append(part)
    return ",".join(out)


def _filters(args, ver) -> dict:
    """The severity and type parameters for this server version (design §5)."""
    new = _is_new(ver)
    out = {}
    if getattr(args, "severity", None):
        col = 0 if not new else (2 if ver is None or ver >= IMPACT_BLOCKER_INFO else 1)
        out["impactSeverities" if new else "severities"] = _join(
            SEVERITIES[s][col] for s in args.severity)
    if getattr(args, "type", None):
        out["impactSoftwareQualities" if new else "types"] = _join(
            TYPES[t][1 if new else 0] for t in args.type)
    return out


def _q(value) -> str:
    return urllib.parse.quote(str(value), safe="")


def _dashboard(ctx, project) -> str:
    return ctx.client.web_url(f"dashboard?id={_q(project)}")


def _file(component) -> str | None:
    if not component or ":" not in component:
        return None
    return component.split(":", 1)[1]


def _impacts(raw) -> list:
    return [{"quality": i.get("softwareQuality"), "severity": i.get("severity")}
            for i in raw.get("impacts") or [] if isinstance(i, dict)]


class PagePaging:
    """SonarQube's p / ps paging with paging.total, stopped at the search cap."""
    size = "ps"

    def next(self, data, params, got):
        p, ps = int(params.get("p") or 1), int(params.get(self.size) or PAGE)
        total = _total(data)
        if got == 0 or got < ps:
            return None
        if isinstance(total, int) and p * ps >= min(total, CAP):
            return None
        if p * ps >= CAP:
            return None
        return None, {**params, "p": p + 1}


def _total(data):
    total = http.dig(data, "paging.total")
    if total is None:
        total = data.get("total") if isinstance(data, dict) else None
    return total if isinstance(total, int) else None


def _paged(ctx, path, params, items_key, limit):
    """(rows, truncated, capped): like Client.paginate, but with a fixed page size, since
    page-number paging repeats items when `ps` changes between pages."""
    paging = PagePaging()
    ps = max(1, min(PAGE, limit))
    params = {**params, "p": 1, "ps": ps}
    rows = []
    while True:
        data = ctx.client.get_json(path, params) or {}
        batch = (data.get(items_key) if isinstance(data, dict) else None) or []
        room = limit - len(rows)
        rows.extend(batch[:room])
        nxt = paging.next(data, params, len(batch)) if isinstance(data, dict) else None
        total = _total(data) if isinstance(data, dict) else None
        if len(rows) >= limit:
            more = bool(nxt) or len(batch) > room or (total is not None and total > len(rows))
            return rows, more, False
        if not nxt:
            capped = total is not None and total > CAP and len(rows) < total
            return rows, capped, capped
        params = nxt[1]


# --- commands -------------------------------------------------------------------------

def _whoami(ctx, args) -> Result:
    me = ctx.client.get_json("/api/users/current") or {}
    if not me.get("isLoggedIn") or not me.get("login"):
        raise http.ConnectorError("SonarQube treated you as anonymous: the token was not "
                                  "accepted (wrong, expired or revoked).", "unauthorized", 401)
    return Result(item={"user": me.get("login"), "display_name": me.get("name") or me["login"],
                        "email": me.get("email") or None,
                        "server_version": _version_text(_version(ctx)),
                        "url": ctx.client.web_url("account")})


def _project_arg(p):
    p.add_argument("project", help="the project key (sonar.projectKey)")


def _period(status) -> dict | None:
    period = status.get("period")
    if not isinstance(period, dict):
        periods = status.get("periods") or []
        period = periods[0] if periods and isinstance(periods[0], dict) else None
    if not period:
        return None
    return {"mode": period.get("mode"), "date": period.get("date"),
            "parameter": period.get("parameter")}


def _gate(ctx, args) -> Result:
    data = ctx.client.get_json("/api/qualitygates/project_status",
                               {"projectKey": args.project}) or {}
    st = data.get("projectStatus") or {}
    conds = [c for c in st.get("conditions") or [] if isinstance(c, dict)]
    status = st.get("status")
    failed = [{"metric": c.get("metricKey"), "comparator": c.get("comparator"),
               "threshold": c.get("errorThreshold"), "actual": c.get("actualValue")}
              for c in conds if status == "ERROR" and c.get("status") == "ERROR"]
    item = {
        "project": args.project, "status": status, "failed": failed,
        "conditions": [{"metric": c.get("metricKey"), "status": c.get("status"),
                        "comparator": c.get("comparator"), "threshold": c.get("errorThreshold"),
                        "actual": c.get("actualValue")} for c in conds],
        "new_code_period": _period(st),
        "url": _dashboard(ctx, args.project),
    }
    lines = [f"{args.project}: quality gate {status or 'unknown'}", f"url: {item['url']}"]
    for f in failed:
        lines.append(f"failed: {f['metric']} is {f['actual']} ({f['comparator']} "
                     f"{f['threshold']})")
    return Result(item=item, lines=lines)


def _issues_args(p):
    _project_arg(p)
    p.add_argument("--severity", type=_choices(list(SEVERITIES)),
                   help="comma list: " + ", ".join(SEVERITIES))
    p.add_argument("--type", type=_choices(list(TYPES)), help="comma list: " + ", ".join(TYPES))
    p.add_argument("--rule", help="a rule key, e.g. java:S2095")
    p.add_argument("--file", help="a file path in the project, e.g. src/main/java/App.java")
    p.add_argument("--new-code", action="store_true", help="only issues in the new code")
    p.add_argument("--limit", type=_limit, default=100)


def _issue_item(ctx, project, raw) -> dict:
    key = raw.get("key")
    return {
        "key": key, "rule": raw.get("rule"), "message": raw.get("message"),
        "severity": raw.get("severity"), "type": raw.get("type"),
        "impacts": _impacts(raw), "clean_code_attribute": raw.get("cleanCodeAttribute"),
        "status": raw.get("issueStatus") or raw.get("status"),
        "file": _file(raw.get("component")), "line": raw.get("line"),
        "effort": raw.get("effort"), "tags": list(raw.get("tags") or []),
        "created": raw.get("creationDate"), "updated": raw.get("updateDate"),
        "url": ctx.client.web_url(f"project/issues?id={_q(project)}&open={_q(key)}"),
    }


def _issues(ctx, args) -> Result:
    ver = _version(ctx)
    component = f"{args.project}:{args.file.lstrip('/')}" if args.file else args.project
    sent = {("components" if _is_new(ver) else "componentKeys"): component,
            "resolved": "false"}
    if args.rule:
        sent["rules"] = args.rule
    if args.new_code:
        sent["inNewCodePeriod"] = "true"
    sent.update(_filters(args, ver))
    raw, truncated, capped = _paged(ctx, "/api/issues/search", sent, "issues", args.limit)
    items = [_issue_item(ctx, args.project, r) for r in raw]
    extra = {"server_version": _version_text(ver), "filter_sent": dict(sent)}
    if capped:
        extra["capped_at"] = CAP
    lines = []
    for it in items:
        sev = it["severity"] or ",".join(f"{i['quality']}:{i['severity']}"
                                         for i in it["impacts"]) or "?"
        where = f"{it['file']}:{it['line']}" if it["file"] and it["line"] else (it["file"] or "")
        lines.append(f"- {it['key']} [{sev}] {it['rule']} {where} {it['message'] or ''}".rstrip()
                     + f"  {it['url']}")
    lines.append(f"({len(items)} shown" + (", more exist: narrow the filter or raise --limit)"
                                           if truncated else ")"))
    if capped:
        lines.append(f"SonarQube returns at most {CAP} issues for one search: narrow the "
                     "filter (--file, --rule, --severity, --new-code).")
    lines.append("filter sent: " + ", ".join(f"{k}={v}" for k, v in sent.items()))
    return Result(items=items, truncated=truncated, lines=lines, extra=extra)


def _hotspots_args(p):
    _project_arg(p)
    p.add_argument("--status", choices=("TO_REVIEW", "REVIEWED"), default="TO_REVIEW")
    p.add_argument("--limit", type=_limit, default=100)


def _hotspots(ctx, args) -> Result:
    raw, truncated, capped = _paged(ctx, "/api/hotspots/search",
                                    {"project": args.project, "status": args.status},
                                    "hotspots", args.limit)
    items = [{"key": h.get("key"), "rule": h.get("ruleKey"),
              "category": h.get("securityCategory"),
              "probability": h.get("vulnerabilityProbability"), "status": h.get("status"),
              "resolution": h.get("resolution"), "message": h.get("message"),
              "file": _file(h.get("component")), "line": h.get("line"),
              "url": ctx.client.web_url(f"security_hotspots?id={_q(args.project)}"
                                        f"&hotspots={_q(h.get('key'))}")} for h in raw]
    extra = {"capped_at": CAP} if capped else {}
    return Result(items=items, truncated=truncated, extra=extra)


def _measures_args(p):
    _project_arg(p)
    p.add_argument("--metrics", default=DEFAULT_METRICS, help="comma list of metric keys")


def _measures(ctx, args) -> Result:
    wanted = [m.strip() for m in args.metrics.split(",") if m.strip()]
    data = ctx.client.get_json("/api/measures/component",
                               {"component": args.project, "metricKeys": ",".join(wanted)}) or {}
    comp = data.get("component") or {}
    measures, new_code, seen = {}, {}, set()
    for m in comp.get("measures") or []:
        if not isinstance(m, dict) or not m.get("metric"):
            continue
        seen.add(m["metric"])
        if "value" in m:
            measures[m["metric"]] = m["value"]
        period = m.get("period")
        if not isinstance(period, dict):
            periods = m.get("periods") or []
            period = periods[0] if periods and isinstance(periods[0], dict) else None
        if period and "value" in period:
            new_code[m["metric"]] = period["value"]
    return Result(item={"project": args.project, "name": comp.get("name"),
                        "measures": measures, "new_code": new_code,
                        "missing": [m for m in wanted if m not in seen],
                        "url": _dashboard(ctx, args.project)})


def _rule_args(p):
    p.add_argument("key", help="the rule key, e.g. java:S2095")
    p.add_argument("--max-chars", type=_limit_chars, default=RULE_CHARS)


def _limit_chars(value) -> int:
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {value}") from None
    if n < 20:
        raise argparse.ArgumentTypeError("must be at least 20")
    return n


def _rule_text(rule) -> str:
    if rule.get("htmlDesc"):
        return text.html_to_text(rule["htmlDesc"])
    parts = []
    for s in rule.get("descriptionSections") or []:
        if not isinstance(s, dict):
            continue
        heading = str(s.get("key") or "").replace("_", " ").strip().capitalize()
        body = text.html_to_text(s.get("content"))
        parts.extend(p for p in (heading, body) if p)
    if not parts and rule.get("mdDesc"):
        parts.append(str(rule["mdDesc"]))
    return "\n".join(parts)


def _rule(ctx, args) -> Result:
    data = ctx.client.get_json("/api/rules/show", {"key": args.key}) or {}
    rule = data.get("rule") or {}
    full = _rule_text(rule)
    key = rule.get("key") or args.key
    return Result(item={
        "key": key, "name": rule.get("name"), "language": rule.get("langName"),
        "severity": rule.get("severity"), "type": rule.get("type"),
        "impacts": _impacts(rule), "clean_code_attribute": rule.get("cleanCodeAttribute"),
        "description": text.clip(full, args.max_chars),
        "description_truncated": len(full) > args.max_chars,
        "url": ctx.client.web_url(f"coding_rules?open={_q(key)}&rule_key={_q(key)}")})


WHOAMI = Command("who you are signed in as, and the server version", run=_whoami)
COMMANDS = {
    "gate": Command("a project's quality gate: status, failed conditions first",
                    run=_gate, args=_project_arg),
    "issues": Command("a project's open issues (filters: severity, type, rule, file, "
                      "new code)", run=_issues, args=_issues_args),
    "hotspots": Command("a project's security hotspots (default: to review)",
                        run=_hotspots, args=_hotspots_args),
    "measures": Command("a project's measures: coverage, duplication, ratings, new code",
                        run=_measures, args=_measures_args),
    "rule": Command("one rule's description as plain text", run=_rule, args=_rule_args),
}
