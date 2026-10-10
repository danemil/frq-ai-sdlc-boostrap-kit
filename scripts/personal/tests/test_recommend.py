#!/usr/bin/env python3
"""Skill suggestions from the repo's files, and the list of other skills (design 2026-10-09 §5,
plan Tasks 16 and 17).

The engine (recommend.py) reads the repo through the kit's own detect_stack.py, applies the
rules in roles/recommend.json and never changes anything. The `recommend` command prints the
suggestions (and, with --all, every other skill), records declined ones in state.json, and
setup, update and a roles change mention open suggestions in one line.
"""
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
        self.assertIn("drop:brainstorming", self.ids(java, ["dev"], kit, all_packs))
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


class TestRulesFile(unittest.TestCase):
    """roles/recommend.json validates, and each kind of mistake gives one readable error."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.kit = Path(cls.tmp.name) / "kit"
        shutil.copytree(KIT / packs.ROLES_REL, cls.kit / packs.ROLES_REL)
        shutil.copytree(KIT / packs.SKILLS_REL, cls.kit / packs.SKILLS_REL, ignore=helpers.SKIP)
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


if __name__ == "__main__":
    unittest.main()
