#!/usr/bin/env python3
"""Releases: the version, the changelog entries, and docs that lead with personal setup."""
import unittest

import helpers

KIT = helpers.KIT


def read(rel):
    return (KIT / rel).read_text(encoding="utf-8")


class TestRelease(unittest.TestCase):
    def test_version(self):
        self.assertEqual(read("VERSION").strip(), "0.9.0")

    def test_the_newest_changelog_entry_is_the_version_and_unreleased_is_empty(self):
        log = read("CHANGELOG.md")
        unreleased = log.split("## [Unreleased]", 1)[1].split("\n## [", 1)
        self.assertEqual(unreleased[0].strip(), "")
        self.assertTrue(unreleased[1].startswith(read("VERSION").strip() + "] — "))

    def test_changelog_0_9_0_has_the_stack_pack(self):
        entry = read("CHANGELOG.md").split("## [0.9.0]", 1)[1].split("\n## [", 1)[0]
        for text in ("`ai-sdlc-java-junit`", "`ai-sdlc-golang-testing`", "`ai-sdlc-react-testing-library`",
                     "`ai-sdlc-maven-via-artifactory`", "`ai-sdlc-javafx`", "recommend", "--all",
                     "library skills", "never `@latest`", "react-best-practices", "frq-4-pptx-agent",
                     "44 layouts", ".kit-only"):
            self.assertIn(text, entry)

    def test_changelog_0_8_0_has_the_brand_skill_and_binary_placement(self):
        entry = read("CHANGELOG.md").split("## [0.8.0]", 1)[1].split("\n## [", 1)[0]
        for text in ("`frq-brandbook` skill in the core pack", "`ai-sdlc-frq-brandbook`",
                     "`scripts/check_brand.py`", "`scripts/new_deck.py`", "**Company brand by default**",
                     "unless the person asks for a plain one", "binary files", "`template/.gitignore`",
                     "one exception"):
            self.assertIn(text, entry)

    def test_changelog_0_8_0_has_the_lifecycle_fixes(self):
        entry = read("CHANGELOG.md").split("## [0.8.0]", 1)[1].split("\n## [", 1)[0]
        self.assertIn("\n### Fixed\n", entry)
        for text in ("**`remove` and `disconnect` ask first.**", "notice(s) to read", "`--verbose`",
                     "Moved <copy> into .ai-sdlc/kit", "warns when it runs as root",
                     "detected dubious ownership", "`--drop-skill`", "`template/ONBOARDING.retired.md`",
                     "asks the three questions again"):
            self.assertIn(text, entry)

    def test_changelog_0_7_0_has_the_process_skills(self):
        entry = read("CHANGELOG.md").split("## [0.7.0]", 1)[1].split("\n## [", 1)[0]
        for text in ("obra/superpowers v6.4.2", "`ai-sdlc-brainstorming`", "`ai-sdlc-writing-plans`",
                     "`ai-sdlc-test-driven-development`", "`ai-sdlc-systematic-debugging`",
                     "`ai-sdlc-verification-before-completion`", "`ai-sdlc-receiving-code-review`",
                     "never commit, push or merge on their own"):
            self.assertIn(text, entry)

    def test_changelog_0_6_0_has_likec4_connect_suggested_and_the_update_fix(self):
        entry = read("CHANGELOG.md").split("## [0.6.0]", 1)[1].split("\n## [", 1)[0]
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
