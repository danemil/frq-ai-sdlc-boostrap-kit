# Onboarding, Roles & Skills — Design

**Status:** design agreed, awaiting implementation approval · **Version:** 0.2 · **Author:** Emil Dan (+ AI) · **Created:** 2026-10-07 · **Last reviewed:** 2026-10-07

Design-first record for three linked changes to the kit: (1) a seat model that absorbs the FRQ role catalogues in [`docs/FRQ-Roles/`](../FRQ-Roles/), (2) a curated skill set per seat, and (3) onboarding that supports multiple seats, re-runs, and a post-install catalogue. Nothing under `template/` changes until this design is approved; implementation then gets its own plan.

---

## 1. Inputs

**FRQ catalogues.** Three role files (Product Owner PO01–PO10, Scrum Master SM01–SM12, Product Manager PM01–PM12) plus a cross-role matrix. They are pandoc conversions of `.docx` with no fixed schema: each skill has `Purpose`, then one variably-labelled list (Checks / Identifies / Outputs / Produces / …), optional guardrails under four different labels, and sometimes a fixed verdict enum. The consistent thread is the safety stance: AI suggests, humans decide; report evidence, never compliance; no judgements about individuals; no causal claims without source, definition and period. SAFe vocabulary throughout (ART, PI, I&A, ROAM, WSJF), but RTE and Business Owner are never named.

**Kit today.** Five seats (Architect, EM, Product, Developer, QA) in `template/scripts/session/seat-profiles.json`, one `playbook-<seat>` skill each. Product merges PO and PM. No Scrum Master or RTE anywhere. Constraints found:

- `validate-seat-profiles.py` hard-codes `KNOWN_SEATS` and requires all of them, so adding or splitting seats is a validator + test change, and the "custom seat" promise in ONBOARDING B1 cannot pass validation.
- Profile `connectors` disagree with playbook §4 in four places (Architect/EM cite context7, Product cites knowledge, QA cites docs-wiki).
- SPEC.md §7 "add a seat" recipe omits the profile entry, validator and ONBOARDING list.

**FRQ delivery environment (stated 2026-10-07).** Developers work inside a VM with **GitHub Copilot** as the AI harness, Cartograph running alongside it, on **Zulu Java 17/21, Go and React**. MCP servers are not yet approved, so tooling is CLI-first. COBOL belongs to a different stream and is out of scope here. **Toolchain:** Bitbucket (not GitHub), Jira, Confluence, **Jama** (requirements management), Maven, Jenkins. The kit is currently written for Claude Code, so harness portability is a design input (see §4).

## 2. Decision: seat model

| Decision | Choice |
|---|---|
| Seat count | **8 seats**: Architect, EM, **PO**, **PM**, **SM**, **RTE**, Developer, QA |
| Product | Split into PO and PM. `Product` survives as an **alias** that selects PO + PM together (back-compat for existing `USER.md` files and docs). |
| RTE | Added now, because PI Planning, Inspect & Adapt and ROAM are in FRQ scope and need an ART-level owner. |
| People holding several seats | Handled by multi-seat selection (§4a), not by merged seats. |
| EM ↔ SM | **SM owns** sprint cadence, ceremonies, flow metrics and impediments. **EM keeps** engineering practice, CI/CD gates, capacity and release approval. `playbook-em` loses "sprint cadence, velocity". |
| RTE scope | **SAFe projects only.** `bootstrap.sh --framework scrum|safe` (default `scrum`) is recorded in the project; RTE, and the PI/ART/WSJF/ROAM skills (SM09-team part stays), are offered only under `safe`. Under `scrum`, SM10/SM11 fall back to SM and PM12 is not offered. |
| Traceability | One shared skill, two views. **PO** owns the requirement end (requirement → story → AC completeness, FRQ PO04). **QA** owns AC → test → result → defect and signs off the gate. |

### 2.1 Proposed FRQ skill ownership (to confirm with the client)

Primary owner first; others consume a role-specific view as in the FRQ matrix.

| FRQ skill | Primary seat | Also used by |
|---|---|---|
| PO01 Story Readiness, PO02 AC Quality, PO03 Ambiguity, PO05 Refinement Prep, PO06 Story Split, PO07 DoR, PO10 Requirement Diff | PO | PM (oversight), QA (AC testability), SM (process check) |
| PO04 Requirement-to-Test Traceability, PO08 DoD Evidence | PO | QA (co-owns traceability today), PM |
| PO09 Functional Change Impact | PO | Architect, PM |
| SM01 Flow Health, SM02 Progress Evidence, SM03 Blockers, SM05 Daily Prep, SM06 Review Pack, SM07 Retro Patterns, SM08 Flow Metrics, SM12 Ceremony Builder | SM | EM (capacity), PO |
| SM04 Dependency Radar | SM (team level) | RTE (cross-team), PM |
| SM09 PI Planning Readiness | SM (team readiness) | RTE (train readiness) |
| SM10 I&A Evidence, SM11 ROAM Prep | **RTE** | SM, PM |
| PM01 Feature Readiness, PM02 Feature-to-Story, PM04 WSJF Prep, PM05 PI Objectives, PM06 Decision Brief, PM08 Risk & Compliance Intake, PM09 Insight Synthesis, PM11 Outcome Measures | PM | PO, RTE |
| PM03 Roadmap Dependencies, PM07 Cross-Product Impact, PM10 Release Scope Evidence | PM | RTE, Architect, QA |
| PM12 ART-Level Progress & Integration | PM | **RTE** (facilitates) |
| Cross-role: Decision recorder, Documentation sync, AI-use safety check | all | — (no FRQ skill exists; see §3) |

