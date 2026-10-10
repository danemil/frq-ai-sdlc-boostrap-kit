#!/usr/bin/env python3
"""The blackduck connector (Black Duck REST API, API token exchanged for a bearer token)
against tests/fakeserver.py: no network.

Canned answers follow the documented shapes: lists as {"totalCount", "items": [...]},
paged with offset/limit; each object has "_meta": {"href", "links": [{"rel", "href"}]}.

To confirm on a live server (design §9):
- the media types per endpoint: user-4 (current user, token exchange), project-detail-4
  (projects), project-detail-5 (versions), bill-of-materials-6 (vulnerable components,
  components, policy status), component-detail-5 (upgrade guidance); an older server may
  want lower numbers;
- the token-exchange answer field names bearerToken and expiresInMilliseconds;
- the vulnerable-components field names: vulnerabilityWithRemediation.vulnerabilityName,
  .source, .severity, .overallScore (or .baseScore), .remediationStatus,
  .relatedVulnerability (read as a link whose last part is the id, or an object with a
  name); componentVersionOriginId; componentVersion (the href used for upgrade guidance);
- the upgrade guidance path <componentVersion href>/upgrade-guidance and its fields
  shortTerm.versionName and longTerm.versionName (fixed_in);
- that _meta.href + "/components" or "/vulnerability-bom" opens in a browser (the web UI
  uses the same /api/projects/<id>/versions/<id>/... paths), and what a componentVersion
  href (an /api/components/... link, used as a component's url) opens;
- filter=bomPolicy:in_violation on the components endpoint;
- sort=updatedAt desc on the versions endpoint;
- that the hrefs in _meta carry the same host as the saved URL (the client refuses a link
  to another host, e.g. behind a reverse proxy with another name).
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import unittest
from unittest import mock

import helpers  # noqa: F401  puts scripts/ on sys.path
from fakeserver import ConnectorTestCase, Reply
from test_connectors_foundation import scan_for_writes

API_TOKEN = "bd-API-t0ken-S3CRET-4242"
BEARER = "bd-BEARER-t0ken-S3CRET-9191"
TOKEN_PATH = "/api/tokens/authenticate"

V = "application/vnd.blackducksoftware."
USER, PROJECT, VERSION = V + "user-4+json", V + "project-detail-4+json", V + "project-detail-5+json"
BOM, COMPONENT = V + "bill-of-materials-6+json", V + "component-detail-5+json"


def meta(href, **links):
    return {"href": href, "links": [{"rel": k.replace("_", "-"), "href": v}
                                    for k, v in links.items()]}


def project(base, pid, name, **extra):
    href = f"{base}/api/projects/{pid}"
    return {"name": name, "description": extra.get("description"),
            "updatedAt": "2026-10-01T10:00:00.000Z",
            "_meta": meta(href, versions=f"{href}/versions")}


def version(base, pid, vid, name, links=True):
    href = f"{base}/api/projects/{pid}/versions/{vid}"
    m = meta(href, vulnerable_components=f"{href}/vulnerable-bom-components",
             components=f"{href}/components", policy_status=f"{href}/policy-status") \
        if links else meta(href)
    return {"versionName": name, "phase": "DEVELOPMENT", "distribution": "INTERNAL",
            "settingUpdatedAt": "2026-10-02T08:00:00.000Z",
            "updatedAt": "2026-10-03T08:00:00.000Z", "_meta": m}


def vuln(base, name, sev, comp="commons-text", cver="1.9", cid="c1", vid="v1", source=None,
         score=9.8, related=None):
    v = {"vulnerabilityName": name, "source": source or name.split("-")[0].replace("CVE", "NVD"),
         "severity": sev, "overallScore": score, "baseScore": 7.0,
         "remediationStatus": "NEW"}
    if related is not None:
        v["relatedVulnerability"] = related
    return {"componentName": comp, "componentVersionName": cver,
            "componentVersion": f"{base}/api/components/{cid}/versions/{vid}",
            "componentVersionOriginId": f"org.apache.commons:{comp}:{cver}",
            "componentVersionOriginName": "maven",
            "vulnerabilityWithRemediation": v,
            "_meta": meta(f"{base}/api/projects/p1/versions/r1/vulnerable-bom-components/x")}


def listing(rows):
    return {"totalCount": len(rows), "items": rows}


def paged(rows):
    """A route serving `rows` with offset/limit paging and totalCount."""
    def route(req):
        start = int(req.query.get("offset", ["0"])[0])
        size = int(req.query.get("limit", ["10"])[0])
        return {"totalCount": len(rows), "items": rows[start:start + size]}
    return route


ME = {"userName": "ana.pop", "firstName": "Ana", "lastName": "Pop", "email": "ana@example.com",
      "_meta": {"href": "x"}}


class Base(ConnectorTestCase):
    def setUp(self):
        super().setUp()
        self.c = self.connector("blackduck")
        from personal.connectors import blackduck
        self.mod = blackduck

    def serve(self, build):
        """A fake server whose routes `build(base_url)` makes (hrefs carry its address)."""
        srv = self.server({})
        srv.routes.update({TOKEN_PATH: {"bearerToken": BEARER, "expiresInMilliseconds": 7199000},
                           **build(srv.url)})
        return srv

    def values(self, srv):
        return {"url": srv.url, "token": API_TOKEN}

    def cmd(self, srv, *argv):
        return self.run_command(self.c, self.context(self.c, self.values(srv)), list(argv))

    def gets(self, srv):
        return [r for r in srv.requests if r.method == "GET"]


def app_routes(base, vulns=None, components=None, guidance=None, version_links=True):
    """Project 'App' (with 'App-old' and 'application' as other search hits) and its
    version '1.0'; the version's links lead to `vulns` and `components`."""
    vhref = f"{base}/api/projects/p1/versions/r1"
    routes = {
        "/api/projects": listing([project(base, "p0", "App-old"), project(base, "p1", "App"),
                                  project(base, "p2", "application")]),
        "/api/projects/p1/versions": listing([version(base, "p1", "r1", "1.0",
                                                      links=version_links)]),
        "/api/projects/p1/versions/r1/vulnerable-bom-components": paged(vulns or []),
        "/api/projects/p1/versions/r1/components": paged(components or []),
        "/api/projects/p1/versions/r1/policy-status": {
            "overallStatus": "IN_VIOLATION",
            "componentVersionStatusCounts": [{"name": "IN_VIOLATION", "value": 2},
                                             {"name": "NOT_IN_VIOLATION", "value": 40}],
            "_meta": {"href": vhref + "/policy-status"}},
    }
    routes.update(guidance or {})
    return routes


