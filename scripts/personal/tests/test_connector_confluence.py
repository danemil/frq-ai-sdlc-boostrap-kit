#!/usr/bin/env python3
"""Tests for the confluence connector (Cloud and Data Center), against the fake server.

Canned answers follow the documented response shapes: Cloud `GET /wiki/api/v2/pages/{id}`,
`GET /wiki/rest/api/search` (CQL, results[].content) and `/wiki/rest/api/user/current`;
Data Center `GET /rest/api/content/{id}?expand=...`, `GET /rest/api/content/search` and
`/rest/api/user/current`. Paging follows `_links.next`, relative to `_links.base`.

To confirm on a live server: Cloud search with `expand=content.space,content.version`
(gives the space key and version of each hit), and the `@@@hl@@@` highlight markers in
Cloud search excerpts.
"""
from __future__ import annotations

import base64
import json
import unittest
import urllib.parse

import helpers  # noqa: F401  puts scripts/ on sys.path
from fakeserver import ConnectorTestCase, Reply, Seq  # noqa: F401

SECRET = "s3cr3t-confluence-token-0042"
EMAIL = "ana@example.com"

CLOUD_ME = {"type": "known", "accountId": "5b10ac8d82e05b22cc7d4ef5", "accountType": "atlassian",
            "email": EMAIL, "publicName": "Ana P", "displayName": "Ana Popescu",
            "_links": {"base": "https://example.atlassian.net/wiki", "self": "x"}}
DC_ME = {"type": "known", "username": "ana", "userKey": "8a8a1234", "displayName": "Ana Popescu",
         "_links": {"base": "https://confluence.example.com/confluence"}}

STORAGE = ("<h1>Release notes</h1><p>The <strong>login</strong> flow &amp; the "
           "<em>cart</em>.</p><ul><li>one</li><li>two</li></ul>")


def cloud_page(base):
    return {"id": "123", "status": "current", "title": "Release notes", "spaceId": "98306",
            "parentId": "100", "authorId": "x",
            "version": {"number": 7, "createdAt": "2026-10-01T09:30:00.000Z", "authorId": "x"},
            "body": {"storage": {"value": STORAGE, "representation": "storage"}},
            "_links": {"webui": "/spaces/ENG/pages/123/Release+notes",
                       "editui": "/pages/resumedraft.action?draftId=123",
                       "tinyui": "/x/ewE", "base": base}}


def dc_page(base):
    return {"id": "456", "type": "page", "status": "current", "title": "Runbook",
            "space": {"id": 1, "key": "OPS", "name": "Operations"},
            "version": {"number": 3, "when": "2026-09-30T08:00:00.000+02:00"},
            "body": {"storage": {"value": STORAGE, "representation": "storage"}},
            "_links": {"webui": "/display/OPS/Runbook", "base": base,
                       "self": "/rest/api/content/456"}}


def cloud_hit(i):
    return {"content": {"id": str(i), "type": "page", "status": "current", "title": f"Page {i}",
                        "space": {"key": "ENG", "name": "Engineering"},
                        "version": {"number": 1, "when": "2026-09-0%dT10:00:00.000Z" % (i % 9 + 1)},
                        "_links": {"webui": f"/spaces/ENG/pages/{i}/Page+{i}"}},
            "title": f"Page {i}",
            "excerpt": "the @@@hl@@@login@@@endhl@@@ flow &amp; more " + "x" * 400,
            "url": f"/spaces/ENG/pages/{i}/Page+{i}", "entityType": "content",
            "lastModified": "2026-09-0%dT10:00:00.000Z" % (i % 9 + 1)}


def dc_hit(i):
    return {"id": str(i), "type": "page", "status": "current", "title": f"Doc {i}",
            "space": {"key": "OPS", "name": "Operations"},
            "version": {"number": 2, "when": "2026-09-1%dT10:00:00.000+02:00" % (i % 9)},
            "_links": {"webui": f"/display/OPS/Doc+{i}", "self": "x"}}


class ConfluenceTestCase(ConnectorTestCase):
    def setUp(self):
        super().setUp()
        self.c = self.connector("confluence")

    def cloud(self, routes, url_suffix=""):
        srv = self.server(routes)
        return srv, self.cloud_context(srv.url + url_suffix)

    def cloud_context(self, url):
        """A Cloud context against the fake server; the forced kind gives Cloud auth (Basic)."""
        return self.context(self.c, {"url": url, "email": EMAIL, "token": SECRET}, kind="cloud")

    def dc(self, routes, context_path=""):
        srv = self.server(routes)
        ctx = self.context(self.c, {"url": srv.url + context_path, "token": SECRET}, kind="dc")
        return srv, ctx


