#!/usr/bin/env python3
"""Team-file warnings: stable ids, precise text, acknowledged by fingerprint."""
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import conflicts, paths, state

ARGS = ["setup", "--name", "Ana", "--roles", "po,sm", "--lang", "en"]
TEAM = {
    "AGENTS.md": "# Team brief\n",
    ".github/copilot-instructions.md": "Use British English.\n",
    ".github/instructions/docs.instructions.md": "---\napplyTo: 'docs/**'\n---\nTwo reviewers.\n",
    ".github/instructions/manual.instructions.md": "No applyTo: only used when attached.\n",
    ".claude/skills/playbook-product/SKILL.md": "---\nname: playbook-product\n---\nTeam's.\n",
    ".github/skills/ai-sdlc-playbook-sm/SKILL.md": "---\nname: ai-sdlc-playbook-sm\n---\nX.\n",
    ".github/skills/release-notes/SKILL.md": "---\nname: release-notes\n---\nNo clash.\n",
}


class TestOverlaps(unittest.TestCase):
    def test_globs(self):
        self.assertTrue(conflicts.overlaps("docs/**", "**"))
        self.assertTrue(conflicts.overlaps("src/*.ts", "src/app/**"))
        self.assertFalse(conflicts.overlaps("docs/**", "src/**"))


class TestWarnings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = helpers.make_repo(Path(self.tmp.name).resolve() / "repo", TEAM)
        self.kit = self.root / paths.KIT_REL
        code, self.out = helpers.cli(self.root, helpers.copy_kit(self.root / "kit-copy"), *ARGS)
        self.assertEqual(code, 0, self.out)

    def tearDown(self):
        self.tmp.cleanup()

    def warnings(self):
        return {wid: text for wid, text, _ in conflicts.warnings(self.root, state.load(self.root))}

    def test_each_kind_of_overlap_has_a_stable_id(self):
        self.assertEqual(sorted(self.warnings()), [
            "skill-clash:.claude/skills/playbook-product",
            "skill-clash:.github/skills/ai-sdlc-playbook-sm",
            "team-agents-md", "team-copilot-instructions",
            "team-instructions:.github/instructions/docs.instructions.md"])

    def test_the_text_is_precise(self):
        w = self.warnings()
        self.assertEqual(w["team-instructions:.github/instructions/docs.instructions.md"],
                         "The team's .github/instructions/docs.instructions.md also applies to "
                         "docs/**, where the kit's instructions apply too.")
        self.assertIn("the kit adds ai-sdlc-playbook-product",
                      w["skill-clash:.claude/skills/playbook-product"])

    def test_setup_lists_them_and_changes_no_team_file(self):
        self.assertIn("- [team-agents-md] The team has its own AGENTS.md.", self.out)
        self.assertEqual(helpers.git(self.root, "status", "--porcelain").stdout, "")
        self.assertEqual(helpers.git(self.root, "diff", "HEAD", "--stat").stdout, "")

    def test_ack_silences_a_warning_until_the_team_file_changes(self):
        code, out = helpers.cli(self.root, self.kit, "ack", "team-agents-md")
        self.assertEqual(code, 0, out)
        self.assertNotIn("[team-agents-md]", helpers.cli(self.root, self.kit, "check")[1])
        (self.root / "AGENTS.md").write_text("# Team brief, edited\n")
        self.assertIn("[team-agents-md]", helpers.cli(self.root, self.kit, "check")[1])

    def test_ack_needs_a_current_id(self):
        code, out = helpers.cli(self.root, self.kit, "ack", "team-nope")
        self.assertEqual(code, 2)
        self.assertIn("No current warning has the id team-nope.", out)


class TestQuietRepo(unittest.TestCase):
    def test_no_team_files_no_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = helpers.make_repo(Path(tmp).resolve() / "repo", {"README.md": "x\n"})
            helpers.cli(root, helpers.copy_kit(root / "kit-copy"), *ARGS)
            self.assertEqual(conflicts.warnings(root, state.load(root)), [])


if __name__ == "__main__":
    unittest.main()
