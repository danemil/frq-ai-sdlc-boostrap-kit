#!/usr/bin/env python3
"""The sonarqube connector (SonarQube Web API, read-only) against tests/fakeserver.py:
no network.

Canned answers follow SonarQube's documented Web API shapes for 9.9 LTS, 10.x and
2025.x (paging {pageIndex, pageSize, total}; issues with `severity`/`type` before
10.2 and `impacts`/`cleanCodeAttribute` from 10.2).

To confirm on a live server (design §9):
- `GET /api/users/current` returns `isLoggedIn: false` (not a 401) for a bad token on
  the client's version;
- the token as the Basic user name with an empty password on the newest version the
  client runs (2025.x); Bearer is the fallback if not;
- the impacts field names `impacts[].softwareQuality`, `impacts[].severity`,
  `cleanCodeAttribute`; the filter parameters `impactSeverities`,
  `impactSoftwareQualities`; `BLOCKER` and `INFO` impact severities from 2025.1;
- `components` versus `componentKeys` at the client's version; `issueStatus` from 10.4;
- the 10,000-issue cap answer (a 400 past it, or an empty page);
- the default metric keys of `measures` on 10.x and 2025.x (some were renamed
  `software_quality_*`);
- (added in B1) Community Build version numbers (`24.12`, `25.1`, ...) read as the
  2024.12 / 2025.1 feature level, so BLOCKER and INFO impact severities are sent from
  Community Build 25.1;
- (added in B1) the `/api/server/version` answer is plain text and readable with the
  user token (it is public on a default server).
"""
from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import unittest
from unittest import mock

import helpers  # noqa: F401  puts scripts/ on sys.path
from fakeserver import ConnectorTestCase, Reply

TOKEN = "squ_S0NAR-user-token-7f3a9c"
PROJECT = "demo"

ME = {"isLoggedIn": True, "login": "ana", "name": "Ana Pop", "email": "ana@example.com",
      "groups": ["sonar-users"]}


def version(text):
    return Reply(200, text, {"Content-Type": "text/plain"})


def issue(key, **over):
    raw = {"key": key, "rule": "java:S2095", "severity": "CRITICAL", "type": "BUG",
           "component": f"{PROJECT}:src/main/java/App.java", "project": PROJECT,
           "line": 42, "message": "Use try-with-resources", "effort": "5min",
           "status": "OPEN", "tags": ["cwe"], "creationDate": "2026-10-01T10:00:00+0000",
           "updateDate": "2026-10-02T10:00:00+0000"}
    raw.update(over)
    return raw


def new_issue(key, **over):
    raw = {"key": key, "rule": "java:S2095", "component": f"{PROJECT}:src/A.java",
           "project": PROJECT, "line": 7, "message": "Close this stream",
           "effort": "5min", "issueStatus": "OPEN", "status": "OPEN", "tags": [],
           "impacts": [{"softwareQuality": "RELIABILITY", "severity": "HIGH"}],
           "cleanCodeAttribute": "COMPLETE", "cleanCodeAttributeCategory": "INTENTIONAL",
           "creationDate": "2026-10-01T10:00:00+0000",
           "updateDate": "2026-10-02T10:00:00+0000"}
    raw.update(over)
    return raw


def paged(rows, key="issues"):
    """A route serving `rows` with SonarQube's p/ps paging and paging.total."""
    def route(req):
        p = int(req.query.get("p", ["1"])[0])
        ps = int(req.query.get("ps", ["100"])[0])
        start = (p - 1) * ps
        return {"paging": {"pageIndex": p, "pageSize": ps, "total": len(rows)},
                key: rows[start:start + ps]}
    return route


class Base(ConnectorTestCase):
    def setUp(self):
        super().setUp()
        self.c = self.connector("sonarqube")

    def srv(self, routes, ver="10.6.0.92116"):
        base = {"/api/server/version": version(ver)} if ver is not None else {}
        return self.server({**base, **routes})

    def values(self, srv):
        return {"url": srv.url, "token": TOKEN}

    def ctx(self, srv):
        return self.context(self.c, self.values(srv))

    def cmd(self, srv, *argv, ctx=None):
        return self.run_command(self.c, ctx or self.ctx(srv), list(argv))

    def api(self, srv, path):
        return [r for r in srv.requests if r.path == path]