class TestContract(ConfluenceTestCase):
    def test_registry_validates_and_fields(self):
        self.assertEqual(self.c.title, "Confluence")
        self.assertEqual(self.c.keys, ["url", "email", "token", "ca_bundle"])
        fields = {f.key: f for f in self.c.fields}
        self.assertTrue(fields["token"].secret)
        self.assertTrue(fields["email"].identity)
        self.assertFalse(fields["url"].secret or fields["email"].secret)
        self.assertEqual(set(self.c.commands), {"page", "search"})

    def test_auth_by_kind(self):
        cloud = self.c.auth({"url": "https://example.atlassian.net", "email": EMAIL,
                             "token": SECRET})
        dc = self.c.auth({"url": "https://confluence.example.com", "token": SECRET})
        expected = base64.b64encode(f"{EMAIL}:{SECRET}".encode()).decode()
        self.assertEqual(cloud.headers(None), {"Authorization": f"Basic {expected}"})
        self.assertEqual(dc.headers(None), {"Authorization": f"Bearer {SECRET}"})

    def test_kind_and_applicable_fields(self):
        cloud = {"url": "https://example.atlassian.net/wiki"}
        dc = {"url": "https://confluence.example.com/confluence"}
        self.assertEqual(self.c.kind(cloud), "cloud")
        self.assertEqual(self.c.kind(dc), "dc")
        self.assertEqual([f.key for f in self.c.applicable(cloud)],
                         ["url", "email", "token", "ca_bundle"])
        self.assertEqual([f.key for f in self.c.applicable(dc)], ["url", "token", "ca_bundle"])
        self.assertEqual([f.key for f in self.c.missing({**dc, "token": "t"})], [])
        self.assertEqual([f.key for f in self.c.missing({**cloud, "token": "t"})], ["email"])


class TestWhoami(ConfluenceTestCase):
    def test_cloud_basic_auth_wiki_root_and_shape(self):
        srv, ctx = self.cloud({"/wiki/rest/api/user/current": CLOUD_ME})
        item = self.run_command(self.c, ctx, ["whoami"]).item
        req = srv.requests[0]
        self.assertEqual(req.path, "/wiki/rest/api/user/current")
        expected = base64.b64encode(f"{EMAIL}:{SECRET}".encode()).decode()
        self.assertEqual(req.headers["Authorization"], f"Basic {expected}")
        self.assertEqual(item, {"user": "5b10ac8d82e05b22cc7d4ef5", "display_name": "Ana Popescu",
                                "email": EMAIL, "kind": "cloud", "url": srv.url + "/wiki"})

    def test_cloud_url_already_ending_in_wiki(self):
        srv, ctx = self.cloud({"/wiki/rest/api/user/current": CLOUD_ME}, url_suffix="/wiki")
        item = self.run_command(self.c, ctx, ["whoami"]).item
        self.assertEqual(srv.requests[0].path, "/wiki/rest/api/user/current")
        self.assertEqual(item["url"], srv.url + "/wiki")

    def test_dc_bearer_context_path_and_shape(self):
        srv, ctx = self.dc({"/confluence/rest/api/user/current": DC_ME},
                           context_path="/confluence")
        item = self.run_command(self.c, ctx, ["whoami"]).item
        req = srv.requests[0]
        self.assertEqual(req.path, "/confluence/rest/api/user/current")
        self.assertEqual(req.headers["Authorization"], f"Bearer {SECRET}")
        self.assertEqual(item, {"user": "ana", "display_name": "Ana Popescu", "email": None,
                                "kind": "dc", "url": srv.url + "/confluence"})

    def test_anonymous_is_unauthorized(self):
        from personal.connectors import http
        _, ctx = self.dc({"/rest/api/user/current": {"type": "anonymous",
                                                      "displayName": "Anonymous"}})
        with self.assertRaises(http.ConnectorError) as cm:
            self.run_command(self.c, ctx, ["whoami"])
        self.assertEqual(cm.exception.kind, "unauthorized")
        self.assertNotIn(SECRET, str(cm.exception))


PAGE_KEYS = {"id", "title", "space", "version", "updated", "body", "body_truncated", "url"}


