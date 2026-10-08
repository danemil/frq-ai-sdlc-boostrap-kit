#!/usr/bin/env python3
"""The reconcile engine: write, adopt, keep edits, sweep, never touch tracked paths."""
import errno
import posixpath
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers
from personal import packs, place, state

KIT = helpers.KIT
CORE = ".github/instructions/ai-sdlc-core.instructions.md"
PO = ".github/instructions/ai-sdlc-po.instructions.md"
DEV_SKILL = ".agents/skills/ai-sdlc-playbook-dev/SKILL.md"


def choices(**kw):
    c = state.new("0")["choices"]
    c.update(name="Ana", roles=["po", "dev"], lang="de")
    c.update(kw)
    return c


class TestPlace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = helpers.make_repo(Path(self.tmp.name) / "repo", {"README.md": "team\n"})
        self.packs = packs.load(KIT)
        self.st = state.new("0.4.0")

    def tearDown(self):
        self.tmp.cleanup()

    def wanted(self, **kw):
        return place.wanted_files(KIT, self.packs, choices(**kw))

    def test_wanted_files_follow_the_choices(self):
        self.assertEqual(sorted(self.wanted()), sorted([
            ".agents/skills/ai-sdlc-playbook-dev/SKILL.md",
            ".agents/skills/ai-sdlc-playbook-product/SKILL.md",
            ".ai-sdlc/USER.md", ".github/instructions/ai-sdlc-core.instructions.md",
            ".github/instructions/ai-sdlc-dev.instructions.md", PO]))
        self.assertIn("- **Roles:** Product Owner, Developer", self.wanted()[".ai-sdlc/USER.md"])

    def test_first_apply_writes_everything_and_records_it(self):
        report = place.apply(self.root, self.st, self.wanted())
        self.assertEqual(sorted(report["written"]), sorted(self.wanted()))
        self.assertEqual(sorted(self.st["files"]), sorted(self.wanted()))
        self.assertIn(".agents", self.st["created_dirs"])

    def test_second_apply_changes_nothing(self):
        place.apply(self.root, self.st, self.wanted())
        before = helpers.snapshot(self.root)
        report = place.apply(self.root, self.st, self.wanted())
        self.assertEqual(report, {"written": [], "kept": [], "skipped": [], "removed": []})
        self.assertEqual(helpers.snapshot(self.root), before)

    def test_an_interrupted_run_is_completed_without_duplicates(self):
        place.apply(self.root, self.st, self.wanted())   # files written, state never saved
        fresh = state.new("0.4.0")
        report = place.apply(self.root, fresh, self.wanted())
        self.assertEqual(report["written"], [])
        self.assertEqual(sorted(fresh["files"]), sorted(self.wanted()))

    def test_an_edit_is_kept_and_the_kit_copy_lands_next_to_it_only_when_it_changed(self):
        place.apply(self.root, self.st, self.wanted())
        (self.root / PO).write_text("my edit\n")
        report = place.apply(self.root, self.st, self.wanted())
        self.assertEqual((report["kept"], report["written"]), ([PO], []))
        report = place.apply(self.root, self.st, self.wanted(name="Ana Maria"))
        self.assertEqual((self.root / PO).read_text(), "my edit\n")
        self.assertNotIn(PO + place.SIDECAR, report["written"])   # po's text did not change
        report = place.apply(self.root, self.st, self.wanted(lang="ro"))
        self.assertIn(CORE, report["written"])                     # core did change, unedited
        (self.root / CORE).write_text("mine\n")
        report = place.apply(self.root, self.st, self.wanted(lang="en"))
        self.assertIn(CORE + place.SIDECAR, report["written"])
        self.assertIn("Always answer in English", (self.root / (CORE + place.SIDECAR)).read_text())

    def test_an_unwanted_clean_file_is_removed_with_its_empty_folders(self):
        place.apply(self.root, self.st, self.wanted())
        report = place.apply(self.root, self.st, self.wanted(roles=["po"]))
        self.assertIn(DEV_SKILL, report["removed"])
        self.assertFalse((self.root / DEV_SKILL).parent.exists())
        place.apply(self.root, self.st, {})
        self.assertFalse((self.root / ".agents").exists())
        self.assertFalse((self.root / ".github").exists())

    def test_an_unwanted_edited_file_is_kept_and_forgotten(self):
        place.apply(self.root, self.st, self.wanted())
        (self.root / DEV_SKILL).write_text("my notes\n")
        report = place.apply(self.root, self.st, self.wanted(roles=["po"]))
        self.assertIn(DEV_SKILL, report["kept"])
        self.assertEqual((self.root / DEV_SKILL).read_text(), "my notes\n")
        self.assertNotIn(DEV_SKILL, self.st["files"])

    def test_a_tracked_path_is_never_written(self):
        (self.root / CORE).parent.mkdir(parents=True)
        (self.root / CORE).write_text("team's\n")
        helpers.git(self.root, "add", "-A")
        helpers.git(self.root, "commit", "-qm", "team file at a kit path")
        report = place.apply(self.root, self.st, self.wanted())
        self.assertIn(f"{CORE} (the team's git tracks this path)", report["skipped"])
        self.assertEqual((self.root / CORE).read_text(), "team's\n")

    def test_a_file_the_kit_did_not_write_is_left_alone(self):
        (self.root / PO).parent.mkdir(parents=True)
        (self.root / PO).write_text("someone else's\n")
        report = place.apply(self.root, self.st, self.wanted())
        self.assertIn(f"{PO} (a file the kit did not write is already there)", report["skipped"])
        self.assertEqual((self.root / PO).read_text(), "someone else's\n")


