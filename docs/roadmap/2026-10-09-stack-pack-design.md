# Stack pack: skills for the client's languages and tools — design

**Status:** approved 2026-10-10 (kit owner; answers to the open questions in §10). Owner decisions: §2 (skills), §3 (kit-written skills), §4 (placement: library skills, by role packs only for what they list today), §5.5 (the picker step), §8 (brand merge, kit-copy-only assets, both templates, ATM default), §9 (out of scope). Plan: [stack pack plan](./2026-10-09-stack-pack-plan.md). Target release: **0.9.0**.
**Related:** [onboarding, roles & skills design](./2026-10-07-onboarding-roles-and-skills-design.md), [personal setup design](./2026-10-08-personal-setup-design.md) (role packs, placement, `change --add-skill/--drop-skill`), [superpowers pack design](./2026-10-08-superpowers-pack-design.md) (how skills are vendored), [connectors design](./2026-10-08-connectors-design.md).

## 1. Problem

The kit gives process skills (design, plan, test first, debug) but nothing about the client's code. The client builds with:

- **Java**: Azul Zulu JDK 17 and 21, **JavaFX** desktop UI, **Maven**. Spring Boot may be used; the version is unknown.
- **Go**.
- **React**, tested with **Jest**.
- **JFrog Artifactory**, self-hosted. No direct downloads from the internet: every package comes through the company mirror.
- **SonarQube Community** and **Black Duck** for code quality and open-source risk.
- Docs partly on SharePoint (Online or on-premises is not known; out of scope).

So Copilot gives generic advice. Worse, public skills often say "`go install …@latest`", "`npx …`" or "add this `<repositories>` block", which breaks the no-internet rule and the kit rule that **a human validates everything**.

## 2. Vendored skills (owner decision 1)

Nine skills, each pinned to one upstream commit, with the upstream `LICENSE` and a `PROVENANCE.md` that lists every local change, the same way as `drawio`, `likec4-dsl` and the superpowers skills. Upstream names are kept (the kit never renamed a vendored skill); setup places them as `ai-sdlc-<name>`. All pins taken 2026-10-09. They are **library skills** (§4.2): placed only when the person accepts a suggestion or picks them. The roles column says to whom they are *suggested*.

| Skill | Upstream (commit) | Licence | Suggested for | Main local changes |
|---|---|---|---|---|
| `java-code-review` | decebals/claude-code-java `0d98fe9bd629` | MIT | dev, architect | Kit section; `README.md` not bundled (Claude-only load line). |
| `java-junit` | github/awesome-copilot `82701c24b994` | MIT | dev, qa | Kit section; JUnit version first (4 vs 5/6); AssertJ and Mockito only if the POM has them; trigger phrases. |
| `110-java-maven-best-practices` | jabrena/plinth `dca88dc17dc2` | Apache-2.0 | dev, architect | **Never declare `<repositories>` in the POM**; resolve through the `settings.xml` mirror (Artifactory). Example 6 rewritten. "APPLY directly" becomes "propose, apply after a yes". `./mvnw` may download Maven: ask first. Apache-2.0 change notice in each changed file. |
| `golang-testing` | samber/cc-skills-golang `8e899e20ff0c` | MIT | dev, qa | **Remove `gotests@latest`**; **read the `go` line in `go.mod` first** and use only features that version has; no sub-agents; cross-references to skills not shipped removed; `evals/` not bundled. |
| `golang-code-style` | samber/cc-skills-golang `8e899e20ff0c` | MIT | dev | No sub-agents; cross-references removed; `evals/` not bundled. |
| `golang-lint` | samber/cc-skills-golang `8e899e20ff0c` | MIT | dev | **Remove `go install …@latest`** (golangci-lint must already be installed); no background `--fix` (fixes only after a yes); `assets/.golangci.yml` renamed `assets/golangci.yml` (setup skips dotfiles, so the link would break); `evals/` not bundled. |
| `javascript-typescript-jest` | github/awesome-copilot `82701c24b994` | MIT | dev, qa | Kit section; trigger phrases. |
| `react-testing-library` | itechmeat/llm-code `7ae8a0052457` | MIT | dev, qa | **Jest only**: the Vitest sections are removed; `npm install` lines become "check `package.json`, ask before adding". |
| `accessibility` | addyosmani/web-quality-skills `afa8da942115` | MIT | dev, qa | **Remove the MCP lines** (Chrome DevTools MCP); no `npx lighthouse` download, no global `npm install -g`; use an installed tool or the browser's Lighthouse panel. |

Every vendored skill also gets one section, "This kit's copy", with three rules: no git on its own; show before you change (the 0.8.0 rule); packages only through the company mirror. The frontmatter keeps `name`, `description`, `license` and `metadata` (author, version). It drops `allowed-tools` (in some tools it pre-approves commands such as `git` without asking), `user-invocable`, `paths`, the Claude-only `compatibility` line and the `openclaw` install block (it installs `gotests@latest` or `golangci-lint` through Homebrew).

### 2.1 Not taken

