#!/usr/bin/env python3
"""The 13 stack skills (9 vendored, 4 written for this kit): content policy guards.

These check the shipped text, not behaviour (detect_stack/recommend tests and a manual
try in Copilot do that): the planned files and nothing else, the upstream pin, blobs and
licence (or "Written for this kit" and the idea sources), the kit's rules in SKILL.md, no
download from the public internet, no MCP, no sub-agents, no link to a skill the kit does
not ship, no git step the AI takes without asking, a trimmed frontmatter, and that they
are library skills (in no role pack).
Plan: docs/roadmap/2026-10-09-stack-pack-plan.md, Task 1 (design §2, §3, §4.2, §7).
"""
import collections
import re
import unittest

import helpers
from personal import packs, place
from test_superpowers import GIT, GIT_RULE, SHOW_RULE

KIT = helpers.KIT
LIB = KIT / packs.SKILLS_REL
Upstream = collections.namedtuple("Upstream", "repo path commit licence copyright")
SAMBER = ("samber/cc-skills-golang", "8e899e20ff0cd4dc524af3993e4c62d8ee8c5717", "MIT",
          "Copyright (c) 2026 Samuel Berthe")
AWESOME = ("github/awesome-copilot", "82701c24b99488536ca399ff4789a458b7a05db7", "MIT",
           "Copyright GitHub, Inc.")