class TestPage(ConfluenceTestCase):
    def test_cloud_page_v2_text(self):
        srv = self.server({})
        srv.routes["/wiki/api/v2/pages/123"] = cloud_page(srv.url + "/wiki")
        ctx = self.cloud_context(srv.url)
        item = self.run_command(self.c, ctx, ["page", "123"]).item
        req = srv.requests[0]
        self.assertEqual(req.path, "/wiki/api/v2/pages/123")
        self.assertEqual(req.query, {"body-format": ["storage"]})
        self.assertEqual(set(item), PAGE_KEYS)
        self.assertEqual(item["space"], "98306")
        self.assertEqual((item["version"], item["updated"]), (7, "2026-10-01T09:30:00.000Z"))
        self.assertEqual(item["body"], "Release notes\nThe login flow & the cart.\none\ntwo")
        self.assertFalse(item["body_truncated"])
        self.assertEqual(item["url"], srv.url + "/wiki/spaces/ENG/pages/123/Release+notes")

    def test_dc_page_content_api_storage_and_clip(self):
        srv = self.server({})
        srv.routes["/confluence/rest/api/content/456"] = dc_page(srv.url + "/confluence")
        ctx = self.context(self.c, {"url": srv.url + "/confluence", "token": SECRET}, kind="dc")
        item = self.run_command(self.c, ctx,
                                ["page", "456", "--format", "storage", "--max-chars", "20"]).item
        req = srv.requests[0]
        self.assertEqual(req.path, "/confluence/rest/api/content/456")
        self.assertEqual(req.query, {"expand": ["body.storage,version,space"]})
        self.assertEqual(set(item), PAGE_KEYS)
        self.assertEqual((item["space"], item["version"]), ("OPS", 3))
        self.assertEqual(item["updated"], "2026-09-30T08:00:00.000+02:00")
        self.assertEqual(len(item["body"]), 20)
        self.assertTrue(item["body"].startswith("<h1>Release"))
        self.assertTrue(item["body_truncated"])
        self.assertEqual(item["url"], srv.url + "/confluence/display/OPS/Runbook")

    def test_page_url_falls_back_to_site_root(self):
        page = cloud_page(None)
        del page["_links"]["base"]
        srv, ctx = self.cloud({"/wiki/api/v2/pages/123": page})
        item = self.run_command(self.c, ctx, ["page", "123"]).item
        self.assertEqual(item["url"], srv.url + "/wiki/spaces/ENG/pages/123/Release+notes")
        page = dc_page(None)
        del page["_links"]["base"]
        srv, ctx = self.dc({"/rest/api/content/456": page})
        item = self.run_command(self.c, ctx, ["page", "456"]).item
        self.assertEqual(item["url"], srv.url + "/display/OPS/Runbook")
        self.assertEqual(item["body"], "Release notes\nThe login flow & the cart.\none\ntwo")

    def test_missing_page_is_not_found(self):
        from personal.connectors import http
        _, ctx = self.dc({})
        with self.assertRaises(http.ConnectorError) as cm:
            self.run_command(self.c, ctx, ["page", "999"])
        self.assertEqual((cm.exception.kind, cm.exception.status), ("not_found", 404))


class TestCql(unittest.TestCase):
    def test_text_query_cql_detection_and_space(self):
        from personal.connectors import confluence as cf
        self.assertEqual(cf.build_cql("release notes", None),
                         'text ~ "release notes" AND type = page')
        self.assertEqual(cf.build_cql('say "hi" \\ there', "ENG"),
                         'text ~ "say \\"hi\\" \\\\ there" AND type = page AND space = "ENG"')
        for cql in ('type = page', 'title ~ "x"', 'a = 1 AND b = 2', 'space in ("A","B")',
                    'label = "x" order by lastmodified desc'):
            self.assertEqual(cf.build_cql(cql, None), cql)
        self.assertEqual(cf.build_cql('label = "x" OR label = "y" ORDER BY created DESC', "ENG"),
                         '(label = "x" OR label = "y") AND space = "ENG" ORDER BY created DESC')
        self.assertEqual(cf.build_cql("type = page", 'A"B'),
                         '(type = page) AND space = "A\\"B"')


