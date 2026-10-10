#!/usr/bin/env python3
"""Role packs: loading, combining several roles, validation, and the core pack."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import packs

SKILL = "---\nname: {name}\ndescription: Use for {name}.\n---\n\nAbout <PROJECT_NAME>.\n"


def pack(pid, skills=(), git="git-native", rituals="status", source="docs/src.md"):
    return {"id": pid, "label": pid.upper(), "source": source, "skills": list(skills),
            "defaults": {"git_comfort": git, "rituals": rituals}, "connectors": []}


def fake_kit(root, extra=None):
    """A minimal kit: core + po + dev packs, four library skills, two connector modules."""
    root = Path(root)
    (root / "docs").mkdir(parents=True)
    (root / "docs/src.md").write_text("source\n")
    conn = root / packs.CONNECTORS_REL
    conn.mkdir(parents=True)
    for name in ("jira", "jenkins", "store", "_private"):   # store, _private: not connectors
        (conn / f"{name}.py").write_text("")
    for name in ("playbook-product", "playbook-dev", "skill-creator", "git-verbs"):
        d = root / packs.SKILLS_REL / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(SKILL.format(name=name))
    roles = {"core": pack("core", git="git-native", rituals="none"),
             "po": pack("po", ["playbook-product"], git="hidden"),
             "dev": pack("dev", ["playbook-dev"], git="git-native")}
    roles.update(extra or {})
    for pid, data in roles.items():
        d = root / packs.ROLES_REL / pid
        d.mkdir(parents=True)
        (d / "role.json").write_text(json.dumps(data))
        (d / "instructions.md").write_text("Say $name in $language.\n" if pid == "core"
                                           else f"# {pid}\n")
    return root


def choices(**kw):
    base = {"name": "Ana", "roles": [], "lang": "en", "git_comfort": None,
            "rituals": None, "add_skills": [], "drop_skills": []}
    base.update(kw)
    return base


class TestCombine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kit = fake_kit(self.tmp.name)
        self.packs = packs.load(self.kit)

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_reads_role_json_and_instructions(self):
        self.assertEqual(sorted(self.packs), ["core", "dev", "po"])
        self.assertEqual(self.packs["po"]["instructions"], "# po\n")
        self.assertEqual(packs.selectable(self.packs), ["dev", "po"])

    def test_skills_are_a_union_then_your_own_add_and_drop(self):
        got = packs.combine(self.packs, choices(roles=["po", "dev"], add_skills=["skill-creator"],
                                                drop_skills=["playbook-dev"]))
        self.assertEqual(got["skills"], ["playbook-product", "skill-creator"])

    def test_the_more_guided_default_wins(self):
        got = packs.combine(self.packs, choices(roles=["dev", "po"]))
        self.assertEqual((got["git_comfort"], got["rituals"]), ("hidden", "status"))

    def test_an_explicit_choice_beats_the_defaults(self):
        got = packs.combine(self.packs, choices(roles=["po"], git_comfort="git-native",
                                                rituals="none"))
        self.assertEqual((got["git_comfort"], got["rituals"]), ("git-native", "none"))

    def test_core_alone_gives_the_core_defaults(self):
        got = packs.combine(self.packs, choices())
        self.assertEqual(got, {"skills": [], "git_comfort": "git-native", "rituals": "none"})

    def test_unsupported_skills_are_not_available(self):
        self.assertEqual(packs.available_skills(self.kit),
                         ["playbook-dev", "playbook-product", "skill-creator"])

    def test_prefixed_skill_renames_and_fills_the_project_name(self):
        text = packs.prefixed_skill(SKILL.format(name="playbook-dev"), "playbook-dev")
        self.assertTrue(text.startswith("---\nname: ai-sdlc-playbook-dev\n"))
        self.assertIn("About this project.", text)
        with self.assertRaises(ValueError):
            packs.prefixed_skill("# no frontmatter\n", "x")


class TestValidate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def errors(self, **extra):
        return packs.validate(fake_kit(tempfile.mkdtemp(dir=self.tmp.name), extra))

    def test_the_fixture_is_valid(self):
        self.assertEqual(self.errors(), [])

    def test_missing_source_and_unknown_skill(self):
        errs = self.errors(qa=pack("qa", ["nope"], source="docs/gone.md"))
        self.assertIn("roles/qa/role.json: source 'docs/gone.md' does not exist in the kit", errs)
        self.assertIn(f"roles/qa/role.json: skill 'nope' is not in {packs.SKILLS_REL}", errs)

    def test_unsupported_skill_is_rejected(self):
        errs = self.errors(qa=pack("qa", ["git-verbs"]))
        self.assertTrue(any("'git-verbs' cannot be placed" in e for e in errs), errs)

    def test_core_may_have_skills(self):
        self.assertEqual(self.errors(core=pack("core", ["skill-creator"], rituals="none")), [])

    def test_personal_names_are_reserved_for_the_person(self):
        errs = self.errors(personal=pack("personal"))
        self.assertTrue(any("id 'personal' is reserved" in e for e in errs), errs)
        errs = self.errors(qa=pack("qa", ["personal-notes"]))
        self.assertTrue(any("names starting personal- are the person's own" in e for e in errs), errs)

    def test_bad_defaults_connectors_and_keys(self):
        bad = pack("qa", git="sometimes")
        bad["connectors"] = ["jira", "nope"]
        bad["extra"] = 1
        errs = self.errors(qa=bad)
        self.assertEqual(errs, ["roles/qa/role.json: unknown key: extra"])
        del bad["extra"]
        errs = self.errors(qa=bad)
        self.assertTrue(any("defaults must be" in e for e in errs), errs)
        self.assertIn(f"roles/qa/role.json: connector 'nope' is not in {packs.CONNECTORS_REL} "
                      "(known: jenkins, jira)", errs)

    def test_connectors_are_known_connector_names(self):
        ok = pack("qa")
        ok["connectors"] = ["jira", "jenkins"]
        self.assertEqual(self.errors(qa=ok), [])
        for value, words in ((["store"], "connector 'store' is not in"),
                             (["_private"], "connector '_private' is not in"),
                             (["jira", "jira"], "must not repeat"),
                             ("jira", "must be a list of connector names"),
                             ([1], "must be a list of connector names")):
            with self.subTest(value=value):
                bad = pack("qa")
                bad["connectors"] = value
                errs = self.errors(qa=bad)
                self.assertTrue(any(words in e for e in errs), errs)

    def test_role_connectors_are_the_union_in_role_order(self):
        all_packs = {"a": {"connectors": ["jira", "jenkins"]}, "b": {"connectors": ["jama", "jira"]}}
        self.assertEqual(packs.role_connectors(all_packs, ["a", "b"]), ["jira", "jenkins", "jama"])
        self.assertEqual(packs.role_connectors(all_packs, []), [])

    def test_instructions_frontmatter_and_length(self):
        kit = fake_kit(self.tmp.name)
        md = kit / "roles/po/instructions.md"
        md.write_text("---\napplyTo: '**'\n---\nx\n")
        self.assertIn("roles/po/role.json: instructions.md must not have frontmatter: "
                      "setup adds applyTo", packs.validate(kit))
        md.write_text("line\n" * (packs.MAX_LINES + 1))
        self.assertTrue(any("keep it to" in e for e in packs.validate(kit)))

    def test_core_is_required_and_its_placeholders_checked(self):
        kit = fake_kit(self.tmp.name)
        (kit / "roles/core/instructions.md").write_text("Hello $nobody\n")
        self.assertTrue(any("placeholder" in e for e in packs.validate(kit)))
        (kit / "roles/core/role.json").unlink()
        self.assertIn("roles/core/role.json is missing: the core pack is required",
                      packs.validate(kit))


class TestRealKit(unittest.TestCase):
    def test_the_kit_packs_validate(self):
        self.assertEqual(packs.validate(helpers.KIT), [])

    def test_core_file_has_the_language_line_and_the_gate(self):
        all_packs = packs.load(helpers.KIT)
        c = choices(lang="de")
        rel, text = packs.instructions_file(all_packs["core"], packs.core_values(
            all_packs, c, packs.combine(all_packs, c)))
        self.assertEqual(rel, ".github/instructions/ai-sdlc-core.instructions.md")
        self.assertTrue(text.startswith("---\napplyTo: '**'\n---\n"))
        self.assertIn("Always answer in German (Deutsch)", text)
        self.assertIn("If `.ai-sdlc/USER.md` is missing, do the onboarding first", text)
        self.assertIn("A human validates everything", text)
        self.assertIn("If a team rule in this repo contradicts a kit rule, follow the team rule "
                      "and mention the difference once.", text)
        for rituals in packs.RITUALS:  # the session-start check is always on (option 2)
            r = choices(lang="de", rituals=rituals)
            _, text = packs.instructions_file(all_packs["core"], packs.core_values(
                all_packs, r, packs.combine(all_packs, r)))
            self.assertIn("At the start of each session, run `python3 .ai-sdlc/kit/setup.py "
                          "check --quiet` once", text, rituals)
            self.assertIn(packs.RITUAL_TEXT[rituals], text, rituals)
            self.assertNotIn("check --quiet", packs.RITUAL_TEXT[rituals], rituals)

    def test_the_recommend_file_validates(self):
        from personal import recommend
        self.assertEqual(recommend.validate(helpers.KIT), [])

    @unittest.skipUnless(subprocess.run([sys.executable, "-c", "import yaml"]).returncode == 0,
                         "needs PyYAML")
    def test_validator_cli_passes(self):
        r = subprocess.run([sys.executable, str(helpers.KIT / "scripts/personal/validate_packs.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ok", r.stdout)


if __name__ == "__main__":
    unittest.main()
