#!/usr/bin/env python3
"""All five connectors end to end, as subprocesses: setup.py connect (without a terminal,
from AI_SDLC_<NAME>_* variables), connect --test, connections, connectors.py --json and
disconnect, against one fake server (tests/fake_tools.py; no network). No secret may
appear in any output; credentials land only in the temporary AI_SDLC_CONFIG_DIR."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import helpers
import fake_tools
from fakeserver import FakeServer

KIT = helpers.KIT
# connector: (connectors.py arguments, a check of the --json document)
READS = {
    "jira": (["search", "project = ABC"],
             lambda d: [i["key"] for i in d["items"]] == ["ABC-1", "ABC-2"]),
    "confluence": (["search", "runbook"],
                   lambda d: d["items"][0]["title"] == "Release runbook"),
    "bitbucket": (["prs", "ABC/app"], lambda d: d["items"][0]["from_branch"] == "fix/safari"),
    "jama": (["item", "1001"], lambda d: d["item"]["key"] == "REQ-1"),
    "jenkins": (["job", "app/main"], lambda d: d["item"]["status"] == "success"),
}


class TestConnectorsEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = FakeServer(fake_tools.routes()).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.config = self.base / "config"
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith("AI_SDLC_") and k.upper() not in
                    ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")}
        self.env.update(AI_SDLC_CONFIG_DIR=str(self.config), NO_PROXY="127.0.0.1",
                        no_proxy="127.0.0.1", PYTHONDONTWRITEBYTECODE="1")
        self.shown = []

    def run_kit(self, script, *argv, env=None, cwd=None):
        """Run a kit script without a terminal (stdin is /dev/null): (code, stdout + stderr)."""
        r = subprocess.run([sys.executable, str(KIT / script), *argv], cwd=cwd or self.base,
                           env={**self.env, **(env or {})}, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=60)
        self.shown.append(r.stdout + r.stderr)
        return r.returncode, r.stdout + r.stderr, r.stdout

    def assertNoSecretShown(self):
        everything = "\n".join(self.shown)
        for secret in fake_tools.SECRETS:
            self.assertNotIn(secret, everything)

    def test_each_connector_connects_reads_and_disconnects(self):
        for name, (argv, check) in READS.items():
            with self.subTest(connector=name):
                env = fake_tools.env_for(self.srv.url, name)
                code, out, _ = self.run_kit("setup.py", "connect", name, env=env)
                self.assertEqual(code, 0, out)
                self.assertIn("Test: OK: signed in to 127.0.0.1", out)
                saved = self.config / "connectors" / f"{name}.json"
                self.assertEqual(stat.S_IMODE(saved.stat().st_mode), 0o600)
                # From here on the values come from the saved file only.
                code, out, _ = self.run_kit("setup.py", "connect", name, "--test")
                self.assertEqual(code, 0, out)
                self.assertIn("OK: signed in", out)
                code, out, _ = self.run_kit("setup.py", "connections")
                self.assertIn(f"- {name}: {self.srv.url}", out)
                self.assertIn("last test OK", out)
                code, out, stdout = self.run_kit("connectors.py", name, *argv, "--json")
                self.assertEqual(code, 0, out)
                doc = json.loads(stdout)
                self.assertEqual((doc["connector"], doc["source"]), (name, self.srv.url))
                self.assertTrue(check(doc), doc)
                for item in doc.get("items") or [doc.get("item")]:
                    self.assertTrue(item["url"], item)
                code, out, _ = self.run_kit("connectors.py", name, "whoami")
                self.assertEqual(code, 0, out)
                self.assertIn("user: ana", out)
                code, out, _ = self.run_kit("setup.py", "disconnect", name)
                self.assertIn("Removed the saved", out)
                self.assertFalse(saved.exists())
                code, out, _ = self.run_kit("connectors.py", name, "whoami")
                self.assertEqual(code, 3, out)
        self.assertNoSecretShown()

    def test_connect_without_a_terminal_or_values_points_at_the_terminal(self):
        code, out, _ = self.run_kit("setup.py", "connect", "jira")
        self.assertEqual(code, 2, out)
        self.assertIn("runs only in your own terminal", out)
        self.assertIn("python3 .ai-sdlc/kit/setup.py connect jira", out)
        self.assertIn("AI_SDLC_JIRA_URL, AI_SDLC_JIRA_TOKEN", out)
        self.assertFalse((self.config / "connectors" / "jira.json").exists())

    def test_a_wrong_token_is_a_plain_401_and_never_shown(self):
        env = {**fake_tools.env_for(self.srv.url, "jira"), "AI_SDLC_JIRA_TOKEN": "wrong-T0KEN-9"}
        code, out, _ = self.run_kit("connectors.py", "jira", "whoami", env=env)
        self.assertEqual(code, 1, out)
        self.assertIn("401 Unauthorized", out)
        self.assertIn("python3 .ai-sdlc/kit/setup.py connect jira", out)
        self.assertNotIn("wrong-T0KEN-9", out)

    def test_setup_and_remove_never_touch_the_credentials(self):
        code, out, _ = self.run_kit("setup.py", "connect", "jira",
                                    env=fake_tools.env_for(self.srv.url, "jira"))
        self.assertEqual(code, 0, out)
        before = helpers.snapshot(self.config)
        root = helpers.make_repo(self.base / "repo", {"README.md": "team\n"})
        helpers.copy_kit(root / "ai-sdlc-kit")
        for argv in (["ai-sdlc-kit/setup.py", "setup", "--protect-only"],
                     [".ai-sdlc/kit/setup.py", "setup", "--name", "Ana", "--roles", "dev",
                      "--lang", "en"],
                     [".ai-sdlc/kit/setup.py", "remove"]):
            r = subprocess.run([sys.executable, *argv], cwd=root, env=self.env, text=True,
                               stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.shown.append(r.stdout + r.stderr)
        self.assertIn("- Connectors for your roles: bitbucket, jira (connected), jenkins "
                      "(say 'connect bitbucket')", "\n".join(self.shown))
        self.assertEqual(helpers.snapshot(self.config), before)
        self.assertEqual(helpers.git(root, "status", "--porcelain").stdout, "")
        self.assertFalse((root / ".config").exists())
        self.assertNoSecretShown()


if __name__ == "__main__":
    unittest.main()
