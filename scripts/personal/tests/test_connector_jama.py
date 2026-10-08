#!/usr/bin/env python3
"""The jama connector (Jama Connect REST v1, OAuth client credentials) against
tests/fakeserver.py: no network.

Canned answers follow Jama's documented envelope: {"meta": {"pageInfo": {startIndex,
resultCount, totalResults}}, "data": ..., "linked": {"items": {"<id>": {...}}}}.

To confirm on a live instance:
- the test-run field names (fields.testRunStatus, testCase, testCycle, executionDate,
  assignedTo): Jama lets an organization rename fields per item type;
- the item web URL <base>/perspective.req#/items/<id>?projectId=<p> (documented by
  Jama support for items; for test runs the UI may prefer its own view);
- `include` sent as a repeated parameter (include=data.fromItem&include=data.toItem),
  as in Jama's Swagger (an array, collectionFormat multi).
"""
import base64
import json
import unittest

import helpers  # noqa: F401  puts scripts/ on sys.path
from fakeserver import ConnectorTestCase, Reply

SECRET = "jama-S3CRET-client-value-77"
TOKEN = "acc3ss-T0KEN-jama-99"
CID = "kit-client-id"


def env(data, total=None, start=0, linked=None):
    meta = {"status": "OK"}
    if isinstance(data, list):
        meta["pageInfo"] = {"startIndex": start, "resultCount": len(data),
                            "totalResults": len(data) if total is None else total}
    doc = {"meta": meta, "links": {}, "data": data}
    if linked is not None:
        doc["linked"] = linked
    return doc


def item(i, project=10, name=None, **fields):
    return {"id": i, "documentKey": f"PRJ-REQ-{i}", "globalId": f"GID-{i}", "project": project,
            "itemType": 89, "createdDate": "2026-09-01T10:00:00.000+0000",
            "modifiedDate": "2026-10-01T12:30:00.000+0000", "type": "items",
            "fields": {"name": name or f"Requirement {i}", "documentKey": f"PRJ-REQ-{i}",
                       "globalId": f"GID-{i}", **fields}}


def paged(rows, size_param="maxResults"):
    """A route serving `rows` with startAt/maxResults paging and totalResults."""
    def route(req):
        start = int(req.query.get("startAt", ["0"])[0])
        size = int(req.query.get(size_param, ["50"])[0])
        return env(rows[start:start + size], total=len(rows), start=start)
    return route


ME = {"id": 7, "username": "ana.pop", "firstName": "Ana", "lastName": "Pop",
      "email": "ana@example.com", "active": True}
TOKEN_ROUTE = {"/rest/oauth/token": {"access_token": TOKEN, "token_type": "bearer",
                                     "expires_in": 3600}}


class Base(ConnectorTestCase):
    def setUp(self):
        super().setUp()
        self.c = self.connector("jama")

    def srv(self, routes):
        return self.server({**TOKEN_ROUTE, **routes})

    def ctx(self, srv):
        return self.context(self.c, {"url": srv.url, "client_id": CID, "client_secret": SECRET})

    def cmd(self, srv, *argv):
        return self.run_command(self.c, self.ctx(srv), list(argv))

    def gets(self, srv):
        return [r for r in srv.requests if r.method == "GET"]


class TestModule(Base):
    def test_registry_validates_and_fields(self):
        self.assertEqual(self.c.title, "Jama")
        self.assertEqual(self.c.keys, ["url", "client_id", "client_secret", "ca_bundle"])
        f = {x.key: x for x in self.c.fields}
        self.assertTrue(f["client_secret"].secret)
        self.assertTrue(f["client_id"].identity)
        self.assertFalse(f["client_id"].secret)
        self.assertEqual(self.c.kind({"url": "https://example.jamacloud.com"}), "")
        self.assertEqual([x.key for x in self.c.applicable({})], self.c.keys)
        self.assertEqual(set(self.c.commands),
                         {"item", "search", "relationships", "testruns"})