VENDORED = {
    "java-code-review": Upstream("decebals/claude-code-java", "skills/java-code-review",
                                 "0d98fe9bd62923e819568ee1e041a1bf320f74d4", "MIT",
                                 "Copyright (c) 2026 Decebal Suiu"),
    "java-junit": Upstream(AWESOME[0], "skills/java-junit", *AWESOME[1:]),
    "110-java-maven-best-practices": Upstream("jabrena/plinth", "skills/110-java-maven-best-practices",
                                              "dca88dc17dc2a86732b3360db201778e51c3a038",
                                              "Apache-2.0", None),
    "golang-testing": Upstream(SAMBER[0], "skills/golang-testing", *SAMBER[1:]),
    "golang-code-style": Upstream(SAMBER[0], "skills/golang-code-style", *SAMBER[1:]),
    "golang-lint": Upstream(SAMBER[0], "skills/golang-lint", *SAMBER[1:]),
    "javascript-typescript-jest": Upstream(AWESOME[0], "skills/javascript-typescript-jest", *AWESOME[1:]),
    "react-testing-library": Upstream("itechmeat/llm-code", "skills/react-testing-library",
                                      "7ae8a005245770a0fa1e10337b2eb10174c5886b", "MIT",
                                      "Copyright (c) 2026 itechmeat"),
    "accessibility": Upstream("addyosmani/web-quality-skills", "skills/accessibility",
                              "afa8da942115f2961fdbfa80807ea0b232ff6c00", "MIT",
                              "Copyright (c) 2026 Addy Osmani"),
}
KIT_WRITTEN = {"javafx", "maven-via-artifactory", "sonarqube-findings", "blackduck-findings"}
STACK = set(VENDORED) | KIT_WRITTEN
V = ["LICENSE", "PROVENANCE.md", "SKILL.md"]
FILES = {
    "java-code-review": V,                       # README.md not bundled
    "java-junit": V,
    "110-java-maven-best-practices": V + ["references/110-java-maven-best-practices.md"],
    "golang-testing": V + [f"references/{n}.md" for n in (
        "benchmarks", "coverage", "examples", "helpers", "http-testing", "integration-testing",
        "mocking")],                              # evals/ not bundled
    "golang-code-style": V + ["references/details.md"],
    "golang-lint": V + ["assets/golangci.yml", "references/linter-reference.md",
                        "references/nolint-directives.md"],     # renamed from .golangci.yml
    "javascript-typescript-jest": V,
    "react-testing-library": V + [f"references/{n}.md" for n in (
        "api", "async", "config", "debugging", "queries", "user-events")],
    "accessibility": V + ["references/A11Y-PATTERNS.md", "references/WCAG.md"],
    "javafx": ["PROVENANCE.md", "SKILL.md", "references/testing-and-packaging.md"],
    "maven-via-artifactory": ["PROVENANCE.md", "SKILL.md", "scripts/detect_stack.py"],
    "sonarqube-findings": ["PROVENANCE.md", "SKILL.md"],
    "blackduck-findings": ["PROVENANCE.md", "SKILL.md"],
}
# Upstream blob SHAs (first 12 characters) at the pin, checked 2026-10-10 with
# `gh api repos/<repo>/contents/<path>?ref=<commit> --jq .sha`. Each must be named in
# PROVENANCE.md, so a later update can tell which upstream text a file came from.
BLOBS = {
    "java-code-review": {"LICENSE": "85c2f8765b2a", "SKILL.md": "66fe7ee9e1cf"},
    "java-junit": {"LICENSE": "89bc5e962c99", "SKILL.md": "b5da58d17eb7"},
    "110-java-maven-best-practices": {
        "LICENSE": "261eeb9e9f8b", "SKILL.md": "09f59a3076ff",
        "references/110-java-maven-best-practices.md": "885a464f580b"},
    "golang-testing": {
        "LICENSE": "e01f008a1feb", "SKILL.md": "7c437a850b22",
        "references/benchmarks.md": "5fd29f065b6d", "references/coverage.md": "46618241a898",
        "references/examples.md": "103889b49cab", "references/helpers.md": "3c0487705d10",
        "references/http-testing.md": "a7ff122f3419",
        "references/integration-testing.md": "a5d11413e313",
        "references/mocking.md": "4c93e4668635"},
    "golang-code-style": {"LICENSE": "e01f008a1feb", "SKILL.md": "3e644ade46d9",
                          "references/details.md": "1f7dfa82a52f"},
    "golang-lint": {
        "LICENSE": "e01f008a1feb", "SKILL.md": "63837c1b06e9",
        "assets/.golangci.yml": "4af14a017269",
        "references/linter-reference.md": "a789d54baf71",
        "references/nolint-directives.md": "4600c68d7736"},
    "javascript-typescript-jest": {"LICENSE": "89bc5e962c99", "SKILL.md": "9552d7cb7b74"},
    "react-testing-library": {
        "LICENSE": "85df337d262b", "SKILL.md": "510f6bf61feb",
        "references/api.md": "546ef447810c", "references/async.md": "83d0e531fd56",
        "references/config.md": "4176b5b7124e", "references/debugging.md": "1c2c7d0c373d",
        "references/queries.md": "9785ac474e9f", "references/user-events.md": "6208ff5d6c7f"},
    "accessibility": {
        "LICENSE": "90715bb429f3", "SKILL.md": "22a244430f89",
        "references/A11Y-PATTERNS.md": "6d500efb3eb2", "references/WCAG.md": "a0bd65fa7494"},
}
IDEAS = {   # design §3: the idea sources of the kit-written skills (repo, commit), pinned 2026-10-09
    "javafx": [("JohannesRabauer/javafx-skills", "0a6b8f197f52"),
               ("DongZY0617/javafx-skill", "ddc35f1935a4")],
    "maven-via-artifactory": [("jfrog/jfrog-skills", "a27c74da9e36"),
                              ("decebals/claude-code-java", "0d98fe9bd629")],
    "sonarqube-findings": [("SonarSource/sonarqube-agent-plugins", "6142e57738de")],
    "blackduck-findings": [("AgentSecOps/SecOpsAgentKit", "6e25a4bc5743"),
                           ("OWASP/secure-agent-playbook", "1b5fd4cff760")],
}
MIRROR_RULE = ("- **Packages only through the company mirror:** never add `<repositories>` to a POM, "
               "never use `@latest`, and never run `npx` or `go install` against the public internet. "
               "Ask before anything that downloads. Load `ai-sdlc-maven-via-artifactory` (if you have "
               "it) to find the mirror and the versions this repo uses.")
READ_ONLY_RULE = ("- **Read-only:** work from the report the person pastes or exports. Never ask for, "
                  "see or repeat a token or password, and never change anything in the tool: marking a "
                  "finding as a false positive, accepted or ignored is the person's decision, made in "
                  "the tool.")
