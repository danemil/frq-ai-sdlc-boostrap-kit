#!/usr/bin/env python3
"""The artifactory connector against the fake server: whoami, repos, versions, latest,
npm, go (read-only; GET only; no AQL).

To confirm on a live server (design §9, Artifactory):
- The JWT `sub` format (`jfrt@…/users/<name>` or `jfac@…/users/<name>`) for the client's
  token type (access token, identity token); reference tokens (not a JWT) give no user.
- The identity endpoint: that `GET /api/system/version` answers 401 for a bad token when
  anonymous access is on. If not, a better read-only call that needs a login.
- The Go list endpoint path `/api/go/<repo>/<module>/@v/list` (some set-ups serve it as
  `/<repo>/<module>/@v/list`), and the case-encoding of module paths.
- `GET /api/search/latestVersion` on the client's edition (it may need a Pro licence;
  `versions` then gives `release` from `maven-metadata.xml`).
- For a remote or virtual repository, which versions `maven-metadata.xml` lists (cached
  only, or the upstream's too).
- The web UI link form `<host>/ui/repos/tree/General/<repo>/<path>`.
- The npm metadata endpoint `/api/npm/<repo>/<package>` with a scoped name sent as
  `@scope%2fname` (some reverse proxies decode `%2f`; then the request 404s).
- `GET /api/repositories` field names (`key`, `type`, `packageType`, `description`).
"""
from __future__ import annotations

import ast
import base64
import io
import json
import os
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

import helpers  # noqa: F401  (puts scripts/ on sys.path)
from fakeserver import ConnectorTestCase, Reply

SECRET = "art-reference-token-s3cr3t-0042"
CTX = "/artifactory"


def jwt(sub, extra=None) -> str:
    """A JWT-shaped token (header.payload.signature) with `sub`; not signed for real."""
    def part(doc):
        raw = json.dumps(doc).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return ".".join([part({"alg": "RS256", "typ": "JWT"}),
                     part({"sub": sub, "scp": "applied-permissions/user", **(extra or {})}),
                     "c2lnbmF0dXJlLXMzY3IzdC1wYXJ0"])


JWT_RT = jwt("jfrt@01h2k3m4n5/users/ana")
JWT_AC = jwt("jfac@01h2k3m4n5/users/ana")

VERSION = {"version": "7.77.5", "revision": "77705900", "addons": ["build", "docker"],
           "license": "abcdef"}

REPOS = [
    {"key": "maven-virtual", "type": "VIRTUAL", "packageType": "Maven",
     "description": "All Maven", "url": "SERVER/artifactory/maven-virtual"},
    {"key": "maven-central-remote", "type": "REMOTE", "packageType": "Maven",
     "url": "SERVER/artifactory/maven-central-remote"},
    {"key": "libs-release-local", "type": "LOCAL", "packageType": "Maven",
     "description": "", "url": "SERVER/artifactory/libs-release-local"},
]

METADATA = """<?xml version="1.0" encoding="UTF-8"?>
<metadata>
  <groupId>org.apache.commons</groupId>
  <artifactId>commons-text</artifactId>
  <versioning>
    <latest>1.12.0</latest>
    <release>1.12.0</release>
    <versions>
      <version>1.10.0</version>
      <version>1.11.0</version>
      <version>1.12.0</version>
    </versions>
    <lastUpdated>20260901123045</lastUpdated>
  </versioning>
</metadata>
"""

DOCTYPE_METADATA = """<?xml version="1.0"?>
<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;">]>
<metadata><versioning><versions><version>&lol2;</version></versions></versioning></metadata>
"""

NPM = {
    "name": "@acme/widgets",
    "dist-tags": {"latest": "2.1.0", "next": "3.0.0-beta.1"},
    "versions": {"1.0.0": {"version": "1.0.0"}, "2.1.0": {"version": "2.1.0"},
                 "2.0.0": {"version": "2.0.0"}, "3.0.0-beta.1": {"version": "3.0.0-beta.1"}},
    "time": {"created": "2025-01-01T00:00:00.000Z", "modified": "2026-09-01T00:00:00.000Z",
             "1.0.0": "2025-01-01T00:00:00.000Z", "2.0.0": "2025-06-01T00:00:00.000Z",
             "2.1.0": "2026-03-01T00:00:00.000Z", "3.0.0-beta.1": "2026-09-01T00:00:00.000Z"},
}

