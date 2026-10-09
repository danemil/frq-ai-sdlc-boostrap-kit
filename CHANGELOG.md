# Changelog

All notable changes to the AI-SDLC Bootstrap Kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions: [SemVer](https://semver.org/).

**Version policy (for maintainers):**
- **MAJOR**: a person must act by hand on upgrade, beyond copying the newer kit folder in and saying "update the kit" (a removed `setup.py` command, a `state.json` change that `update` cannot carry over, a change to the role-pack format).
- **MINOR**: a new or removed role pack, skill or command. Upgrades apply cleanly through "update the kit" (`setup.py update`). While the kit is 0.x, a breaking change also rides a MINOR bump.
- **PATCH**: fixes and wording. "Update the kit" refreshes the placed files; nothing is added or taken away.
- Every PR that changes `roles/`, `scripts/personal/`, `setup.py`, `ONBOARDING.md` or `template/` adds a line under **Unreleased**. A release moves those lines under the new version and bumps `VERSION`.

## [Unreleased]

## [0.8.0] — 2026-10-09
### Added
- `frq-brandbook` skill in the core pack (`ai-sdlc-frq-brandbook`), for every role and any future one: the company brand on one screen (palette with Office and web values, Arial and Roboto, logo and tagline rules, writing rules, the classification footer, the known template conflicts and the value to use). **Create** builds new decks from a bundled 25-layout slim template by layout name (`scripts/new_deck.py` turns a Markdown outline into a deck with python-pptx; the classification is required, never guessed), with tested recipes for on-brand shapes, text boxes, tables and charts; Word, Excel, PDF, HTML, draw.io, LikeC4, Mermaid and e-mail guidance, with customer Word documents starting from the official Word template. **Check** runs `scripts/check_brand.py` (Python 3.9+ standard library only, no install): colours, tints, fonts (including theme fonts), italics, shadows, gradients and outlines (including what shapes inherit from theme styles), 3D, the tagline typed on its own, "Thank you" and "Questions?" slides and a missing classification fail; Title Case, US spelling, contractions, dates and numbers, bold, alignment, dense slides and the internal company abbreviation in internal files are warnings; master and layout findings are INFO; exit 1 on FAIL, 2 on a file it cannot read; `--json`; `.docx` and `.xlsx` checked on the styles they use. It refuses non-UTF-8 parts, entity declarations, oversized and over-compressed parts. Changes are made only after the person confirms them, and the skill says to render or look at the file because the checker reads XML only. Bundles about 1.9 MB of client-owned brand assets (logos converted shape for shape from the template with sharp PNG renders, key visuals, side bars, the gradient, the template without sample slides or personal metadata); photos with unknown rights, portraits, third-party logos and font files are left out. Sources, decisions and the open items for the brand team are in its `PROVENANCE.md`.
- **Company brand by default** (owner decision): when `ai-sdlc-frq-brandbook` is installed, `ai-sdlc-doc-powerpoint`, `-doc-word`, `-doc-excel`, `-doc-pdf`, `ai-sdlc-visual-explainers` and `ai-sdlc-drawio` use the brand for every new file unless the person asks for a plain one (one rule in each; the core instructions say so too).

### Changed
- README: a new section on getting the latest kit from GitHub (clone or release ZIP), redoing the onboarding, and changing roles.
- A placed skill may hold binary files (a `.pptx` template, `.png` and `.jpeg` images): `setup`, `change` and `update` write them byte for byte and record them like any other file, an edited one is kept with the kit's copy next to it as `.kit-new`, and `remove` takes them back. Before, a non-UTF-8 file in a skill folder stopped setup.
- `template/.gitignore` keeps the brand skill's `.pptx` template (generated decks stay ignored), and a test checks that every file of that skill is tracked by git.
- The client-name rule for Copilot guidance has one exception: the `frq-brandbook` folder, and that skill's own name where other guidance points to it. Every other skill and instruction file stays generic (tested).

### Fixed (skills and instructions, from the Copilot E2E runs of 2026-10-09)
- Brand by default failed because Copilot's search skips the git-excluded `.agents/skills/ai-sdlc-*` folders and it concluded the brand skill was missing. Every "Company brand by default" rule (doc-powerpoint, doc-word, doc-excel, doc-pdf, visual-explainers, drawio, and now likec4-dsl) and the core instructions say: if the skill is in your skill list it is installed; read its files by exact path; never decide by glob or search.
- The classification is never guessed: the brand skill asks and waits, or, when it cannot ask, writes the literal `Frequentis [classification to be set]`; the same for Word, Excel, HTML and diagram footers. The outline is a hard stop before building. `new_deck.py` checks the class in `build()` and `set_footer()` too (keyword-only, one of the three classes or the placeholder), so calling its internals cannot skip it; `check_brand.py` reports the placeholder as a WARN (`footer.classification-to-set`).
- `systematic-debugging`, `test-driven-development` and `receiving-code-review` (and the Developer and QA instructions): show the proposed diff and wait for a yes before editing any file; if the AI cannot ask, it stops after proposing; it reports test output, never just "Fixed".
- The session-start check is the first rule of the core instructions, to run before the first reply.
- Trigger phrases: `test-driven-development` ("write tests first", "test-first", "TDD", "red-green", "a failing test", "tests for this function") and `verification-before-completion` ("fixed", "done", "tests pass", "ready to merge"); `deceneus` ("remember that", "from now on", "always do X").
- `brainstorming`: after a spec, the next step offered is always a plan (`ai-sdlc-writing-plans`), never implementation.
- Core instructions: ask before anything that downloads or installs (`npx`, `pip install`); personal notes are hidden from git on purpose and never offered for a commit; "remember that" goes through `ai-sdlc-deceneus`, which shows the text first; a pasted token is never quoted back ("the token you pasted") and the person is told to revoke it; connectors are suggested only for the person's roles.
- `visual-issue`: asks before running mermaid-cli through `npx`, otherwise hands the diagram over marked "not compiled"; writes only the acceptance criteria the person gave, with additions under "Suggested, to confirm".
- `connectors`: "my current sprint" uses `jira search "sprint in openSprints() AND assignee = currentUser()"` (no board id); a role-to-connectors table, and no suggestion to connect a tool outside the person's roles (a Scrum Master was told to connect Bitbucket and Jenkins).
- `frq-brandbook`: fix every FAIL and every font WARN in your own output; the python-docx theme-font snippet and a working openpyxl Arial recipe (`arial_everywhere()`; changing the Normal style alone left every cell in Calibri) come first in the Word and Excel recipes; one fixed render command into `.ai-sdlc/tmp/`; the scripts set `sys.dont_write_bytecode` and say to run them as commands, not import them.
- `check_brand.py`: the Markdown table has a running `#` column and `--json` findings an `id`, so a person can pick fixes by number; the "findings come from the template" note appears only when there are template INFO findings.
- `visual-explainers`: no "Prompt" panel echoing the request on a page unless the person asks for one.
- Core instructions: "do the onboarding" always goes to `ONBOARDING.md`, also when the kit is already set up (Copilot answered "already complete"); German replies use "Sie" throughout unless the person asks for "du", and every language reads naturally, not word for word.
- `connectors`: `disconnect` is run first without `--yes` (it only shows what it would remove), and with `--yes` only after the person says yes.

## [0.7.0] — 2026-10-08
### Added
- Six process skills from obra/superpowers v6.4.2 (commit 8ca22dba9a94, MIT), vendored with a `PROVENANCE.md` each, given by role: `ai-sdlc-brainstorming`, `ai-sdlc-writing-plans`, `ai-sdlc-test-driven-development`, `ai-sdlc-systematic-debugging`, `ai-sdlc-verification-before-completion`, `ai-sdlc-receiving-code-review` (Developer all six; QA test-driven-development, systematic-debugging, verification-before-completion; Architect brainstorming, writing-plans, receiving-code-review; Engineering Manager writing-plans). They never commit, push or merge on their own: they follow the person's git-comfort setting and ask before each commit. Specs go to `docs/specs/`, plans to `docs/plans/`. Not taken: the skills that run work without a person in between (see the design). Add or leave one out with "change my preferences"; `update` brings them to existing setups.

## [0.6.0] — 2026-10-08
### Added
- `likec4-dsl` skill in the core pack (`ai-sdlc-likec4-dsl`), for every role: LikeC4 architecture-as-code (`.c4`/`.likec4` files). Upstream likec4/likec4 `skills/likec4-dsl` @4e6ee7afc526, MIT; references bundled, upstream `evals/` not bundled. Models go to `docs/architecture/`; the `likec4` CLI is optional, and Copilot asks before running it through `npx`/`bunx`/`pnpm dlx` the first time.
- `setup.py connect --suggested`, run by the person in their own terminal: the connectors their roles usually use, one at a time, leaving out the ones already connected (`y` connects with the same questions as `connect <name>`, `s` skips it, `a` skips all the rest; Enter skips), then any other tool by name. Skips are remembered in `state.json` (`skipped_connectors`), so the setup summary marks them "(skipped)" and stops suggesting them, and `connections` shows them as skipped; `connect <name>` clears that tool's skip, `update` drops skips for connectors the kit no longer has, and older state files load unchanged. Without a terminal it asks nothing and changes nothing.
- `ONBOARDING.md`: after the close, Copilot offers once to connect the person's tools with `connect --suggested` (in their own terminal); "not now" ends it. The `ai-sdlc-connectors` skill suggests `connect --suggested` and never runs it.

### Fixed
- `update` and `setup` check that a kit copy is complete before they move it. An incomplete copy (for example one missing `template/.claude/skills/connectors/SKILL.md`) used to be moved into `.ai-sdlc/kit` and then stop with a traceback, leaving a half-updated setup (`check`: `stale-kit`). Now they refuse with "This kit copy is incomplete (missing …). Copy the whole kit folder again (without .git) and retry. Nothing was changed." `update` also prepares every file from the copy before it moves, drops an extra skill the newer kit no longer has, and a half-updated setup is finished by `python3 .ai-sdlc/kit/setup.py update` (or, if the kit folder itself is incomplete, by updating from a whole copy). `setup` replaces a kit folder left by an unfinished setup. An unexpected error prints a plain message (exit code 4) instead of a traceback; `AI_SDLC_DEBUG=1` shows the details.

## [0.5.0] — 2026-10-08
### Added
- **Personal connectors, read-only:** `jira` and `confluence` (Data Center and Cloud), `bitbucket` (Data Center), `jama` (Jama Connect, OAuth client credentials) and `jenkins`. Copilot reads with `python3 .ai-sdlc/kit/connectors.py <name> <command> [--json]`; every item carries its `url`. Only GET requests are sent (plus Jama's token request). Stdlib only; proxies and a company CA bundle are honoured, TLS verification is never switched off.
- `setup.py connect <name> [--test]`, `connections` and `disconnect <name>`. The person runs `connect` in their own terminal (secrets typed hidden; it refuses without a terminal unless every value is in `AI_SDLC_<NAME>_*` variables). Logins are saved per user in `~/.config/ai-sdlc/connectors/` (0700/0600), outside every repo; `remove` never touches them, and no command prints a secret.
- `connectors` skill in the core pack (`ai-sdlc-connectors`): how Copilot checks connections, reads data, cites links, stays read-only, explains errors, and never handles a secret.
- Connector defaults per role in `roles/<id>/role.json` (suggestions only; anyone can connect any tool). The setup summary names them ("Connectors for your roles: …", marking connected ones).
- `docs/how-to.md`: step-by-step guide (first-time setup, update, connect and use the connectors, change, check, personal notes and skills, remove, troubleshooting).

### Changed
- `ONBOARDING.md` gains "Connect a tool", and its close names the connectors for the person's roles without asking for a login.

### Fixed
- `check` no longer tells a person to delete a kit copy with the **same** version as the installed kit, which they may have copied in to update. It now says: "Another copy of the kit (same version X) is in <folder>. If you copied it in to update, say "update the kit"; otherwise delete it." Newer and older copies keep their messages; the finding id stays `kit-copy:<folder>`.

## [0.4.0] — 2026-10-08
### Changed
- **Team mode is retired.** Nothing from the kit is committed to a shared repo any more. Each person copies the kit folder into their working copy and tells Copilot "do the onboarding"; `setup.py` places their role, language and preference files and hides every one of them from git through `.git/info/exclude`.
- `install.sh`, `scripts/install/`, `template/ci/` and `template/.github/workflows/` stay in the repo as retired, internal code; `install.sh` prints a notice. Kit CI replaces the `adopt-e2e` job with `personal-e2e`.

### Added
- `setup.py` with `setup`, `change`, `update`, `check`, `ack` and `remove`, backed by `scripts/personal/` (stdlib only, Python 3.9+).
- `ONBOARDING.md` at the kit root: the conversation Copilot follows (three questions: name, role(s), language). Afterwards a person can say "change my preferences", "update the kit", "check the kit" or "remove the kit".
- Role packs in `roles/`: core, Product Owner, Product Manager, Scrum Master / Team Coach (SAFe), Developer, QA, Architect and Engineering Manager, with `scripts/personal/validate_packs.py`.
- `playbook-sm`: a SAFe Scrum Master / Team Coach playbook in the skill library, used by the Scrum Master pack.
- Eight skills for every role, in the core pack (each has a `PROVENANCE.md`; leave one out with "change my preferences"):
  - `drawio` (upstream jgraph/drawio-mcp Copilot variant @1da785068fde, Apache-2.0; references bundled, no URL or upload mode, diagrams in `docs/diagrams/`), `visual-explainers` (HTML explainers in `docs/explainers/`), `visual-issue` (issues and PRs with a compiled Mermaid diagram for GitHub, Bitbucket or Jira) and `deceneus` (danemil/deceneus @01de547, MIT; saves only approved preferences, personal notes or personal skills).
  - `doc-word` (.docx), `doc-excel` (.xlsx/.csv), `doc-powerpoint` (.pptx) and `doc-pdf` (.pdf), written from scratch for the kit (MIT), using python-docx, openpyxl, python-pptx and pypdf, installed only with the person's consent into a personal venv at `~/.ai-sdlc/venv`.
- A placed skill is its whole folder (`references/`, `assets/`, licence files), each file fingerprinted in `state.json` and removed byte for byte. Its relative links that leave the folder point at the same file inside `.ai-sdlc/kit/`.
- Personal notes (`.github/instructions/ai-sdlc-personal.instructions.md`) and personal skills (`.agents/skills/ai-sdlc-personal-*/`) belong to the person: hidden from git, never reported as unknown by `check`, kept and listed by `remove`. The `personal` pack id and `personal-*` skill names are reserved.
- Warnings with stable ids when the team's own `AGENTS.md`, `.github/copilot-instructions.md`, `.github/instructions/` or skills overlap the kit's files; `ack` silences one until that team file changes.
- A session-start line in the core instructions: Copilot runs `setup.py check --quiet` once and mentions any warning, whatever the rituals setting; `--rituals status` adds a one-line summary of where the work stands.
- Team mode, last changes before it was retired:
  - `install.sh --ci jenkins|github|none` installs only the CI governance gate a project runs (repeatable for both). The choice is recorded in `.ai-sdlc/manifest.json` and kept on re-run; without it, both gates ship as before. Switching removes the old gate's file only while it is unedited. `doctor` shows the choice.
  - The generated `.github/workflows/ai-governance.yml` runs `validate-moments.py` and `validate-seat-profiles.py` when their manifests are installed, as the Jenkinsfile already did.

### Fixed
- Team mode, last fixes before it was retired:
  - The generated `ci/Jenkinsfile.ai-governance` no longer runs `pip install --user`, which PEP 668 refuses on Debian 12+ and Ubuntu 23.04+ agents. It uses the agent's pyyaml when importable, otherwise installs it into a gitignored `.venv-ai-governance/`, and fails with a clear message when `python3-venv` is missing.
  - `--ci jenkins` no longer ships the GitHub-only docs link check (`.github/workflows/docs.yml`, `mlc-config.json`); it now belongs to the `github` gate and still needs the `standard` profile or above. Switching to Jenkins removes it while unedited.
  - The generated `.github/workflows/ai-governance.yml` now runs on `minimal` and `standard` installs: steps for scripts a profile does not ship are skipped. Kit CI's `adopt-e2e` job covers all three profiles and runs the generated GitHub workflow on a fresh clone.

## [0.3.0] — 2026-10-07
### Added
- GitHub Copilot surfaces generated from the canonical sources: `.github/copilot-instructions.md` (AGENTS.md §0 + §3 inlined for IntelliJ), `.github/instructions/*.instructions.md` from `.claude/rules/*`, and `chat.useClaudeHooks` in `.vscode/settings.json`.
- Harness drift gate in pre-commit, GitHub Actions and Jenkins (`ci/Jenkinsfile.ai-governance`).
- `CHANGELOG.md` and the version policy above.

## [0.2.0] — 2026-08-28
### Added
- Brownfield installer (`install.sh`): idempotent adoption into existing repos, install manifest (`.ai-sdlc/manifest.json`) with upgrade states, `--dry-run`, `doctor`, uninstall.
- Data-driven harness adapter table and `scripts/harness/sync.py` (Claude Code, Codex CLI, Copilot CLI, Cursor, Gemini CLI, Windsurf, opencode).