# 0.10.0: the two findings skills read through a connector when it is connected, so their
# read-only rule names the connector too (design 2026-10-10 §7.1, §7.2).
READ_ONLY_CONNECTOR_RULE = ("- **Read-only:** work from the kit's read-only connector's output, or "
                            "from a report the person pastes or exports. Never ask for, see or "
                            "repeat a token or password, and never change anything in the tool: "
                            "marking a finding as a false positive, accepted or ignored is the "
                            "person's decision, made in the tool.")
INSTALLS = re.compile(r"@latest|\bgo install\b|\bnpm (?:install|i)\b[^\n]*(?:\s-g\b|--global)|"
                      r"\bnpx (?!--no-install)|\bpip3? install\b|\bbrew install\b|"
                      r"curl [^\n|]*\|\s*(?:ba)?sh")
MCP = re.compile(r"\bMCP\b|mcp__|lighthouse_audit|take_snapshot")
AGENTS = re.compile(r"(?i)sub-?agents?\b|background agent|ultrathink|ultracode|\bfan out\b")
FOREIGN = re.compile(r"samber/cc-skills-golang@|\.claude/skills/|\bplinth:|frq-4-pptx")
PLACED = re.compile(r"`ai-sdlc-([a-z0-9-]+)`")
FRONTMATTER_KEYS = {"name", "description", "license", "metadata"}
REVIEWED = {   # upstream lines with a git word that tell the AI to do nothing; reviewed 2026-10-09
    "java-code-review": ["or before merging changes", "Before merging a PR"],
    "javascript-typescript-jest": ["Review snapshot changes carefully before committing"],
    "react-testing-library": ["errors.push(error)", "recoverableErrors.push(error)"],
}
TRIGGERS = {
    "java-junit": ["write a JUnit test", "parameterized test", "Mockito"],
    "javascript-typescript-jest": ["write a Jest test", "mock this module", "snapshot test"],
    "javafx": ["JavaFX", "FXML", "the UI freezes", "TestFX", "jpackage", "frozen", "not responding"],
    "maven-via-artifactory": ["could not resolve", "add a dependency", "which Java version",
                              "upgrade a dependency", "dependency not found", "which mirror"],
    "golang-lint": ["lint", "golangci-lint", "go vet"],
    "golang-testing": ["Go tests", "go test", "table-driven"],
    "sonarqube-findings": ["Sonar", "quality gate failed", "code smell"],
    "blackduck-findings": ["Black Duck", "BDSA", "vulnerable dependency", "licence risk"],
}
MAVEN_REF = "references/110-java-maven-best-practices.md"


def shipped(skill):
    """(file name, text) of every UTF-8 file Copilot reads as the skill: all but PROVENANCE.md
    and LICENSE (a human-facing record that must name what was changed, and the licence)."""
    for p in sorted((LIB / skill).rglob("*")):
        rel = p.relative_to(LIB / skill).as_posix()
        if p.is_file() and rel not in ("PROVENANCE.md", "LICENSE"):
            try:
                yield rel, p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue


def section(text, heading):
    """The body of a `## ` section, up to the next `## ` heading ('' when it is missing)."""
    if heading not in text:
        return ""
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def frontmatter_keys(text):
    """Top-level keys of the YAML frontmatter (no YAML parser: the kit stays stdlib)."""
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    return {k for k in re.findall(r"(?m)^([A-Za-z][\w-]*):", m.group(1))} if m else set()


def description(text):
    m = re.search(r"(?m)^description: (.+)$", text)
    return m.group(1) if m else ""


