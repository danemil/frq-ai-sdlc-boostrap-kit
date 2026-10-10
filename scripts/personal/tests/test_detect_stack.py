#!/usr/bin/env python3
"""The behaviour of maven-via-artifactory/scripts/detect_stack.py: one read-only detector of
the repo's stack (Java, JavaFX, Go, Node, the quality tools) and of the company mirrors.

Each test builds a small repo in a temporary folder. The script is loaded from the kit's
copy with importlib, as recommend.py loads it (Task 16).
Plan: docs/roadmap/2026-10-09-stack-pack-plan.md, Task 12 (design §5.2).
"""
import ast
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import packs

sys.dont_write_bytecode = True     # the test imports the skill's script: no __pycache__ in the skill

LIB = helpers.KIT / packs.SKILLS_REL
DETECT = LIB / "maven-via-artifactory/scripts/detect_stack.py"


def load():
    spec = importlib.util.spec_from_file_location("detect_stack_under_test", DETECT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write(root, files):
    for rel, text in files.items():
        p = Path(root) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return Path(root)


def pom(body="", props="", parent="", deps="", managed="", plugins=""):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  {parent}
  <groupId>com.example</groupId><artifactId>app</artifactId><version>1.0.0</version>
  <properties>{props}</properties>
  <dependencyManagement><dependencies>{managed}</dependencies></dependencyManagement>
  <dependencies>{deps}</dependencies>
  <build><plugins>{plugins}</plugins></build>
  {body}
</project>
"""


def dep(group, artifact, version=None, extra=""):
    v = f"<version>{version}</version>" if version else ""
    return f"<dependency><groupId>{group}</groupId><artifactId>{artifact}</artifactId>{v}{extra}</dependency>"


BOOT_PARENT = ("<parent><groupId>org.springframework.boot</groupId>"
               "<artifactId>spring-boot-starter-parent</artifactId><version>3.3.4</version></parent>")


class Base(unittest.TestCase):
    def setUp(self):
        self.ds = load()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def repo(self, files, name="repo"):
        return write(self.tmp / name, files)

    def cli(self, *argv, python=None):
        r = subprocess.run([python or sys.executable, "-I", str(DETECT), *argv],
                           capture_output=True, text=True, check=False)
        return r.returncode, r.stdout + r.stderr


class TestJava(Base):
    def test_java_release_spring_boot_and_junit_from_a_pom(self):
        root = self.repo({"pom.xml": pom(
            parent=BOOT_PARENT,
            props="<java.version>21</java.version><maven.compiler.release>${java.version}"
                  "</maven.compiler.release>",
            managed=dep("org.junit", "junit-bom", "5.10.2", "<type>pom</type><scope>import</scope>"),
            deps=dep("org.junit.jupiter", "junit-jupiter", extra="<scope>test</scope>")
                 + dep("org.assertj", "assertj-core", extra="<scope>test</scope>"))})
        java = self.ds.scan(root)["java"]
        self.assertEqual(java["build"], "maven")
        self.assertEqual(java["poms"], ["pom.xml"])
        self.assertEqual(java["release"], "21")
        self.assertEqual(java["release_from"], "pom.xml: maven.compiler.release")
        self.assertEqual(java["spring_boot"], "3.3.4")
        self.assertEqual((java["junit"], java["junit_version"]), ("5", "5.10.2"))
        self.assertTrue(java["assertj"])
        self.assertFalse(java["mockito"])
        self.assertFalse(java["testfx"])

    def test_junit_4_and_6(self):
        four = self.repo({"pom.xml": pom(deps=dep("junit", "junit", "4.13.2"))}, "four")
        java = self.ds.scan(four)["java"]
        self.assertEqual((java["junit"], java["junit_version"]), ("4", "4.13.2"))
        # A parent POM manages the version (BOM); the module declares the artifact only.
        six = self.repo({
            "pom.xml": pom(props="<junit.version>6.0.0</junit.version>",
                           managed=dep("org.junit", "junit-bom", "${junit.version}",
                                       "<type>pom</type><scope>import</scope>")),
            "core/pom.xml": pom(deps=dep("org.junit.jupiter", "junit-jupiter-api")),
        }, "six")
        java = self.ds.scan(six)["java"]
        self.assertEqual(java["poms"], ["pom.xml", "core/pom.xml"])
        self.assertEqual((java["junit"], java["junit_version"]), ("6", "6.0.0"))

    def test_no_spring_boot_is_none(self):
        root = self.repo({"pom.xml": pom(props="<maven.compiler.source>17</maven.compiler.source>"
                                               "<maven.compiler.target>17</maven.compiler.target>")})
        java = self.ds.scan(root)["java"]
        self.assertIsNone(java["spring_boot"])
        self.assertEqual(java["release"], "17")
        self.assertIsNone(java["junit"])

    def test_javafx_from_openjfx_with_version(self):
        root = self.repo({
            "pom.xml": pom(props="<javafx.version>21.0.5</javafx.version>",
                           deps=dep("org.openjfx", "javafx-controls", "${javafx.version}")
                                + dep("org.testfx", "testfx-junit5", "4.0.18"),
                           plugins="<plugin><groupId>org.openjfx</groupId>"
                                   "<artifactId>javafx-maven-plugin</artifactId>"
                                   "<version>0.0.8</version></plugin>"),
            "src/main/resources/main.fxml": "<?xml version=\"1.0\"?>\n<VBox/>\n",
        })
        r = self.ds.scan(root)
        fx = r["java"]["javafx"]
        self.assertTrue(fx["used"])
        self.assertEqual(fx["source"], "openjfx")
        self.assertEqual(fx["version"], "21.0.5")
        self.assertIn("pom.xml: org.openjfx:javafx-controls", fx["evidence"])
        self.assertIn("src/main/resources/main.fxml", fx["evidence"])
        self.assertTrue(r["java"]["testfx"])
        self.assertIn("src/main/resources/main.fxml", r["files"]["javafx"])

    def test_javafx_from_a_zulu_fx_jdk(self):
        root = self.repo({
            "pom.xml": pom(props="<maven.compiler.release>21</maven.compiler.release>"),
            ".sdkmanrc": "java=21.0.5.fx-zulu\n",
            "src/main/java/App.java": "package app;\n\nimport javafx.application.Application;\n",
        })
        fx = self.ds.scan(root)["java"]["javafx"]
        self.assertTrue(fx["used"])
        self.assertEqual(fx["source"], "jdk")
        self.assertIn(".sdkmanrc: java=21.0.5.fx-zulu", fx["evidence"])
        self.assertIn("src/main/java/App.java: import javafx.", fx["evidence"])
        # Imports alone do not tell where JavaFX comes from.
        only = self.repo({"src/main/java/App.java": "import javafx.scene.Scene;\n"}, "imports-only")
        fx = self.ds.scan(only)["java"]["javafx"]
        self.assertEqual((fx["used"], fx["source"]), (True, "unknown"))
        # No JavaFX at all.
        none = self.repo({"pom.xml": pom()}, "plain")
        fx = self.ds.scan(none)["java"]["javafx"]
        self.assertEqual((fx["used"], fx["source"], fx["version"], fx["evidence"]),
                         (False, None, None, []))


class TestGoNodeQuality(Base):
    def test_go_version_and_toolchain(self):
        root = self.repo({"svc/go.mod": "module example.com/svc\n\ngo 1.24.2\n\ntoolchain go1.25.1\n"})
        go = self.ds.scan(root)["go"]
        self.assertEqual(go, {"modules": ["svc/go.mod"], "go": "1.24.2", "toolchain": "go1.25.1"})

    def test_node_versions_and_lockfile(self):
        root = self.repo({
            "web/package.json": json.dumps({
                "dependencies": {"react": "^18.3.1"},
                "devDependencies": {"jest": "^29.7.0", "@testing-library/react": "^16.0.1",
                                    "typescript": "~5.5.4"}}),
            "web/package-lock.json": json.dumps({"lockfileVersion": 3, "packages": {
                "": {"name": "web"},
                "node_modules/react": {"version": "18.3.1"},
                "node_modules/jest": {"version": "29.7.0"}}}),
        })
        r = self.ds.scan(root)
        node = r["node"]
        self.assertEqual(node["packages"], ["web/package.json"])
        self.assertEqual((node["react"], node["jest"], node["testing_library_react"], node["typescript"]),
                         ("^18.3.1", "^29.7.0", "^16.0.1", "~5.5.4"))
        self.assertEqual(node["locked"], {"jest": "29.7.0", "react": "18.3.1"})
        self.assertEqual(r["files"]["react"], ["web/package.json"])
        self.assertEqual(r["files"]["jest"], ["web/package.json"])

    def test_sonar_and_blackduck_evidence(self):
        root = self.repo({
            "pom.xml": pom(props="<sonar.projectKey>app</sonar.projectKey>"),
            "Jenkinsfile": "stage('scan') {\n  withSonarQubeEnv('sq') { sh 'mvn sonar:sonar' }\n"
                           "  sh 'bash detect.sh --detect.project.name=app'\n}\n",
            "src/main/resources/application.yml": "server:\n  port: 8080\n",
        })
        q = self.ds.scan(root)["quality"]
        self.assertIn("pom.xml: sonar. property", q["sonar"])
        self.assertIn("Jenkinsfile: withSonarQubeEnv", q["sonar"])
        self.assertIn("Jenkinsfile: detect.sh", q["blackduck"])
        self.assertFalse(any("application.yml" in e for e in q["blackduck"]))
        empty = self.ds.scan(self.repo({"README.md": "hello\n"}, "empty"))
        self.assertEqual(empty["quality"], {"sonar": [], "blackduck": []})


class TestMirrors(Base):
    SETTINGS = """<?xml version="1.0"?>
<settings>
  <servers><server><id>corp</id><username>dev-user</username><password>s3cret-pw</password></server></servers>
  <mirrors><mirror><id>corp</id><mirrorOf>*</mirrorOf>
    <url>https://ci-bot:pw-789@artifactory.example.com/artifactory/maven-remote/</url></mirror></mirrors>
</settings>
"""

    def test_mirrors_from_repo_and_home(self):
        root = self.repo({".mvn/settings.xml": self.SETTINGS,
                          ".npmrc": "registry=https://artifactory.example.com/api/npm/npm/\n"})
        home = write(self.tmp / "home", {
            ".m2/settings.xml": self.SETTINGS.replace("maven-remote", "maven-home"),
            ".npmrc": "@corp:registry=https://artifactory.example.com/api/npm/corp/\n"})
        r = self.ds.scan(root, home=home, env={"GOPROXY": "https://artifactory.example.com/api/go/go,direct"})
        m = r["mirrors"]
        self.assertEqual([x["file"] for x in m["maven"]], [".mvn/settings.xml", "~/.m2/settings.xml"])
        self.assertEqual(m["maven"][0], {"file": ".mvn/settings.xml", "id": "corp", "mirrorOf": "*",
                                         "url": "https://artifactory.example.com/artifactory/maven-remote/"})
        self.assertEqual([(x["file"], x["registry"]) for x in m["npm"]],
                         [(".npmrc", "https://artifactory.example.com/api/npm/npm/"),
                          ("~/.npmrc", "https://artifactory.example.com/api/npm/corp/")])
        self.assertEqual(m["go"], {"GOPROXY": "https://artifactory.example.com/api/go/go,direct"})
        # Without home: the repo only; the person's files and environment are not read.
        r = self.ds.scan(root)
        self.assertEqual([x["file"] for x in r["mirrors"]["maven"]], [".mvn/settings.xml"])
        self.assertEqual(r["mirrors"]["go"], {"GOPROXY": None})

    def test_secrets_are_never_printed(self):
        root = self.repo({".mvn/settings.xml": self.SETTINGS,
                          ".npmrc": "registry=https://user:pw-456@host.example.com/npm/\n"
                                    "_authToken=tok-123\n"
                                    "//host.example.com/npm/:_authToken=tok-123\n"
                                    "_auth=dG9rLTEyMw==\n_password=pw-456\n",
                          "pom.xml": pom()})
        home = write(self.tmp / "home", {".m2/settings.xml": self.SETTINGS, ".npmrc": "_authToken=tok-123\n"})
        dumped = json.dumps(self.ds.scan(root, home=home,
                                         env={"GOPROXY": "https://u:pw-456@goproxy.example.com"}))
        code, out = self.cli("--json", "--root", str(root))
        self.assertEqual(code, 0)
        code, plain = self.cli("--root", str(root))
        self.assertEqual(code, 0)
        for text in (dumped, out, plain):
            for secret in ("s3cret-pw", "tok-123", "pw-456", "pw-789", "dev-user", "dG9rLTEyMw=="):
                self.assertNotIn(secret, text)
        self.assertIn("https://host.example.com/npm/", out)
        self.assertIn("https://artifactory.example.com/artifactory/maven-remote/", out)


class TestSafety(Base):
    def test_read_only(self):
        root = self.repo({"pom.xml": pom(deps=dep("org.openjfx", "javafx-controls", "21.0.5")),
                          "go.mod": "module x\n\ngo 1.22\n", "package.json": "{}",
                          ".mvn/settings.xml": TestMirrors.SETTINGS})
        before = helpers.snapshot(root)
        self.ds.scan(root)
        self.cli("--json", "--root", str(root))
        self.assertEqual(helpers.snapshot(root), before)

    def test_bounds(self):
        root = self.repo({
            "node_modules/x/package.json": json.dumps({"dependencies": {"react": "18"}}),
            "a/b/c/d/e/package.json": json.dumps({"dependencies": {"react": "18"}}),
            "big/pom.xml": pom(body="<!--" + "x" * 600 * 1024 + "-->"),
        })
        r = self.ds.scan(root)
        self.assertEqual(r["node"]["packages"], [])
        self.assertIsNone(r["node"]["react"])
        self.assertIn("big/pom.xml", [s["path"] for s in r["skipped"]])
        self.assertEqual(r["java"]["poms"], [])
        # The entry cap: a folder with more entries than the cap is cut, and said so.
        many = self.repo({f"f{i:05d}.txt": "" for i in range(self.ds.MAX_ENTRIES + 5)}, "many")
        self.assertTrue(any("limit" in s["reason"] for s in self.ds.scan(many)["skipped"]))

    def test_doctype_is_refused(self):
        root = self.repo({"pom.xml": "<?xml version=\"1.0\"?>\n<!DOCTYPE project [\n"
                                     "<!ENTITY x SYSTEM \"file:///etc/passwd\">]>\n"
                                     "<project><properties><maven.compiler.release>&x;"
                                     "</maven.compiler.release></properties></project>\n"})
        r = self.ds.scan(root)
        self.assertIsNone(r["java"]["release"])
        self.assertIn({"path": "pom.xml", "reason": "DOCTYPE or ENTITY declaration refused"}, r["skipped"])

    def test_stdlib_only_no_network_no_subprocess(self):
        tree = ast.parse(DETECT.read_text(encoding="utf-8"), feature_version=(3, 9))
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                mods.add((node.module or "").split(".")[0])
        allowed = {"__future__", "argparse", "json", "os", "re", "sys", "pathlib", "xml", "typing"}
        self.assertLessEqual(mods, allowed)
        for banned in ("socket", "urllib", "http", "subprocess", "ftplib", "ssl"):
            self.assertNotIn(banned, mods)

    def test_the_result_has_every_key_and_is_deterministic(self):
        root = self.repo({"README.md": "x\n"})
        a, b = self.ds.scan(root), self.ds.scan(root)
        self.assertEqual(a, b)
        self.assertEqual(set(a), {"schema", "java", "go", "node", "quality", "mirrors", "files", "skipped"})
        self.assertEqual(a["schema"], 1)
        self.assertEqual(set(a["java"]), {"build", "poms", "release", "release_from", "spring_boot",
                                          "junit", "junit_version", "assertj", "mockito", "testfx",
                                          "javafx"})
        self.assertEqual(set(a["node"]), {"packages", "react", "jest", "testing_library_react",
                                          "typescript", "locked"})
        code, out = self.cli("--root", str(self.tmp / "missing"))
        self.assertEqual(code, 2)

    @unittest.skipUnless(Path("/usr/bin/python3").is_file(), "no system python3")
    def test_runs_on_the_system_python(self):
        root = self.repo({"pom.xml": pom(props="<maven.compiler.release>17</maven.compiler.release>")})
        code, out = self.cli("--json", "--root", str(root), python="/usr/bin/python3")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["java"]["release"], "17")


if __name__ == "__main__":
    unittest.main()