| Skill | Why not |
|---|---|
| vercel-labs/agent-skills `react-best-practices` | **No `LICENSE` file** in the repo (owner decision). Revisit if upstream adds one. |
| JFrog official skills (jfrog/jfrog-skills) | Built around the JFrog MCP server and `jf` CLI installs. Used only as ideas for `maven-via-artifactory`. |
| SonarSource sonar-* skills | Source-available licence, not open source; they need the Sonar MCP server or CLI. Ideas only, no text copied. |
| Black Duck skills (AgentSecOps/SecOpsAgentKit `sca-blackduck`) | Licence not stated; runs Detect, which downloads from the internet. Ideas only. |
| JavaFX skills (JohannesRabauer/javafx-skills, DongZY0617/javafx-skill) | The first has no licence. The second is Apache-2.0 but very long (about 1,400 lines in two skills) and not about the client's set-up. Ideas only. |
| decebals `java-migration`, `concurrency-review`; plinth 111, 125, 131; affaan-m/ECC Go and React skills | Overlap with what we take, or not needed now. `java-migration` (17 → 21) can come later. |
| SharePoint (merill/msgraph) | Out of scope until we know Online or on-premises. |

## 3. Kit-written skills (owner decision 2)

Four skills written for this kit, MIT like the kit, also library skills (suggested to dev, QA and architect). Each has a `PROVENANCE.md` that says "Written for this kit (date)" and lists the upstream skills whose **ideas** it used, with repo, commit and licence, and the line "No text was copied". No `LICENSE` file (the kit's licence applies).

| Skill | What it does | Files |
|---|---|---|
| `javafx` | The FX application thread (`Platform.runLater`, `Task`, `Service`, never block the UI); FXML, controllers (`fx:controller`, `@FXML`, `initialize`) and CSS; properties, bindings and listener leaks (`WeakChangeListener`, remove listeners); MVVM or MVCI, and how to choose; TestFX tests, headless with Monocle on Ubuntu CI; `javafx-maven-plugin`, `jlink`, `jpackage`. **Detects where JavaFX comes from**: the Zulu "FX" JDK (JavaFX built in) or `org.openjfx` Maven dependencies, and does not mix the two. | `SKILL.md`, `references/testing-and-packaging.md`, `PROVENANCE.md` |
| `maven-via-artifactory` | **Resolve only through mirrors**: Maven `settings.xml` mirrors (repo `.mvn/`, then `~/.m2/`), `.npmrc` registry, `GOPROXY`. Never `@latest`, never `npx` or `go install` from the public internet. **On a resolution failure: stop and report** (which artifact, which mirror URL, the error), never work around it by adding a repository. **Version detection** the other skills rely on: Java release, Spring Boot (if any), JUnit (4, 5 or 6), AssertJ and Mockito (present or not), JavaFX source and version, TestFX, Go (`go` and `toolchain` lines), React, Jest and Testing Library. A stdlib script prints these facts as JSON, so Copilot does not read whole build files. It never prints a password or token. | `SKILL.md`, `scripts/detect_stack.py`, `PROVENANCE.md` |
| `sonarqube-findings` | Read-only help to understand and fix SonarQube findings, **from a report the person pastes or exports now** (issue list copied from the UI, a JSON export, the scanner or quality-gate output in a CI log). Explains the rule (for example `java:S2095`), proposes a fix as a diff, says when a finding looks like a false positive. Marking a finding (false positive, accepted) is the person's decision, in SonarQube. Notes what SonarQube Community does not have (branch and pull-request analysis). A connector comes in 0.10.0. | `SKILL.md`, `PROVENANCE.md` |
| `blackduck-findings` | Read-only help with Black Duck findings from a pasted or exported report (vulnerable components with CVE or BDSA ids, policy violations, licence risks). Proposes the smallest upgrade that fixes it, through the mirror (`<dependencyManagement>` in Maven, a version in `go.mod`, `overrides` in npm), and asks before any build that downloads. Licence questions go to the person; Copilot never decides them. Ignores and policy overrides are the person's decision, in Black Duck. Connector in 0.10.0. | `SKILL.md`, `PROVENANCE.md` |

The idea sources (pinned 2026-10-09): JohannesRabauer/javafx-skills `0a6b8f197f52` (no licence), DongZY0617/javafx-skill `ddc35f1935a4` (Apache-2.0), jfrog/jfrog-skills `a27c74da9e36` (Apache-2.0), decebals/claude-code-java `0d98fe9bd629` `maven-dependency-audit` (MIT), SonarSource/sonarqube-agent-plugins `6142e57738de` (source-available), AgentSecOps/SecOpsAgentKit `6e25a4bc5743` (not stated), OWASP/secure-agent-playbook `1b5fd4cff760` `sca-audit` (not stated).

### 3.1 One rule for every package (core instructions)

The core instructions already say "ask before anything that downloads or installs". 0.9.0 adds one sentence there, for every role, also when `maven-via-artifactory` is left out: *packages come only through the company mirror (Maven `settings.xml`, `.npmrc`, `GOPROXY`); never `@latest` or `npx` from the public internet.* No client name, no URL.

## 4. Placement

### 4.1 The rule (owner decision 3)

A skill is placed only for one of these reasons:

1. a **role pack** lists it (as now);
2. in the future, a **team pack** lists it (§6);
3. the person **accepted a recommendation** (§5) or **picked the skill** (from the other-skills list, or with "add the … skill"). It is stored in `state.json` as an added or left-out skill, the same field `change --add-skill/--drop-skill` uses, so every re-run gives the same result.

**No silent auto-placement.** The repo's files never change what is placed by themselves.

What a person gets stays the existing formula (`packs.combine`): `(core ∪ their roles) ∪ added − left out`. Later: `(core ∪ roles ∪ teams, minus what the teams leave out) ∪ added − left out` (§6.2).

### 4.2 Which skill goes where (owner decision, 2026-10-10)

**All 13 new skills are library skills.** No role pack lists them; the role packs stay as they are (playbooks and process skills). A stack skill is placed only when the person:

- accepts a **suggestion** (§5), or
- **picks it** from the list of other skills (§5.5, step "Other skills"), or
- says "add the … skill" (`change --add-skill`).

Each of these lands in `choices.add_skills` in `state.json`, so every re-run places the same skills.

Why this is right for the client: the repo decides the stack, not the role. A developer in a Go repo needs no Java skill, and every placed skill costs context on every turn (each description is about 0.1 to 0.6 KB; all 13 together about 4 KB). With library placement a person in a Maven-only repo carries only the Java skills they accepted (about 1.4 KB).

The cost: someone who says "not now" to suggestions and picks nothing has no stack skills. They can say "recommend skills" or "show me the other skills" at any time.

## 5. Detect and recommend (in 0.9.0)

### 5.1 What it does

After roles (and later teams) are chosen, the kit reads the repo's files, **deterministically and read-only**, and recommends skills to add, each with a reason. The person accepts all, some or none. Accepted ones are applied with the existing `change --add-skill/--drop-skill`; declined ones are remembered so they are not offered again.

The same repo and the same choices always give the same list, in the same order: adds first, then drops (none in 0.9.0), each sorted by skill name. Recommendations read only the repo, never the person's home folder, so two people in the same repo get the same list for the same roles.

### 5.2 What it reads

A bounded walk of the repo: the root and up to three folder levels down, in sorted order, at most 5,000 entries, files up to 512 KB. It skips `.git`, `.ai-sdlc`, `.agents`, `node_modules`, `target`, `build`, `dist`, `out`, `vendor` and other dot-folders except `.github` and `.mvn`. It never runs a tool (no `mvn`, `go`, `npm`), never uses the network, and refuses an XML file with a `DOCTYPE` or entity declaration.

| Signal | Found when |
|---|---|
| `maven` | a `pom.xml` |
| `java` | `maven`, or a `build.gradle(.kts)`, or a `.java` file |
| `javafx` | a POM names `org.openjfx` or `javafx-maven-plugin`; or `module-info.java` has `requires javafx.`; or a `.fxml` file; or a `.java` file imports `javafx.`; or `.sdkmanrc` / `.java-version` / `.tool-versions` names a Zulu FX JDK (`fx-zulu`, `zulu…fx`) |
| `go` | a `go.mod` |
| `node` | a `package.json` |
| `jest` | `jest`, `ts-jest` or `@jest/core` in a `package.json`'s dependencies, a `jest` key, or a `jest.config.*` file |
| `react` | `react` in a `package.json`'s dependencies |
| `web` | `react`, or an `index.html` under `src/` or `public/` |
| `sonar` | `sonar-project.properties`; a POM with `sonar-maven-plugin` or a `sonar.` property; a `Jenkinsfile` or `.github/workflows/*.yml` that names `withSonarQubeEnv`, `sonar-scanner` or `sonar:sonar` |
| `blackduck` | a `Jenkinsfile`, `.github/workflows/*.yml` or `application*.{yml,yaml,properties}` that names `blackduck`, `synopsys_detect`, `detect.sh` or a `detect.` / `blackduck.` property (a heuristic: how the client runs Detect is not known, so the skill asks when the signal is missing) |
| `code` | any of `java`, `go`, `node` |

The detection lives in `maven-via-artifactory/scripts/detect_stack.py` (stdlib, Python 3.9). The kit loads it from its own copy (`.ai-sdlc/kit/template/.claude/skills/…`), so it works even when the person left that skill out. Copilot runs the same script, through the skill, for the versions (§3). One detector, two users.

### 5.3 The rules and the catalogue

Rules are data, in `roles/recommend.json`, so the client can add rules without code (kit future: client ownership). A rule names one skill and one action:

```json
{"skill": "javafx", "action": "add", "when": ["javafx"], "roles": ["dev", "qa", "architect"],
 "reason": "this repo uses JavaFX"}
```

- An **add** rule fires when one of its `when` signals is found, the person has one of its `roles`, and the skill is not placed yet.
- A **drop** rule (`"unless": [...]`) fires when none of its signals is found, the repo has some `code`, and the skill is placed. **0.9.0 ships no drop rules**: the stack skills are only ever placed by the person's own choice, and that choice wins. The engine keeps drop rules for the client and for teams (for example, to suggest leaving out a role's process skill). **No drops in a repo without code.**
- **The person's explicit choice always wins:** a skill they left out is never suggested back; a skill they added is never suggested for dropping.
- A rule's id is `add:<skill>` or `drop:<skill>`. One rule per id. An `add` rule may only name a skill that no role pack lists.
- `packs.validate` checks the file: known skills, known signals, known roles, `add` needs `when` and `roles`, `drop` needs `unless`, a reason of 1 to 120 characters.