class TestModule(Base):
    def test_registry_validates_and_fields(self):
        self.assertEqual(self.c.title, "SonarQube")
        self.assertEqual(self.c.keys, ["url", "token", "ca_bundle"])
        f = {x.key: x for x in self.c.fields}
        self.assertTrue(f["token"].secret)
        self.assertFalse(f["url"].secret)
        self.assertFalse(any(x.identity for x in self.c.fields))
        self.assertEqual(self.c.kind({"url": "https://sonar.example.com"}), "")
        self.assertEqual(set(self.c.commands),
                         {"gate", "issues", "hotspots", "measures", "rule"})

    def test_module_never_posts(self):
        import ast
        from personal.connectors import sonarqube
        from pathlib import Path
        tree = ast.parse(Path(sonarqube.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, ("_send", "_exchange"))
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertNotIn(node.value, ("POST", "PUT", "PATCH", "DELETE"))
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.assertNotIn(a.name, ("urllib.request", "http.client"))
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module or "", ("urllib.request", "http.client"))


class TestAuth(Base):
    def test_header_is_basic_token_colon_empty(self):
        srv = self.srv({"/api/users/current": ME})
        self.cmd(srv, "whoami")
        want = "Basic " + base64.b64encode(f"{TOKEN}:".encode()).decode()
        for r in srv.requests:
            self.assertEqual(r.headers["Authorization"], want)
            self.assertEqual(r.method, "GET")

    def test_the_token_is_scrubbed_from_errors_and_debug(self):
        from personal.connectors import http
        srv = self.srv({"/api/qualitygates/project_status":
                        Reply(400, {"errors": [{"msg": "bad token " + TOKEN}],
                                    "message": "bad token " + TOKEN})})
        err = io.StringIO()
        with mock.patch.dict(os.environ, {"AI_SDLC_DEBUG": "1"}), \
                contextlib.redirect_stderr(err):
            with self.assertRaises(http.ConnectorError) as cm:
                self.cmd(srv, "gate", PROJECT)
        self.assertIn(http.REDACTED, str(cm.exception))
        self.assertNotIn(TOKEN, str(cm.exception))
        self.assertIn("> Authorization: <redacted>", err.getvalue())
        self.assertNotIn(TOKEN, err.getvalue())
        encoded = base64.b64encode(f"{TOKEN}:".encode()).decode()
        self.assertNotIn(encoded, err.getvalue() + str(cm.exception))

    def test_the_auth_lists_the_token_as_a_secret(self):
        a = self.c.auth({"url": "https://sonar.example.com", "token": TOKEN})
        self.assertIn(TOKEN, a.secrets())
        self.assertIn(base64.b64encode(f"{TOKEN}:".encode()).decode(), a.secrets())

    def test_secret_absent_from_all_cli_output(self):
        srv = self.srv({
            "/api/users/current": ME,
            "/api/qualitygates/project_status": {"projectStatus": {"status": "OK",
                                                                   "conditions": []}},
            "/api/issues/search": paged([new_issue("I1")]),
            "/api/hotspots/search": paged([], key="hotspots"),
            "/api/measures/component": {"component": {"key": PROJECT, "name": "Demo",
                                                      "measures": []}},
            "/api/rules/show": Reply(401, {"errors": [{"msg": "token " + TOKEN}]}),
        })
        outputs = []
        for argv in (["whoami"], ["gate", PROJECT], ["issues", PROJECT],
                     ["hotspots", PROJECT], ["measures", PROJECT], ["rule", "java:S1"]):
            for extra in ([], ["--json"]):
                code, out, err = self.run_cli(self.c, argv + extra, values=self.values(srv))
                outputs.append(out + err)
        blob = "\n".join(outputs)
        self.assertNotIn(TOKEN, blob)
        self.assertNotIn(base64.b64encode(f"{TOKEN}:".encode()).decode(), blob)
        self.assertIn("setup.py connect sonarqube", blob)


