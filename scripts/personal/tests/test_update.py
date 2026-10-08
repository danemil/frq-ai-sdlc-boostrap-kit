#!/usr/bin/env python3
"""`update`, run from a newer kit copy: replace the kit, refresh unedited files, keep edits."""
import json
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import paths

ARGS = ["setup", "--name", "Ana", "--roles", "po,dev", "--lang", "de"]
CORE = ".github/instructions/ai-sdlc-core.instructions.md"
PO = ".github/instructions/ai-sdlc-po.instructions.md"


class TestUpdate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = helpers.make_repo(Path(self.tmp.name).resolve() / "repo", {"README.md": "x\n"})
        self.kit = self.root / paths.KIT_REL
        helpers.cli(self.root, helpers.copy_kit(self.root / "kit-copy"), *ARGS)
        self.newer = helpers.copy_kit(self.root / "kit-newer")
        (self.newer / "VERSION").write_text("9.9.9\n")
        for pid in ("core", "po"):
            with open(self.newer / f"roles/{pid}/instructions.md", "a", encoding="utf-8") as fh:
                fh.write("\nNewer kit line.\n")

    def tearDown(self):
        self.tmp.cleanup()

    def update(self, kit=None):
        return helpers.cli(self.root, kit or self.newer, "update")

    def test_the_kit_folder_is_replaced_and_the_version_recorded(self):
        code, out = self.update()
        self.assertEqual(code, 0, out)
        self.assertIn("Updated to AI-SDLC 9.9.9", out)
        self.assertEqual(paths.kit_version(self.kit), "9.9.9")
        self.assertFalse(self.newer.exists())
        st = json.loads((self.root / paths.STATE_REL).read_text())
        self.assertEqual(st["kit_version"], "9.9.9")
        self.assertEqual(st["choices"]["roles"], ["po", "dev"])

    def test_unedited_files_are_refreshed_and_edited_ones_kept(self):
        (self.root / PO).write_text("my po notes\n")
        self.update()
        self.assertIn("Newer kit line.", (self.root / CORE).read_text())
        self.assertEqual((self.root / PO).read_text(), "my po notes\n")
        self.assertIn("Newer kit line.", (self.root / (PO + ".kit-new")).read_text())
        self.assertEqual(helpers.git(self.root, "status", "--porcelain").stdout, "")

    def test_a_skill_the_newer_kit_drops_is_removed(self):
        role = self.newer / "roles/dev/role.json"
        data = json.loads(role.read_text())
        data["skills"] = []
        role.write_text(json.dumps(data))
        self.update()
        self.assertFalse((self.root / ".agents/skills/ai-sdlc-playbook-dev").exists())

    def test_an_older_copy_is_refused(self):
        (self.newer / "VERSION").write_text("0.0.1\n")
        code, out = self.update()
        self.assertEqual(code, 2)
        self.assertIn("This copy is older (0.0.1)", out)
        self.assertTrue(self.newer.exists())

    def test_update_from_the_installed_kit_refreshes_in_place(self):
        (self.root / CORE).unlink()
        code, out = self.update(self.kit)
        self.assertEqual(code, 0, out)
        self.assertTrue((self.root / CORE).is_file())

    def test_after_update_check_is_clean(self):
        code, out = self.update()
        self.assertIn("Check: all good.", out)


if __name__ == "__main__":
    unittest.main()
