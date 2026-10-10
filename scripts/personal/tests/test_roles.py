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
               "frq-brandbook", "likec4-dsl", "visual-explainers",
               "visual-issue"]   # every person gets them
CLIENT_WORDS = re.compile(r"\b(frequentis|frq|mosaix)\b", re.I)
# The one exception to the client-name rule (owner decision, 2026-10-09): the company brand
# skill. Its own folder may name the client, and other guidance may name the skill itself
# (`ai-sdlc-frq-brandbook`) to point at it. Nothing else may name the client.
BRAND_SKILL = "frq-brandbook"
BRAND_DIR = f".agents/skills/{packs.PREFIX}{BRAND_SKILL}/"
BRAND_NAME = re.compile(rf"(?<![\w-])(?:{packs.PREFIX})?{BRAND_SKILL}(?![\w-])")


def client_names(rel, text) -> list[str]:
    """Client names in guidance file `rel`, after the brand-skill exception."""
    if rel.startswith(BRAND_DIR):
        return []
    return [m.group(0) for m in CLIENT_WORDS.finditer(BRAND_NAME.sub("", text))]


def guidance_texts():
    """(path, text) of everything Copilot reads as guidance: the client-name rule (owner
    decision, 2026-10-08) keeps these generic; docs, tests and `source` paths may name the client.
    Binary skill files (a template, an image) are not text guidance and are left out."""
    for p in sorted((KIT / packs.ROLES_REL).glob("*/instructions.md")):
        yield p.relative_to(KIT).as_posix(), p.read_text(encoding="utf-8")
    for skill in packs.available_skills(KIT):        # any of them can be placed, whole folder
        for rel, text in place.placed_skill_files(KIT, skill).items():
            if isinstance(text, str):
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
                held = set(place.kit_only(kit, skill))     # kept in the kit copy (design §8.7)
                files = sorted(p.relative_to(src).as_posix() for p in src.rglob("*") if p.is_file()
                               and not any(part.startswith(".") for part in p.relative_to(src).parts))
                for rel in files:                  # dotfiles (a skill's .kit-only) are never placed
                    if rel in held:
                        self.assertNotIn(f".agents/skills/{packs.PREFIX}{skill}/{rel}", wanted)
                        continue
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

    def test_playbooks_name_only_shipped_skills_by_their_placed_names(self):
        """Every skill a placed playbook names is one the kit ships, as `ai-sdlc-<name>`
        (owner decision 3, 2026-10-08). Team mode (retired in 0.4.0) is not checked."""
        shipped = set(packs.available_skills(KIT))
        unprefixed = shipped | set(packs.UNSUPPORTED_SKILLS) | set(FILES) | {"code-review"}
        name = re.compile(r"(?<![\w/.-])(ai-sdlc-)?([a-z0-9]+(?:-[a-z0-9]+)+)(?![\w/-])")
        bad = {}
        for pb in (s for s in shipped if s.startswith("playbook-")):
            _, text = place.placed_skill(KIT, pb)
            for m in name.finditer(text):
                prefixed, skill = m.group(1), m.group(2)
                if (skill not in shipped) if prefixed else (skill in unprefixed):
                    bad.setdefault(pb, set()).add(m.group(0))
            # one-word process skill names (`brainstorming`): the pattern above needs a hyphen
            for skill in (s for s in FILES if "-" not in s):
                if re.search(rf"(?<![\w/.-]){skill}(?![\w/-])", text):
                    bad.setdefault(pb, set()).add(skill)
        self.assertEqual({pb: sorted(names) for pb, names in bad.items()}, {})

    def test_all_packs_validate(self):
        self.assertEqual(packs.validate(KIT), [])

    def test_no_client_names_in_copilot_guidance(self):
        for rel, text in guidance_texts():
            with self.subTest(path=rel):
                self.assertEqual(client_names(rel, text), [])

    def test_the_brand_skill_is_the_only_exception_and_it_is_used(self):
        texts = dict(guidance_texts())
        brand = [rel for rel in texts if rel.startswith(BRAND_DIR)]
        self.assertIn(BRAND_DIR + "SKILL.md", brand)
        self.assertTrue(any(CLIENT_WORDS.search(texts[rel]) for rel in brand),
                        "the brand skill no longer names the client: drop the exception")
        # Core guidance names the skill, and only the skill.
        core = texts["roles/core/instructions.md"]
        self.assertIn(f"`{packs.PREFIX}{BRAND_SKILL}`", core)
        self.assertEqual(client_names("roles/core/instructions.md", core), [])

    def test_any_other_skill_that_names_the_client_still_fails(self):
        for rel, text in (
                (".agents/skills/ai-sdlc-drawio/SKILL.md", "Use the Frequentis colours."),
                (".agents/skills/ai-sdlc-doc-word/SKILL.md", "Make FRQ reports."),
                (".agents/skills/ai-sdlc-frq-brandbook-extra/SKILL.md", "Frequentis decks."),
                (".agents/skills/ai-sdlc-notes/frq-brandbook/x.md", "Mosaix."),
                ("roles/core/instructions.md",
                 "Use `ai-sdlc-frq-brandbook` for FRQ decks."),     # the skill name is fine, FRQ is not
                ("roles/dev/instructions.md", "the frq-brandbook-v2 skill")):
            with self.subTest(path=rel):
                self.assertNotEqual(client_names(rel, text), [])
        self.assertEqual(client_names(".agents/skills/ai-sdlc-drawio/SKILL.md",
                                      "For company branding, use `ai-sdlc-frq-brandbook`."), [])

    def test_a_placed_skill_naming_the_client_fails_the_rule_in_a_kit_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            kit = helpers.copy_kit(Path(tmp) / "kit")
            ref = kit / packs.SKILLS_REL / "drawio/references/brand.md"
            ref.write_text("Diagrams in Frequentis blue.\n", encoding="utf-8")
            hits = {rel: client_names(rel, text)
                    for skill in ("drawio", BRAND_SKILL)
                    for rel, text in place.placed_skill_files(kit, skill).items()
                    if isinstance(text, str)}
            self.assertEqual({rel for rel, h in hits.items() if h},
                             {".agents/skills/ai-sdlc-drawio/references/brand.md"})


if __name__ == "__main__":
    unittest.main()