class TestAuth(Base):
    def test_token_is_fetched_once_and_reused(self):
        srv = self.srv({"/rest/v1/users/current": env(ME), "/rest/v1/items/5": env(item(5))})
        ctx = self.ctx(srv)
        self.run_command(self.c, ctx, ["whoami"])
        self.run_command(self.c, ctx, ["item", "5"])
        posts = [r for r in srv.requests if r.method == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].path, "/rest/oauth/token")
        self.assertEqual(posts[0].body, b"grant_type=client_credentials")
        self.assertEqual(posts[0].headers["Authorization"],
                         "Basic " + base64.b64encode(f"{CID}:{SECRET}".encode()).decode())
        self.assertEqual(srv.requests[0].method, "POST")  # the token comes first
        gets = self.gets(srv)
        self.assertEqual(len(gets), 2)
        for g in gets:
            self.assertEqual(g.headers["Authorization"], f"Bearer {TOKEN}")

    def test_bad_client_secret_is_plain_and_secret_free(self):
        srv = self.server({"/rest/oauth/token": Reply(401, {"error": "invalid_client"})})
        code, out, err = self.run_cli(self.c, ["whoami"], values={
            "url": srv.url, "client_id": CID, "client_secret": SECRET})
        self.assertEqual(code, 1)
        self.assertIn("client ID or client secret was not accepted", err)
        self.assertIn("setup.py connect jama", err)
        self.assertNotIn(SECRET, out + err)


class TestWhoami(Base):
    def test_whoami(self):
        srv = self.srv({"/rest/v1/users/current": env(ME)})
        r = self.cmd(srv, "whoami")
        self.assertEqual(r.item, {"user": "ana.pop", "display_name": "Ana Pop",
                                  "email": "ana@example.com", "id": 7, "url": srv.url})


class TestItem(Base):
    def test_item_shape(self):
        raw = item(5, project=10, description="<p>The <b>system</b> shall</p><ul><li>log</li></ul>",
                   priority=301, status=400)
        srv = self.srv({"/rest/v1/items/5": env(raw)})
        r = self.cmd(srv, "item", "5")
        self.assertEqual(self.gets(srv)[0].path, "/rest/v1/items/5")
        self.assertEqual(r.item, {
            "id": 5, "key": "PRJ-REQ-5", "global_id": "GID-5", "name": "Requirement 5",
            "type_id": 89, "project_id": 10, "created": "2026-09-01T10:00:00.000+0000",
            "modified": "2026-10-01T12:30:00.000+0000", "description": "The system shall\nlog",
            "fields": {"documentKey": "PRJ-REQ-5", "globalId": "GID-5", "priority": 301,
                       "status": 400},
            "url": f"{srv.url}/perspective.req#/items/5?projectId=10"})

    def test_item_description_clipped_and_missing_values_null(self):
        long = "<p>" + "x" * 5000 + "</p>"
        raw = item(6, description=long)
        del raw["createdDate"]
        srv = self.srv({"/rest/v1/items/6": env(raw)})
        r = self.cmd(srv, "item", "6")
        self.assertEqual(len(r.item["description"]), 4000)
        self.assertTrue(r.item["description"].endswith("…"))
        self.assertIsNone(r.item["created"])

    def test_item_404(self):
        from personal.connectors import http
        srv = self.srv({})
        with self.assertRaises(http.ConnectorError) as cm:
            self.cmd(srv, "item", "999")
        self.assertEqual(cm.exception.kind, "not_found")


class TestSearch(Base):
    def test_search_request_and_shape(self):
        srv = self.srv({"/rest/v1/abstractitems": paged([item(1), item(2, project=11)])})
        r = self.cmd(srv, "search", "login flow", "--project", "10", "--type", "89")
        q = self.gets(srv)[0].query
        self.assertEqual(q["contains"], ["login flow"])
        self.assertEqual(q["project"], ["10"])
        self.assertEqual(q["itemType"], ["89"])
        self.assertEqual(q["startAt"], ["0"])
        self.assertEqual(q["maxResults"], ["50"])
        self.assertEqual(r.items[1], {
            "id": 2, "key": "PRJ-REQ-2", "name": "Requirement 2", "type_id": 89,
            "project_id": 11, "modified": "2026-10-01T12:30:00.000+0000",
            "url": f"{srv.url}/perspective.req#/items/2?projectId=11"})
        self.assertFalse(r.truncated)

    def test_search_without_filters_sends_none(self):
        srv = self.srv({"/rest/v1/abstractitems": paged([item(1)])})
        self.cmd(srv, "search", "x")
        q = self.gets(srv)[0].query
        self.assertNotIn("project", q)
        self.assertNotIn("itemType", q)

    def test_search_pages_and_truncates(self):
        rows = [item(i) for i in range(1, 121)]
        srv = self.srv({"/rest/v1/abstractitems": paged(rows)})
        r = self.cmd(srv, "search", "x", "--limit", "70")
        self.assertEqual([x["id"] for x in r.items], list(range(1, 71)))
        self.assertTrue(r.truncated)
        starts = [g.query["startAt"][0] for g in self.gets(srv)]
        self.assertEqual(starts, ["0", "50"])
        self.assertEqual(self.gets(srv)[1].query["maxResults"], ["20"])

    def test_search_all_pages_not_truncated(self):
        rows = [item(i) for i in range(1, 61)]
        srv = self.srv({"/rest/v1/abstractitems": paged(rows)})
        r = self.cmd(srv, "search", "x", "--limit", "100")
        self.assertEqual(len(r.items), 60)
        self.assertFalse(r.truncated)


