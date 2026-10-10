#!/usr/bin/env python3
"""Skill suggestions from the repo's files, and the list of other skills (design 2026-10-09 §5,
plan Tasks 16 and 17).

The engine (recommend.py) reads the repo through the kit's own detect_stack.py, applies the
rules in roles/recommend.json and never changes anything. The `recommend` command prints the
suggestions (and, with --all, every other skill), records declined ones in state.json, and
setup, update and a roles change mention open suggestions in one line.
"""
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers
from personal import packs, paths, recommend, state

KIT = helpers.KIT
JAVAFX_POM = """<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId><artifactId>desk</artifactId><version>1.0</version>
  <dependencies>
    <dependency><groupId>org.openjfx</groupId><artifactId>javafx-controls</artifactId><version>21.0.5</version></dependency>
  </dependencies>
  <build><plugins>
    <plugin><groupId>org.sonarsource.scanner.maven</groupId><artifactId>sonar-maven-plugin</artifactId><version>4.0.0.4121</version></plugin>
  </plugins></build>
</project>
"""
PLAIN_POM = "<project><modelVersion>4.0.0</modelVersion></project>\n"
JAVAFX_DEV = ["add:110-java-maven-best-practices", "add:java-code-review", "add:java-junit",
              "add:javafx", "add:maven-via-artifactory", "add:sonarqube-findings"]


def choices(roles, **kw):
    c = state.new("0")["choices"]
    c.update(name="Ana", roles=list(roles), **kw)
    return c


def st_for(roles, declined=(), **kw):
    st = state.new("0")
    st["choices"] = choices(roles, **kw)
    st["declined_recommendations"] = list(declined)
    return st


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.packs = packs.load(KIT)

    def tearDown(self):
        self.tmp.cleanup()

    def repo(self, files, name="repo"):
        return helpers.make_repo(self.base / name, files)

    def ids(self, root, roles, kit=KIT, all_packs=None, **kw):
        st = st_for(roles, **kw)
        return [i["id"] for i in recommend.compute(kit, root, st, all_packs or self.packs)]


class TestSignals(Base):
    def test_each_signal(self):
        cases = {
            "maven": ({"pom.xml": PLAIN_POM}, {"maven", "java", "code"}),
            "gradle": ({"build.gradle": "plugins { id 'java' }\n"}, {"java", "code"}),
            "java file": ({"src/App.java": "class App {}\n"}, {"java", "code"}),
            "javafx pom": ({"pom.xml": JAVAFX_POM}, {"maven", "java", "javafx", "sonar", "code"}),
            "javafx module-info": ({"src/main/java/module-info.java": "module app { requires javafx.controls; }\n"},
                                   {"java", "javafx", "code"}),
            "fxml": ({"src/main/resources/main.fxml": "<VBox/>\n"}, {"javafx"}),
            "go": ({"go.mod": "module x\n\ngo 1.23\n"}, {"go", "code"}),
            "node": ({"package.json": "{}\n"}, {"node", "code"}),
            "jest": ({"package.json": '{"devDependencies": {"jest": "^29.7.0"}}\n'}, {"node", "jest", "code"}),
            "jest config": ({"jest.config.js": "module.exports = {};\n"}, {"jest"}),
            "react": ({"package.json": '{"dependencies": {"react": "^18.3.1"}}\n'}, {"node", "react", "web", "code"}),
            "web": ({"public/index.html": "<!doctype html>\n"}, {"web"}),
            "sonar": ({"sonar-project.properties": "sonar.projectKey=x\n"}, {"sonar"}),
            "blackduck": ({"Jenkinsfile": "sh 'bash detect.sh --blackduck.url=x'\n"}, {"blackduck"}),
            "pyproject": ({"pyproject.toml": "[project]\nname = 'x'\n"}, {"python", "code"}),
            "requirements": ({"requirements-dev.txt": "pytest\n"}, {"python", "code"}),
            "python file": ({"tools/report.py": "print('x')\n"}, {"python", "code"}),
        }
        for n, (label, (files, want)) in enumerate(cases.items()):
            with self.subTest(label):
                root = self.repo(files, f"r{n}")
                found = recommend.signals(root, KIT)
                self.assertEqual(set(found), want)
                for sig, evidence in found.items():
                    self.assertTrue(evidence, sig)
                    for e in evidence:
                        self.assertTrue((root / e).is_file(), (sig, e))

    def test_build_and_vendor_folders_are_not_read(self):
        root = self.repo({"README.md": "x\n",
                          "node_modules/react/package.json": '{"dependencies": {"react": "1"}}\n',
                          "target/classes/pom.xml": PLAIN_POM})
        self.assertEqual(recommend.signals(root, KIT), {})
        self.assertEqual(self.ids(root, ["dev"]), [])


