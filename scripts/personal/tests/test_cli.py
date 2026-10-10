#!/usr/bin/env python3
"""setup.py: the CLI surface, and imports that hold wherever the kit folder sits."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers
from personal import paths, reuse

SETUP = helpers.KIT / "setup.py"
COMMANDS = ["setup", "change", "update", "check", "recommend", "ack", "remove"]


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

    def test_recommend_flags_parse(self):
        sys.path.insert(0, str(helpers.KIT))
        import setup  # the kit-root setup.py
        args = setup.parser().parse_args(["recommend", "--all", "--json"])
        self.assertEqual((args.all, args.json, args.decline), (True, True, None))
        args = setup.parser().parse_args(["recommend", "--decline", "add:javafx,add:java-junit"])
        self.assertEqual(args.decline, "add:javafx,add:java-junit")

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

    def fake_git_refusing(self):
        """A `git` first on PATH that refuses every repo, as git does for a folder another
        user owns ("detected dubious ownership")."""
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "git"
        fake.write_text("#!/bin/sh\n"
                        "echo \"fatal: detected dubious ownership in repository at '$PWD'\" >&2\n"
                        "exit 128\n")
        fake.chmod(0o755)
        return mock.patch.dict(os.environ, {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"})

    def test_a_repo_git_refuses_is_a_plain_error_with_the_fix(self):
        helpers.make_repo(self.root / "repo")
        (self.root / "repo/a").mkdir()
        with self.fake_git_refusing():
            with self.assertRaises(paths.SetupError) as cm:
                paths.repo_root(self.root / "repo/a")
        text = str(cm.exception)
        self.assertIn("detected dubious ownership", text)
        self.assertIn("belongs to another user", text)
        self.assertIn("ask IT", text)
        self.assertIn(f"git config --global --add safe.directory {(self.root / 'repo').resolve()}",
                      text)
        self.assertIn("Nothing was changed.", text)

    def test_setup_stops_in_a_repo_git_refuses_and_changes_nothing(self):
        root = helpers.make_repo(self.root / "repo")
        copy = helpers.copy_kit(root / "ai-sdlc-kit")
        before = helpers.snapshot(root)
        with self.fake_git_refusing():
            code, out = helpers.cli(root, copy, "setup", "--protect-only")
            quiet_code, quiet = helpers.cli(root, copy, "check", "--quiet")
        self.assertEqual(code, 2, out)
        self.assertIn("safe.directory", out)
        self.assertEqual(helpers.snapshot(root), before)
        self.assertEqual(quiet_code, 0)                 # the session-start check never fails
        self.assertIn("safe.directory", quiet)

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
