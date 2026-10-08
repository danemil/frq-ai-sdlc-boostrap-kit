#!/usr/bin/env python3
"""The v1 role packs: which roles exist, what each one gets, and generic Copilot guidance."""
import json
import re
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import packs, place, state
from test_superpowers import FILES

KIT = helpers.KIT
# id: (label, skills, git comfort default)
EXPECTED = {
    "po": ("Product Owner", ["playbook-product"], "hidden"),
    "pm": ("Product Manager", ["playbook-product"], "hidden"),
    "sm": ("Scrum Master / Team Coach (SAFe)", ["playbook-sm"], "guided"),
    "dev": ("Developer", ["playbook-dev", "brainstorming", "receiving-code-review",
                          "systematic-debugging", "test-driven-development",
                          "verification-before-completion", "writing-plans"], "git-native"),
    "qa": ("QA", ["playbook-qa", "systematic-debugging", "test-driven-development",
                  "verification-before-completion"], "guided"),
    "architect": ("Architect", ["playbook-architect", "brainstorming", "receiving-code-review",
                                "writing-plans"], "git-native"),
    "em": ("Engineering Manager", ["playbook-em", "writing-plans"], "git-native"),
}
# id: the connectors onboarding suggests (owner approval, 2026-10-08); core suggests none
CONNECTORS = {
    "po": ["jira", "confluence", "jama"],
    "pm": ["jira", "confluence", "jama"],
    "sm": ["jira", "confluence"],
    "dev": ["bitbucket", "jira", "jenkins"],
    "qa": ["jira", "jama", "jenkins"],
    "architect": ["confluence", "bitbucket", "jira"],
    "em": ["jenkins", "bitbucket", "jira"],
}
CORE_SKILLS = ["connectors", "deceneus", "doc-excel", "doc-pdf", "doc-powerpoint", "doc-word", "drawio",
               "likec4-dsl", "visual-explainers", "visual-issue"]   # every person gets them
CLIENT_WORDS = re.compile(r"\b(frequentis|frq|mosaix)\b", re.I)


def guidance_texts():
    """(path, text) of everything Copilot reads as guidance: the client-name rule (owner
    decision, 2026-10-08) keeps these generic; docs, tests and `source` paths may name the client."""
    for p in sorted((KIT / packs.ROLES_REL).glob("*/instructions.md")):
        yield p.relative_to(KIT).as_posix(), p.read_text(encoding="utf-8")
    for skill in packs.available_skills(KIT):        # any of them can be placed, whole folder
        for rel, text in place.placed_skill_files(KIT, skill).items():
            yield rel, text
    yield "packs.GIT_TEXT", "\n".join(packs.GIT_TEXT.values())         # rendered into core
    yield "packs.RITUAL_TEXT", "\n".join(packs.RITUAL_TEXT.values())
    yield "packs.HEADER", packs.HEADER
    if (KIT / "ONBOARDING.md").is_file():
        yield "ONBOARDING.md", (KIT / "ONBOARDING.md").read_text(encoding="utf-8")


