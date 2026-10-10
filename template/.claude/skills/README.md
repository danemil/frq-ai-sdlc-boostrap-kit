# Bundled Agent Skills

These are **project-level AI skills** that ship with the repo, so every team member gets the same baseline the moment they clone and open the project in an agent — no plugin install required. They are **versioned governance artefacts**: change them in a PR like any other.

This directory is the `.claude/skills/` half of the board's **Roles × Skills × MCP** matrix — each seat has an invokable skill here; its MCP connectors are declared in [`../../.mcp.json`](../../.mcp.json).

## Role-seat contracts

The `playbook-<seat>` skills capture each named seat's **role contract** — what it owns end-to-end, co-owns and with whom, deliberately doesn't touch, and how it works with the other seats and with AI. Invoke one to reason from, act as, or get a seat's perspective (e.g. "act as the Architect", "what's the Product view"), or to settle a "who owns / who decides" boundary question.

| Skill | Seat |
|---|---|
| **playbook-architect** | Architect |
| **playbook-em** | Engineering Manager |
| **playbook-product** | Product (PO/PM) |
| **playbook-dev** | Developer |
| **playbook-qa** | QA |
| **playbook-sm** | Scrum Master / Team Coach (SAFe) |

These are **Architect-owned baselines**; each seat holder may amend their own via PR.

## Tooling skills

| Skill | Use it for |
|---|---|
| **skill-creator** | Create new skills, and improve / evaluate existing ones. Use it to add a team skill or sharpen one's triggering. |
| **drawio** | draw.io diagrams (Mermaid or XML), saved locally; export needs the draw.io desktop app. Upstream Apache-2.0, see its `PROVENANCE.md`. |
| **likec4-dsl** | LikeC4 architecture-as-code models (`.c4`/`.likec4`), saved locally; validation and export need the LikeC4 CLI or VS Code extension. Upstream MIT, see its `PROVENANCE.md`. |
| **visual-explainers** | A self-contained HTML explainer for a concept, flow or tradeoff. |
| **visual-issue** | An issue, ticket or PR description with a compiled Mermaid diagram, for GitHub, Bitbucket or Jira. |
| **connectors** | Read-only facts from Jira, Confluence, Bitbucket Data Center, Jama and Jenkins through the kit's `connectors.py`, each with its link. The person connects in their own terminal (`setup.py connect <name>`); the AI never handles a secret. |
| **frq-brandbook** | The company brand: palette, fonts, logo and writing rules on one screen; new on-brand decks from the slim template (the full 44-layout master when a layout needs it), from an outline or a JSON spec; a stdlib-only brand check of `.pptx`/`.docx`/`.xlsx` files (FAIL/WARN/INFO, fixes only on approval). Its binary assets stay in the kit copy (`.kit-only`). Client-owned brand assets, see its `PROVENANCE.md`. |
| **deceneus** | What to remember from a chat: proposes preferences, notes or a skill, and writes only what is approved. MIT, see its `PROVENANCE.md`. |

Personal setup gives the tooling skills above, except skill-creator, to every role (the `core` pack in `roles/core/role.json`); the process skills go by role.

## Process skills

| Skill | Use it for | Source |
|---|---|---|
| **brainstorming** | Shape an idea into an approved design before building; specs go to `docs/specs/`. | Upstream MIT, see its `PROVENANCE.md` |
| **writing-plans** | A step-by-step implementation plan in `docs/plans/`; a person carries out or reviews each task. | Upstream MIT, see its `PROVENANCE.md` |
| **test-driven-development** | Write the failing test first, then the code that makes it pass. | Upstream MIT, see its `PROVENANCE.md` |
| **systematic-debugging** | Find the root cause of a bug or failing test before proposing a fix. | Upstream MIT, see its `PROVENANCE.md` |
| **verification-before-completion** | Run the checks and show the evidence before saying work is done. | Upstream MIT, see its `PROVENANCE.md` |
| **receiving-code-review** | Check review comments before acting on them; replies are drafted for the person to post. | Upstream MIT, see its `PROVENANCE.md` |

From obra/superpowers v6.4.2, with the kit's changes listed in each `PROVENANCE.md` (none of them commits, pushes or merges on its own). Personal setup gives them by role: Developer all six; QA test-driven-development, systematic-debugging, verification-before-completion; Architect brainstorming, writing-plans, receiving-code-review; Engineering Manager writing-plans.

## Stack skills

| Skill | Use it for | Source and licence |
|---|---|---|
| **java-code-review** | Review Java code: null safety, exceptions, concurrency, performance (Java 17 and 21). | decebals/claude-code-java, MIT |
| **java-junit** | JUnit tests; JUnit version, AssertJ and Mockito read from the POM first. | github/awesome-copilot, MIT |
| **110-java-maven-best-practices** | Improve a `pom.xml`; repositories only through the `settings.xml` mirror. | jabrena/plinth, Apache-2.0 |
| **javafx** | JavaFX desktop UI: FX thread, FXML, bindings, TestFX (headless), packaging. | Written for this kit, MIT |
| **maven-via-artifactory** | Packages only through the company mirror; the versions this repo uses (`scripts/detect_stack.py`). | Written for this kit, MIT |
| **golang-testing** | Go tests for the repo's Go version (read from `go.mod`). | samber/cc-skills-golang, MIT |
| **golang-code-style** | Go code style and clarity. | samber/cc-skills-golang, MIT |
| **golang-lint** | golangci-lint: run, configure, read findings; fixes only after a yes. | samber/cc-skills-golang, MIT |
| **javascript-typescript-jest** | Jest tests for JavaScript and TypeScript. | github/awesome-copilot, MIT |
| **react-testing-library** | React component tests with Testing Library and Jest (Vitest parts removed). | itechmeat/llm-code, MIT |
| **accessibility** | Web accessibility (WCAG 2.2) checks and fixes; no MCP, no downloads. | addyosmani/web-quality-skills, MIT |
| **sonarqube-findings** | Understand and fix SonarQube findings from a report the person pastes; read-only. | Written for this kit, MIT |
| **blackduck-findings** | Understand and fix Black Duck findings from a report the person pastes; read-only. | Written for this kit, MIT |

These are **library skills**: no role pack lists them. Personal setup suggests them from the repo's files and the person's roles (`setup.py recommend`, rules in `roles/recommend.json`), or the person picks them ("show me the other skills"). Each `PROVENANCE.md` lists the upstream commit and every local change.

## Conformity to agentskills.io

Every `SKILL.md` is validated against the [agentskills.io](https://agentskills.io/specification) standard by [`../../scripts/validate-skills.py`](../../scripts/validate-skills.py):

- **Locally** via [`../../.pre-commit-config.yaml`](../../.pre-commit-config.yaml) — runs on every commit touching a `SKILL.md`.
- **Centrally** via [`../../.github/workflows/ai-governance.yml`](../../.github/workflows/ai-governance.yml) as the enforced merge gate.

Run it anytime: `python3 scripts/validate-skills.py`.

## Two kinds of skill, two homes

- **Invokable** skills — here in `.claude/skills/<name>/SKILL.md`, auto-discovered and triggered by the agent.
- **Read-on-demand** MCP task playbooks — under [`../../docs/ai-context/skills/<role>/`](../../docs/ai-context/skills/), reference docs the agent reads when relevant (*how we run this project* over the connectors), not auto-invoked.

See [`../../docs/ai-context/README.md`](../../docs/ai-context/README.md) for the full AI-context contract.
