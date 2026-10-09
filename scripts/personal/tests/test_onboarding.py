#!/usr/bin/env python3
"""ONBOARDING.md names only real setup.py commands and flags, and offers every role and language."""
import argparse
import re
import sys
import unittest

import helpers
from personal import packs

sys.path.insert(0, str(helpers.KIT))
import setup  # noqa: E402  the kit-root setup.py

DOC = (helpers.KIT / "ONBOARDING.md").read_text(encoding="utf-8")
CALL = re.compile(r"setup\.py ([a-z]+)([^`\n]*)")
FLAG = re.compile(r"--[a-z][a-z-]*")


def subcommands() -> dict:
    """{command: {its option strings}} straight from setup.py's argparse parser."""
    action = next(a for a in setup.parser()._actions
                  if isinstance(a, argparse._SubParsersAction))
    return {name: set(p._option_string_actions) for name, p in action.choices.items()}


def section(title: str) -> str:
    return DOC.split(f"\n## {title}\n", 1)[1].split("\n## ", 1)[0]


class TestOnboarding(unittest.TestCase):
    def test_every_command_named_is_real_and_its_flags_belong_to_it(self):
        real = subcommands()
        calls = CALL.findall(DOC)
        self.assertGreater(len(calls), 5)
        for command, tail in calls:
            with self.subTest(call=f"setup.py {command}{tail}"):
                self.assertIn(command, real)
                self.assertLessEqual(set(FLAG.findall(tail)), real[command])

    def test_the_change_table_uses_change_flags_only(self):
        flags = set(FLAG.findall(section("Change my preferences")))
        self.assertTrue(flags)
        self.assertLessEqual(flags, subcommands()["change"])

    def test_every_role_and_language_is_offered(self):
        for pid in packs.selectable(packs.load(helpers.KIT)):
            self.assertIn(f"`{pid}`", section("Do the onboarding"), pid)
        for code in packs.LANGUAGES:
            self.assertIn(f"`{code}`", section("Do the onboarding"), code)

    def test_every_spoken_request_has_a_section(self):
        for title in ("Do the onboarding", "Change my preferences", "Update the kit",
                      "Check the kit", "Remove the kit", "Connect a tool"):
            self.assertIn(f"\n## {title}\n", DOC)

    def test_connecting_is_left_to_the_person(self):
        onboarding, connect = section("Do the onboarding"), section("Connect a tool")
        self.assertIn("say *connect Jira* (etc.) whenever you're ready", onboarding)
        self.assertIn("Do not ask for a URL, login or token now.", onboarding)
        self.assertIn("**themselves, in their own terminal**", connect)
        self.assertIn("`python3 .ai-sdlc/kit/setup.py connect <name>`", connect)
        self.assertIn("`python3 .ai-sdlc/kit/setup.py connect <name> --test`", connect)
        self.assertIn("revoke it", connect)
        from personal.connectors import registry
        for name in registry.names():
            self.assertIn(f"`{name}`", connect, name)

    def test_the_onboarding_offers_connect_suggested_once_and_takes_not_now(self):
        onboarding = section("Do the onboarding")
        self.assertIn("`python3 .ai-sdlc/kit/setup.py connect --suggested`", onboarding)
        self.assertIn("not a fourth question", onboarding)
        self.assertIn('If they say "not now" (or no), skip this step', onboarding)
        self.assertIn("Do not run it yourself", onboarding)
        self.assertIn("**Ask three questions,**", onboarding)

    def test_remove_and_disconnect_get_yes_only_after_the_person_says_yes(self):
        remove, connect = section("Remove the kit"), section("Connect a tool")
        self.assertIn("`python3 .ai-sdlc/kit/setup.py remove`, without `--yes`", remove)
        self.assertIn("**Only after they say yes,** run `python3 .ai-sdlc/kit/setup.py remove --yes`",
                      remove)
        self.assertIn("Never run `remove --yes` on your own.", remove)
        self.assertIn("Only after they say yes, run `python3 .ai-sdlc/kit/setup.py disconnect "
                      "<name> --yes`", connect)

    def test_onboarding_again_in_a_set_up_repo_redoes_it(self):
        onboarding = section("Do the onboarding")
        step0 = onboarding.split("\n1. ", 1)[0]
        self.assertIn("If `.ai-sdlc/USER.md` exists", step0)
        self.assertIn("Do not say it is already done", step0)
        self.assertIn("`python3 .ai-sdlc/kit/setup.py check`", step0)
        self.assertIn("`kit-copy:`", step0)
        self.assertIn("Shall I update the kit first?", step0)
        self.assertIn("say who it is set up for now", step0)
        self.assertIn("Skip steps 1 and 2 (no `--protect-only`)", step0)

    def test_the_three_questions_come_one_at_a_time_without_defaults(self):
        onboarding = section("Do the onboarding")
        self.assertIn("Never put two questions in one message.", onboarding)
        self.assertIn("Do not offer defaults or suggested answers", onboarding)
        self.assertIn("Never invent an answer or a default", DOC)

    def test_warnings_are_marked_seen_only_after_a_yes(self):
        onboarding = section("Do the onboarding")
        self.assertIn('"Shall I mark these as seen?', onboarding)
        self.assertIn("Only after a yes, run `python3 .ai-sdlc/kit/setup.py ack <warning-id>`",
                      onboarding)

    def test_connect_suggested_is_given_only_after_a_yes(self):
        step9 = section("Do the onboarding").split("\n9. ", 1)[1]
        self.assertLess(step9.index("Wait for the answer."), step9.index("connect --suggested"))
        self.assertIn("Only if they say yes", step9)

    def test_update_names_where_to_get_the_kit(self):
        # The address itself names the client, so it stays in README.md (the client-name rule
        # for Copilot guidance, test_roles); ONBOARDING sends Copilot there for it.
        update = section("Update the kit")
        self.assertIn('section "Get the latest version from GitHub"', update)
        self.assertIn("**Releases**", update)
        readme = (helpers.KIT / "README.md").read_text(encoding="utf-8")
        self.assertIn("### Get the latest version from GitHub", readme)
        self.assertIn("https://github.com/danemil/frq-ai-sdlc-boostrap-kit", readme)
        self.assertNotIn("rsync", DOC)

    def test_this_file_says_it_is_the_one_next_to_setup_py(self):
        self.assertIn("the `ONBOARDING.md` next to `setup.py`", DOC)

    def test_python_floor_matches_setup_py(self):
        self.assertIn("3.9 or newer", DOC)
        self.assertIn("sys.version_info < (3, 9)", (helpers.KIT / "setup.py").read_text())

    def test_the_core_instructions_point_here(self):
        core = (helpers.KIT / "roles/core/instructions.md").read_text()
        self.assertIn("`.ai-sdlc/kit/ONBOARDING.md`", core)

    def test_the_retired_template_onboarding_is_named_so_and_points_to_the_kit_root(self):
        # Only one file in the kit is named ONBOARDING.md, so a file search finds this one.
        found = sorted(p.relative_to(helpers.KIT).as_posix()
                       for p in helpers.KIT.rglob("ONBOARDING.md")
                       if not {".git", ".claude"} & set(p.relative_to(helpers.KIT).parts))
        self.assertEqual(found, ["ONBOARDING.md"])
        for rel in ("template/ONBOARDING.retired.md", "template/docs/onboarding/README.md"):
            text = (helpers.KIT / rel).read_text()
            self.assertIn("follow the `ONBOARDING.md` next to `setup.py`, at the kit's top folder",
                          text, rel)


if __name__ == "__main__":
    unittest.main()
