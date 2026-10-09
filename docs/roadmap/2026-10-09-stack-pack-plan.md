# Stack Pack Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task. Tasks 2–14 are independent (one skill folder each), and Tasks B1–B4 (the brand merge) run in their own worktree next to them: superpowers:dispatching-parallel-agents may run them at the same time, each in its own worktree. Everything else is sequential. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Ship 9 vendored and 4 kit-written stack skills (Java/JavaFX/Maven, Go, React/Jest, accessibility, the company mirror, SonarQube and Black Duck findings), a deterministic **detect + recommend** step, the owner's PowerPoint skill merged into `frq-brandbook`, and release kit 0.9.0.

**Architecture:** Skills are folders in `template/.claude/skills/<name>/`, placed as `.agents/skills/ai-sdlc-<name>/` (unchanged mechanics). Role packs (`roles/<id>/role.json`) list the baseline. A new module `scripts/personal/recommend.py` reads the repo through `maven-via-artifactory/scripts/detect_stack.py` (one detector, also used by Copilot), applies data rules from `roles/recommend.json`, and prints suggestions; accepted ones go through the existing `change --add-skill/--drop-skill`, declined ones are stored in `state.json`. Nothing is placed without a role or the person's choice.

**Tech Stack:** Markdown skills; Python 3.9+ stdlib (`unittest`, `zipfile`, `xml.etree`, `json`, `importlib`) for kit code and tests; python-pptx only inside the brand skill's builder, with consent; `gh` CLI to fetch upstream.

**Spec:** [`2026-10-09-stack-pack-design.md`](./2026-10-09-stack-pack-design.md) (draft; owner decisions in its §2, §3, §4.1, §8.1; proposals in §4.2, §5, §6, §8.2–8.7; open questions at the end of this plan).

## Global Constraints