class TestSearch(ConfluenceTestCase):
    def test_cloud_search_paging_shape_and_truncated(self):
        srv = self.server({})
        base = srv.url + "/wiki"
        nxt = "/rest/api/search?cql=x&limit=2&cursor=abc"
        page1 = {"results": [cloud_hit(1), cloud_hit(2)], "start": 0, "limit": 2, "size": 2,
                 "_links": {"base": base, "context": "/wiki", "next": nxt}}
        page2 = {"results": [cloud_hit(3), cloud_hit(4)], "start": 2, "limit": 2, "size": 2,
                 "_links": {"base": base, "context": "/wiki",
                            "next": "/rest/api/search?cql=x&limit=2&cursor=def"}}

        def route(req):
            return page2 if "cursor" in req.query else page1
        srv.routes["/wiki/rest/api/search"] = route
        ctx = self.cloud_context(srv.url)
        res = self.run_command(self.c, ctx, ["search", "login", "--space", "ENG",
                                             "--limit", "3"])
        first, second = srv.requests
        self.assertEqual(first.path, "/wiki/rest/api/search")
        self.assertEqual(first.query["cql"],
                         ['text ~ "login" AND type = page AND space = "ENG"'])
        self.assertEqual(first.query["limit"], ["3"])
        self.assertEqual(second.query["cursor"], ["abc"])
        self.assertEqual([i["id"] for i in res.items], ["1", "2", "3"])
        self.assertTrue(res.truncated)
        it = res.items[0]
        self.assertEqual(set(it), {"id", "type", "title", "space", "updated", "excerpt", "url"})
        self.assertEqual((it["type"], it["title"], it["space"]), ("page", "Page 1", "ENG"))
        self.assertEqual(it["updated"], "2026-09-02T10:00:00.000Z")
        self.assertTrue(it["excerpt"].startswith("the login flow & more x"))
        self.assertNotIn("@@@", it["excerpt"])
        self.assertLessEqual(len(it["excerpt"]), 300)
        self.assertEqual(it["url"], base + "/spaces/ENG/pages/1/Page+1")

    def test_dc_search_paging_shape(self):
        srv = self.server({})
        base = srv.url + "/confluence"
        page1 = {"results": [dc_hit(1), dc_hit(2)], "start": 0, "limit": 2, "size": 2,
                 "_links": {"base": base, "context": "/confluence",
                            "next": "/rest/api/content/search?cql=x&limit=2&start=2"}}
        page2 = {"results": [dc_hit(3)], "start": 2, "limit": 2, "size": 1,
                 "_links": {"base": base, "context": "/confluence"}}

        def route(req):
            return page2 if req.query.get("start") == ["2"] else page1
        srv.routes["/confluence/rest/api/content/search"] = route
        ctx = self.context(self.c, {"url": base, "token": SECRET}, kind="dc")
        res = self.run_command(self.c, ctx, ["search", "type = page AND space = OPS"])
        first = srv.requests[0]
        self.assertEqual(first.path, "/confluence/rest/api/content/search")
        self.assertEqual(first.query["cql"], ["type = page AND space = OPS"])
        self.assertEqual(first.query["expand"], ["space,version"])
        self.assertEqual(first.query["limit"], ["25"])
        self.assertEqual(len(srv.requests), 2)
        self.assertEqual([i["id"] for i in res.items], ["1", "2", "3"])
        self.assertFalse(res.truncated)
        self.assertEqual(res.items[0], {
            "id": "1", "type": "page", "title": "Doc 1", "space": "OPS",
            "updated": "2026-09-11T10:00:00.000+02:00", "excerpt": None,
            "url": base + "/display/OPS/Doc+1"})


class TestCli(ConfluenceTestCase):
    def test_cli_json_end_to_end_without_secret(self):
        srv = self.server({})
        srv.routes["/rest/api/content/456"] = dc_page(srv.url)
        code, out, err = self.run_cli(self.c, ["page", "456", "--json"],
                                      values={"url": srv.url, "token": SECRET})
        self.assertEqual(code, 0, err)
        doc = json.loads(out)
        self.assertEqual((doc["connector"], doc["command"], doc["source"]),
                         ("confluence", "page", srv.url))
        self.assertEqual(doc["item"]["url"], srv.url + "/display/OPS/Runbook")
        self.assertEqual(doc["item"]["title"], "Runbook")
        code, text_out, err2 = self.run_cli(self.c, ["page", "456"])
        self.assertEqual(code, 0, err2)
        self.assertIn("Runbook", text_out)
        self.assertIn(srv.url + "/display/OPS/Runbook", text_out)
        for blob in (out, err, text_out, err2):
            self.assertNotIn(SECRET, blob)

    def test_cli_401_message_has_no_secret(self):
        srv = self.server({"/rest/api/user/current": Reply(401, {"message": SECRET})})
        code, out, err = self.run_cli(self.c, ["whoami", "--json"],
                                      values={"url": srv.url, "token": SECRET})
        self.assertEqual(code, 1)
        self.assertIn("401", err)
        self.assertIn("setup.py connect confluence", err)
        self.assertNotIn(SECRET, out + err)
        enc = urllib.parse.quote(SECRET)
        self.assertNotIn(enc, out + err)


if __name__ == "__main__":
    unittest.main()
