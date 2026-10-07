#!/usr/bin/env python3
"""Unit tests for the Bitbucket PR source (deck-builder design §3.1). No network."""
import io
import json
import sys
import unittest
import urllib.error
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sources import SourceUnavailable
from sources import bitbucket_prs as bb

FIX = Path(__file__).resolve().parent / "fixtures"
CLOUD_PAGES = json.loads((FIX / "bb_cloud_prs.json").read_text(encoding="utf-8"))
DC_PAGES = json.loads((FIX / "bb_dc_prs.json").read_text(encoding="utf-8"))

CLOUD_CFG = {"bitbucket": {"deployment": "cloud", "workspace": "frq", "repos": ["vcs-core"]}}
DC_CFG = {"bitbucket": {"deployment": "datacenter", "base_url_env": "BITBUCKET_BASE_URL",
                        "project": "ATM", "repos": ["recorder"]}}
TOKEN_ENV = {"BITBUCKET_TOKEN": "t0ken", "BITBUCKET_BASE_URL": "https://bitbucket.example.com"}


class FakeHttp:
    """Serves fixture pages in order and records every request."""
    def __init__(self, pages):
        self.pages, self.calls = list(pages), []

    def __call__(self, url, headers):
        self.calls.append((url, headers))
        return self.pages.pop(0)


def by_id(prs):
    return {p["id"]: p for p in prs}


class KeysTest(unittest.TestCase):
    def test_keys_from_title_and_branch_deduplicated_and_sorted(self):
        self.assertEqual(bb.extract_keys("Fix radio path ATM-12, ATM-10", "bugfix/ATM-12-radio"),
                         ["ATM-10", "ATM-12"])
        self.assertEqual(bb.extract_keys("Bump logging library", "chore/bump-logging"), [])
        self.assertEqual(bb.extract_keys("", "feature/ATM-7-retention"), ["ATM-7"])


class NormalizeTest(unittest.TestCase):
    def test_cloud(self):
        pr = bb.normalize_pr(CLOUD_PAGES[0]["values"][0], "cloud", "vcs-core")
        self.assertEqual(pr, {
            "repo": "vcs-core", "id": 41, "title": "ATM-10 Remote tower voice failover",
            "state": "MERGED", "author": "Ada", "source_branch": "feature/ATM-10-failover",
            "target_branch": "main", "created": "2026-10-02T08:00:00Z",
            "updated": "2026-10-03T14:30:00Z", "closed": "2026-10-03T14:30:00Z",
            "keys": ["ATM-10"], "url": "https://bitbucket.org/frq/vcs-core/pull-requests/41"})

    def test_cloud_open_pr_has_no_closed_time(self):
        pr = bb.normalize_pr(CLOUD_PAGES[0]["values"][1], "cloud", "vcs-core")
        self.assertEqual((pr["state"], pr["closed"], pr["keys"]), ("OPEN", "", []))

    def test_cloud_superseded_counts_as_declined(self):
        raw = dict(CLOUD_PAGES[0]["values"][1], state="SUPERSEDED")
        self.assertEqual(bb.normalize_pr(raw, "cloud", "vcs-core")["state"], "DECLINED")

    def test_datacenter(self):
        pr = bb.normalize_pr(DC_PAGES[0]["values"][0], "datacenter", "recorder")
        self.assertEqual(pr["author"], "J. Doe")
        self.assertEqual((pr["source_branch"], pr["target_branch"]), ("feature/ATM-7-retention", "develop"))
        self.assertEqual((pr["created"], pr["closed"]), ("2026-10-01T08:00:00Z", "2026-10-02T09:00:00Z"))
        self.assertEqual(pr["keys"], ["ATM-7"])
        self.assertTrue(pr["url"].endswith("/pull-requests/7"))