SKILL_DIR = "template/.claude/skills/playbook-dev"     # where the skill lives in the kit
PLACED_DIR = ".agents/skills/ai-sdlc-playbook-dev"     # where setup places it in the repo


def kit_has(rel):
    return (KIT / rel).exists()


class TestLinks(unittest.TestCase):
    """Relative links that leave the skill's folder are pointed into .ai-sdlc/kit/."""

    def rewrite(self, text):
        return place.rewrite_links(text, SKILL_DIR, PLACED_DIR, kit_has)

    def test_an_outside_link_is_rewritten_and_resolves_to_a_kit_file(self):
        # playbook-dev/SKILL.md line 77 and playbook-em/SKILL.md line 69, as they are today
        text, missing = self.rewrite(
            "See also [`AGENTS.md`](../../../AGENTS.md) for cross-seat AI operating rules.\n"
            "the [`scripts/validate-*.py`](../../../scripts/) checks\n")
        self.assertEqual(text,
            "See also [`AGENTS.md`](../../../.ai-sdlc/kit/template/AGENTS.md) for cross-seat "
            "AI operating rules.\n"
            "the [`scripts/validate-*.py`](../../../.ai-sdlc/kit/template/scripts/) checks\n")
        self.assertEqual(missing, [])
        # Every outside link in a really placed playbook lands on an existing kit file.
        placed = place.wanted_files(KIT, packs.load(KIT), choices(roles=["dev"]))[DEV_SKILL]
        targets = [t for t in re.findall(r"\]\(([^)\s]+)\)", placed) if t.startswith("../")]
        self.assertTrue(targets)
        for t in targets:
            rel = posixpath.normpath(posixpath.join(PLACED_DIR, t.split("#")[0]))
            self.assertTrue(rel.startswith(".ai-sdlc/kit/"), t)
            self.assertTrue(kit_has(rel[len(".ai-sdlc/kit/"):]), t)

    def test_an_inside_link_is_unchanged(self):
        text = "Read [the checklist](checklist.md) and [ref](./refs/a.md#top).\n"
        self.assertEqual(self.rewrite(text), (text, []))

    def test_urls_and_anchors_are_never_touched(self):
        text = ("[spec](https://agentskills.io/specification) [plain](http://example.com/x) "
                "[mail](mailto:team@example.com) [§2](#2--decision-rights-cheat-sheet)\n")
        self.assertEqual(self.rewrite(text), (text, []))
        text, _ = self.rewrite("[`WORKING-AGREEMENT.md`](../../../WORKING-AGREEMENT.md#55) §5.5\n")
        self.assertEqual(text, "[`WORKING-AGREEMENT.md`]"
                               "(../../../.ai-sdlc/kit/template/WORKING-AGREEMENT.md#55) §5.5\n")

    def test_a_link_with_no_target_in_the_kit_is_left_and_reported(self):
        text = "[gone](../../../docs/nowhere.md) and [out](../../../../../../etc/passwd)\n"
        self.assertEqual(self.rewrite(text),
                         (text, ["../../../docs/nowhere.md", "../../../../../../etc/passwd"]))


class TestMoveKit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve() / "repo"
        self.copy = helpers.copy_kit(self.root / "tools/kit-copy")

    def tearDown(self):
        self.tmp.cleanup()

    def test_moves_into_ai_sdlc(self):
        dest = place.move_kit(self.root, self.copy)
        self.assertEqual(dest, self.root / ".ai-sdlc/kit")
        self.assertTrue(place.is_kit(dest))
        self.assertFalse(self.copy.exists())

    def test_across_filesystems_it_copies_then_deletes(self):
        with mock.patch("os.rename", side_effect=OSError(errno.EXDEV, "cross-device link")):
            dest = place.move_kit(self.root, self.copy)
        self.assertTrue(place.is_kit(dest))
        self.assertFalse(self.copy.exists())

    def test_already_in_place_is_a_no_op(self):
        dest = place.move_kit(self.root, self.copy)
        self.assertEqual(place.move_kit(self.root, dest), dest)

    def test_refuses_a_kit_outside_the_repo_or_a_second_kit(self):
        with self.assertRaises(ValueError):
            place.move_kit(self.root / "elsewhere", self.copy)
        place.move_kit(self.root, self.copy)
        other = helpers.copy_kit(self.root / "other-kit")
        with self.assertRaises(FileExistsError):
            place.move_kit(self.root, other)


if __name__ == "__main__":
    unittest.main()
