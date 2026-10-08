#!/usr/bin/env python3
"""The jira connector (Cloud and Data Center), against tests/fakeserver.py (no network).

Canned answers follow the documented Jira REST shapes: Cloud v3 (`/search/jql` with a
nextPageToken cursor, ADF descriptions, `/issue/{key}/changelog`) and Data Center v2
(`/search` with startAt/maxResults/total, wiki-text descriptions, `expand=changelog`).

To confirm on a live server: that a Data Center `expand=changelog` returns every history
entry (no cap) and in ascending order (the connector sorts by time anyway).
"""
import base64
import json
import unittest

import helpers  # noqa: F401  puts scripts/ on sys.path
from fakeserver import ConnectorTestCase, Reply, Seq  # noqa: F401
from personal.connectors import http

SECRET = "jira-S3CRET-token-0042"
EMAIL = "ana@example.com"
BASE_FIELDS = "summary,issuetype,status,assignee,priority,updated"
ISSUE_FIELDS = ("summary,issuetype,status,assignee,reporter,priority,labels,created,updated,"
                "resolution,parent,description,components,fixVersions,issuelinks")
ITEM_KEYS = {"key", "summary", "type", "status", "assignee", "priority", "updated", "url"}
ISSUE_KEYS = {"key", "summary", "type", "status", "assignee", "reporter", "priority", "labels",
              "components", "fix_versions", "created", "updated", "resolution", "parent",
              "description", "url"}
SPRINT_KEYS = {"id", "name", "state", "start", "end", "complete", "goal", "board", "url"}


def person(name):
    return {"displayName": name, "name": name.split()[0].lower(), "accountId": "acc-" + name[:3]}


def raw_issue(key, summary="Do a thing", assignee="Ana Pop", extra=None):
    fields = {"summary": summary, "issuetype": {"name": "Story"}, "status": {"name": "To Do"},
              "assignee": person(assignee) if assignee else None,
              "priority": {"name": "Major"}, "updated": "2026-10-01T10:00:00.000+0000"}
    fields.update(extra or {})
    return {"id": "1" + key[-3:], "key": key, "fields": fields}


