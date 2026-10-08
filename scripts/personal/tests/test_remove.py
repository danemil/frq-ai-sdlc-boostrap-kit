#!/usr/bin/env python3
"""`remove`: the repo ends byte for byte as it was before the kit was copied in."""
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import paths

ARGS = ["setup", "--name", "Ana", "--roles", "po,sm,dev", "--lang", "ro"]
TEAM = {"README.md": "team\n", "AGENTS.md": "# Team\n",
        ".github/instructions/team.instructions.md": "---\napplyTo: 'docs/**'\n---\nTeam.\n"}
CORE = ".github/instructions/ai-sdlc-core.instructions.md"


class TestRemove(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def round_trip(self, root, edit=None):
        """Snapshot, copy the kit in, set up, use it, remove. Returns (before, after, output)."""
        before = helpers.snapshot(root)
        copy = helpers.copy_kit(root / "ai-sdlc-kit")
        kit = root / paths.KIT_REL
        helpers.cli(root, copy, "setup", "--protect-only")
        helpers.cli(root, kit, *ARGS)
        helpers.cli(root, kit, "change", "--lang", "en", "--add-skill", "skill-creator")
        if (root / "AGENTS.md").exists():
            self.assertEqual(helpers.cli(root, kit, "ack", "team-agents-md")[0], 0)
        if edit:
            edit(root)
        code, out = helpers.cli(root, kit, "remove")
        self.assertEqual(code, 0, out)
        return before, helpers.snapshot(root), out

    def test_git_repo_is_restored_byte_for_byte(self):
        root = helpers.make_repo(self.base / "repo", TEAM)
        before, after, out = self.round_trip(root)
        self.assertEqual(after, before)
        self.assertIn("The repo is back to how it was before setup.", out)

    def test_an_exclude_file_without_a_final_newline_is_restored(self):
        root = helpers.make_repo(self.base / "repo", TEAM)
        (root / ".git/info/exclude").write_text("*.log")
        before, after, _ = self.round_trip(root)
        self.assertEqual(after, before)

    def test_a_repo_whose_github_folder_the_kit_created(self):
        root = helpers.make_repo(self.base / "repo", {"README.md": "x\n"})
        before, after, _ = self.round_trip(root)
        self.assertEqual(after, before)
        self.assertFalse((root / ".github").exists())

    def test_a_non_git_folder_is_restored(self):
        root = self.base / "plain"
        root.mkdir()
        (root / "notes.md").write_text("mine\n")
        before, after, _ = self.round_trip(root)
        self.assertEqual(after, before)

    def test_edited_files_are_kept_and_listed(self):
        root = helpers.make_repo(self.base / "repo", TEAM)
        _, _, out = self.round_trip(root, edit=lambda r: (r / CORE).write_text("mine\n"))
        self.assertEqual((root / CORE).read_text(), "mine\n")
        self.assertIn(f"Kept, because you edited them (git now shows them; delete them if you "
                      f"don't need them): {CORE}", out)
        self.assertFalse((root / paths.HOME_REL).exists())

    def test_a_multi_file_skill_is_placed_hidden_and_removed_byte_for_byte(self):
        src = helpers.copy_kit(self.base / "src-kit")
        skill = src / "template/.claude/skills/notes"
        files = {"SKILL.md": "---\nname: notes\ndescription: Use for notes.\n---\n\nNotes.\n",
                 "references/guide.md": "# Guide\n", "assets/starter.html": "<!doctype html>\n"}
        for rel, text in files.items():
            (skill / rel).parent.mkdir(parents=True, exist_ok=True)
            (skill / rel).write_text(text, encoding="utf-8")
        root = helpers.make_repo(self.base / "repo", TEAM)
        before = helpers.snapshot(root)
        helpers.cli(root, helpers.copy_kit(root / "ai-sdlc-kit", src=src), *ARGS)
        kit = root / paths.KIT_REL
        self.assertEqual(helpers.cli(root, kit, "change", "--add-skill", "notes")[0], 0)
        for rel in files:
            self.assertTrue((root / ".agents/skills/ai-sdlc-notes" / rel).is_file(), rel)
        self.assertEqual(helpers.git(root, "status", "--porcelain").stdout, "")
        self.assertEqual(helpers.cli(root, kit, "ack", "team-agents-md")[0], 0)
        code, out = helpers.cli(root, kit, "remove")
        self.assertEqual(code, 0, out)
        self.assertEqual(helpers.snapshot(root), before)

    def test_personal_notes_and_skills_are_kept_and_listed(self):
        def write_personal(r):
            (r / paths.PERSONAL_NOTES_REL).write_text("---\napplyTo: '**'\n---\nMine.\n")
            skill = r / ".agents/skills/ai-sdlc-personal-release/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("mine\n")
        root = helpers.make_repo(self.base / "repo", TEAM)
        _, after, out = self.round_trip(root, edit=write_personal)
        self.assertIn("Kept your personal notes and skills (git now shows them; delete them if "
                      f"you don't need them): {paths.PERSONAL_NOTES_REL}, "
                      ".agents/skills/ai-sdlc-personal-release/SKILL.md", out)
        self.assertNotIn("The repo is back to how it was", out)
        self.assertEqual((root / paths.PERSONAL_NOTES_REL).read_text(), "---\napplyTo: '**'\n---\nMine.\n")
        mine = {".agents/skills/ai-sdlc-personal-release/SKILL.md", paths.PERSONAL_NOTES_REL}
        status = helpers.git(root, "status", "--porcelain", "-uall").stdout
        self.assertEqual(sorted(line[3:] for line in status.splitlines()), sorted(mine))

    def test_remove_before_setup_is_a_plain_error(self):
        root = helpers.make_repo(self.base / "repo")
        code, out = helpers.cli(root, helpers.KIT, "remove")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
