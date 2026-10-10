#!/usr/bin/env python3
"""The six process skills vendored from obra/superpowers v6.4.2: content policy guards.

These check the shipped text, not behaviour (a manual try in Copilot does that): the
planned files and nothing else, the upstream licence and pin, no link to a skill or file
the kit does not ship, and no git step the AI takes without asking the person.
Plan: docs/roadmap/2026-10-08-superpowers-pack-plan.md, Task 1.
"""
import re
import unittest

import helpers
from personal import packs, place

KIT = helpers.KIT
LIB = helpers.KIT / packs.SKILLS_REL
UPSTREAM_COMMIT = "8ca22dba9a94f28898bbce59f2537ff4d87c747d"
COMMON = ["LICENSE", "PROVENANCE.md", "SKILL.md"]
FILES = {
    "brainstorming": COMMON,                  # decision 1: no spec-document-reviewer-prompt.md
    "writing-plans": COMMON,
    "test-driven-development": COMMON + ["writing-good-tests.md"],
    "systematic-debugging": COMMON + ["condition-based-waiting.md", "defense-in-depth.md",
                                      "root-cause-tracing.md"],
    "verification-before-completion": COMMON,
    "receiving-code-review": COMMON,
}
NOT_SHIPPED = re.compile(
    r"subagent-driven-development|executing-plans|finishing-a-development-branch|"
    r"using-superpowers|requesting-code-review|dispatching-parallel-agents|using-git-worktrees|"
    r"writing-skills|diagnosing-superpowers|elements-of-style|superpowers:")
LEFT_OUT = re.compile(r"visual-companion|Visual Companion|scripts/|find-polluter|"
                      r"condition-based-waiting-example|CREATION-LOG|test-pressure|"
                      r"test-academic|docs/superpowers/|spec-document-reviewer")
GIT = re.compile(r"(?i)\bcommit(?:s|ted|ting)?\b|\bmerg(?:e|es|ed|ing)\b|"
                 r"\bpush(?:es|ed|ing)?\b(?!\s+back)")        # "push back" is review talk
GIT_RULE = ("- **Git:** never commit, push or merge on your own. Follow the person's "
            "git-comfort setting and ask before each commit.")
SHOW_RULE = ("- **Show before you change:** before editing or creating any file (a new test file too), "
             "show the proposed diff or content and wait "
             "for a yes; if you can't ask, stop after proposing. Report evidence (the test output), "
             "never just \"Fixed\".")
SHOWS_FIRST = {"systematic-debugging", "test-driven-development", "receiving-code-review"}  # E2E 2026-10-09
TRIGGERS = {   # E2E 2026-10-09: these never triggered on plain phrasings
    "test-driven-development": ["write tests first", "test-first", "TDD", "red-green", "failing test",
                                "tests for this function"],
    "verification-before-completion": ['"fixed"', '"done"', '"tests pass"', '"ready to merge"'],
    # Copilot re-test 2026-10-10: a bug report or a request for tests did not load them
    "systematic-debugging": ['"bug"', '"freezes"', '"error"', '"fails"', '"could not"', '"crash"',
                             '"exception"'],
}
TRIGGERS["test-driven-development"] += ['"write a test"', '"tests for"', '"add tests"']
BRAINSTORMING_DESCRIPTION = (     # decision 2: upstream "You MUST use this before …", softened
    'description: "Use before any creative work - creating features, building components, '
    'adding functionality, or modifying behavior. Explores user intent, requirements and '
    'design before implementation."')
REVIEWED = {   # upstream lines with a git word that tell the AI to do nothing; reviewed 2026-10-08
    "brainstorming": ["recent commits"],
    "writing-plans": ['git commit -m "feat: add specific feature"'],
    "test-driven-development": ["catches bugs before commit"],
    "systematic-debugging": ["recent commits"],
    "verification-before-completion": ["before committing or creating PRs",
                                       "About to commit/push/PR without verification",
                                       "Committing, PR creation, task completion"],
    "receiving-code-review": [],
}


