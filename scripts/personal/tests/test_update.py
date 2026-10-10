#!/usr/bin/env python3
"""`update`, run from a newer kit copy: replace the kit, refresh unedited files, keep edits."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers
from personal import paths

ARGS = ["setup", "--name", "Ana", "--roles", "po,dev", "--lang", "de"]
CORE = ".github/instructions/ai-sdlc-core.instructions.md"
PO = ".github/instructions/ai-sdlc-po.instructions.md"


class TestUpdate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = helpers.make_repo(Path(self.tmp.name).resolve() / "repo", {"README.md": "x\n"})
        self.kit = self.root / paths.KIT_REL
        helpers.cli(self.root, helpers.copy_kit(self.root / "kit-copy"), *ARGS)
        self.newer = helpers.copy_kit(self.root / "kit-newer")
        (self.newer / "VERSION").write_text("9.9.9\n")
        for pid in ("core", "po"):
            with open(self.newer / f"roles/{pid}/instructions.md", "a", encoding="utf-8") as fh:
                fh.write("\nNewer kit line.\n")

    def tearDown(self):
        self.tmp.cleanup()

    def update(self, kit=None):
        return helpers.cli(self.root, kit or self.newer, "update")

    def test_the_kit_folder_is_replaced_and_the_version_recorded(self):
        code, out = self.update()
        self.assertEqual(code, 0, out)
        self.assertIn("Updated to AI-SDLC 9.9.9", out)
        self.assertEqual(paths.kit_version(self.kit), "9.9.9")
        self.assertFalse(self.newer.exists())
        st = json.loads((self.root / paths.STATE_REL).read_text())
        self.assertEqual(st["kit_version"], "9.9.9")
        self.assertEqual(st["choices"]["roles"], ["po", "dev"])

    def test_the_summary_says_where_the_copy_went_and_what_it_replaced(self):
        old = paths.kit_version(self.kit)
        code, out = self.update()
        self.assertEqual(code, 0, out)
        self.assertIn(f"- Moved kit-newer into .ai-sdlc/kit (replaced {old}).", out)

    def test_unedited_files_are_refreshed_and_edited_ones_kept(self):
        (self.root / PO).write_text("my po notes\n")
        code, out = self.update()
        self.assertIn(f"- Kept your edit in {PO}. The kit's newer copy is next to it as "
                      f"{PO}.kit-new, for you to compare.", out)
        self.assertIn("Newer kit line.", (self.root / CORE).read_text())
        self.assertEqual((self.root / PO).read_text(), "my po notes\n")
        self.assertIn("Newer kit line.", (self.root / (PO + ".kit-new")).read_text())
        self.assertEqual(helpers.git(self.root, "status", "--porcelain").stdout, "")

    def test_an_update_cleans_a_bogus_skill_entry(self):
        state_file = self.root / paths.STATE_REL
        st = json.loads(state_file.read_text())
        st["choices"]["drop_skills"] = ["ai-sdlc-drawio"]
        st["choices"]["add_skills"] = ["ai-sdlc-skill-creator"]
        state_file.write_text(json.dumps(st))
        code, out = self.update()
        self.assertEqual(code, 0, out)
        st = json.loads(state_file.read_text())
        self.assertEqual((st["choices"]["add_skills"], st["choices"]["drop_skills"]),
                         (["skill-creator"], ["drawio"]))
        self.assertTrue((self.root / ".agents/skills/ai-sdlc-skill-creator/SKILL.md").is_file())
        self.assertFalse((self.root / ".agents/skills/ai-sdlc-drawio").exists())

    def test_a_skill_the_newer_kit_drops_is_removed(self):
        role = self.newer / "roles/dev/role.json"
        data = json.loads(role.read_text())
        data["skills"] = []
        role.write_text(json.dumps(data))
        self.update()
        self.assertFalse((self.root / ".agents/skills/ai-sdlc-playbook-dev").exists())

    def test_an_older_copy_is_refused(self):
        (self.newer / "VERSION").write_text("0.0.1\n")
        code, out = self.update()
        self.assertEqual(code, 2)
        self.assertIn("This copy is older (0.0.1)", out)
        self.assertTrue(self.newer.exists())

    def test_update_from_the_installed_kit_refreshes_in_place(self):
        (self.root / CORE).unlink()
        code, out = self.update(self.kit)
        self.assertEqual(code, 0, out)
        self.assertTrue((self.root / CORE).is_file())

    def test_after_update_check_is_clean(self):
        code, out = self.update()
        self.assertIn("Check: all good.", out)

    # --- an incomplete copy, and recovering a half-updated setup -------------------

    def check(self):
        return helpers.cli(self.root, self.kit, "check")

    def assert_untouched(self, before, status, code, out):
        self.assertEqual(code, 2, out)
        self.assertNotIn("Traceback", out)
        self.assertIn("Nothing was changed.", out)
        self.assertEqual(helpers.snapshot(self.root), before)
        self.assertEqual(helpers.git(self.root, "status", "--porcelain").stdout, status)

    def test_an_incomplete_copy_is_refused_before_anything_moves(self):
        (self.newer / "template/.claude/skills/connectors/SKILL.md").unlink()
        before = helpers.snapshot(self.root)
        status = helpers.git(self.root, "status", "--porcelain").stdout
        code, out = self.update()
        self.assert_untouched(before, status, code, out)
        self.assertIn("This kit copy is incomplete (missing "
                      "template/.claude/skills/connectors/SKILL.md)", out)
        self.assertIn("Copy the whole kit folder again (without .git) and retry.", out)
        self.assertTrue(self.newer.exists())
        self.assertEqual(paths.kit_version(self.kit), paths.kit_version(helpers.KIT))
        code, out = self.check()
        self.assertNotIn("stale-kit", out)

    def test_a_copy_missing_a_role_or_a_linked_file_is_refused(self):
        for rel in ("roles/po/instructions.md", "ONBOARDING.md"):
            with self.subTest(rel=rel):
                p = self.newer / rel
                text = p.read_bytes()
                p.unlink()
                before = helpers.snapshot(self.root)
                code, out = self.update()
                self.assert_untouched(before, helpers.git(self.root, "status", "--porcelain").stdout,
                                      code, out)
                self.assertIn(f"missing {rel}", out)
                p.write_bytes(text)

    def test_the_real_cli_on_an_incomplete_copy_prints_no_traceback(self):
        (self.newer / "template/.claude/skills/connectors/SKILL.md").unlink()
        r = subprocess.run([sys.executable, str(self.newer / "setup.py"), "update"],
                           cwd=self.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertIn("This kit copy is incomplete", r.stdout)

    def test_an_unexpected_error_is_a_plain_message_and_update_finishes_the_job(self):
        with mock.patch("personal.place.apply", side_effect=OSError("disk full")):
            code, out = self.update()
        self.assertEqual(code, 4, out)
        self.assertNotIn("Traceback", out)
        self.assertIn("disk full", out)
        code, out = self.check()
        self.assertIn("[stale-kit]", out)                 # the half-updated state
        code, out = self.update(self.kit)                 # the stale-kit advice
        self.assertEqual(code, 0, out)
        self.assertIn("Updated to AI-SDLC 9.9.9", out)
        self.assertIn("Newer kit line.", (self.root / CORE).read_text())
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertEqual(helpers.git(self.root, "status", "--porcelain").stdout, "")

    def test_an_incomplete_kit_folder_left_by_an_older_kit_is_recovered(self):
        # what 0.5.0 left behind: the incomplete copy moved in, state.json still old
        (self.kit / "VERSION").write_text("9.9.9\n")
        (self.kit / "template/.claude/skills/connectors/SKILL.md").unlink()
        before = helpers.snapshot(self.root)
        status = helpers.git(self.root, "status", "--porcelain").stdout
        code, out = self.update(self.kit)
        self.assert_untouched(before, status, code, out)
        self.assertIn("The kit folder .ai-sdlc/kit is incomplete (missing "
                      "template/.claude/skills/connectors/SKILL.md)", out)
        code, out = self.update()                         # a whole copy fixes it
        self.assertEqual(code, 0, out)
        self.assertIn("Check: all good.", out)
        self.assertTrue((self.kit / "template/.claude/skills/connectors/SKILL.md").is_file())

    def test_a_skill_the_newer_kit_no_longer_has_is_dropped_not_a_crash(self):
        code, out = helpers.cli(self.root, self.kit, "change", "--add-skill", "skill-creator")
        self.assertEqual(code, 0, out)
        shutil.rmtree(self.newer / "template/.claude/skills/skill-creator")
        code, out = self.update()
        self.assertEqual(code, 0, out)
        self.assertIn("The newer kit has no skill-creator skill any more; it was dropped.", out)
        self.assertFalse((self.root / ".agents/skills/ai-sdlc-skill-creator").exists())
        st = json.loads((self.root / paths.STATE_REL).read_text())
        self.assertEqual(st["choices"]["add_skills"], [])

    def test_a_skill_a_newer_kit_adds_to_a_role_arrives_and_a_left_out_one_stays_out(self):
        root = helpers.make_repo(Path(self.tmp.name).resolve() / "repo-0.6", {"README.md": "x\n"})
        old = helpers.copy_kit(root / "kit-old")
        role = old / "roles/dev/role.json"
        data = json.loads(role.read_text())
        data["skills"] = ["playbook-dev"]                  # a kit before the process skills
        role.write_text(json.dumps(data))
        code, out = helpers.cli(root, old, "setup", "--name", "Ana", "--roles", "dev", "--lang", "en")
        self.assertEqual(code, 0, out)
        skills = root / ".agents/skills"
        self.assertFalse((skills / "ai-sdlc-writing-plans").exists())
        code, out = helpers.cli(root, root / paths.KIT_REL, "change", "--drop-skill", "brainstorming")
        self.assertEqual(code, 0, out)
        newer = helpers.copy_kit(root / "kit-newer")
        (newer / "VERSION").write_text("9.9.9\n")
        code, out = helpers.cli(root, newer, "update")
        self.assertEqual(code, 0, out)
        self.assertTrue((skills / "ai-sdlc-writing-plans/SKILL.md").is_file())
        self.assertFalse((skills / "ai-sdlc-brainstorming").exists())
        self.assertEqual(helpers.git(root, "status", "--porcelain").stdout, "")


    def test_an_update_from_0_8_0_removes_the_placed_brand_binaries(self):
        """0.8.0 placed the brand skill's binaries; 0.9.0 keeps them in .ai-sdlc/kit only
        (.kit-only). An update removes the unedited ones and keeps an edited one."""
        root = helpers.make_repo(Path(self.tmp.name).resolve() / "repo-0.8", {"README.md": "x\n"})
        old = helpers.copy_kit(root / "kit-old")
        (old / "template/.claude/skills/frq-brandbook/.kit-only").unlink()   # places binaries, like 0.8.0
        code, out = helpers.cli(root, old, "setup", "--name", "Ana", "--roles", "po", "--lang", "en")
        self.assertEqual(code, 0, out)
        brand = root / ".agents/skills/ai-sdlc-frq-brandbook"
        slim = brand / "assets/templates/frq-template-slim-core.pptx"
        edited = brand / "assets/logo/logo-frequentis-wordmark-blue.png"
        self.assertTrue(slim.is_file())
        edited.write_bytes(edited.read_bytes() + b"\x00my edit")
        newer = helpers.copy_kit(root / "kit-newer")
        (newer / "VERSION").write_text("9.9.9\n")
        code, out = helpers.cli(root, newer, "update")
        self.assertEqual(code, 0, out)
        self.assertFalse(slim.exists())
        self.assertFalse((brand / "assets/layouts").exists())
        self.assertTrue((brand / "SKILL.md").is_file())
        self.assertTrue((brand / "scripts/check_brand.py").is_file())
        self.assertTrue((brand / "assets/logo/logo-frequentis-wordmark-blue.svg").is_file())
        self.assertTrue((root / paths.KIT_REL / "template/.claude/skills/frq-brandbook/assets/templates/"
                         "frq-template-slim-core.pptx").is_file())
        rel = edited.relative_to(root).as_posix()
        self.assertIn(f"- Kept your edit in {rel}.", out)
        self.assertTrue(edited.is_file())
        self.assertIn("Removed", out)
        # The kept edit is a notice, not an unknown file: check exits 0 (re-test round 2, S6).
        self.assertNotIn(f"unknown:{rel}", out)
        self.assertIn(f"[kept-edit:{rel}]", out)
        code, out = helpers.cli(root, root / paths.KIT_REL, "check")
        self.assertEqual(code, 0, out)
        self.assertIn(f"[kept-edit:{rel}]", out)
        self.assertIn("delete it if you don't need it", out)


if __name__ == "__main__":
    unittest.main()
