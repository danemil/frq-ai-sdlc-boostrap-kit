#!/usr/bin/env python3
"""Unit tests for the git fallback source (merge commits and tags) on a temp repo."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sources import SourceUnavailable
from sources import git_log


def make_repo(tmp):
    def git(*args, date="2026-10-02T10:00:00+00:00"):
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": tmp,
               "GIT_AUTHOR_NAME": "Ada", "GIT_AUTHOR_EMAIL": "ada@example.com",
               "GIT_COMMITTER_NAME": "Ada", "GIT_COMMITTER_EMAIL": "ada@example.com",
               "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
        subprocess.run(["git", *args], cwd=tmp, check=True, capture_output=True, env=env)

    git("init", "-q", "-b", "main")
    Path(tmp, "a.txt").write_text("a\n")
    git("add", "a.txt")
    git("commit", "-q", "-m", "init", date="2026-09-01T10:00:00+00:00")
    # Bitbucket Cloud style merge, inside the window.
    git("checkout", "-q", "-b", "feature/ATM-10-failover")
    Path(tmp, "b.txt").write_text("b\n")
    git("add", "b.txt")
    git("commit", "-q", "-m", "ATM-10 add failover", date="2026-10-02T09:00:00+00:00")
    git("checkout", "-q", "main")
    git("merge", "-q", "--no-ff", "feature/ATM-10-failover",
        "-m", "Merged in feature/ATM-10-failover (pull request #41)\n\nATM-10 Remote tower voice failover",
        date="2026-10-02T10:00:00+00:00")
    git("tag", "-a", "v5.2.0", "-m", "R5.2", date="2026-10-02T11:00:00+00:00")
    # Bitbucket Data Center style merge, outside the window.
    git("checkout", "-q", "-b", "old")
    Path(tmp, "c.txt").write_text("c\n")
    git("add", "c.txt")
    git("commit", "-q", "-m", "old work", date="2026-09-01T11:00:00+00:00")
    git("checkout", "-q", "main")
    git("merge", "-q", "--no-ff", "old",
        "-m", "Pull request #3: Old cleanup\n\nMerge in ATM/recorder from old to main",
        date="2026-09-02T10:00:00+00:00")
    git("tag", "v5.1.0", date="2026-09-02T11:00:00+00:00")


class GitLogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        make_repo(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_merges_in_window_become_pr_like_rows(self):
        rows = git_log.merges("2026-10-01", "2026-10-31", cwd=self.tmp.name)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["id"], r["state"], r["author"]), (41, "MERGED", "Ada"))
        self.assertEqual(r["title"], "Merged in feature/ATM-10-failover (pull request #41)")
        self.assertEqual(r["source_branch"], "feature/ATM-10-failover")
        self.assertEqual(r["closed"], "2026-10-02T10:00:00Z")
        self.assertEqual(r["keys"], ["ATM-10"])
        self.assertEqual(r["repo"], Path(self.tmp.name).name)
        self.assertEqual(r["source"], "git")
        self.assertEqual(len(r["commit"]), 40)

    def test_datacenter_merge_message_parsed(self):
        rows = git_log.merges("2026-09-01", "2026-09-30", cwd=self.tmp.name)
        self.assertEqual([(r["id"], r["title"]) for r in rows], [(3, "Pull request #3: Old cleanup")])

    def test_until_is_inclusive_of_the_whole_day(self):
        rows = git_log.merges("2026-10-02", "2026-10-02", cwd=self.tmp.name)
        self.assertEqual([r["id"] for r in rows], [41])

    def test_tags_newest_first_with_dates(self):
        tags = git_log.tags(cwd=self.tmp.name)
        self.assertEqual([t["name"] for t in tags], ["v5.2.0", "v5.1.0"])
        self.assertEqual(tags[0]["date"], "2026-10-02T11:00:00Z")
        self.assertEqual(len(tags[1]["commit"]), 40)

    def test_not_a_repo_is_unavailable(self):
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(SourceUnavailable):
                git_log.merges("2026-10-01", "2026-10-31", cwd=empty)


if __name__ == "__main__":
    unittest.main()
