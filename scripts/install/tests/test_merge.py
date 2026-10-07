#!/usr/bin/env python3
"""Unit tests for the format-aware mergers."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "template/scripts/harness"))
import merge


class TestJson(unittest.TestCase):
    def test_unions_disjoint_servers(self):
        mine = '{"mcpServers":{"code-review-graph":{"command":"uvx"}}}'
        kit = '{"mcpServers":{"knowledge":{"command":"python3"}}}'
        text, conflicts = merge.merge_json(mine, kit)
        servers = json.loads(text)["mcpServers"]
        self.assertEqual(sorted(servers), ["code-review-graph", "knowledge"])
        self.assertEqual(conflicts, [])

    def test_operator_wins_and_conflict_is_reported(self):
        text, conflicts = merge.merge_json('{"a":{"b":"mine"}}', '{"a":{"b":"kit"}}')
        self.assertEqual(json.loads(text)["a"]["b"], "mine")
        self.assertEqual(conflicts, ["a.b"])

    def test_empty_existing(self):
        text, _ = merge.merge_json("", '{"x":1}')
        self.assertEqual(json.loads(text), {"x": 1})

    def test_invalid_existing_raises(self):
        with self.assertRaises(ValueError):
            merge.merge_json("{not json", '{"x":1}')

    def test_idempotent(self):
        mine, kit = '{"mcpServers":{"a":{"command":"x"}}}', '{"mcpServers":{"b":{"command":"y"}}}'
        once, _ = merge.merge_json(mine, kit)
        twice, _ = merge.merge_json(once, kit)
        self.assertEqual(once, twice)


class TestHooks(unittest.TestCase):
    EXISTING = json.dumps({"hooks": {"PostToolUse": [
        {"matcher": "Edit", "hooks": [{"type": "command", "command": "graph update"}]}]}})
    KIT = json.dumps({"hooks": {"SessionStart": [
        {"matcher": "startup", "hooks": [{"type": "command", "command": "start.sh"}]}]}})

    def test_preserves_foreign_hooks(self):
        text, _ = merge.merge_json_hooks(self.EXISTING, self.KIT)
        hooks = json.loads(text)["hooks"]
        self.assertEqual(len(hooks["PostToolUse"]), 1)
        self.assertNotIn(merge.TAG, hooks["PostToolUse"][0])
        self.assertTrue(hooks["SessionStart"][0][merge.TAG])

    def test_rerun_replaces_only_tagged(self):
        once, _ = merge.merge_json_hooks(self.EXISTING, self.KIT)
        twice, _ = merge.merge_json_hooks(once, self.KIT)
        self.assertEqual(json.loads(once), json.loads(twice))
        self.assertEqual(len(json.loads(twice)["hooks"]["SessionStart"]), 1)

    def test_same_event_from_both_sides_coexists(self):
        mine = json.dumps({"hooks": {"SessionStart": [
            {"matcher": "", "hooks": [{"type": "command", "command": "graph status"}]}]}})
        text, _ = merge.merge_json_hooks(mine, self.KIT)
        groups = json.loads(text)["hooks"]["SessionStart"]
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["hooks"][0]["command"], "graph status")


class TestBlocks(unittest.TestCase):
    def test_append_then_replace(self):
        once = merge.merge_block("keep me\n", "one")
        self.assertIn("keep me", once)
        twice = merge.merge_block(once, "two")
        self.assertIn("keep me", twice)
        self.assertIn("two", twice)
        self.assertNotIn("one", twice)

    def test_content_after_block_survives(self):
        base = merge.merge_block("head\n", "body") + "tail\n"
        out = merge.merge_block(base, "body2")
        self.assertIn("head", out)
        self.assertIn("tail", out)
        self.assertIn("body2", out)

    def test_extract(self):
        text = merge.merge_block("", "hello\nworld")
        self.assertEqual(merge.extract_block(text), "hello\nworld")
        self.assertIsNone(merge.extract_block("nothing here"))

    def test_lines_skips_duplicates(self):
        out = merge.merge_lines("__pycache__/\n", "__pycache__/\nUSER.md\n")
        self.assertEqual(merge.extract_block(out), "USER.md")

    def test_toml_stays_valid(self):
        out = merge.merge_toml_block('model = "gpt-5"\n', '[mcp_servers.k]\ncommand = "python3"\n')
        self.assertIn("[mcp_servers.k]", out)
        with self.assertRaises(ValueError):
            merge.merge_toml_block("", "[[[broken")


class TestTomlRootKey(unittest.TestCase):
    """A bare key appended after a [table] belongs to that table, not the root."""

    EXISTING = 'model = "gpt-5.5"\n\n[projects."/x"]\ntrust_level = "trusted"\n'

    def test_key_lands_at_document_root(self):
        import tomllib
        out = merge.set_toml_root_key(self.EXISTING, "hooks", "./hooks.json")
        parsed = tomllib.loads(out)
        self.assertEqual(parsed["hooks"], "./hooks.json")
        self.assertEqual(parsed["model"], "gpt-5.5")
        self.assertEqual(parsed["projects"]["/x"]["trust_level"], "trusted")

    def test_survives_an_existing_sentinel_block(self):
        import tomllib
        text = merge.merge_toml_block(self.EXISTING, '[mcp_servers.k]\ncommand = "python3"\n')
        out = merge.set_toml_root_key(text, "hooks", "./hooks.json")
        parsed = tomllib.loads(out)
        self.assertEqual(parsed["hooks"], "./hooks.json")
        self.assertEqual(parsed["mcp_servers"]["k"]["command"], "python3")

    def test_replaces_rather_than_duplicates(self):
        once = merge.set_toml_root_key(self.EXISTING, "hooks", "./hooks.json")
        twice = merge.set_toml_root_key(once, "hooks", "./hooks.json")
        self.assertEqual(once, twice)
        changed = merge.set_toml_root_key(once, "hooks", "./other.json")
        self.assertEqual(changed.count("hooks ="), 1)

    def test_empty_file(self):
        self.assertEqual(merge.set_toml_root_key("", "hooks", "./h.json"),
                         'hooks = "./h.json"\n')


class TestTomlEmission(unittest.TestCase):
    def test_values(self):
        self.assertEqual(merge.toml_value(["a", "b"]), '["a", "b"]')
        self.assertEqual(merge.toml_value(True), "true")
        self.assertEqual(merge.toml_value('q"x'), '"q\\"x"')

    def test_keys(self):
        self.assertEqual(merge.toml_key("code-review-graph"), "code-review-graph")
        self.assertEqual(merge.toml_key("has space"), '"has space"')


if __name__ == "__main__":
    unittest.main()
