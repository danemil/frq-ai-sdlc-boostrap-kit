# Changelog

All notable changes to the AI-SDLC Bootstrap Kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions: [SemVer](https://semver.org/).

**Version policy (for maintainers):**
- **MAJOR**: a person must act by hand on upgrade, beyond copying the newer kit folder in and saying "update the kit" (a removed `setup.py` command, a `state.json` change that `update` cannot carry over, a change to the role-pack format).
- **MINOR**: a new or removed role pack, skill or command. Upgrades apply cleanly through "update the kit" (`setup.py update`). While the kit is 0.x, a breaking change also rides a MINOR bump.
- **PATCH**: fixes and wording. "Update the kit" refreshes the placed files; nothing is added or taken away.
- Every PR that changes `roles/`, `scripts/personal/`, `setup.py`, `ONBOARDING.md` or `template/` adds a line under **Unreleased**. A release moves those lines under the new version and bumps `VERSION`.

## [Unreleased]
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
