"""Jenkins, read-only: who you are, a job (or folder), a build, a build's test report.

Auth is Basic with your user name and an API token. Only GET requests on `/api/json`
endpoints with a `tree=` filter are sent; nothing is ever built, stopped or changed.

A job path `team/app/main` (or `job/team/job/app/job/main`) becomes
`/job/team/job/app/job/main`. A build ref is a number or `last`, `lastSuccessful`,
`lastFailed`. Times are ISO-8601 UTC; durations are in seconds.
"""
from __future__ import annotations

import re
import urllib.parse

from . import http, text
from .registry import Command, Field, Result

TITLE = "Jenkins"
FIELDS = [
    Field("url", "Jenkins URL, e.g. https://jenkins.example.com"),
    Field("username", "Jenkins user name", identity=True),
    Field("token", "API token (your name → Security → API Token)", secret=True),
]

REFS = {"last": "lastBuild", "lastSuccessful": "lastSuccessfulBuild",
        "lastFailed": "lastFailedBuild"}
COLORS = {"blue": "success", "red": "failed", "yellow": "unstable", "aborted": "aborted",
          "disabled": "disabled", "notbuilt": "not built"}
FAILED_CASES = ("FAILED", "REGRESSION")
ERROR_CHARS = 2000

JOB_TREE = ("name,fullName,url,color,description,"
            "lastBuild[number,url,result,timestamp],lastSuccessfulBuild[number,url],"
            "lastFailedBuild[number,url],healthReport[description,score],jobs[name,url,color]")
BUILD_TREE = ("number,url,result,building,timestamp,duration,displayName,description,"
              "changeSet[items[commitId,msg,author[fullName]]],"
              "changeSets[items[commitId,msg,author[fullName]]],"
              "actions[causes[shortDescription],parameters[_class,name,value]]")
TESTS_TREE = ("failCount,passCount,skipCount,duration,"
              "suites[name,cases[className,name,status,duration,errorDetails]]")


def auth(values) -> http.Auth:
    return http.basic(values["username"], values["token"])


def kind(values) -> str:
    return ""


# --- helpers ------------------------------------------------------------------

def job_path(path) -> str:
    """`a/b/c` or `job/a/job/b/job/c` → `/job/a/job/b/job/c`, each name URL-encoded."""
    segs = [urllib.parse.unquote(s) for s in str(path).strip("/").split("/") if s]
    if segs and len(segs) % 2 == 0 and all(s == "job" for s in segs[0::2]):
        segs = segs[1::2]
    if not segs:
        raise http.ConnectorError("Give a job path, e.g. team/app/main.", "config")
    return "".join("/job/" + urllib.parse.quote(s, safe="") for s in segs)


def build_ref(ref) -> str:
    """A build number, or last / lastSuccessful / lastFailed, as Jenkins names it."""
    ref = str(ref).strip()
    if re.fullmatch(r"[0-9]+", ref):
        return ref
    if ref in REFS:
        return REFS[ref]
    if ref in REFS.values():
        return ref
    raise ValueError(f"not a build number or one of {', '.join(REFS)}: {ref}")


