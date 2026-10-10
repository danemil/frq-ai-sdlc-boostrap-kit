#!/usr/bin/env python3
"""`setup.py connect --suggested`: the person's role connectors one at a time (y / s / a,
Enter skips), then one "connect another tool?" step. Skips are remembered in state.json,
so the setup summary and `connections` stop suggesting them; `connect <tool>` clears a skip.

Stdin is injected (a fake terminal); `manage.connect` is replaced by a recorder except in
the one test that runs the real connect flow against tests/fakeserver.py. No test reads
or writes the real ~/.config.
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers
from fakeserver import ConnectorTestCase
from personal import paths, state
from personal.connectors import manage, registry, store

STUB_FILE = Path(__file__).resolve().parent / "stub_connector.py"
SECRET = "suggest-S3CRET-token-91"
SETUP_ARGS = ["setup", "--name", "Ana", "--roles", "sm", "--lang", "en"]   # sm: jira, confluence


class FakeTTY(io.StringIO):
    """Typed answers, one per line, on a stdin that says it is a terminal."""

    def isatty(self):
        return True


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name).resolve()
        env = mock.patch.dict(os.environ, {"AI_SDLC_CONFIG_DIR": str(base / "cfg")})
        env.start()
        self.addCleanup(env.stop)
        self.root = helpers.make_repo(base / "repo", {"README.md": "team\n"})
        self.kit = self.root / paths.KIT_REL
        code, out = helpers.cli(self.root, helpers.copy_kit(self.root / "kit-copy"), *SETUP_ARGS)
        self.assertEqual(code, 0, out)
        self.connected = []

    def fake_connect(self, name, **kwargs):
        """Stands in for manage.connect: saves a login without asking anything."""
        self.connected.append(name)
        store.save(name, {"url": f"https://{name}.example.com", "token": SECRET})
        return 0, [f"Saved {name}."]

    def suggested(self, answers, tty=True, *argv):
        stdin = FakeTTY(answers) if tty else io.StringIO(answers)
        with mock.patch("sys.stdin", stdin), \
                mock.patch.object(manage, "connect", side_effect=self.fake_connect):
            return helpers.cli(self.root, self.kit, "connect", "--suggested", *argv)

    def skipped(self):
        return json.loads((self.root / paths.STATE_REL).read_text())["skipped_connectors"]


class TestWalk(Base):
    def test_yes_then_skip_connects_one_and_remembers_the_other(self):
        code, out = self.suggested("y\ns\n\n")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.connected, ["jira"])
        self.assertIn("Connect Jira now? [y = yes, s = skip, a = skip all the rest; "
                      "Enter = skip]", out)
        self.assertIn("Connect Confluence now?", out)
        self.assertEqual(self.skipped(), ["confluence"])
        self.assertIn("Connected: jira.", out)
        self.assertIn("Skipped: confluence.", out)
        self.assertNotIn(SECRET, out)

    def test_enter_skips(self):
        code, out = self.suggested("\n\n\n")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.connected, [])
        self.assertEqual(self.skipped(), ["confluence", "jira"])

    def test_skip_all_skips_the_rest_and_ends_without_the_other_tools_step(self):
        code, out = self.suggested("a\n")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.connected, [])
        self.assertEqual(self.skipped(), ["confluence", "jira"])
        self.assertNotIn("Connect Confluence now?", out)
        self.assertNotIn("Connect another tool?", out)

    def test_already_connected_ones_are_not_asked(self):
        store.save("jira", {"url": "https://jira.example.com", "token": SECRET})
        code, out = self.suggested("s\n\n")
        self.assertEqual(code, 0, out)
        self.assertNotIn("Connect Jira now?", out)
        self.assertIn("Jira: already connected.", out)
        self.assertEqual(self.skipped(), ["confluence"])

    def test_an_unknown_answer_asks_again(self):
        code, out = self.suggested("maybe\ny\ns\n\n")
        self.assertEqual(code, 0, out)
        self.assertIn("Please answer y, s or a.", out)
        self.assertEqual(self.connected, ["jira"])

    def test_the_other_tools_step_connects_by_name_until_enter(self):
        code, out = self.suggested("s\ns\njenkins\nnosuch\n\n")
        self.assertEqual(code, 0, out)
        self.assertIn("Connect another tool? Available: bitbucket, jama, jenkins "
                      "(type its name; Enter = done)", out)
        self.assertEqual(self.connected, ["jenkins"])
        self.assertIn("There is no tool 'nosuch' to connect here.", out)
        self.assertEqual(self.skipped(), ["confluence", "jira"])     # others are never skips

    def test_a_skipped_one_is_offered_again_and_yes_clears_the_skip(self):
        self.suggested("s\ns\n\n")
        self.assertEqual(self.skipped(), ["confluence", "jira"])
        code, out = self.suggested("y\ns\n\n")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.skipped(), ["confluence"])

    def test_end_of_input_stops_without_a_traceback_and_records_only_answers(self):
        code, out = self.suggested("s\n")                              # then EOF
        self.assertEqual(code, 0, out)
        self.assertIn("No more answers; skipping the rest for now.", out)
        self.assertEqual(self.skipped(), ["jira"])                    # confluence not asked
        self.assertNotIn("Traceback", out)

    def test_no_terminal_asks_nothing_and_changes_nothing(self):
        before = (self.root / paths.STATE_REL).read_bytes()
        code, out = self.suggested("y\ny\n", False)
        self.assertEqual(code, 2, out)                 # refused, like connect <name> without one
        self.assertEqual(self.connected, [])
        self.assertIn("runs only in your own terminal", out)
        self.assertIn("python3 .ai-sdlc/kit/setup.py connect --suggested", out)
        self.assertEqual((self.root / paths.STATE_REL).read_bytes(), before)

    def test_needs_the_kit_set_up(self):
        with tempfile.TemporaryDirectory() as other:
            with mock.patch("sys.stdin", FakeTTY("")):
                code, out = helpers.cli(Path(other), self.kit, "connect", "--suggested")
        self.assertEqual(code, 2)
        self.assertIn("not set up", out)

    def test_name_and_suggested_together_is_a_plain_error(self):
        code, out = helpers.cli(self.root, self.kit, "connect", "jira", "--suggested")
        self.assertEqual(code, 2)
        self.assertIn("connect <connector> or connect --suggested", out)
        code, out = helpers.cli(self.root, self.kit, "connect")
        self.assertEqual(code, 2)
        self.assertIn("connect <connector> or connect --suggested", out)

    def test_git_still_sees_nothing(self):
        self.suggested("y\ns\n\n")
        self.assertEqual(helpers.git(self.root, "status", "--porcelain").stdout, "")


class TestSkipsAreRespected(Base):
    def test_the_summary_marks_skipped_ones_and_stops_suggesting_them(self):
        self.suggested("s\n\n\n")                                      # skip jira, confluence
        code, out = helpers.cli(self.root, self.kit, "change")
        self.assertEqual(code, 0, out)
        self.assertIn("- Connectors for your roles: jira (skipped), confluence (skipped)\n", out)
        self.assertNotIn("say 'connect", out)

    def test_the_summary_still_suggests_the_ones_not_skipped(self):
        self.suggested("s\n")                                          # jira, then EOF
        code, out = helpers.cli(self.root, self.kit, "change")
        self.assertIn("- Connectors for your roles: jira (skipped), confluence "
                      "(say 'connect confluence')", out)

    def test_connections_marks_skipped_ones(self):
        self.suggested("s\n")
        code, out = helpers.cli(self.root, self.kit, "connections")
        self.assertEqual(code, 0, out)
        self.assertIn("- jira: not connected, skipped (python3 .ai-sdlc/kit/setup.py connect "
                      "jira when you want it)", out)
        self.assertIn("- confluence: not connected (python3 .ai-sdlc/kit/setup.py connect "
                      "confluence)", out)

    def test_an_explicit_connect_clears_that_skip_only(self):
        self.suggested("s\ns\n\n")
        with mock.patch.object(manage, "connect", side_effect=self.fake_connect):
            code, out = helpers.cli(self.root, self.kit, "connect", "jira")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.skipped(), ["confluence"])

    def test_a_refused_connect_or_a_test_keeps_the_skip(self):
        self.suggested("s\n")
        with mock.patch.object(manage, "connect", return_value=(2, ["Stopped."])):
            helpers.cli(self.root, self.kit, "connect", "jira")
            helpers.cli(self.root, self.kit, "connect", "jira", "--test")
        self.assertEqual(self.skipped(), ["jira"])

    def test_change_keeps_the_skips(self):
        self.suggested("s\n")
        helpers.cli(self.root, self.kit, "change", "--roles", "po")
        self.assertEqual(self.skipped(), ["jira"])

    def test_update_keeps_known_skips_and_drops_unknown_names(self):
        self.suggested("s\n")
        st = state.load(self.root)
        st["skipped_connectors"] = ["gone-tool", "jira"]
        state.save(self.root, st)
        newer = helpers.copy_kit(self.root / "kit-newer")
        (newer / "VERSION").write_text("9.9.9\n")
        code, out = helpers.cli(self.root, newer, "update")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.skipped(), ["jira"])

    def test_remove_still_leaves_the_repo_as_it_was(self):
        self.suggested("s\n")
        code, out = helpers.cli(self.root, self.kit, "remove", "--yes")
        self.assertEqual(code, 0, out)
        self.assertFalse((self.root / paths.STATE_REL).exists())

    def test_an_old_state_file_without_the_field_still_loads(self):
        path = self.root / paths.STATE_REL
        doc = json.loads(path.read_text())
        doc.pop("skipped_connectors", None)
        path.write_text(json.dumps(doc))
        self.assertEqual(state.load(self.root)["skipped_connectors"], [])
        code, out = helpers.cli(self.root, self.kit, "change")
        self.assertEqual(code, 0, out)
        self.assertIn("(say 'connect jira')", out)
        code, out = self.suggested("s\n")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.skipped(), ["jira"])

    def test_new_state_has_an_empty_skip_list(self):
        self.assertEqual(state.new("0.5.0")["skipped_connectors"], [])


STUB_PROMPT = ("Connect Stub Tool now? It fits this repo: this repo is analysed by the stub tool. "
               "[y = yes, s = skip, a = skip all the rest; Enter = skip]: ")


class TestRepoTools(Base):
    """0.10.0: the repo's tool suggestions come after the role tools, each with its reason;
    a skipped one is declined (connect:<name>), not put in skipped_connectors."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name).resolve()
        env = mock.patch.dict(os.environ, {"AI_SDLC_CONFIG_DIR": str(base / "cfg")})
        env.start()
        self.addCleanup(env.stop)
        self.root = helpers.make_repo(base / "repo", {"sonar-project.properties": "x=1\n"})
        self.kit = self.root / paths.KIT_REL
        copy = helpers.kit_with_connector_rule(self.root / "kit-copy")
        with helpers.stubtool_registered(self.kit):
            code, out = helpers.cli(self.root, copy, "setup", "--name", "Ana", "--roles", "dev",
                                    "--lang", "en")    # dev: bitbucket, jira, jenkins
        self.assertEqual(code, 0, out)
        self.connected = []

    def suggested(self, answers, tty=True, *argv):
        with helpers.stubtool_registered(self.kit):
            return super().suggested(answers, tty, *argv)

    def declined(self):
        return json.loads((self.root / paths.STATE_REL).read_text())["declined_recommendations"]

    def test_repo_tools_come_after_role_tools_with_their_reason(self):
        code, out = self.suggested("s\ns\ns\ny\n\n")
        self.assertEqual(code, 0, out)
        self.assertIn(STUB_PROMPT, out)
        self.assertGreater(out.index(STUB_PROMPT), out.index("Connect Jenkins now?"))
        self.assertEqual(self.connected, ["stubtool"])
        self.assertEqual(self.declined(), [])
        self.assertEqual(self.skipped(), ["bitbucket", "jenkins", "jira"])

    def test_a_skipped_repo_tool_is_declined(self):
        code, out = self.suggested("s\ns\ns\ns\n\n")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.declined(), ["connect:stubtool"])
        self.assertNotIn("stubtool", self.skipped())
        self.assertEqual(self.skipped(), ["bitbucket", "jenkins", "jira"])
        self.assertIn('Not now for this repo: stubtool. Say "recommend skills" to see them again.',
                      out)

    def test_a_skips_the_rest_of_both_lists(self):
        code, out = self.suggested("a\n")
        self.assertEqual(code, 0, out)
        self.assertNotIn(STUB_PROMPT, out)
        self.assertEqual(self.skipped(), ["bitbucket", "jenkins", "jira"])
        self.assertEqual(self.declined(), ["connect:stubtool"])

    def test_a_at_a_repo_tool(self):
        code, out = self.suggested("s\ns\ns\na\n")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.declined(), ["connect:stubtool"])
        self.assertNotIn("Connect another tool?", out)

    def test_the_other_tools_step_leaves_out_the_repo_tools(self):
        code, out = self.suggested("s\ns\ns\ns\n\n")
        self.assertIn("Connect another tool? Available: confluence, jama (type its name", out)

    def test_end_of_input_records_only_answers(self):
        code, out = self.suggested("s\ns\ns\n")             # EOF at the repo tool
        self.assertEqual(code, 0, out)
        self.assertEqual(self.declined(), [])

    def test_no_terminal_changes_nothing(self):
        before = (self.root / paths.STATE_REL).read_bytes()
        code, out = self.suggested("y\ny\n", False)
        self.assertEqual(code, 2, out)
        self.assertIn("runs only in your own terminal", out)
        self.assertEqual((self.root / paths.STATE_REL).read_bytes(), before)

    def test_a_declined_one_is_not_offered_and_connect_clears_it(self):
        self.suggested("s\ns\ns\ns\n\n")
        code, out = self.suggested("s\ns\ns\n\n")
        self.assertNotIn(STUB_PROMPT, out)
        with helpers.stubtool_registered(self.kit), \
                mock.patch.object(manage, "connect", side_effect=self.fake_connect):
            code, out = helpers.cli(self.root, self.kit, "connect", "stubtool")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.declined(), [])


