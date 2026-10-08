#!/usr/bin/env python3
"""The bitbucket connector (Bitbucket Data Center, REST 1.0), against tests/fakeserver.py.

Canned JSON follows Atlassian's documented Bitbucket Data Center response shapes
(paged `values` with `isLastPage` / `nextPageStart`, epoch-millisecond dates).

To confirm on a live server:
- the `X-AUSERNAME` response header is sent for requests made with an HTTP access
  token (personal, project or repository), which `whoami` relies on;
- the raw diff endpoint `GET .../pull-requests/{id}.diff` (Bitbucket DC 6.7+),
  which `pr --diff` uses.
"""
import json
import unittest

import helpers  # noqa: F401  puts scripts/ on sys.path
from fakeserver import ConnectorTestCase, Reply, Seq  # noqa: F401
from personal.connectors import http

SECRET = "bbdc-T0KEN-s3cr3t-value-77"
PREFIX = "/rest/api/1.0/projects/PRJ/repos/web"
T1, T2 = 1759915800000, 1759919400000           # 2025-10-08T09:30:00Z, 10:30:00Z
ISO1, ISO2 = "2025-10-08T09:30:00Z", "2025-10-08T10:30:00Z"


def user(name, display):
    return {"name": name, "slug": name, "displayName": display,
            "emailAddress": f"{name}@example.com"}


def raw_pr(n, srv_url="https://bitbucket.example.com", state="OPEN"):
    return {
        "id": n, "title": f"PR {n}", "description": f"Body of {n}", "state": state,
        "createdDate": T1, "updatedDate": T2,
        "author": {"user": user("ana", "Ana Pop"), "role": "AUTHOR"},
        "reviewers": [{"user": user("ion", "Ion Popa"), "status": "APPROVED"},
                      {"user": user("eva", "Eva Ilie"), "status": "UNAPPROVED"}],
        "fromRef": {"id": f"refs/heads/feature/{n}", "displayId": f"feature/{n}"},
        "toRef": {"id": "refs/heads/main", "displayId": "main"},
        "links": {"self": [{"href": f"{srv_url}/projects/PRJ/repos/web/pull-requests/{n}"}]},
    }


def page(values, last=True, next_start=None):
    out = {"values": values, "size": len(values), "isLastPage": last, "start": 0}
    if not last:
        out["nextPageStart"] = next_start
    return out


PR_KEYS = {"id", "title", "state", "author", "reviewers", "from_branch", "to_branch",
           "created", "updated", "url"}


class Base(ConnectorTestCase):
    def setUp(self):
        super().setUp()
        self.bb = self.connector("bitbucket")

    def ctx(self, srv):
        return self.context(self.bb, {"url": srv.url, "token": SECRET})


class TestModule(Base):
    def test_registry_validates_and_fields(self):
        self.assertEqual(self.bb.title, "Bitbucket")
        self.assertEqual(self.bb.keys, ["url", "token", "ca_bundle"])
        token = self.bb.fields[1]
        self.assertTrue(token.secret)
        self.assertEqual([f.key for f in self.bb.applicable({"url": "https://b.example.com"})],
                         ["url", "token", "ca_bundle"])
        self.assertEqual(self.bb.kind({"url": "https://bitbucket.example.com"}), "dc")
        self.assertEqual(set(self.bb.commands), {"prs", "pr", "branches"})

    def test_check_refuses_bitbucket_cloud(self):
        for url in ("https://bitbucket.org", "https://bitbucket.org/team/repo",
                    "https://api.bitbucket.org", "https://www.Bitbucket.org/"):
            reason = self.bb.check({"url": url, "token": SECRET})
            self.assertIn("Bitbucket Cloud is not supported yet", reason or "", url)
        self.assertIsNone(self.bb.check({"url": "https://bitbucket.example.com",
                                         "token": SECRET}))
        self.assertIsNone(self.bb.check({"url": "https://bitbucket.org.example.com",
                                         "token": SECRET}))


