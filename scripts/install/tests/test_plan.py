#!/usr/bin/env python3
"""Unit tests for file classification, profile expansion and plan building."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
KIT = HERE.parents[3]

import manifest  # noqa: E402
import plan  # noqa: E402


class TestClassify(unittest.TestCase):
    def setUp(self):
        self.spec = plan.load_classes()

    def test_kit_owned_by_default(self):
        for rel in ("scripts/session/start.sh", "dashboard/app.py",
                    ".claude/skills/playbook-dev/SKILL.md"):
            self.assertEqual(plan.classify(rel, self.spec), plan.CLASS_OWN, rel)

    def test_seed_files(self):
        for rel in ("AGENTS.md", "WORKING-AGREEMENT.md", "docs/knowledge/README.md"):
            self.assertEqual(plan.classify(rel, self.spec), plan.CLASS_SEED, rel)

    def test_merge_files(self):
        for rel in (".mcp.json", ".claude/settings.json", ".gitignore"):
            self.assertEqual(plan.classify(rel, self.spec), plan.CLASS_MERGE, rel)


class TestProfiles(unittest.TestCase):
    def setUp(self):
        self.spec = plan.load_classes()
        self.template = KIT / "template"

    def test_profiles_nest(self):
        sizes = [len(plan.selected_files(self.template, self.spec, p))
                 for p in ("minimal", "standard", "full")]
        self.assertEqual(sizes, sorted(sizes))
        self.assertLess(sizes[0], sizes[2])

    def test_minimal_excludes_dashboard_full_includes_it(self):
        minimal = plan.selected_files(self.template, self.spec, "minimal")
        full = plan.selected_files(self.template, self.spec, "full")
        self.assertFalse([r for r in minimal if r.startswith("dashboard/")])
        self.assertTrue([r for r in full if r.startswith("dashboard/")])
        self.assertIn("AGENTS.md", minimal)

    def test_unknown_profile_raises(self):
        with self.assertRaises(KeyError):
            plan.profile_patterns(self.spec, "nope")

    def test_no_vcs_or_cache_files_selected(self):
        for rel in plan.selected_files(self.template, self.spec, "full"):
            self.assertNotIn("__pycache__", rel)
            self.assertFalse(rel.endswith(".pyc"))


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.spec = plan.load_classes()
        self.template = KIT / "template"

    def test_empty_target_is_all_creates(self):
        with tempfile.TemporaryDirectory() as tmp:
            actions = plan.build(self.template, tmp, self.spec, "minimal",
                                 manifest.new_manifest())
            self.assertTrue(actions)
            self.assertEqual({a.kind for a in actions}, {plan.CREATE})

    def test_foreign_seed_is_skipped_owned_is_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("mine\n", encoding="utf-8")
            (root / "scripts").mkdir()
            (root / "scripts/validate-skills.py").write_text("mine\n", encoding="utf-8")
            actions = {a.rel: a for a in plan.build(self.template, tmp, self.spec,
                                                    "minimal", manifest.new_manifest())}
            self.assertEqual(actions["AGENTS.md"].kind, plan.SKIP)
            self.assertEqual(actions["scripts/validate-skills.py"].kind, plan.CONFLICT)

    def test_deferred_conflict_is_not_re_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts/validate-skills.py").write_text("mine\n", encoding="utf-8")
            kit_bytes = (self.template / "scripts/validate-skills.py").read_bytes()
            man = manifest.new_manifest()
            man["deferred"] = {"scripts/validate-skills.py":
                               manifest.sha256_bytes(kit_bytes)}
            actions = {a.rel: a for a in plan.build(self.template, tmp, self.spec,
                                                    "minimal", man)}
            self.assertEqual(actions["scripts/validate-skills.py"].kind, plan.SKIP)

    def test_render_substitutes_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            def render(rel, data):
                return data.replace(b"<PROJECT_NAME>", b"Acme")
            actions = {a.rel: a for a in plan.build(self.template, tmp, self.spec,
                                                    "minimal", manifest.new_manifest(),
                                                    render=render)}
            self.assertIn(b"Acme", actions["AGENTS.md"].payload)
            self.assertNotIn(b"<PROJECT_NAME>", actions["AGENTS.md"].payload)


if __name__ == "__main__":
    unittest.main()
