#!/usr/bin/env python3
"""`check`: missing, unknown and unhidden files, kit copies, a stale kit, the one-liner."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers
from personal import checks, exclude, paths

ARGS = ["setup", "--name", "Ana", "--roles", "po,sm", "--lang", "de"]
CORE = ".github/instructions/ai-sdlc-core.instructions.md"


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = helpers.make_repo(Path(self.tmp.name).resolve() / "repo", {"README.md": "x\n"})
        self.kit = self.root / paths.KIT_REL
        code, self.setup_out = helpers.cli(self.root, helpers.copy_kit(self.root / "kit-copy"), *ARGS)
        self.assertEqual(code, 0, self.setup_out)

    def tearDown(self):
        self.tmp.cleanup()

    def ids(self):
        return [fid for fid, _ in checks.run(self.root)[1]]

    def test_a_fresh_setup_is_clean_and_the_one_liner_says_ok(self):
        self.assertEqual(self.ids(), [])
        self.assertIn("Check: all good.", self.setup_out)
        code, out = helpers.cli(self.root, self.kit, "check", "--quiet")
        version = paths.kit_version(self.kit)
        self.assertEqual((code, out), (0, f"AI-SDLC {version} · roles: PO, SM · de · ok\n"))

    def test_a_deleted_file_is_missing(self):
        (self.root / CORE).unlink()
        self.assertEqual(self.ids(), [f"missing:{CORE}"])

    def test_files_the_kit_did_not_write_are_unknown(self):
        (self.root / ".github/instructions/ai-sdlc-extra.instructions.md").write_text("x\n")
        stray = self.root / ".claude/skills/ai-sdlc-notes/SKILL.md"
        stray.parent.mkdir(parents=True)
        stray.write_text("x\n")
        self.assertEqual(sorted(self.ids()), [
            "unexcluded:.claude/skills/ai-sdlc-notes/SKILL.md",
            "unknown:.claude/skills/ai-sdlc-notes/SKILL.md",
            "unknown:.github/instructions/ai-sdlc-extra.instructions.md"])

    def test_a_removed_exclude_block_is_reported(self):
        exclude.unprotect(self.root)
        ids = self.ids()
        self.assertIn(f"unexcluded:{CORE}", ids)
        self.assertIn(f"unexcluded:{paths.USER_REL}", ids)
        self.assertIn(f"unexcluded:{paths.KIT_REL}", ids)

    def test_kit_copies_are_reported_and_a_newer_one_waits(self):
        newer = helpers.copy_kit(self.root / "downloads/ai-sdlc-kit")
        (newer / "VERSION").write_text("9.9.9\n")
        found = dict(checks.run(self.root)[1])
        self.assertEqual(found["kit-copy:downloads/ai-sdlc-kit"],
                         'A newer kit (9.9.9) is waiting in downloads/ai-sdlc-kit. Say "update the kit".')
        (newer / "VERSION").write_text("0.0.1\n")
        found = dict(checks.run(self.root)[1])
        self.assertIn("is a copy of the kit that git does not hide", found["kit-copy:downloads/ai-sdlc-kit"])

    def test_a_kit_folder_newer_than_the_state_is_stale(self):
        (self.kit / "VERSION").write_text("9.9.9\n")
        self.assertEqual(self.ids(), ["stale-kit"])

    def test_check_exit_codes(self):
        self.assertEqual(helpers.cli(self.root, self.kit, "check")[0], 0)
        (self.root / CORE).unlink()
        code, out = helpers.cli(self.root, self.kit, "check")
        self.assertEqual(code, 1)
        self.assertIn(f"- [missing:{CORE}] {CORE} is missing.", out)
        code, out = helpers.cli(self.root, self.kit, "check", "--quiet")
        self.assertEqual(code, 0)
        self.assertIn("· 1 to look at:", out)

    def test_quiet_never_fails(self):
        with mock.patch.object(checks, "run", side_effect=RuntimeError("boom")):
            code, out = helpers.cli(self.root, self.kit, "check", "--quiet")
        self.assertEqual((code, out), (0, "AI-SDLC: the check could not run (boom).\n"))

    def test_not_set_up(self):
        other = helpers.make_repo(Path(self.tmp.name) / "other")
        code, out = helpers.cli(other, self.kit, "check", "--quiet")
        self.assertEqual(out, 'The kit is not set up in this repo. Say "do the onboarding".\n')


if __name__ == "__main__":
    unittest.main()