def guide(cid="c1", vid="v1", short="1.10.0", long="1.12.0"):
    body = {"shortTerm": {"versionName": short}, "longTerm": {"versionName": long}}
    return {f"/api/components/{cid}/versions/{vid}/upgrade-guidance": body}


class TestModule(Base):
    def test_registry_validates_and_fields(self):
        self.assertEqual(self.c.title, "Black Duck")
        self.assertEqual(self.c.keys, ["url", "token", "ca_bundle"])
        f = {x.key: x for x in self.c.fields}
        self.assertTrue(f["token"].secret)
        self.assertIn("API token", f["token"].prompt)
        self.assertEqual(self.c.kind({"url": "https://blackduck.example.com"}), "")
        self.assertEqual(set(self.c.commands),
                         {"projects", "versions", "vulns", "components", "policy"})

    def test_auth_is_the_token_exchange(self):
        from personal.connectors import http
        a = self.c.auth({"url": "https://x", "token": API_TOKEN})
        self.assertIsInstance(a, http.TokenExchange)
        self.assertEqual(a.token_path, TOKEN_PATH)

    def test_module_never_posts(self):
        with open(self.mod.__file__, encoding="utf-8") as fh:
            self.assertEqual(scan_for_writes(fh.read()), [])


class TestAuth(Base):
    def test_one_exchange_for_a_whole_command_then_bearer(self):
        srv = self.serve(lambda b: app_routes(b, vulns=[vuln(b, "CVE-2022-42889", "CRITICAL")],
                                              guidance=guide()))
        self.cmd(srv, "vulns", "App", "1.0")
        posts = [r for r in srv.requests if r.method == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].path, TOKEN_PATH)
        self.assertEqual(posts[0].headers["Authorization"], f"token {API_TOKEN}")
        self.assertEqual(srv.requests[0].method, "POST")
        gets = self.gets(srv)
        self.assertEqual(len(gets), 4)          # projects, versions, vulns, guidance
        for g in gets:
            self.assertEqual(g.headers["Authorization"], f"Bearer {BEARER}")
        self.assertEqual({r.method for r in srv.requests}, {"POST", "GET"})

    def test_accept_header_per_endpoint(self):
        srv = self.serve(lambda b: app_routes(b, vulns=[vuln(b, "CVE-1", "HIGH")],
                                              guidance=guide()))
        self.cmd(srv, "vulns", "App", "1.0")
        self.cmd(srv, "components", "App", "1.0")
        self.cmd(srv, "policy", "App", "1.0")
        seen = {}
        for g in self.gets(srv):
            seen.setdefault(g.path, set()).add(g.headers["Accept"])
        self.assertEqual(seen["/api/projects"], {PROJECT})
        self.assertEqual(seen["/api/projects/p1/versions"], {VERSION})
        self.assertEqual(seen["/api/projects/p1/versions/r1/vulnerable-bom-components"], {BOM})
        self.assertEqual(seen["/api/projects/p1/versions/r1/components"], {BOM})
        self.assertEqual(seen["/api/projects/p1/versions/r1/policy-status"], {BOM})
        self.assertEqual(seen["/api/components/c1/versions/v1/upgrade-guidance"], {COMPONENT})
        post = [r for r in srv.requests if r.method == "POST"][0]
        self.assertEqual(post.headers["Accept"], USER)

    def test_bad_api_token_is_plain_and_secret_free(self):
        srv = self.server({TOKEN_PATH: Reply(401, {"errorMessage": f"bad token {API_TOKEN}"})})
        code, out, err = self.run_cli(self.c, ["whoami"], values=self.values(srv))
        self.assertEqual(code, 1)
        self.assertIn("API token was not accepted", err)
        self.assertIn("setup.py connect blackduck", err)
        self.assertNotIn(API_TOKEN, out + err)