### 2.2 Open questions

None for the seat model. Playbook text for the three new seats (PO, PM split from Product; SM; RTE) is drafted at implementation.

## 3. Skills inventory

Sources scanned: kit `template/`, `~/.claude/skills` (124 skills, mostly symlinks into `~/.agents/skills`), 19 installed plugins (+2 synced Cowork plugins), and 21 project-level skill folders under `~/work`.

### 3.1 What the kit ships

| Skill / asset | Kind | Seats |
|---|---|---|
| `playbook-{architect,em,product,dev,qa}` | role contracts | one each |
| `git-verbs` | plain-language git for guided/hidden operators | PO, PM, some QA |
| `skill-creator` | minimal skill authoring | all |
| `docs/ai-context/skills/product/backlog-playbook.md`, `qa/traceability-playbook.md` | read-on-demand MCP playbooks | PO, QA |
| `scripts/{decks,jira,knowledge,spend,git,session}` | capability backends (snapshot, Jira ledger, KG MCP, spend, ticket hook, session verbs) | various |

Referenced but not shipped: brainstorming, writing-plans, test-driven-development, systematic-debugging, code-review, "test-generation/QA skills", deck-builder (designed, not built), pptx/docx generation.

Repo hygiene found: `template/scripts/harness/` and `scripts/install/` hold only orphan `.pyc` files from the unmerged `feat/brownfield-installer` branch; root `.claude/settings.local.json` enables a `code-review-graph` MCP defined nowhere in the repo.

### 3.2 Locally available, SDLC-relevant

| Skill | Where | Purpose | Seats |
|---|---|---|---|
| superpowers (brainstorming, writing-plans, executing-plans, TDD, systematic-debugging, verification, requesting/receiving-code-review, worktrees, finishing-branch, writing-skills) | plugin (obra 4.3.1 ON; official 6.4.1 OFF) | process baseline | Dev, Arch, QA, EM |
| code-review | user skill + plugin `/code-review` | Standards + Spec diff review | Dev, QA, Arch |
| diagnosing-bugs (supersedes diagnose) | user | bug diagnosis loop | Dev, QA |
| tdd | user | red-green-refactor | Dev, QA |
| grilling, grill-with-docs, batch-grill-me | user | one-question stress-test interviews | PO, PM, Arch |
| domain-modeling (supersedes ubiquitous-language) | user | glossary + ADRs | Arch, PO |
| to-spec, to-tickets (supersede to-prd, to-issues) | user | spec and tracer-bullet tickets on the tracker | PO, PM, SM |
| triage, qa | user | issue triage; conversational bug filing | PO, SM, QA |
| wayfinder, to-questionnaire | user | decision tickets; stakeholder questionnaires | PM, Arch, PO |
| improve-codebase-architecture, codebase-design, design-an-interface | user | architecture upkeep | Arch, Dev |
| technical-architecture-council, a-team | user | multi-perspective decision review | Arch, EM, PM |
| research, prototype | user | cited research; throwaway prototypes | all |
| git-guardrails-claude-code, setup-pre-commit | user | safety hooks | Dev, EM |
| drawio, uml, archimate, bpmn, c4-like `architecture`, mindmap, infographic, vega | user (also in FRQ-COBOL-sample) | diagrams and charts | Arch, PM, SM, EM |
| document-skills (docx, xlsx, pptx, pdf, doc-coauthoring, internal-comms, webapp-testing) | plugin ON | documents, status comms, web testing | all; QA |
| claude-md-management, claude-code-setup | plugin (project / OFF) | CLAUDE.md upkeep; automation recommender | Arch, EM |
| context7 | plugin (project) + kit `.mcp.json` (disabled) | live library docs | Dev, Arch |
| security-guidance 2.0.0 | plugin ON | security hooks + commit review | Dev, QA, Arch |
| claude-mem (standup, weekly-digests, agent-cost-report, pathfinder, oh-my-issues) | plugin ON | memory + reporting | SM, EM, Arch |
| design (user-research, research-synthesis, accessibility-review) | synced Cowork plugin | discovery; a11y | PM, PO, QA |
| defending-code harness (threat-model, vuln-scan, triage, patch) | project (COBOL samples) | security lane | Arch, QA, Dev |
| playwright-cli | project ([other project]) | browser test automation | QA |
| doc-convert | project (NOTES) | DOCX ↔ MD/Mermaid | Arch, PM |

Not SDLC-relevant (excluded): ~27 marketing/brand, ~12 frontend design-taste, databricks, huggingface, n8n, paper, domain skills.

### 3.3 Duplicates to resolve

superpowers installed from two marketplaces (older obra 4.3.1 is the active one); security-guidance ×2; frontend-design ×4; review vs code-review; diagnose vs diagnosing-bugs; to-prd/to-issues vs to-spec/to-tickets; ubiquitous-language vs domain-modeling; write-a-skill / writing-great-skills / skill-creator / superpowers:writing-skills.