def rel(i, frm, to, rtype=3, suspect=False):
    return {"id": i, "fromItem": frm, "toItem": to, "relationshipType": rtype,
            "suspect": suspect, "type": "relationships"}


class TestRelationships(Base):
    def routes(self):
        up = env([rel(100, 1, 5)], linked={"items": {"1": item(1, name="Need"),
                                                     "5": item(5, name="Req")}})
        down = env([rel(200, 5, 9, suspect=True)],
                   linked={"items": {"5": item(5, name="Req"), "9": item(9, project=12,
                                                                         name="Test")}})
        return {"/rest/v1/items/5/upstreamrelationships": up,
                "/rest/v1/items/5/downstreamrelationships": down}

    def test_both_directions(self):
        srv = self.srv(self.routes())
        r = self.cmd(srv, "relationships", "5")
        paths = [g.path for g in self.gets(srv)]
        self.assertEqual(paths, ["/rest/v1/items/5/upstreamrelationships",
                                 "/rest/v1/items/5/downstreamrelationships"])
        self.assertEqual(self.gets(srv)[0].query["include"], ["data.fromItem", "data.toItem"])
        u = f"{srv.url}/perspective.req#/items/"
        self.assertEqual(r.items, [
            {"id": 100, "direction": "upstream", "type_id": 3, "suspect": False,
             "from": {"id": 1, "key": "PRJ-REQ-1", "name": "Need", "url": u + "1?projectId=10"},
             "to": {"id": 5, "key": "PRJ-REQ-5", "name": "Req", "url": u + "5?projectId=10"},
             "url": u + "1?projectId=10"},
            {"id": 200, "direction": "downstream", "type_id": 3, "suspect": True,
             "from": {"id": 5, "key": "PRJ-REQ-5", "name": "Req", "url": u + "5?projectId=10"},
             "to": {"id": 9, "key": "PRJ-REQ-9", "name": "Test", "url": u + "9?projectId=12"},
             "url": u + "9?projectId=12"}])

    def test_up_only_and_unlinked_item(self):
        routes = self.routes()
        routes["/rest/v1/items/5/upstreamrelationships"] = env([rel(100, 1, 5)])
        srv = self.srv(routes)
        r = self.cmd(srv, "relationships", "5", "--direction", "up")
        self.assertEqual([g.path for g in self.gets(srv)],
                         ["/rest/v1/items/5/upstreamrelationships"])
        self.assertEqual(r.items[0]["from"], {"id": 1, "key": None, "name": None,
                                              "url": f"{srv.url}/perspective.req#/items/1"})

    def test_pages_keep_linked_names_and_limit(self):
        rows = [rel(1000 + i, 5, 300 + i) for i in range(60)]
        linked = {str(300 + i): item(300 + i, name=f"T{i}") for i in range(60)}

        def route(req):
            start = int(req.query.get("startAt", ["0"])[0])
            size = int(req.query.get("maxResults", ["50"])[0])
            page = rows[start:start + size]
            return env(page, total=len(rows), start=start,
                       linked={"items": {str(p["toItem"]): linked[str(p["toItem"])]
                                         for p in page}})
        srv = self.srv({"/rest/v1/items/5/downstreamrelationships": route})
        r = self.cmd(srv, "relationships", "5", "--direction", "down", "--limit", "55")
        self.assertEqual(len(r.items), 55)
        self.assertTrue(r.truncated)
        self.assertEqual(r.items[54]["to"]["name"], "T54")
        self.assertEqual([g.query["maxResults"][0] for g in self.gets(srv)], ["50", "5"])


