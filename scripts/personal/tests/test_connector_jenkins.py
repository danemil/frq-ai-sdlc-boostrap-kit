#!/usr/bin/env python3
"""The jenkins connector against the fake server: whoami, job, build, tests (read-only)."""
from __future__ import annotations

import contextlib
import io
import json
import unittest

import helpers  # noqa: F401  (puts scripts/ on sys.path)
from fakeserver import ConnectorTestCase, Reply

SECRET = "jenkins-api-token-s3cr3t-0042"
USER = "ana"

ME = {"_class": "hudson.model.User", "id": "ana", "fullName": "Ana Example"}

JOB = {
    "_class": "org.jenkinsci.plugins.workflow.job.WorkflowJob",
    "name": "main",
    "fullName": "team/app/main",
    "url": "SERVER/job/team/job/app/job/main/",
    "color": "blue_anime",
    "description": "Main branch build",
    "lastBuild": {"number": 42, "url": "SERVER/job/team/job/app/job/main/42/",
                  "result": None, "timestamp": 1791451800000},
    "lastSuccessfulBuild": {"number": 41, "url": "SERVER/job/team/job/app/job/main/41/"},
    "lastFailedBuild": None,
    "healthReport": [{"description": "Build stability: No recent builds failed.",
                      "score": 100}],
}

FOLDER = {
    "_class": "com.cloudbees.hudson.plugins.folder.Folder",
    "name": "app",
    "fullName": "team/app",
    "url": "SERVER/job/team/job/app/",
    "description": None,
    "healthReport": [],
    "jobs": [
        {"_class": "WorkflowJob", "name": "main", "url": "SERVER/job/team/job/app/job/main/",
         "color": "red"},
        {"_class": "WorkflowJob", "name": "feature x", "url":
         "SERVER/job/team/job/app/job/feature%20x/", "color": "notbuilt"},
    ],
}

BUILD = {
    "_class": "org.jenkinsci.plugins.workflow.job.WorkflowRun",
    "number": 41,
    "url": "SERVER/job/team/job/app/job/main/41/",
    "result": "SUCCESS",
    "building": False,
    "timestamp": 1791451800000,
    "duration": 125500,
    "displayName": "#41",
    "description": None,
    "changeSets": [{"items": [
        {"commitId": "abc123", "msg": "Fix login", "author": {"fullName": "Bo Dev"}},
        {"commitId": "def456", "msg": "Add test", "author": {"fullName": "Cy Dev"}},
    ]}],
    "actions": [
        {"_class": "hudson.model.CauseAction",
         "causes": [{"shortDescription": "Started by user Ana Example"}]},
        {"_class": "hudson.model.ParametersAction", "parameters": [
            {"_class": "hudson.model.StringParameterValue", "name": "ENV", "value": "qa"},
            {"_class": "hudson.model.PasswordParameterValue", "name": "DB_PASS",
             "value": "hunter2-param"},
            {"_class": "hudson.model.BooleanParameterValue", "name": "DRY", "value": True},
        ]},
        {},
    ],
}

FREESTYLE_BUILD = {
    "number": 7, "result": "FAILURE", "building": False, "timestamp": 1791451800000,
    "duration": 2000, "displayName": "#7",
    "changeSet": {"items": [{"commitId": "aaa111", "msg": "Tweak", "author":
                             {"fullName": "Di Dev"}}]},
    "actions": [],
}

REPORT = {
    "_class": "hudson.tasks.junit.TestResult",
    "failCount": 2, "passCount": 3, "skipCount": 1, "duration": 12.5,
    "suites": [
        {"name": "LoginTest", "cases": [
            {"className": "app.LoginTest", "name": "ok", "status": "PASSED",
             "duration": 0.5, "errorDetails": None},
            {"className": "app.LoginTest", "name": "bad_password", "status": "FAILED",
             "duration": 1.25, "errorDetails": "expected 401 " + "x" * 3000},
            {"className": "app.LoginTest", "name": "fixed", "status": "FIXED",
             "duration": 0.1, "errorDetails": None},
        ]},
        {"name": "CartTest", "cases": [
            {"className": "app.CartTest", "name": "total", "status": "REGRESSION",
             "duration": 2.0, "errorDetails": "1 != 2"},
            {"className": "app.CartTest", "name": "empty", "status": "PASSED",
             "duration": 0.2, "errorDetails": None},
            {"className": "app.CartTest", "name": "later", "status": "SKIPPED",
             "duration": 0.0, "errorDetails": None},
        ]},
    ],
}

JOB_KEYS = {"name", "full_name", "status", "building", "health", "last_build", "last_success",
            "last_failure", "children", "url"}
BUILD_KEYS = {"number", "display_name", "result", "building", "started", "duration_s",
              "causes", "parameters", "changes", "url"}