class Checks:
    """Every stack skill passes these. Subclasses set `skill`."""
    skill = ""

    def folder(self):
        d = LIB / self.skill
        self.assertTrue(d.is_dir(), f"{packs.SKILLS_REL}/{self.skill}/ is missing: not written yet")
        return d

    def text(self, name):
        p = self.folder() / name
        self.assertTrue(p.is_file(), f"{self.skill}/{name} is missing")
        return p.read_text(encoding="utf-8")

    def rules(self):
        """The kit's rules section of SKILL.md: `## This kit's copy` (vendored) or `## Rules`."""
        heading = "## This kit's copy" if self.skill in VENDORED else "## Rules"
        text = self.text("SKILL.md")
        self.assertIn(heading, text)
        return section(text, heading)

    def everything(self):
        self.folder()
        return "\n".join(t for _, t in shipped(self.skill))

    def test_the_folder_holds_exactly_the_planned_files(self):
        d = self.folder()
        got = sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file())
        self.assertEqual(got, sorted(FILES[self.skill]))

    def test_the_name_matches_and_setup_places_it_prefixed(self):
        self.assertTrue(self.text("SKILL.md").startswith(f"---\nname: {self.skill}\n"))
        self.assertEqual(set(place.placed_skill_files(KIT, self.skill)),
                         {f".agents/skills/{packs.PREFIX}{self.skill}/{f}" for f in FILES[self.skill]})
        missing = []
        place.placed_skill(KIT, self.skill, missing)
        self.assertEqual(missing, [], "links in SKILL.md with no target")

    def test_licence_and_provenance(self):
        prov = self.text("PROVENANCE.md")
        if self.skill in VENDORED:
            up = VENDORED[self.skill]
            lic = self.text("LICENSE")
            if up.licence == "MIT":
                self.assertTrue(lic.startswith("MIT License"))
                self.assertIn(up.copyright, lic)
            else:
                self.assertIn("Apache License", lic[:300])
                self.assertIn("Version 2.0", lic[:300])
            for needed in (f"https://github.com/{up.repo}", f"`{up.path}`", up.commit, up.licence,
                           "Taken", "## Local modifications", "## Updating"):
                self.assertIn(needed, prov)
            for f in FILES[self.skill]:
                if f != "PROVENANCE.md":
                    self.assertIn(f"`{f}`", prov)
            for upstream_file, blob in BLOBS[self.skill].items():
                self.assertIn(blob, prov, f"PROVENANCE.md does not name the blob of {upstream_file}")
        else:
            self.assertFalse((self.folder() / "LICENSE").exists(), "kit-written: the kit's licence applies")
            for needed in ("Written for this kit", "## Ideas from", "No text was copied", "MIT"):
                self.assertIn(needed, prov)
            for repo, commit in IDEAS[self.skill]:
                self.assertIn(repo, prov)
                self.assertIn(commit, prov)

    def test_the_kit_rules_are_in_skill_md(self):
        rules = self.rules()
        self.assertIn(GIT_RULE, rules)
        self.assertIn(SHOW_RULE, rules)
        if self.skill == "maven-via-artifactory":
            self.assertNotIn(MIRROR_RULE, rules)        # it *is* the mirror rule
        else:
            self.assertIn(MIRROR_RULE, rules)
        if self.skill in ("sonarqube-findings", "blackduck-findings"):
            self.assertIn(READ_ONLY_CONNECTOR_RULE, rules)
            self.assertNotIn(READ_ONLY_RULE, rules)     # the 0.9.0 report-only wording

    def test_no_internet_installs(self):
        # A line that forbids it ("never use `@latest`", MIRROR_RULE itself) is fine.
        found = [f"{name}:{n}: {line.strip()}" for name, text in self.shipped_or_fail()
                 for n, line in enumerate(text.splitlines(), 1)
                 if INSTALLS.search(line) and "never" not in line.lower()]
        self.assertEqual(found, [])

    def shipped_or_fail(self):
        self.folder()
        return list(shipped(self.skill))

    def test_no_mcp_and_no_sub_agents(self):
        found = [f"{name}: {m.group(0)!r}" for name, text in self.shipped_or_fail()
                 for rx in (MCP, AGENTS) for m in rx.finditer(text)]
        self.assertEqual(found, [])

    def test_no_reference_to_a_skill_not_shipped(self):
        files = self.shipped_or_fail()
        self.assertEqual([f"{name}: {m.group(0)!r}" for name, text in files
                          for m in FOREIGN.finditer(text)], [])
        # The other stack skills count as shipped: they are vendored in parallel (Tasks 2-14),
        # and TestPack and each class prove every one of them exists once merged.
        known = set(packs.available_skills(KIT)) | STACK
        self.assertEqual([f"{name}: ai-sdlc-{m.group(1)}" for name, text in files
                          for m in PLACED.finditer(text) if m.group(1) not in known], [])

    def test_every_git_mention_asks_first_or_was_reviewed(self):
        unasked = [f"{name}:{n}" for name, text in self.shipped_or_fail()
                   for n, line in enumerate(text.splitlines(), 1)
                   if GIT.search(line) and "ask" not in line.lower()
                   and not any(r in line for r in REVIEWED.get(self.skill, []))]
        self.assertEqual(unasked, [], "git words that neither ask the person nor were reviewed")

    def test_frontmatter_is_trimmed(self):
        text = self.text("SKILL.md")
        keys = frontmatter_keys(text)
        self.assertTrue(keys, "no frontmatter")
        self.assertLessEqual(keys, FRONTMATTER_KEYS)
        head = text.split("\n---\n", 1)[0]
        self.assertNotIn("openclaw", head)
        self.assertNotIn("allowed-tools", head)

    def test_the_description_fits_and_has_its_triggers(self):
        desc = description(self.text("SKILL.md"))
        self.assertTrue(desc, "no one-line description")
        self.assertLessEqual(len(desc), 1024)
        for phrase in TRIGGERS.get(self.skill, []):
            self.assertIn(phrase, desc)


