#!/usr/bin/env python3
"""`change`: new choices touch only the files they affect; edits are kept."""
import json
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import packs, paths
from test_superpowers import FILES

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
        # the dev instructions, the dev playbook, and the six process skills' files
        removed = 2 + sum(len(files) for files in FILES.values())
        self.assertIn(f"Removed {removed} file(s) no longer needed", out)

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

    def skill_files(self, name):
        d = self.root / ".agents/skills" / f"ai-sdlc-{name}"
        return sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file())

    def test_a_role_skill_can_be_dropped_and_added_back(self):
        self.change("--roles", "po,dev")
        self.assertEqual(self.skill_files("brainstorming"), ["LICENSE", "PROVENANCE.md", "SKILL.md"])
        self.change("--drop-skill", "brainstorming")
        self.assertFalse((self.root / ".agents/skills/ai-sdlc-brainstorming").exists())
        self.assertTrue((self.root / ".agents/skills/ai-sdlc-writing-plans/SKILL.md").is_file())
        self.assertIn("- **Skills left out:** brainstorming",
                      (self.root / paths.USER_REL).read_text(encoding="utf-8"))
        self.change("--add-skill", "brainstorming")
        self.assertTrue((self.root / ".agents/skills/ai-sdlc-brainstorming/SKILL.md").is_file())

    def test_a_process_skill_outside_the_roles_can_be_added(self):
        self.change("--add-skill", "systematic-debugging")
        self.assertEqual(self.skill_files("systematic-debugging"),
                         sorted(FILES["systematic-debugging"]))      # no find-polluter.sh
        self.assertIn("- **Extra skills:** systematic-debugging",
                      (self.root / paths.USER_REL).read_text(encoding="utf-8"))
        self.assertFalse((self.root / ".agents/skills/ai-sdlc-test-driven-development").exists())

    def test_unknown_or_unsupported_skills_are_refused(self):
        code, out = helpers.cli(self.root, self.kit, "change", "--add-skill", "nope")
        self.assertEqual(code, 2)
        self.assertIn("There is no skill nope.", out)
        code, out = helpers.cli(self.root, self.kit, "change", "--add-skill", "git-verbs")
        self.assertEqual(code, 2)
        self.assertIn("cannot be added", out)

    def test_an_unknown_skill_to_drop_is_refused_like_one_to_add(self):
        before = helpers.snapshot(self.root)
        code, out = helpers.cli(self.root, self.kit, "change", "--drop-skill", "nope")
        self.assertEqual(code, 2, out)
        self.assertIn("There is no skill nope.", out)
        code, out = helpers.cli(self.root, self.kit, "change", "--drop-skill", "git-verbs")
        self.assertEqual(code, 2, out)
        self.assertEqual(helpers.snapshot(self.root), before)

    def test_the_ai_sdlc_prefix_is_accepted_on_add_and_drop(self):
        self.change("--add-skill", "ai-sdlc-skill-creator", "--drop-skill", "ai-sdlc-drawio")
        self.assertTrue((self.root / ".agents/skills/ai-sdlc-skill-creator/SKILL.md").is_file())
        self.assertFalse((self.root / ".agents/skills/ai-sdlc-drawio").exists())
        st = json.loads((self.root / paths.STATE_REL).read_text())
        self.assertEqual((st["choices"]["add_skills"], st["choices"]["drop_skills"]),
                         (["skill-creator"], ["drawio"]))
        user = (self.root / paths.USER_REL).read_text(encoding="utf-8")
        self.assertIn("- **Skills left out:** drawio\n", user)

    def test_a_bogus_skill_already_stored_is_cleaned_on_the_next_change(self):
        state_file = self.root / paths.STATE_REL
        st = json.loads(state_file.read_text())
        st["choices"]["drop_skills"] = ["ai-sdlc-drawio", "nosuch"]   # as an older kit stored them
        state_file.write_text(json.dumps(st))
        out = self.change()
        st = json.loads(state_file.read_text())
        self.assertEqual(st["choices"]["drop_skills"], ["drawio"])
        self.assertIn("- Your choices named the skill ai-sdlc-drawio; it is drawio now.", out)
        self.assertIn("- Your choices left out a skill the kit does not have (nosuch); "
                      "that entry is gone.", out)
        self.assertFalse((self.root / ".agents/skills/ai-sdlc-drawio").exists())
        self.assertIn("- **Skills left out:** drawio\n",
                      (self.root / paths.USER_REL).read_text(encoding="utf-8"))

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
        self.assertIn(f"- Kept your edit in {CORE}. The kit's newer copy is next to it as "
                      f"{CORE}.kit-new, for you to compare.", out)
        self.assertIn("Always answer in German", (self.root / (CORE + ".kit-new")).read_text())

    def test_an_edited_file_the_kit_did_not_change_has_nothing_to_compare(self):
        (self.root / PO).write_text("my own po\n")
        out = self.change("--lang", "de")              # the po file does not depend on it
        self.assertIn(f"- Kept your edit in {PO}. The kit's copy has not changed, so there is "
                      "nothing to compare.", out)
        self.assertFalse((self.root / (PO + ".kit-new")).exists())

    def test_change_verbose_lists_every_file(self):
        out = helpers.cli(self.root, self.kit, "change", "--lang", "de", "--verbose")[1]
        self.assertIn(f"- Wrote 2 file(s): {paths.USER_REL}, {CORE}\n", out)
        out = self.change("--lang", "ro")
        self.assertIn("- Wrote 2 file(s): .ai-sdlc/ (1), .github/instructions/ (1)\n", out)
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
