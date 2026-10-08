#!/usr/bin/env python3
"""Release 0.4.0: the version, the changelog entry, and docs that lead with personal setup."""
import unittest

import helpers

KIT = helpers.KIT


def read(rel):
    return (KIT / rel).read_text(encoding="utf-8")


class TestRelease(unittest.TestCase):
    def test_version(self):
        self.assertEqual(read("VERSION").strip(), "0.4.0")

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