class TestVersion(Base):
    def test_read_once_for_three_commands_in_one_run(self):
        srv = self.srv({"/api/users/current": ME,
                        "/api/issues/search": paged([new_issue("I1")]),
                        "/api/rules/show": {"rule": {"key": "java:S1", "name": "R"}}})
        ctx = self.ctx(srv)
        self.cmd(srv, "whoami", ctx=ctx)
        self.cmd(srv, "issues", PROJECT, ctx=ctx)
        self.cmd(srv, "issues", PROJECT, "--severity", "high", ctx=ctx)
        self.assertEqual(len(self.api(srv, "/api/server/version")), 1)

    def test_unreadable_version_is_null_and_treated_as_new(self):
        srv = self.srv({"/api/issues/search": paged([new_issue("I1")])}, ver=None)
        r = self.cmd(srv, "issues", PROJECT, "--severity", "blocker")
        self.assertIsNone(r.extra["server_version"])
        q = self.api(srv, "/api/issues/search")[0].query
        self.assertEqual(q["components"], [PROJECT])
        self.assertEqual(q["impactSeverities"], ["BLOCKER"])

    def test_parse_versions(self):
        from personal.connectors import sonarqube
        self.assertEqual(sonarqube.parse_version("9.9.4.87374"), (9, 9))
        self.assertEqual(sonarqube.parse_version("10.6.0.92116\n"), (10, 6))
        self.assertEqual(sonarqube.parse_version("2025.1.0.102418"), (2025, 1))
        self.assertEqual(sonarqube.parse_version("25.1.0.102122"), (2025, 1))  # Community Build
        self.assertIsNone(sonarqube.parse_version("<html>login</html>"))
        self.assertIsNone(sonarqube.parse_version(""))


class TestWhoami(Base):
    def test_whoami(self):
        srv = self.srv({"/api/users/current": ME})
        r = self.cmd(srv, "whoami")
        self.assertEqual(r.item, {"user": "ana", "display_name": "Ana Pop",
                                  "email": "ana@example.com", "server_version": "10.6",
                                  "url": f"{srv.url}/account"})

    def test_anonymous_is_unauthorized(self):
        from personal.connectors import http
        srv = self.srv({"/api/users/current": {"isLoggedIn": False}})
        with self.assertRaises(http.ConnectorError) as cm:
            self.cmd(srv, "whoami")
        self.assertEqual(cm.exception.kind, "unauthorized")
        self.assertIn("token was not accepted", str(cm.exception))

    def test_anonymous_cli_says_how_to_connect(self):
        srv = self.srv({"/api/users/current": {"isLoggedIn": False}})
        code, out, err = self.run_cli(self.c, ["whoami"], values=self.values(srv))
        self.assertEqual(code, 1)
        self.assertIn("anonymous", err)
        self.assertIn("setup.py connect sonarqube", err)


GATE = {"projectStatus": {
    "status": "ERROR",
    "conditions": [
        {"status": "OK", "metricKey": "new_reliability_rating", "comparator": "GT",
         "errorThreshold": "1", "actualValue": "1"},
        {"status": "ERROR", "metricKey": "new_coverage", "comparator": "LT",
         "errorThreshold": "80", "actualValue": "61.5"},
        {"status": "ERROR", "metricKey": "new_duplicated_lines_density", "comparator": "GT",
         "errorThreshold": "3", "actualValue": "7.2"},
    ],
    "ignoredConditions": False,
    "period": {"mode": "PREVIOUS_VERSION", "date": "2026-09-01T10:00:00+0000",
               "parameter": "1.4"},
}}