class TestCompute(Base):
    def test_a_javafx_maven_repo_for_a_developer(self):
        root = self.repo({"pom.xml": JAVAFX_POM})
        items = recommend.compute(KIT, root, st_for(["dev"]), self.packs)
        self.assertEqual([i["id"] for i in items], JAVAFX_DEV)
        for i in items:
            self.assertEqual(set(i), {"id", "action", "skill", "reason", "evidence", "declined"})
            self.assertEqual(i["evidence"], ["pom.xml"])
            self.assertFalse(i["declined"])
            self.assertEqual(i["id"], f"add:{i['skill']}")

    def test_an_empty_repo_gets_no_suggestions(self):
        root = self.repo({"README.md": "x\n"})
        self.assertEqual(self.ids(root, ["dev", "qa", "architect"]), [])

    def test_a_python_repo_has_code_but_no_stack_suggestion(self):
        """Python counts as code (a drop rule can fire), but no skill is Python's yet, and the
        mirror skill covers Maven, npm and Go only (re-test round 2, N2)."""
        root = self.repo({"pyproject.toml": "[project]\nname = 'x'\n", "src/x/app.py": "x = 1\n"})
        self.assertEqual(recommend.signals(root, KIT)["code"], ["pyproject.toml", "src/x/app.py"])
        self.assertEqual(self.ids(root, ["dev", "qa", "architect"]), [])

    def test_a_monorepo_gets_every_language(self):
        root = self.repo({"pom.xml": PLAIN_POM, "services/api/go.mod": "module api\n\ngo 1.23\n",
                          "web/package.json": '{"dependencies": {"react": "^18"}, "devDependencies": {"jest": "^29"}}\n'})
        got = self.ids(root, ["dev"])
        self.assertEqual(got, sorted(got, key=lambda i: i.split(":")[1]))
        for skill in ("java-code-review", "java-junit", "110-java-maven-best-practices", "golang-testing",
                      "golang-code-style", "golang-lint", "javascript-typescript-jest",
                      "react-testing-library", "accessibility", "maven-via-artifactory"):
            self.assertIn(f"add:{skill}", got)
        self.assertNotIn("add:javafx", got)

    def test_the_role_filter(self):
        root = self.repo({"pom.xml": JAVAFX_POM})
        self.assertEqual(self.ids(root, ["po"]), [])
        self.assertEqual(self.ids(root, ["qa"]), ["add:java-junit", "add:javafx", "add:maven-via-artifactory",
                                                  "add:sonarqube-findings"])

    def test_the_persons_choice_wins(self):
        root = self.repo({"pom.xml": JAVAFX_POM})
        copy = helpers.copy_kit(root / "kit-copy")
        code, out = helpers.cli(root, copy, "setup", "--name", "Ana", "--roles", "dev", "--lang", "en")
        self.assertEqual(code, 0, out)
        kit = root / paths.KIT_REL
        helpers.cli(root, kit, "change", "--drop-skill", "javafx", "--add-skill", "java-junit")
        st = state.load(root)
        got = [i["id"] for i in recommend.compute(kit, root, st, packs.load(kit))]
        self.assertNotIn("add:javafx", got)
        self.assertNotIn("add:java-junit", got)
        self.assertIn("add:java-code-review", got)

    def test_drop_rules_work_and_never_fire_without_code(self):
        kit = helpers.copy_kit(self.base / "kit")
        f = kit / recommend.RULES_REL
        data = json.loads(f.read_text(encoding="utf-8"))
        data["rules"].append({"skill": "brainstorming", "action": "drop", "unless": ["go"], "reason": "test"})
        f.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(recommend.validate(kit), [])
        all_packs = packs.load(kit)
        java = self.repo({"pom.xml": PLAIN_POM}, "java")
        empty = self.repo({"README.md": "x\n"}, "empty")
        python = self.repo({"requirements.txt": "requests\n"}, "python")
        self.assertIn("drop:brainstorming", self.ids(java, ["dev"], kit, all_packs))
        self.assertEqual(self.ids(python, ["dev"], kit, all_packs), ["drop:brainstorming"])
        self.assertEqual(self.ids(java, ["dev"], kit, all_packs)[-1], "drop:brainstorming", "adds first")
        self.assertEqual(self.ids(empty, ["dev"], kit, all_packs), [])
        self.assertNotIn("drop:brainstorming", self.ids(java, ["dev"], kit, all_packs, add_skills=["brainstorming"]))
        self.assertNotIn("drop:brainstorming", self.ids(java, ["po"], kit, all_packs), "not placed for a PO")

    def test_declined_ones_are_marked_not_open(self):
        root = self.repo({"pom.xml": JAVAFX_POM})
        items = recommend.compute(KIT, root, st_for(["dev"], declined=["add:javafx"]), self.packs)
        javafx = [i for i in items if i["id"] == "add:javafx"]
        self.assertEqual(len(javafx), 1)
        self.assertTrue(javafx[0]["declined"])
        self.assertNotIn("add:javafx", [i["id"] for i in recommend.open_items(items)])
        self.assertEqual(len(recommend.open_items(items)), len(items) - 1)

    def test_others_lists_every_unplaced_skill_once_grouped(self):
        root = self.repo({"pom.xml": JAVAFX_POM})
        st = st_for(["dev"], declined=["add:javafx"])
        items = recommend.compute(KIT, root, st, self.packs)
        others = recommend.others(KIT, st, self.packs, items)
        names = [o["skill"] for o in others]
        have = set(packs.combine(self.packs, st["choices"])["skills"])
        self.assertEqual(len(names), len(set(names)))
        self.assertFalse(have & set(names))
        self.assertFalse({i["skill"] for i in items} & set(names))
        self.assertNotIn("git-verbs", names)
        self.assertEqual(set(names), set(packs.available_skills(KIT)) - have - {i["skill"] for i in items})
        groups = recommend.load(KIT)["groups"]
        self.assertEqual(others, sorted(others, key=lambda o: (groups.index(o["group"]), o["skill"])))
        by = {o["skill"]: o for o in others}
        self.assertEqual(by["playbook-qa"]["group"], "Role playbooks")
        self.assertEqual(by["skill-creator"]["group"], "Other")
        self.assertEqual(by["golang-lint"]["summary"], "golangci-lint: run, configure, read and fix findings.")
        for o in others:
            self.assertEqual(set(o), {"skill", "group", "summary"})
            self.assertTrue(1 <= len(o["summary"]) <= 100, o)

    def test_the_same_repo_gives_the_same_list(self):
        root = self.repo({"pom.xml": JAVAFX_POM, "web/package.json": '{"dependencies": {"react": "1"}}\n'})
        first = recommend.compute(KIT, root, st_for(["dev", "qa"]), self.packs)
        home = self.base / "home"
        (home / ".m2").mkdir(parents=True)
        (home / ".m2/settings.xml").write_text("<settings><mirrors><mirror><id>m</id><mirrorOf>*</mirrorOf>"
                                               "<url>https://mirror.example.com/</url></mirror></mirrors></settings>\n")
        (home / "pom.xml").write_text(PLAIN_POM)
        with mock.patch.dict(os.environ, {"HOME": str(home)}):
            again = recommend.compute(KIT, root, st_for(["dev", "qa"]), self.packs)
        self.assertEqual(first, again)
        self.assertEqual(first, recommend.compute(KIT, root, st_for(["dev", "qa"]), self.packs))