def adf(*paragraphs):
    return {"type": "doc", "version": 1, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": p}]} for p in paragraphs]}


def full_issue(key, description, **more):
    extra = {"reporter": person("Bo Ion"), "labels": ["api", "auth"],
             "components": [{"name": "Backend"}], "fixVersions": [{"name": "1.2"}],
             "created": "2026-09-01T09:00:00.000+0000", "resolution": None,
             "parent": {"key": "ABC-1"}, "description": description, "issuelinks": []}
    extra.update(more)
    return raw_issue(key, extra=extra)


def history(at, author, *changes):
    return {"id": at[-2:], "author": {"displayName": author}, "created": at,
            "items": [{"field": f, "fromString": a, "toString": b} for f, a, b in changes]}


class Base(ConnectorTestCase):
    def setUp(self):
        super().setUp()
        self.jira = self.connector("jira")

    def dc(self, routes):
        srv = self.server(routes)
        return srv, self.context(self.jira, {"url": srv.url, "token": SECRET}, kind="dc")

    def cloud(self, routes):
        srv = self.server(routes)
        values = {"url": srv.url, "email": EMAIL, "token": SECRET}
        ctx = self.context(self.jira, values, kind="cloud")
        # The fake server is 127.0.0.1, so use the auth a *.atlassian.net URL would get.
        ctx.client.auth = self.jira.auth({**values, "url": "https://example.atlassian.net"})
        return srv, ctx

    def cmd(self, ctx, *argv):
        return self.run_command(self.jira, ctx, list(argv))


# --- module, fields, auth -------------------------------------------------------------

class TestModule(Base):
    def test_registry_validates_the_module(self):
        self.assertEqual(self.jira.title, "Jira")
        self.assertEqual(self.jira.keys, ["url", "email", "token", "ca_bundle"])
        by_key = {f.key: f for f in self.jira.fields}
        self.assertTrue(by_key["token"].secret)
        self.assertTrue(by_key["email"].identity)
        self.assertFalse(by_key["url"].secret or by_key["email"].secret)
        self.assertEqual(set(self.jira.commands), {"search", "issue", "sprints"})

    def test_email_applies_to_cloud_only(self):
        cloud = [f.key for f in self.jira.applicable({"url": "https://example.atlassian.net"})]
        dc = [f.key for f in self.jira.applicable({"url": "https://jira.example.com"})]
        self.assertIn("email", cloud)
        self.assertNotIn("email", dc)
        self.assertEqual([f.key for f in self.jira.missing({"url": "https://jira.example.com"})],
                         ["token"])

    def test_kind_from_the_url(self):
        self.assertEqual(self.jira.kind({"url": "https://example.atlassian.net"}), "cloud")
        self.assertEqual(self.jira.kind({"url": "https://jira.example.com/jira"}), "dc")

    def test_auth_bearer_on_dc_basic_on_cloud(self):
        srv, ctx = self.dc({"/rest/api/2/myself": {"name": "ana", "displayName": "Ana"}})
        self.cmd(ctx, "whoami")
        self.assertEqual(srv.requests[0].headers["Authorization"], f"Bearer {SECRET}")
        self.assertEqual(srv.requests[0].method, "GET")

        srv, ctx = self.cloud({"/rest/api/3/myself": {"accountId": "a1", "displayName": "Ana"}})
        self.cmd(ctx, "whoami")
        expected = base64.b64encode(f"{EMAIL}:{SECRET}".encode()).decode()
        self.assertEqual(srv.requests[0].headers["Authorization"], f"Basic {expected}")


# --- whoami -----------------------------------------------------------------------------

class TestWhoami(Base):
    def test_dc(self):
        srv, ctx = self.dc({"/rest/api/2/myself": {
            "name": "ana.pop", "key": "JIRAUSER1", "displayName": "Ana Pop",
            "emailAddress": "ana@example.com"}})
        item = self.cmd(ctx, "whoami").item
        self.assertEqual(item, {
            "user": "ana.pop", "display_name": "Ana Pop", "email": "ana@example.com",
            "kind": "dc", "url": f"{srv.url}/secure/ViewProfile.jspa?name=ana.pop"})

    def test_cloud_hidden_email_is_null(self):
        srv, ctx = self.cloud({"/rest/api/3/myself": {
            "accountId": "5b10:abc", "displayName": "Ana Pop"}})
        item = self.cmd(ctx, "whoami").item
        self.assertEqual(item, {
            "user": "5b10:abc", "display_name": "Ana Pop", "email": None, "kind": "cloud",
            "url": f"{srv.url}/jira/people/5b10:abc"})
        self.assertEqual(srv.requests[0].path, "/rest/api/3/myself")


# --- search -------------------------------------------------------------------------------

class TestSearch(Base):
    def test_dc_offset_paging_across_pages(self):
        pages = {0: [raw_issue("ABC-1"), raw_issue("ABC-2")], 2: [raw_issue("ABC-3")]}

        def search(req):
            start = int(req.query["startAt"][0])
            return {"startAt": start, "maxResults": 2, "total": 3, "issues": pages[start]}

        srv, ctx = self.dc({"/rest/api/2/search": search})
        result = self.cmd(ctx, "search", "project = ABC", "--limit", "10")
        self.assertEqual([i["key"] for i in result.items], ["ABC-1", "ABC-2", "ABC-3"])
        self.assertFalse(result.truncated)
        self.assertEqual(len(srv.requests), 2)
        q = srv.requests[0].query
        self.assertEqual(q["jql"], ["project = ABC"])
        self.assertEqual(q["fields"], [BASE_FIELDS])
        self.assertEqual(q["startAt"], ["0"])
        self.assertIn("maxResults", q)
        self.assertEqual(srv.requests[1].query["startAt"], ["2"])
        item = result.items[0]
        self.assertEqual(set(item), ITEM_KEYS)
        self.assertEqual(item, {"key": "ABC-1", "summary": "Do a thing", "type": "Story",
                                "status": "To Do", "assignee": "Ana Pop", "priority": "Major",
                                "updated": "2026-10-01T10:00:00.000+0000",
                                "url": f"{srv.url}/browse/ABC-1"})

    def test_dc_truncated_at_the_limit(self):
        srv, ctx = self.dc({"/rest/api/2/search": lambda req: {
            "startAt": 0, "maxResults": 2, "total": 40,
            "issues": [raw_issue("ABC-1"), raw_issue("ABC-2")]}})
        result = self.cmd(ctx, "search", "project = ABC", "--limit", "2")
        self.assertEqual(len(result.items), 2)
        self.assertTrue(result.truncated)
        self.assertEqual(srv.requests[0].query["maxResults"], ["2"])

    def test_cloud_token_paging_and_no_start_at(self):
        def search(req):
            if "nextPageToken" not in req.query:
                return {"issues": [raw_issue("ABC-1"), raw_issue("ABC-2")],
                        "nextPageToken": "tok-2", "isLast": False}
            return {"issues": [raw_issue("ABC-3", assignee=None)], "isLast": True}

        srv, ctx = self.cloud({"/rest/api/3/search/jql": search})
        result = self.cmd(ctx, "search", "assignee = currentUser()")
        self.assertEqual([i["key"] for i in result.items], ["ABC-1", "ABC-2", "ABC-3"])
        self.assertFalse(result.truncated)
        self.assertEqual(result.items[2]["assignee"], None)
        self.assertEqual(srv.requests[1].query["nextPageToken"], ["tok-2"])
        for req in srv.requests:
            self.assertEqual(req.path, "/rest/api/3/search/jql")
            self.assertNotIn("startAt", req.query)
            self.assertEqual(req.query["fields"], [BASE_FIELDS])

    def test_cloud_truncated(self):
        srv, ctx = self.cloud({"/rest/api/3/search/jql": {
            "issues": [raw_issue("ABC-1"), raw_issue("ABC-2")], "nextPageToken": "more"}})
        result = self.cmd(ctx, "search", "project = ABC", "--limit", "2")
        self.assertEqual(len(result.items), 2)
        self.assertTrue(result.truncated)
        self.assertEqual(len(srv.requests), 1)

    def test_extra_fields(self):
        issue = raw_issue("ABC-1", extra={"customfield_10016": 5,
                                          "labels": ["x"]})
        srv, ctx = self.dc({"/rest/api/2/search": {"startAt": 0, "total": 1,
                                                   "issues": [issue]}})
        result = self.cmd(ctx, "search", "key = ABC-1", "--fields",
                          "customfield_10016, labels,duedate")
        self.assertEqual(srv.requests[0].query["fields"],
                         [BASE_FIELDS + ",customfield_10016,labels,duedate"])
        self.assertEqual(result.items[0]["fields"],
                         {"customfield_10016": 5, "labels": ["x"], "duedate": None})
        self.assertEqual(set(result.items[0]), ITEM_KEYS | {"fields"})

    def test_limit_is_capped_at_1000(self):
        srv, ctx = self.dc({"/rest/api/2/search": {"startAt": 0, "total": 0, "issues": []}})
        self.cmd(ctx, "search", "project = ABC", "--limit", "5000")
        self.assertLessEqual(int(srv.requests[0].query["maxResults"][0]), 1000)


# --- issue -----------------------------------------------------------------------------

class TestIssue(Base):
    def test_dc_issue_keeps_wiki_text(self):
        srv, ctx = self.dc({"/rest/api/2/issue/ABC-7": full_issue("ABC-7", "h1. Title\n*bold*")})
        item = self.cmd(ctx, "issue", "ABC-7").item
        self.assertEqual(srv.requests[0].query["fields"], [ISSUE_FIELDS])
        self.assertNotIn("expand", srv.requests[0].query)
        self.assertEqual(set(item), ISSUE_KEYS)
        self.assertEqual(item["description"], "h1. Title\n*bold*")
        self.assertEqual(item["reporter"], "Bo Ion")
        self.assertEqual(item["labels"], ["api", "auth"])
        self.assertEqual(item["components"], ["Backend"])
        self.assertEqual(item["fix_versions"], ["1.2"])
        self.assertEqual(item["parent"], "ABC-1")
        self.assertIsNone(item["resolution"])
        self.assertEqual(item["created"], "2026-09-01T09:00:00.000+0000")
        self.assertEqual(item["url"], f"{srv.url}/browse/ABC-7")

    def test_cloud_issue_flattens_adf_and_clips(self):
        long = "x" * 5000
        raw = full_issue("ABC-8", adf("First line", long), parent=None,
                         resolution={"name": "Done"})
        srv, ctx = self.cloud({"/rest/api/3/issue/ABC-8": raw})
        item = self.cmd(ctx, "issue", "ABC-8").item
        self.assertTrue(item["description"].startswith("First line\nxxx"))
        self.assertEqual(len(item["description"]), 4000)
        self.assertIsNone(item["parent"])
        self.assertEqual(item["resolution"], "Done")
        self.assertEqual(srv.requests[0].path, "/rest/api/3/issue/ABC-8")

    def test_links(self):
        links = [
            {"id": "1", "type": {"name": "Blocks", "inward": "is blocked by",
                                 "outward": "blocks"},
             "outwardIssue": {"key": "ABC-9", "fields": {"summary": "Later",
                                                         "status": {"name": "Open"}}}},
            {"id": "2", "type": {"name": "Relates", "inward": "relates to",
                                 "outward": "relates to"},
             "inwardIssue": {"key": "XYZ-2", "fields": {"summary": "Other",
                                                        "status": {"name": "Done"}}}},
        ]
        srv, ctx = self.dc({"/rest/api/2/issue/ABC-7":
                            full_issue("ABC-7", None, issuelinks=links)})
        item = self.cmd(ctx, "issue", "ABC-7", "--links").item
        self.assertEqual(item["links"], [
            {"type": "Blocks", "direction": "outward", "relation": "blocks", "key": "ABC-9",
             "summary": "Later", "status": "Open", "url": f"{srv.url}/browse/ABC-9"},
            {"type": "Relates", "direction": "inward", "relation": "relates to",
             "key": "XYZ-2", "summary": "Other", "status": "Done",
             "url": f"{srv.url}/browse/XYZ-2"},
        ])
        self.assertIsNone(item["description"])
        self.assertNotIn("changelog", item)

    def test_cloud_changelog_paged_oldest_first(self):
        page1 = {"startAt": 0, "maxResults": 2, "total": 3, "isLast": False, "values": [
            history("2026-09-02T10:00:00.000+0000", "Ana Pop",
                    ("status", "To Do", "In Progress"), ("assignee", None, "Ana Pop")),
            history("2026-09-01T10:00:00.000+0000", "Bo Ion", ("summary", "Old", "New"))]}
        page2 = {"startAt": 2, "maxResults": 2, "total": 3, "isLast": True, "values": [
            history("2026-09-03T10:00:00.000+0000", "Ana Pop", ("status", "In Progress", "Done"))]}

        def changelog(req):
            return page2 if req.query.get("startAt") == ["2"] else page1

        srv, ctx = self.cloud({"/rest/api/3/issue/ABC-8": full_issue("ABC-8", adf("d")),
                               "/rest/api/3/issue/ABC-8/changelog": changelog})
        item = self.cmd(ctx, "issue", "ABC-8", "--changelog").item
        self.assertEqual(item["changelog"], [
            {"at": "2026-09-01T10:00:00.000+0000", "author": "Bo Ion", "field": "summary",
             "from": "Old", "to": "New"},
            {"at": "2026-09-02T10:00:00.000+0000", "author": "Ana Pop", "field": "status",
             "from": "To Do", "to": "In Progress"},
            {"at": "2026-09-02T10:00:00.000+0000", "author": "Ana Pop", "field": "assignee",
             "from": None, "to": "Ana Pop"},
            {"at": "2026-09-03T10:00:00.000+0000", "author": "Ana Pop", "field": "status",
             "from": "In Progress", "to": "Done"},
        ])
        self.assertEqual([r.path for r in srv.requests],
                         ["/rest/api/3/issue/ABC-8", "/rest/api/3/issue/ABC-8/changelog",
                          "/rest/api/3/issue/ABC-8/changelog"])
        self.assertNotIn("expand", srv.requests[0].query)

    def test_dc_changelog_by_expand(self):
        raw = full_issue("ABC-7", "d")
        raw["changelog"] = {"startAt": 0, "maxResults": 1, "total": 1, "histories": [
            history("2026-09-02T10:00:00.000+0000", "Ana Pop", ("status", "Open", "Closed"))]}
        srv, ctx = self.dc({"/rest/api/2/issue/ABC-7": raw})
        item = self.cmd(ctx, "issue", "ABC-7", "--changelog").item
        self.assertEqual(len(srv.requests), 1)
        self.assertEqual(srv.requests[0].query["expand"], ["changelog"])
        self.assertEqual(item["changelog"], [
            {"at": "2026-09-02T10:00:00.000+0000", "author": "Ana Pop", "field": "status",
             "from": "Open", "to": "Closed"}])

    def test_missing_issue_is_not_found(self):
        srv, ctx = self.dc({"/rest/api/2/issue/ABC-404": Reply(404, {
            "errorMessages": ["Issue does not exist or you do not have permission to see it."]})})
        with self.assertRaises(http.ConnectorError) as cm:
            self.cmd(ctx, "issue", "ABC-404")
        self.assertEqual(cm.exception.kind, "not_found")


# --- sprints -----------------------------------------------------------------------------

class TestSprints(Base):
    def test_sprints_paged_with_is_last(self):
        s1 = {"id": 11, "name": "Sprint 11", "state": "active", "originBoardId": 7,
              "startDate": "2026-10-01T08:00:00.000Z", "endDate": "2026-10-14T08:00:00.000Z",
              "goal": "Ship login"}
        s2 = {"id": 12, "name": "Sprint 12", "state": "future", "originBoardId": 7}

        def sprints(req):
            if req.query.get("startAt") == ["1"]:
                return {"startAt": 1, "maxResults": 1, "isLast": True, "values": [s2]}
            return {"startAt": 0, "maxResults": 1, "isLast": False, "values": [s1]}

        srv, ctx = self.cloud({"/rest/agile/1.0/board/7/sprint": sprints})
        result = self.cmd(ctx, "sprints", "7")
        self.assertEqual(srv.requests[0].query["state"], ["active,future"])
        self.assertEqual(len(srv.requests), 2)
        self.assertFalse(result.truncated)
        self.assertEqual([set(i) for i in result.items], [SPRINT_KEYS, SPRINT_KEYS])
        self.assertEqual(result.items[0], {
            "id": 11, "name": "Sprint 11", "state": "active",
            "start": "2026-10-01T08:00:00.000Z", "end": "2026-10-14T08:00:00.000Z",
            "complete": None, "goal": "Ship login", "board": 7,
            "url": f"{srv.url}/secure/RapidBoard.jspa?rapidView=7&sprint=11"})
        self.assertIsNone(result.items[1]["goal"])

    def test_state_and_limit(self):
        srv, ctx = self.dc({"/rest/agile/1.0/board/3/sprint": {
            "startAt": 0, "maxResults": 1, "isLast": False,
            "values": [{"id": 1, "name": "S1", "state": "closed"}]}})
        result = self.cmd(ctx, "sprints", "3", "--state", "closed", "--limit", "1")
        self.assertEqual(srv.requests[0].query["state"], ["closed"])
        self.assertTrue(result.truncated)
        self.assertEqual(result.items[0]["board"], 3)


# --- connectors.py end to end -------------------------------------------------------------

class TestCli(Base):
    def test_search_json_end_to_end_without_the_secret(self):
        srv = self.server({"/rest/api/2/search": {"startAt": 0, "total": 1,
                                                  "issues": [raw_issue("ABC-1")]}})
        code, out, err = self.run_cli(self.jira, ["search", "project = ABC", "--json"],
                                      values={"url": srv.url, "token": SECRET})
        self.assertEqual(code, 0, err)
        doc = json.loads(out)
        self.assertEqual(doc["connector"], "jira")
        self.assertEqual(doc["command"], "search")
        self.assertEqual(doc["count"], 1)
        self.assertFalse(doc["truncated"])
        self.assertEqual(doc["items"][0]["url"], f"{srv.url}/browse/ABC-1")
        self.assertEqual(srv.requests[0].headers["Authorization"], f"Bearer {SECRET}")
        self.assertNotIn(SECRET, out + err)

    def test_whoami_and_issue_text_and_401_never_show_the_secret(self):
        srv = self.server({"/rest/api/2/myself": {"name": "ana", "displayName": "Ana"},
                           "/rest/api/2/issue/ABC-7": full_issue("ABC-7", "text"),
                           "/rest/api/2/issue/ABC-401": Reply(401, {
                               "errorMessages": [f"bad token {SECRET}"]})})
        values = {"url": srv.url, "token": SECRET}
        everything = ""
        for argv in (["whoami", "--json"], ["issue", "ABC-7", "--links", "--changelog"]):
            code, out, err = self.run_cli(self.jira, argv, values=values)
            self.assertEqual(code, 0, err)
            everything += out + err
        self.assertIn("ABC-7", everything)
        code, out, err = self.run_cli(self.jira, ["issue", "ABC-401"])
        self.assertEqual(code, 1)
        self.assertIn("connect jira", err)
        self.assertNotIn(SECRET, everything + out + err)


if __name__ == "__main__":
    unittest.main()