class TestGate(Base):
    def test_gate_with_two_failed_conditions(self):
        srv = self.srv({"/api/qualitygates/project_status": GATE})
        r = self.cmd(srv, "gate", PROJECT)
        self.assertEqual(self.api(srv, "/api/qualitygates/project_status")[0].query,
                         {"projectKey": [PROJECT]})
        self.assertEqual(r.item, {
            "project": PROJECT, "status": "ERROR",
            "failed": [
                {"metric": "new_coverage", "comparator": "LT", "threshold": "80",
                 "actual": "61.5"},
                {"metric": "new_duplicated_lines_density", "comparator": "GT",
                 "threshold": "3", "actual": "7.2"}],
            "conditions": [
                {"metric": "new_reliability_rating", "status": "OK", "comparator": "GT",
                 "threshold": "1", "actual": "1"},
                {"metric": "new_coverage", "status": "ERROR", "comparator": "LT",
                 "threshold": "80", "actual": "61.5"},
                {"metric": "new_duplicated_lines_density", "status": "ERROR",
                 "comparator": "GT", "threshold": "3", "actual": "7.2"}],
            "new_code_period": {"mode": "PREVIOUS_VERSION",
                                "date": "2026-09-01T10:00:00+0000", "parameter": "1.4"},
            "url": f"{srv.url}/dashboard?id={PROJECT}"})
        self.assertIn("ERROR", r.lines[0])
        self.assertTrue(any("new_coverage" in line for line in r.lines))

    def test_gate_ok_has_no_failed_and_periods_list(self):
        data = {"projectStatus": {"status": "OK", "conditions": [],
                                  "periods": [{"index": 1, "mode": "NUMBER_OF_DAYS",
                                               "date": "2026-09-10T00:00:00+0000",
                                               "parameter": "30"}]}}
        srv = self.srv({"/api/qualitygates/project_status": data})
        r = self.cmd(srv, "gate", PROJECT)
        self.assertEqual(r.item["failed"], [])
        self.assertEqual(r.item["new_code_period"],
                         {"mode": "NUMBER_OF_DAYS", "date": "2026-09-10T00:00:00+0000",
                          "parameter": "30"})

    def test_gate_unknown_project_is_404(self):
        from personal.connectors import http
        srv = self.srv({"/api/qualitygates/project_status":
                        Reply(404, {"errors": [{"msg": "Project 'nope' not found"}]})})
        with self.assertRaises(http.ConnectorError) as cm:
            self.cmd(srv, "gate", "nope")
        self.assertEqual(cm.exception.kind, "not_found")


ISSUE_KEYS = {"key", "rule", "message", "severity", "type", "impacts", "clean_code_attribute",
              "status", "file", "line", "effort", "tags", "created", "updated", "url"}