GO_LIST = "v1.2.0\nv1.10.0\nv1.2.0-rc.1\nv1.9.3\nv1.10.0-beta.2\nv1.10.0-beta.10\n\nv2.0.0+incompatible\n"

WHOAMI_KEYS = {"user", "display_name", "server_version", "url"}
REPO_KEYS = {"key", "type", "package_type", "description", "url"}
VERSIONS_KEYS = {"group", "artifact", "repo", "versions", "latest", "release", "updated",
                 "count", "url"}
LATEST_KEYS = {"group", "artifact", "repo", "version", "url"}
NPM_KEYS = {"package", "repo", "dist_tags", "versions", "published", "count", "url"}
GO_KEYS = {"module", "repo", "versions", "count", "url"}

MD_PATH = "/artifactory/maven-virtual/org/apache/commons/commons-text/maven-metadata.xml"


class ArtifactoryCase(ConnectorTestCase):
    def setUp(self):
        super().setUp()
        self.c = self.connector("artifactory")

    def serve(self, routes):
        srv = self.server({})
        for k, v in routes.items():
            if isinstance(v, list):
                v = json.loads(json.dumps(v).replace("SERVER", srv.url))
            srv.routes[k] = v
        return srv

    def values(self, srv, token=SECRET, **more):
        return {"url": srv.url + CTX, "token": token, **more}

    def ctx(self, srv, **more):
        return self.context(self.c, self.values(srv, **more))

    def cmd(self, srv, argv, **more):
        return self.run_command(self.c, self.ctx(srv, **more), argv)

    def error(self, srv, argv, **more):
        from personal.connectors import http
        with self.assertRaises(http.ConnectorError) as cm:
            self.cmd(srv, argv, **more)
        return cm.exception


