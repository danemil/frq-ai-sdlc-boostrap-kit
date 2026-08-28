#!/usr/bin/env python3
"""Unit tests for the install manifest and its file-state machine."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import manifest


class TestState(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.man = manifest.new_manifest("1.0.0")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def test_new_when_absent_and_unmanaged(self):
        self.assertEqual(manifest.state(self.root, self.man, "a.md"), manifest.NEW)

    def test_foreign_when_present_and_unmanaged(self):
        self.write("a.md", "mine")
        self.assertEqual(manifest.state(self.root, self.man, "a.md", b"kit"),
                         manifest.FOREIGN)

    def test_identical_beats_foreign(self):
        self.write("a.md", "same")
        self.assertEqual(manifest.state(self.root, self.man, "a.md", b"same"),
                         manifest.IDENTICAL)

    def test_clean_then_modified(self):
        self.write("a.md", "kit")
        manifest.record(self.man, "a.md", "own", b"kit")
        self.assertEqual(manifest.state(self.root, self.man, "a.md"), manifest.CLEAN)
        self.write("a.md", "edited by hand")
        self.assertEqual(manifest.state(self.root, self.man, "a.md"), manifest.MODIFIED)

    def test_missing_when_deleted(self):
        manifest.record(self.man, "a.md", "own", b"kit")
        self.assertEqual(manifest.state(self.root, self.man, "a.md"), manifest.MISSING)

    def test_roundtrip(self):
        manifest.record(self.man, "a.md", "seed", b"x")
        self.man["profile"] = "full"
        manifest.save(self.root, self.man)
        again = manifest.load(self.root)
        self.assertEqual(again["profile"], "full")
        self.assertEqual(again["files"]["a.md"]["class"], "seed")
        self.assertIsNotNone(again["installed_at"])

    def test_corrupt_manifest_is_survivable(self):
        p = self.root / manifest.MANIFEST_REL
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{ not json", encoding="utf-8")
        self.assertEqual(manifest.load(self.root)["files"], {})

    def test_schema_mismatch_resets(self):
        p = self.root / manifest.MANIFEST_REL
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"schema": 99, "files": {"x": {}}}), encoding="utf-8")
        self.assertEqual(manifest.load(self.root)["files"], {})

    def test_managed_filter(self):
        manifest.record(self.man, "a.md", "own", b"1")
        manifest.record(self.man, "b.md", "seed", b"2")
        self.assertEqual(manifest.managed(self.man, "seed"), ["b.md"])
        self.assertEqual(manifest.managed(self.man), ["a.md", "b.md"])


if __name__ == "__main__":
    unittest.main()