**0.9.0 rules (all `add`):**

| Skill | When | Suggested to |
|---|---|---|
| `java-code-review` | `java` | dev, architect |
| `java-junit` | `java` | dev, qa |
| `110-java-maven-best-practices` | `maven` | dev, architect |
| `javafx` | `javafx` | dev, qa, architect |
| `maven-via-artifactory` | `code` | dev, qa, architect |
| `golang-testing` | `go` | dev, qa |
| `golang-code-style`, `golang-lint` | `go` | dev |
| `javascript-typescript-jest` | `jest` | dev, qa |
| `react-testing-library` | `react` | dev, qa |
| `accessibility` | `web` | dev, qa |
| `sonarqube-findings` | `sonar` | dev, qa, architect |
| `blackduck-findings` | `blackduck` | dev, qa, architect |

**The catalogue.** The same file has a `catalogue`: for each library skill a group and a one-line summary, for the "other skills" list (§5.5). Groups: *Java*, *Go*, *React and web*, *Quality and security*, *Ways of working* (process skills), *Role playbooks*, *Documents and diagrams*, *Other*. A skill with no entry goes under *Other*, with the first sentence of its description cut to 100 characters. `packs.validate` checks that every catalogue entry names a skill the kit has and that every summary is 1 to 100 characters.