class TestIssues(Base):
    def test_old_server_params_and_shape(self):
        srv = self.srv({"/api/issues/search": paged([issue("AX1")])}, ver="9.9.4.87374")
        r = self.cmd(srv, "issues", PROJECT, "--severity", "high", "--type", "bug")
        q = self.api(srv, "/api/issues/search")[0].query
        self.assertEqual(q["componentKeys"], [PROJECT])
        self.assertNotIn("components", q)
        self.assertEqual(q["severities"], ["BLOCKER,CRITICAL"])
        self.assertEqual(q["types"], ["BUG"])
        self.assertEqual(q["resolved"], ["false"])
        self.assertEqual((q["p"], q["ps"]), (["1"], ["100"]))
        self.assertEqual(r.items, [{
            "key": "AX1", "rule": "java:S2095", "message": "Use try-with-resources",
            "severity": "CRITICAL", "type": "BUG", "impacts": [], "clean_code_attribute": None,
            "status": "OPEN", "file": "src/main/java/App.java", "line": 42, "effort": "5min",
            "tags": ["cwe"], "created": "2026-10-01T10:00:00+0000",
            "updated": "2026-10-02T10:00:00+0000",
            "url": f"{srv.url}/project/issues?id={PROJECT}&open=AX1"}])
        self.assertEqual(r.extra, {"server_version": "9.9",
                                   "filter_sent": {"componentKeys": PROJECT,
                                                   "resolved": "false",
                                                   "severities": "BLOCKER,CRITICAL",
                                                   "types": "BUG"}})
        self.assertFalse(r.truncated)

    def test_new_server_params_and_shape(self):
        srv = self.srv({"/api/issues/search": paged([new_issue("AY1")])}, ver="10.6.0.92116")
        r = self.cmd(srv, "issues", PROJECT, "--severity", "high", "--type", "reliability")
        q = self.api(srv, "/api/issues/search")[0].query
        self.assertEqual(q["components"], [PROJECT])
        self.assertNotIn("componentKeys", q)
        self.assertEqual(q["impactSeverities"], ["HIGH"])
        self.assertEqual(q["impactSoftwareQualities"], ["RELIABILITY"])
        self.assertNotIn("severities", q)
        it = r.items[0]
        self.assertEqual(set(it), ISSUE_KEYS)
        self.assertIsNone(it["severity"])
        self.assertIsNone(it["type"])
        self.assertEqual(it["impacts"], [{"quality": "RELIABILITY", "severity": "HIGH"}])
        self.assertEqual(it["clean_code_attribute"], "COMPLETE")
        self.assertEqual(r.extra["filter_sent"]["impactSeverities"], "HIGH")
        self.assertEqual(r.extra["server_version"], "10.6")

    def test_10_4_issue_status_wins(self):
        srv = self.srv({"/api/issues/search": paged([new_issue("AY2", issueStatus="CONFIRMED",
                                                               status="OPEN")])})
        r = self.cmd(srv, "issues", PROJECT)
        self.assertEqual(r.items[0]["status"], "CONFIRMED")

    def test_blocker_and_info_by_version(self):
        cases = [("10.6.0.1", "blocker", "HIGH"), ("10.6.0.1", "info", "LOW"),
                 ("2025.1.0.1", "blocker", "BLOCKER"), ("2025.1.0.1", "info", "INFO"),
                 ("25.2.0.1", "blocker", "BLOCKER"),
                 ("9.9.0.1", "blocker", "BLOCKER"), ("9.9.0.1", "low", "MINOR,INFO")]
        for ver, sev, want in cases:
            with self.subTest(ver=ver, sev=sev):
                srv = self.srv({"/api/issues/search": paged([])}, ver=ver)
                self.cmd(srv, "issues", PROJECT, "--severity", sev)
                q = self.api(srv, "/api/issues/search")[0].query
                param = "severities" if ver.startswith("9.") else "impactSeverities"
                self.assertEqual(q[param], [want])

    def test_comma_lists_merge_without_duplicates(self):
        srv = self.srv({"/api/issues/search": paged([])}, ver="10.6.0.1")
        r = self.cmd(srv, "issues", PROJECT, "--severity", "critical,high,major",
                     "--type", "security,vulnerability,code_smell")
        self.assertEqual(r.extra["filter_sent"]["impactSeverities"], "HIGH,MEDIUM")
        self.assertEqual(r.extra["filter_sent"]["impactSoftwareQualities"],
                         "SECURITY,MAINTAINABILITY")

    def test_unknown_severity_is_a_usage_error(self):
        srv = self.srv({"/api/issues/search": paged([])})
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            self.cmd(srv, "issues", PROJECT, "--severity", "huge")
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("blocker", err.getvalue())
        self.assertEqual(self.api(srv, "/api/issues/search"), [])

    def test_both_shapes_are_kept(self):
        both = new_issue("AZ1", severity="MAJOR", type="CODE_SMELL")
        srv = self.srv({"/api/issues/search": paged([both])})
        it = self.cmd(srv, "issues", PROJECT).items[0]
        self.assertEqual((it["severity"], it["type"]), ("MAJOR", "CODE_SMELL"))
        self.assertEqual(it["impacts"], [{"quality": "RELIABILITY", "severity": "HIGH"}])

    def test_file_rule_and_new_code(self):
        srv = self.srv({"/api/issues/search": paged([new_issue("F1")])})
        r = self.cmd(srv, "issues", PROJECT, "--file", "src/A.java", "--rule", "java:S2095",
                     "--new-code")
        q = self.api(srv, "/api/issues/search")[0].query
        self.assertEqual(q["components"], [f"{PROJECT}:src/A.java"])
        self.assertEqual(q["rules"], ["java:S2095"])
        self.assertEqual(q["inNewCodePeriod"], ["true"])
        self.assertEqual(r.items[0]["file"], "src/A.java")
        self.assertEqual(r.extra["filter_sent"]["inNewCodePeriod"], "true")

    def test_file_on_old_server_uses_component_keys(self):
        srv = self.srv({"/api/issues/search": paged([])}, ver="9.9.0.1")
        self.cmd(srv, "issues", PROJECT, "--file", "src/A.java")
        q = self.api(srv, "/api/issues/search")[0].query
        self.assertEqual(q["componentKeys"], [f"{PROJECT}:src/A.java"])

    def test_two_pages_and_truncated(self):
        rows = [new_issue(f"K{i}") for i in range(1, 251)]
        srv = self.srv({"/api/issues/search": paged(rows)})
        r = self.cmd(srv, "issues", PROJECT, "--limit", "150")
        self.assertEqual([x["key"] for x in r.items], [f"K{i}" for i in range(1, 151)])
        self.assertTrue(r.truncated)
        reqs = self.api(srv, "/api/issues/search")
        self.assertEqual([(q.query["p"][0], q.query["ps"][0]) for q in reqs],
                         [("1", "100"), ("2", "100")])
        self.assertNotIn("capped_at", r.extra)

    def test_all_pages_not_truncated(self):
        rows = [new_issue(f"K{i}") for i in range(1, 121)]
        srv = self.srv({"/api/issues/search": paged(rows)})
        r = self.cmd(srv, "issues", PROJECT, "--limit", "500")
        self.assertEqual(len(r.items), 120)
        self.assertFalse(r.truncated)
        self.assertEqual(len(self.api(srv, "/api/issues/search")), 2)

    def test_the_search_cap(self):
        from personal.connectors import sonarqube
        rows = [new_issue(f"K{i}") for i in range(1, 51)]
        srv = self.srv({"/api/issues/search": paged(rows)})
        with mock.patch.object(sonarqube, "PAGE", 10), mock.patch.object(sonarqube, "CAP", 30):
            r = self.cmd(srv, "issues", PROJECT, "--limit", "100")
        self.assertEqual(len(self.api(srv, "/api/issues/search")), 3)
        self.assertEqual(len(r.items), 30)
        self.assertTrue(r.truncated)
        self.assertEqual(r.extra["capped_at"], 30)

    def test_json_end_to_end_and_get_only(self):
        srv = self.srv({"/api/issues/search": paged([new_issue("J1")])})
        code, out, err = self.run_cli(self.c, ["issues", PROJECT, "--severity", "high",
                                               "--json"], values=self.values(srv))
        self.assertEqual((code, err), (0, ""))
        doc = json.loads(out)
        self.assertEqual((doc["connector"], doc["command"], doc["source"]),
                         ("sonarqube", "issues", srv.url))
        self.assertEqual(doc["count"], 1)
        self.assertFalse(doc["truncated"])
        self.assertEqual(doc["items"][0]["key"], "J1")
        self.assertTrue(doc["items"][0]["url"].startswith(srv.url))
        self.assertEqual(doc["server_version"], "10.6")
        self.assertEqual(doc["filter_sent"]["impactSeverities"], "HIGH")
        self.assertTrue(all(r.method == "GET" for r in srv.requests))

    def test_plain_text_lists_issues_with_links(self):
        srv = self.srv({"/api/issues/search": paged([new_issue("T1")])})
        code, out, _ = self.run_cli(self.c, ["issues", PROJECT], values=self.values(srv))
        self.assertEqual(code, 0)
        self.assertIn("T1", out)
        self.assertIn("src/A.java:7", out)
        self.assertIn(f"{srv.url}/project/issues?id={PROJECT}&open=T1", out)