class TestWhoami(Base):
    def test_whoami_reads_header_then_user(self):
        srv = self.server({
            "/rest/api/1.0/projects": Reply(200, page([]), {"X-AUSERNAME": "ana.pop"}),
            "/rest/api/1.0/users/ana.pop": user("ana.pop", "Ana Pop"),
        })
        res = self.run_command(self.bb, self.ctx(srv), ["whoami"])
        self.assertEqual(res.item, {"user": "ana.pop", "display_name": "Ana Pop",
                                    "email": "ana.pop@example.com",
                                    "url": f"{srv.url}/users/ana.pop"})
        first = srv.requests[0]
        self.assertEqual(first.path, "/rest/api/1.0/projects")
        self.assertEqual(first.query, {"limit": ["1"]})
        self.assertEqual(first.method, "GET")
        self.assertEqual(first.headers["Authorization"], f"Bearer {SECRET}")
        self.assertEqual(srv.requests[1].path, "/rest/api/1.0/users/ana.pop")

    def test_whoami_without_header_is_unauthorized(self):
        srv = self.server({"/rest/api/1.0/projects": page([])})
        with self.assertRaises(http.ConnectorError) as cm:
            self.run_command(self.bb, self.ctx(srv), ["whoami"])
        self.assertEqual(cm.exception.kind, "unauthorized")
        self.assertIn("Bitbucket did not say who you are", str(cm.exception))

    def test_whoami_tolerates_user_404(self):
        srv = self.server({
            "/rest/api/1.0/projects": Reply(200, page([]), {"X-AUSERNAME": "svc"}),
        })
        res = self.run_command(self.bb, self.ctx(srv), ["whoami"])
        self.assertEqual(res.item, {"user": "svc", "display_name": "svc", "email": None,
                                    "url": f"{srv.url}/users/svc"})


class TestPrs(Base):
    def test_prs_request_and_shape(self):
        srv = self.server({f"{PREFIX}/pull-requests": lambda r: page([raw_pr(7)])})
        res = self.run_command(self.bb, self.ctx(srv), ["prs", "PRJ/web"])
        q = srv.requests[0].query
        self.assertEqual(q["state"], ["OPEN"])
        self.assertEqual(q["order"], ["NEWEST"])
        self.assertEqual(q["limit"], ["25"])
        self.assertEqual(len(res.items), 1)
        it = res.items[0]
        self.assertEqual(set(it), PR_KEYS)
        self.assertEqual(it["id"], 7)
        self.assertEqual(it["author"], "Ana Pop")
        self.assertEqual(it["reviewers"], [{"name": "Ion Popa", "status": "APPROVED"},
                                           {"name": "Eva Ilie", "status": "UNAPPROVED"}])
        self.assertEqual((it["from_branch"], it["to_branch"]), ("feature/7", "main"))
        self.assertEqual((it["created"], it["updated"]), (ISO1, ISO2))
        self.assertEqual(it["url"],
                         "https://bitbucket.example.com/projects/PRJ/repos/web/pull-requests/7")
        self.assertFalse(res.truncated)

    def test_prs_state_all(self):
        srv = self.server({f"{PREFIX}/pull-requests": page([raw_pr(1, state="MERGED")])})
        res = self.run_command(self.bb, self.ctx(srv), ["prs", "PRJ/web", "--state", "ALL"])
        self.assertEqual(srv.requests[0].query["state"], ["ALL"])
        self.assertEqual(res.items[0]["state"], "MERGED")

    def test_prs_paging_and_truncated(self):
        def pages(req):
            start = int(req.query.get("start", ["0"])[0])
            if start == 0:
                return page([raw_pr(1), raw_pr(2)], last=False, next_start=2)
            if start == 2:
                return page([raw_pr(3), raw_pr(4)], last=False, next_start=4)
            return page([raw_pr(5)])
        srv = self.server({f"{PREFIX}/pull-requests": pages})
        res = self.run_command(self.bb, self.ctx(srv), ["prs", "PRJ/web", "--limit", "3"])
        self.assertEqual([p["id"] for p in res.items], [1, 2, 3])
        self.assertTrue(res.truncated)
        self.assertEqual(srv.requests[1].query["start"], ["2"])

        srv.requests.clear()
        res = self.run_command(self.bb, self.ctx(srv), ["prs", "PRJ/web", "--limit", "50"])
        self.assertEqual([p["id"] for p in res.items], [1, 2, 3, 4, 5])
        self.assertFalse(res.truncated)
        self.assertEqual(len(srv.requests), 3)

    def test_bad_repo_shapes_are_config_errors(self):
        srv = self.server({})
        ctx = self.ctx(srv)
        for argv in (["prs", "web"], ["prs", "PRJ/web/1"], ["branches", "/web"],
                     ["pr", "PRJ/web"], ["pr", "PRJ/web/abc"], ["pr", "PRJ//3"]):
            with self.assertRaises(http.ConnectorError, msg=argv) as cm:
                self.run_command(self.bb, ctx, argv)
            self.assertEqual(cm.exception.kind, "config")
            self.assertIn("<project>/<repo>", str(cm.exception))
        self.assertEqual(srv.requests, [])


