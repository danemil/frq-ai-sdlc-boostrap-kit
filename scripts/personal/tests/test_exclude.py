#!/usr/bin/env python3
"""The .git/info/exclude block: idempotent, byte-exact to remove, worktree-aware."""
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import exclude

KIT_PATHS = [".ai-sdlc/kit/setup.py", ".ai-sdlc/USER.md",
             ".github/instructions/ai-sdlc-core.instructions.md",
             ".github/instructions/ai-sdlc-po.instructions.md.kit-new",
             ".agents/skills/ai-sdlc-playbook-dev/SKILL.md"]
TEAM_PATHS = [".github/instructions/team.instructions.md", ".agents/skills/team/SKILL.md",
              "AGENTS.md"]


class TestText(unittest.TestCase):
    def test_absent_file_is_created_and_strip_says_delete(self):
        text = exclude.add(None)
        self.assertIn("/.ai-sdlc/", text)
        self.assertIsNone(exclude.strip(text))

    def test_existing_lines_survive_and_strip_restores_them(self):
        original = "# git ls-files --others --exclude-from=.git/info/exclude\n*.log\n"
        text = exclude.add(original)
        self.assertTrue(text.startswith(original))
        self.assertEqual(exclude.strip(text), original)

    def test_unterminated_last_line_is_restored(self):
        self.assertEqual(exclude.strip(exclude.add("*.log")), "*.log")

    def test_empty_file_stays_an_empty_file(self):
        self.assertEqual(exclude.strip(exclude.add("")), "")

    def test_add_is_idempotent(self):
        once = exclude.add("*.log")
        self.assertEqual(exclude.add(once), once)

    def test_lines_added_after_the_block_survive(self):
        text = exclude.add(None) + "mine/\n"
        self.assertEqual(exclude.strip(text), "mine/\n")


class TestRepo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"

    def tearDown(self):
        self.tmp.cleanup()

    def ignored(self, cwd, rels):
        out = helpers.git(cwd, "check-ignore", "--", *rels).stdout
        return set(out.split())

    def test_protect_hides_kit_paths_and_nothing_else(self):
        helpers.make_repo(self.root)
        self.assertTrue(exclude.protect(self.root))
        self.assertEqual(self.ignored(self.root, KIT_PATHS + TEAM_PATHS), set(KIT_PATHS))

    def test_unprotect_restores_the_file_byte_for_byte(self):
        helpers.make_repo(self.root)
        path = self.root / ".git/info/exclude"
        before = path.read_bytes()
        exclude.protect(self.root)
        exclude.protect(self.root)
        exclude.unprotect(self.root)
        self.assertEqual(path.read_bytes(), before)

    def test_a_missing_exclude_file_is_removed_again(self):
        helpers.make_repo(self.root)
        path = self.root / ".git/info/exclude"
        path.unlink()
        exclude.protect(self.root)
        self.assertTrue(path.is_file())
        exclude.unprotect(self.root)
        self.assertFalse(path.exists())

    def test_worktree_uses_the_shared_exclude_file(self):
        helpers.make_repo(self.root)
        wt = Path(self.tmp.name) / "wt"
        helpers.git(self.root, "worktree", "add", "-q", str(wt))
        exclude.protect(wt)
        self.assertIn(exclude.BEGIN, (self.root / ".git/info/exclude").read_text())
        self.assertEqual(self.ignored(wt, [".ai-sdlc/USER.md"]), {".ai-sdlc/USER.md"})

    def test_non_git_folder_is_not_protected_and_untouched(self):
        self.root.mkdir()
        self.assertFalse(exclude.protect(self.root))
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
