#!/usr/bin/env python3
"""The session-start hook: setup places a git-hidden `.github/hooks/ai-sdlc-session.json`
that Copilot CLI runs at the start of a session (in a trusted folder); `check --quiet --hook`
prints the JSON whose `additionalContext` Copilot adds to the conversation. It never fails."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers
from personal import checks, paths

ARGS = ["setup", "--name", "Ana", "--roles", "po,sm", "--lang", "de"]
HOOK = paths.SESSION_HOOK_REL
TEAM_HOOK = ".github/hooks/team.json"


class TestSessionHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.root = helpers.make_repo(self.base / "repo", {
            "README.md": "x\n", TEAM_HOOK: '{"version": 1, "hooks": {}}\n'})
        self.before = helpers.snapshot(self.root)
        self.kit = self.root / paths.KIT_REL
        code, out = helpers.cli(self.root, helpers.copy_kit(self.root / "ai-sdlc-kit"), *ARGS)
        self.assertEqual(code, 0, out)

    def tearDown(self):
        self.tmp.cleanup()

    def hook_json(self, cwd=None):
        code, out = helpers.cli(cwd or self.root, self.kit, "check", "--quiet", "--hook")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        return json.loads(out)

    def test_setup_places_the_hook_hidden_from_git(self):
        hook = json.loads((self.root / HOOK).read_text(encoding="utf-8"))
        self.assertEqual(hook["version"], 1)
        [entry] = hook["hooks"]["sessionStart"]
        self.assertEqual(entry["type"], "command")
        self.assertEqual(entry["bash"], "python3 .ai-sdlc/kit/setup.py check --quiet --hook")
        self.assertEqual(entry["powershell"], entry["bash"])
        self.assertEqual(entry["cwd"], ".")
        self.assertLessEqual(entry["timeoutSec"], 30)
        self.assertEqual(helpers.git(self.root, "status", "--porcelain").stdout, "")
        self.assertEqual([fid for fid, _ in checks.run(self.root)[1]], [])
        self.assertEqual((self.root / TEAM_HOOK).read_text(), '{"version": 1, "hooks": {}}\n')

    def test_the_hook_output_carries_the_session_check(self):
        version = paths.kit_version(self.kit)
        ctx = self.hook_json()["additionalContext"]
        self.assertIn(f"AI-SDLC {version} · roles: PO, SM · de · ok", ctx)
        self.assertIn("session hook", ctx)
        self.assertIn("no need to run it again", ctx)

    def test_a_warning_reaches_the_context(self):
        (self.root / ".github/instructions/ai-sdlc-core.instructions.md").unlink()
        ctx = self.hook_json()["additionalContext"]
        self.assertIn("is missing", ctx)
        self.assertIn("mention", ctx)

    def test_never_fails(self):
        with mock.patch.object(checks, "run", side_effect=RuntimeError("boom")):
            ctx = self.hook_json()["additionalContext"]
        self.assertIn("could not run", ctx)

    def test_a_folder_without_the_kit_still_gets_json(self):
        plain = helpers.make_repo(self.base / "other", {"README.md": "x\n"})
        ctx = self.hook_json(cwd=plain)["additionalContext"]
        self.assertIn("not set up", ctx)

    def test_another_ai_sdlc_hook_is_unknown(self):
        (self.root / ".github/hooks/ai-sdlc-extra.json").write_text("{}\n")
        self.assertEqual([fid for fid, _ in checks.run(self.root)[1]],
                         ["unknown:.github/hooks/ai-sdlc-extra.json"])

    def test_remove_takes_the_hook_back_and_keeps_the_team_hook(self):
        code, out = helpers.cli(self.root, self.kit, "remove", "--yes")
        self.assertEqual(code, 0, out)
        self.assertEqual(helpers.snapshot(self.root), self.before)

    def test_an_update_from_a_kit_without_the_hook_adds_it(self):
        (self.root / HOOK).unlink()
        st_files = json.loads((self.root / paths.STATE_REL).read_text())
        st_files["files"].pop(HOOK)
        (self.root / paths.STATE_REL).write_text(json.dumps(st_files))
        code, out = helpers.cli(self.root, self.kit, "change")
        self.assertEqual(code, 0, out)
        self.assertTrue((self.root / HOOK).is_file())
        self.assertEqual(helpers.git(self.root, "status", "--porcelain").stdout, "")


if __name__ == "__main__":
    unittest.main()