def _ref_arg(value):
    import argparse
    try:
        build_ref(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None
    return value


def status(color):
    """(status, building) from a Jenkins ball colour such as `blue` or `red_anime`."""
    if not color:
        return None, False
    building = color.endswith("_anime")
    base = color[:-len("_anime")] if building else color
    return COLORS.get(base, base), building


def _link(ctx, data, fallback):
    """The server's own link for an item, else one built under the base URL."""
    url = (data or {}).get("url") if isinstance(data, dict) else None
    return url or ctx.client.web_url(fallback)


def _seconds(value, ms=False):
    if value in (None, ""):
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return round(v / 1000.0 if ms else v, 3)


# --- commands -----------------------------------------------------------------

def _whoami(ctx, args) -> Result:
    me = ctx.client.get_json("/me/api/json", {"tree": "id,fullName"}) or {}
    user = me.get("id") or ""
    if not user or user == "anonymous":
        raise http.ConnectorError("Jenkins treated you as anonymous: the user name or API "
                                  "token was not accepted.", "unauthorized", 401)
    return Result(item={"user": user, "display_name": me.get("fullName") or user,
                        "url": ctx.client.web_url("user/" + urllib.parse.quote(user, safe=""))})


def _path_args(p):
    p.add_argument("path", help="job path, e.g. team/app/main")


def _job(ctx, args) -> Result:
    jp = job_path(args.path)
    data = ctx.client.get_json(jp + "/api/json", {"tree": JOB_TREE}) or {}
    st, building = status(data.get("color"))
    last = data.get("lastBuild")
    ok, bad = data.get("lastSuccessfulBuild"), data.get("lastFailedBuild")
    children = []
    for child in data.get("jobs") or []:
        name = child.get("name")
        children.append({"name": name, "status": status(child.get("color"))[0],
                         "url": _link(ctx, child, jp + "/job/" +
                                      urllib.parse.quote(name or "", safe="") + "/")})
    item = {
        "name": data.get("name"),
        "full_name": data.get("fullName"),
        "status": st,
        "building": building,
        "health": [{"score": h.get("score"), "description": h.get("description")}
                   for h in data.get("healthReport") or []],
        "last_build": None if not last else {
            "number": last.get("number"), "result": last.get("result"),
            "at": text.iso_from_ms(last.get("timestamp")),
            "url": _link(ctx, last, f"{jp}/{last.get('number')}/")},
        "last_success": None if not ok else {
            "number": ok.get("number"), "url": _link(ctx, ok, f"{jp}/{ok.get('number')}/")},
        "last_failure": None if not bad else {
            "number": bad.get("number"), "url": _link(ctx, bad, f"{jp}/{bad.get('number')}/")},
        "children": children,
        "url": _link(ctx, data, jp + "/"),
    }
    lines = [f"{item['full_name'] or args.path}: {st or 'folder'}"
             + (" (building)" if building else ""), f"url: {item['url']}"]
    if last:
        lines.append(f"last build: #{last.get('number')} {last.get('result') or 'running'} "
                     f"{item['last_build']['at'] or ''}".rstrip())
    for h in item["health"]:
        lines.append(f"health {h['score']}: {h['description']}")
    for c in children:
        lines.append(f"- {c['name']} [{c['status'] or 'folder'}]  {c['url']}")
    return Result(item=item, lines=lines)


def _build_args(p):
    _path_args(p)
    p.add_argument("ref", type=_ref_arg,
                   help="build number, or last / lastSuccessful / lastFailed")


def _build(ctx, args) -> Result:
    jp, ref = job_path(args.path), build_ref(args.ref)
    data = ctx.client.get_json(f"{jp}/{ref}/api/json", {"tree": BUILD_TREE}) or {}
    causes, params = [], []
    for action in data.get("actions") or []:
        if not isinstance(action, dict):
            continue
        for cause in action.get("causes") or []:
            if cause.get("shortDescription"):
                causes.append(cause["shortDescription"])
        for p in action.get("parameters") or []:
            if "Password" in str(p.get("_class") or ""):
                continue
            params.append({"name": p.get("name"), "value": p.get("value")})
    sets = []
    if isinstance(data.get("changeSet"), dict):
        sets.append(data["changeSet"])
    sets.extend(s for s in data.get("changeSets") or [] if isinstance(s, dict))
    changes, seen = [], set()
    for s in sets:
        for ch in s.get("items") or []:
            key = (ch.get("commitId"), ch.get("msg"))
            if key in seen:
                continue
            seen.add(key)
            changes.append({"commit": ch.get("commitId"), "message": ch.get("msg"),
                            "author": (ch.get("author") or {}).get("fullName")})
    item = {
        "number": data.get("number"),
        "display_name": data.get("displayName"),
        "result": data.get("result"),
        "building": bool(data.get("building")),
        "started": text.iso_from_ms(data.get("timestamp")),
        "duration_s": _seconds(data.get("duration"), ms=True),
        "causes": causes,
        "parameters": params,
        "changes": changes,
        "url": _link(ctx, data, f"{jp}/{ref}/"),
    }
    lines = [f"{args.path} {item['display_name'] or '#' + str(item['number'])}: "
             f"{'building' if item['building'] else item['result'] or 'unknown'}",
             f"url: {item['url']}",
             f"started: {item['started'] or ''}  duration: {item['duration_s']} s"]
    lines += [f"cause: {c}" for c in causes]
    lines += [f"param {p['name']} = {p['value']}" for p in params]
    lines += [f"- {(c['commit'] or '')[:12]} {c['author'] or ''}: "
              f"{(c['message'] or '').splitlines()[0] if c['message'] else ''}"
              for c in changes]
    return Result(item=item, lines=lines)


def _tests_args(p):
    _build_args(p)
    p.add_argument("--all", action="store_true", help="every test case, not only failures")


def _tests(ctx, args) -> Result:
    jp, ref = job_path(args.path), build_ref(args.ref)
    try:
        data = ctx.client.get_json(f"{jp}/{ref}/testReport/api/json",
                                   {"tree": TESTS_TREE}) or {}
    except http.ConnectorError as exc:
        if exc.kind == "not_found":
            raise http.ConnectorError(f"Build {args.ref} of {args.path} has no test report.",
                                      "not_found", 404) from None
        raise
    cases = []
    for suite in data.get("suites") or []:
        for case in suite.get("cases") or []:
            if not args.all and case.get("status") not in FAILED_CASES:
                continue
            err = case.get("errorDetails")
            cases.append({"class": case.get("className"), "name": case.get("name"),
                          "status": case.get("status"),
                          "duration_s": _seconds(case.get("duration")),
                          "error": text.clip(err, ERROR_CHARS) if err else None})
    item = {"fail": data.get("failCount"), "pass": data.get("passCount"),
            "skip": data.get("skipCount"), "duration_s": _seconds(data.get("duration")),
            "cases": cases, "url": ctx.client.web_url(f"{jp}/{ref}/testReport/")}
    lines = [f"{args.path} build {args.ref}: {item['fail']} failed, {item['pass']} passed, "
             f"{item['skip']} skipped ({item['duration_s']} s)", f"url: {item['url']}"]
    for c in cases:
        first = (c["error"] or "").splitlines()[0] if c["error"] else ""
        lines.append(f"- {c['status']} {c['class']}.{c['name']}" + (f": {first}" if first
                                                                     else ""))
    return Result(item=item, lines=lines)


WHOAMI = Command("who you are signed in as", run=_whoami)
COMMANDS = {
    "job": Command("a job or folder: status, health, last builds, children", run=_job,
                   args=_path_args),
    "build": Command("one build: result, times, causes, parameters, changes", run=_build,
                     args=_build_args),
    "tests": Command("a build's test report: counts and failures (--all: every case)",
                     run=_tests, args=_tests_args),
}