TESTS_KEYS = {"fail", "pass", "skip", "duration_s", "cases", "url"}
CASE_KEYS = {"class", "name", "status", "duration_s", "error"}


def with_server(doc, srv):
    """`doc` with every "SERVER" prefix replaced by the fake server's URL."""
    return json.loads(json.dumps(doc).replace("SERVER", srv.url))


class JenkinsCase(ConnectorTestCase):
    def setUp(self):
        super().setUp()
        self.c = self.connector("jenkins")

    def values(self, srv):
        return {"url": srv.url, "username": USER, "token": SECRET}

    def ctx(self, srv):
        return self.context(self.c, self.values(srv))

    def serve(self, routes):
        srv = self.server({})
        srv.routes.update({k: with_server(v, srv) if isinstance(v, (dict, list)) else v
                           for k, v in routes.items()})
        return srv

    def tree(self, srv, i=-1):
        return srv.requests[i].query["tree"][0]


class TestContract(JenkinsCase):
    def test_registry_validates_the_module(self):
        self.assertEqual(self.c.title, "Jenkins")
        self.assertEqual(self.c.keys, ["url", "username", "token", "ca_bundle"])
        self.assertEqual(set(self.c.commands), {"job", "build", "tests"})
        self.assertEqual(self.c.kind({"url": "https://jenkins.example.com"}), "")

    def test_fields(self):
        f = {x.key: x for x in self.c.fields}
        self.assertTrue(f["username"].identity)
        self.assertFalse(f["username"].secret)
        self.assertTrue(f["token"].secret)
        self.assertFalse(f["url"].secret)
        self.assertEqual([x.key for x in self.c.applicable({})],
                         ["url", "username", "token", "ca_bundle"])
        self.assertEqual(self.c.identity({"username": "ana"}), "ana")

    def test_job_paths_and_refs(self):
        from personal.connectors import jenkins
        self.assertEqual(jenkins.job_path("a/b/c"), "/job/a/job/b/job/c")
        self.assertEqual(jenkins.job_path("job/a/job/b/job/c"), "/job/a/job/b/job/c")
        self.assertEqual(jenkins.job_path("/team/feature x/"), "/job/team/job/feature%20x")
        self.assertEqual(jenkins.job_path("team/feature%2Fy"), "/job/team/job/feature%2Fy")
        self.assertEqual(jenkins.job_path("a#b?c"), "/job/a%23b%3Fc")
        self.assertEqual(jenkins.build_ref("12"), "12")
        self.assertEqual(jenkins.build_ref("last"), "lastBuild")
        self.assertEqual(jenkins.build_ref("lastSuccessful"), "lastSuccessfulBuild")
        self.assertEqual(jenkins.build_ref("lastFailed"), "lastFailedBuild")
        with self.assertRaises(ValueError):
            jenkins.build_ref("../12")

    def test_status_from_color(self):
        from personal.connectors import jenkins
        cases = {"blue": ("success", False), "red": ("failed", False),
                 "yellow": ("unstable", False), "aborted": ("aborted", False),
                 "disabled": ("disabled", False), "notbuilt": ("not built", False),
                 "red_anime": ("failed", True), "blue_anime": ("success", True),
                 None: (None, False)}
        for color, want in cases.items():
            self.assertEqual(jenkins.status(color), want, color)


class TestWhoami(JenkinsCase):
    def test_whoami_basic_auth_and_tree(self):
        srv = self.serve({"/me/api/json": ME})
        r = self.run_command(self.c, self.ctx(srv), ["whoami"])
        self.assertEqual(r.item, {"user": "ana", "display_name": "Ana Example",
                                  "url": srv.url + "/user/ana"})
        req = srv.requests[0]
        self.assertEqual(req.method, "GET")
        self.assertEqual(self.tree(srv), "id,fullName")
        import base64
        want = base64.b64encode(f"{USER}:{SECRET}".encode()).decode()
        self.assertEqual(req.headers["Authorization"], "Basic " + want)

    def test_anonymous_is_unauthorized(self):
        from personal.connectors import http
        srv = self.serve({"/me/api/json": {"id": "anonymous", "fullName": "anonymous"}})
        with self.assertRaises(http.ConnectorError) as cm:
            self.run_command(self.c, self.ctx(srv), ["whoami"])
        self.assertEqual(cm.exception.kind, "unauthorized")
        self.assertIn("anonymous", str(cm.exception))


