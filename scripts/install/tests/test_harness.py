#!/usr/bin/env python3
"""Unit tests for harness detection and canonical->derived translation."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness

MCP = {"mcpServers": {
    "code-review-graph": {"command": "uvx", "args": ["code-review-graph", "serve"],
                          "type": "stdio"},
    "knowledge": {"command": "python3", "args": ["scripts/knowledge/mcp_server.py"],
                  "$note": "documentation only"},
    "issue-tracker": {"url": "https://mcp.atlassian.com/v1/mcp", "auth": "oauth"},
    "context7": {"url": "https://mcp.context7.com/mcp", "$disabled": True},
}}


class TestTable(unittest.TestCase):
    def test_ships_the_three_named_harnesses(self):
        table = harness.load_table()
        for name in ("claude-code", "codex-cli", "copilot-cli"):
            self.assertIn(name, table)
        self.assertNotIn("$comment", table)

    def test_detects_by_repo_path(self):
        table = harness.load_table()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".cursorrules").write_text("x", encoding="utf-8")
            self.assertIn("cursor", harness.detect(tmp, table))

    def test_copilot_reuses_claude_skills(self):
        table = harness.load_table()
        self.assertEqual(table["copilot-cli"]["skills"]["kind"], "native")
        self.assertEqual(table["copilot-cli"]["skills"]["path"], ".claude/skills")

    def test_codex_symlinks_to_the_canonical_tree(self):
        table = harness.load_table()
        self.assertEqual(table["codex-cli"]["skills"]["kind"], "symlink")
        self.assertEqual(table["codex-cli"]["skills"]["to"], ".claude/skills")

    def test_copilot_generates_brief_rules_and_vscode_hooks(self):
        row = harness.load_table()["copilot-cli"]
        self.assertEqual(row["brief"]["kind"], "generated")
        self.assertEqual(row["brief"]["path"], ".github/copilot-instructions.md")
        self.assertEqual(row["brief"]["format"], "copilot-brief")
        self.assertEqual(row["brief"]["sections"], ["0", "3"])
        self.assertEqual(row["rules"]["format"], "copilot-instructions")
        self.assertEqual(row["rules"]["path"], ".github/instructions")
        self.assertEqual(row["rules"]["from"], ".claude/rules")
        self.assertEqual(row["hooks"]["format"], "vscode-claude-hooks")
        self.assertEqual(row["hooks"]["path"], ".vscode/settings.json")

    def test_copilot_is_detected_by_its_generated_brief(self):
        table = harness.load_table()
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch("sync.shutil.which", return_value=None):
            (Path(tmp) / ".github/instructions").mkdir(parents=True)
            self.assertIn("copilot-cli", harness.detect(tmp, table))


class TestMcpTranslation(unittest.TestCase):
    def test_drops_docs_and_disabled(self):
        names = sorted(harness.mcp_servers(MCP))
        self.assertEqual(names, ["code-review-graph", "issue-tracker", "knowledge"])
        self.assertNotIn("$note", harness.mcp_servers(MCP)["knowledge"])

    def test_codex_toml_parses(self):
        import tomllib
        parsed = tomllib.loads(harness.to_codex_toml(MCP))
        self.assertEqual(parsed["mcp_servers"]["code-review-graph"]["command"], "uvx")
        self.assertEqual(parsed["mcp_servers"]["issue-tracker"]["url"],
                         "https://mcp.atlassian.com/v1/mcp")
        self.assertNotIn("context7", parsed["mcp_servers"])

    def test_copilot_schema(self):
        out = harness.to_copilot_mcp(MCP)["mcpServers"]
        local = out["code-review-graph"]
        self.assertEqual(local["type"], "local")
        self.assertEqual(local["args"], ["code-review-graph", "serve"])
        self.assertEqual(local["tools"], ["*"])          # required by Copilot's schema
        self.assertEqual(out["issue-tracker"]["type"], "http")
        self.assertNotIn("context7", out)

    def test_hyphenated_names_stay_bare_keys(self):
        self.assertIn("[mcp_servers.code-review-graph]", harness.to_codex_toml(MCP))


class TestHookTranslation(unittest.TestCase):
    def test_drops_claude_only_events_and_tags(self):
        settings = {"hooks": {
            "SessionStart": [{"matcher": "startup", "_aiSdlc": True,
                              "hooks": [{"type": "command", "command": "start.sh"}]}],
            "SessionEnd": [{"hooks": [{"type": "command", "command": "save.sh"}]}],
        }}
        out = harness.to_codex_hooks(settings)["hooks"]
        self.assertIn("SessionStart", out)
        self.assertNotIn("SessionEnd", out)          # Codex has no SessionEnd
        self.assertNotIn("_aiSdlc", out["SessionStart"][0])


class TestPointer(unittest.TestCase):
    def test_points_at_agents_md_and_carries_no_rules(self):
        text = harness.pointer_text({"label": "Gemini CLI"})
        self.assertIn("AGENTS.md", text)
        self.assertIn("Gemini CLI", text)

    def test_mdc_style_has_frontmatter(self):
        text = harness.pointer_text({"label": "Cursor", "style": "mdc"})
        self.assertTrue(text.startswith("---"))
        self.assertIn("alwaysApply", text)


if __name__ == "__main__":
    unittest.main()
