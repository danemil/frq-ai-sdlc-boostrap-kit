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

    def test_python_floor_matches_setup_py(self):
        self.assertIn("3.9 or newer", DOC)
        self.assertIn("sys.version_info < (3, 9)", (helpers.KIT / "setup.py").read_text())

    def test_the_core_instructions_point_here(self):
        core = (helpers.KIT / "roles/core/instructions.md").read_text()
        self.assertIn("`.ai-sdlc/kit/ONBOARDING.md`", core)

    def test_the_retired_template_onboarding_points_to_the_kit_root(self):
        text = (helpers.KIT / "template/ONBOARDING.md").read_text()
        self.assertTrue("follow the `ONBOARDING.md` at the kit's top folder" in text,
                        "template/ONBOARDING.md does not point to the kit-root ONBOARDING.md")


if __name__ == "__main__":
    unittest.main()