### 3.4 Gaps nothing covers

No skill anywhere (kit, local, or plugin) implements the FRQ core: story readiness / DoR, AC quality, requirement-to-test traceability, flow health, progress-evidence correlation, dependency/blocker radar, PI/ART/WSJF/ROAM, decision recorder for non-architects. These are the kit's own skills to build; §5 covers what can be borrowed around them.

### 3.5 Cartograph evaluation (hands-on, 2026-10-07)

**FRQ stack re-test** (spring-petclinic, a Java 21 demo, cobra, go-kit, bulletproof-react; scratch copies, registry unchanged). Build takes 1–2 s and parses all source files. Config, `.yml`, `.properties`, templates and `pom.xml` are skipped silently.

| Criterion (1–5) | Java 17 / Spring | Java 21 features | Go | React (TS/TSX) |
|---|---|---|---|---|
| Parse support | 4 | 2 (records not extracted) | 5 | 3 (`forwardRef` components missing) |
| Symbol accuracy | 3 (overloads collapse) | 2 | 5 | 3 |
| Relationship accuracy | 3: DI-typed calls good; no MockMvc→controller→test link | 2 | 2: name-matched callers, ~60 % callees, no interface satisfaction | 4: `@/` aliases, JSX, hooks good |
| Wiki | 1 | 1 | 1 | 1 |
| detect-changes / review | 2: changed symbols + entry flows good; test gaps wrong | n/a | 1 | 4 |

**Reliable:** `build`/`update`, `detect-changes` for *which symbols changed* and *which entry flows they touch*, `callers_of` as a recall list, `inheritors_of` for Java classes, `review-context`/`impact` on React, `large-functions`, Spring endpoint extraction. **Not reliable:** `tests_for` / "Untested" (wrong on Spring MockMvc and Go cross-package tests, stated as certain), `dead-code` (mostly false positives), Go `impact`/`review-context`, interface→implementation questions, `wiki`/`communities`/`architecture` as documentation. Always use `--format json` and key on `name`/`file`/`line`, because `qualified_name` truncates on long paths.

First pass (Python kit scripts and COBOL sample, kept for reference; COBOL is another stream):

Cartograph 0.9.7 (fork of code-review-graph 2.3.8) was run on scratch copies of the kit's `template/` (Python/bash) and of `FRQ-COBOL-sample`. No LLM or network is used by `build` or `wiki`; both run in about a second.

| Criterion (1–5) | Python (kit) | COBOL (FRQ sample) |
|---|---|---|
| Language support | 4: python, bash, sql, js | **1**: no `.cbl/.cpy/.jcl` grammar; COBOL dropped **silently** |
| Accuracy of what it states | 3: symbols/lines ~100 %, relationships ~50 % (builtins as "dependencies", missing callers) | 4, but only via the repo's own regex bridge `inject-cobol-graph.py` |
| Coverage | 2: no shell scripts without functions, no Markdown/JSON/skills | 1 vanilla, 3 with bridge (loses 88-levels, copybook→program use) |
| Explanatory depth | **1**: member tables, no purpose text | **1** |
| Navigation / freshness | 2: no cross-links, absolute paths, orphaned pages, unstable page names | 2 |

**Verdict: the wiki command is poor; the graph underneath is useful.** `carto wiki` is a 277-line template that dumps symbols per directory; it should not be shipped or committed as documentation. The graph's strengths are tree-sitter CALLS/TESTED_BY edges, execution flows and `detect-changes` blast radius, which the kit's own KG (`scripts/knowledge/`, docs + issues + commits, regex symbols, no call graph) lacks. The two are complementary.

Operational cautions: `build` registers the repo in global `~/.cartograph/registry.json` unasked (scratch entries were unregistered afterwards); `--data-dir` also writes that registry; never run `install`/`hook`/`daemon` from the kit.

### 3.6 Copilot fit (FRQ harness)

Copilot already reads most of the kit unchanged. VS Code Chat and Copilot CLI read `AGENTS.md`. All Copilot surfaces discover `.claude/skills/`. Copilot CLI also runs `.claude/settings.json` hooks. Cartograph 0.9.7 targets **Copilot only** and needs **no MCP**. A per-developer `carto install` writes six `.github/skills/*`, one `.github/instructions/cartograph.instructions.md` and a `.github/hooks/cartograph.json`, all excluded locally via `.git/info/exclude`. The kit's own skills are left alone.

| Gap | Fix | Effort |
|---|---|---|
| **IntelliJ Copilot Chat does not read AGENTS.md**, so Java devs miss the brief and the USER.md gate | Generate `.github/copilot-instructions.md`: a pointer plus the hard constraints and gate inlined | S |
| `.claude/rules/*` (`paths:`) not seen by Chat | Generate `.github/instructions/*.instructions.md` (`applyTo:`) | S |
| `start.sh` prints prose, but VS Code expects JSON; IntelliJ has no session hooks | `--json` mode; IntelliJ fallback "run `scripts/session/start.sh`" in instructions | M |
| SessionEnd (`auto-save`, `collect-usage`) exists only in Copilot CLI | Move to SessionStart catch-up or explicit git-verbs | M |
| Spend telemetry parses Claude transcripts only | Copilot usage-metrics API (seat-level) or CLI logs; dashboard becomes approximate | L |
| Knowledge layer is exposed via MCP (blocked) | Add a `knowledge` CLI; Cartograph for code graph, kit KG for docs↔ADR↔story | M |
| Onboarding assumes brew/sudo, browser OAuth, one JDK | VM profile: verify-then-report, proxy/CA setup incl. each Zulu JDK `cacerts`, device-code auth, Maven/Gradle toolchains for 17/21 | M |