class TestSecrets(Base):
    def test_api_token_and_bearer_absent_from_all_output(self):
        def build(b):
            routes = app_routes(b, vulns=[vuln(b, "CVE-1", "HIGH")],
                                components=[{"componentName": "x", "_meta": meta("h")}],
                                guidance=guide())
            routes["/api/current-user"] = ME
            routes["/api/projects/p9"] = Reply(400, {"message": f"echo {BEARER} {API_TOKEN}"})
            routes["/api/projects/p8"] = Reply(401, {"message": f"echo {BEARER}"})
            return routes
        srv = self.serve(build)
        blob = []
        runs = (["whoami"], ["projects", "App"], ["versions", "App"], ["vulns", "App", "1.0"],
                ["components", "App", "1.0"], ["policy", "App", "1.0"])
        for argv in runs:
            for extra in ([], ["--json"]):
                err = io.StringIO()
                with mock.patch.dict(os.environ, {"AI_SDLC_DEBUG": "1"}), \
                        contextlib.redirect_stderr(err):
                    code, out, cerr = self.run_cli(self.c, argv + extra, values=self.values(srv))
                self.assertEqual(code, 0, cerr)
                blob.append(out + cerr + err.getvalue())
        from personal.connectors import http
        ctx = self.context(self.c, self.values(srv), debug=True, stderr=io.StringIO())
        for path in ("/api/projects/p9", "/api/projects/p8"):
            with self.assertRaises(http.ConnectorError) as cm:
                ctx.client.get(path, accept=PROJECT)
            blob.append(str(cm.exception))
        blob.append(ctx.client._stderr.getvalue())
        text = "\n".join(blob)
        self.assertIn("> GET", text)                 # the debug lines were captured
        self.assertNotIn(API_TOKEN, text)
        self.assertNotIn(BEARER, text)


class TestWhoami(Base):
    def test_whoami(self):
        srv = self.serve(lambda b: {"/api/current-user": ME})
        r = self.cmd(srv, "whoami")
        self.assertEqual(r.item, {"user": "ana.pop", "display_name": "Ana Pop",
                                  "email": "ana@example.com", "url": srv.url})
        self.assertEqual(self.gets(srv)[0].headers["Accept"], USER)

    def test_whoami_without_names(self):
        srv = self.serve(lambda b: {"/api/current-user": {"userName": "svc"}})
        self.assertEqual(self.cmd(srv, "whoami").item,
                         {"user": "svc", "display_name": "svc", "email": None, "url": srv.url})


