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
        wanted = self.wanted()
        self.assertEqual(sorted(r for r in wanted if not r.startswith(".agents/")), sorted([
            ".ai-sdlc/USER.md", ".github/hooks/ai-sdlc-session.json",
        ".github/instructions/ai-sdlc-core.instructions.md",
            ".github/instructions/ai-sdlc-dev.instructions.md", PO]))
        skills = {r.split("/")[2] for r in wanted if r.startswith(".agents/")}
        self.assertEqual(skills, {f"ai-sdlc-{s}" for s in (
            *self.packs["dev"]["skills"], *self.packs["po"]["skills"],
            *self.packs["core"]["skills"])})
        self.assertIn(".agents/skills/ai-sdlc-drawio/references/xml-reference.md", wanted)
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


NOTES = {   # a multi-file library skill: {path in its folder: bytes}
    "SKILL.md": b"---\nname: notes\ndescription: Use for notes.\n---\n\nSee [ref](references/a.md).\n",
    "references/a.md": b"# A\n\nWindows line ends stay as they are.\r\n",
    "assets/page.html": "<!doctype html><title>Café</title>\n".encode("utf-8"),
    "LICENSE": b"Apache License 2.0\n",
}
NOTES_DIR = ".agents/skills/ai-sdlc-notes"


class TestMultiFileSkill(unittest.TestCase):
    """A skill is placed as its whole folder, tracked file by file, and removed cleanly."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.kit = base / "kit"
        src = self.kit / packs.SKILLS_REL / "notes"
        for rel, data in {**NOTES, ".DS_Store": b"\x00\x01", "__pycache__/x.pyc": b"\x00"}.items():
            (src / rel).parent.mkdir(parents=True, exist_ok=True)
            (src / rel).write_bytes(data)
        self.root = helpers.make_repo(base / "repo", {"README.md": "team\n"})
        self.st = state.new("0.4.0")

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_file_of_the_folder_is_placed_byte_for_byte(self):
        files = place.placed_skill_files(self.kit, "notes")
        self.assertEqual(sorted(files), sorted(f"{NOTES_DIR}/{rel}" for rel in NOTES))
        self.assertTrue(files[f"{NOTES_DIR}/SKILL.md"].startswith("---\nname: ai-sdlc-notes\n"))
        for rel in ("references/a.md", "assets/page.html", "LICENSE"):
            self.assertEqual(files[f"{NOTES_DIR}/{rel}"].encode("utf-8"), NOTES[rel], rel)

    def test_placed_files_are_recorded_and_removed_with_their_folders(self):
        before = helpers.snapshot(self.root)
        wanted = place.placed_skill_files(self.kit, "notes")
        report = place.apply(self.root, self.st, wanted)
        self.assertEqual(sorted(report["written"]), sorted(wanted))
        self.assertEqual(sorted(self.st["files"]), sorted(wanted))
        self.assertEqual((self.root / NOTES_DIR / "references/a.md").read_bytes(),
                         NOTES["references/a.md"])
        self.assertEqual(place.apply(self.root, self.st, wanted),
                         {"written": [], "kept": [], "skipped": [], "removed": []})
        report = place.apply(self.root, self.st, {})
        self.assertEqual(sorted(report["removed"]), sorted(wanted))
        self.assertEqual(helpers.snapshot(self.root), before)

    def test_an_edited_reference_file_is_kept(self):
        wanted = place.placed_skill_files(self.kit, "notes")
        place.apply(self.root, self.st, wanted)
        ref = self.root / NOTES_DIR / "references/a.md"
        ref.write_text("my notes\n")
        report = place.apply(self.root, self.st, {})
        self.assertEqual(report["kept"], [f"{NOTES_DIR}/references/a.md"])
        self.assertEqual(ref.read_text(), "my notes\n")
        self.assertFalse((self.root / NOTES_DIR / "assets").exists())

    def test_a_binary_file_is_placed_byte_for_byte_and_removed(self):
        logo = b"\x89PNG\r\n\x1a\n\xff\x00\xfe"           # not UTF-8
        (self.kit / packs.SKILLS_REL / "notes/assets/logo.png").write_bytes(logo)
        before = helpers.snapshot(self.root)
        wanted = place.placed_skill_files(self.kit, "notes")
        self.assertEqual(wanted[f"{NOTES_DIR}/assets/logo.png"], logo)    # bytes, not text
        self.assertIsInstance(wanted[f"{NOTES_DIR}/references/a.md"], str)
        place.apply(self.root, self.st, wanted)
        self.assertEqual((self.root / NOTES_DIR / "assets/logo.png").read_bytes(), logo)
        self.assertEqual(place.apply(self.root, self.st, wanted),
                         {"written": [], "kept": [], "skipped": [], "removed": []})
        report = place.apply(self.root, self.st, {})
        self.assertIn(f"{NOTES_DIR}/assets/logo.png", report["removed"])
        self.assertEqual(helpers.snapshot(self.root), before)

    def test_an_edited_binary_file_is_kept_and_the_newer_copy_goes_next_to_it(self):
        src = self.kit / packs.SKILLS_REL / "notes/assets/logo.png"
        src.write_bytes(b"\xff\x01")
        place.apply(self.root, self.st, place.placed_skill_files(self.kit, "notes"))
        (self.root / NOTES_DIR / "assets/logo.png").write_bytes(b"\xff\x02")   # the person's edit
        src.write_bytes(b"\xff\x03")                                          # a newer kit
        report = place.apply(self.root, self.st, place.placed_skill_files(self.kit, "notes"))
        self.assertEqual(report["kept"], [f"{NOTES_DIR}/assets/logo.png"])
        self.assertEqual((self.root / NOTES_DIR / "assets/logo.png").read_bytes(), b"\xff\x02")
        self.assertEqual((self.root / NOTES_DIR / "assets/logo.png.kit-new").read_bytes(), b"\xff\x03")


SKILL_DIR ="template/.claude/skills/playbook-dev"     # where the skill lives in the kit
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

    # --- validate_kit: is a copy whole enough to set up from? ---------------------

    def test_a_whole_kit_has_no_problems(self):
        self.assertEqual(place.validate_kit(KIT), [])
        self.assertEqual(place.validate_kit(self.copy), [])

    def test_each_missing_piece_is_named(self):
        for rel in ("VERSION", "setup.py", "ONBOARDING.md", "roles/core/role.json",
                    "roles/sm/instructions.md", "template/.claude/skills/connectors/SKILL.md",
                    "scripts/personal/connectors/jira.py"):
            with self.subTest(rel=rel):
                p = self.copy / rel
                data = p.read_bytes()
                p.unlink()
                self.assertIn(f"missing {rel}", place.validate_kit(self.copy))
                p.write_bytes(data)
        self.assertEqual(place.validate_kit(self.copy), [])

    def test_a_file_a_skill_links_to_is_required(self):
        skill = self.copy / packs.SKILLS_REL / "playbook-dev"
        targets = [m.group(1).partition("#")[0] for m in re.finditer(
            r"\]\(([^)\s]+)\)", (skill / "SKILL.md").read_text(encoding="utf-8"))
                   if not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:|[#/]", m.group(1))]
        self.assertTrue(targets, "playbook-dev links to no kit file; pick another skill")
        rel = posixpath.normpath(posixpath.join(f"{packs.SKILLS_REL}/playbook-dev", targets[0]))
        (self.copy / rel).unlink()
        self.assertIn(f"missing {rel} (linked from playbook-dev/SKILL.md)",
                      place.validate_kit(self.copy))

    def test_a_broken_role_file_or_version_is_named(self):
        (self.copy / "roles/po/role.json").write_text("{not json")
        (self.copy / "VERSION").write_text("\n")
        problems = place.validate_kit(self.copy)
        self.assertTrue(any(p.startswith("roles/po/role.json is not readable") for p in problems),
                        problems)
        self.assertIn("VERSION is empty or not a version number", problems)


if __name__ == "__main__":
    unittest.main()