class TestPr(Base):
    def test_pr_item_with_description(self):
        srv = self.server({f"{PREFIX}/pull-requests/7": raw_pr(7)})
        res = self.run_command(self.bb, self.ctx(srv), ["pr", "PRJ/web/7"])
        self.assertEqual(set(res.item), PR_KEYS | {"description"})
        self.assertEqual(res.item["description"], "Body of 7")
        self.assertEqual(len(srv.requests), 1)

    def test_pr_missing_description_is_null(self):
        raw = raw_pr(8)
        del raw["description"]
        srv = self.server({f"{PREFIX}/pull-requests/8": raw})
        res = self.run_command(self.bb, self.ctx(srv), ["pr", "PRJ/web/8"])
        self.assertIsNone(res.item["description"])

    def test_pr_diff_clipped(self):
        diff = "diff --git a/x b/x\n" + "+line\n" * 100
        srv = self.server({
            f"{PREFIX}/pull-requests/7": raw_pr(7),
            f"{PREFIX}/pull-requests/7.diff": Reply(200, diff, {"Content-Type": "text/plain"}),
        })
        res = self.run_command(self.bb, self.ctx(srv),
                               ["pr", "PRJ/web/7", "--diff", "--max-diff-bytes", "50"])
        self.assertEqual(res.item["diff"], diff[:50])
        self.assertTrue(res.item["diff_truncated"])
        req = srv.requests[1]
        self.assertEqual(req.path, f"{PREFIX}/pull-requests/7.diff")
        self.assertEqual(req.headers["Accept"], "text/plain")

        res = self.run_command(self.bb, self.ctx(srv), ["pr", "PRJ/web/7", "--diff"])
        self.assertEqual(res.item["diff"], diff)
        self.assertFalse(res.item["diff_truncated"])

    def test_pr_comments(self):
        acts = [
            {"id": 1, "action": "OPENED", "createdDate": T1, "user": user("ana", "Ana Pop")},
            {"id": 2, "action": "COMMENTED", "commentAction": "ADDED", "createdDate": T1,
             "user": user("ion", "Ion Popa"),
             "comment": {"id": 101, "text": "Looks good", "createdDate": T1,
                         "author": user("ion", "Ion Popa")}},
            {"id": 3, "action": "APPROVED", "createdDate": T2, "user": user("ion", "Ion Popa")},
        ]
        acts2 = [
            {"id": 4, "action": "COMMENTED", "commentAction": "ADDED", "createdDate": T2,
             "user": user("eva", "Eva Ilie"),
             "commentAnchor": {"path": "src/app.py", "line": 12, "lineType": "ADDED"},
             "comment": {"id": 102, "text": "Rename this", "createdDate": T2,
                         "author": user("eva", "Eva Ilie")}},
        ]

        def activities(req):
            if req.query.get("start", ["0"])[0] == "0":
                return page(acts, last=False, next_start=3)
            return page(acts2)
        srv = self.server({f"{PREFIX}/pull-requests/7": raw_pr(7),
                           f"{PREFIX}/pull-requests/7/activities": activities})
        res = self.run_command(self.bb, self.ctx(srv), ["pr", "PRJ/web/7", "--comments"])
        pr_url = "https://bitbucket.example.com/projects/PRJ/repos/web/pull-requests/7"
        self.assertEqual(res.item["comments"], [
            {"id": 101, "author": "Ion Popa", "text": "Looks good", "created": ISO1,
             "path": None, "line": None, "url": pr_url + "/overview?commentId=101"},
            {"id": 102, "author": "Eva Ilie", "text": "Rename this", "created": ISO2,
             "path": "src/app.py", "line": 12, "url": pr_url + "/overview?commentId=102"},
        ])
        self.assertNotIn("diff", res.item)
        self.assertEqual([r.path for r in srv.requests][1:],
                         [f"{PREFIX}/pull-requests/7/activities"] * 2)

    def test_pr_not_found(self):
        srv = self.server({})
        with self.assertRaises(http.ConnectorError) as cm:
            self.run_command(self.bb, self.ctx(srv), ["pr", "PRJ/web/404"])
        self.assertEqual(cm.exception.kind, "not_found")