class TestProjects(Base):
    def test_projects_two_pages_and_truncated(self):
        holder = {}

        def build(b):
            holder["rows"] = [project(b, f"p{i}", f"App {i}") for i in range(150)]
            return {"/api/projects": paged(holder["rows"])}
        srv = self.serve(build)
        r = self.cmd(srv, "projects", "App", "--limit", "120")
        self.assertEqual(len(r.items), 120)
        self.assertTrue(r.truncated)
        q = [g.query for g in self.gets(srv)]
        self.assertEqual([x["offset"] for x in q], [["0"], ["100"]])
        self.assertEqual([x["limit"] for x in q], [["100"], ["20"]])
        self.assertEqual(q[0]["q"], ["name:App"])
        self.assertEqual(r.items[1], {"name": "App 1", "description": None,
                                      "updated": "2026-10-01T10:00:00.000Z",
                                      "url": f"{srv.url}/api/projects/p1"})

    def test_projects_all_read_not_truncated(self):
        srv = self.serve(lambda b: {"/api/projects": paged([project(b, "p1", "App")])})
        r = self.cmd(srv, "projects", "App")
        self.assertEqual((len(r.items), r.truncated), (1, False))
        self.assertEqual(self.gets(srv)[0].query["limit"], ["25"])


class TestResolve(Base):
    def test_exact_name_among_three_case_insensitive(self):
        srv = self.serve(lambda b: app_routes(b))
        r = self.cmd(srv, "versions", "app")
        self.assertEqual(self.gets(srv)[0].query["q"], ["name:app"])
        self.assertEqual(self.gets(srv)[1].path, "/api/projects/p1/versions")
        self.assertEqual([i["name"] for i in r.items], ["1.0"])

    def test_no_project_is_not_found_with_a_hint(self):
        from personal.connectors import http
        srv = self.serve(lambda b: app_routes(b))
        with self.assertRaises(http.ConnectorError) as cm:
            self.cmd(srv, "versions", "Ap")
        self.assertEqual(cm.exception.kind, "not_found")
        msg = str(cm.exception)
        self.assertIn("No Black Duck project named 'Ap'", msg)
        self.assertIn("connectors.py blackduck projects", msg)
        self.assertIn("App-old", msg)                # the candidates are listed

    def test_two_exact_matches_are_a_config_error_listing_them(self):
        from personal.connectors import http
        srv = self.serve(lambda b: {"/api/projects": listing(
            [project(b, "p1", "App"), project(b, "p2", "APP")])})
        with self.assertRaises(http.ConnectorError) as cm:
            self.cmd(srv, "versions", "app")
        self.assertEqual(cm.exception.kind, "config")
        self.assertIn("'App'", str(cm.exception))
        self.assertIn("'APP'", str(cm.exception))

    def test_no_version_is_not_found(self):
        from personal.connectors import http
        srv = self.serve(lambda b: app_routes(b))
        with self.assertRaises(http.ConnectorError) as cm:
            self.cmd(srv, "policy", "App", "2.0")
        self.assertEqual(cm.exception.kind, "not_found")
        self.assertIn("no version named '2.0'", str(cm.exception))
        self.assertIn("connectors.py blackduck versions App", str(cm.exception))
        self.assertEqual(self.gets(srv)[1].query["q"], ["versionName:2.0"])

    def test_missing_meta_link_is_bad_response(self):
        from personal.connectors import http
        srv = self.serve(lambda b: app_routes(b, version_links=False))
        with self.assertRaises(http.ConnectorError) as cm:
            self.cmd(srv, "vulns", "App", "1.0")
        self.assertEqual(cm.exception.kind, "bad_response")
        self.assertIn("vulnerable-components", str(cm.exception))


class TestVersions(Base):
    def test_versions_follow_the_link(self):
        srv = self.serve(lambda b: app_routes(b))
        r = self.cmd(srv, "versions", "App")
        g = self.gets(srv)[1]
        self.assertEqual(g.path, "/api/projects/p1/versions")     # the canned href's path
        self.assertEqual(g.query["sort"], ["updatedAt desc"])
        self.assertEqual(g.query["limit"], ["50"])
        self.assertEqual(r.items, [{"name": "1.0", "phase": "DEVELOPMENT",
                                    "distribution": "INTERNAL",
                                    "updated": "2026-10-02T08:00:00.000Z",
                                    "url": f"{srv.url}/api/projects/p1/versions/r1/components"}])