class TestRealConnectFlow(ConnectorTestCase):
    """The walk hands `y` to the very same connect flow: prompts, hidden secret, save, test."""

    def test_yes_runs_connect_with_the_same_prompts_and_saves(self):
        srv = self.server({"/api/me": {"login": "ana", "name": "Ana Pop"}})
        connectors = registry.discover(extra=[STUB_FILE])
        queue, shown = ["y", srv.url, "", ""], []   # URL, user, CA bundle

        def ask(prompt):
            shown.append(prompt)
            if not queue:
                raise EOFError
            return queue.pop(0)

        def ask_secret(prompt):
            shown.append(prompt)
            return SECRET

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code, lines, result = manage.suggest(["stub_connector"], connectors=connectors,
                                                 isatty=True, ask=ask, ask_secret=ask_secret,
                                                 say=shown.append)
        everything = "\n".join(shown + lines) + out.getvalue()
        self.assertEqual(code, 0, everything)
        self.assertEqual(result["connected"], ["stub_connector"], everything)
        self.assertIn("Stub URL: ", shown)
        self.assertIn("Token: ", shown)
        self.assertIn("OK: signed in to 127.0.0.1 as Ana Pop.", everything)
        self.assertEqual(store.read_file("stub_connector")["values"],
                         {"url": srv.url, "token": SECRET})
        self.assertNotIn(SECRET, everything)

    def test_end_of_input_inside_connect_stops_plainly_and_saves_nothing(self):
        connectors = registry.discover(extra=[STUB_FILE])
        queue = ["y", "https://stub.example.com"]

        def ask(prompt):
            if not queue:
                raise EOFError
            return queue.pop(0)

        shown = []
        code, lines, result = manage.suggest(["stub_connector"], connectors=connectors,
                                             isatty=True, ask=ask, ask_secret=ask,
                                             say=shown.append)
        self.assertEqual((code, result), (0, {"connected": [], "skipped": [], "declined": []}))
        self.assertIn("Stopped connecting Stub. Nothing more was saved.", shown)
        self.assertFalse(store.file_for("stub_connector").exists())


class TestSubprocess(Base):
    def test_without_a_terminal_the_real_cli_does_not_hang(self):
        r = subprocess.run([sys.executable, str(self.kit / "setup.py"), "connect", "--suggested"],
                           cwd=self.root, stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=60)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("runs only in your own terminal", r.stdout)
        self.assertNotIn("Traceback", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