class TestCommand(Base):
    """`setup.py recommend`: read-only text and JSON, --all, --decline (plan Task 17)."""

    def set_up(self, files, roles="dev"):
        root = self.repo(files)
        code, out = helpers.cli(root, helpers.copy_kit(root / "kit-copy"), "setup", "--name", "Ana",
                                "--roles", roles, "--lang", "en")
        self.assertEqual(code, 0, out)
        self.kit = root / paths.KIT_REL
        return root

    def run_cli(self, root, *argv, code=0):
        got, out = helpers.cli(root, self.kit, "recommend", *argv)
        self.assertEqual(got, code, out)
        return out

    def test_recommend_lists_numbered_items_and_the_exact_change_command(self):
        root = self.set_up({"pom.xml": JAVAFX_POM})
        before = helpers.snapshot(root)
        out = self.run_cli(root)
        lines = out.splitlines()
        self.assertEqual(lines[0], "Skill suggestions for this repo (from its files; nothing is changed yet):")
        self.assertEqual(lines[1], "1. add:110-java-maven-best-practices — add ai-sdlc-110-java-maven-best-practices: "
                                   "this repo builds with Maven (pom.xml).")
        self.assertEqual(len([x for x in lines if x[:2].rstrip(".").isdigit()]), len(JAVAFX_DEV))
        skills = [i.split(":")[1] for i in JAVAFX_DEV]
        self.assertIn("To take them all: python3 .ai-sdlc/kit/setup.py change "
                      + " ".join(f"--add-skill {s}" for s in skills), lines)
        self.assertIn("To take some: the same command with only those skills.", lines)
        self.assertIn("To say no to the rest: python3 .ai-sdlc/kit/setup.py recommend --decline "
                      "<skill names or ids, comma-separated>  (or --decline all)", lines)
        self.assertEqual(helpers.snapshot(root), before)

    def test_no_suggestions_says_so(self):
        root = self.set_up({"README.md": "x\n"})
        self.assertEqual(self.run_cli(root).strip(), "No skill suggestions for this repo.")

    def test_all_adds_the_other_skills_grouped(self):
        root = self.set_up({"pom.xml": JAVAFX_POM})
        before = helpers.snapshot(root)
        lines = self.run_cli(root, "--all").splitlines()
        start = lines.index("Other skills you can add (nothing is changed yet):")
        self.assertGreater(start, lines.index("To take some: the same command with only those skills."))
        part = lines[start + 1:]
        groups = recommend.load(self.kit)["groups"]
        heads = [x[:-1] for x in part if x.endswith(":") and not x.startswith("- ")]
        self.assertEqual(heads, sorted(heads, key=groups.index))
        self.assertIn("- ai-sdlc-golang-lint — golangci-lint: run, configure, read and fix findings.", part)
        self.assertEqual(part[-1], "To add any of them: python3 .ai-sdlc/kit/setup.py change --add-skill <name> "
                                   "[--add-skill <name> …]")
        listed = [x[2:].split(" — ")[0] for x in part if x.startswith("- ")]
        for skill in ["playbook-dev", "brainstorming", "drawio", "javafx", "java-junit"]:
            self.assertNotIn(f"ai-sdlc-{skill}", listed)
        self.assertEqual(helpers.snapshot(root), before)

    def test_decline_some_and_all(self):
        root = self.set_up({"pom.xml": JAVAFX_POM})
        before = helpers.snapshot(root)
        out = self.run_cli(root, "--decline", "add:javafx")
        self.assertIn("Noted: add:javafx.", out)
        after = helpers.snapshot(root)
        self.assertEqual(sorted(k for k in after if after[k] != before.get(k)), [paths.STATE_REL])
        self.assertEqual(state.load(root)["declined_recommendations"], ["add:javafx"])
        lines = self.run_cli(root).splitlines()
        self.assertIn("Declined earlier (to take one, use the change command above):", lines)
        self.assertIn("- add:javafx — add ai-sdlc-javafx: this repo uses JavaFX (pom.xml).", lines)
        self.assertNotIn("add:javafx", lines[0:lines.index("To take some: the same command with only those skills.")][-1])
        self.run_cli(root, "--decline", "all")
        self.assertEqual(state.load(root)["declined_recommendations"], sorted(JAVAFX_DEV))
        out = self.run_cli(root)
        self.assertTrue(out.startswith("No new skill suggestions for this repo."), out)

    def test_decline_takes_skill_names_as_well_as_ids(self):
        """Copilot passes the skill names the person said no to (re-test round 2, M2)."""
        root = self.set_up({"pom.xml": JAVAFX_POM})
        out = self.run_cli(root, "--decline", "javafx, ai-sdlc-java-junit,add:sonarqube-findings")
        self.assertIn("Noted: add:javafx, add:java-junit, add:sonarqube-findings.", out)
        self.assertEqual(state.load(root)["declined_recommendations"],
                         ["add:java-junit", "add:javafx", "add:sonarqube-findings"])
        before = helpers.snapshot(root)
        out = self.run_cli(root, "--decline", "drawio", code=2)
        self.assertIn("Not a current suggestion: drawio.", out)
        self.assertIn("Use the skill names or ids it lists.", out)
        self.assertEqual(helpers.snapshot(root), before)

    def test_an_unknown_id_is_refused(self):
        root = self.set_up({"pom.xml": JAVAFX_POM})
        before = helpers.snapshot(root)
        out = self.run_cli(root, "--decline", "add:nothing", code=2)
        self.assertIn("Not a current suggestion: add:nothing.", out)
        out = self.run_cli(root, "--decline", "add:javafx", "--all", code=2)
        self.assertIn("--decline takes suggestion ids or skill names only", out)
        self.assertEqual(helpers.snapshot(root), before)

    def test_change_clears_a_declined_id(self):
        root = self.set_up({"pom.xml": JAVAFX_POM})
        self.run_cli(root, "--decline", "add:javafx,add:java-junit")
        code, out = helpers.cli(root, self.kit, "change", "--add-skill", "javafx")
        self.assertEqual(code, 0, out)
        self.assertEqual(state.load(root)["declined_recommendations"], ["add:java-junit"])

    def test_json_output(self):
        root = self.set_up({"pom.xml": JAVAFX_POM})
        data = json.loads(self.run_cli(root, "--json"))
        self.assertEqual(set(data), {"suggestions", "connectors", "others"})
        self.assertEqual(data["others"], [])
        self.assertEqual([i["id"] for i in data["suggestions"]], JAVAFX_DEV)
        for i in data["suggestions"]:
            self.assertEqual(set(i), {"id", "action", "skill", "reason", "evidence", "declined"})
        data = json.loads(self.run_cli(root, "--json", "--all"))
        self.assertTrue(data["others"])
        for o in data["others"]:
            self.assertEqual(set(o), {"skill", "group", "summary"})

    def test_not_set_up(self):
        root = self.repo({"README.md": "x\n"})
        code, out = helpers.cli(root, KIT, "recommend")
        self.assertEqual(code, 2, out)
        self.assertIn('Say "do the onboarding"', out)

    def test_setup_mentions_open_suggestions_and_a_roles_change_does(self):
        root = self.repo({"pom.xml": JAVAFX_POM})
        code, out = helpers.cli(root, helpers.copy_kit(root / "kit-copy"), "setup", "--name", "Ana",
                                "--roles", "dev", "--lang", "en")
        self.assertEqual(code, 0, out)
        kit = root / paths.KIT_REL
        n = len(recommend.open_items(recommend.compute(kit, root, state.load(root), packs.load(kit))))
        self.assertEqual(n, len(JAVAFX_DEV))
        self.assertIn(f'- Skill suggestions for this repo: {n} (say "recommend skills")', out)
        code, out = helpers.cli(root, kit, "change", "--lang", "de")
        self.assertNotIn("Skill suggestions for this repo", out)
        code, out = helpers.cli(root, kit, "change", "--roles", "po,dev")
        self.assertIn("- Skill suggestions for this repo:", out)
        code, out = helpers.cli(root, kit, "check")
        self.assertNotIn("Skill suggestions", out)
        empty = self.repo({"README.md": "x\n"}, "empty")
        code, out = helpers.cli(empty, helpers.copy_kit(empty / "kit-copy"), "setup", "--name", "Ana",
                                "--roles", "dev", "--lang", "en")
        self.assertNotIn("Skill suggestions for this repo", out)

    def test_update_mentions_only_new_suggestions(self):
        root = self.repo({"pom.xml": JAVAFX_POM})
        old = helpers.copy_kit(root / "kit-old")
        f = old / recommend.RULES_REL
        data = json.loads(f.read_text(encoding="utf-8"))
        data["rules"] = [r for r in data["rules"] if r.get("skill") != "javafx"]
        f.write_text(json.dumps(data), encoding="utf-8")
        code, out = helpers.cli(root, old, "setup", "--name", "Ana", "--roles", "dev", "--lang", "en")
        self.assertEqual(code, 0, out)
        kit = root / paths.KIT_REL
        helpers.cli(root, kit, "recommend", "--decline", "all")
        st = state.load(root)
        st["declined_recommendations"].append("add:a-skill-the-kit-dropped")
        state.save(root, st)
        newer = helpers.copy_kit(root / "kit-newer")
        (newer / "VERSION").write_text("9.9.9\n")
        code, out = helpers.cli(root, newer, "update")
        self.assertEqual(code, 0, out)
        self.assertIn('- Skill suggestions for this repo: 1 (say "recommend skills")', out)
        self.assertNotIn("add:a-skill-the-kit-dropped", state.load(root)["declined_recommendations"])
        code, out = helpers.cli(root, kit, "recommend")
        self.assertIn("1. add:javafx", out)
        helpers.cli(root, kit, "recommend", "--decline", "all")
        code, out = helpers.cli(root, kit, "update")
        self.assertEqual(code, 0, out)
        self.assertNotIn("Skill suggestions for this repo", out)