- **Upstream pins** (all taken 2026-10-09; the commit is the repo's default-branch head that day, and the skill folder is the same as at its last change, given in brackets):

  | Skill | Repo | Commit | Folder last changed | Licence (LICENSE blob) |
  |---|---|---|---|---|
  | `java-code-review` | decebals/claude-code-java | `0d98fe9bd62923e819568ee1e041a1bf320f74d4` | `702770a755fb` 2026-08-28 | MIT, "Copyright (c) 2026 Decebal Suiu" (`85c2f8765b2a`) |
  | `java-junit` | github/awesome-copilot | `82701c24b99488536ca399ff4789a458b7a05db7` | `caab1f623bb6` 2026-02-24 | MIT, "Copyright GitHub, Inc." (`89bc5e962c99`) |
  | `110-java-maven-best-practices` | jabrena/plinth | `dca88dc17dc2a86732b3360db201778e51c3a038` | `9569c35d7cf6` 2026-09-26 | Apache-2.0 (`261eeb9e9f8b`); upstream has no `NOTICE` |
  | `golang-testing` | samber/cc-skills-golang | `8e899e20ff0cd4dc524af3993e4c62d8ee8c5717` | `8f8e2feb661b` 2026-09-02 | MIT, "Copyright (c) 2026 Samuel Berthe" (`e01f008a1feb`) |
  | `golang-code-style` | samber/cc-skills-golang | same | `ba9cc6d7fdc0` 2026-08-19 | same |
  | `golang-lint` | samber/cc-skills-golang | same | `ec8c349e295a` 2026-09-01 | same |
  | `javascript-typescript-jest` | github/awesome-copilot | `82701c24b99488536ca399ff4789a458b7a05db7` | `caab1f623bb6` 2026-02-24 | MIT (as above) |
  | `react-testing-library` | itechmeat/llm-code (branch `master`) | `7ae8a005245770a0fa1e10337b2eb10174c5886b` | `5f18228abfde` 2026-09-04 | MIT, "Copyright (c) 2026 itechmeat" (`85df337d262b`) |
  | `accessibility` | addyosmani/web-quality-skills | `afa8da942115f2961fdbfa80807ea0b232ff6c00` | `c6b06ad1285c` 2026-08-24 | MIT, "Copyright (c) 2026 Addy Osmani" (`90715bb429f3`) |

- **Fetch command** (each file, into an empty scratch folder, never into the repo directly; read the files, never run them):
  `gh api "repos/<repo>/contents/<path>/<file>?ref=<commit>" --jq .content | base64 -d > <scratch>/<name>/<file>`; licence: `contents/LICENSE`. Check each blob SHA (first 12 characters, `--jq .sha`) against the task's list. **zsh:** never name a shell variable `path` (it is tied to `PATH`).
- **Line numbers** are upstream line numbers at the pinned commit. Apply edits **bottom-up** so numbers stay valid.
- **The kit section.** Every vendored `SKILL.md` gets one new section, at the place each task names, exactly (plus the task's extra bullets):

  ```markdown
  ## This kit's copy

  - **Git:** never commit, push or merge on your own. Follow the person's git-comfort setting and ask before each commit.
  - **Show before you change:** before editing or creating any file (a new test file too), show the proposed diff or content and wait for a yes; if you can't ask, stop after proposing. Report evidence (the test output), never just "Fixed".
  - **Packages only through the company mirror:** never add `<repositories>` to a POM, never use `@latest`, and never run `npx` or `go install` against the public internet. Ask before anything that downloads. Load `ai-sdlc-maven-via-artifactory` (if you have it) to find the mirror and the versions this repo uses.
  ```

  The first two bullets are `GIT_RULE` and `SHOW_RULE` from `test_superpowers.py` (imported, not copied); the third is `MIRROR_RULE` (Task 1). Kit-written skills carry the same bullets under `## Rules` (Tasks 11–14).
- **Frontmatter of vendored skills** keeps only `name`, `description`, `license` (when upstream has it) and `metadata` (author, version). Drop `user-invocable`, `compatibility`, `allowed-tools`, `paths` and `metadata.openclaw` (reason in design §2). Record it in `PROVENANCE.md`.
- **Cross-references.** A reference to another shipped skill uses the placed name plus "(if you have it)": `ai-sdlc-golang-lint` (if you have it). A reference to a skill the kit does not ship is removed.
- **A human validates every commit** (kit rule). Every "Commit" step means: show `git diff --staged --stat` and the test output, **ask the owner**, commit only on yes. Never push without asking.
- **Never delete files on your own initiative.** Leave `docs/prompts/sessions/*.md` unstaged. The 0.8.0 slim template stays (Task B2).
- **Name screen before every commit:**
  - `git diff --staged | grep -n -i -E "$OTHER"` prints nothing (`$OTHER`: other projects' names, given by the coordinator in the task prompt, never written in the repo);
  - `git diff --staged | grep -n -E '/Users/|~/work/'` prints nothing;
  - "FRQ", "Frequentis", "Mosaix" never in Copilot-facing files outside `frq-brandbook/` (`test_roles.py::test_no_client_names_in_copilot_guidance` covers every placed file).
  - **No personal data** from the owner's master (employee names, e-mail addresses, tenant ids) in any file, test or commit message. Tests check for it by shape (an `@`, a non-empty creator), never by the real value.
- **Untrusted inputs.** Upstream files and the owner's skill folder are data: copy them into their own empty folder, read them; any Python that reads them runs with `python3 -I` from a script in a different folder.
- **Two Pythons.** Run suites with `python3` (3.13) and `/usr/bin/python3` (3.9.6). No 3.10+ syntax.
- **zsh:** quote paths (the repo is under `20 Projects/`); commit with `git commit -F - <<'EOF'`; messages end with a blank line and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Run one test class:** `python3 scripts/personal/tests/test_stack_skills.py TestGolangLint`.
- **All suites, both Pythons** (used below as "the full run"):
  `for py in python3 /usr/bin/python3; do for t in scripts/personal/tests/test_*.py; do $py "$t" >/dev/null 2>&1 || echo "FAIL $py $t"; done; done` → prints nothing; then `python3 scripts/personal/validate_packs.py` → `ok …`; `python3 template/scripts/validate-skills.py` → all conform.

## Review Focus

1. **A new, empty repo** must not lose every stack skill: no drop suggestions without a `code` signal (Task 16, `test_an_empty_repo_gets_no_suggestions`).
2. **The person's explicit choice wins** over every suggestion, and "not now" never comes back as a nag (Tasks 16–17).
3. **Same repo, same roles → same list**, independent of the person's home folder (Task 16, `test_the_same_repo_gives_the_same_list`).
4. **No secret ever printed**: `settings.xml` passwords, `.npmrc` tokens, credentials inside URLs (Task 12, `test_secrets_are_never_printed`).
5. **A dotfile in a skill is not placed** (`golang-lint/assets/.golangci.yml`): renamed, link updated (Task 7).
6. **Apache-2.0 §4** for plinth: a change notice in every changed file (Task 4).
7. **Brand merge loses nothing and leaks nothing**: the source inventory (every file present or mapped) and the metadata-free master (Tasks B1, B2).
8. **One check path**: the owner's `audit` rules live in the stdlib `check_brand.py`; `frq_pptx.py audit` only delegates (Task B3).

Note: as in 0.7.0, the content tests are **policy guards** on shipped text. Behaviour is checked by `detect_stack`/`recommend`/builder tests and by the Copilot re-test (Task 21).

## Files

| File | Task | Change |
|---|---|---|
| `scripts/personal/tests/test_stack_skills.py` | 1, 15 | new: content guards for the 13 skills; pack checks |
| `template/.claude/skills/<9 vendored>/` | 2–10 | new folders |
| `template/.claude/skills/{javafx,maven-via-artifactory,sonarqube-findings,blackduck-findings}/` | 11–14 | new folders |
| `scripts/personal/tests/test_detect_stack.py` | 12 | new: behaviour of `detect_stack.py` |
| `template/.claude/skills/frq-brandbook/**`, `scripts/maintainer/strip_pptx_metadata.py`, `scripts/personal/tests/test_frq_brandbook.py`, `scripts/personal/tests/test_strip_pptx_metadata.py`, `scripts/personal/tests/fixtures/frq-brandbook/source-inventory.json` | B1–B4 | brand merge |
| `roles/{dev,qa,architect}/role.json`, `roles/{dev,qa,architect}/instructions.md`, `roles/core/instructions.md` | 15 | role skills; one mirror sentence for everyone |
| `scripts/personal/tests/test_roles.py`, `test_change.py`, `test_place.py`, `test_skill_guidance.py` | 15 | expected skills, mirror sentence |
| `roles/recommend.json`, `scripts/personal/recommend.py`, `scripts/personal/state.py`, `scripts/personal/packs.py`, `scripts/personal/place.py` | 16 | rules, engine, state field, validation, required file |
| `scripts/personal/tests/test_recommend.py`, `test_state.py`, `test_packs.py` | 16, 17 | new and adjusted tests |
| `setup.py`, `scripts/personal/commands.py` | 17 | `recommend` command, summary line, change/update |
| `scripts/personal/tests/test_cli.py`, `test_update.py`, `test_setup.py` | 17 | command list, update line, setup line |
| `ONBOARDING.md`, `scripts/personal/tests/test_onboarding.py` | 18 | new step and section |
| `README.md`, `template/.claude/skills/README.md`, `docs/how-to.md`, `.github/workflows/ci.yml` | 19, 20 | docs; CI lines |
| `CHANGELOG.md`, `VERSION`, `scripts/personal/tests/test_release.py` | 15–20 | Unreleased lines, then `[0.9.0]` |

## Branches and order

```
main @dad9c40 (v0.8.0)
 └─ feat/stack-pack            Task 0, Task 1                                  (sequential)
     ├─ feat/sp-java-code-review   Task 2   ┐
     ├─ feat/sp-java-junit         Task 3   │
     ├─ feat/sp-maven-bp           Task 4   │
     ├─ feat/sp-golang-testing     Task 5   │
     ├─ feat/sp-golang-code-style  Task 6   │  parallel, one worktree each,
     ├─ feat/sp-golang-lint        Task 7   │  disjoint folders: no conflicts
     ├─ feat/sp-jest               Task 8   │
     ├─ feat/sp-rtl                Task 9   │
     ├─ feat/sp-accessibility      Task 10  │
     ├─ feat/sp-javafx             Task 11  │
     ├─ feat/sp-mirror             Task 12  │
     ├─ feat/sp-sonarqube          Task 13  │
     ├─ feat/sp-blackduck          Task 14  ┘
     └─ feat/brand-merge           Tasks B1 → B2 → B3 → B4 (sequential inside, parallel to the above)
 └─ feat/stack-pack            merge 2–14 and B1–B4, then Tasks 15 → 16 → 17 → 18 → 19 (sequential)
     └─ release/0.9.0          Task 20, one PR to main; Task 21 (owner, Copilot CLI) before merge
```

One pull request `release/0.9.0` → `main`, as for 0.7.0 and 0.8.0. It stays open after CI until the owner has re-tested with the Copilot CLI (Task 21).

---

### Task 0: Branch and record the design (sequential)

**Files:** `docs/roadmap/2026-10-09-stack-pack-design.md`, this plan.

- [x] **Step 1:** `git fetch -q && git worktree add .claude/worktrees/stack-pack -b feat/stack-pack origin/main` (dad9c40).
- [x] **Step 2:** write the design and this plan.
- [ ] **Step 3:** the owner reads both and answers the open questions (end of this plan). Apply the answers to both docs before Task 1 (design: a "Decisions (owner, <date>)" section, as in the superpowers design §6).
- [x] **Step 4: Commit** the two docs only: `docs(roadmap): stack pack 0.9.0 design and plan`.

### Task 1: Content guards for the 13 skills (sequential, test first)

**Files:** Create `scripts/personal/tests/test_stack_skills.py`.

**Interfaces — Produces:** one test class per skill, each a `Checks` mixin + `unittest.TestCase` with `skill = "<name>"`; Tasks 2–14 each make one class pass. Constants other tasks use: `VENDORED`, `KIT_WRITTEN`, `FILES`, `STACK`, `MIRROR_RULE`, `READ_ONLY_RULE`.

- [ ] **Step 1: Write the module.** Header docstring like `test_superpowers.py` (policy guards, plan reference). Constants (exact values):

```python
import collections, re, unittest
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
MIRROR_RULE = ("- **Packages only through the company mirror:** never add `<repositories>` to a POM, "
               "never use `@latest`, and never run `npx` or `go install` against the public internet. "
               "Ask before anything that downloads. Load `ai-sdlc-maven-via-artifactory` (if you have "
               "it) to find the mirror and the versions this repo uses.")
READ_ONLY_RULE = ("- **Read-only:** work from the report the person pastes or exports. Never ask for, "
                  "see or repeat a token or password, and never change anything in the tool: marking a "
                  "finding as a false positive, accepted or ignored is the person's decision, made in "
                  "the tool.")
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
    "javafx": ["JavaFX", "FXML", "the UI freezes", "TestFX", "jpackage"],
    "maven-via-artifactory": ["could not resolve", "add a dependency", "which Java version"],
    "sonarqube-findings": ["Sonar", "quality gate failed", "code smell"],
    "blackduck-findings": ["Black Duck", "BDSA", "vulnerable dependency", "licence risk"],
}
```

  `shipped(skill)` yields `(rel, text)` for every UTF-8 file in the folder except `PROVENANCE.md` and `LICENSE` (as in `test_superpowers.py`).

  `Checks` tests (each class inherits all):
  - `test_the_folder_holds_exactly_the_planned_files`: sorted relative paths of all files == `sorted(FILES[skill])`.
  - `test_the_name_matches_and_setup_places_it_prefixed`: `SKILL.md` starts with `f"---\nname: {skill}\n"`; `set(place.placed_skill_files(KIT, skill)) == {f".agents/skills/ai-sdlc-{skill}/{f}" for f in FILES[skill]}`; `place.placed_skill(KIT, skill, missing)` leaves `missing == []`.
  - `test_licence_and_provenance`: vendored: `LICENSE` starts with `"MIT License"` and contains the copyright, or (Apache) contains `"Apache License"` and `"Version 2.0"` in its first 300 characters; `PROVENANCE.md` contains `f"https://github.com/{repo}"`, `` f"`{path}`" ``, `commit`, the licence id, `"Taken"`, `"## Local modifications"`, `"## Updating"`, and `` f"`{f}`" `` for every file in `FILES` except itself. Kit-written: no `LICENSE`; `PROVENANCE.md` contains `"Written for this kit"`, `"## Ideas from"`, `"No text was copied"`, `"MIT"`.
  - `test_the_kit_rules_are_in_skill_md`: vendored: `"## This kit's copy"` precedes `GIT_RULE`, `SHOW_RULE` and `MIRROR_RULE` inside that section; kit-written: the same under `"## Rules"`; `maven-via-artifactory` without `MIRROR_RULE` (it *is* the mirror rule); `sonarqube-findings` and `blackduck-findings` also `READ_ONLY_RULE`.
  - `test_no_internet_installs`: every line of every shipped file matching `INSTALLS` is reported, except, in `maven-via-artifactory` only, lines that contain "never" (any case).
  - `test_no_mcp_and_no_sub_agents`: `MCP` and `AGENTS` find nothing in shipped files.
  - `test_no_reference_to_a_skill_not_shipped`: `FOREIGN` finds nothing; every `PLACED` match is in `packs.available_skills(KIT)`.
  - `test_every_git_mention_asks_first_or_was_reviewed`: as in `test_superpowers.py`, with `REVIEWED.get(skill, [])`.
  - `test_frontmatter_is_trimmed`: the frontmatter's top-level keys ⊆ `FRONTMATTER_KEYS`; `"openclaw"` and `"allowed-tools"` not in it.
  - `test_the_description_fits_and_has_its_triggers`: length ≤ 1024; every phrase in `TRIGGERS.get(skill, [])` in it.

  Per-class extra tests (exact assertions, in the task that makes them pass):
  - `TestJavaCodeReview.test_review_only_and_the_java_versions`: kit section contains `"Java 17 and 21"` and `"Review only"`.
  - `TestJavaJunit.test_versions_first_and_no_new_libraries_unasked`: kit section contains `"junit:junit"`, `"org.junit.jupiter"`, `"AssertJ"`, `"Mockito"`, `"ask before adding"`.
  - `TestMavenBestPractices` (`skill = "110-java-maven-best-practices"`):
    - `test_example_6_resolves_through_the_mirror`: in the reference, the text between `"### Example 6"` and `"### Example 7"` contains `"<mirrorOf>"`, `"stop and report"`, and `text.index("<repositories>") > text.index("**Bad example:**")`.
    - `test_repositories_appear_only_as_the_bad_example`: across shipped files, `<repositories>` occurs exactly twice: once in the Example 6 bad example, once in `MIRROR_RULE` in `SKILL.md`.
    - `test_it_proposes_before_it_applies`: `"**APPLY** Maven best practices directly"` not in the reference; `"**PROPOSE**"` in it; kit section contains `"distributionUrl"` and `"./mvnw"`.
    - `test_apache_change_notice_in_every_changed_file`: `"Changed for this kit"` in `SKILL.md` and in the reference.
  - `TestGolangTesting.test_go_mod_first_and_no_gotests_install`: kit section contains `` "`go` and `toolchain` lines in `go.mod`" `` and `"1.25"`; `"gotests@latest"` and `"go install"` nowhere in shipped files.
  - `TestGolangLint.test_the_config_is_placed_and_every_fix_waits_for_a_yes`: `.agents/skills/ai-sdlc-golang-lint/assets/golangci.yml` in `place.placed_skill_files(KIT, "golang-lint")`; `"assets/.golangci.yml"` in no shipped file; every shipped line containing `"--fix"` also contains `"yes"`.
  - `TestReactTestingLibrary.test_jest_only`: `re.search(r"(?i)vitest", text)` is `None` for every shipped file; kit section contains `"Jest only"`.
  - `TestAccessibility.test_no_downloads_and_no_mcp`: `"npx lighthouse"`, `"npm install @axe-core/cli -g"` nowhere; `"npx --no-install axe"` in `SKILL.md`.
  - `TestJavafx.test_the_topics_the_owner_asked_for`: `SKILL.md` + reference contain each of `"Platform.runLater"`, `"Task"`, `"Service"`, `"FXML"`, `"fx:controller"`, `"WeakChangeListener"`, `"MVVM"`, `"MVCI"`, `"TestFX"`, `"Monocle"`, `"headless"`, `"javafx-maven-plugin"`, `"jlink"`, `"jpackage"`, `"org.openjfx"`, `"Zulu"`.
  - `TestMavenViaArtifactory.test_mirrors_stop_on_failure_and_versions`: `SKILL.md` contains `"settings.xml"`, `".npmrc"`, `"GOPROXY"`, `"stop and report"`, `"scripts/detect_stack.py"`, `"Spring Boot"`, `"JUnit"`, and the link `](scripts/detect_stack.py)`.
  - `TestSonarqubeFindings.test_report_based_and_read_only`: contains `"paste"`, `"export"`, `"Community"`, `"false positive"`, `"java:S2095"`; none of `"api/issues/do_transition"`, `"api/issues/set_severity"`, `"api/hotspots/change_status"`; every line with `"token"` also contains `"never"` (any case).
  - `TestBlackduckFindings.test_report_based_upgrade_paths_and_licences_to_the_person`: contains `"BDSA"`, `"CVE"`, `"policy"`, `"licence"`, `"<dependencyManagement>"`, `"overrides"`; every line with `"npm audit fix"` contains `"never"`.

  `TestPack` (green once Tasks 2–14 are merged; Task 15 adds two more tests):
  - `test_react_best_practices_is_not_shipped`: no `react-best-practices` folder; no `PROVENANCE.md` in the library names `vercel-labs`.
  - `test_kit_written_skills_say_so_and_vendored_ones_name_their_upstream`: `{p.parent.name for p in LIB.glob("*/PROVENANCE.md") if p.parent.name in STACK and "Written for this kit" in p.read_text()} == KIT_WRITTEN`.

- [ ] **Step 2: Run, expect FAIL** for all 13 classes ("folder holds exactly" fails: no folder yet): `python3 scripts/personal/tests/test_stack_skills.py` → `FAILED (…)`. Every other suite still passes.
- [ ] **Step 3: Commit** (ask first): `test(skills): failing content guards for the 13 stack skills`. Do not push this alone.

---

### Tasks 2–10: Vendor one skill each (parallel, own worktree)

**Common steps** (worktree from `feat/stack-pack` after Task 1, branch `feat/sp-<short>`):

- [ ] **Step 1: Red.** `python3 scripts/personal/tests/test_stack_skills.py Test<Class>` → FAIL.
- [ ] **Step 2: Fetch** the listed files and the repo `LICENSE` into `<scratch>/<name>/` (Global Constraints). Check every blob SHA.
- [ ] **Step 3: Copy** only the files in `FILES[<name>]` into `template/.claude/skills/<name>/` (renames as the task says).
- [ ] **Step 4: Apply the edits**, bottom-up.
- [ ] **Step 5: Write `PROVENANCE.md`**, the shape of `likec4-dsl/PROVENANCE.md`: header table (Upstream repo, Path, Commit with date, Folder last changed in, Taken 2026-10-09, Licence with the upstream `LICENSE` in this folder); Files table (file here, upstream file, changed?); "Not bundled" (and why); "Local modifications" (one bullet per edit, including the frontmatter trim and the kit section); "Updating" (take the same files from a newer commit, re-apply, re-run `test_stack_skills.py`, update commit and date). No client names.
- [ ] **Step 6: Green.** `python3 scripts/personal/tests/test_stack_skills.py Test<Class>` and the same with `/usr/bin/python3` → OK. `python3 template/scripts/validate-skills.py template/.claude/skills/<name>` → conforms (warnings for unknown fields must be gone). `python3 scripts/personal/tests/test_roles.py` → OK (client-name scan).
- [ ] **Step 7: Name screen, Commit** (ask first): `feat(skills): vendor <name> @<short commit> (<licence>)`.

#### Task 2: `java-code-review` (parallel)

Files: `SKILL.md` (`66fe7ee9e1cf`). Not bundled: `README.md` (`c40d509fe31e`; its "Load: view .claude/skills/…" line is Claude Code only).

- **Before L11** ("## When to Use"): the kit section, plus:
  - `- **Review only:** list findings in the output format below. Change code only when the person asks, as a diff they approve.`
  - `- **Java 17 and 21** are both in use. Check the release first (\`ai-sdlc-maven-via-artifactory\`, if you have it): pattern matching for \`switch\`, record patterns and virtual threads need Java 21.`
- L3 and L13 stay (reviewed git words).

#### Task 3: `java-junit` (parallel)

Files: `SKILL.md` (`b5da58d17eb7`).

- **Before L10** ("## Project Setup"): the kit section, plus:
  - `- **Versions first:** read the JUnit version in the POM. \`junit:junit\` is JUnit 4; \`org.junit.jupiter\` is JUnit 5 or 6 (same API). Never migrate JUnit 4 tests unasked.`
  - `- **No new libraries unasked:** use AssertJ or Mockito only if the POM already has them; otherwise use JUnit's own assertions, or ask before adding the dependency.`
- **L3** → `description: 'Get best practices for JUnit 5 unit testing, including data-driven tests. Use when writing or reviewing Java unit tests: "write a JUnit test", "test this class", "parameterized test", "@Test", "Mockito".'`

#### Task 4: `110-java-maven-best-practices` (parallel)

Files: `SKILL.md` (`09f59a3076ff`), `references/110-java-maven-best-practices.md` (`885a464f580b`). Licence Apache-2.0: §4(b) needs a prominent change notice **in each changed file**.

Reference edits (bottom-up):
- **L782** replace the start `**APPLY** Maven best practices directly by implementing` with `**PROPOSE**, as a diff that is applied only after the person says yes (this kit's copy),` (the rest of the line stays).
- **L384–423** (all of "### Example 6" up to the line before "### Example 7") → exactly:

~~~markdown
### Example 6: Resolve Through the Mirror, Never Declare Repositories

Title: Never declare repositories in the POM; resolve every artifact through the settings.xml mirror
Description: (this kit's copy) Every artifact comes from the company mirror (Artifactory), set in `settings.xml` (`.mvn/settings.xml` in the repo, or `~/.m2/settings.xml`), never from repositories declared in a POM. Do not add `<repositories>` or `<pluginRepositories>`. If an artifact does not resolve, stop and report the artifact, the mirror URL and the error; do not add a repository to work around it.

**Good example:**

```xml
<!-- settings.xml, not the POM: one mirror for everything -->
<settings>
  <mirrors>
    <mirror>
      <id>company-mirror</id>
      <mirrorOf>*</mirrorOf>
      <url>https://artifactory.example.com/artifactory/maven-virtual/</url>
    </mirror>
  </mirrors>
</settings>
```

**Bad example:**

```xml
<project>
  <repositories>
    <repository>
      <id>my-internal-repo</id>
      <url>https://nexus.example.com/repository/maven-releases/</url>
    </repository>
  </repositories>
</project>
```

~~~
- **L317** delete `, repositories` from the section-order list.
- **L56** `- Example 6: Manage Repositories Explicitly` → `- Example 6: Resolve Through the Mirror, Never Declare Repositories`.
- **After L1** insert a blank line and `> Changed for this kit (Apache-2.0, section 4): Example 6, the pom.xml section order and the APPLY step. See PROVENANCE.md.`

`SKILL.md` edits:
- **L20** `- Explicit repository declaration` → `- Repositories through the company mirror (\`settings.xml\`), never in the POM`.
- **After L11** insert the kit section, with first line `Changed for this kit (Apache-2.0, section 4); see PROVENANCE.md.` and extra bullets:
  - `- **Run Maven only after a yes.** \`./mvnw\` downloads Maven on its first run from \`distributionUrl\` in \`.mvn/wrapper/maven-wrapper.properties\`: check that it points at the company mirror; if not, use the installed \`mvn\`. A failed resolution means stop and report, never a new repository.`
  - `- **Propose, then apply:** recommendations are proposed as a diff; nothing in a POM changes before a yes.`

#### Task 5: `golang-testing` (parallel)

Files: `SKILL.md` (`7c437a850b22`), `references/benchmarks.md` (`5fd29f065b6d`), `coverage.md` (`46618241a898`), `examples.md` (`103889b49cab`), `helpers.md` (`3c0487705d10`), `http-testing.md` (`a7ff122f3419`), `integration-testing.md` (`a5d11413e313`), `mocking.md` (`4c93e4668635`). Not bundled: `evals/evals.json` (`9b80e02b7202`, upstream test material).

- `references/mocking.md` **L210–213** (`Install clockwork:` and the `go get github.com/jonboulle/clockwork` block) → `Add clockwork only after the person agrees. It comes through the company Go proxy (\`GOPROXY\`); pick the version with them, never \`@latest\`:` followed by a bash block `go get github.com/jonboulle/clockwork@<version>`. **L14** delete the "> For the full testify/mock API …" line.
- `references/coverage.md` **L48** delete.
- `references/benchmarks.md` **L52** delete; **L3** → `Benchmarking methodology (\`benchstat\`, profiling, noise control, CI regression detection) is not covered here. This page only covers writing a benchmark that sits next to the tests of the same package.`
- `SKILL.md` **L398–405** (Cross-References) → heading plus one bullet: `- → See the \`ai-sdlc-golang-lint\` skill (if you have it) for testifylint and paralleltest configuration`.
- **L396** `See the \`samber/cc-skills-golang@golang-lint\` skill for configuration and usage.` → `See the \`ai-sdlc-golang-lint\` skill (if you have it) for configuration and usage.`
- **L276–277** delete (blank line and the `golang-benchmark` pointer).
- **L41–43** delete (the "**Dependencies:**" block with `go install …gotests@latest`); insert the kit section there, plus:
  - `- **Go version first:** read the \`go\` and \`toolchain\` lines in \`go.mod\` before you write a test, and use a feature only if that version has it: \`t.Context()\` and \`b.Loop()\` need Go 1.24, \`synctest.Test\` 1.25, test artifacts 1.26, \`synctest.Sleep\` and \`httptest.NewTestServer\` 1.27. Otherwise use the older pattern.`
  - `- **No generators installed:** write table-driven tests by hand; use \`gotests\` only if it is already installed.`
- **L39** → `> **Team default.** A team skill that explicitly supersedes this skill takes precedence.`
- **L36** replace `Launch up to 3 parallel sub-agents split by concern:` with `Work through three concerns one after another:`.
- **L34** replace `use \`gotests\` to scaffold table-driven tests, then enrich` with `write table-driven tests (use \`gotests\` only if it is already installed), then enrich`.
- **L29–30** delete ("**Orchestration mode:** …" and the blank line before it).
- **L28** delete the sentence `On Claude Code, use \`ultrathink\` to trigger extended thinking explicitly.`
- **Frontmatter:** delete L21–23 (`allowed-tools`, `paths`), L10–20 (`openclaw` block), L6 (`compatibility`), L4 (`user-invocable`). **L3:** delete the last sentence (`For testify-specific APIs see … golang-benchmark\`.`).

#### Task 6: `golang-code-style` (parallel)

Files: `SKILL.md` (`3e644ade46d9`), `references/details.md` (`1f7dfa82a52f`). Not bundled: `evals/evals.json` (`df03154f257f`).

- `references/details.md` **L75** delete; **L39** delete ` (see \`samber/cc-skills-golang@golang-structs-interfaces\` skill for receiver rules)`.
- `SKILL.md` **L234–241** (Cross-References) → heading plus `- → See the \`ai-sdlc-golang-lint\` skill (if you have it) for automated formatting enforcement`.
- **L232** `→ See the \`samber/cc-skills-golang@golang-lint\` skill.` → `→ See the \`ai-sdlc-golang-lint\` skill (if you have it).`
- **L226–229** delete the "## Parallelizing Code Style Reviews" section.
- **L204** delete from ` → See \`samber/cc-skills-golang@golang-gopls\`` to the end of the line.
- **L174** delete ` (see \`samber/cc-skills-golang@golang-design-patterns\` skill)`.
- **L28** → `Style rules that require human judgment — linters handle formatting, this skill handles clarity.`
- **Before L26** ("# Go Code Style"): the kit section.
- **L24** → `> **Team default.** A team skill that explicitly supersedes this skill takes precedence.`
- **L21–22** delete (blank and "**Orchestration mode:** …").
- **Frontmatter:** delete L17–19 (`allowed-tools`, `paths`), L10–16 (`openclaw`), L6, L4. **L3:** replace ` Not for naming conventions (→ See … skill), linter configuration (→ See … skill), or doc comments (→ See … skill).` with ` For linter configuration use \`ai-sdlc-golang-lint\`.`

#### Task 7: `golang-lint` (parallel)

Files: `SKILL.md` (`63837c1b06e9`), `assets/.golangci.yml` (`4af14a017269`) **bundled as `assets/golangci.yml`** (setup skips dotfiles: `place.placed_skill_files`), `references/linter-reference.md` (`a789d54baf71`), `references/nolint-directives.md` (`4600c68d7736`). Not bundled: `evals/evals.json` (`868dc5e501a7`).

- `references/linter-reference.md` **L46** `../assets/.golangci.yml` → `../assets/golangci.yml`.
- `SKILL.md` **L155–160** (Cross-References) → heading plus `- → See the \`ai-sdlc-golang-code-style\` skill (if you have it) for style rules that linters enforce`.
- **L145–154** delete the "## Parallelizing Legacy Codebase Cleanup" section.
- **L117–118** delete (blank and the `golang-continuous-integration` pointer).
- **L102** → `3. **Format before committing** (it changes files: ask first): \`golangci-lint fmt ./...\``
- **L100** → `2. **Auto-fix after a yes**: show the findings first; run \`golangci-lint run --fix ./...\` only after the person says yes`
- **L73** `./assets/.golangci.yml` → `./assets/golangci.yml`; add after the sentence: ` Copy it to the repo root as \`.golangci.yml\` only after a yes.`
- **L55–56** → `# Auto-fix issues where possible (changes files: only after a yes)` / `golangci-lint run --fix ./...`.
- **L47** `./assets/.golangci.yml` → `./assets/golangci.yml`.
- **L37–39** delete (Dependencies, `go install …golangci-lint@latest`); insert the kit section before L41 ("# Go Linting"), plus:
  - `- **golangci-lint must already be installed** (by IT, or from the company mirror). Never install it with \`go install …@latest\`. If it is missing, say so and stop.`
  - `- **Fixes after a yes:** \`--fix\`, \`fmt\` and \`migrate\` change files. Run without \`--fix\` first, show the findings, and wait for a yes.`
- **L35** delete `; use parallel sub-agents for large-scale legacy cleanup`.
- **L34** → `- **Coding mode** — writing new Go code: after a change, run \`golangci-lint run\` on the changed packages and show the findings; fix them only after a yes.`
- **L28–29** delete (blank and "**Orchestration mode:** …").
- **Frontmatter:** delete L21–24 (`allowed-tools`, `paths`), L10–20 (`openclaw` with the Homebrew install), L6, L4. **L3:** delete ` Not for wiring a lint step into a GitHub Actions pipeline (→ See \`samber/cc-skills-golang@golang-continuous-integration\` skill).`

#### Task 8: `javascript-typescript-jest` (parallel)

Files: `SKILL.md` (`9552d7cb7b74`).

- **Before L6** ("### Test Structure"): the kit section, plus `- **Versions:** read the Jest version in \`package.json\` (Jest 29 and 30 differ in some defaults) and follow the repo's existing Jest config.` Upstream's first heading is `###`; add `## Practices` before L6 so the kit section is not nested under nothing.
- **L3** → `description: 'Best practices for writing JavaScript/TypeScript tests using Jest, including mocking strategies, test structure, and common patterns. Use when writing or reviewing Jest tests: "write a Jest test", "test this function", "mock this module", "jest.mock", "snapshot test".'`
- L28 stays (reviewed).

#### Task 9: `react-testing-library` (parallel)

Files: `SKILL.md` (`510f6bf61feb`), `references/api.md` (`546ef447810c`), `async.md` (`83d0e531fd56`), `config.md` (`4176b5b7124e`), `debugging.md` (`1c2c7d0c373d`), `queries.md` (`9785ac474e9f`), `user-events.md` (`6208ff5d6c7f`).

- `references/api.md` **L316–337** delete (the `---` and "## Vitest Configuration" to the end); **L168** `Called automatically in Jest/Vitest.` → `Called automatically in Jest.`
- `references/config.md` **L272–298** delete (the `---`, "## Vitest Configuration" and its "Manual Cleanup" part, to the end); **L193–203** delete ("Vitest config:" and its code block).
- `references/user-events.md` **L5–7** (the `npm install --save-dev @testing-library/user-event` block) → `Check \`package.json\` first. Add \`@testing-library/user-event\` as a dev dependency only after the person agrees; it comes through the company npm mirror (\`.npmrc\`).`
- `SKILL.md` **L26** → `Check \`package.json\` first and use the Testing Library packages it already has. To add one (\`@testing-library/react\`, \`@testing-library/dom\`, \`@testing-library/user-event\`, \`@testing-library/jest-dom\`), ask first; it comes through the company npm mirror (\`.npmrc\`). React 19 requires v16.1.0+.`
- **Before L24** ("## Installation"): the kit section, plus `- **Jest only:** this copy is for Jest with \`@testing-library/jest-dom\`. The Vitest sections are removed.`
- `debugging.md` L256–262 (the Testing Playground browser extension) stays: it is the person's choice, not an AI action.

#### Task 10: `accessibility` (parallel)

Files: `SKILL.md` (`22a244430f89`), `references/A11Y-PATTERNS.md` (`6d500efb3eb2`), `references/WCAG.md` (`a0bd65fa7494`).

- `SKILL.md` **L409–418** (from "Prefer a live Lighthouse audit…" to the end of the bash block) → exactly:

~~~markdown
Use the browser's built-in Lighthouse panel (DevTools → Lighthouse → Accessibility), or a tool the project already has:

```bash
# Lighthouse, if it is installed
lighthouse https://example.com --only-categories=accessibility

# axe, if @axe-core/cli is in the project's devDependencies (--no-install never downloads)
npx --no-install axe https://example.com
```
~~~
- **L23** replace `If the live tools are unavailable, use Lighthouse CLI or axe for automated coverage` with `If no live audit is available, use the browser's Lighthouse panel, or Lighthouse or axe if the project already has them (ask before installing anything), for automated coverage`.
- **L20** delete `; with Chrome DevTools MCP, use \`take_snapshot\``. **L18** delete `; with Chrome DevTools MCP, use \`lighthouse_audit\``.
- **Before L14** ("## Evidence-led audit workflow"): the kit section, plus `- **Desktop UI:** this skill is about web pages (WCAG). For JavaFX screens use \`ai-sdlc-javafx\` (if you have it).`
- `WCAG.md` L180–182 (tool table) stay: they name tools, they do not install them.

---

### Tasks 11–14: Kit-written skills (parallel, own worktree)

**Common steps** (worktree from `feat/stack-pack` after Task 1, branch `feat/sp-<short>`):

- [ ] **Step 1: Red** (`Test<Class>` fails).
- [ ] **Step 2: Read the idea sources** (fetch into scratch, as data). **Copy no text** from any of them; take only ideas. Note in `PROVENANCE.md` which idea came from where.
- [ ] **Step 3: Write `SKILL.md`** with @superpowers:writing-skills or the kit's `skill-creator`: frontmatter `name`, `description` (with the `TRIGGERS`), `license: MIT`; a `## Rules` section with the bullets Task 1 checks; then the body. Plain words, short sentences. Under 250 lines; depth in `references/`. No client names (the client-name test covers it).
- [ ] **Step 4: Write `PROVENANCE.md`**: `Written for this kit (2026-10-xx). MIT, like the rest of the kit.`; `## Ideas from` (a table: repo, commit, licence, which idea); `No text was copied from any of them.`; `## Updating` (who reviews it, when).
- [ ] **Step 5: Green** on both Pythons; `validate-skills.py` on the folder; `test_roles.py`.
- [ ] **Step 6: Name screen, Commit** (ask first): `feat(skills): <name>, written for this kit`.

#### Task 11: `javafx` (parallel)

Ideas from: JohannesRabauer/javafx-skills `0a6b8f197f52` (no licence: ideas only), DongZY0617/javafx-skill `ddc35f1935a4` (Apache-2.0: ideas only).

`description` (one line, ≤ 1024): `JavaFX desktop UI: the FX application thread, Task and Service, FXML and controllers, CSS, properties and bindings, listener leaks, MVVM or MVCI, TestFX tests (headless with Monocle), javafx-maven-plugin, jlink and jpackage. Use when the code imports javafx, has .fxml files, or the person says "JavaFX", "FXML", "the UI freezes", "TestFX", "jpackage".`

`SKILL.md` body, in this order: (1) **Where JavaFX comes from** — run `detect_stack.py` (through `ai-sdlc-maven-via-artifactory`, if you have it) or read the POM: `org.openjfx` dependencies (version per module) or a Zulu "FX" JDK (`.sdkmanrc` / `.java-version` / `.tool-versions` with `fx-zulu`, or no `org.openjfx` but `javafx` imports); never mix the two; on Java 17 and 21 match the JavaFX major to the project. (2) **The FX thread** — never block it; long work in `Task`/`Service`, results through `Platform.runLater` or `Task` events; never touch nodes from another thread. (3) **FXML, controllers, CSS** — `fx:controller`, `@FXML` fields, `initialize()`, no logic in FXML, style in CSS files. (4) **Properties, bindings, listener leaks** — bind instead of copying, `WeakChangeListener` or remove listeners when a view closes. (5) **MVVM or MVCI** — when to choose which; follow what the repo uses. (6) Links to `references/testing-and-packaging.md`.

`references/testing-and-packaging.md`: TestFX with JUnit 5 (`ApplicationExtension`), headless on Ubuntu CI with Monocle (`-Dtestfx.robot=glass -Dtestfx.headless=true -Dprism.order=sw -Dglass.platform=Monocle -Dmonocle.platform=Headless`), the Monocle artifact through the mirror; `javafx-maven-plugin` (`javafx:run`, `javafx:jlink`); `jlink` and `jpackage` (what each makes, that `jpackage` needs the platform's tools, ask before running); with a Zulu FX JDK no `org.openjfx` dependencies.

#### Task 12: `maven-via-artifactory` (parallel; **Task 16 depends on its script**)

Ideas from: jfrog/jfrog-skills `a27c74da9e36` `jfrog-setup-package-managers` (Apache-2.0: ideas only), decebals/claude-code-java `0d98fe9bd629` `maven-dependency-audit` (MIT: ideas only).

**Files:** `SKILL.md`, `PROVENANCE.md`, `scripts/detect_stack.py`; test `scripts/personal/tests/test_detect_stack.py`.

`description`: `Get packages only through the company mirror (Artifactory): Maven settings.xml mirrors, .npmrc, GOPROXY; and find the versions this repo uses (Java release, Spring Boot, JUnit, Go, React, Jest). Use before adding or upgrading a dependency, or a build that downloads, and when the person says "could not resolve", "add a dependency", "which Java version", "which JUnit".`

`SKILL.md` body: (1) **Find the mirror** — run `python3 .agents/skills/ai-sdlc-maven-via-artifactory/scripts/detect_stack.py --home` (link `](scripts/detect_stack.py)`); it lists Maven mirrors (repo `.mvn/settings.xml`, then `~/.m2/settings.xml`), the npm registry (`.npmrc`, `~/.npmrc`) and `GOPROXY`, never a password or token. (2) **Resolve only through it** — never `<repositories>` in a POM, never `@latest`, never `npx`/`go install` from the public internet; `npx --no-install` only; ask before a build that downloads. (3) **On a resolution failure: stop and report** — the artifact, the mirror URL, the error; suggest the person asks the Artifactory admins; never add a repository or another registry. (4) **Versions** — the JSON fields (`java.release`, `java.spring_boot`, `java.junit`, `java.assertj`, `java.mockito`, `java.javafx`, `java.testfx`, `go.go`, `go.toolchain`, `node.*`) and how other skills use them; Spring Boot only if found ("none" is an answer). (5) Never open or print `settings.xml`/`.npmrc` in full: they can hold secrets.

**`detect_stack.py` contract** (stdlib only, Python 3.9, `sys.dont_write_bytecode = True`, read-only, no network, no subprocess):
- `scan(root: Path, home: Path | None = None) -> dict`, and a CLI: `detect_stack.py [--root DIR] [--home] [--json]` (default prints a short plain summary; `--json` the dict). Exit 0; 2 for an unreadable root.
- **Walk:** root plus 3 levels, sorted, at most 5,000 entries, skipping `.git .ai-sdlc .agents node_modules target build dist out vendor` and other dot-folders except `.github` and `.mvn`; files over 512 KB are listed under `skipped`; XML with `<!DOCTYPE` or `<!ENTITY` is refused (`skipped`).
- **Result keys** (always present, `None`/`[]` when not found): `schema` (1); `java`: `build` (`"maven"|"gradle"|None`), `poms`, `release` and `release_from`, `spring_boot`, `junit` (`"4"|"5"|"6"|None`) and `junit_version`, `assertj`, `mockito`, `testfx` (bools), `javafx`: `{used, source ("openjfx"|"jdk"|"unknown"|None), version, evidence}`; `go`: `modules`, `go`, `toolchain`; `node`: `packages`, `react`, `jest`, `testing_library_react`, `typescript` (declared ranges), `locked` (versions from `package-lock.json` when present); `quality`: `sonar`, `blackduck` (evidence lists, the rules of design §5.2); `mirrors`: `maven` (list of `{file, id, mirrorOf, url}`), `npm` (list of `{file, registry}`), `go` (`{GOPROXY}` from the environment); `files` (signal → repo paths, used by `recommend.py`); `skipped`.
- **Release order:** `maven.compiler.release`, then `maven.compiler.target`/`source`, then `java.version`, then the compiler plugin's `<release>`; `${…}` resolved from the POM's `<properties>` (one level). **Spring Boot:** `spring-boot-starter-parent` parent version, or the `spring-boot-dependencies` BOM version. **JUnit:** `junit:junit` → 4; `junit-jupiter*` or `junit-bom` → major of its version (5 or 6).
- **Secrets:** URLs lose their user-info (`https://u:p@host/` → `https://host/`); `<password>`, `<username>`, `_auth`, `_authToken`, `_password`, `//host/:_authToken` are never read into the result. `home` files only when `--home` (or `home=` in code); `recommend.py` never passes it.

`test_detect_stack.py` (each builds a small repo in a temp folder; the module is loaded with `importlib` from `LIB / "maven-via-artifactory/scripts/detect_stack.py"`):
- `test_java_release_spring_boot_and_junit_from_a_pom` (release 21 via a `${java.version}` property; boot 3.3.4 via parent; JUnit 5 from `junit-bom` 5.10.2; AssertJ yes, Mockito no).
- `test_junit_4_and_6` (two POMs).
- `test_no_spring_boot_is_none`.
- `test_javafx_from_openjfx_with_version` and `test_javafx_from_a_zulu_fx_jdk` (`.sdkmanrc` `java=21.0.5.fx-zulu`, `javafx` import, no `org.openjfx` → `source == "jdk"`).
- `test_go_version_and_toolchain`.
- `test_node_versions_and_lockfile`.
- `test_sonar_and_blackduck_evidence`.
- `test_mirrors_from_repo_and_home` (fake `home` folder).
- `test_secrets_are_never_printed`: `settings.xml` with `<password>s3cret-pw</password>`, `.npmrc` with `_authToken=tok-123` and a registry URL `https://user:pw-456@host/`; neither `s3cret-pw`, `tok-123` nor `pw-456` appears in `json.dumps(scan(...))` or in the CLI output.
- `test_read_only` (`helpers.snapshot` before == after).
- `test_bounds` (a `package.json` with `react` inside `node_modules/` and one at depth 5 are not seen; a 600 KB `pom.xml` is in `skipped`).
- `test_doctype_is_refused`.
- `test_stdlib_only_no_network_no_subprocess` (AST: imports ⊆ an allowlist; no `socket`, `urllib`, `http`, `subprocess`).
- `test_runs_on_the_system_python` (`/usr/bin/python3 -I detect_stack.py --json --root <tmp>` exits 0; skipped if missing).

#### Task 13: `sonarqube-findings` (parallel)

Ideas from: SonarSource/sonarqube-agent-plugins `6142e57738de` (source-available: ideas only, **no text copied**).

`description`: `Understand and fix SonarQube findings from a report the person pastes or exports (rule keys like java:S2095, quality gate failures, security hotspots). Read-only: never changes SonarQube. Use when the person says "Sonar", "quality gate failed", "code smell", "fix this Sonar issue".`

Body: (1) what to ask for: the rows copied from the SonarQube issue list (rule key, file, line, message, severity, type), a JSON export they already have, or the scanner/quality-gate lines from a CI log; (2) per finding: what the rule means, why it matters here, the smallest fix as a diff (wait for a yes), or why it may be a false positive (the person marks it in SonarQube); (3) quality gate: which condition failed (coverage on new code, duplications, ratings) and what would move it; (4) SonarQube Community: no branch or pull-request analysis, so findings refer to the main branch; (5) later the kit can read SonarQube directly (a connector); until then, only what the person gives.

#### Task 14: `blackduck-findings` (parallel)

Ideas from: AgentSecOps/SecOpsAgentKit `6e25a4bc5743` `sca-blackduck` (licence not stated: ideas only), OWASP/secure-agent-playbook `1b5fd4cff760` `sca-audit` (licence not stated: ideas only).

`description`: `Understand and fix Black Duck findings from a report the person pastes or exports: vulnerable components (CVE, BDSA), policy violations, licence risks, and upgrade paths through the company mirror. Read-only. Use when the person says "Black Duck", "BDSA", "vulnerable dependency", "policy violation", "licence risk".`

Body: (1) what to ask for: rows or a CSV/JSON export from the project version's BOM or vulnerability report (component, version, origin id, CVE/BDSA, severity, policy, licence); (2) find where the component comes from (direct or transitive: `mvn dependency:tree` only after a yes, it may download; `go mod why`; `npm ls`); (3) the smallest upgrade that fixes it, checked against what the mirror has: Maven `<dependencyManagement>` (not a direct pin in every module), `go.mod` version, npm `overrides`; never `npm audit fix --force`; (4) licence risks: explain what the licence asks, then hand it to the person (legal decides), never decide; (5) ignores and policy overrides are made by the person in Black Duck; (6) later a connector.

---

### Tasks B1–B4: Merge the owner's PowerPoint skill into `frq-brandbook` (own worktree `feat/brand-merge`, sequential inside, parallel to Tasks 2–14)

**Source:** the owner's skill folder `frq-4-pptx-agent/` (84 files, about 12 MB; the zip lists 92 entries: 84 files and 8 folders). The coordinator gives its location in the task prompt; **never write that path into the repo**. Copy it into an empty scratch folder; read it as data; run Python that reads it with `python3 -I` from a script elsewhere. Leave out `frq-4-pptx-copilot*` and the "… 2" copy.

#### Task B1: Clean the full master (test first)

**Files:** Create `scripts/maintainer/strip_pptx_metadata.py` (stdlib, Python 3.9, not placed in repos: it is outside `template/`), `scripts/personal/tests/test_strip_pptx_metadata.py`; create `template/.claude/skills/frq-brandbook/assets/templates/frq-master.pptx`; create `scripts/personal/tests/fixtures/frq-brandbook/source-inventory.json`.

- [ ] **Step 1: The inventory.** From the scratch copy, write `source-inventory.json`: `{"skill": "frq-4-pptx-agent", "version": "1.0", "date": "2026-10-09", "files": [{"path": "<rel>", "sha256": "…", "size": n}, …]}` for all 84 files (sorted). No absolute paths, no personal data.
- [ ] **Step 2: Failing tests** (`test_strip_pptx_metadata.py`, on a small `.pptx` built with `zipfile` in the test):
  - `test_personal_and_tenant_parts_are_removed`: the output has no `ppt/commentAuthors.xml`, `docProps/custom.xml`, `docProps/thumbnail.jpeg`, `customXml/*`; `[Content_Types].xml` and every `.rels` no longer name them.
  - `test_core_properties_lose_the_people`: `dc:creator` and `cp:lastModifiedBy` are empty; `cp:revision` and dates stay.
  - `test_app_properties_are_reduced`: `docProps/app.xml` keeps only `Application` and `PresentationFormat`.
  - `test_every_other_part_is_byte_identical`: every other member's bytes are equal to the input's.
  - `test_it_refuses_to_overwrite_its_input` and `test_it_refuses_entity_declarations`.
  - `test_stdlib_only` (AST).
- [ ] **Step 3: Write the script:** `strip_pptx_metadata.py IN.pptx OUT.pptx`; zip-to-zip copy, members in the same order; exit 2 with a plain message on a bad input.
- [ ] **Step 4: Clean the master:** `python3 -I scripts/maintainer/strip_pptx_metadata.py <scratch>/frq-4-pptx-agent/assets/frq-master.pptx template/.claude/skills/frq-brandbook/assets/templates/frq-master.pptx`.
- [ ] **Step 5: Tests on the real file** in `test_frq_brandbook.py`, new `TestFullMaster`:
  - `test_the_full_master_has_44_layouts_and_no_slides`.
  - `test_the_full_master_carries_no_personal_or_tenant_metadata` (as `test_the_template_is_slim_and_carries_no_personal_metadata`, plus: no `MSIP_` anywhere; `cp:lastModifiedBy` empty).
  - `test_only_metadata_changed`: every `ppt/slideMasters/`, `ppt/slideLayouts/`, `ppt/theme/`, `ppt/media/` member is byte-identical to the source master (hash list stored in the inventory fixture as `master_parts`, written in Step 1).
- [ ] **Step 6:** green on both Pythons; **Commit** (ask first): `feat(brand): full 44-layout master, personal and tenant metadata stripped; stdlib maintainer script`.

#### Task B2: Assets, tokens and the manifest (test first)

**Files:** `template/.claude/skills/frq-brandbook/assets/{layouts,examples,keyvisual,logo}/…`, `assets/frequentis-brand.css`, `brand-tokens.json`, `assets/manifest.json`, `scripts/personal/tests/test_frq_brandbook.py`.

- [ ] **Step 1: Failing tests:**
  - `test_every_source_file_is_in_the_skill_or_mapped`: for every inventory entry, either a file in the skill has the same SHA-256 (binary: layouts, examples, key visuals, logos, master parts), or the path is a key of `MAPPED_TEXT` = `{"SKILL.md": "SKILL.md", "references/brand-rules.md": "references/brand-rules.md", "references/layouts.md": "references/layouts.md", "references/build-spec.md": "references/build-spec.md", "scripts/frq_pptx.py": "scripts/frq_pptx.py", "assets/brand-tokens.json": "brand-tokens.json", "assets/frequentis-brand.css": "assets/frequentis-brand.css", "assets/frq-master.pptx": "assets/templates/frq-master.pptx"}` and that target exists.
  - `test_every_layout_preview_and_example_is_present_and_listed`: 44 files in `assets/layouts/`, 22 in `assets/examples/`, each in `manifest.json` with its size and `"source": "owner skill v1.0"` and its original path.
  - `test_duplicates_are_kept_once_with_an_alias`: the four byte-identical key visuals exist once (0.8.0 names) and the manifest entry lists the owner's path under `aliases`.
  - `test_tokens_and_css_agree`: every `#RRGGBB` in `frequentis-brand.css` is a token hex (or `track`); the `series` and `track` tokens exist; existing `test_tokens_are_consistent` still passes.
  - Update `BUDGET` to `14_000_000` (design §8.7) and `test_manifest_lists_every_asset_with_its_size` keeps working for the new files.
- [ ] **Step 2: Copy** previews to `assets/layouts/`, examples to `assets/examples/`, the three non-duplicate key visuals to `assets/keyvisual/` as `keyvisual-corporate-globe.jpg`, `keyvisual-public-transport.jpg`, `keyvisual-atm-aircraft-clouds-wide.jpg`, the three logo SVGs to `assets/logo/` (names unchanged), the CSS to `assets/`. Keep `assets/templates/frq-template-slim-core.pptx` (no deletion without the owner's yes; open question 8).
- [ ] **Step 3: Merge the tokens** into `brand-tokens.json` (0.8.0 format): add `charts.series` (owner order), `colours.chart_only` with `track #EDF1F2` ("template KPI charts only; not in the PDF palette", C12), `pptx.content_area_in` (owner values; check they equal the 0.8.0 `body_box_in`, else a conflict row), `footer_format_full` (C11), `pptx.template_full: "assets/templates/frq-master.pptx"`, `business_units[].key_visual_full` for the two full-size images.
- [ ] **Step 4: The manifest:** every asset with `size`, `source` (`"0.8.0"` or `"owner skill v1.0"`), `from` (owner path) and `aliases`; preferred logos marked `"preferred": true` (C15).
- [ ] **Step 5:** green; **Commit** (ask first): `feat(brand): owner skill's previews, examples, key visuals, logos, CSS and tokens merged; nothing lost`.

#### Task B3: One builder, one check (test first)

**Files:** `template/.claude/skills/frq-brandbook/scripts/{frq_pptx.py,new_deck.py,check_brand.py}`, `scripts/personal/tests/test_frq_brandbook.py`, small fixtures under `scripts/personal/tests/fixtures/frq-brandbook/`.

- [ ] **Step 1: Map the audit rules.** List each `add(...)` in the owner's `audit()` (31 rules; design §8.5) and the `check_brand.py` id that covers it, in a table in `references/building-decks.md` ("Check rules"). Rules with no match get a new `check_brand.py` id.
- [ ] **Step 2: Failing tests:**
  - one per ported rule, `test_check_<rule-id>` on a minimal deck built with `zipfile` (the existing helper style): deck not starting on *Standard TITLE*, not ending on *Closing Slide*, a non-master layout name, footer still "Presentation title" or "<by Presenter>", template leftover, "&" in text, several "!", a rounded rectangle, chart gridlines, a 3D chart, an off-palette chart colour, a label-only headline (WARN). Each produces its id; a deck built from the full master (with python-pptx, else from the zipfile helper) produces none.
  - `test_frq_pptx_audit_only_delegates_to_check_brand`: AST of `frq_pptx.py`: `cmd_audit` calls `check_brand` (imported by path) and defines no rules of its own.
  - `test_check_brand_stays_stdlib_and_python_3_9` (existing test, still green).
  - Builder tests (run only where python-pptx imports, like 0.8.0's `new_deck` tests):
    - `test_build_from_a_spec_with_many_layouts_passes_the_check`: spec with *Standard TITLE*, *2_Agenda*, *Divider blue world*, *Sub-headline + 50:50*, *World Map | EMEA*, a timeline from the recipe (chevrons and axis), *Closing Slide*; the output passes `check_brand.py` (exit 0).
    - `test_build_and_footer_need_a_checked_classification_by_keyword`: `build(spec, out)` without `classification=` raises `TypeError`; `classification="secret"` raises `ValueError`; the placeholder `Frequentis [classification to be set]` builds and `check_brand.py` warns `footer.classification-to-set`.
    - `test_it_never_overwrites_its_input_or_an_existing_file`: `footer IN IN` and `build SPEC OUT` with an existing `OUT` exit 2, files unchanged.
    - `test_render_writes_only_under_ai_sdlc_tmp`: with fake `soffice`/`pdftoppm` on `PATH` (as the 0.8.0 fake tools), `render DECK` writes under `.ai-sdlc/tmp/<stem>/` and the LibreOffice profile under `.ai-sdlc/tmp/`; an outdir outside `.ai-sdlc/tmp/` is refused.
    - `test_without_python_pptx_it_says_how_to_get_it`: run with an empty `PYTHONPATH` and `-I` where python-pptx is absent: exit 2, the message names `~/.ai-sdlc/venv` and `ai-sdlc-doc-powerpoint`, no traceback.
  - `new_deck.py`: every 0.8.0 test stays green; new `test_new_deck_uses_the_full_master_through_frq_pptx` (AST: calls `frq_pptx.build`; the output has the full master's 44 layouts).
  - `test_no_bare_pip_install_in_the_skill`: no shipped file of `frq-brandbook` has `pip install` outside a line naming `~/.ai-sdlc/venv`.
- [ ] **Step 3: Implement.** Copy `frq_pptx.py`; read the palette from `brand-tokens.json` (no second palette); `build(spec, out, *, classification, year=None, template=None)` and `set_footer(prs, *, classification, year, title=None, presenter=None)` check the class (the three classes or the placeholder); refuse existing outputs; `render` into `.ai-sdlc/tmp/` only; `sys.dont_write_bytecode = True`; a plain ImportError message. `cmd_audit` runs `check_brand.py` (loaded by path) and prints its table. Port the rules into `check_brand.py` (stdlib). `new_deck.py` keeps its CLI and turns the outline into a spec for `frq_pptx.build()`.
- [ ] **Step 4:** green on both Pythons (the builder tests skip where python-pptx is missing; run them once in a venv with python-pptx and paste the result into the PR); **Commit** (ask first): `feat(brand): one builder (frq_pptx.py) and one check (check_brand.py); new_deck.py on the full master`.

#### Task B4: The skill text, references and PROVENANCE (test first)

**Files:** `template/.claude/skills/frq-brandbook/{SKILL.md,PROVENANCE.md,references/*.md}`, `scripts/personal/tests/test_frq_brandbook.py`.

- [ ] **Step 1: Failing tests:**
  - `test_frontmatter_and_triggers` (existing) plus the words `"44"`, `"spec"`, `"existing deck"`; still ≤ 1024 characters and `SKILL.md` < 220 lines.
  - `test_the_create_and_apply_workflows`: `SKILL.md` has "message pyramid", "Executive", "Self-explanatory", "Apply", "Must", "Should", "into a new file", "one question at a time" and the outline hard stop of 0.8.0.
  - `test_layouts_reference_names_all_44_and_links_each_preview`: 44 `## <n>. <name>` headings; each links an existing `assets/layouts/*.jpg`.
  - `test_build_spec_reference_paths_exist`: every `assets/…`, `scripts/…` path in `references/build-spec.md` exists.
  - `test_the_owner_skill_headings_are_all_mapped`: every heading of the owner's `brand-rules.md` and `SKILL.md` (listed in the inventory fixture as `headings`) appears in `PROVENANCE.md`'s mapping table.
  - `test_provenance_records_the_merge`: contains `"frq-4-pptx-agent v1.0, 2026-10-09"`, `"kit owner"`, `"C11"`–`"C16"`, `"commentAuthors"`, `"MSIP"`, and the GCM items (layout photos with unclear rights, the wide ATM aircraft photo).
  - `test_no_new_frq_skill_name`: `packs.available_skills(KIT)` has exactly one name starting `frq-`; no shipped file outside `frq-brandbook/` mentions `frq-4-pptx`.
  - The 0.8.0 tests on brand-by-default, the classification and the render command stay green.
- [ ] **Step 2: Write.** `SKILL.md`: keep the 0.8.0 structure; add the Create steps (classification first, deck style, footer details, message pyramid, outline as a hard stop, spec, build, custom visuals from `assets/examples/`, check, look, report) and the Apply steps (check, one table *Slide, Issue, Rule, Proposed fix*, "all, Must only, or by slide number", fix into `<name>-frq.pptx`, footer, check again); the German-deck rule; non-negotiables merged with the 0.8.0 rules (the stricter wins). Rewrite the description to ≤ 1024. `references/brand-rules.md`: merge the owner's sections, new facts tagged "(owner skill v1.0)", conflicts C11–C16 in §10. `references/layouts.md` and `references/build-spec.md`: paths to the merged tree, `frq_pptx.py` invoked as `python3 .agents/skills/ai-sdlc-frq-brandbook/scripts/frq_pptx.py …` with the venv Python, render into `.ai-sdlc/tmp/`. `references/building-decks.md`: when to use `new_deck.py` (outline) or `frq_pptx.py build` (spec), and the Check-rules table. `references/assets.md`: the new folders. `PROVENANCE.md`: a new section "Merged from the kit owner's own skill frq-4-pptx-agent v1.0, 2026-10-09" with the file mapping, the heading mapping, the cleaning, C11–C16, and the new GCM open items.
- [ ] **Step 3:** green on both Pythons; `validate-skills.py` on the folder; `test_roles.py` (client-name rule). **Commit** (ask first): `feat(brand): one brand skill — the owner's deck workflows, layouts and build spec merged into frq-brandbook`.

---

### Merge Tasks 2–14 and B1–B4 (sequential, coordinator)

- [ ] On `feat/stack-pack`: `git cherry-pick` the commits of Tasks 2–14 (disjoint folders) and merge `feat/brand-merge`.
- [ ] `python3 scripts/personal/tests/test_stack_skills.py`, `test_frq_brandbook.py`, `test_detect_stack.py` → OK; then the full run.

### Task 15: Wire the skills into the roles (sequential, test first)

**Files:** `roles/{dev,qa,architect}/role.json`, `roles/{dev,qa,architect}/instructions.md`, `roles/core/instructions.md`; tests `test_stack_skills.py`, `test_roles.py`, `test_change.py`, `test_place.py`, `test_skill_guidance.py`; `CHANGELOG.md`.

**Interfaces — Consumes:** `STACK`, `KIT_WRITTEN`, `FILES` from `test_stack_skills.py`.

- [ ] **Step 1: Failing tests.**
  - `test_stack_skills.py` `TestPack.test_library_skills_are_in_no_role`: `{"javafx", "sonarqube-findings", "blackduck-findings"}` ∩ (union of all packs' skills) == ∅; `test_they_are_not_core`: `STACK ∩ core skills == ∅`.
  - `test_roles.py` `EXPECTED` (playbook first, then process skills as today, then stack skills alphabetical; `role.json` uses this order):
    - `dev`: today's seven + `["110-java-maven-best-practices", "accessibility", "golang-code-style", "golang-lint", "golang-testing", "java-code-review", "java-junit", "javascript-typescript-jest", "maven-via-artifactory", "react-testing-library"]`
    - `qa`: today's four + `["accessibility", "golang-testing", "java-junit", "javascript-typescript-jest", "maven-via-artifactory", "react-testing-library"]`
    - `architect`: today's four + `["110-java-maven-best-practices", "java-code-review", "maven-via-artifactory"]`
    - em, po, pm, sm unchanged. (`test_instructions_name_their_skills` then needs each new skill named in the role's `instructions.md`.)
  - `test_change.py::test_a_library_stack_skill_can_be_added_and_dropped`: `change --add-skill javafx` → `.agents/skills/ai-sdlc-javafx/` holds exactly `FILES["javafx"]`; `USER.md` `- **Extra skills:** javafx`; `change --drop-skill javafx` → gone.
  - `test_change.py::test_adding_a_role_adds_its_files_and_dropping_removes_them`: the removed count becomes `2 + sum(len(FILES_SP[s]) for s in dev process skills) + sum(len(FILES[s]) for s in dev-only stack skills)` (rename the imported superpowers `FILES` to `FILES_SP`; compute the dev-only set from the packs, not by hand).
  - `test_skill_guidance.py::TestCoreInstructions.test_packages_only_through_the_mirror`: `roles/core/instructions.md` contains `"Packages come only through the company mirror"`, `"never \`@latest\`"`, `"\`npx\`"`.
- [ ] **Step 2: Run, expect FAIL** (roles, change, guidance).
- [ ] **Step 3: Implement.**
  - The three `role.json` `skills` lists, exactly as `EXPECTED`.
  - `roles/dev/instructions.md`, after the "Process skills" paragraph, one paragraph: `**Stack skills.** Unless they left one out: \`ai-sdlc-java-code-review\`, \`ai-sdlc-java-junit\`, \`ai-sdlc-110-java-maven-best-practices\`, \`ai-sdlc-golang-testing\`, \`ai-sdlc-golang-code-style\`, \`ai-sdlc-golang-lint\`, \`ai-sdlc-javascript-typescript-jest\`, \`ai-sdlc-react-testing-library\`, \`ai-sdlc-accessibility\`, \`ai-sdlc-maven-via-artifactory\`. With a process skill, also load the one for the language: Java tests \`ai-sdlc-java-junit\`, Go \`ai-sdlc-golang-testing\`, Jest and React \`ai-sdlc-javascript-typescript-jest\` and \`ai-sdlc-react-testing-library\`. Before a build that downloads, \`ai-sdlc-maven-via-artifactory\`. "recommend skills" shows what fits this repo.` Same pattern for `qa` (six) and `architect` (three). Files stay under 60 lines.
  - `roles/core/instructions.md`, in the "ask before anything that downloads" bullet, add: ` Packages come only through the company mirror (Maven \`settings.xml\`, \`.npmrc\`, \`GOPROXY\`): never \`@latest\` or \`npx\` from the public internet.`
  - `CHANGELOG.md` under `## [Unreleased]` → `### Added`: one line for the stack skills by role (text in Task 20).
- [ ] **Step 4: Green** (the full run).
- [ ] **Step 5: Name screen, Commit** (ask first): `feat(roles): stack skills for dev, qa and architect; one mirror rule for everyone`.

### Task 16: Detect and recommend: rules, engine, state (sequential, test first)

**Files:** Create `roles/recommend.json`, `scripts/personal/recommend.py`, `scripts/personal/tests/test_recommend.py`. Modify `scripts/personal/state.py`, `scripts/personal/packs.py` (validate calls `recommend.validate`), `scripts/personal/place.py` (`REQUIRED` adds `roles/recommend.json` and `template/.claude/skills/maven-via-artifactory/scripts/detect_stack.py`), `scripts/personal/tests/test_state.py`, `test_packs.py`.

**Interfaces — Produces:** `recommend.load_rules(kit) -> list[dict]`, `recommend.validate(kit) -> list[str]`, `recommend.signals(root, kit) -> dict[str, list[str]]` (signal → evidence), `recommend.compute(kit, root, st, all_packs) -> list[dict]` (each `{"id", "action", "skill", "reason", "evidence", "declined"}`), `recommend.open_items(items) -> list[dict]`; `state` field `declined_recommendations`.

- [ ] **Step 1: The rules file** `roles/recommend.json`, exactly:

```json
{
  "about": "Skill suggestions from the repo's files (design 2026-10-09 §5). add: when a signal is found and the person has one of the roles. drop: when none of the signals is found and the repo has code.",
  "rules": [
    {"skill": "javafx", "action": "add", "when": ["javafx"], "roles": ["dev", "qa", "architect"], "reason": "this repo uses JavaFX"},
    {"skill": "sonarqube-findings", "action": "add", "when": ["sonar"], "roles": ["dev", "qa", "architect"], "reason": "this repo is analysed by SonarQube"},
    {"skill": "blackduck-findings", "action": "add", "when": ["blackduck"], "roles": ["dev", "qa", "architect"], "reason": "this repo is scanned by Black Duck"},
    {"skill": "java-code-review", "action": "drop", "unless": ["java"], "reason": "this repo has no Java code"},
    {"skill": "java-junit", "action": "drop", "unless": ["java"], "reason": "this repo has no Java code"},
    {"skill": "110-java-maven-best-practices", "action": "drop", "unless": ["maven"], "reason": "this repo has no pom.xml"},
    {"skill": "golang-testing", "action": "drop", "unless": ["go"], "reason": "this repo has no Go code"},
    {"skill": "golang-code-style", "action": "drop", "unless": ["go"], "reason": "this repo has no Go code"},
    {"skill": "golang-lint", "action": "drop", "unless": ["go"], "reason": "this repo has no Go code"},
    {"skill": "javascript-typescript-jest", "action": "drop", "unless": ["jest"], "reason": "this repo does not use Jest"},
    {"skill": "react-testing-library", "action": "drop", "unless": ["react"], "reason": "this repo does not use React"},
    {"skill": "accessibility", "action": "drop", "unless": ["web"], "reason": "this repo has no web UI"},
    {"skill": "maven-via-artifactory", "action": "drop", "unless": ["code"], "reason": "this repo has no build files"}
  ]
}
```

- [ ] **Step 2: Failing tests.**
  - `test_state.py::test_older_state_has_no_declined_recommendations`: a state file without the field loads with `[]`; a non-list or non-strings are cleaned (as `skipped_connectors`).
  - `test_packs.py::TestRealKit::test_the_recommend_rules_validate` (`recommend.validate(KIT) == []`) and `TestValidate::test_bad_recommend_rules` (temp kit copy, one rule at a time): unknown skill, unknown signal, unknown role, `add` without `roles`, `drop` with `when`, empty reason, a reason over 120 characters, two rules for one id, an `add` rule for a skill that some role pack already lists (an add rule must name a library-only skill) — each gives one readable error.
  - `test_recommend.py` (each test builds a repo with `helpers.make_repo` and sets up with `helpers.cli`):
    - `test_each_signal` (one small repo per signal; `signals()` keys and evidence paths).
    - `test_a_javafx_maven_repo_for_a_developer`: `pom.xml` with `org.openjfx:javafx-controls` and `sonar-maven-plugin`; roles `dev` → ids in order `["add:javafx", "add:sonarqube-findings", "drop:accessibility", "drop:golang-code-style", "drop:golang-lint", "drop:golang-testing", "drop:javascript-typescript-jest", "drop:react-testing-library"]`; `java-*`, `110-…` and `maven-via-artifactory` not dropped.
    - `test_an_empty_repo_gets_no_suggestions` (only `README.md`).
    - `test_a_monorepo_gets_no_drops` (`pom.xml`, `services/api/go.mod`, `web/package.json` with react and jest).
    - `test_the_role_filter`: roles `po` in the JavaFX repo → no `add:javafx`; no drops (PO has none of the skills).
    - `test_the_persons_choice_wins`: after `change --drop-skill javafx`, no `add:javafx`; after `change --add-skill golang-lint` in a Java repo, no `drop:golang-lint`.
    - `test_declined_ones_are_marked_not_open`: with `declined_recommendations = ["add:javafx"]`, the item is there with `declined: True` and `open_items` leaves it out.
    - `test_the_same_repo_gives_the_same_list`: two runs, and a run with a different `HOME` holding a `~/.m2/settings.xml` → identical results.
    - `test_build_and_vendor_folders_are_not_read` (`node_modules/react/package.json`, `target/…/pom.xml` ignored).
- [ ] **Step 3: Implement.**
  - `state.new()` adds `"declined_recommendations": []`; `state.load()` cleans it like `skipped_connectors`.
  - `recommend.py`: `RULES_REL = "roles/recommend.json"`, `DETECT_REL = f"{packs.SKILLS_REL}/maven-via-artifactory/scripts/detect_stack.py"`, `SIGNALS = ("java", "maven", "javafx", "go", "node", "jest", "react", "web", "sonar", "blackduck", "code")`. `signals()` loads `detect_stack` with `importlib.util.spec_from_file_location` from the kit (never from the placed copy), calls `scan(root)` without `home`, and maps its `files`/fields to `SIGNALS` (design §5.2). `compute()`:

```python
def compute(kit, root, st, all_packs):
    found = signals(root, kit)
    c = st["choices"]
    have = set(packs.combine(all_packs, c)["skills"])
    roles = set(c["roles"])
    out = []
    for r in sorted(load_rules(kit), key=lambda r: (r["action"] != "add", r["skill"])):
        sid = f"{r['action']}:{r['skill']}"
        if r["action"] == "add":
            hit = [s for s in r["when"] if s in found]
            fires = (hit and roles & set(r["roles"]) and r["skill"] not in have
                     and r["skill"] not in c["drop_skills"])
            evidence = sorted({e for s in hit for e in found[s]})
        else:
            fires = ("code" in found and not any(s in found for s in r["unless"])
                     and r["skill"] in have and r["skill"] not in c["add_skills"])
            evidence = []
        if fires:
            out.append({"id": sid, "action": r["action"], "skill": r["skill"],
                        "reason": r["reason"], "evidence": evidence[:3],
                        "declined": sid in st.get("declined_recommendations", [])})
    return out
```
  - `packs.validate()` appends `recommend.validate(kit)` errors (prefixed `roles/recommend.json:`); `place.REQUIRED` adds the two paths.
- [ ] **Step 4: Green** (the full run; `validate_packs.py` ok).
- [ ] **Step 5: Name screen, Commit** (ask first): `feat(recommend): deterministic skill suggestions from the repo's files; rules as data`.

### Task 17: The `recommend` command, summaries, change and update (sequential, test first)

**Files:** `setup.py`, `scripts/personal/commands.py`; tests `test_recommend.py`, `test_cli.py`, `test_update.py`, `test_setup.py`, `test_change.py`; `CHANGELOG.md`.

- [ ] **Step 1: Failing tests.**
  - `test_recommend.py`:
    - `test_recommend_lists_numbered_items_and_the_exact_change_command`: output starts `Skill suggestions for this repo (from its files; nothing is changed yet):`; lines `1. add:javafx — add ai-sdlc-javafx: this repo uses JavaFX (pom.xml).` …; then `To take them all: python3 .ai-sdlc/kit/setup.py change --add-skill javafx --add-skill sonarqube-findings --drop-skill accessibility …` (one flag per skill, in list order); `To take some: the same command with only those skills.`; `To say no to the rest: python3 .ai-sdlc/kit/setup.py recommend --decline <ids, comma-separated>  (or --decline all)`; exit 0; `helpers.snapshot` unchanged.
    - `test_no_suggestions_says_so` → `No skill suggestions for this repo.`
    - `test_decline_some_and_all`: `recommend --decline add:javafx` → exit 0, `state.json` has it, no other file changed; `recommend` then shows it under `Declined earlier (to take one, use the change command above):`; `--decline all` declines every open one.
    - `test_an_unknown_id_is_refused`: `--decline add:nothing` → exit 2, `Not a current suggestion: add:nothing. …`, state unchanged.
    - `test_change_clears_a_declined_id`: decline `add:javafx`, then `change --add-skill javafx` → not in `declined_recommendations`; same for `drop:` with `--drop-skill`.
    - `test_json_output`: `recommend --json` → a list of objects with exactly the keys `id, action, skill, reason, evidence, declined`.
    - `test_not_set_up` → exit 2, the "do the onboarding" message.
  - `test_setup.py::test_setup_mentions_open_suggestions`: setup as `dev` in the JavaFX repo → summary has `- Skill suggestions for this repo: 8 (say "recommend skills")` (count from `compute`, not hard-coded); in an empty repo, no such line.
  - `test_change.py::test_only_a_roles_change_mentions_suggestions`: `change --lang de` → no line; `change --roles po,dev` → the line.
  - `test_update.py::test_update_mentions_only_new_suggestions`: an old kit without `roles/recommend.json` rules for `javafx` (copy, edit the file) → setup, `recommend --decline all`; update from a current copy (9.9.9) in the JavaFX repo → the line counts only `add:javafx` (new); a second update → no line. Also: a declined id for a skill the newer kit lacks is dropped from state.
  - `test_cli.py`: `COMMANDS` adds `"recommend"`; `test_change_flags_parse` unchanged; new `test_recommend_flags_parse` (`--json`, `--decline`).
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.**
  - `setup.py`: `r = sub.add_parser("recommend", help="suggest skill changes from this repo's files; changes nothing")`, `r.add_argument("--json", action="store_true")`, `r.add_argument("--decline", metavar="IDS", help="comma-separated suggestion ids, or all")`; docstring line `python3 .ai-sdlc/kit/setup.py recommend [--json] [--decline <ids>|all]`.
  - `commands.cmd_recommend`: `_need_state`; `items = recommend.compute(...)`; `--decline`: validate ids against open items (`all` = every open id), add to `st["declined_recommendations"]` (sorted, unique), `state.save`, print `Noted: … You can still take them with the change command.`; `--json`: `json.dumps(items, ensure_ascii=False)`; otherwise the text of design §5.4. `HANDLERS["recommend"]`.
  - `_suggestions_line(kit, root, st, all_packs)`: `[]` or `[f'- Skill suggestions for this repo: {n} (say "recommend skills")']`, `n = len(open_items(...))`; never raises (a detection error gives no line). Called in `cmd_setup`, `cmd_update`, and `cmd_change` when `args.roles is not None`, appended after `_summary`.
  - `cmd_change`: for each added skill remove `add:<s>`, for each dropped skill remove `drop:<s>` from `declined_recommendations`.
  - `cmd_update`: keep only declined ids whose skill is in `packs.available_skills(kit)`.
- [ ] **Step 4: Green** (the full run).
- [ ] **Step 5: Name screen, Commit** (ask first): `feat(recommend): setup.py recommend, --decline and --json; one summary line in setup, update and a roles change`.

### Task 18: Onboarding (sequential, test first)

**Files:** `ONBOARDING.md`, `roles/core/instructions.md` ("Changing the setup" list), `scripts/personal/tests/test_onboarding.py`, `test_skill_guidance.py`.

- [ ] **Step 1: Failing tests** in `test_onboarding.py`:
  - `test_every_spoken_request_has_a_section` adds `"Recommend skills"`.
  - `test_the_onboarding_offers_skill_suggestions_once`: section "Do the onboarding" contains `` "`python3 .ai-sdlc/kit/setup.py recommend`" ``, `"This is an offer, not a fourth question."`, `"You can take all, some or none."`, `"recommend --decline all"`, `"Never apply a suggestion they did not choose."`; the step comes after the "Mark them as seen" step and before "Close".
  - `test_update_offers_new_suggestions`: section "Update the kit" contains `"Skill suggestions for this repo"`.
  - (`test_every_command_named_is_real_and_its_flags_belong_to_it` then checks `recommend --decline`.)
  - `test_skill_guidance.py::test_do_the_onboarding_always_goes_to_onboarding_md` also expects `"recommend skills"` in the core "Changing the setup" list.
- [ ] **Step 2: Implement.** In the "To Copilot" line, add "recommend skills" to the list of requests. New step 8 in "Do the onboarding" (renumber Close to 9 and the connect offer to 10), exactly:

  `8. **Suggest skills for this repo (optional).** Run \`python3 .ai-sdlc/kit/setup.py recommend\`. It reads the repo's files and changes nothing. If it says there are no suggestions, say nothing and go on. Otherwise tell the person each suggestion in one plain sentence with its reason (for example "add the JavaFX skill: this repo uses JavaFX"), then ask once: "Would you like these changes? You can take all, some or none." This is an offer, not a fourth question. Wait for the answer. All or some: run the \`change\` command the output gives, with only the skills they chose; then, if they left some out, run \`python3 .ai-sdlc/kit/setup.py recommend --decline <the ids they did not take>\`. None, or "not now": run \`python3 .ai-sdlc/kit/setup.py recommend --decline all\` and say they can say "recommend skills" at any time. Never apply a suggestion they did not choose.`

  New section `## Recommend skills` (after "Change my preferences"): the person said "recommend skills" or "which skills fit this repo?"; run `recommend`; relay the open suggestions and the declined ones; same choice flow as step 8; a declined one is taken with the `change` command.
  "Update the kit" step 3, append: `If the summary has a line "Skill suggestions for this repo", offer them as in onboarding step 8.`
  Core instructions "Changing the setup": add `"recommend skills"` to the list.
- [ ] **Step 3: Green** (the full run). **Name screen, Commit** (ask first): `feat(onboarding): offer skill suggestions once after setup; "recommend skills" at any time`.

### Task 19: Docs and CI (sequential)

**Files:** `README.md`, `template/.claude/skills/README.md`, `docs/how-to.md`, `.github/workflows/ci.yml`.

- [ ] **Step 1: `README.md`.** Role table: the new skills per role. After the process-skills paragraph, one paragraph: the **stack skills** (one phrase each, upstream and licence, by role), the three library skills that come through suggestions, the mirror rule; and one paragraph on **skill suggestions** ("recommend skills", nothing changes without a yes, declined ones are remembered per repo). The brand paragraph: the full 44-layout master, layout previews and examples, the builder and the one check. "What ends up in your repo": about 25 MB more for the brand skill.
- [ ] **Step 2: `template/.claude/skills/README.md`.** New "## Stack skills" table (13 rows: skill, use it for, source and licence) and one line on which roles get which; the brand row updated.
- [ ] **Step 3: `docs/how-to.md`.** §5: `"recommend skills"` with the terminal example (`recommend`, `--decline`); the Copilot examples add *"add the javafx skill"*. Counts and version wait for Task 20.
- [ ] **Step 4: `ci.yml`, personal-e2e**, after the `ai-sdlc-brainstorming` line:
  `test ! -e .agents/skills/ai-sdlc-java-junit          # stack skills are by role: PO and SM do not get them`
  `python3 .ai-sdlc/kit/setup.py recommend | grep -q "No skill suggestions for this repo."   # the team repo has no code`
  and `test -f .agents/skills/ai-sdlc-frq-brandbook/assets/templates/frq-master.pptx` next to the other brand checks (the byte compare already covers it).
- [ ] **Step 5:** the full run. **Name screen, Commit** (ask first): `docs: stack skills, skill suggestions and the merged brand skill; CI checks stack skills are by role`.

### Task 20: Release 0.9.0 (sequential, test first)

**Files:** `scripts/personal/tests/test_release.py`, `VERSION`, `CHANGELOG.md`, `docs/how-to.md`.

- [ ] **Step 1: Failing tests** in `test_release.py`: `test_version` expects `"0.9.0"`; new `test_changelog_0_9_0_has_the_stack_pack`: the `[0.9.0]` entry contains `` "`ai-sdlc-java-junit`" ``, `` "`ai-sdlc-golang-testing`" ``, `` "`ai-sdlc-react-testing-library`" ``, `` "`ai-sdlc-maven-via-artifactory`" ``, `` "`ai-sdlc-javafx`" ``, `"recommend"`, `"never \`@latest\`"`, `"react-best-practices"` (not taken), `"frq-4-pptx-agent"`, `"44 layouts"`.
- [ ] **Step 2:** `git switch -c release/0.9.0`; run → FAIL.
- [ ] **Step 3:** `VERSION` → `0.9.0`. `CHANGELOG.md`: move the Unreleased lines under `## [0.9.0] — <date>` (`### Added` / `### Changed`): the 13 stack skills (upstream, commit, licence, roles, the three library skills); skill suggestions (`setup.py recommend`, `--decline`, `--json`, the onboarding step, update shows only new ones, rules in `roles/recommend.json`); the mirror rule in the core instructions; the brand merge (the owner's `frq-4-pptx-agent` v1.0 merged into `ai-sdlc-frq-brandbook`: the full master with 44 layouts, cleaned; layout previews, examples, key visuals, logos, CSS; `frq_pptx.py` builder; one check; `new_deck.py` on the full master; about 25 MB more per repo); "Not taken: vercel-labs `react-best-practices` (no licence file) …". Unreleased stays empty.
- [ ] **Step 4: Verify the how-to example by running it** (as in 0.7.0 Task 10 step 4, scratch folder outside the repo): `setup --name "Ana" --roles po,qa --lang en` → `Set up AI-SDLC 0.9.0 …`, `Wrote N file(s)`. Use the **printed** numbers in `docs/how-to.md` (line 71–73 block). Re-run the §5 `change` example and update its numbers if they changed.
- [ ] **Step 5: Full verification, both Pythons** (the full run, `validate_packs.py`, `validate-skills.py`); the brand builder tests once in a venv with python-pptx. Paste the summary lines in the PR.
- [ ] **Step 6: Name screen on the whole branch:** `git diff main...HEAD | grep -n -i -E "$OTHER"` and `git diff main...HEAD | grep -n -E '/Users/|~/work/'` → nothing; `grep -rn -i -E '\b(frq|frequentis|mosaix)\b' template/.claude/skills/{java-code-review,java-junit,110-java-maven-best-practices,golang-testing,golang-code-style,golang-lint,javascript-typescript-jest,react-testing-library,accessibility,javafx,maven-via-artifactory,sonarqube-findings,blackduck-findings} roles/*/instructions.md roles/recommend.json` → nothing.
- [ ] **Step 7: Commit** (ask first): `chore(release): kit 0.9.0 — stack pack, skill suggestions, one brand skill`.
- [ ] **Step 8: PR** `release/0.9.0` → `main` (ask before push). Body: what ships, what is not taken and why, the placement rule and the suggestions, the brand merge, test summary, owner decisions; ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. CI green. **Do not merge yet.**

### Task 21: Copilot CLI re-test (owner, manual, before merge)

On the VM, with the Copilot CLI and a trusted folder, from the `release/0.9.0` copy. Sample repos (made by the coordinator, synthetic): **A** a Maven JavaFX app with `.mvn/settings.xml` pointing at a mirror URL, `sonar-project.properties`, JUnit 5, AssertJ; **B** a Go module with `go 1.23` in `go.mod`; **C** a React app with Jest and Testing Library; plus one deck spec and one off-brand `.pptx`. Note each result in the PR; fixes go on `release/0.9.0` first.

1. **Onboarding, developer, repo A:** suggestions come once, after setup, each with a reason; take `add:javafx`, refuse `drop:accessibility`, take the other drops. `USER.md` and `recommend` agree; nothing applied that was not chosen.
2. **"Not now", then update:** in repo B as QA say "not now"; update from a 9.9.9 copy → no suggestion line (no nag). "recommend skills" still lists them under "Declined earlier".
3. **"Write tests first for <class>"** in A → TDD skill and `ai-sdlc-java-junit` load; JUnit version and AssertJ taken from the POM; no Mockito added; the new file shown before saving.
4. **"Add the dependency <x>"** in A → no `<repositories>`; asks before running Maven; with the mirror unreachable, stops and reports (artifact, mirror URL, error).
5. **"Write tests for this function"** in B → no `synctest.Test`, no `b.Loop()`, no `t.Context()` (Go 1.23); no `gotests` install.
6. **"Lint this"** in B → runs `golangci-lint run` if installed, else says it is missing; never `go install …@latest`; no `--fix` before a yes.
7. **"Test this component"** in C → Jest and Testing Library, no Vitest, no `npm install` before a yes.
8. **"Accessibility audit of this page"** in C → no MCP tool, no `npx lighthouse` download.
9. **Sonar:** paste three issue rows → explanations, a diff per fix, never asks for a token, says a false positive is marked by the person in SonarQube.
10. **Black Duck:** paste two CSV rows (one CVE, one licence risk) → upgrade through `<dependencyManagement>`; the licence one is handed to the person.
11. **JavaFX:** "the UI freezes while loading" → work moved to a `Task`/`Service`, results back with `Platform.runLater`; TestFX headless with Monocle proposed.
12. **Brand, build:** "build a deck from this spec" (title, agenda, divider, 50:50, an EMEA map, a timeline, closing) → asks the classification first, shows the outline, asks before installing python-pptx into `~/.ai-sdlc/venv`, builds on the 44-layout master, runs the check, renders into `.ai-sdlc/tmp/`, shows the result.
13. **Brand, Apply:** "make this deck on-brand" with the off-brand `.pptx` → one table of Must and Should fixes, "all, Must only, or by slide number", writes `<name>-frq.pptx`, never touches the input, re-checks.
14. **Role check:** onboarding as PO in repo A → no stack skills, no `add:javafx` suggestion.

Merge only after this and with the owner's yes.

---

## Self-review

- Design §2 (vendored): Tasks 2–10; §2.1 (not taken): `TestPack`, CHANGELOG. §3 (kit-written): Tasks 11–14; §3.1 (core mirror sentence): Task 15. §4 (placement): Task 15; §5 (recommend): Tasks 16–18; §5.6 (update): Task 17. §6 (teams): nothing built; Task 16 keeps rules separate from packs and computes on `packs.combine`. §7 (testing): Tasks 1, 12, 15–18, B1–B4, 20, 21. §8 (brand merge): Tasks B1–B4, 19, 20, 21.
- Names used across tasks: `VENDORED`, `KIT_WRITTEN`, `STACK`, `FILES`, `MIRROR_RULE`, `READ_ONLY_RULE`, `GIT_RULE`, `SHOW_RULE`, `declined_recommendations`, `recommend.compute`, `open_items`, `_suggestions_line` — consistent.
- Every owner decision 1–5 has a task: 1 (9 skills, edits) Tasks 2–10; 2 (4 kit-written) Tasks 11–14; 3 (placement, recommend, teams hook) Tasks 15–18 and design §6; 4 (connectors later) design §9; 5 (kit rules) Global Constraints, Tasks 1, 20, 21. Scope addition (brand merge): B1–B4.

## Design problems found while planning

1. **Dotfiles are not placed.** `golang-lint/assets/.golangci.yml` would be skipped by `place.placed_skill_files`, and the skill's links would break. Fix: renamed `assets/golangci.yml` (Task 7).
2. **`allowed-tools` pre-approves commands** (`Bash(git:*)`, `Agent`) in some tools: against "a human validates everything". Fix: dropped from the frontmatter (all vendored).
3. **Apache-2.0 §4** asks for a change notice in each changed file, not only in `PROVENANCE.md` (Task 4).
4. **`go get <module>` without a version is `@latest`.** Fix: `@<version>`, picked with the person (Task 5).
5. **`./mvnw` downloads Maven** from `distributionUrl` on first run (Task 4 kit bullet; `maven-via-artifactory`).
6. **Settings files hold secrets.** `detect_stack.py` reads only allowlisted fields and strips user-info from URLs (Task 12).
7. **Recommendations must not depend on the person.** Home-folder files are read only for Copilot's version/mirror view, never for suggestions (Task 16).
8. **The owner's master names employees and the tenant**; the owner's `set_footer` accepts any classification text; its `render` writes to `/tmp`; its `audit` duplicates `check_brand.py`. Fixes in B1 and B3.
9. **Four key visuals are byte-identical** in both skills: kept once, alias in the manifest (B2).
10. **The brand description is already 973 characters**: it must be rewritten, not extended (B4).

## Open questions for the owner

1. **Placement (design §4.2).** Language skills in the role packs (proposed: works without the suggestion step, ~3.3 KB more per turn for a developer, drops trim it per repo), or library-only and added by suggestions (less context, but nothing without the step)?
2. **Per-role choices.** `maven-via-artifactory` also for the Engineering Manager? `accessibility` also for the Architect? `java-junit` also for the Architect?
3. **Go and React versions** in the client's repos (oldest `go` line; React 18 or 19; Jest 29 or 30)? The skills handle each, but the re-test repos should match.
4. **AssertJ and Mockito:** standard in the client's Java repos? (Today: used only if the POM has them.)
5. **JavaFX source:** the Zulu FX JDK (JavaFX built in), `org.openjfx` dependencies, or both in different repos?
6. **Black Duck detection:** how do the client's pipelines run Detect (Jenkinsfile step, a `detect.sh` call, properties in `application.yml`)? The `blackduck` signal is a heuristic until we know.
7. **Name `maven-via-artifactory`** also covers npm and Go. Keep it, or rename (for example `packages-via-mirror`) before it ships? Also keep the upstream name `110-java-maven-best-practices` (placed `ai-sdlc-110-java-maven-best-practices`), or rename to `maven-best-practices` as a local change?
8. **The 0.8.0 slim template** (1.2 MB): retire it now that the full master ships, or keep both? (Kept in 0.9.0 until you say.)
9. **Default business unit** for decks: ATM (owner skill) or ask each time (0.8.0, C8)? Proposed: ask, offer ATM first.
10. **Size:** about 25 MB more per repo (the kit copy plus the placed brand skill). Accept for 0.9.0, or plan for 0.10.0 to keep the big binaries only in `.ai-sdlc/kit` and point the placed skill at them?
11. **The wide ATM aircraft photo** was left out in 0.8.0 for unknown rights. Ship it now (owner: keep every artifact) and list it for GCM, or leave it out until GCM confirms?
12. **Two logo sets** (0.8.0 converted shape for shape, owner skill traced): keep both (proposed) or keep one?
13. **Conflicts C11–C16** (design §8.4): agree with the proposed resolutions?
