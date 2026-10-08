#!/usr/bin/env python3
"""`change`: new choices touch only the files they affect; edits are kept."""
import json
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import packs, paths

ARGS = ["setup", "--name", "Ana", "--roles", "po", "--lang", "en"]
CORE = ".github/instructions/ai-sdlc-core.instructions.md"
PO = ".github/instructions/ai-sdlc-po.instructions.md"
DEV = ".github/instructions/ai-sdlc-dev.instructions.md"


class TestChange(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = helpers.make_repo(Path(self.tmp.name).resolve() / "repo", {"README.md": "x\n"})
        self.kit = self.root / paths.KIT_REL
        helpers.cli(self.root, helpers.copy_kit(self.root / "kit-copy"), *ARGS)

    def tearDown(self):
        self.tmp.cleanup()

    def change(self, *argv):
        code, out = helpers.cli(self.root, self.kit, "change", *argv)
        self.assertEqual(code, 0, out)
        return out

    def test_language_rewrites_only_the_core_and_user_files(self):
        before = helpers.snapshot(self.root)
        self.change("--lang", "ro")
        after = helpers.snapshot(self.root)
        changed = sorted(k for k in after if after[k] != before.get(k))
        self.assertEqual(changed, sorted([paths.STATE_REL, paths.USER_REL, CORE]))
        self.assertIn("Always answer in Romanian (română)", (self.root / CORE).read_text())

    def test_adding_a_role_adds_its_files_and_dropping_removes_them(self):
        self.change("--roles", "po,dev")
        self.assertTrue((self.root / DEV).is_file())
        self.assertTrue((self.root / ".agents/skills/ai-sdlc-playbook-dev/SKILL.md").is_file())
        out = self.change("--roles", "po")
        self.assertFalse((self.root / DEV).exists())
        self.assertFalse((self.root / ".agents/skills/ai-sdlc-playbook-dev").exists())
        self.assertIn("Removed 2 file(s) no longer needed", out)

    def test_skills_can_be_added_and_dropped(self):
        self.change("--add-skill", "skill-creator", "--drop-skill", "playbook-product")
        skills = sorted(p.name for p in (self.root / ".agents/skills").iterdir())
        core = [f"ai-sdlc-{s}" for s in packs.load(self.kit)["core"]["skills"]]
        self.assertEqual(skills, sorted(core + ["ai-sdlc-skill-creator"]))

    def test_a_core_skill_can_be_dropped_and_added_back(self):
        self.change("--drop-skill", "drawio")
        self.assertFalse((self.root / ".agents/skills/ai-sdlc-drawio").exists())
        self.assertTrue((self.root / ".agents/skills/ai-sdlc-visual-issue/SKILL.md").is_file())
        self.change("--add-skill", "drawio")
        self.assertTrue((self.root / ".agents/skills/ai-sdlc-drawio/references/xml-reference.md")
                        .is_file())

    def test_setup_places_the_likec4_skill_and_it_can_be_dropped(self):
        skill = self.root / ".agents/skills/ai-sdlc-likec4-dsl"
        self.assertTrue((skill / "SKILL.md").is_file())
        self.assertTrue((skill / "references/cli.md").is_file())
        self.assertTrue((skill / "LICENSE").is_file())
        self.assertIn("docs/architecture/", (skill / "SKILL.md").read_text(encoding="utf-8"))
        self.change("--drop-skill", "likec4-dsl")
        self.assertFalse(skill.exists())
        self.assertTrue((self.root / ".agents/skills/ai-sdlc-drawio/SKILL.md").is_file())

    def test_unknown_or_unsupported_skills_are_refused(self):
        code, out = helpers.cli(self.root, self.kit, "change", "--add-skill", "nope")
        self.assertEqual(code, 2)
        self.assertIn("There is no skill nope.", out)
        code, out = helpers.cli(self.root, self.kit, "change", "--add-skill", "git-verbs")
        self.assertEqual(code, 2)
        self.assertIn("cannot be added", out)

    def test_git_comfort_override_and_back_to_the_default(self):
        self.change("--git-comfort", "git-native")
        self.assertIn("They use git themselves.", (self.root / CORE).read_text())
        self.change("--git-comfort", "default")
        self.assertIn("Do git for them in plain words", (self.root / CORE).read_text())
        st = json.loads((self.root / paths.STATE_REL).read_text())
        self.assertIsNone(st["choices"]["git_comfort"])

    def test_an_edited_file_is_kept(self):
        (self.root / CORE).write_text("my own core\n")
        out = self.change("--lang", "de")
        self.assertEqual((self.root / CORE).read_text(), "my own core\n")
        self.assertIn(f"Kept your edit in {CORE}", out)
        self.assertIn("Always answer in German", (self.root / (CORE + ".kit-new")).read_text())
        self.assertEqual(helpers.git(self.root, "status", "--porcelain").stdout, "")

    def test_change_with_no_options_repairs_missing_files(self):
        (self.root / PO).unlink()
        out = self.change()
        self.assertTrue((self.root / PO).is_file())
        self.assertIn("Check: all good.", out)

    def test_change_before_setup_is_a_plain_error(self):
        other = helpers.make_repo(Path(self.tmp.name) / "other")
        code, out = helpers.cli(other, self.kit, "change", "--lang", "de")
        self.assertEqual((code, out), (2, 'The kit is not set up in this repo yet. Say "do the onboarding".\n'))


if __name__ == "__main__":
    unittest.main()