# --- connector suggestions (0.10.0, design 2026-10-10 §6.2) -----------------------------------

SONAR = {"sonar-project.properties": "sonar.projectKey=demo\n"}
TOOLS_HEAD = ("Tools to connect for this repo (from its files; you type the login yourself, "
              "in your own terminal):")
STUB_LINE = ("1. connect:stubtool — Stub Tool: this repo is analysed by the stub tool "
             "(sonar-project.properties).")
DECLINED_TOOLS = ("Declined earlier (to connect one after all: python3 .ai-sdlc/kit/setup.py "
                  "connect <name>, in your own terminal):")


class TestConnectorItems(Base):
    """recommend.connector_items: the engine, on a kit copy with a stub connector rule."""

    @classmethod
    def setUpClass(cls):
        cls.ctmp = tempfile.TemporaryDirectory()
        cls.ckit = helpers.kit_with_connector_rule(Path(cls.ctmp.name) / "kit", light=True)

    @classmethod
    def tearDownClass(cls):
        cls.ctmp.cleanup()

    def items(self, root, roles, connected=(), all_packs=None, **kw):
        st = st_for(roles, **kw)
        with helpers.stubtool_registered(self.ckit):
            return recommend.connector_items(self.ckit, root, st,
                                             all_packs or packs.load(self.ckit), set(connected))

    def test_fires_on_its_signal_for_anyone(self):
        got = self.items(self.repo(SONAR), ["po"])
        self.assertEqual(got, [{"id": "connect:stubtool", "action": "connect",
                                "connector": "stubtool", "title": "Stub Tool",
                                "reason": "this repo is analysed by the stub tool",
                                "evidence": ["sonar-project.properties"],
                                "declined": False, "connected": False}])

    def test_no_signal_no_item(self):
        self.assertEqual(self.items(self.repo({"README.md": "x\n"}), ["po"]), [])

    def test_not_for_a_role_default(self):
        all_packs = packs.load(self.ckit)
        all_packs["dev"] = dict(all_packs["dev"],
                                connectors=all_packs["dev"]["connectors"] + ["stubtool"])
        root = self.repo(SONAR)
        self.assertEqual(self.items(root, ["dev"], all_packs=all_packs), [])
        self.assertEqual([i["id"] for i in self.items(root, ["po"], all_packs=all_packs)],
                         ["connect:stubtool"])
        self.assertEqual(self.items(root, ["po", "dev"], all_packs=all_packs), [])

    def test_connected_is_marked_not_open(self):
        got = self.items(self.repo(SONAR), ["po"], connected={"stubtool"})
        self.assertEqual([(i["id"], i["connected"]) for i in got], [("connect:stubtool", True)])
        self.assertEqual(recommend.open_connectors(got), [])

    def test_skipped_and_declined_are_not_open(self):
        root = self.repo(SONAR)
        st = st_for(["po"])
        st["skipped_connectors"] = ["stubtool"]
        with helpers.stubtool_registered(self.ckit):
            got = recommend.connector_items(self.ckit, root, st, packs.load(self.ckit), set())
        self.assertTrue(got[0]["declined"])
        self.assertEqual(recommend.open_connectors(got), [])
        got = self.items(root, ["po"], declined=["connect:stubtool"])
        self.assertTrue(got[0]["declined"])
        self.assertEqual(recommend.open_connectors(got), [])

    def test_compute_still_returns_only_skills(self):
        root = self.repo({**SONAR, "pom.xml": JAVAFX_POM})
        ids = self.ids(root, ["dev"], kit=self.ckit, all_packs=packs.load(self.ckit))
        self.assertTrue(ids)
        self.assertFalse([i for i in ids if i.startswith("connect:")])

    def test_same_repo_same_list(self):
        root = self.repo(SONAR)
        first = self.items(root, ["po"])
        with tempfile.TemporaryDirectory() as home, \
                mock.patch.dict(os.environ, {"HOME": home, "AI_SDLC_CONFIG_DIR": home}):
            self.assertEqual(self.items(root, ["po"]), first)
        self.assertEqual(self.items(root, ["po"]), first)

    def test_no_connect_rule_no_scan(self):
        kit = helpers.kit_with_connector_rule(self.base / "nokit", light=True)
        f = kit / recommend.RULES_REL
        data = json.loads(f.read_text(encoding="utf-8"))
        data["rules"] = [r for r in data["rules"] if r["action"] != "connect"]
        f.write_text(json.dumps(data), encoding="utf-8")
        with mock.patch.object(recommend, "signals") as scan:
            got = recommend.connector_items(kit, self.base, st_for(["po"]), self.packs, set())
        self.assertEqual(got, [])
        scan.assert_not_called()