class TestHotspots(Base):
    HOT = {"key": "H1", "component": f"{PROJECT}:src/Db.java", "project": PROJECT,
           "securityCategory": "sql-injection", "vulnerabilityProbability": "HIGH",
           "status": "TO_REVIEW", "line": 12, "message": "Make sure this query is safe",
           "ruleKey": "java:S2077", "creationDate": "2026-10-01T10:00:00+0000"}

    def test_default_status_and_shape(self):
        srv = self.srv({"/api/hotspots/search": paged([self.HOT], key="hotspots")})
        r = self.cmd(srv, "hotspots", PROJECT)
        q = self.api(srv, "/api/hotspots/search")[0].query
        self.assertEqual(q["project"], [PROJECT])
        self.assertEqual(q["status"], ["TO_REVIEW"])
        self.assertEqual(r.items, [{
            "key": "H1", "rule": "java:S2077", "category": "sql-injection",
            "probability": "HIGH", "status": "TO_REVIEW", "resolution": None,
            "message": "Make sure this query is safe", "file": "src/Db.java", "line": 12,
            "url": f"{srv.url}/security_hotspots?id={PROJECT}&hotspots=H1"}])

    def test_reviewed(self):
        srv = self.srv({"/api/hotspots/search": paged([], key="hotspots")})
        self.cmd(srv, "hotspots", PROJECT, "--status", "REVIEWED")
        self.assertEqual(self.api(srv, "/api/hotspots/search")[0].query["status"],
                         ["REVIEWED"])