class FetchTest(unittest.TestCase):
    def test_cloud_follows_next_and_filters_window(self):
        http = FakeHttp(CLOUD_PAGES)
        prs, meta = bb.fetch(CLOUD_CFG, "2026-10-01", "2026-10-31", http_get=http, env=TOKEN_ENV)
        self.assertEqual(sorted(by_id(prs)), [39, 41, 42])
        first_url = http.calls[0][0]
        self.assertTrue(first_url.startswith(
            "https://api.bitbucket.org/2.0/repositories/frq/vcs-core/pullrequests?"))
        query = urllib.parse.parse_qs(urllib.parse.urlparse(first_url).query)
        self.assertEqual(sorted(query["state"]), ["DECLINED", "MERGED", "OPEN", "SUPERSEDED"])
        self.assertIn('updated_on >= 2026-10-01T00:00:00+00:00', query["q"][0])
        self.assertEqual(http.calls[1][0], CLOUD_PAGES[0]["next"])
        self.assertEqual(http.calls[0][1]["Authorization"], "Bearer t0ken")
        self.assertEqual(meta, {"tier": "script", "deployment": "cloud", "repos": ["vcs-core"],
                                "count": 3, "window": ["2026-10-01", "2026-10-31"]})

    def test_datacenter_offset_paging_and_window(self):
        http = FakeHttp(DC_PAGES)
        prs, _ = bb.fetch(DC_CFG, "2026-10-01", "2026-10-31", http_get=http, env=TOKEN_ENV)
        self.assertEqual(sorted(by_id(prs)), [7, 8])  # #3 closed in September: out of window
        self.assertIn("/rest/api/1.0/projects/ATM/repos/recorder/pull-requests?", http.calls[0][0])
        self.assertIn("start=2", http.calls[1][0])

    def test_open_pr_created_after_window_is_excluded(self):
        prs, _ = bb.fetch(DC_CFG, "2026-09-01", "2026-09-30", http_get=FakeHttp(DC_PAGES), env=TOKEN_ENV)
        self.assertEqual(sorted(by_id(prs)), [3])

    def test_basic_auth_fallback(self):
        http = FakeHttp(DC_PAGES)
        env = {"BITBUCKET_USER": "u", "BITBUCKET_APP_PASSWORD": "p",
               "BITBUCKET_BASE_URL": "https://bitbucket.example.com"}
        bb.fetch(DC_CFG, "2026-10-01", "2026-10-31", http_get=http, env=env)
        self.assertEqual(http.calls[0][1]["Authorization"], "Basic dTpw")

    def test_results_sorted_by_repo_then_id(self):
        prs, _ = bb.fetch(CLOUD_CFG, "2026-10-01", "2026-10-31", http_get=FakeHttp(CLOUD_PAGES),
                          env=TOKEN_ENV)
        self.assertEqual([p["id"] for p in prs], [39, 41, 42])

    def test_page_cap_stops_runaway_paging(self):
        looping = [dict(CLOUD_PAGES[0]) for _ in range(5)]
        cfg = {"bitbucket": dict(CLOUD_CFG["bitbucket"], max_pages=2)}
        http = FakeHttp(looping)
        bb.fetch(cfg, "2026-10-01", "2026-10-31", http_get=http, env=TOKEN_ENV)
        self.assertEqual(len(http.calls), 2)


class UnavailableTest(unittest.TestCase):
    def test_no_bitbucket_config(self):
        with self.assertRaises(SourceUnavailable):
            bb.fetch({}, "2026-10-01", "2026-10-31", http_get=FakeHttp([]), env=TOKEN_ENV)

    def test_no_credentials(self):
        with self.assertRaises(SourceUnavailable) as ctx:
            bb.fetch(CLOUD_CFG, "2026-10-01", "2026-10-31", http_get=FakeHttp([]), env={})
        self.assertIn("BITBUCKET_TOKEN", str(ctx.exception))

    def test_datacenter_needs_base_url(self):
        with self.assertRaises(SourceUnavailable) as ctx:
            bb.fetch(DC_CFG, "2026-10-01", "2026-10-31", http_get=FakeHttp([]),
                     env={"BITBUCKET_TOKEN": "t"})
        self.assertIn("BITBUCKET_BASE_URL", str(ctx.exception))

    def test_http_failure_becomes_unavailable(self):
        def failing(url, headers):
            raise SourceUnavailable("bitbucket: HTTP 401")
        with self.assertRaises(SourceUnavailable):
            bb.fetch(CLOUD_CFG, "2026-10-01", "2026-10-31", http_get=failing, env=TOKEN_ENV)


class HttpRetryTest(unittest.TestCase):
    def _http_error(self, code, retry_after=None):
        headers = {"Retry-After": retry_after} if retry_after else {}
        return urllib.error.HTTPError("https://x", code, "err", headers, io.BytesIO(b""))

    def test_retries_once_on_429_honouring_retry_after(self):
        calls, sleeps = [], []

        class Resp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def opener(req, timeout):
            calls.append(req.full_url)
            if len(calls) == 1:
                raise self._http_error(429, "3")
            return Resp(b'{"ok": true}')

        self.assertEqual(bb._http_get("https://x", {}, opener=opener, sleep=sleeps.append), {"ok": True})
        self.assertEqual((len(calls), sleeps), (2, [3.0]))

    def test_second_failure_and_4xx_raise_unavailable(self):
        def always_503(req, timeout):
            raise self._http_error(503)

        def always_401(req, timeout):
            raise self._http_error(401)

        with self.assertRaises(SourceUnavailable):
            bb._http_get("https://x", {}, opener=always_503, sleep=lambda s: None)
        with self.assertRaises(SourceUnavailable) as ctx:
            bb._http_get("https://x", {}, opener=always_401, sleep=lambda s: None)
        self.assertIn("401", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