class TestContract(ArtifactoryCase):
    def test_registry_validates_the_module(self):
        self.assertEqual(self.c.title, "Artifactory")
        self.assertEqual(self.c.keys, ["url", "token", "maven_repo", "npm_repo", "go_repo",
                                       "ca_bundle"])
        self.assertEqual(set(self.c.commands), {"repos", "versions", "latest", "npm", "go"})
        self.assertEqual(self.c.kind({"url": "https://artifactory.example.com/artifactory"}),
                         "")
        self.assertIsNone(self.c.check({"url": "https://artifactory.example.com"}))

    def test_fields(self):
        f = {x.key: x for x in self.c.fields}
        self.assertIn("/artifactory", f["url"].prompt)
        self.assertTrue(f["token"].secret and f["token"].required)
        for key in ("maven_repo", "npm_repo", "go_repo"):
            self.assertFalse(f[key].required, key)
            self.assertFalse(f[key].secret, key)
        self.assertEqual(self.c.missing({"url": "https://a.example.com", "token": "t"}), [])

    def test_connect_from_env_without_repo_fields(self):
        from personal.connectors import manage, store
        srv = self.serve({"/artifactory/api/system/version": VERSION})
        with mock.patch.dict(os.environ, {"AI_SDLC_ARTIFACTORY_URL": srv.url + CTX,
                                          "AI_SDLC_ARTIFACTORY_TOKEN": JWT_RT}):
            code, lines = manage.connect("artifactory", connectors={"artifactory": self.c},
                                         isatty=False, client_kwargs={"sleep": lambda s: None})
        self.assertEqual(code, 0, lines)
        self.assertIn("as ana.", "\n".join(lines))
        self.assertNotIn(JWT_RT, "\n".join(lines))
        saved = store.load("artifactory", self.c.keys)
        self.assertNotIn("maven_repo", {k for k, v in saved.items() if v})

    def test_module_never_posts(self):
        """The rule the foundation's static scan enforces (design §3.2), for this module."""
        from personal.connectors import artifactory
        tree = ast.parse(Path(artifactory.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, ("_send", "_exchange"))
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertNotIn(node.value, ("POST", "PUT", "PATCH", "DELETE"))
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.assertFalse(a.name.startswith(("urllib", "http.client")), a.name)
            if isinstance(node, ast.ImportFrom):
                self.assertFalse((node.module or "").startswith(("urllib", "http.client")),
                                 node.module)


class TestHelpers(ArtifactoryCase):
    def test_jwt_user(self):
        from personal.connectors import artifactory as a
        self.assertEqual(a._jwt_user(JWT_RT), "ana")
        self.assertEqual(a._jwt_user(JWT_AC), "ana")
        self.assertEqual(a._jwt_user(jwt("ana@example.com")), "ana@example.com")
        self.assertIsNone(a._jwt_user(SECRET))
        self.assertIsNone(a._jwt_user("aaa.%%%not-base64%%%.ccc"))
        self.assertIsNone(a._jwt_user("aaa." + base64.urlsafe_b64encode(b"[1,2]").decode()
                                      + ".ccc"))
        self.assertIsNone(a._jwt_user(jwt(42)))
        self.assertIsNone(a._jwt_user(""))

    def test_go_escape(self):
        from personal.connectors import artifactory as a
        self.assertEqual(a._go_escape("github.com/Azure/azure-sdk-for-go"),
                         "github.com/!azure/azure-sdk-for-go")
        self.assertEqual(a._go_escape("github.com/BurntSushi/TOML"),
                         "github.com/!burnt!sushi/!t!o!m!l")

    def test_go_sort_is_semver_newest_first_prereleases_after_release(self):
        from personal.connectors import artifactory as a
        got = a._semver_sorted(["v1.2.0", "v1.10.0", "v1.2.0-rc.1", "v1.9.3",
                                "v1.10.0-beta.2", "v1.10.0-beta.10", "v2.0.0+incompatible",
                                "junk"])
        self.assertEqual(got, ["v2.0.0+incompatible", "v1.10.0", "v1.10.0-beta.10",
                               "v1.10.0-beta.2", "v1.9.3", "v1.2.0", "v1.2.0-rc.1", "junk"])

    def test_metadata_refuses_doctype_and_entities(self):
        from personal.connectors import artifactory as a, http
        for doc in (DOCTYPE_METADATA, '<?xml version="1.0"?><!ENTITY x "y"><metadata/>',
                    "<!doctype metadata><metadata/>"):
            with self.assertRaises(http.ConnectorError) as cm:
                a._parse_metadata(doc)
            self.assertEqual(cm.exception.kind, "bad_response")
        with self.assertRaises(http.ConnectorError) as cm:
            a._parse_metadata("<html><body>Sign in</body>")
        self.assertEqual(cm.exception.kind, "bad_response")

    def test_bad_coordinates_and_names(self):
        srv = self.serve({})
        for coords in ("commons-text", "org.apache:", ":x", "org/../x:y", "org..x:y",
                       "org.apache:..", "a:b:c d"):
            e = self.error(srv, ["versions", coords, "--repo", "maven-virtual"])
            self.assertEqual(e.kind, "config", coords)
            self.assertIn("group:artifact", str(e))
        e = self.error(srv, ["versions", "a:b", "--repo", "../etc"])
        self.assertEqual(e.kind, "config")
        e = self.error(srv, ["go", "github.com/x/../y", "--repo", "go-virtual"])
        self.assertEqual(e.kind, "config")
        e = self.error(srv, ["npm", "bad name", "--repo", "npm-virtual"])
        self.assertEqual(e.kind, "config")
        self.assertEqual(srv.requests, [])


class TestWhoami(ArtifactoryCase):
    def test_whoami_bearer_and_user_from_jwt(self):
        srv = self.serve({"/artifactory/api/system/version": VERSION})
        r = self.cmd(srv, ["whoami"], token=JWT_RT)
        self.assertEqual(r.item, {"user": "ana", "display_name": "ana",
                                  "server_version": "7.77.5", "url": srv.url + "/ui/"})
        req = srv.requests[0]
        self.assertEqual((req.method, req.path), ("GET", "/artifactory/api/system/version"))
        self.assertEqual(req.headers["Authorization"], "Bearer " + JWT_RT)

    def test_reference_token_has_no_user_but_passes(self):
        srv = self.serve({"/artifactory/api/system/version": VERSION})
        r = self.cmd(srv, ["whoami"])
        self.assertEqual(set(r.item), WHOAMI_KEYS)
        self.assertIsNone(r.item["user"])
        self.assertEqual(r.item["display_name"], "unknown (not a JWT token)")

    def test_401_is_unauthorized(self):
        srv = self.serve({"/artifactory/api/system/version":
                          Reply(401, {"errors": [{"status": 401, "message": "Bad token"}]})})
        e = self.error(srv, ["whoami"])
        self.assertEqual(e.kind, "unauthorized")
        self.assertNotIn(SECRET, str(e))

    def test_404_hints_at_the_context_path(self):
        srv = self.serve({})
        from personal.connectors import http
        ctx = self.context(self.c, {"url": srv.url, "token": SECRET})
        with self.assertRaises(http.ConnectorError) as cm:
            self.run_command(self.c, ctx, ["whoami"])
        self.assertEqual(cm.exception.kind, "not_found")
        self.assertIn(f"Nothing at {srv.url}/api/system/version", str(cm.exception))
        self.assertIn("does the URL need /artifactory at the end?", str(cm.exception))


class TestRepos(ArtifactoryCase):
    def test_repos_by_type(self):
        srv = self.serve({"/artifactory/api/repositories": REPOS})
        r = self.cmd(srv, ["repos", "--type", "maven"])
        self.assertEqual(srv.requests[0].query, {"packageType": ["maven"]})
        self.assertEqual(len(r.items), 3)
        for it in r.items:
            self.assertEqual(set(it), REPO_KEYS)
        self.assertEqual(r.items[0], {
            "key": "maven-virtual", "type": "VIRTUAL", "package_type": "Maven",
            "description": "All Maven",
            "url": srv.url + "/ui/repos/tree/General/maven-virtual"})
        self.assertIsNone(r.items[1]["description"])
        self.assertIsNone(r.items[2]["description"])
        self.assertFalse(r.truncated)

    def test_repos_all_and_limit(self):
        srv = self.serve({"/artifactory/api/repositories": REPOS})
        r = self.cmd(srv, ["repos", "--limit", "2"])
        self.assertEqual(srv.requests[0].query, {})
        self.assertEqual([i["key"] for i in r.items], ["maven-virtual", "maven-central-remote"])
        self.assertTrue(r.truncated)


class TestVersions(ArtifactoryCase):
    def test_versions_parses_metadata(self):
        srv = self.serve({MD_PATH: Reply(200, METADATA, {"Content-Type": "application/xml"})})
        r = self.cmd(srv, ["versions", "org.apache.commons:commons-text"],
                     maven_repo="maven-virtual")
        req = srv.requests[0]
        self.assertEqual(req.path, MD_PATH)
        self.assertEqual(req.headers["Accept"], "application/xml")
        it = r.item
        self.assertEqual(set(it), VERSIONS_KEYS)
        self.assertEqual(it, {
            "group": "org.apache.commons", "artifact": "commons-text", "repo": "maven-virtual",
            "versions": ["1.12.0", "1.11.0", "1.10.0"], "latest": "1.12.0",
            "release": "1.12.0", "updated": "2026-09-01T12:30:45Z", "count": 3,
            "url": srv.url + "/ui/repos/tree/General/maven-virtual/org/apache/commons/"
                             "commons-text"})
        self.assertFalse(r.truncated)

    def test_limit_truncates(self):
        srv = self.serve({MD_PATH: Reply(200, METADATA)})
        r = self.cmd(srv, ["versions", "org.apache.commons:commons-text", "--limit", "2"],
                     maven_repo="maven-virtual")
        self.assertEqual(r.item["versions"], ["1.12.0", "1.11.0"])
        self.assertEqual(r.item["count"], 3)
        self.assertTrue(r.truncated)

    def test_missing_optional_values_are_null(self):
        doc = "<metadata><versioning><versions><version>1.0</version></versions>" \
              "</versioning></metadata>"
        srv = self.serve({MD_PATH: Reply(200, doc)})
        r = self.cmd(srv, ["versions", "org.apache.commons:commons-text"],
                     maven_repo="maven-virtual")
        self.assertEqual((r.item["latest"], r.item["release"], r.item["updated"]),
                         (None, None, None))
        self.assertEqual(r.item["versions"], ["1.0"])

    def test_doctype_answer_is_refused(self):
        srv = self.serve({MD_PATH: Reply(200, DOCTYPE_METADATA)})
        e = self.error(srv, ["versions", "org.apache.commons:commons-text"],
                       maven_repo="maven-virtual")
        self.assertEqual(e.kind, "bad_response")
        self.assertIn("DOCTYPE", str(e))

    def test_repo_flag_wins_over_saved_default(self):
        path = "/artifactory/libs-release-local/org/apache/commons/commons-text/" \
               "maven-metadata.xml"
        srv = self.serve({path: Reply(200, METADATA)})
        r = self.cmd(srv, ["versions", "org.apache.commons:commons-text", "--repo",
                           "libs-release-local"], maven_repo="maven-virtual")
        self.assertEqual(srv.requests[0].path, path)
        self.assertEqual(r.item["repo"], "libs-release-local")

    def test_no_repo_at_all_is_a_config_error(self):
        srv = self.serve({})
        e = self.error(srv, ["versions", "org.apache.commons:commons-text"])
        self.assertEqual(e.kind, "config")
        self.assertEqual(str(e), "Give --repo, or save a default with connect artifactory "
                                 "(the repo key, e.g. maven-virtual).")
        self.assertEqual(srv.requests, [])

    def test_missing_artifact_is_not_found(self):
        srv = self.serve({})
        e = self.error(srv, ["versions", "org.example:nope"], maven_repo="maven-virtual")
        self.assertEqual(e.kind, "not_found")
        self.assertIn("org.example:nope", str(e))
        self.assertIn("maven-virtual", str(e))


class TestLatest(ArtifactoryCase):
    def test_latest_text(self):
        srv = self.serve({"/artifactory/api/search/latestVersion":
                          Reply(200, "1.12.0\n", {"Content-Type": "text/plain"})})
        r = self.cmd(srv, ["latest", "org.apache.commons:commons-text"],
                     maven_repo="maven-virtual")
        self.assertEqual(srv.requests[0].query, {"g": ["org.apache.commons"],
                                                 "a": ["commons-text"],
                                                 "repos": ["maven-virtual"]})
        self.assertEqual(set(r.item), LATEST_KEYS)
        self.assertEqual(r.item["version"], "1.12.0")
        self.assertEqual(r.item["url"], srv.url + "/ui/repos/tree/General/maven-virtual/org/"
                                                  "apache/commons/commons-text/1.12.0")

    def test_latest_404_is_null(self):
        srv = self.serve({"/artifactory/api/search/latestVersion":
                          Reply(404, {"errors": [{"status": 404, "message": "not found"}]})})
        r = self.cmd(srv, ["latest", "org.example:nope", "--repo", "maven-virtual"])
        self.assertIsNone(r.item["version"])
        self.assertEqual(r.item["url"], srv.url + "/ui/repos/tree/General/maven-virtual/org/"
                                                  "example/nope")


class TestNpm(ArtifactoryCase):
    def test_scoped_name_and_dist_tags(self):
        srv = self.serve({"/artifactory/api/npm/npm-virtual/@acme%2fwidgets": NPM})
        r = self.cmd(srv, ["npm", "@acme/widgets"], npm_repo="npm-virtual")
        self.assertEqual(srv.requests[0].target,
                         "/artifactory/api/npm/npm-virtual/@acme%2fwidgets")
        it = r.item
        self.assertEqual(set(it), NPM_KEYS)
        self.assertEqual(it["dist_tags"], {"latest": "2.1.0", "next": "3.0.0-beta.1"})
        self.assertEqual(it["versions"], ["3.0.0-beta.1", "2.1.0", "2.0.0", "1.0.0"])
        self.assertEqual(it["published"]["2.1.0"], "2026-03-01T00:00:00.000Z")
        self.assertNotIn("created", it["published"])
        self.assertEqual((it["package"], it["repo"], it["count"]),
                         ("@acme/widgets", "npm-virtual", 4))
        self.assertEqual(it["url"], srv.url + "/ui/repos/tree/General/npm-virtual/@acme/widgets")

    def test_no_times_keeps_listed_order_and_limit(self):
        doc = {"name": "left-pad", "dist-tags": {"latest": "1.3.0"},
               "versions": {"1.0.0": {}, "1.1.0": {}, "1.3.0": {}}}
        srv = self.serve({"/artifactory/api/npm/npm-virtual/left-pad": doc})
        r = self.cmd(srv, ["npm", "left-pad", "--repo", "npm-virtual", "--limit", "2"])
        self.assertEqual(r.item["versions"], ["1.0.0", "1.1.0"])
        self.assertEqual(r.item["published"], {})
        self.assertEqual(r.item["count"], 3)
        self.assertTrue(r.truncated)


class TestGo(ArtifactoryCase):
    def test_case_encoding_and_sort(self):
        path = "/artifactory/api/go/go-virtual/github.com/!azure/x/@v/list"
        srv = self.serve({path: Reply(200, GO_LIST, {"Content-Type": "text/plain"})})
        r = self.cmd(srv, ["go", "github.com/Azure/x"], go_repo="go-virtual")
        self.assertEqual(srv.requests[0].path, path)
        it = r.item
        self.assertEqual(set(it), GO_KEYS)
        self.assertEqual(it["versions"], ["v2.0.0+incompatible", "v1.10.0", "v1.10.0-beta.10",
                                          "v1.10.0-beta.2", "v1.9.3", "v1.2.0", "v1.2.0-rc.1"])
        self.assertEqual((it["module"], it["repo"], it["count"]),
                         ("github.com/Azure/x", "go-virtual", 7))
        self.assertEqual(it["url"], srv.url + "/ui/repos/tree/General/go-virtual/github.com/"
                                              "Azure/x")

    def test_limit(self):
        path = "/artifactory/api/go/go-virtual/example.com/m/@v/list"
        srv = self.serve({path: Reply(200, GO_LIST)})
        r = self.cmd(srv, ["go", "example.com/m", "--repo", "go-virtual", "--limit", "1"])
        self.assertEqual(r.item["versions"], ["v2.0.0+incompatible"])
        self.assertTrue(r.truncated)


class TestCli(ArtifactoryCase):
    def test_versions_json_end_to_end_and_get_only(self):
        srv = self.serve({MD_PATH: Reply(200, METADATA)})
        code, out, err = self.run_cli(self.c, ["versions", "org.apache.commons:commons-text",
                                               "--json"],
                                      values=self.values(srv, maven_repo="maven-virtual"))
        self.assertEqual((code, err), (0, ""))
        doc = json.loads(out)
        self.assertEqual((doc["connector"], doc["command"], doc["source"]),
                         ("artifactory", "versions", srv.url + CTX))
        self.assertEqual(doc["item"]["versions"][0], "1.12.0")
        self.assertTrue(doc["item"]["url"].startswith(srv.url + "/ui/"))
        self.assertTrue(all(r.method == "GET" for r in srv.requests))

    def test_plain_text_lists_versions(self):
        srv = self.serve({MD_PATH: Reply(200, METADATA)})
        code, out, _ = self.run_cli(self.c, ["versions", "org.apache.commons:commons-text"],
                                    values=self.values(srv, maven_repo="maven-virtual"))
        self.assertEqual(code, 0)
        self.assertIn("1.12.0", out)
        self.assertIn(srv.url + "/ui/repos/tree/General/maven-virtual/", out)

    def test_secret_absent_from_all_output(self):
        for token in (SECRET, JWT_RT):
            srv = self.serve({
                "/artifactory/api/system/version": VERSION,
                "/artifactory/api/repositories": REPOS,
                MD_PATH: Reply(200, METADATA),
                "/artifactory/api/search/latestVersion": Reply(200, "1.12.0"),
                "/artifactory/api/npm/npm-virtual/@acme%2fwidgets": NPM,
                "/artifactory/api/go/go-virtual/example.com/m/@v/list": Reply(200, GO_LIST),
                "/artifactory/bad/org/x/y/maven-metadata.xml":
                    Reply(401, {"errors": [{"status": 401, "message": "bad token " + token}]}),
                "/artifactory/boom/org/x/y/maven-metadata.xml":
                    Reply(400, {"errors": [{"status": 400, "message": "echo " + token}]}),
            })
            values = self.values(srv, token=token, maven_repo="maven-virtual",
                                 npm_repo="npm-virtual", go_repo="go-virtual")
            outputs = []
            debug = io.StringIO()
            with mock.patch.dict(os.environ, {"AI_SDLC_DEBUG": "1"}), redirect_stderr(debug):
                for argv in (["whoami"], ["repos"], ["versions", "org.apache.commons:commons-text"],
                             ["latest", "org.apache.commons:commons-text"],
                             ["npm", "@acme/widgets"], ["go", "example.com/m"],
                             ["versions", "org.x:y", "--repo", "bad"],
                             ["versions", "org.x:y", "--repo", "boom"]):
                    for extra in ([], ["--json"]):
                        code, out, err = self.run_cli(self.c, argv + extra, values=values)
                        outputs.append(out + err)
            blob = "\n".join(outputs) + debug.getvalue()
            self.assertNotIn(token, blob)
            self.assertIn("setup.py connect artifactory", blob)
            self.assertIn("<redacted>", blob)
            if token == JWT_RT:
                self.assertIn('"user": "ana"', blob)


if __name__ == "__main__":
    unittest.main()
