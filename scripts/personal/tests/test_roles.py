#!/usr/bin/env python3
"""The v1 role packs: which roles exist, what each one gets, and generic Copilot guidance."""
import re
import unittest

import helpers
from personal import packs

KIT = helpers.KIT
# id: (label, skills, git comfort default)
EXPECTED = {
    "po": ("Product Owner", ["playbook-product"], "hidden"),
    "pm": ("Product Manager", ["playbook-product"], "hidden"),
    "sm": ("Scrum Master / Team Coach (SAFe)", ["playbook-sm"], "guided"),
    "dev": ("Developer", ["playbook-dev"], "git-native"),
    "qa": ("QA", ["playbook-qa"], "guided"),
    "architect": ("Architect", ["playbook-architect"], "git-native"),
    "em": ("Engineering Manager", ["playbook-em"], "git-native"),
}
CLIENT_WORDS = re.compile(r"\b(frequentis|frq|mosaix)\b", re.I)


def guidance_texts():
    """(path, text) of everything Copilot reads as guidance: the client-name rule (owner
    decision, 2026-10-08) keeps these generic; docs, tests and `source` paths may name the client."""
    for p in sorted((KIT / packs.ROLES_REL).glob("*/instructions.md")):
        yield p.relative_to(KIT).as_posix(), p.read_text(encoding="utf-8")
    for skill in packs.available_skills(KIT):        # any of them can be placed
        p = KIT / packs.SKILLS_REL / skill / "SKILL.md"
        yield p.relative_to(KIT).as_posix(), p.read_text(encoding="utf-8")
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