class TestVulns(Base):
    def rows(self, b):
        return [vuln(b, "CVE-2022-42889", "CRITICAL"),
                vuln(b, "BDSA-2022-2771", "HIGH", source="BDSA", score=None,
                     related=f"{b}/api/vulnerabilities/CVE-2022-42889"),
                vuln(b, "CVE-2021-1", "MEDIUM", comp="snakeyaml", cver="1.30", cid="c2",
                     vid="v2")]

    def test_cve_and_bdsa_items_exact_keys_and_fixed_in(self):
        srv = self.serve(lambda b: app_routes(b, vulns=self.rows(b), guidance={
            **guide(), **guide("c2", "v2", short="1.33", long=None)}))
        r = self.cmd(srv, "vulns", "App", "1.0")
        vhref = f"{srv.url}/api/projects/p1/versions/r1"
        self.assertEqual(r.items[0], {
            "id": "CVE-2022-42889", "source": "NVD", "severity": "critical", "score": 9.8,
            "remediation": "NEW", "component": "commons-text", "component_version": "1.9",
            "origin": "org.apache.commons:commons-text:1.9", "related": None,
            "fixed_in": {"short_term": "1.10.0", "long_term": "1.12.0"},
            "url": vhref + "/vulnerability-bom"})
        self.assertEqual(r.items[1]["id"], "BDSA-2022-2771")
        self.assertEqual(r.items[1]["source"], "BDSA")
        self.assertEqual(r.items[1]["score"], 7.0)               # baseScore when no overall
        self.assertEqual(r.items[1]["related"], "CVE-2022-42889")
        self.assertEqual(r.items[2]["fixed_in"], {"short_term": "1.33", "long_term": None})
        self.assertEqual(r.extra, {"fix_versions_read": 2, "fix_versions_skipped": 0})
        guidance = [g for g in self.gets(srv) if g.path.endswith("/upgrade-guidance")]
        self.assertEqual(len(guidance), 2)                       # once per component version
        self.assertFalse(r.truncated)

    def test_severity_filter_on_the_client(self):
        srv = self.serve(lambda b: app_routes(b, vulns=self.rows(b), guidance=guide()))
        r = self.cmd(srv, "vulns", "App", "1.0", "--severity", "critical")
        self.assertEqual([i["id"] for i in r.items], ["CVE-2022-42889"])

    def test_severity_filter_pages_until_the_limit(self):
        def build(b):
            rows = [vuln(b, f"CVE-{i}", "LOW", cid="c1") for i in range(150)]
            rows[10] = vuln(b, "CVE-A", "HIGH")
            rows[120] = vuln(b, "CVE-B", "HIGH")
            rows[140] = vuln(b, "CVE-C", "HIGH")
            return app_routes(b, vulns=rows, guidance=guide())
        srv = self.serve(build)
        r = self.cmd(srv, "vulns", "App", "1.0", "--severity", "high,critical", "--limit", "2")
        self.assertEqual([i["id"] for i in r.items], ["CVE-A", "CVE-B"])
        self.assertTrue(r.truncated)
        pages = [g.query["offset"][0] for g in self.gets(srv)
                 if g.path.endswith("vulnerable-bom-components")]
        self.assertEqual(pages, ["0", "100"])

    def test_bad_severity_is_a_usage_error(self):
        srv = self.serve(lambda b: app_routes(b))
        with contextlib.redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit):
            self.cmd(srv, "vulns", "App", "1.0", "--severity", "blocker")
        self.assertIn("critical, high, medium, low", err.getvalue())

    def test_guidance_404_is_null(self):
        srv = self.serve(lambda b: app_routes(b, vulns=self.rows(b)[:1]))
        r = self.cmd(srv, "vulns", "App", "1.0")
        self.assertIsNone(r.items[0]["fixed_in"])
        self.assertEqual(r.extra, {"fix_versions_read": 1, "fix_versions_skipped": 0})

    def test_guidance_cap(self):
        srv = self.serve(lambda b: app_routes(b, vulns=self.rows(b), guidance={
            **guide(), **guide("c2", "v2")}))
        with mock.patch.object(self.mod, "MAX_GUIDANCE", 1):
            r = self.cmd(srv, "vulns", "App", "1.0")
        self.assertIsNotNone(r.items[0]["fixed_in"])
        self.assertIsNone(r.items[2]["fixed_in"])
        self.assertEqual(r.extra, {"fix_versions_read": 1, "fix_versions_skipped": 1})
        guidance = [g for g in self.gets(srv) if g.path.endswith("/upgrade-guidance")]
        self.assertEqual(len(guidance), 1)

    def test_no_fix_versions_makes_no_guidance_call(self):
        srv = self.serve(lambda b: app_routes(b, vulns=self.rows(b), guidance=guide()))
        r = self.cmd(srv, "vulns", "App", "1.0", "--no-fix-versions")
        self.assertFalse([g for g in self.gets(srv) if g.path.endswith("/upgrade-guidance")])
        self.assertTrue(all(i["fixed_in"] is None for i in r.items))
        self.assertEqual(r.extra, {"fix_versions_read": 0, "fix_versions_skipped": 2})

    def test_plain_text_lines(self):
        srv = self.serve(lambda b: app_routes(b, vulns=self.rows(b)[:1], guidance=guide()))
        code, out, err = self.run_cli(self.c, ["vulns", "App", "1.0"], values=self.values(srv))
        self.assertEqual(code, 0, err)
        self.assertIn("CVE-2022-42889 [critical] commons-text 1.9", out)
        self.assertIn("fixed in 1.10.0 (short term), 1.12.0 (long term)", out)