class TestMeasures(Base):
    def test_measures_with_a_missing_metric(self):
        data = {"component": {"key": PROJECT, "name": "Demo App", "qualifier": "TRK",
                              "measures": [
                                  {"metric": "bugs", "value": "3"},
                                  {"metric": "coverage", "value": "71.2"},
                                  {"metric": "new_coverage", "period": {"index": 1,
                                                                        "value": "64.0"}},
                                  {"metric": "new_violations",
                                   "periods": [{"index": 1, "value": "5"}]}]}}
        srv = self.srv({"/api/measures/component": data})
        r = self.cmd(srv, "measures", PROJECT, "--metrics",
                     "bugs,coverage,new_coverage,new_violations,sqale_rating")
        q = self.api(srv, "/api/measures/component")[0].query
        self.assertEqual(q["component"], [PROJECT])
        self.assertEqual(q["metricKeys"],
                         ["bugs,coverage,new_coverage,new_violations,sqale_rating"])
        self.assertEqual(r.item, {
            "project": PROJECT, "name": "Demo App",
            "measures": {"bugs": "3", "coverage": "71.2"},
            "new_code": {"new_coverage": "64.0", "new_violations": "5"},
            "missing": ["sqale_rating"],
            "url": f"{srv.url}/dashboard?id={PROJECT}"})

    def test_default_metrics(self):
        from personal.connectors import sonarqube
        srv = self.srv({"/api/measures/component": {"component": {"key": PROJECT,
                                                                  "name": "D",
                                                                  "measures": []}}})
        r = self.cmd(srv, "measures", PROJECT)
        sent = self.api(srv, "/api/measures/component")[0].query["metricKeys"][0]
        self.assertEqual(sent, sonarqube.DEFAULT_METRICS)
        self.assertIn("coverage", sent.split(","))
        self.assertEqual(r.item["missing"], sent.split(","))


class TestRule(Base):
    def test_rule_from_description_sections(self):
        data = {"rule": {
            "key": "java:S2095", "repo": "java", "name": "Resources should be closed",
            "langName": "Java", "type": "BUG", "severity": "BLOCKER",
            "impacts": [{"softwareQuality": "RELIABILITY", "severity": "HIGH"}],
            "cleanCodeAttribute": "COMPLETE",
            "descriptionSections": [
                {"key": "root_cause", "content": "<p>Connections <b>must</b> be closed.</p>"},
                {"key": "how_to_fix", "content": "<pre>try (var c = open()) {}</pre>"}]}}
        srv = self.srv({"/api/rules/show": data})
        r = self.cmd(srv, "rule", "java:S2095")
        self.assertEqual(self.api(srv, "/api/rules/show")[0].query, {"key": ["java:S2095"]})
        self.assertEqual(r.item, {
            "key": "java:S2095", "name": "Resources should be closed", "language": "Java",
            "severity": "BLOCKER", "type": "BUG",
            "impacts": [{"quality": "RELIABILITY", "severity": "HIGH"}],
            "clean_code_attribute": "COMPLETE",
            "description": "Root cause\nConnections must be closed.\nHow to fix\n"
                           "try (var c = open()) {}",
            "description_truncated": False,
            "url": f"{srv.url}/coding_rules?open=java%3AS2095&rule_key=java%3AS2095"})

    def test_rule_html_desc_clipped(self):
        data = {"rule": {"key": "js:S1", "name": "Old rule", "langName": "JavaScript",
                         "htmlDesc": "<p>" + "x" * 300 + "</p>"}}
        srv = self.srv({"/api/rules/show": data})
        r = self.cmd(srv, "rule", "js:S1", "--max-chars", "100")
        self.assertEqual(len(r.item["description"]), 100)
        self.assertTrue(r.item["description_truncated"])
        self.assertIsNone(r.item["severity"])
        self.assertEqual(r.item["impacts"], [])
        self.assertIsNone(r.item["clean_code_attribute"])


if __name__ == "__main__":
    unittest.main()
