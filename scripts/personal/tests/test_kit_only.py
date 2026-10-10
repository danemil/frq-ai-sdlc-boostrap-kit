#!/usr/bin/env python3
"""Kit-copy-only skill assets (design 2026-10-09 §8.7, plan Task K1).

A skill folder may hold a `.kit-only` file: one glob per line, relative to the skill
folder, `#` comments. Setup never places a matching file (nor `.kit-only` itself); a
Markdown link to such a file is pointed into .ai-sdlc/kit/; check reports a kit-only
file missing from the kit copy; drop and remove behave.

Each test uses a temp kit copy with a small fixture skill `kitonly-demo`, added to the
dev role.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import packs, paths, place

DEMO = "kitonly-demo"
PLACED = f".agents/skills/{packs.PREFIX}{DEMO}"
KIT_SKILL = f"{paths.KIT_REL}/{packs.SKILLS_REL}/{DEMO}"
BIG = b"\x89BIG\x00\xff\xfe binary"
SKILL_MD = ("---\nname: kitonly-demo\ndescription: Use for the kit-only test.\n---\n\n"
            "See [big](assets/big.bin) and [small](assets/small.svg).\n")
REF_MD = "# Ref\n\nThe [big file](../assets/big.bin) and [small](../assets/small.svg).\n"


def add_demo(kit, kit_only="# kept in the kit copy\n\nassets/*.bin\n"):
    src = Path(kit) / packs.SKILLS_REL / DEMO
    (src / "assets").mkdir(parents=True)
    (src / "references").mkdir()
    (src / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
    (src / "references/ref.md").write_text(REF_MD, encoding="utf-8")
    (src / "assets/big.bin").write_bytes(BIG)
    (src / "assets/small.svg").write_text("<svg/>\n", encoding="utf-8")
    if kit_only is not None:
        (src / place.KIT_ONLY_FILE).write_text(kit_only, encoding="utf-8")
    role = Path(kit) / "roles/dev/role.json"
    data = json.loads(role.read_text(encoding="utf-8"))
    data["skills"].append(DEMO)
    role.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return src


class TestKitOnly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.root = helpers.make_repo(self.base / "repo", {"README.md": "team\n"})
        self.before = helpers.snapshot(self.root)
        self.copy = helpers.copy_kit(self.root / "kit-copy")
        add_demo(self.copy)

    def tearDown(self):
        self.tmp.cleanup()

    def setup_dev(self):
        code, out = helpers.cli(self.root, self.copy, "setup", "--name", "Ana", "--roles", "dev",
                                "--lang", "en")
        self.assertEqual(code, 0, out)
        return self.root / paths.KIT_REL

    def test_a_kit_only_file_is_not_placed(self):
        self.assertEqual(place.kit_only(self.copy, DEMO), ["assets/big.bin"])
        self.assertEqual(place.kit_only(self.copy, "drawio"), [])
        files = place.placed_skill_files(self.copy, DEMO)
        self.assertEqual(sorted(files), [f"{PLACED}/SKILL.md", f"{PLACED}/assets/small.svg",
                                         f"{PLACED}/references/ref.md"])
        self.assertEqual(place.kit_asset_rel(DEMO, "assets/big.bin"), f"{KIT_SKILL}/assets/big.bin")

    def test_a_link_to_a_kit_only_file_points_into_the_kit_copy(self):
        files = place.placed_skill_files(self.copy, DEMO)
        skill = files[f"{PLACED}/SKILL.md"]
        self.assertIn(f"[big](../../../{KIT_SKILL}/assets/big.bin)", skill)
        self.assertIn("[small](assets/small.svg)", skill)
        ref = files[f"{PLACED}/references/ref.md"]
        self.assertIn(f"[big file](../../../../{KIT_SKILL}/assets/big.bin)", ref)
        self.assertIn("[small](../assets/small.svg)", ref)
        kit = self.setup_dev()
        self.assertTrue((self.root / PLACED / "references" / f"../../../../{KIT_SKILL}/assets/big.bin")
                        .resolve() == (kit / packs.SKILLS_REL / DEMO / "assets/big.bin").resolve())

    def test_patterns_are_globs_with_comments(self):
        src = Path(self.copy) / packs.SKILLS_REL / DEMO
        (src / "assets/deep").mkdir()
        (src / "assets/deep/other.bin").write_bytes(b"\xff")
        self.assertEqual(place.kit_only(self.copy, DEMO), ["assets/big.bin"], "* stays in one folder")
        self.assertIn(f"{PLACED}/assets/deep/other.bin", place.placed_skill_files(self.copy, DEMO))
        self.assertEqual(place.validate_kit(self.copy), [])
        (src / place.KIT_ONLY_FILE).write_text("assets/*.bin\nassets/*/*.bin\n# x\n\nfonts/*.ttf\n",
                                               encoding="utf-8")
        self.assertEqual(place.kit_only(self.copy, DEMO), ["assets/big.bin", "assets/deep/other.bin"])
        self.assertEqual(place.validate_kit(self.copy),
                         [f".kit-only pattern matches nothing: {packs.SKILLS_REL}/{DEMO}: fonts/*.ttf"])

    def test_check_reports_a_missing_kit_only_file(self):
        kit = self.setup_dev()
        code, out = helpers.cli(self.root, kit, "check")
        self.assertEqual(code, 0, out)
        big = self.root / KIT_SKILL / "assets/big.bin"
        big.unlink()
        code, out = helpers.cli(self.root, kit, "check")
        self.assertEqual(code, 1, out)
        self.assertIn(f"missing:{KIT_SKILL}/assets/big.bin", out)
        code, out = helpers.cli(self.root, kit, "change", "--drop-skill", DEMO)
        self.assertEqual(code, 0, out)
        code, out = helpers.cli(self.root, kit, "check")
        self.assertNotIn(f"missing:{KIT_SKILL}", out)

    def test_drop_and_remove(self):
        kit = self.setup_dev()
        self.assertTrue((self.root / PLACED / "SKILL.md").is_file())
        self.assertFalse((self.root / PLACED / "assets/big.bin").exists())
        self.assertFalse((self.root / PLACED / place.KIT_ONLY_FILE).exists())
        code, out = helpers.cli(self.root, kit, "change", "--drop-skill", DEMO)
        self.assertEqual(code, 0, out)
        self.assertFalse((self.root / PLACED).exists())
        self.assertEqual((self.root / KIT_SKILL / "assets/big.bin").read_bytes(), BIG)
        code, out = helpers.cli(self.root, kit, "remove", "--yes")
        self.assertEqual(code, 0, out)
        self.assertEqual(helpers.snapshot(self.root), self.before)

    def test_binary_placement_still_works_without_kit_only(self):
        (Path(self.copy) / packs.SKILLS_REL / DEMO / place.KIT_ONLY_FILE).unlink()
        self.assertEqual(place.kit_only(self.copy, DEMO), [])
        files = place.placed_skill_files(self.copy, DEMO)
        self.assertEqual(files[f"{PLACED}/assets/big.bin"], BIG)
        self.assertIn("[big](assets/big.bin)", files[f"{PLACED}/SKILL.md"])
        self.setup_dev()
        self.assertEqual((self.root / PLACED / "assets/big.bin").read_bytes(), BIG)


if __name__ == "__main__":
    unittest.main()
