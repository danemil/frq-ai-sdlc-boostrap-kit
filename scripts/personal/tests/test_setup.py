#!/usr/bin/env python3
"""`setup`: hide and move the kit first, place the files, write state last."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers
from personal import paths
from personal.connectors import store

ARGS = ["setup", "--name", "Ana Pop", "--roles", "po,sm", "--lang", "de"]


class TestSetup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = helpers.make_repo(Path(self.tmp.name).resolve() / "repo",
                                      {"README.md": "team\n"})
        self.copy = helpers.copy_kit(self.root / "tools/ai-sdlc-kit")
        self.kit = self.root / paths.KIT_REL

    def tearDown(self):
        self.tmp.cleanup()

    def status(self):
        return helpers.git(self.root, "status", "--porcelain").stdout

    def test_protect_only_moves_and_hides_the_kit(self):
        code, out = helpers.cli(self.root, self.copy, "setup", "--protect-only")
        self.assertEqual(code, 0, out)
        self.assertIn("The kit is now in .ai-sdlc/kit and hidden from git.", out)
        self.assertFalse(self.copy.exists())
        self.assertTrue((self.kit / "setup.py").is_file())
        self.assertEqual(self.status(), "")
        self.assertFalse((self.root / paths.STATE_REL).exists())

    def test_setup_places_the_files_and_git_sees_nothing(self):
        code, out = helpers.cli(self.root, self.copy, *ARGS)
        self.assertEqual(code, 0, out)
        self.assertIn("Set up AI-SDLC", out)
        self.assertIn("for Ana Pop: Product Owner, Scrum Master / Team Coach (SAFe) · German (Deutsch).", out)
        for rel in (".github/instructions/ai-sdlc-core.instructions.md",
                    ".github/instructions/ai-sdlc-po.instructions.md",
                    ".github/instructions/ai-sdlc-sm.instructions.md",
                    ".agents/skills/ai-sdlc-playbook-product/SKILL.md",
                    ".agents/skills/ai-sdlc-playbook-sm/SKILL.md", paths.USER_REL):
            self.assertTrue((self.root / rel).is_file(), rel)
        self.assertEqual(self.status(), "")

    def test_state_records_the_choices_the_version_and_every_file(self):
        helpers.cli(self.root, self.copy, *ARGS)
        st = json.loads((self.root / paths.STATE_REL).read_text())
        self.assertEqual(st["choices"]["roles"], ["po", "sm"])
        self.assertEqual(st["kit_version"], paths.kit_version(self.kit))
        self.assertIn(paths.USER_REL, st["files"])

    def test_running_setup_again_changes_nothing_but_the_timestamp(self):
        helpers.cli(self.root, self.copy, *ARGS)
        before = helpers.snapshot(self.root)
        code, out = helpers.cli(self.root, self.kit, *ARGS)
        self.assertEqual(code, 0, out)
        after = helpers.snapshot(self.root)
        for snap in (before, after):
            snap.pop(paths.STATE_REL)
        self.assertEqual(after, before)

    def test_a_bad_role_or_language_is_a_plain_error(self):
        code, out = helpers.cli(self.root, self.copy, "setup", "--name", "Ana",
                                "--roles", "po,boss", "--lang", "de")
        self.assertEqual(code, 2)
        self.assertIn("(not known: boss)", out)
        code, out = helpers.cli(self.root, self.kit, "setup", "--name", "Ana",
                                "--roles", "po", "--lang", "fr")
        self.assertEqual(code, 2)
        self.assertIn("Choose a language from: en, ro, de.", out)
        self.assertFalse((self.root / ".github").exists())

    def test_a_second_kit_copy_is_sent_to_update(self):
        helpers.cli(self.root, self.copy, *ARGS)
        newer = helpers.copy_kit(self.root / "newer-kit")
        code, out = helpers.cli(self.root, newer, *ARGS)
        self.assertEqual(code, 2)
        self.assertIn('say "update the kit"', out)

    def test_a_non_git_folder_works_and_says_so(self):
        plain = Path(self.tmp.name).resolve() / "plain"
        copy = helpers.copy_kit(plain / "kit")
        code, out = helpers.cli(plain, copy, *ARGS)
        self.assertEqual(code, 0, out)
        self.assertIn("not a git repo, so nothing hides these files from git", out)

    def test_the_summary_names_the_roles_connectors_and_marks_connected_ones(self):
        secret = "summary-S3CRET-token-77"
        with mock.patch.dict(os.environ, {"AI_SDLC_CONFIG_DIR": str(Path(self.tmp.name) / "cfg")}):
            code, out = helpers.cli(self.root, self.copy, *ARGS)          # po, sm
            self.assertEqual(code, 0, out)
            self.assertIn("- Connectors for your roles: jira, confluence, jama "
                          "(say 'connect jira')", out)
            store.save("jira", {"url": "https://jira.example.com", "token": secret})
            code, out = helpers.cli(self.root, self.kit, "change", "--roles", "sm")
            self.assertEqual(code, 0, out)
            self.assertIn("- Connectors for your roles: jira (connected), confluence "
                          "(say 'connect confluence')", out)
            store.save("confluence", {"url": "https://wiki.example.com", "token": secret})
            code, out = helpers.cli(self.root, self.kit, "change", "--roles", "sm")
            self.assertIn("- Connectors for your roles: jira (connected), confluence (connected)\n",
                          out)
            self.assertNotIn(secret, out)
        self.assertEqual(self.status(), "")

    def test_the_real_cli_from_a_copied_folder(self):
        r = subprocess.run([sys.executable, str(self.copy / "setup.py"), "setup", "--protect-only"],
                           cwd=self.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = subprocess.run([sys.executable, ".ai-sdlc/kit/setup.py", *ARGS],
                           cwd=self.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.status(), "")


if __name__ == "__main__":
    unittest.main()