def shipped(skill):
    """(file name, text) of every file Copilot reads as the skill: all but PROVENANCE.md and
    LICENSE (a human-facing record that must name what was left out, and the licence)."""
    for p in sorted((LIB / skill).rglob("*")):
        rel = p.relative_to(LIB / skill).as_posix()
        if p.is_file() and rel not in ("PROVENANCE.md", "LICENSE"):
            yield rel, p.read_text(encoding="utf-8")


class Checks:
    """Every vendored skill passes these. Subclasses set `skill`."""
    skill = ""

    def folder(self):
        d = LIB / self.skill
        self.assertTrue(d.is_dir(), f"{packs.SKILLS_REL}/{self.skill}/ is missing: not vendored yet")
        return d

    def text(self, name):
        p = self.folder() / name
        self.assertTrue(p.is_file(), f"{self.skill}/{name} is missing")
        return p.read_text(encoding="utf-8")

    def test_the_folder_holds_exactly_the_planned_files(self):
        d = self.folder()
        got = sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file())
        self.assertEqual(got, sorted(FILES[self.skill]))

    def test_the_name_is_upstream_and_setup_places_it_prefixed(self):
        self.assertTrue(self.text("SKILL.md").startswith(f"---\nname: {self.skill}\n"))
        self.assertEqual(set(place.placed_skill_files(KIT, self.skill)),
                         {f".agents/skills/{packs.PREFIX}{self.skill}/{f}" for f in FILES[self.skill]})
        missing = []
        place.placed_skill(KIT, self.skill, missing)
        self.assertEqual(missing, [])

    def test_the_licence_is_upstream_mit(self):
        text = self.text("LICENSE")
        self.assertTrue(text.startswith("MIT License"))
        self.assertIn("Copyright (c) 2025 Jesse Vincent", text)

    def test_provenance_pins_upstream_and_lists_each_file(self):
        text = self.text("PROVENANCE.md")
        for needed in ("https://github.com/obra/superpowers", "v6.4.2", UPSTREAM_COMMIT, "MIT",
                       "## Local modifications", "## Updating"):
            self.assertIn(needed, text)
        for f in FILES[self.skill]:
            if f != "PROVENANCE.md":
                self.assertIn(f"`{f}`", text)

    def _none_match(self, pattern):
        self.folder()
        found = [f"{name}: {m.group(0)!r}" for name, text in shipped(self.skill)
                 for m in pattern.finditer(text)]
        self.assertEqual(found, [])

    def test_no_file_names_a_skill_the_kit_does_not_ship(self):
        self._none_match(NOT_SHIPPED)

    def test_no_file_points_at_upstream_material_left_out(self):
        self._none_match(LEFT_OUT)

    def test_skill_md_has_the_kit_git_rule(self):
        text = self.text("SKILL.md")
        self.assertIn("## This kit's copy", text)
        self.assertIn(GIT_RULE, text)
        self.assertLess(text.index("## This kit's copy"), text.index(GIT_RULE))

    def test_the_ai_shows_the_diff_before_it_edits(self):
        text = self.text("SKILL.md")
        if self.skill in SHOWS_FIRST:
            kit = text.split("## This kit's copy", 1)[1].split("\n## ", 1)[0]
            self.assertIn(SHOW_RULE, kit)
            self.assertIn("Show before you change", self.text("PROVENANCE.md"))
        else:
            self.assertNotIn(SHOW_RULE, text)

    def test_the_description_has_its_trigger_phrases_and_fits(self):
        desc = re.search(r"(?m)^description: (.+)$", self.text("SKILL.md")).group(1)
        self.assertLessEqual(len(desc), 1024)
        for phrase in TRIGGERS.get(self.skill, []):
            self.assertIn(phrase, desc)
        if self.skill in TRIGGERS:
            self.assertIn("trigger phrases added", self.text("PROVENANCE.md"))

    def test_every_git_mention_asks_first_or_was_reviewed(self):
        self.folder()
        unasked = [f"{name}:{n}" for name, text in shipped(self.skill)
                   for n, line in enumerate(text.splitlines(), 1)
                   if GIT.search(line) and "ask" not in line.lower()
                   and not any(r in line for r in REVIEWED[self.skill])]
        self.assertEqual(unasked, [], "git words that neither ask the person nor were reviewed")