### 5.4 The command

```text
$ python3 .ai-sdlc/kit/setup.py recommend
Skill suggestions for this repo (from its files; nothing is changed yet):
1. add:javafx — add ai-sdlc-javafx: this repo uses JavaFX (pom.xml: org.openjfx:javafx-controls).
2. add:java-junit — add ai-sdlc-java-junit: this repo has Java code (pom.xml).
…
To take them all: python3 .ai-sdlc/kit/setup.py change --add-skill javafx --add-skill java-junit …
To take some: the same command with only those skills.
To say no to the rest: python3 .ai-sdlc/kit/setup.py recommend --decline <ids, comma-separated>  (or --decline all)
```

- `recommend` changes nothing. Exit 0. With no suggestion: "No skill suggestions for this repo." Not set up: the usual "say do the onboarding", exit 2.
- `recommend --decline add:javafx,add:java-junit` (or `all`) writes only `state.json`: the ids go to a new list, `declined_recommendations`. An unknown id is refused, exit 2, nothing changed. Declined ones are listed under "Declined earlier", with the command to take one after all.
- `recommend --all` adds a second part, **"Other skills you can add"**: every skill the kit has that is not placed, not suggested and not declined, grouped by the catalogue, one line each (`ai-sdlc-<name> — <summary>`), and the command to add any of them (`change --add-skill <name> …`). This is the simplest way to "show me the other skills": one command, no new command name, read-only.
- `recommend --json` prints `{"suggestions": [...], "others": [...]}`: each suggestion has `id`, `action`, `skill`, `reason`, `evidence` (repo paths), `declined`; each other skill has `skill`, `group`, `summary`. `others` is filled only with `--all`.
- `change --add-skill X` takes `add:X` off the declined list; `--drop-skill X` takes `drop:X` off. The person changed their mind; the explicit choice is what counts.
- `setup`, `update`, and `change --roles` add one line to their summary when there are open suggestions (not applied, not declined): `- Skill suggestions for this repo: 3 (say "recommend skills")`. Other `change` runs and `check` say nothing about them.

### 5.5 Onboarding

Two new steps after the warnings are marked as seen, before "Close":

1. **Suggest skills for this repo (optional).** Copilot runs `recommend`. If there are suggestions, it says each one in a plain sentence with its reason and asks once: "Would you like these skills? You can take all, some or none." This is an offer, not a fourth question.
   - All or some: Copilot runs the `change` command with only the chosen skills, then `recommend --decline` for the rest.
   - None or "not now": `recommend --decline all`, and "say 'recommend skills' at any time".
2. **Other skills (optional, owner decision).** Copilot runs `recommend --all` and shows only the "Other skills you can add" part, grouped, one line each. It asks once: "Would you like any of these as well? 'None' is fine." Picks go through `change --add-skill` (stored like any added skill). "None" stores nothing: the list is a catalogue, it is never offered again by itself, so there is nothing to decline.

A new section, **Recommend skills**, handles "recommend skills", "which skills fit this repo?" and "show me the other skills" the same way, and lists the declined suggestions too.

### 5.6 Update, without nagging