class TestComponentsAndPolicy(Base):
    def test_components_violations_filter_and_shape(self):
        def build(b):
            row = {"componentName": "commons-text", "componentVersionName": "1.9",
                   "componentVersion": f"{b}/api/components/c1/versions/v1",
                   "origins": [{"externalId": "org.apache.commons:commons-text:1.9"},
                               {"name": "no id"}],
                   "licenses": [{"licenseDisplay": "Apache License 2.0"},
                                {"licenseName": "MIT"}],
                   "policyStatus": "IN_VIOLATION", "reviewStatus": "NOT_REVIEWED"}
            bare = {"componentName": "x"}
            return app_routes(b, components=[row, bare])
        srv = self.serve(build)
        r = self.cmd(srv, "components", "App", "1.0", "--violations")
        g = [x for x in self.gets(srv) if x.path.endswith("/components")][0]
        self.assertEqual(g.query["filter"], ["bomPolicy:in_violation"])
        self.assertEqual(r.items[0], {
            "name": "commons-text", "version": "1.9",
            "origins": ["org.apache.commons:commons-text:1.9"],
            "licenses": ["Apache License 2.0", "MIT"], "policy_status": "IN_VIOLATION",
            "review_status": "NOT_REVIEWED",
            "url": f"{srv.url}/api/components/c1/versions/v1"})
        self.assertEqual(r.items[1], {
            "name": "x", "version": None, "origins": [], "licenses": [], "policy_status": None,
            "review_status": None,
            "url": f"{srv.url}/api/projects/p1/versions/r1/components"})

    def test_components_without_violations_sends_no_filter(self):
        srv = self.serve(lambda b: app_routes(b, components=[{"componentName": "x"}]))
        self.cmd(srv, "components", "App", "1.0")
        g = [x for x in self.gets(srv) if x.path.endswith("/components")][0]
        self.assertNotIn("filter", g.query)

    def test_policy_counts(self):
        srv = self.serve(lambda b: app_routes(b))
        r = self.cmd(srv, "policy", "App", "1.0")
        self.assertEqual(r.item, {
            "project": "App", "version": "1.0", "status": "IN_VIOLATION",
            "counts": {"IN_VIOLATION": 2, "NOT_IN_VIOLATION": 40},
            "url": f"{srv.url}/api/projects/p1/versions/r1/components"})


class TestCli(Base):
    def test_vulns_json_end_to_end_and_get_only_reads(self):
        srv = self.serve(lambda b: app_routes(b, vulns=[vuln(b, "CVE-2022-42889", "CRITICAL")],
                                              guidance=guide()))
        code, out, err = self.run_cli(self.c, ["vulns", "App", "1.0", "--json"],
                                      values=self.values(srv))
        self.assertEqual((code, err), (0, ""))
        doc = json.loads(out)
        self.assertEqual((doc["connector"], doc["command"], doc["source"]),
                         ("blackduck", "vulns", srv.url))
        self.assertEqual(doc["count"], 1)
        self.assertFalse(doc["truncated"])
        self.assertEqual(doc["items"][0]["fixed_in"],
                         {"short_term": "1.10.0", "long_term": "1.12.0"})
        self.assertEqual((doc["fix_versions_read"], doc["fix_versions_skipped"]), (1, 0))
        self.assertEqual([r.path for r in srv.requests if r.method != "GET"], [TOKEN_PATH])
        self.assertNotIn(API_TOKEN, out)
        self.assertNotIn(BEARER, out)


if __name__ == "__main__":
    unittest.main()