class TestRecommendTools(unittest.TestCase):
    """`setup.py recommend` with connector suggestions (a kit copy with the stub rule)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        env = mock.patch.dict(os.environ, {"AI_SDLC_CONFIG_DIR": str(self.base / "cfg")})
        env.start()
        self.addCleanup(env.stop)

    def set_up(self, files, roles="po", name="repo"):
        root = helpers.make_repo(self.base / name, files)
        copy = helpers.kit_with_connector_rule(root / "kit-copy")
        self.kit = root / paths.KIT_REL
        with helpers.stubtool_registered(self.kit):
            code, out = helpers.cli(root, copy, "setup", "--name", "Ana", "--roles", roles,
                                    "--lang", "en")
        self.assertEqual(code, 0, out)
        self.setup_out = out
        return root

    def run_cli(self, root, *argv, code=0, command="recommend"):
        with helpers.stubtool_registered(self.kit):
            got, out = helpers.cli(root, self.kit, command, *argv)
        self.assertEqual(got, code, out)
        return out

    def declined(self, root):
        return state.load(root)["declined_recommendations"]

    def test_text_has_a_tools_part(self):
        root = self.set_up(SONAR)
        before = helpers.snapshot(root)
        lines = self.run_cli(root).splitlines()
        self.assertEqual(lines[lines.index(TOOLS_HEAD) + 1], STUB_LINE)
        self.assertIn("To connect one: python3 .ai-sdlc/kit/setup.py connect <name>   (in your "
                      "own terminal), or all of them with connect --suggested", lines)
        self.assertIn("To say no: python3 .ai-sdlc/kit/setup.py recommend --decline "
                      "connect:stubtool   (or the tool name)", lines)
        self.assertNotIn("No skill suggestions for this repo.", lines)
        self.assertEqual(helpers.snapshot(root), before)

    def test_the_tools_part_comes_after_the_skill_part(self):
        root = self.set_up({**SONAR, "pom.xml": JAVAFX_POM}, roles="dev")
        lines = self.run_cli(root).splitlines()
        self.assertEqual(lines[0], "Skill suggestions for this repo (from its files; nothing "
                                   "is changed yet):")
        self.assertGreater(lines.index(TOOLS_HEAD), lines.index(
            "To take some: the same command with only those skills."))

    def test_no_suggestions_line_unchanged(self):
        root = self.set_up({"README.md": "x\n"})
        self.assertEqual(self.run_cli(root).strip(), "No skill suggestions for this repo.")

    def test_decline_by_id_and_by_name(self):
        for n, value in enumerate(("connect:stubtool", "stubtool")):
            with self.subTest(value):
                root = self.set_up(SONAR, name=f"repo{n}")
                out = self.run_cli(root, "--decline", value)
                self.assertIn("Noted: connect:stubtool.", out)
                self.assertEqual(self.declined(root), ["connect:stubtool"])
                lines = self.run_cli(root).splitlines()
                self.assertNotIn(TOOLS_HEAD, lines)
                self.assertEqual(lines[lines.index(DECLINED_TOOLS) + 1],
                                 "- " + STUB_LINE[3:])
                self.assertEqual(lines[0], "No skill suggestions for this repo.")

    def test_decline_all_is_skills_only(self):
        root = self.set_up({**SONAR, "pom.xml": JAVAFX_POM}, roles="dev")
        self.run_cli(root, "--decline", "all")
        declined = self.declined(root)
        self.assertTrue(declined)
        self.assertNotIn("connect:stubtool", declined)
        self.assertIn("1. connect:stubtool — Stub Tool: this repo is analysed by the stub tool "
                      "(pom.xml, sonar-project.properties).", self.run_cli(root).splitlines())

    def test_decline_all_tools(self):
        root = self.set_up({**SONAR, "pom.xml": JAVAFX_POM}, roles="dev")
        out = self.run_cli(root, "--decline", "all-tools")
        self.assertIn("Noted: connect:stubtool.", out)
        self.assertEqual(self.declined(root), ["connect:stubtool"])
        self.assertIn("1. add:", self.run_cli(root))          # the skills are still open
        out = self.run_cli(root, "--decline", "all-tools")
        self.assertEqual(out.strip(), "Nothing to decline: there are no open tool suggestions.")

    def test_unknown_names_are_refused_and_mention_tools(self):
        root = self.set_up(SONAR)
        before = helpers.snapshot(root)
        out = self.run_cli(root, "--decline", "jira", code=2)
        self.assertIn("Not a current suggestion: jira.", out)
        self.assertIn("Use the skill names or ids it lists", out)
        self.assertIn("connect:<tool>", out)
        self.assertEqual(helpers.snapshot(root), before)

    def test_json_has_connectors(self):
        root = self.set_up(SONAR)
        data = json.loads(self.run_cli(root, "--json"))
        self.assertEqual(set(data), {"suggestions", "connectors", "others"})
        self.assertEqual([i["id"] for i in data["connectors"]], ["connect:stubtool"])
        self.assertEqual(set(data["connectors"][0]), {"id", "action", "connector", "title",
                                                      "reason", "evidence", "declined",
                                                      "connected"})

    def test_connect_clears_a_decline(self):
        from fakeserver import FakeServer
        root = self.set_up(SONAR)
        self.run_cli(root, "--decline", "stubtool")
        with FakeServer({"/api/me": {"login": "ana", "name": "Ana"}}) as srv, \
                mock.patch.dict(os.environ, {"AI_SDLC_STUBTOOL_URL": srv.url,
                                             "AI_SDLC_STUBTOOL_TOKEN": "stub-T0KEN-1234",
                                             "AI_SDLC_STUBTOOL_USER": "ana"}), \
                mock.patch("sys.stdin", io.StringIO("")):
            out = self.run_cli(root, "stubtool", command="connect")
        self.assertNotIn("stub-T0KEN-1234", out)
        self.assertEqual(self.declined(root), [])
        out = self.run_cli(root, "--json")
        self.assertTrue(json.loads(out)["connectors"][0]["connected"])

    def test_connected_tools_are_not_shown(self):
        root = self.set_up(SONAR)
        from personal.connectors import store
        store.save("stubtool", {"url": "https://stub.example.com", "token": "stub-T0KEN-1234"})
        self.assertEqual(self.run_cli(root).strip(), "No skill suggestions for this repo.")

    def test_summary_line_in_setup_roles_change_and_update(self):
        root = self.set_up(SONAR)
        line = "- Tools to connect for this repo: stubtool (say 'connect stubtool')"
        self.assertIn(line, self.setup_out.splitlines())
        out = self.run_cli(root, "--lang", "de", command="change")
        self.assertNotIn("Tools to connect", out)
        out = self.run_cli(root, "--roles", "po,sm", command="change")
        self.assertIn(line, out.splitlines())
        newer = helpers.kit_with_connector_rule(root / "kit-newer")
        (newer / "VERSION").write_text("9.9.9\n")
        with helpers.stubtool_registered(self.kit):
            code, out = helpers.cli(root, newer, "update")
        self.assertEqual(code, 0, out)
        self.assertIn(line, out.splitlines())
        self.run_cli(root, "--decline", "all-tools")
        newer = helpers.kit_with_connector_rule(root / "kit-newer2")
        (newer / "VERSION").write_text("9.9.10\n")
        with helpers.stubtool_registered(self.kit):
            code, out = helpers.cli(root, newer, "update")
        self.assertEqual(code, 0, out)
        self.assertNotIn("Tools to connect", out)
        self.assertEqual(self.declined(root), ["connect:stubtool"])   # kept: the kit has it

    def test_summary_line_after_the_skill_line_and_never_in_an_empty_repo(self):
        root = self.set_up({**SONAR, "pom.xml": JAVAFX_POM}, roles="dev")
        lines = self.setup_out.splitlines()
        skill = [n for n, x in enumerate(lines) if x.startswith("- Skill suggestions")][0]
        self.assertTrue(lines[skill + 1].startswith("- Tools to connect for this repo: "))
        self.set_up({"README.md": "x\n"}, name="empty")
        self.assertNotIn("Tools to connect", self.setup_out)


class TestRulesFile(unittest.TestCase):
    """roles/recommend.json validates, and each kind of mistake gives one readable error."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.kit = Path(cls.tmp.name) / "kit"
        shutil.copytree(KIT / packs.ROLES_REL, cls.kit / packs.ROLES_REL)
        shutil.copytree(KIT / packs.SKILLS_REL, cls.kit / packs.SKILLS_REL, ignore=helpers.SKIP)
        # The connector modules too: the connect rules name them (0.10.0).
        shutil.copytree(KIT / helpers.CONNECTORS_REL, cls.kit / helpers.CONNECTORS_REL,
                        ignore=helpers.SKIP)
        cls.good = json.loads((KIT / recommend.RULES_REL).read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def errors_with(self, change):
        data = json.loads(json.dumps(self.good))
        change(data)
        (self.kit / recommend.RULES_REL).write_text(json.dumps(data), encoding="utf-8")
        return recommend.validate(self.kit)

    def test_the_real_file_validates(self):
        self.assertEqual(recommend.validate(KIT), [])
        self.assertEqual(self.errors_with(lambda d: None), [])

    def test_bad_entries(self):
        def rule(**kw):
            def change(d):
                d["rules"][0].update(kw)
                for k, v in list(d["rules"][0].items()):
                    if v is None:
                        del d["rules"][0][k]
            return change
        cases = {
            "unknown skill": (rule(skill="nothing-here"), "nothing-here"),
            "unknown signal": (rule(when=["cobol"]), "cobol"),
            "unknown role": (rule(roles=["ceo"]), "ceo"),
            "add without roles": (rule(roles=None), "roles"),
            "drop with when": (rule(action="drop", unless=["go"], skill="brainstorming"), "when"),
            "empty reason": (rule(reason=""), "reason"),
            "long reason": (rule(reason="x" * 121), "reason"),
            "two rules for one id": (lambda d: d["rules"].append(dict(d["rules"][0])), "add:java-code-review"),
            "add for a role skill": (rule(skill="brainstorming"), "brainstorming"),
            "catalogue unknown skill": (lambda d: d["catalogue"].update({"nope": {"group": "Other", "summary": "x"}}), "nope"),
            "unknown group": (lambda d: d["catalogue"]["javafx"].update(group="Desktop"), "Desktop"),
            "long summary": (lambda d: d["catalogue"]["javafx"].update(summary="y" * 101), "summary"),
        }
        for label, (change, word) in cases.items():
            with self.subTest(label):
                errs = self.errors_with(change)
                self.assertEqual(len(errs), 1, errs)
                self.assertIn(word, errs[0])



class TestRealConnectorRules(Base):
    """The three connector rules of design 2026-10-10 §6.2, in the shipped kit (Task C1).
    `code` stays the artifactory signal (owner decision 2026-10-10, §12 item 3)."""

    REPO = {"pom.xml": JAVAFX_POM,                              # sonar-maven-plugin
            "Jenkinsfile": "sh 'bash detect.sh --blackduck.url=x'\n"}

    def connect_ids(self, root, roles):
        st = st_for(roles)
        return [i["id"] for i in recommend.connector_items(KIT, root, st, self.packs, set())]

    def test_the_three_rules(self):
        rules = [r for r in recommend.load(KIT)["rules"] if r["action"] == "connect"]
        self.assertEqual(rules, [
            {"connector": "sonarqube", "action": "connect", "when": ["sonar"],
             "reason": "this repo is analysed by SonarQube"},
            {"connector": "blackduck", "action": "connect", "when": ["blackduck"],
             "reason": "this repo is scanned by Black Duck"},
            {"connector": "artifactory", "action": "connect", "when": ["code"],
             "reason": "this repo downloads packages; the connector checks which versions "
                       "the company mirror has"},
        ])

    def test_a_po_in_a_sonar_and_blackduck_maven_repo(self):
        self.assertEqual(self.connect_ids(self.repo(self.REPO), ["po"]),
                         ["connect:artifactory", "connect:blackduck", "connect:sonarqube"])

    def test_a_developer_gets_none(self):
        self.assertEqual(self.connect_ids(self.repo(self.REPO), ["dev"]), [])

    def test_qa_gets_artifactory_and_blackduck(self):
        self.assertEqual(self.connect_ids(self.repo(self.REPO), ["qa"]),
                         ["connect:artifactory", "connect:blackduck"])

    def test_architect_gets_artifactory(self):
        self.assertEqual(self.connect_ids(self.repo(self.REPO), ["architect"]),
                         ["connect:artifactory"])

    def test_an_empty_repo_gets_none(self):
        self.assertEqual(self.connect_ids(self.repo({"README.md": "x\n"}), ["po"]), [])


if __name__ == "__main__":
    unittest.main()
