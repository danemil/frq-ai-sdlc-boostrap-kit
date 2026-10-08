#!/usr/bin/env python3
"""Releases: the version, the changelog entries, and docs that lead with personal setup."""
import unittest

import helpers

KIT = helpers.KIT


def read(rel):
    return (KIT / rel).read_text(encoding="utf-8")


class TestRelease(unittest.TestCase):
    def test_version(self):
        self.assertEqual(read("VERSION").strip(), "0.5.1")

    def test_the_newest_changelog_entry_is_the_version_and_unreleased_is_empty(self):
        log = read("CHANGELOG.md")
        unreleased = log.split("## [Unreleased]", 1)[1].split("\n## [", 1)
        self.assertEqual(unreleased[0].strip(), "")
        self.assertTrue(unreleased[1].startswith(read("VERSION").strip() + "] — "))

    def test_changelog_0_5_1_has_likec4_connect_suggested_and_the_update_fix(self):
        entry = read("CHANGELOG.md").split("## [0.5.1]", 1)[1].split("\n## [", 1)[0]
        for text in ("`likec4-dsl` skill in the core pack", "`setup.py connect --suggested`",
                     "`skipped_connectors`", "check that a kit copy is complete"):
            self.assertIn(text, entry)

    def test_changelog_0_5_0_has_the_connectors_and_the_check_fix(self):
        entry = read("CHANGELOG.md").split("## [0.5.0]", 1)[1].split("\n## [", 1)[0]
        for text in ("**Personal connectors, read-only:**", "`setup.py connect <name> [--test]`",
                     "`connectors` skill in the core pack", "Connector defaults per role",
                     "`docs/how-to.md`", "Another copy of the kit (same version X)"):
            self.assertIn(text, entry)

    def test_changelog_says_team_mode_is_retired(self):
        entry = read("CHANGELOG.md").split("## [0.4.0]", 1)[1].split("\n## [", 1)[0]
        self.assertIn("**Team mode is retired.**", entry)

    def test_readme_leads_with_copy_then_onboarding(self):
        top = "\n".join(read("README.md").splitlines()[:20])
        self.assertIn("Copy this kit folder", top)
        self.assertIn('Say **"do the onboarding"**', top)

    def test_readme_no_longer_offers_the_installer(self):
        self.assertNotIn("./install.sh --into", read("README.md"))

    def test_install_sh_says_it_is_retired(self):
        self.assertIn("team mode is retired since kit 0.4.0", read("install.sh"))


if __name__ == "__main__":
    unittest.main()