class TestJob(JenkinsCase):
    def test_job_request_and_shape(self):
        srv = self.serve({"/job/team/job/app/job/main/api/json": JOB})
        r = self.run_command(self.c, self.ctx(srv), ["job", "team/app/main"])
        self.assertEqual(srv.requests[0].path, "/job/team/job/app/job/main/api/json")
        tree = self.tree(srv)
        for part in ("name", "fullName", "color", "lastBuild[number,url,result,timestamp]",
                     "lastSuccessfulBuild[number,url]", "lastFailedBuild[number,url]",
                     "healthReport[description,score]", "jobs[name,url,color]"):
            self.assertIn(part, tree)
        it = r.item
        self.assertEqual(set(it), JOB_KEYS)
        self.assertEqual(it["name"], "main")
        self.assertEqual(it["full_name"], "team/app/main")
        self.assertEqual((it["status"], it["building"]), ("success", True))
        self.assertEqual(it["health"], [{"score": 100, "description":
                                         "Build stability: No recent builds failed."}])
        self.assertEqual(it["last_build"], {"number": 42, "result": None,
                                            "at": "2026-10-08T09:30:00Z",
                                            "url": srv.url + "/job/team/job/app/job/main/42/"})
        self.assertEqual(it["last_success"], {"number": 41, "url": srv.url +
                                              "/job/team/job/app/job/main/41/"})
        self.assertIsNone(it["last_failure"])
        self.assertEqual(it["children"], [])
        self.assertEqual(it["url"], srv.url + "/job/team/job/app/job/main/")

    def test_folder_children_and_missing_url_is_built(self):
        folder = dict(FOLDER)
        del folder["url"]
        srv = self.serve({"/job/team/job/app/api/json": folder})
        r = self.run_command(self.c, self.ctx(srv), ["job", "job/team/job/app"])
        it = r.item
        self.assertEqual(it["url"], srv.url + "/job/team/job/app/")
        self.assertIsNone(it["status"])
        self.assertFalse(it["building"])
        self.assertIsNone(it["last_build"])
        self.assertEqual(it["children"], [
            {"name": "main", "status": "failed",
             "url": srv.url + "/job/team/job/app/job/main/"},
            {"name": "feature x", "status": "not built",
             "url": srv.url + "/job/team/job/app/job/feature%20x/"}])

    def test_missing_job_is_not_found(self):
        from personal.connectors import http
        srv = self.serve({})
        with self.assertRaises(http.ConnectorError) as cm:
            self.run_command(self.c, self.ctx(srv), ["job", "nope"])
        self.assertEqual(cm.exception.kind, "not_found")
        self.assertEqual(srv.requests[0].path, "/job/nope/api/json")


class TestBuild(JenkinsCase):
    def test_build_request_and_shape(self):
        srv = self.serve({"/job/team/job/app/job/main/lastSuccessfulBuild/api/json": BUILD})
        r = self.run_command(self.c, self.ctx(srv), ["build", "team/app/main",
                                                      "lastSuccessful"])
        tree = self.tree(srv)
        for part in ("number", "url", "result", "building", "timestamp", "duration",
                     "displayName", "description",
                     "changeSet[items[commitId,msg,author[fullName]]]",
                     "changeSets[items[commitId,msg,author[fullName]]]",
                     "actions[causes[shortDescription],parameters[_class,name,value]]"):
            self.assertIn(part, tree)
        it = r.item
        self.assertEqual(set(it), BUILD_KEYS)
        self.assertEqual(it["number"], 41)
        self.assertEqual(it["display_name"], "#41")
        self.assertEqual(it["result"], "SUCCESS")
        self.assertFalse(it["building"])
        self.assertEqual(it["started"], "2026-10-08T09:30:00Z")
        self.assertEqual(it["duration_s"], 125.5)
        self.assertEqual(it["causes"], ["Started by user Ana Example"])
        self.assertEqual(it["parameters"], [{"name": "ENV", "value": "qa"},
                                            {"name": "DRY", "value": True}])
        self.assertNotIn("hunter2-param", json.dumps(it))
        self.assertEqual(it["changes"], [
            {"commit": "abc123", "message": "Fix login", "author": "Bo Dev"},
            {"commit": "def456", "message": "Add test", "author": "Cy Dev"}])
        self.assertEqual(it["url"], srv.url + "/job/team/job/app/job/main/41/")

    def test_freestyle_build_by_number_with_built_url(self):
        srv = self.serve({"/job/tool/7/api/json": FREESTYLE_BUILD})
        r = self.run_command(self.c, self.ctx(srv), ["build", "tool", "7"])
        it = r.item
        self.assertEqual(it["changes"], [{"commit": "aaa111", "message": "Tweak",
                                          "author": "Di Dev"}])
        self.assertEqual((it["causes"], it["parameters"]), ([], []))
        self.assertEqual((it["result"], it["duration_s"]), ("FAILURE", 2.0))
        self.assertEqual(it["url"], srv.url + "/job/tool/7/")

    def test_bad_ref_is_a_usage_error(self):
        srv = self.serve({})
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            self.run_command(self.c, self.ctx(srv), ["build", "tool", "latest"])
        self.assertEqual(cm.exception.code, 2)
        self.assertEqual(srv.requests, [])