# --- Java ------------------------------------------------------------------------------

class TestJavaCodeReview(Checks, unittest.TestCase):
    skill = "java-code-review"

    def test_review_only_and_the_java_versions(self):
        rules = self.rules()
        self.assertIn("Java 17 and 21", rules)
        self.assertIn("Review only", rules)


class TestJavaJunit(Checks, unittest.TestCase):
    skill = "java-junit"

    def test_versions_first_and_no_new_libraries_unasked(self):
        rules = self.rules()
        for needed in ("junit:junit", "org.junit.jupiter", "AssertJ", "Mockito", "ask before adding"):
            self.assertIn(needed, rules)


class TestMavenBestPractices(Checks, unittest.TestCase):
    skill = "110-java-maven-best-practices"

    def test_example_6_resolves_through_the_mirror(self):
        ref = self.text(MAVEN_REF)
        self.assertIn("### Example 6", ref)
        ex6 = ref.split("### Example 6", 1)[1].split("### Example 7", 1)[0]
        self.assertIn("<mirrorOf>", ex6)
        self.assertIn("stop and report", ex6)
        self.assertIn("**Bad example:**", ex6)
        # `<repositories>` in backticks is prose ("Do not add ..."); bare, it is XML, and the
        # only XML `<repositories>` is the bad example.
        xml = [m.start() for m in re.finditer(r"(?<!`)<repositories>", ex6)]
        self.assertEqual(len(xml), 1)
        self.assertGreater(xml[0], ex6.index("**Bad example:**"))

    def test_repositories_appear_only_as_the_bad_example(self):
        files = self.shipped_or_fail()
        xml = [name for name, text in files for _ in re.finditer(r"(?<!`)<repositories>", text)]
        self.assertEqual(xml, [MAVEN_REF], "XML <repositories> only in the Example 6 bad example")
        prose = [f"{name}:{n}" for name, text in files
                 for n, line in enumerate(text.splitlines(), 1)
                 if "`<repositories>`" in line and not re.search(r"(?i)\bnever\b|\bdo not\b", line)]
        self.assertEqual(prose, [], "`<repositories>` named only to forbid it")
        self.assertIn(MIRROR_RULE, self.text("SKILL.md"))

    def test_it_proposes_before_it_applies(self):
        ref = self.text(MAVEN_REF)
        self.assertNotIn("**APPLY** Maven best practices directly", ref)
        self.assertIn("**PROPOSE**", ref)
        rules = self.rules()
        self.assertIn("distributionUrl", rules)
        self.assertIn("./mvnw", rules)

    def test_the_goal_says_mirror_only_not_custom_repositories(self):
        """Re-test round 2: the Goal paragraph still allowed explicitly declared repositories."""
        goal = self.text(MAVEN_REF).split("## Goal", 1)[1].split("###", 1)[0]
        self.assertNotIn("Custom repositories should be declared explicitly", goal)
        self.assertIn("only through the company mirror", goal)
        self.assertIn("the Goal paragraph", self.text(MAVEN_REF))
        self.assertIn("Custom repositories should be declared explicitly", self.text("PROVENANCE.md"))

    def test_apache_change_notice_in_every_changed_file(self):
        self.assertIn("Changed for this kit", self.text("SKILL.md"))
        self.assertIn("Changed for this kit", self.text(MAVEN_REF))


