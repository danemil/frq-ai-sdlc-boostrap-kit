#!/usr/bin/env python3
"""Unit tests for the deck snapshot schema (deck-builder design §3.2)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import snapshot as sn

SCOPE = {"projects": ["ATM"], "sprint": "ATM Sprint 42"}


class SnapshotTest(unittest.TestCase):
    def test_new_snapshot_is_valid(self):
        snap = sn.new_snapshot("run-1", SCOPE)
        self.assertEqual(snap["schema"], sn.SCHEMA)
        self.assertEqual(snap["run_id"], "run-1")
        self.assertEqual(snap["scope"], SCOPE)
        for key in ("sources", "work_items", "pull_requests", "commits", "requirements", "docs"):
            self.assertEqual(snap[key], [])
        self.assertEqual(sn.validate(snap), [])

    def test_add_source_records_tier_and_timestamp(self):
        snap = sn.new_snapshot("run-1", SCOPE)
        sn.add_source(snap, "jira", "script", query="project = ATM")
        sn.add_source(snap, "sharepoint", "unavailable", reason="no MCP configured")
        jira, sharepoint = snap["sources"]
        self.assertEqual((jira["name"], jira["tier"], jira["query"]), ("jira", "script", "project = ATM"))
        self.assertRegex(jira["fetched_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(sharepoint["reason"], "no MCP configured")
        self.assertEqual(sn.validate(snap), [])

    def test_add_source_rejects_unknown_tier(self):
        snap = sn.new_snapshot("run-1", SCOPE)
        with self.assertRaises(ValueError):
            sn.add_source(snap, "jira", "guessed")

    def test_add_source_replaces_same_name(self):
        snap = sn.new_snapshot("run-1", SCOPE)
        sn.add_source(snap, "jira", "unavailable", reason="no auth")
        sn.add_source(snap, "jira", "agent-sourced", via="atlassian-mcp")
        self.assertEqual([s["tier"] for s in snap["sources"]], ["agent-sourced"])

    def test_validate_flags_unknown_tier(self):
        snap = sn.new_snapshot("run-1", SCOPE)
        snap["sources"].append({"name": "jira", "tier": "guessed", "fetched_at": "x"})
        self.assertTrue(any("tier" in e for e in sn.validate(snap)))

    def test_validate_flags_work_item_without_key(self):
        snap = sn.new_snapshot("run-1", SCOPE)
        snap["work_items"].append({"title": "no key"})
        self.assertTrue(any("work_items[0]" in e for e in sn.validate(snap)))

    def test_validate_flags_wrong_schema_and_missing_lists(self):
        errors = sn.validate({"schema": 99, "run_id": "r", "scope": {}})
        self.assertTrue(any("schema" in e for e in errors))
        self.assertTrue(any("work_items" in e for e in errors))

    def test_weakest(self):
        self.assertEqual(sn.weakest(["script", "agent-sourced"]), "agent-sourced")
        self.assertEqual(sn.weakest(["script", "unavailable", "agent-sourced"]), "unavailable")
        self.assertEqual(sn.weakest(["script"]), "script")
        self.assertEqual(sn.weakest([]), "unavailable")

    def test_source_tier_lookup(self):
        snap = sn.new_snapshot("run-1", SCOPE)
        sn.add_source(snap, "jira", "script")
        self.assertEqual(sn.source_tier(snap, "jira"), "script")
        self.assertEqual(sn.source_tier(snap, "bitbucket"), "unavailable")

    def test_save_load_round_trip_is_byte_identical(self):
        snap = sn.new_snapshot("run-1", SCOPE)
        sn.add_source(snap, "jira", "script")
        snap["work_items"].append({"key": "ATM-2", "title": "Ünïcode ok"})
        with tempfile.TemporaryDirectory() as tmp:
            p1, p2 = Path(tmp, "a", "snapshot.json"), Path(tmp, "b.json")
            sn.save(snap, p1)
            sn.save(sn.load(p1), p2)
            self.assertEqual(p1.read_bytes(), p2.read_bytes())
            self.assertTrue(p1.read_text(encoding="utf-8").endswith("\n"))
            self.assertEqual(sn.load(p1), snap)

    def test_save_refuses_invalid_snapshot_and_keeps_old_file(self):
        snap = sn.new_snapshot("run-1", SCOPE)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "snapshot.json")
            sn.save(snap, path)
            before = path.read_bytes()
            bad = dict(snap, schema=99)
            with self.assertRaises(ValueError):
                sn.save(bad, path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(tmp).iterdir()), [path])  # no stray temp file

    def test_run_dir(self):
        root = Path("/repo")
        self.assertEqual(sn.run_dir("run-1", root), root / ".ai-sdlc" / "decks" / "run-1")
        with self.assertRaises(ValueError):
            sn.run_dir("../escape", root)


if __name__ == "__main__":
    unittest.main()