Prior art: the unmerged `feat/brownfield-installer` branch has a data-driven harness adapter (`harnesses.json`, `sync.py --check` drift gate). Its Copilot row is stale ("no hooks") and it has no Copilot Chat row. Recommended direction (decided in §4): **keep the Claude Code sources canonical and generate the Copilot files from them**, applying CLI-first only to the knowledge and connector layer.

**Verified on the FRQ VM (2026-10-07, Copilot CLI 1.0.91, VS Code 1.138.0; IntelliJ IDEA 2026.2.3 + Copilot plugin 1.18.0 not tested):** 1 ✅ interactive / ❌ `copilot -p` · 2 ✅ · 3 ⏸ · 4 ⏸ · 5 ⏸
- Copilot CLI also loads `.github/copilot-instructions.md` (the brief is read alongside AGENTS.md).
- Org Copilot policy disables third-party MCP servers.
- Checks 3–5 to be run in Task 12 step 2 before Phase 0 closes.

## 4. Onboarding enhancements

### 4.0 Baseline v1 flow (FRQ: Ubuntu VM, Copilot, no MCP)

| Step | What happens | Who acts |
|---|---|---|
| 0. Prerequisites | git, python3, Node (for Copilot CLI), Copilot CLI logged in with device code, proxy/CA check | operator, guided checklist |
| 1. Adopt the kit | brownfield installer `--dry-run`, human reviews the diff, then apply. Merges next to existing code and docs, never overwrites. Generates `.github/copilot-instructions.md` and `.github/instructions/*` | operator approves |
| 2. Start Copilot CLI | reads the brief, sees no `USER.md`, starts onboarding | Copilot |
| 3. Onboarding | Phase A: environment, VM prep, Cartograph `install` + `build` (failures recorded with retry commands). Phase B: one or more seats, git comfort, playbooks. Then the catalogue of extras | Copilot runs it, operator answers and approves |
| 4. Work by role | session start injects the held seats' context; role skills available in Copilot CLI, VS Code and IntelliJ; Cartograph used under the kit's usage rule | operator + Copilot, human validates everything |
| Any time | re-run onboarding to change seats | operator |

**Fallback (no working harness yet):** onboarding must also be runnable without an AI, as a scripted wizard (`scripts/onboard.sh` or `.py`) that walks the same Phase A/B steps and writes the same `USER.md`. Cartograph setup follows, and Copilot CLI starts last. Both paths share one step definition so they cannot drift.

**Cartograph in v1:** onboarding runs `carto install` + `carto build`. `carto wiki` is **opt-in**, labelled "raw symbol index, not documentation", never committed, and regenerated on each build. The kit ships a Cartograph usage rule for both `.github/instructions/` and `.claude/rules/`: trust `detect-changes`, `callers_of`, `inheritors_of` and React impact; never treat `tests_for`, "Untested", `dead-code` or wiki pages as decisions; cite file:line for human verification.

Prerequisite work: finish and merge `feat/brownfield-installer`, and update its Copilot rows (hooks are now supported; add Copilot Chat).

### 4a. Multi-seat selection (approved 2026-10-07)

**Data model.**
- `USER.md` holds `Seats: PO, SM` (a list) plus `Primary seat: PO`. The primary seat fills every place that must stay single-valued: the branch slug `session/<primary>/…`, the metrics `seat` column, and the default frontmatter `owner`.
- `seat-profiles.json` moves to v2 with these new fields:
  - `display_name`
  - `frameworks`: `["scrum","safe"]`; RTE is `["safe"]`
  - `aliases`: `Product → [PO, PM]`
  - `bundle`: `skills`, `optional_skills`, `clis` (catalogue ids)
  - `tools`: per-OS install and verify commands, replacing the prose in ONBOARDING A2
- The validator reads the seat list from the file instead of a hard-coded `KNOWN_SEATS`. Which seats are required depends on the project's framework.

**Combination rules when one person holds several seats.**

| Field | Rule |
|---|---|
| Playbooks | Load all held playbooks. On a write, the agent states which seat it acts as, and `owner` = that seat |
| Skills, CLIs | Union of the bundles |
| Git comfort | Propose the most git-native default among held seats (holding Dev implies git-native); the user confirms |
| First task, default model | From the primary seat |
| Co-owned boundaries (e.g. EM capacity vs SM cadence) | Playbook rules still apply; holding both seats does not merge decision rights |

**Operator flow.** Onboarding asks "Which seats do you hold on this project?" and accepts several answers. If more than one is picked, it asks which is primary. `Product` expands to PO + PM. RTE is shown only when the project framework is `safe`.

**Metrics.** The `sessions.seat` column keeps the primary seat, and a new `seats` column lists every held seat.

**One parser.** A new `scripts/session/seats.py` replaces the three `grep | head -1` parsers in `lib.sh`, `start.sh` and `switch-seat.sh`. The shell scripts call it.