After onboarding, every suggestion was either accepted (it is in the person's choices) or declined (it is on the declined list). So when `update` shows an open suggestion, it is new: a skill the newer kit adds, a new rule, a new role, or a repo change (someone added a `go.mod`). That is the only time it is shown again. The "other skills" list is never shown by `update` or `check`; only when the person asks. "Update the kit" in `ONBOARDING.md` offers such suggestions as in the onboarding step. `update` also forgets declined ids for skills the newer kit no longer has.

## 6. Teams (future hook, **not built in 0.9.0**)

### 6.1 Data model

`teams/<id>/team.json`, next to `roles/`:

```json
{"id": "desktop", "label": "Desktop client team",
 "skills": ["javafx", "java-junit", "maven-via-artifactory", "sonarqube-findings"],
 "leave_out": ["brainstorming"],
 "connectors": ["jira", "bitbucket"]}
```

`skills` adds library skills, `leave_out` removes skills the roles give, `connectors` adds connector suggestions. A team pack has no instructions file and no defaults. Validated like role packs (known skills, known connectors, id equals the folder, `personal` reserved).

### 6.2 Precedence (deterministic)

1. `base = core ∪ roles ∪ (skills of every chosen team)`
2. `base = base − (leave_out of every chosen team)`: a team's leave-out wins over a role or another team (the smaller set; the person can add a skill back).
3. `final = base ∪ the person's added skills − the person's left-out skills`: **the person's explicit choice wins.** Accepted recommendations are part of step 3.
4. Recommendations run on `final`, so they never suggest what a team already decided.

### 6.3 Onboarding and commands

- After the role question, only if `teams/` has a pack: "Which team are you in? You can pick more than one, or none: <labels with ids>." One question, no default.
- `setup --teams a,b`, `change --teams a,b` (the full list), `state.json` `choices.teams` (empty list by default; older state loads with it empty).
- The setup summary names the teams. `USER.md` gets a "Teams" line.
- A team pack works like a known stack: the team's stack skills are placed for everyone in the team, so suggestions become fewer.

### 6.4 What 0.9.0 does for it

Nothing in code. 0.9.0 only keeps the door open: recommendations work on the combined skill set, and the rules file is separate from the packs, so a later `teams/` step slots in before them without changing either.

## 7. Testing

- **Content guards** for the 13 skills (`test_stack_skills.py`): exactly the planned files; the name; placed with the prefix and no broken link; licence and `PROVENANCE.md` (pin, every file, local changes, "Updating"; kit-written: "Written for this kit", idea sources, "No text was copied"); the kit section's rules; no `@latest`, `go install`, global `npm install -g`, `npx` without `--no-install`, `pip install` or `curl | sh`; no MCP; no sub-agents; no cross-reference to a skill not shipped; every git word asks first or was reviewed; descriptions at most 1,024 characters with their trigger phrases; Vitest gone from `react-testing-library`; no `<repositories>` as a good example in the Maven skill; the Apache-2.0 change notice.
- **`detect_stack.py` behaviour** (`test_detect_stack.py`): versions from small fixture repos; JavaFX source (Zulu FX hint, `org.openjfx`); mirrors without secrets (a `settings.xml` password and an `.npmrc` token never appear in the output); read-only (byte snapshot unchanged); no network and stdlib only (AST import check); bounds (skipped folders, depth, a large file); `DOCTYPE` refused.
- **Recommendations** (`test_recommend.py`): each signal; the rules file and the catalogue validate and bad entries fail; the list for a JavaFX Maven repo, an empty repo (none), a monorepo (every language); the role filter; the person's choices win; drop rules (from a test rule) and "no drops without code"; `--decline`, `--decline all`, unknown ids; `change` clears a declined id; `--all` (groups, nothing placed or suggested listed twice); `--json`; summary lines in setup, update and `change --roles`; update shows only new ones; same output twice; older `state.json` loads.
- **Roles**: the role packs are unchanged; none of the 13 stack skills is in a role or the core pack.
- **Kit-copy-only assets** (§8.7): the rule file, placement skips the listed files, links and exact paths point into `.ai-sdlc/kit`, the scripts find their assets, `check`/`update`/`remove`/`change --drop-skill` behave, an update from 0.8.0 removes the binaries 0.8.0 placed.
- **Onboarding**: the two new steps and the section, commands and flags real, "not now" declines, no suggestion or other skill applied without a choice.
- All suites on `python3` (3.13) and `/usr/bin/python3` (3.9.6); `validate_packs.py`; `validate-skills.py`; CI `personal-e2e` (3.9 and 3.12): stack skills are not placed by setup; `recommend` in the team repo says no suggestions; the brand template is in the kit copy and not in the placed folder.
- **Manual, before merge:** the owner re-tests with the Copilot CLI on the VM (scenarios in the plan, Task 21).

## 8. Merge the owner's PowerPoint skill into `frq-brandbook` (scope addition, owner 2026-10-09)

### 8.1 What and why

The kit owner wrote a second brand skill, `frq-4-pptx-agent` v1.0 (2026-10-09): 84 files, about 12 MB (the zip lists 92 entries: 84 files and 8 folders). It builds decks on the **full official master (44 layouts)** from a JSON spec, sets the footer, audits a deck, renders it, and bundles layout previews, example slides, key visuals, logo SVGs, brand tokens and a CSS file. The in-app PowerPoint variant (`frq-4-pptx-copilot`) and the duplicate "… 2" folder are not part of this.

Owner decisions:

1. **Combine it into `frq-brandbook`.** One brand skill, no overlapping triggers. **Keep every artifact**: previews, examples, key visuals, logos, CSS, tokens and the builder.
2. **Ship the full 44-layout master**, not slim, **with personal data stripped** the same way as the 0.8.0 slim template.
3. **Release it with the stack pack, in 0.9.0.**

`frq-4-pptx-agent` never becomes a skill name. Everything lands inside `template/.claude/skills/frq-brandbook/`, the only folder the client-name exception covers (0.8.0). The placed name stays `ai-sdlc-frq-brandbook`; it stays in the core pack, for every role.

### 8.2 Assets: one tree, nothing lost

| Owner skill | Goes to | Note |
|---|---|---|
| `assets/frq-master.pptx` (8.9 MB, 44 layouts, no slides) | `assets/templates/frq-master.pptx` | Cleaned (§8.3). Used when a deck needs a layout only the full master has (§8.5). Kit copy only (§8.7). |
| `assets/layouts/*.jpg` (44 previews) | `assets/layouts/` | Unchanged. One per layout; `references/layouts.md` links each. |
| `assets/examples/*.jpg` (22 example slides) | `assets/examples/` | Unchanged. |
| `assets/key-visuals/*.jpg` (7) | `assets/keyvisual/` | Four are byte-identical to files the skill already has (ATM aircraft, defence, maritime, public safety): kept once, under the existing name. The full-size globe and train images are kept next to the 0.8.0 downscaled ones. The wide ATM aircraft photo is new: 0.8.0 left it out because its rights were unknown; the owner now keeps it, and it becomes an open item for Group Communications and Marketing (GCM). |
| `assets/logo/frequentis-logo-{blue,white,black}.svg` (traced wordmark) | `assets/logo/` | Kept next to the 0.8.0 logos (owner decision: both sets). **Prefer the 0.8.0 logos** (converted shape for shape from the template, so closer to the original); the manifest marks them `preferred`. |
| `assets/brand-tokens.json` | merged into the one `brand-tokens.json` | §8.4. |
| `assets/frequentis-brand.css` | `assets/frequentis-brand.css` | Values checked against the tokens by a test. |
| `scripts/frq_pptx.py` | `scripts/frq_pptx.py` | §8.5. |
| `references/layouts.md`, `references/build-spec.md` | `references/` | Paths updated to the merged tree. |
| `references/brand-rules.md`, `SKILL.md` | merged into the existing `references/brand-rules.md` and `SKILL.md` | §8.4, §8.6. |

`assets/manifest.json` lists every asset with its size, its source (0.8.0 or the owner skill, with the owner skill's original path) and, for the four duplicates, the original path as an alias. A **source inventory** (a test fixture with the path and SHA-256 of each of the 84 files) proves that every binary file of the owner skill is in the merged skill, byte for byte, and that every text file is mapped to where its content now lives.

**Both templates stay** (owner decision): the 0.8.0 slim template (`assets/templates/frq-template-slim-core.pptx`, 25 layouts, 1.2 MB) and the full master (44 layouts, 8.9 MB). When to use which: §8.5.

### 8.3 Cleaning the full master

The master carries personal and tenant data. The same cleaning as the 0.8.0 slim template, done by a small stdlib maintainer script (`scripts/maintainer/strip_pptx_metadata.py`, not placed in repos), so it can be redone when GCM ships a new master:

- `docProps/core.xml`: empty `dc:creator` and `cp:lastModifiedBy` (today a named employee).
- `ppt/commentAuthors.xml`: removed (a named employee and an e-mail), with its relationship and content-type entries.
- `docProps/custom.xml`: removed (MSIP sensitivity-label properties with the tenant id).
- `customXml/` (four SharePoint document-management parts): removed.
- `docProps/thumbnail.jpeg`: removed.
- `docProps/app.xml`: reduced to the application and the presentation format (it lists old titles and counts).

Everything else stays byte for byte: the slide master, all 44 layouts, the theme and the media. A test proves it against the inventory. Pictures inside the layouts whose rights are unclear stay, by owner decision, and are listed in `PROVENANCE.md` as an open item for GCM.

### 8.4 One set of facts

- **Rules:** the existing `references/brand-rules.md` (cited to the PDF and template, with conflicts C1–C10) stays the source of truth. Each section of the owner's `brand-rules.md` is merged in; a fact the 0.8.0 file lacks is added with its source "(owner skill v1.0)". `PROVENANCE.md` has a table mapping every heading of the owner's file to its new place.
- **Tokens:** one `brand-tokens.json` (the 0.8.0 format). The owner's tokens are merged in: the chart series order, the `track` grey `#EDF1F2` (marked "template KPI charts only, not in the PDF palette"), the content-area and footer values. `frq_pptx.py` and `check_brand.py` read their palette from it, so the two scripts cannot drift.
- **Conflicts found so far** (more may come up during the merge; each gets a row with the resolution). The owner accepted these resolutions on 2026-10-10; C11, C12 and C13 also go to GCM for confirmation, because they settle template-versus-PDF questions:

| # | Topic | 0.8.0 skill | Owner skill | Proposed resolution |
|---|---|---|---|---|
| C11 | Footer text | `Frequentis <class> \| © Frequentis AG <year>` | `<title> \| <presenter> \| Frequentis <class> \| © Frequentis AG <year>` | The owner's form: the master has title and presenter fields (C4). Classification and year as in 0.8.0. |
| C12 | `#EDF1F2` "track" grey | not in the palette | allowed (KPI donut tracks) | Allowed for chart tracks only; the checker accepts it there and warns elsewhere. |
| C13 | Allowed gradients | only `#004182 → #00AAE1` in new shapes (C2, C3) | also accepts the template's divider and headline stops | 0.8.0 rule for new shapes; the template's own stops are INFO (inherited), never a FAIL. |
| C14 | Default business unit | a person picks (C8) | ATM by default | **ATM by default** (owner decision): the ATM key visual and wording unless the person names another business unit. Supersedes C8's "a human picks". |
| C15 | Two logo sets | converted shape for shape | traced | Keep both (owner decision); prefer the converted ones. GCM's official logo pack replaces both when it comes. |
| C16 | "FRQ" on slides | WARN in internal files | always "Must" | Customer-facing: FAIL; internal: WARN (0.8.0 rule kept). |

### 8.5 Scripts: one builder, one check

- **Check: one path, `check_brand.py`**, stdlib only, Python 3.9, as in 0.8.0 (it also checks `.docx` and `.xlsx`). Every rule of the owner's `audit` that `check_brand.py` lacks is ported to it, stdlib only: deck starts on *Standard TITLE* and ends on *Closing Slide*; layouts that are not from the master; the master footer still showing "Presentation title" or "<by Presenter>"; template leftovers; "&" in text; several exclamation marks; rounded rectangles; chart gridlines; 3D charts; off-palette chart colours; "headline is a label, not a message" (a WARN). `frq_pptx.py audit` stays as a command, so nothing is lost, but it only runs `check_brand.py` and prints its result.
- **Build: `frq_pptx.py`** (python-pptx, lxml; Pillow only for images) is the builder: `layouts`, `build` (JSON spec with tables, charts, images, `photo_request` and `icons` placeholders), `footer`, `render`. It gets the 0.8.0 guarantees: the classification is required and checked, keyword-only, in `build()` and `set_footer()` (one of the three classes or the `Frequentis [classification to be set]` placeholder, never guessed); it **never overwrites its input** and refuses an output that already exists; `render` writes only under `.ai-sdlc/tmp/` (the LibreOffice profile too), never to `/tmp`; it sets `sys.dont_write_bytecode`; without python-pptx it prints a plain message pointing to the consent step, not a traceback.
- **`new_deck.py` is kept** as the Markdown front end: same command line, same behaviour, same 0.8.0 tests. Inside, it turns the outline into a spec and calls `frq_pptx.build()`.
- **Which template** (owner decision: keep both; proposal for when): the **slim template is the default**. Every deck built on a template carries the template's layouts and pictures, so a deck on the full master is about 9 MB even with three slides; on the slim one about 1.2 MB. The builder takes the **full master only when a slide needs a layout the slim template does not have** (the map and world-map layouts and the event layouts that the 0.8.0 slim template left out; the exact list is read from the two templates), and says so in its output ("used the full master for: World Map | EMEA"). The person can ask for either (`--template slim|full`). Apply on an existing deck keeps the deck's own master; a deck not on a company master is rebuilt on the slim one unless it needs a full-only layout. `references/layouts.md` marks each of the 44 layouts "slim and full" or "full only".
- **Dependencies only with consent**, into `~/.ai-sdlc/venv`, exactly as `ai-sdlc-doc-powerpoint` describes. No bare `pip install` anywhere in the skill. `render` needs LibreOffice and poppler; without them the skill says so and asks the person to look in PowerPoint.

### 8.6 The skill text

- `SKILL.md` keeps the 0.8.0 structure (quick reference, Create, Check, other file types) and takes from the owner skill: the message pyramid and executive versus self-explanatory decks; the Apply workflow (audit, one table of Must and Should fixes, "all, Must only, or by slide number", fix into a new file); the custom-visual step (open the matching example first); the German-deck rule; the non-negotiables. 0.8.0 rules win where they are stricter: one question at a time, the outline as a hard stop before building, the classification asked and never guessed, every change confirmed, render into `.ai-sdlc/tmp/`.
- **Brand by default** stays exactly as in 0.8.0 (one rule in each file skill, the core instructions unchanged).
- **The description stays at most 1,024 characters** (today 973). It is rewritten, not extended, so it also covers "build a deck from a spec", "restyle or fix an existing deck" and "the 44 master layouts". `SKILL.md` stays under 220 lines; depth goes to `references/`.
- `PROVENANCE.md` adds a section: "Merged from the kit owner's own skill frq-4-pptx-agent v1.0, 2026-10-09", the file mapping, the cleaning, the conflicts, and the new GCM open items (layout photos with unclear rights, the wide ATM aircraft photo).

### 8.7 Size: big assets stay in the kit copy (owner decision, 2026-10-10)

The brand skill grows from about 2 MB to about 13 MB. Placing it would put it in each repo twice (the kit copy in `.ai-sdlc/kit` and the placed `.agents/skills/ai-sdlc-frq-brandbook/`). So in 0.9.0 **the big files stay only in the kit copy**:

- **The rule, per skill, as data.** A skill folder may hold a `.kit-only` file: one glob per line, relative to the skill folder, `#` comments. Setup never places a file that matches, and never places `.kit-only` itself (dotfiles are never placed). It is generic, so another skill (or the client) can use it later.
- **For `frq-brandbook`, every binary file is kit-only** (a simple rule that is easy to check): `assets/templates/*`, `assets/layouts/*`, `assets/examples/*`, `assets/keyvisual/*`, `assets/background/*.jpg`, `assets/logo/*.png`. Placed: `SKILL.md`, `references/`, `scripts/`, `brand-tokens.json`, `assets/manifest.json`, `assets/frequentis-brand.css` and the SVGs (logos, gradient: text, about 130 KB together). The placed skill stays at about 0.4 MB.
- **Exact paths.** Copilot's search skips git-excluded folders, so it cannot find these files by search. `SKILL.md` and `references/` name them by exact path, `.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/…`. A Markdown link inside the skill to a kit-only file is rewritten at placement to point into `.ai-sdlc/kit/` (the same mechanism that already rewrites links that leave a skill folder).
- **Scripts find their assets** with one function: the placed folder first (`<skill>/assets/…`), then `.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/…` found by walking up from the current folder or the script to the repo root, then the script's own folder (when it runs inside the kit itself, as in the kit's tests). If none has the file: a plain error naming the expected path and saying "say 'check the kit'".
- **`check`** reports `missing:<kit path>` (a problem) when a placed skill's kit-only file is missing from `.ai-sdlc/kit`. **`update`** replaces the kit copy, so new assets arrive with it; the binaries 0.8.0 placed in `.agents/skills/ai-sdlc-frq-brandbook/assets/` are no longer wanted and are removed while unedited (the existing reconcile), edited ones are kept and reported. **`remove`** deletes the kit folder, so the assets go with it. **`change --drop-skill frq-brandbook`** removes the placed files; the kit copy keeps its assets (it always holds the whole library). The kit never runs without `.ai-sdlc/kit`, so the assets are always there.
- **The manifest** (`assets/manifest.json`) gets `"placement": "kit-only" | "placed"` per file; a test checks it against `.kit-only`.
- **CI** `personal-e2e`: the template is in the kit copy and not in the placed folder; the checker runs from the placed folder and finds its assets; remove still ends byte-identical.

Result: **per repo about 13 MB once** (in `.ai-sdlc/kit`), plus about 0.4 MB placed. The size-budget test splits: the whole skill folder at most 14 MB, the placed files at most 0.6 MB.

### 8.8 Tests

`test_frq_brandbook.py` gains: the source inventory (every file present or mapped); the full master is metadata-free and otherwise identical (44 layouts, no slides, no comment authors, no custom properties, no `customXml/`, no thumbnail, empty creator, no `@` in any XML part, media and layouts byte-identical to the owner's master); every layout preview and example present and listed in the manifest with its size; `references/layouts.md` names all 44 layouts and links an existing preview for each; tokens and CSS agree; `check_brand.py` stays stdlib and passes on a deck built from the full master; the ported audit rules each fail a small fixture; `frq_pptx.py` (only where python-pptx is installed, as in 0.8.0) builds a deck from a spec with several layouts (title, agenda, a divider, a 50:50, a map, a timeline, closing) that passes the check, refuses a missing or wrong classification, refuses to overwrite its input or an existing output, and renders only under `.ai-sdlc/tmp/`; `new_deck.py` keeps its 0.8.0 tests; the slim template is the default and the full master is taken only for a full-only layout; no `pip install` in the skill; the two size budgets; nothing binary placed, and the placed skill builds and checks a deck with its assets in the kit copy; the client-name rule (no new `frq-*` skill name, the new files inside the brand folder only).

## 9. Out of scope

- **Connectors** for SonarQube, Black Duck and Artifactory: **0.10.0** (owner decision 4). SharePoint later.
- **Teams**: designed in §6, built later.
- Automatic upstream updates (updating stays manual, per `PROVENANCE.md`).
- Gradle-specific guidance (the client uses Maven; Gradle files still count as `java` for detection).
- The skills in §2.1.

## 10. Decisions (owner, 2026-10-09/10)

1. **Skills:** the nine vendored and four kit-written skills of §2 and §3, as listed (2026-10-09).
2. **Placement: library skills plus suggestions** (2026-10-10). None of the 13 is in a role pack; role packs stay as they are. They arrive only through an accepted suggestion or the person's own choice (§4.2).
3. **Other skills step** (2026-10-10): after the suggestions, onboarding offers every other available skill, grouped, one line each; picks are stored like `--add-skill`; also later with "show me the other skills" (`recommend --all`) (§5.4, §5.5).
4. **Size is fixed in 0.9.0** (2026-10-10): the brand skill's binary assets stay only in the kit copy; the placed skill names them by exact path; the scripts find them (§8.7).
5. **Both templates stay** (2026-10-10): slim is the default, the full master when a layout needs it (§8.5).
6. **ATM is the default business unit** (2026-10-10; C14).
7. **Versions and tools are detected, never assumed** (2026-10-10): Go, React, Jest, AssertJ, Mockito, the JavaFX source and how Black Duck runs are read from the repo by `detect_stack.py`; when something is not found, the skill asks.
8. **Names kept** (2026-10-10): `maven-via-artifactory` and `110-java-maven-best-practices` (placed `ai-sdlc-110-java-maven-best-practices`). The kit has never renamed a vendored skill, so it does not start now.
9. **The wide ATM aircraft photo ships** (2026-10-10), listed in `PROVENANCE.md` as an open item for GCM, with the layout photos whose rights are unclear.
10. **Both logo sets stay** (2026-10-10); the 0.8.0 ones (converted shape for shape) are preferred.
11. **C11–C16 resolutions accepted** (2026-10-10); C11, C12 and C13 go to GCM for confirmation.
12. **Merge the owner's `frq-4-pptx-agent` into `frq-brandbook`**, full master cleaned, release in 0.9.0 (2026-10-09; §8.1).
13. **Connectors** (SonarQube, Black Duck, Artifactory) in 0.10.0; SharePoint later (2026-10-09).
