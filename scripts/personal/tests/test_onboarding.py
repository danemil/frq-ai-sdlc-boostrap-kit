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


def core_text():
    return (helpers.KIT / "roles/core/instructions.md").read_text(encoding="utf-8")


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
                      "Check the kit", "Remove the kit", "Connect a tool", "Recommend skills"):
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

    def test_a_pasted_token_is_never_quoted_back(self):
        text = section("Connect a tool")
        self.assertIn('never quote it: say "the token you pasted"', text)
        self.assertIn("revoke it now", text)

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
        step11 = section("Do the onboarding").split("\n11. ", 1)[1]
        self.assertLess(step11.index("Wait for the answer."), step11.index("connect --suggested"))
        self.assertIn("Only if they say yes", step11)

    def step(self, n):
        return section("Do the onboarding").split(f"\n{n}. ", 1)[1].split(f"\n{n + 1}. ", 1)[0]

    def test_the_onboarding_offers_skill_suggestions_once(self):
        onboarding = section("Do the onboarding")
        step8 = self.step(8)
        for needed in ("`python3 .ai-sdlc/kit/setup.py recommend`", "This is an offer, not a fourth question.",
                       "You can take all, some or none.", "recommend --decline all",
                       "Never apply a suggestion they did not choose.", "Wait for the answer."):
            self.assertIn(needed, step8)
        self.assertLess(onboarding.index("Mark them as seen"), onboarding.index("Suggest skills for this repo"))
        self.assertLess(onboarding.index("Suggest skills for this repo"), onboarding.index("**Close.**"))

    # 0.10.0 (design 2026-10-10 §6.2): tools suggested from the repo's files.
    def test_close_names_tools_for_this_repo(self):
        step10 = self.step(10)
        self.assertIn("Tools to connect for this repo", step10)
        self.assertIn("with its reason", step10)
        self.assertLess(step10.index("Connectors for your roles"),
                        step10.index("Tools to connect for this repo"))

    def test_not_now_records_nothing(self):
        """Owner decision 2026-10-10 (design §12 item 5): "not now" in step 11 records
        nothing, for the repo tools as for the role tools; they are offered again."""
        step11 = section("Do the onboarding").split("\n11. ", 1)[1]
        self.assertNotIn("--decline", step11)
        self.assertIn("records nothing", step11)
        self.assertIn("offered again next time", step11)
        self.assertIn("Tools to connect for this repo", step11)
        self.assertIn("say *connect <tool>* at any time", step11)

    def test_step_8_decline_all_is_skills_only(self):
        self.assertIn("`python3 .ai-sdlc/kit/setup.py recommend --decline all` (this declines "
                      "skills only; tools come later)", self.step(8))

    def test_recommend_skills_relays_tools(self):
        text = section("Recommend skills")
        for needed in ("Tools to connect for this repo", "in their own terminal",
                       "`python3 .ai-sdlc/kit/setup.py recommend --decline <tool>`",
                       "`python3 .ai-sdlc/kit/setup.py connect <name>`"):
            self.assertIn(needed, text)
        self.assertIn("never by you", text)

    def test_connect_a_tool_has_the_token_hints(self):
        text = section("Connect a tool")
        for needed in ("SonarQube: a user token", "Black Duck: an API token",
                       "Artifactory: an access or identity token"):
            self.assertIn(needed, text)

    def test_the_onboarding_offers_the_other_skills_once(self):
        step9 = self.step(9)
        for needed in ("`python3 .ai-sdlc/kit/setup.py recommend --all`", "'None' is fine.", "--add-skill",
                       "Never add a skill they did not pick.", "nothing is stored", "wait for the answer"):
            self.assertIn(needed, step9)
        self.assertLess(section("Do the onboarding").index("Other skills (optional)"),
                        section("Do the onboarding").index("**Close.**"))

    # --- Copilot re-test round 2 (2026-10-10) ------------------------------------------

    COPY = "copy each line exactly as printed: the skill name and its summary"

    def test_declines_go_by_skill_name(self):
        step8 = self.step(8)
        self.assertIn("recommend --decline <the skill names they did not take", step8)
        self.assertIn("--decline javafx,java-junit", step8)

    def test_suggestions_and_other_skills_are_copied_line_by_line(self):
        for text in (self.step(8), self.step(9), section("Recommend skills")):
            self.assertIn(self.COPY, text.replace("Copy each line", "copy each line"))

    def test_step_9_stops_before_the_close(self):
        self.assertIn("Stop and wait for the answer before step 10.", self.step(9))

    def test_the_seen_question_is_asked_even_without_a_contradiction(self):
        step7 = self.step(7)
        self.assertIn("even when there was no contradiction", step7)
        self.assertIn('"Shall I mark these as seen?', step7)

    def test_one_question_even_when_no_answer_can_come(self):
        """Re-test round 2: in a one-shot run Copilot listed every later question in one message."""
        head = DOC.split("## Do the onboarding", 1)[0]
        self.assertIn("Also when nobody can answer in this session, ask only the next question and stop", head)
        self.assertIn("never list the later questions or offers", head)

    def test_check_explains_a_kept_edit(self):
        self.assertIn("`kept-edit:`", section("Check the kit"))

    def test_an_update_reads_the_onboarding_of_the_new_copy(self):
        update = section("Update the kit")
        self.assertIn("read the `ONBOARDING.md` in that folder", update)
        self.assertIn("not the one in `.ai-sdlc/kit`", update)
        self.assertIn("read the `ONBOARDING.md` in the newer copy", core_text())

    def test_recommend_skills_covers_the_other_skills(self):
        text = section("Recommend skills")
        for needed in ('"recommend skills"', '"show me the other skills"', "recommend --all",
                       "Declined earlier", "one question", "Never apply a suggestion they did not choose."):
            self.assertIn(needed, text)

    def test_update_offers_new_suggestions(self):
        self.assertIn("Skill suggestions for this repo", section("Update the kit"))

    def test_check_names_a_missing_kit_copy_file(self):
        self.assertIn("under `.ai-sdlc/kit`", section("Check the kit"))

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