# --- Go --------------------------------------------------------------------------------

class TestGolangTesting(Checks, unittest.TestCase):
    skill = "golang-testing"

    def test_go_mod_first_and_no_gotests_install(self):
        rules = self.rules()
        self.assertIn("`go` and `toolchain` lines in `go.mod`", rules)
        self.assertIn("1.25", rules)
        files = self.shipped_or_fail()
        self.assertEqual([n for n, t in files if "gotests@latest" in t], [])
        # `go install` only where it is forbidden (MIRROR_RULE).
        self.assertEqual([f"{name}:{n}" for name, text in files
                          for n, line in enumerate(text.splitlines(), 1)
                          if "go install" in line and "never" not in line.lower()], [])


class TestGolangCodeStyle(Checks, unittest.TestCase):
    skill = "golang-code-style"


class TestGolangLint(Checks, unittest.TestCase):
    skill = "golang-lint"

    def test_the_config_is_placed_and_every_fix_waits_for_a_yes(self):
        self.folder()
        self.assertIn(".agents/skills/ai-sdlc-golang-lint/assets/golangci.yml",
                      place.placed_skill_files(KIT, self.skill))
        files = self.shipped_or_fail()
        self.assertEqual([n for n, t in files if "assets/.golangci.yml" in t], [])
        # In the Markdown (the instructions; the YAML config only names the flag in a comment),
        # each `--fix` line, or the comment line just above it, says it waits for a yes.
        unasked = []
        for name, text in files:
            if not name.endswith(".md"):
                continue
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if "--fix" in line and "yes" not in line and not (i and "yes" in lines[i - 1]):
                    unasked.append(f"{name}:{i + 1}: {line.strip()}")
        self.assertEqual(unasked, [])


# --- React and web ---------------------------------------------------------------------

class TestJavascriptTypescriptJest(Checks, unittest.TestCase):
    skill = "javascript-typescript-jest"


class TestReactTestingLibrary(Checks, unittest.TestCase):
    skill = "react-testing-library"

    def test_jest_only(self):
        self.assertEqual([n for n, t in self.shipped_or_fail() if re.search(r"(?i)vitest", t)], [])
        self.assertIn("Jest only", self.rules())


class TestAccessibility(Checks, unittest.TestCase):
    skill = "accessibility"

    def test_no_downloads_and_no_mcp(self):
        text = self.everything()
        self.assertNotIn("npx lighthouse", text)
        self.assertNotIn("npm install @axe-core/cli -g", text)
        self.assertIn("npx --no-install axe", self.text("SKILL.md"))


# --- Kit-written -----------------------------------------------------------------------

class TestJavafx(Checks, unittest.TestCase):
    skill = "javafx"

    def test_the_topics_the_owner_asked_for(self):
        text = self.text("SKILL.md") + self.text("references/testing-and-packaging.md")
        for needed in ("Platform.runLater", "Task", "Service", "FXML", "fx:controller",
                       "WeakChangeListener", "MVVM", "MVCI", "TestFX", "Monocle", "headless",
                       "javafx-maven-plugin", "jlink", "jpackage", "org.openjfx", "Zulu"):
            self.assertIn(needed, text)


class TestMavenViaArtifactory(Checks, unittest.TestCase):
    skill = "maven-via-artifactory"

    def test_mirrors_stop_on_failure_and_versions(self):
        text = self.text("SKILL.md")
        for needed in ("settings.xml", ".npmrc", "GOPROXY", "stop and report", "scripts/detect_stack.py",
                       "Spring Boot", "JUnit", "](scripts/detect_stack.py)"):
            self.assertIn(needed, text)

    def test_check_the_mirror_has_the_version(self):
        text = self.text("SKILL.md")
        part = text.split("## 6. Check the mirror has the version", 1)[1]
        for needed in ("connectors.py artifactory whoami --json",
                       "connectors.py artifactory versions", "connectors.py artifactory npm",
                       "connectors.py artifactory go", "propose only a version in that list",
                       "say the version is not confirmed", "section 3"):
            self.assertIn(needed, part)
        self.assertIn("Check the mirror has the version", text.split("## 6.", 1)[0])  # from 5


