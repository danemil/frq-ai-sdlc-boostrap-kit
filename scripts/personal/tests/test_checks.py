#!/usr/bin/env python3
"""`check`: missing, unknown and unhidden files, kit copies, a stale kit, the one-liner."""
import json
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

    def test_an_edit_kept_after_a_change_is_a_notice_not_unknown(self):
        """A file the person edited and no longer needs stays (place.apply keeps it); check
        names it as a notice, exit 0, until they delete it (re-test round 2, S6)."""
        sm = ".github/instructions/ai-sdlc-sm.instructions.md"
        (self.root / sm).write_text("my sm notes\n")
        code, out = helpers.cli(self.root, self.kit, "change", "--roles", "po")
        self.assertEqual(code, 0, out)
        self.assertTrue((self.root / sm).is_file())
        self.assertEqual(self.ids(), [f"kept-edit:{sm}"])
        self.assertTrue(checks.is_notice(f"kept-edit:{sm}"))
        code, out = helpers.cli(self.root, self.kit, "check")
        self.assertEqual(code, 0, out)
        self.assertIn(f"[kept-edit:{sm}]", out)
        self.assertIn("delete it if you don't need it", out)
        self.assertNotIn("unknown:", out)
        (self.root / sm).unlink()
        self.assertEqual(self.ids(), [])
        code, out = helpers.cli(self.root, self.kit, "change")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads((self.root / paths.STATE_REL).read_text())["kept_edits"], {})

    def test_a_kept_edit_the_roles_need_again_is_the_kits_file_again(self):
        sm = ".github/instructions/ai-sdlc-sm.instructions.md"
        (self.root / sm).write_text("my sm notes\n")
        helpers.cli(self.root, self.kit, "change", "--roles", "po")
        code, out = helpers.cli(self.root, self.kit, "change", "--roles", "po,sm")
        self.assertEqual(code, 0, out)
        self.assertEqual((self.root / sm).read_text(), "my sm notes\n")
        self.assertIn(f"- Kept your edit in {sm}.", out)
        self.assertEqual(self.ids(), [])
        self.assertIn(sm, json.loads((self.root / paths.STATE_REL).read_text())["files"])

    def test_python_bytecode_in_a_kit_skill_is_not_unknown(self):
        """Running a skill's script (the brand checker) can leave __pycache__/*.pyc behind."""
        skill = self.root / ".agents/skills/ai-sdlc-frq-brandbook/scripts"
        cache = skill / "__pycache__"
        cache.mkdir(parents=True, exist_ok=True)
        (cache / "check_brand.cpython-39.pyc").write_bytes(b"\x00")
        (skill / "stray.pyc").write_bytes(b"\x00")
        self.assertEqual(self.ids(), [])
        code, out = helpers.cli(self.root, self.kit, "check", "--quiet")
        self.assertEqual(code, 0, out)

    def test_personal_notes_and_skills_are_not_unknown_and_stay_hidden(self):
        (self.root / paths.PERSONAL_NOTES_REL).write_text("---\napplyTo: '**'\n---\nMine.\n")
        mine = self.root / ".agents/skills/ai-sdlc-personal-release/SKILL.md"
        mine.parent.mkdir(parents=True)
        mine.write_text("x\n")
        lookalike = self.root / ".agents/skills/ai-sdlc-personalx/SKILL.md"
        lookalike.parent.mkdir(parents=True)
        lookalike.write_text("x\n")
        self.assertEqual(self.ids(), ["unknown:.agents/skills/ai-sdlc-personalx/SKILL.md"])
        self.assertEqual(helpers.git(self.root, "status", "--porcelain").stdout, "")

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

    def test_a_same_version_copy_offers_the_update_or_deletion(self):
        helpers.copy_kit(self.root / "downloads/ai-sdlc-kit")
        version = paths.kit_version(self.kit)
        found = dict(checks.run(self.root)[1])
        self.assertEqual(found["kit-copy:downloads/ai-sdlc-kit"],
                         f"Another copy of the kit (same version {version}) is in downloads/ai-sdlc-kit. "
                         'If you copied it in to update, say "update the kit"; otherwise delete it.')
        self.assertNotIn("Delete it.", found["kit-copy:downloads/ai-sdlc-kit"])

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

    def test_notices_alone_exit_0_and_problems_exit_1(self):
        """The split: team-…, skill-clash:… and kit-copy:… are notices (exit 0); anything
        else (missing, unknown, unexcluded, stale-kit, not-set-up) is a problem (exit 1)."""
        for fid in ("team-agents-md", "team-copilot-instructions", "team-instructions:a.md",
                    "skill-clash:.claude/skills/x", "kit-copy:downloads/kit"):
            self.assertTrue(checks.is_notice(fid), fid)
        for fid in (f"missing:{CORE}", f"unknown:{CORE}", f"unexcluded:{CORE}", "stale-kit",
                    "not-set-up"):
            self.assertFalse(checks.is_notice(fid), fid)
        (self.root / "AGENTS.md").write_text("# Team\n")
        newer = helpers.copy_kit(self.root / "downloads/ai-sdlc-kit")
        (newer / "VERSION").write_text("9.9.9\n")
        code, out = helpers.cli(self.root, self.kit, "check")
        self.assertEqual(code, 0, out)
        self.assertIn("Check: nothing to fix; 2 notice(s) to read:", out)
        self.assertIn("- [team-agents-md]", out)
        self.assertIn("- [kit-copy:downloads/ai-sdlc-kit]", out)
        (self.root / CORE).unlink()
        code, out = helpers.cli(self.root, self.kit, "check")
        self.assertEqual(code, 1, out)
        self.assertIn("Check: 3 to look at:", out)

    def test_check_names_the_connectors_for_the_roles(self):
        code, out = helpers.cli(self.root, self.kit, "check")
        self.assertEqual(code, 0, out)
        self.assertIn("- Connectors for your roles: jira, confluence, jama (say 'connect jira')",
                      out)

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