**Visibility.** Kit skills stay committed in `.claude/skills/`. Claude Code and Copilot discover every skill in that folder, so the folder cannot be filtered per user. Seat selection therefore controls three things: which playbooks are injected at session start, which CLIs and user-level extras get installed, and the Cartograph profile. It does not control which project skills exist.

### 4b. Re-runnable onboarding (approved 2026-10-07)

- **Gate.** No `USER.md` runs the full onboarding. If `USER.md` exists, the agent reads it. Saying "re-run onboarding" (or running `onboard --reconfigure`) re-enters Phase B with current values pre-filled, and Phase A sections can be re-run on request.
- **State.** A git-ignored `.ai-sdlc/user-state.json` records every item installed per seat, with its source (`kit` or `user`), version and install command. This file is the basis for the diff.
- **Diff on change.** Every removal needs per-item approval, and every change is logged in the state file and summarised at the end.
  - Install what newly selected seats need.
  - List what dropped seats no longer need, and offer removal only for items onboarding itself installed. User-installed items and committed project files are never removed.
- **Compatibility.** `switch-seat.sh` becomes a thin wrapper over reconfigure. It no longer overwrites a custom git-comfort choice.
- **`doctor`.** A read-only health check of tools, auth, proxy, Cartograph graph freshness, and drift between `USER.md` and the state file. Re-running onboarding calls it first.
- **Both paths.** The scripted fallback wizard and the Copilot-driven flow share one step definition.

### 4c. Post-install catalogue (approved 2026-10-07)

- **Single source.** `catalogue.json` holds every optional extra: skills, CLIs, IDE extensions, plugins, and MCP servers (dormant).
- **Entry fields.** `id`, `kind`, a one-line `summary`, `seats`, per-OS `install` (no-sudo first), `verify`, `uninstall`, `requires` (network, sudo, GUI), licence, pinned source and version, and an HITL note.
- **Onboarding display.** After the seat bundle installs, onboarding groups entries as "recommended for your seats", then "other". The user picks several entries at once. Each choice installs at user or local scope and is recorded in `user-state.json`. MCP entries are **fully supported in the data model but not offered**: a project policy switch `policy.mcp_allowed` (default `false` for FRQ) hides them from onboarding, the pick list and seat bundles until approval lands. Flipping it to `true` (via PR, EM/Architect-approved) makes them selectable with no other change; the validator still checks MCP entries while hidden, so they are ready on approval.
- **Validation.** A validator checks every catalogue id referenced by a seat bundle. A generated `docs/catalogue.md` gives humans a readable view.

**Catalogue seed (from the 2026-10-07 CLI survey; all install without sudo, all emit JSON/SARIF/JUnit):**