def run_(i, cycle, status="PASSED"):
    return {"id": i, "documentKey": f"PRJ-TSTRN-{i}", "project": 10, "itemType": 40,
            "fields": {"name": f"Run {i}", "testRunStatus": status, "testCase": 500 + i,
                       "testCycle": cycle, "executionDate": "2026-10-02",
                       "assignedTo": 7}}


class TestTestRuns(Base):
    def test_cycle(self):
        srv = self.srv({"/rest/v1/testcycles/30/testruns": paged([run_(1, 30), run_(2, 30,
                                                                                     "FAILED")])})
        r = self.cmd(srv, "testruns", "--cycle", "30")
        self.assertEqual(self.gets(srv)[0].path, "/rest/v1/testcycles/30/testruns")
        self.assertEqual(r.items[1], {
            "id": 2, "key": "PRJ-TSTRN-2", "name": "Run 2", "status": "FAILED",
            "test_case_id": 502, "cycle_id": 30, "executed": "2026-10-02", "assigned_to": 7,
            "url": f"{srv.url}/perspective.req#/items/2?projectId=10"})
        self.assertFalse(r.truncated)

    def test_plan_walks_cycles_until_limit(self):
        cycles = [{"id": 30, "project": 10, "fields": {"name": "C1"}},
                  {"id": 31, "project": 10, "fields": {"name": "C2"}},
                  {"id": 32, "project": 10, "fields": {"name": "C3"}}]
        srv = self.srv({"/rest/v1/testplans/3/testcycles": paged(cycles),
                        "/rest/v1/testcycles/30/testruns": paged([run_(1, 30), run_(2, 30)]),
                        "/rest/v1/testcycles/31/testruns": paged([run_(3, 31), run_(4, 31)]),
                        "/rest/v1/testcycles/32/testruns": paged([run_(5, 32)])})
        r = self.cmd(srv, "testruns", "--plan", "3", "--limit", "3")
        self.assertEqual([x["id"] for x in r.items], [1, 2, 3])
        self.assertTrue(r.truncated)
        self.assertNotIn("/rest/v1/testcycles/32/testruns", [g.path for g in self.gets(srv)])

    def test_plan_all_runs(self):
        cycles = [{"id": 30, "project": 10, "fields": {}}]
        srv = self.srv({"/rest/v1/testplans/3/testcycles": paged(cycles),
                        "/rest/v1/testcycles/30/testruns": paged([run_(1, 30)])})
        r = self.cmd(srv, "testruns", "--plan", "3")
        self.assertEqual(len(r.items), 1)
        self.assertFalse(r.truncated)

    def test_exactly_one_of_cycle_or_plan(self):
        srv = self.srv({})
        for argv in (["testruns"], ["testruns", "--cycle", "1", "--plan", "2"]):
            with self.assertRaises(SystemExit):
                self.cmd(srv, *argv)


class TestCli(Base):
    def test_cli_json_end_to_end_and_read_only(self):
        srv = self.srv({"/rest/v1/abstractitems": paged([item(1), item(2)])})
        code, out, err = self.run_cli(self.c, ["search", "login", "--json"], values={
            "url": srv.url, "client_id": CID, "client_secret": SECRET})
        self.assertEqual(code, 0, err)
        doc = json.loads(out)
        self.assertEqual(doc["connector"], "jama")
        self.assertEqual(doc["command"], "search")
        self.assertEqual(doc["count"], 2)
        self.assertFalse(doc["truncated"])
        self.assertTrue(all(i["url"].startswith(srv.url + "/perspective.req#/items/")
                            for i in doc["items"]))
        self.assertNotIn(SECRET, out + err)
        self.assertNotIn(TOKEN, out + err)
        self.assertEqual(sorted({r.method for r in srv.requests}), ["GET", "POST"])
        self.assertEqual([r.path for r in srv.requests if r.method == "POST"],
                         ["/rest/oauth/token"])

    def test_cli_plain_text_has_no_secret(self):
        srv = self.srv({"/rest/v1/users/current": env(ME)})
        code, out, err = self.run_cli(self.c, ["whoami"], values={
            "url": srv.url, "client_id": CID, "client_secret": SECRET})
        self.assertEqual(code, 0, err)
        self.assertIn("display_name: Ana Pop", out)
        self.assertNotIn(SECRET, out + err)
        self.assertNotIn(TOKEN, out + err)


if __name__ == "__main__":
    unittest.main()