class TestBrainstorming(Checks, unittest.TestCase):
    skill = "brainstorming"

    def test_specs_go_to_docs_specs_and_hand_over_to_ai_sdlc_writing_plans(self):
        skill_md = self.text("SKILL.md")
        self.assertIn("docs/specs/", skill_md)
        self.assertIn("`ai-sdlc-writing-plans`", skill_md)
        self.assertEqual(re.findall(r"(?<!ai-sdlc-)writing-plans", skill_md), [])
        self.assertNotIn("frontend-design", skill_md)
        self.assertNotIn("mcp-builder", skill_md)

    def test_after_a_spec_the_next_step_offered_is_a_plan(self):
        kit = self.text("SKILL.md").split("## This kit's copy", 1)[1].split("\n## ", 1)[0]
        self.assertIn("the next step you offer is always a plan with the `ai-sdlc-writing-plans` skill", kit)
        self.assertIn("never offer to start implementing", kit)

    def test_the_description_is_softened_not_must(self):
        line = self.text("SKILL.md").splitlines()[2]
        self.assertEqual(line, BRAINSTORMING_DESCRIPTION)
        self.assertNotIn("MUST", line)

    def test_provenance_records_the_files_left_out_and_the_softer_description(self):
        text = self.text("PROVENANCE.md")
        for needed in ("`spec-document-reviewer-prompt.md`", "`visual-companion.md`",
                       "You MUST use this before any creative work", "Use before any creative work"):
            self.assertIn(needed, text)


class TestWritingPlans(Checks, unittest.TestCase):
    skill = "writing-plans"

    def test_plans_go_to_docs_plans_and_a_person_gates_each_task(self):
        text = self.text("SKILL.md")
        self.assertIn("docs/plans/", text)
        self.assertIn("A person carries out each task, or reviews it before the next one starts", text)
        self.assertNotIn("Subagent-driven", text)
        self.assertNotIn("worktree", text.lower())


class TestTestDrivenDevelopment(Checks, unittest.TestCase):
    skill = "test-driven-development"

    def test_the_tests_guide_link_stays_in_the_folder(self):
        self.folder()
        _, text = place.placed_skill(KIT, self.skill)
        self.assertIn("](writing-good-tests.md)", text)


class TestSystematicDebugging(Checks, unittest.TestCase):
    skill = "systematic-debugging"

    def test_it_names_the_placed_skills_if_you_have_them(self):
        text = self.text("SKILL.md")
        self.assertIn("`ai-sdlc-test-driven-development` skill (if you have it)", text)
        self.assertIn("`ai-sdlc-verification-before-completion` skill (if you have it)", text)


class TestVerificationBeforeCompletion(Checks, unittest.TestCase):
    skill = "verification-before-completion"


class TestReceivingCodeReview(Checks, unittest.TestCase):
    skill = "receiving-code-review"

    def test_replies_are_posted_by_the_person(self):
        text = self.text("SKILL.md")
        self.assertNotIn("gh api", text)
        self.assertIn("Bitbucket", text)


class TestPack(unittest.TestCase):
    """The six come from obra/superpowers, and they are role skills, not core (Task 8)."""

    def test_exactly_these_six_come_from_superpowers(self):
        got = {p.parent.name for p in LIB.glob("*/PROVENANCE.md")
               if "obra/superpowers" in p.read_text(encoding="utf-8")}
        self.assertEqual(got, set(FILES))

    def test_they_are_role_skills_not_core(self):
        self.assertEqual(set(packs.load(KIT)["core"]["skills"]) & set(FILES), set())


if __name__ == "__main__":
    unittest.main()