| Area | v1 entries | Seats | Notes |
|---|---|---|---|
| Requirements | **Jama adapter (kit-built, stdlib REST)** | PO, PM, QA, Arch, RTE | No CLI exists; OAuth client-credentials; read-only items, relationships, test runs |
| SCM | `bkt` (Bitbucket Cloud + DC) | Dev, QA, SM, EM, Arch | Allow-list read verbs |
| CI | `jk` (Jenkins), Jenkins REST adapter, declarative-linter via curl | SM, RTE, EM, Dev, QA | Read-only Jenkins user; allow-list read verbs |
| Java | Maven wrapper read-only goals, SDKMAN + Zulu 17/21, SpotBugs, PMD, Checkstyle (Maven plugins) | Dev, Arch | Maven needs proxy in `~/.m2/settings.xml` |
| Go | golangci-lint v2, gotestsum, govulncheck | Dev, QA, Arch | |
| React/TS | eslint, tsc, vitest/jest reporters, knip | Dev, QA | project-local |
| Testing | playwright-cli (#7), Schemathesis (#8), Hurl, Pact (needs broker), k6 (AGPL, legal check), `@axe-core/playwright` | QA, Dev | browser-use, Stagehand, chrome-devtools CLI excluded (second LLM / cloud / hidden MCP) |
| Security | semgrep CE (vendored rules, `--metrics=off`), gitleaks or betterleaks, syft + grype | Dev, Arch, EM | Pin + checksum every scanner (trivy 0.69.4 compromise, 2026-03) |
| Docs | pandoc, markdownlint-cli2, vale, draw.io desktop CLI, mermaid-cli (reuse Playwright Chromium) | all | |

**Kit-built gaps:** Jama adapter; a cross-tool evidence correlator (Jama → Jira → Bitbucket PR → Jenkins build → JUnit, keyed on Jira keys) that powers FRQ SM02, PO04 and PO08; a Jenkins multi-build test-trend adapter.

### 4d. Further enhancements

**Design constraint (2026-10-07):** the client will own and version the kit, adding their own skills, plugins, agents and CLIs. Every mechanism below must be extensible by their team without us. That means data-driven manifests, a one-file addition plus one documented command for each extension point, validators with actionable messages, and gates that run in their Jenkins and Bitbucket.


1. **Harness-agnostic generation (accepted).** Copilot files are generated from the canonical sources: `.github/copilot-instructions.md` (pointer + hard constraints + gate inline), `.github/instructions/*`, and `.github/hooks/*` (bash + PowerShell). A CI drift gate runs in Jenkins. Built on the brownfield branch's `harnesses.json` adapter, with its Copilot rows updated. For client ownership, adding a rule, skill or harness is one file plus `sync --write`, and the drift gate says exactly which command to run.
2. **Client-ownership readiness (accepted).**
   - **Versioning.** Semantic versioning plus `CHANGELOG.md`. The installer records the kit version in each adopting repo.
   - **Upgrades.** Through the brownfield manifest: kit-owned files are replaced, and seeded or merged files get a reviewable diff.
   - **Recipes.** `CONTRIBUTING-KIT.md` has one recipe per extension point (seat, vendored skill, catalogue entry, rule, agent, harness), each ending with the validator that must pass in Jenkins.
   - **Vendoring policy, written down.** Pin the source, record the licence, review bundled scripts, apply the FRQ guardrail overlay.
3. **FRQ guardrail rule pack (accepted).** One always-on rule, generated for Copilot and Claude Code via #1, so it covers every skill, including future client-added ones. It opens with the governing rule: a human validates every line of AI-written code and every AI decision. Then the FRQ rules: AI suggests and humans decide (never sets ROAM, WSJF or approvals); evidence found or not found, never "compliant"; no judgements about individuals and team level only; no causal claims without source, definition and period; the team's approved DoR and DoD templates only. A self-check runs before any evidence report, verdict or status summary:
   - Is every claim sourced?
   - Is there no per-person judgement?
   - Does it say "evidence", not "compliant"?
   - Is the human owner named?
   - Is it read-only unless approved?

   Vendored-skill overlays shrink to their skill-specific parts.
4. **Normalised FRQ skill schema + FRQ starter skills: deferred to next week.** Decide after reviewing the other team's harness, which may already implement some FRQ skills. **Expect more FRQ role catalogues** beyond PO, SM and PM. The template must therefore be role-agnostic, and importing a new role catalogue becomes a recipe under #2. Per §4a, that recipe is a new `seat-profiles.json` entry plus a playbook plus normalised skill specs, with no code change. Still to build when resumed: PO01, SM03/SM04 radar, PM01 and PM12. Already covered: PO02 by #2, PO04 and SM02 by #9, SM01 by #1.
5. **Tool permission allow-lists (accepted, adjustable granularity).**
   - **What is generated.** Copilot CLI tool permissions and Claude Code permission settings, produced by the #1 generator from one data file the client maintains.
   - **Three levels.** `allow` covers reads (`jk run ls`, `jk test report`, `bkt pr list`, `carto detect-changes`, adapter dry runs, `mvn dependency:tree`). `ask` covers every write (merge, trigger, `--apply`, `git push`, installs). `deny` covers destructive commands (force-push, branch delete, Jenkins credential and node edits).
   - **Adjustable granularity, in layers.**

     | Layer | Where it lives | What it can change |
     |---|---|---|
     | Kit default | per held seat | the starting lists |
     | Project override | committed, PR-approved by EM or Architect | share one list across seats, per-seat or per-command tweaks |
     | User override | local, git-ignored | tighten only |

   - **Loosening rules.** Moving `ask` to `allow` needs a project-level PR. `deny` can never be overridden by a user.
   - **IDE chat.** IntelliJ and VS Code chat have coarser permission control, so the #3 guardrail pack remains the backstop there. The design states this plainly.
6. **Environment provisioning manifest (accepted; works with the parallel devcontainer stream).**
   - **Contract.** `env-manifest.json`, which shares data with `catalogue.json`, is the one contract for what must be present before onboarding. Each entry records its seats, its needs (sudo, network, GUI) and a verify command.
   - **Two side-by-side ways to satisfy it.**
     - (a) A **VM image checklist**, generated for the image builder.
     - (b) **Devcontainer features**, owned by the parallel devcontainer stream. Examples: the `java` feature with Zulu 17/21, `node`, `go`, Playwright browsers in `postCreateCommand`, the corporate CA, and Cartograph.
   - **Verification.** The `doctor` check from 4b verifies the contract the same way in a VM or a container, verifying only what the held seats need.
   - **Ownership.** The kit owns the contract and the checks, not the devcontainer. Alignment points with that stream: feature versions, proxy and CA handling, and where Copilot CLI runs.


- a. Multi-seat selection
- b. Re-runnable onboarding
- c. Post-install catalogue
- d. Further enhancements

## 5. Accepted skill additions

**Governing rule:** every line of AI-written code and every AI decision is 100% validated by a human. Each addition must keep a human gate: read-only, draft-for-approval or review mode. Skills that execute, commit or write to trackers autonomously are excluded or gated.

**Tooling constraint (2026-10-07):** MCP servers are not yet approved; tooling is CLI-first plus Cartograph. Skills written against the Atlassian MCP (#1, #4) are vendored with a CLI access path; the MCP path stays as a later upgrade and `.mcp.json` entries remain dormant.

Policy for every addition: vendor a pinned copy under `template/.claude/skills/`, record source repo + commit + licence in the skill's frontmatter `metadata`, and apply an FRQ guardrail overlay (no per-person judgement, evidence not verdicts, read-only unless asked).

### 5.0 Jira / Confluence access without MCP

**Superseded and extended (2026-10-08, owner decision):** access now goes through personal, read-only connectors (Jira, Confluence, Bitbucket DC, Jama, Jenkins) with per-user credentials set by `setup.py connect`, outside the repo; see [`2026-10-08-connectors-design.md`](./2026-10-08-connectors-design.md). The API notes below still hold.

Neither Atlassian CLI covers what #1 and #4 need. `acli` (Atlassian, free) is **Cloud-only** and exposes no changelog. `ankitpokhrel/jira-cli` (MIT) supports Data Center but also has no changelog and cannot read Confluence. The kit therefore **extends its own stdlib REST adapter** (`scripts/jira/export_jira.py`, already Cloud + DC with both paging styles) into a small `scripts/atlassian/` library:

| Need | Addition | Used by |
|---|---|---|
| Status history | `--changelog` → `status_history.csv` (`expand=changelog`; Cloud fallback `changelog/bulkfetch`) | #1 |
| Issue links | `issuelinks` field → `links` column | #1, #4 |
| Boards / sprints | `list_sprints(board, state)` on `/rest/agile/1.0` (same on Cloud and DC) | #1 |
| Create epic / child | `create_issue`, `create_child` behind `--dry-run` (default) / `--apply`; Cloud `parent`, DC Epic Link custom field | #4 (after human approval of the JSON plan) |
| Read Confluence page | `confluence_page.py`: Cloud `/wiki/api/v2/pages/{id}`, DC `/rest/api/content/{id}?expand=body.storage` | #4 |

Secrets stay env-only (`JIRA_*`, new `CONFLUENCE_*`), from a git-ignored `.env`, direnv, `op run` or the keychain; a read-only account for #1. `jira-cli` and `acli` are optional conveniences in the post-install catalogue, never requirements.

Side finding: Bitbucket Cloud removed app passwords on 2026-07-28, so the `BITBUCKET_APP_PASSWORD` fallback in `scripts/decks/sources/bitbucket_prs.py` is dead for Cloud and should move to API tokens. Unverified until a live call: `expand=changelog` on Cloud `/search/jql`.

**Accepted list** (#3 is deferred, see §5.1):

| # | Skill | Source | Seats (bundle → optional) | FRQ coverage | Kit-side changes |
|---|---|---|---|---|---|
| 1 | `jira-sprint-dashboard` | atlassian/atlassian-mcp-server @eb9a5956a7ac (Apache-2.0) | SM → EM, PO, RTE | SM01 flow health; most of SM05, SM06 | Remove per-assignee "owner load" (keep unassigned/inactive buckets); strip Cursor Canvas sections; Jira access via CLI path (see §5.0) until MCP is approved |
| 2 | `deliver-acceptance-criteria` | product-on-purpose/pm-skills @1cef1a9eae10 (Apache-2.0) | PO → QA, PM, Dev | PO02 AC quality (via added review mode); feeds PO04/QA traceability | Add review mode returning FRQ verdict `Ready / Ready with conditions / Not ready` without rewriting; drop cross-refs to unshipped siblings; keep licence header; mark generated AC as draft for PO approval |
| 4 | `spec-to-backlog` | atlassian/atlassian-mcp-server @eb9a5956a7ac (Apache-2.0) | PM, PO → SM, RTE | PM02 feature-to-story alignment; PO05 refinement prep; cross-role documentation sync | Explicit per-batch human approval before any Jira write; approving seat recorded on each ticket; AC section delegates to #2; Jira/Confluence access via CLI path (see §5.0) |
| 5 | `docs-sync-audit` | github/awesome-copilot @f32d7c320dea (MIT) | all seats | Cross-role "Documentation synchronization" row (no FRQ skill); supports PO08 DoD evidence, PM10 release scope, PO04 doc-update link | One-time review of bundled `docs_drift.py` (21 KB) before vendoring. Adapt to the FRQ toolchain: Maven (`pom.xml`, profiles, properties) and Jenkins (`Jenkinsfile` stages, params, env) as sources of truth; Go and React commands; Confluence pages as docs (read via §5.0 CLI); Jama requirements and Bitbucket PRs as scope input instead of GitHub. Remove GitHub-specific assumptions |
| 6 | `drawio` (Copilot variant) | jgraph/drawio-mcp `plugins/copilot/skills/drawio` @1da785068fde (Apache-2.0); no MCP used | all seats | Diagrams for every role: story flows (PO), dependency maps (PM03/PM07, SM04), PI/ART boards (RTE), C4/sequence (Arch, Dev), test/state flows and Jama→test traceability picture (QA), Jenkins pipelines (EM) | Bundle `xml-reference.md` and `mermaid-reference.md` locally (no runtime fetch); disable `url` mode (no app.diagrams.net); write to `docs/diagrams/`; draw.io desktop CLI optional in the catalogue (Mermaid conversion and export only); edit via VS Code Draw.io Integration / IntelliJ Diagrams.net plugin; replaces the stale local May copy; uml/archimate/bpmn/mindmap stay optional |
| 7 | `playwright-cli` | microsoft/playwright-cli @83368cb3bfc0 (Apache-2.0); CLI, no MCP | QA → Dev, PO (React frontends only) | QA end of PO04 traceability (AC from #2 → executable e2e test → evidence); PO08 DoD evidence | `heal` only proposes diffs, never relaxes an assertion without QA approval, spec changes go back to PO; tests tagged with Jama requirement ID + Jira key; project-local devDependency (no global npm); browser binaries via internal mirror or pre-provisioned VM image; synthetic test data only |
| 8 | Schemathesis CLI + kit-built skill (~60 lines) | schemathesis/schemathesis (MIT); no skills.sh skill of note | QA, Dev → EM, Arch | API robustness from the OpenAPI spec (springdoc `/v3/api-docs`, Go specs) with no AI-written test code; JUnit for Jenkins | `uv tool install` (user space, via proxy); targets only human-named environments, never shared/prod without approval; findings → evidence or approval-gated Jira defect drafts (#4 path); enabled when a project publishes OpenAPI |
| 9 | Evidence correlator (kit-built) | extends `scripts/decks` snapshot schema v1 | SM, PO → PM, RTE, QA, EM | SM02 progress evidence (`Consistent / Inconsistent / Insufficient evidence`), PO04 traceability (Jama end), PO08 DoD evidence, PM12 ART view | New read-only sources: Jama (OAuth client credentials; items, relationships, test runs) and Jenkins (JSON API, JUnit, read-only user); Bitbucket source moves from app passwords to API tokens; join on Jira keys in branches, PR titles, commits; team-level only, every link cited, never sets status; `jk`/`bkt` are optional human CLIs in the catalogue with read verbs only |

### 5.1 Deferred

**Next iteration (week of 2026-10-12, after this version is tested):** the FRQ skill schema and starter skills (4d-4), any new FRQ role catalogues, the other team's harness (built over months alongside the client's staff), the security pack (semgrep CE, gitleaks or betterleaks, syft + grype; pinned and checksummed), and API testing beyond Schemathesis (Hurl for hand-written API tests, Pact for contract testing, which needs a broker).

| Candidate | Why deferred | Revisit when |
|---|---|---|
| Superpowers plugin (official marketplace, 6.4.x, enabled per seat for Dev/Arch/QA/EM) | Unclear whether it respects the human-validates-everything rule: executing-plans, subagent-driven-development and finishing-a-development-branch run autonomously | The user asks what more can be done; bring an assessment of which of its skills keep a human gate |

### 5.2 Considered and not recommended

| Candidate | Reason |
|---|---|
| atlassian `generate-status-report` | Per-assignee bottleneck ranking, per-person standup format and RAG verdicts conflict with FRQ SM02/SM05; overlaps #1 |
| product-on-purpose `develop-adr` | Architecture-only; duplicates the kit's `adr-conventions` rule and `record-decision.sh` |
| anthropics `risk-assessment` | 40 lines; sets risk status itself, which FRQ SM11 forbids; kit should write its own risk intake |

## 6. Implementation order (proposed)

Each phase gets its own implementation plan (superpowers `writing-plans` format, as for earlier roadmap phases) and is built only after that plan is approved.

| Phase | Scope | Depends on |
|---|---|---|
| 0. Foundations | Finish and merge `feat/brownfield-installer`. Update its Copilot rows (hooks supported; add Copilot Chat). Add the harness generator with drift gate (4d-1). Add semver, `CHANGELOG.md` and kit version recording (4d-2, first part) | — |
| 1. Seat model and onboarding | `seat-profiles.json` v2, validator and tests. 8 seats: PO/PM split, SM, RTE under `--framework safe`, EM playbook edit. `seats.py` parser. Multi-seat `USER.md` (4a). Re-run, state file and `doctor` (4b). Scripted fallback wizard. VM prep steps. Cartograph install/build step with opt-in wiki and usage rule (§4.0) | 0 |
| 2. Governance | Guardrail rule pack (4d-3). Permission allow-lists with layered overrides (4d-5). Env manifest contract with the devcontainer stream (4d-6). Catalogue with `policy.mcp_allowed=false` (4c) | 1 |
| 3. Atlassian and evidence adapters | `scripts/atlassian/`: changelog, links, sprints, create behind `--dry-run`, Confluence read (§5.0). Bitbucket token fix. Jenkins and Jama snapshot sources. Evidence correlator skill (#9) | 0 |
| 4. Vendored skills | #1, #2, #4, #5, #6, #7, #8, each pinned with licence, script review and overlay | 2, 3 |
| 5. Handover docs | `CONTRIBUTING-KIT.md` recipes (4d-2), SPEC.md §7 seat recipe fix, README and skills README | 1–4 |
| Pilot | One existing FRQ repo on an Ubuntu VM with Copilot CLI, following the §4.0 flow end to end; results feed next week's iteration | 1–4 |

**Superseded (2026-10-08, owner decision):** skill #6 `drawio` is no longer a Phase 4 vendored skill; it ships now in the personal-setup core pack, for every role (see the 2026-10-08 personal-setup plan, "Follow-up: core skills").

Next iteration (week of 2026-10-12): the other team's harness, FRQ skill schema and starter skills (4d-4), new FRQ role catalogues, the security pack, Hurl/Pact, and the deferred Superpowers decision.

**Role discovery (idea, 2026-10-07):** `docs/FRQ-Roles/` is the drop folder for role descriptions and JDs. A future mechanism should point the agent at it, detect new or changed roles, and propose how the seat model, playbooks and skills adapt (always as a proposal a human approves). To be designed with `superpowers:brainstorming`, with Codex as an independent second opinion, before any plan is written.
