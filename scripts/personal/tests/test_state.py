#!/usr/bin/env python3
"""state.json: schema, atomic save, and fingerprints through the Phase 0 manifest."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers  # noqa: F401  (sys.path)
from personal import paths, reuse, state


class TestState(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_state_has_schema_version_and_defaults(self):
        st = state.new("0.4.0")
        self.assertEqual((st["schema"], st["kit_version"]), (state.SCHEMA, "0.4.0"))
        self.assertEqual(st["choices"]["lang"], "en")
        self.assertEqual((st["files"], st["acks"]), ({}, {}))

    def test_roundtrip(self):
        st = state.new("0.4.0")
        st["choices"].update(name="Ana", roles=["po", "sm"], lang="de")
        state.save(self.root, st)
        again = state.load(self.root)
        self.assertEqual(again["choices"]["roles"], ["po", "sm"])
        self.assertIsNotNone(again["updated_at"])

    def test_choices_added_later_get_their_defaults(self):
        path = self.root / paths.STATE_REL
        path.parent.mkdir()
        path.write_text(json.dumps({"schema": 1, "kit_version": "0.4.0",
                                    "choices": {"name": "Ana", "roles": ["po"]}}))
        self.assertEqual(state.load(self.root)["choices"]["add_skills"], [])

    def test_older_state_has_no_kit_only_list(self):
        path = self.root / paths.STATE_REL
        path.parent.mkdir()
        path.write_text(json.dumps({"schema": 1, "kit_version": "0.8.0", "choices": {"name": "Ana"}}))
        self.assertEqual(state.load(self.root)["kit_only"], [])
        path.write_text(json.dumps({"schema": 1, "kit_version": "0.9.0", "kit_only": ["b", 3, "a", "a"]}))
        self.assertEqual(state.load(self.root)["kit_only"], ["a", "b"])
        path.write_text(json.dumps({"schema": 1, "kit_version": "0.9.0", "kit_only": "x"}))
        self.assertEqual(state.load(self.root)["kit_only"], [])

    def test_missing_corrupt_or_foreign_schema_is_not_set_up(self):
        self.assertIsNone(state.load(self.root))
        path = self.root / paths.STATE_REL
        path.parent.mkdir()
        path.write_text("{not json")
        self.assertIsNone(state.load(self.root))
        path.write_text('{"schema": 99}')
        self.assertIsNone(state.load(self.root))

    def test_a_failed_save_keeps_the_old_state_and_no_temp_file(self):
        state.save(self.root, state.new("0.4.0"))
        before = (self.root / paths.STATE_REL).read_bytes()
        with mock.patch("os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                state.save(self.root, state.new("9.9.9"))
        self.assertEqual((self.root / paths.STATE_REL).read_bytes(), before)
        self.assertEqual([p.name for p in (self.root / ".ai-sdlc").iterdir()], ["state.json"])

    def test_fingerprints_follow_the_manifest_states(self):
        st = state.new("0.4.0")
        rel = ".github/instructions/ai-sdlc-core.instructions.md"
        (self.root / rel).parent.mkdir(parents=True)
        (self.root / rel).write_text("kit\n")
        reuse.record(st, rel, "kit", b"kit\n")
        self.assertEqual(reuse.file_state(self.root, st, rel), reuse.CLEAN)
        (self.root / rel).write_text("edited\n")
        self.assertEqual(reuse.file_state(self.root, st, rel), reuse.MODIFIED)


if __name__ == "__main__":
    unittest.main()
