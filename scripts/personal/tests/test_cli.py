#!/usr/bin/env python3
"""setup.py: the CLI surface, and imports that hold wherever the kit folder sits."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import paths, reuse

SETUP = helpers.KIT / "setup.py"
COMMANDS = ["setup", "change", "update", "check", "ack", "remove"]


def run(setup_py, *args, cwd=None):
    return subprocess.run([sys.executable, str(setup_py), *args], cwd=cwd,
                          capture_output=True, text=True)


class TestCli(unittest.TestCase):
    def test_help_lists_the_six_commands(self):
        r = run(SETUP, "--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        for name in COMMANDS:
            self.assertIn(name, r.stdout)

    def test_unknown_command_is_a_usage_error(self):
        r = run(SETUP, "install")
        self.assertEqual(r.returncode, 2)
        self.assertIn("invalid choice", r.stderr)

    def test_change_flags_parse(self):
        sys.path.insert(0, str(helpers.KIT))
        import setup  # the kit-root setup.py
        args = setup.parser().parse_args(
            ["change", "--add-skill", "a", "--add-skill", "b", "--drop-skill", "c",
             "--git-comfort", "guided", "--rituals", "default"])
        self.assertEqual((args.add_skill, args.drop_skill), (["a", "b"], ["c"]))
        self.assertEqual((args.git_comfort, args.rituals), ("guided", "default"))

    def test_runs_from_a_moved_copy_with_another_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            kit = helpers.copy_kit(Path(tmp) / "repo/.ai-sdlc/kit")
            r = run(kit / "setup.py", "--help", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(list(kit.rglob("__pycache__")), "setup.py wrote bytecode into the kit")

    def test_reuse_is_the_phase_0_code(self):
        self.assertEqual(reuse.file_state.__module__, "manifest")
        self.assertEqual(reuse.split_frontmatter("---\na: 1\n---\nbody\n"), ("a: 1", "body\n"))
        self.assertEqual(reuse.rule_paths('paths:\n  - "docs/**"', "r.md"), ["docs/**"])


class TestPaths(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_outside_git_the_folder_is_the_root(self):
        self.assertEqual(paths.repo_root(self.root), (self.root.resolve(), False))

    def test_inside_git_the_top_level_is_the_root(self):
        helpers.make_repo(self.root)
        (self.root / "a/b").mkdir(parents=True)
        self.assertEqual(paths.repo_root(self.root / "a/b"), (self.root.resolve(), True))

    def test_tracked_lists_only_tracked_paths(self):
        helpers.make_repo(self.root, {"AGENTS.md": "team\n"})
        self.assertEqual(paths.tracked(self.root, ["AGENTS.md", "new.md"]), {"AGENTS.md"})

    def test_write_atomic_replaces_and_leaves_no_temp_file(self):
        target = self.root / "d/state.json"
        paths.write_atomic(target, "one")
        paths.write_atomic(target, "two")
        self.assertEqual(target.read_text(), "two")
        self.assertEqual([p.name for p in target.parent.iterdir()], ["state.json"])

    def test_read_text_round_trips_odd_bytes(self):
        target = self.root / "x"
        target.write_bytes(b"caf\xe9\n")
        paths.write_atomic(target, paths.read_text(target))
        self.assertEqual(target.read_bytes(), b"caf\xe9\n")


if __name__ == "__main__":
    unittest.main()