class TestRoles(unittest.TestCase):
    def setUp(self):
        self.packs = packs.load(KIT)

    def test_the_v1_roles(self):
        self.assertEqual(sorted(packs.selectable(self.packs)), sorted(EXPECTED))

    def test_label_skills_and_defaults_per_role(self):
        for pid, (label, skills, git) in EXPECTED.items():
            with self.subTest(role=pid):
                p = self.packs[pid]
                self.assertEqual((p["label"], p["skills"]), (label, skills))
                self.assertEqual(p["defaults"], {"git_comfort": git, "rituals": "status"})

    def test_connector_defaults_per_role(self):
        self.assertEqual(self.packs["core"]["connectors"], [])
        for pid, names in CONNECTORS.items():
            with self.subTest(role=pid):
                self.assertEqual(self.packs[pid]["connectors"], names)
                self.assertLessEqual(set(names), set(packs.available_connectors(KIT)))

    def test_core_skills_reach_every_role(self):
        self.assertEqual(self.packs["core"]["skills"], CORE_SKILLS)
        for pid in EXPECTED:
            with self.subTest(role=pid):
                c = state.new("0")["choices"]
                c["roles"] = [pid]
                got = packs.combine(self.packs, c)["skills"]
                self.assertTrue(set(CORE_SKILLS) <= set(got), got)
                self.assertTrue(set(EXPECTED[pid][1]) <= set(got), got)
        for skill in CORE_SKILLS:
            self.assertIn(f"`{packs.PREFIX}{skill}`", self.packs["core"]["instructions"])

    def test_a_new_role_with_no_skills_of_its_own_gets_the_core_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            kit = helpers.copy_kit(Path(tmp) / "kit")
            d = kit / packs.ROLES_REL / "ux"
            d.mkdir()
            (d / "role.json").write_text(json.dumps({
                "id": "ux", "label": "UX Designer", "source": "README.md", "skills": [],
                "defaults": {"git_comfort": "hidden", "rituals": "status"}, "connectors": []}))
            (d / "instructions.md").write_text("# UX Designer\n")
            self.assertEqual(packs.validate(kit), [])
            all_packs = packs.load(kit)
            c = state.new("0")["choices"]
            c.update(name="Ana", roles=["ux"])
            self.assertEqual(packs.combine(all_packs, c)["skills"], CORE_SKILLS)
            wanted = place.wanted_files(kit, all_packs, c)
            for skill in CORE_SKILLS:
                src = kit / packs.SKILLS_REL / skill
                files = sorted(p.relative_to(src).as_posix() for p in src.rglob("*") if p.is_file())
                for rel in files:
                    self.assertIn(f".agents/skills/{packs.PREFIX}{skill}/{rel}", wanted)

    def test_several_roles_get_the_union_once(self):
        def skills(roles):
            c = state.new("0")["choices"]
            c["roles"] = roles
            return packs.combine(self.packs, c)["skills"]
        got = skills(["architect", "em"])
        self.assertEqual(got.count("writing-plans"), 1, got)
        self.assertEqual(set(got) & set(FILES),
                         {"brainstorming", "receiving-code-review", "writing-plans"})
        got = skills(["qa", "architect"])
        self.assertEqual(set(got) & set(FILES), set(FILES))
        self.assertEqual(len(got), len(set(got)), got)

    def test_a_core_skill_can_be_left_out(self):
        c = state.new("0")["choices"]
        c.update(roles=["dev"], drop_skills=["drawio"])
        self.assertNotIn("drawio", packs.combine(self.packs, c)["skills"])

    def test_sources_exist(self):
        for pid in EXPECTED:
            self.assertTrue((KIT / self.packs[pid]["source"]).is_file(), pid)

    def test_instructions_name_their_skills(self):
        for pid, (_, skills, _) in EXPECTED.items():
            for skill in skills:
                self.assertIn(f"`{packs.PREFIX}{skill}`", self.packs[pid]["instructions"], pid)

    def test_the_sm_playbook_is_generic_safe_role_guidance(self):
        text = (KIT / packs.SKILLS_REL / "playbook-sm/SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: playbook-sm\n"))
        for topic in ("PI Planning", "PI objectives", "impediment", "ART Sync",
                      "Scrum of Scrums", "Inspect & Adapt", "servant leader", "coach"):
            self.assertIn(topic, text)
        self.assertIsNone(CLIENT_WORDS.search(text))

    def test_all_packs_validate(self):
        self.assertEqual(packs.validate(KIT), [])

    def test_no_client_names_in_copilot_guidance(self):
        for rel, text in guidance_texts():
            with self.subTest(path=rel):
                self.assertIsNone(CLIENT_WORDS.search(text))


if __name__ == "__main__":
    unittest.main()