class TestSonarqubeFindings(Checks, unittest.TestCase):
    skill = "sonarqube-findings"

    def test_report_based_and_read_only(self):
        text = self.everything()
        for needed in ("paste", "export", "Community", "false positive", "java:S2095"):
            self.assertIn(needed, text)
        for write_api in ("api/issues/do_transition", "api/issues/set_severity",
                          "api/hotspots/change_status"):
            self.assertNotIn(write_api, text)
        self.assertEqual([line for line in text.splitlines()
                          if "token" in line.lower() and "never" not in line.lower()], [])

    def test_reads_through_the_connector_when_connected(self):
        text = self.text("SKILL.md")
        for needed in ("connectors.py sonarqube whoami --json", "connectors.py sonarqube gate",
                       "connectors.py sonarqube issues", "connectors.py sonarqube hotspots",
                       "connectors.py sonarqube rule", "exit code 3", "say *connect sonarqube*",
                       r"grep -E '^\s*sonar\.projectKey'", "never print the whole file",
                       "filter_sent", "`url`"):
            self.assertIn(needed, text)
        for gone in ("You never talk to SonarQube yourself", "## 7. Later: a connector"):
            self.assertNotIn(gone, text)
        for line in text.splitlines():
            if "setup.py connect" in line:
                self.assertIn("in their own terminal", line)
        self.assertIn("reads SonarQube through the read-only sonarqube connector when connected",
                      description(text))


class TestBlackduckFindings(Checks, unittest.TestCase):
    skill = "blackduck-findings"

    def test_report_based_upgrade_paths_and_licences_to_the_person(self):
        text = self.everything()
        for needed in ("BDSA", "CVE", "policy", "licence", "<dependencyManagement>", "overrides"):
            self.assertIn(needed, text)
        self.assertEqual([line for line in text.splitlines()
                          if "npm audit fix" in line and "never" not in line.lower()], [])

    def test_reads_through_the_connector_and_checks_the_mirror(self):
        text = self.text("SKILL.md")
        for needed in ("connectors.py blackduck whoami --json", "connectors.py blackduck vulns",
                       "connectors.py blackduck policy", "connectors.py blackduck components",
                       "--violations", "fixed_in", "detect.project.name",
                       "detect.project.version.name", "by key only", "exit code 3",
                       "say *connect blackduck*",
                       "`ai-sdlc-maven-via-artifactory` (\"Check the mirror has the version\")"):
            self.assertIn(needed, text)
        for gone in ("You never talk to Black Duck yourself", "## 7. Later: a connector"):
            self.assertNotIn(gone, text)
        for line in text.splitlines():
            if "setup.py connect" in line:
                self.assertIn("in their own terminal", line)
        self.assertIn("reads Black Duck through the read-only blackduck connector when connected",
                      description(text))


class TestPack(unittest.TestCase):
    """What the library holds, and that the 13 are library skills (design §2.1, §4.2)."""

    def test_react_best_practices_is_not_shipped(self):
        self.assertFalse((LIB / "react-best-practices").exists())
        self.assertEqual([p.parent.name for p in LIB.glob("*/PROVENANCE.md")
                          if "vercel-labs" in p.read_text(encoding="utf-8")], [])

    def test_kit_written_skills_say_so_and_vendored_ones_name_their_upstream(self):
        got = {p.parent.name for p in LIB.glob("*/PROVENANCE.md")
               if p.parent.name in STACK and "Written for this kit" in p.read_text(encoding="utf-8")}
        self.assertEqual(got, KIT_WRITTEN)
        for skill, up in VENDORED.items():
            p = LIB / skill / "PROVENANCE.md"
            self.assertTrue(p.is_file(), f"{skill}: no PROVENANCE.md")
            self.assertIn(f"https://github.com/{up.repo}", p.read_text(encoding="utf-8"))

    def test_stack_skills_are_library_skills(self):
        in_packs = set()
        for pack in packs.load(KIT).values():
            in_packs |= set(pack.get("skills", []))
        self.assertEqual(STACK & in_packs, set(), "a stack skill is in a role pack (or core)")


if __name__ == "__main__":
    unittest.main()
