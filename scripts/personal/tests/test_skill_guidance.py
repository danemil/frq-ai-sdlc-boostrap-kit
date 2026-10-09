#!/usr/bin/env python3
"""Guidance fixes from the Copilot E2E runs of 2026-10-09 (kit 0.8.0): the rules each finding
added to the core instructions and the skills stay in place. These check the shipped text;
a Copilot run checks the behaviour."""
import json
import re
import unittest

import helpers
from personal import packs

KIT = helpers.KIT
LIB = KIT / packs.SKILLS_REL


def skill(name, rel="SKILL.md"):
    return (LIB / name / rel).read_text(encoding="utf-8")


def core():
    return (KIT / packs.ROLES_REL / "core/instructions.md").read_text(encoding="utf-8")


class TestCoreInstructions(unittest.TestCase):
    def test_the_session_check_is_the_first_rule(self):
        """It ran in 3 of 16 fresh sessions when it sat in the middle of the file."""
        rules = re.findall(r"(?m)^\*\*([^*]+)\*\*", core())
        self.assertEqual(rules[0], "Session start: do this first.")
        self.assertIn("before your first reply", core())

    def test_the_session_hook_line_counts_as_the_check(self):
        """Copilot CLI's sessionStart hook puts the check in the context (trusted folders)."""
        self.assertIn('If your context already holds an "AI-SDLC session check" line', core())

    def test_kit_skills_are_read_by_exact_path_not_found_by_search(self):
        text = core()
        self.assertIn("Kit skills are hidden from git, so search tools skip them.", text)
        self.assertIn("read its files by exact path (`.agents/skills/ai-sdlc-<name>/…`)", text)
        self.assertIn("Never decide by glob or search", text)

    def test_ask_before_downloads(self):
        self.assertIn("Ask before anything that downloads or installs: `npx`", core())

    def test_a_pasted_token_is_never_quoted_back(self):
        for text in (core(), skill("connectors")):
            self.assertIn('"the token you pasted"', text)
        self.assertIn("never quote it back", skill("connectors"))

    def test_personal_notes_are_never_offered_for_a_commit_and_remember_means_deceneus(self):
        text = core()
        self.assertIn("never offer to commit them", text)
        for phrase in ('"Remember that"', '"from now on"', '"always do X"'):
            self.assertIn(phrase, text)
        self.assertIn("`ai-sdlc-deceneus`", text)
        desc = skill("deceneus").split("---", 2)[1]
        for phrase in ('"remember that"', '"from now on"', '"always do X"'):
            self.assertIn(phrase, desc)
        self.assertIn("never offer to\ncommit these files", skill("deceneus"))


    def test_do_the_onboarding_always_goes_to_onboarding_md(self):
        """A set-up repo got "Onboarding is already complete" (lifecycle E2E, item 2)."""
        line = [l for l in core().splitlines() if l.startswith("**Changing the setup.**")][0]
        self.assertIn('"do the onboarding" (also when the kit is already set up', line)
        self.assertIn("`.ai-sdlc/kit/ONBOARDING.md`", line)

    def test_german_uses_one_form_of_address(self):
        self.assertIn('In German, address $name as "Sie" throughout', core())


class TestConnectors(unittest.TestCase):
    def test_disconnect_needs_the_persons_yes(self):
        text = skill("connectors")
        self.assertIn("run it again with `--yes` only after they say yes", text)
        self.assertIn("Never add `--yes` on your own", text)

    def test_the_role_table_matches_the_role_packs(self):
        """A PO/SM run was told to connect Bitbucket and Jenkins."""
        all_packs = packs.load(KIT)
        table = skill("connectors").split("## Which connectors fit a role", 1)[1]
        rows = dict(re.findall(r"(?m)^\| ([^|]+?) \| ([a-z, ]+) \|$", table))
        got = {}
        for label, names in rows.items():
            for part in re.split(r", (?=[A-Z])", label):
                got[part] = names.split(", ")
        for pid, pack in all_packs.items():
            if pid == "core":
                continue
            label = pack["label"].replace(" (SAFe)", "")
            self.assertEqual(got.get(label), pack["connectors"], pid)
        self.assertIn("do not suggest connecting the tool", table)

    def test_my_sprint_needs_no_board_id(self):
        text = skill("connectors")
        self.assertIn('jira search "sprint in openSprints() AND assignee = currentUser()"', text)
        self.assertIn("Ask for a board id only when", text)


class TestVisualIssue(unittest.TestCase):
    def test_npx_only_after_a_yes_otherwise_not_compiled(self):
        text = skill("visual-issue")
        self.assertIn("ask the person before you run it", text)
        self.assertIn('"not compiled"', text)
        npx = [l for l in text.splitlines() if l.startswith("npx ")]
        self.assertTrue(npx)
        for line in npx:
            self.assertIn("only after the person says yes", line)

    def test_only_the_persons_acceptance_criteria(self):
        text = skill("visual-issue")
        self.assertIn('**"Suggested, to confirm"**', text)
        self.assertIn("Suggested, to confirm", skill("visual-issue", "PROVENANCE.md"))


class TestVisualExplainers(unittest.TestCase):
    def test_no_prompt_panel_unless_asked(self):
        self.assertNotIn('<div class="prompt-box">', skill("visual-explainers", "assets/starter.html"))
        self.assertIn("No `.prompt-box`", skill("visual-explainers"))
        self.assertIn("Only when the person asks for it",
                      skill("visual-explainers", "references/design-system.md"))


class TestRoleInstructions(unittest.TestCase):
    def test_dev_shows_the_diff_and_reports_evidence(self):
        text = (KIT / packs.ROLES_REL / "dev/instructions.md").read_text(encoding="utf-8")
        self.assertIn("Show the diff and wait for a yes before saving", text)
        self.assertIn('never just "Fixed"', text)

    def test_tests_first_loads_the_tdd_skill_before_any_file(self):
        """A "write tests first" run in a Developer repo skipped the TDD skill and tried to
        create the test file without showing it."""
        for role in ("dev", "qa"):
            text = (KIT / packs.ROLES_REL / role / "instructions.md").read_text(encoding="utf-8")
            self.assertIn('"write tests first", "test-first" or "TDD": load '
                          "`ai-sdlc-test-driven-development` first", text, role)
            self.assertIn("a failing test or a bug: load `ai-sdlc-systematic-debugging` first",
                          text, role)
            self.assertIn("A new file counts: show its full content first.", text, role)

    def test_a_new_file_counts_as_a_change(self):
        for name in ("test-driven-development", "systematic-debugging", "receiving-code-review"):
            self.assertIn("before editing or creating any file (a new test file too), show the "
                          "proposed diff or content and wait for a yes", skill(name), name)


if __name__ == "__main__":
    unittest.main()