class TestTests(JenkinsCase):
    def test_failures_only_by_default(self):
        srv = self.serve({"/job/team/job/app/job/main/lastBuild/testReport/api/json": REPORT})
        r = self.run_command(self.c, self.ctx(srv), ["tests", "team/app/main", "last"])
        self.assertEqual(self.tree(srv), "failCount,passCount,skipCount,duration,"
                         "suites[name,cases[className,name,status,duration,errorDetails]]")
        it = r.item
        self.assertEqual(set(it), TESTS_KEYS)
        self.assertEqual((it["fail"], it["pass"], it["skip"], it["duration_s"]),
                         (2, 3, 1, 12.5))
        self.assertEqual([(c["class"], c["name"], c["status"]) for c in it["cases"]],
                         [("app.LoginTest", "bad_password", "FAILED"),
                          ("app.CartTest", "total", "REGRESSION")])
        for case in it["cases"]:
            self.assertEqual(set(case), CASE_KEYS)
        self.assertEqual(len(it["cases"][0]["error"]), 2000)
        self.assertEqual(it["cases"][1]["error"], "1 != 2")
        self.assertEqual(it["cases"][1]["duration_s"], 2.0)
        self.assertEqual(it["url"], srv.url +
                         "/job/team/job/app/job/main/lastBuild/testReport/")

    def test_all_lists_every_case(self):
        srv = self.serve({"/job/tool/12/testReport/api/json": REPORT})
        r = self.run_command(self.c, self.ctx(srv), ["tests", "tool", "12", "--all"])
        self.assertEqual(len(r.item["cases"]), 6)
        self.assertIsNone(r.item["cases"][0]["error"])
        self.assertEqual(r.item["url"], srv.url + "/job/tool/12/testReport/")

    def test_no_test_report_is_not_found(self):
        from personal.connectors import http
        srv = self.serve({})
        with self.assertRaises(http.ConnectorError) as cm:
            self.run_command(self.c, self.ctx(srv), ["tests", "team/app", "5"])
        self.assertEqual(cm.exception.kind, "not_found")
        self.assertEqual(str(cm.exception), "Build 5 of team/app has no test report.")


class TestCli(JenkinsCase):
    def test_json_end_to_end_and_get_only(self):
        srv = self.serve({"/job/team/job/app/job/main/lastBuild/testReport/api/json": REPORT})
        code, out, err = self.run_cli(self.c, ["tests", "team/app/main", "last", "--json"],
                                      values=self.values(srv))
        self.assertEqual((code, err), (0, ""))
        doc = json.loads(out)
        self.assertEqual((doc["connector"], doc["command"], doc["source"]),
                         ("jenkins", "tests", srv.url))
        self.assertEqual(doc["item"]["fail"], 2)
        self.assertTrue(all(r.method == "GET" for r in srv.requests))

    def test_plain_text_names_counts_and_failures(self):
        srv = self.serve({"/job/tool/3/testReport/api/json": REPORT})
        code, out, _ = self.run_cli(self.c, ["tests", "tool", "3"], values=self.values(srv))
        self.assertEqual(code, 0)
        self.assertIn("2 failed, 3 passed, 1 skipped", out)
        self.assertIn("app.CartTest.total", out)
        self.assertIn(srv.url + "/job/tool/3/testReport/", out)

    def test_secret_absent_from_all_output(self):
        srv = self.serve({
            "/me/api/json": ME,
            "/job/a/api/json": JOB,
            "/job/a/1/api/json": BUILD,
            "/job/a/1/testReport/api/json": REPORT,
            "/job/bad/api/json": Reply(401, {"message": "bad token " + SECRET}),
        })
        outputs = []
        for argv in (["whoami"], ["job", "a"], ["build", "a", "1"], ["tests", "a", "1"],
                     ["job", "bad"]):
            for extra in ([], ["--json"]):
                code, out, err = self.run_cli(self.c, argv + extra, values=self.values(srv))
                outputs.append(out + err)
        blob = "\n".join(outputs)
        self.assertNotIn(SECRET, blob)
        self.assertNotIn("hunter2-param", blob)
        self.assertIn("setup.py connect jenkins", blob)

    def test_anonymous_cli_says_how_to_connect(self):
        srv = self.serve({"/me/api/json": {"id": "anonymous"}})
        code, out, err = self.run_cli(self.c, ["whoami"], values=self.values(srv))
        self.assertEqual(code, 1)
        self.assertIn("anonymous", err)
        self.assertIn("setup.py connect jenkins", err)


if __name__ == "__main__":
    unittest.main()