class TestBranches(Base):
    def test_branches_request_and_shape(self):
        raw = [
            {"id": "refs/heads/main", "displayId": "main", "type": "BRANCH",
             "latestCommit": "abc123", "isDefault": True},
            {"id": "refs/heads/feature/x", "displayId": "feature/x", "type": "BRANCH",
             "latestCommit": "def456", "isDefault": False},
        ]
        srv = self.server({f"{PREFIX}/branches": page(raw)})
        res = self.run_command(self.bb, self.ctx(srv),
                               ["branches", "PRJ/web", "--filter", "feat"])
        q = srv.requests[0].query
        self.assertEqual(q["filterText"], ["feat"])
        self.assertEqual(q["orderBy"], ["MODIFICATION"])
        self.assertEqual(q["limit"], ["50"])
        self.assertEqual(res.items[1], {
            "name": "feature/x", "id": "refs/heads/feature/x", "latest_commit": "def456",
            "is_default": False,
            "url": f"{srv.url}/projects/PRJ/repos/web/browse?at=refs%2Fheads%2Ffeature%2Fx"})
        self.assertTrue(res.items[0]["is_default"])

    def test_branches_without_filter_sends_none(self):
        srv = self.server({f"{PREFIX}/branches": page([])})
        res = self.run_command(self.bb, self.ctx(srv), ["branches", "PRJ/web"])
        self.assertNotIn("filterText", srv.requests[0].query)
        self.assertEqual(res.items, [])


class TestCli(Base):
    def test_cli_prs_json_end_to_end_without_secret(self):
        srv = self.server({f"{PREFIX}/pull-requests": page([raw_pr(7)])})
        code, out, err = self.run_cli(self.bb, ["prs", "PRJ/web", "--json"],
                                      values={"url": srv.url, "token": SECRET})
        self.assertEqual(code, 0, err)
        doc = json.loads(out)
        self.assertEqual((doc["connector"], doc["command"], doc["count"], doc["truncated"]),
                         ("bitbucket", "prs", 1, False))
        self.assertEqual(doc["source"], srv.url)
        self.assertEqual(doc["items"][0]["id"], 7)
        self.assertNotIn(SECRET, out + err)
        self.assertTrue(all(r.method == "GET" for r in srv.requests))

    def test_cli_errors_never_show_secret(self):
        srv = self.server({
            "/rest/api/1.0/projects": Reply(401, {"errors": [{"message": f"bad {SECRET}"}]}),
            f"{PREFIX}/pull-requests/9": Reply(404, {"errors": [{"message": SECRET}]}),
        })
        values = {"url": srv.url, "token": SECRET}
        code, out, err = self.run_cli(self.bb, ["whoami"], values=values)
        self.assertEqual(code, 1)
        self.assertIn("setup.py connect bitbucket", err)
        code2, out2, err2 = self.run_cli(self.bb, ["pr", "PRJ/web/9", "--json"], values=values)
        self.assertEqual(code2, 1)
        self.assertNotIn(SECRET, out + err + out2 + err2)


if __name__ == "__main__":
    unittest.main()
