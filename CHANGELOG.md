# Changelog

All notable changes to the AI-SDLC Bootstrap Kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions: [SemVer](https://semver.org/).

**Version policy (for maintainers):**
- **MAJOR**: an adopting repo must act by hand on upgrade (renamed or removed seat, manifest schema change, removed extension point).
- **MINOR**: new role pack, skill, harness, surface or gate. Upgrades apply cleanly through "update the kit" (`setup.py update`). While the kit is 0.x, a breaking change also rides a MINOR bump.
- **PATCH**: fixes and wording, with no change to generated surfaces.
- Every PR that changes `roles/`, `scripts/personal/`, `setup.py`, `ONBOARDING.md` or `template/` adds a line under **Unreleased**. A release moves those lines under the new version and bumps `VERSION`.

## [Unreleased]
### Added
- Four skills for every role, in the core pack: `drawio` (upstream jgraph/drawio-mcp Copilot variant @1da785068fde, Apache-2.0; references bundled, no URL or upload mode, diagrams in `docs/diagrams/`), `visual-explainers` (HTML explainers in `docs/explainers/`), `visual-issue` (issues and PRs with a compiled Mermaid diagram for GitHub, Bitbucket or Jira) and `deceneus` (danemil/deceneus @01de547, MIT; saves only approved preferences, personal notes or personal skills). Each has a `PROVENANCE.md`.
- Document skills in the core pack, written from scratch for the kit (MIT): `doc-word` (.docx), `doc-excel` (.xlsx/.csv), `doc-powerpoint` (.pptx) and `doc-pdf` (.pdf), using python-docx, openpyxl, python-pptx and pypdf, installed only with the person's consent into a personal venv at `~/.ai-sdlc/venv`.
- A placed skill is its whole folder (`references/`, `assets/`, licence files), each file fingerprinted in `state.json` and removed byte for byte.
- Personal notes (`.github/instructions/ai-sdlc-personal.instructions.md`) and personal skills (`.agents/skills/ai-sdlc-personal-*/`) belong to the person: hidden from git, never reported as unknown by `check`, kept and listed by `remove`. The `personal` pack id and `personal-*` skill names are reserved.

## [0.4.0] — <release date>
### Changed
- **Team mode is retired.** Nothing from the kit is committed to a shared repo any more. Each person copies the kit folder into their working copy and tells Copilot "do the onboarding"; `setup.py` places their role, language and preference files and hides every one of them from git through `.git/info/exclude`.
- `install.sh`, `scripts/install/`, `template/ci/` and `template/.github/workflows/` stay in the repo as retired, internal code; `install.sh` prints a notice. Kit CI replaces the `adopt-e2e` job with `personal-e2e`.

### Added
- `setup.py` with `setup`, `change`, `update`, `check`, `ack` and `remove`, backed by `scripts/personal/` (stdlib only, Python 3.9+).
- Role packs in `roles/`: core, Product Owner, Product Manager, Scrum Master / Team Coach (SAFe), Developer, QA, Architect and Engineering Manager, with `scripts/personal/validate_packs.py`.
- `playbook-sm`: a SAFe Scrum Master / Team Coach playbook in the skill library, used by the Scrum Master pack.
- Placed skills' relative links that leave their folder point at the same file inside `.ai-sdlc/kit/`.
- `ONBOARDING.md` at the kit root: the conversation Copilot follows (three questions: name, role(s), language).
- Warnings with stable ids when the team's own `AGENTS.md`, `.github/copilot-instructions.md`, `.github/instructions/` or skills overlap the kit's files; `ack` silences one until that team file changes.
- A session-start line in the core instructions: Copilot runs `setup.py check --quiet` once and mentions any warning, whatever the rituals setting; `--rituals status` adds a one-line summary of where the work stands.

### Team mode, last changes: added (released in 0.4.0, now retired)
- `install.sh --ci jenkins|github|none` installs only the CI governance gate a project runs (repeatable for both). The choice is recorded in `.ai-sdlc/manifest.json` and kept on re-run; without it, both gates ship as before. Switching removes the old gate's file only while it is unedited. `doctor` shows the choice.
- The generated `.github/workflows/ai-governance.yml` runs `validate-moments.py` and `validate-seat-profiles.py` when their manifests are installed, as the Jenkinsfile already did.

### Team mode, last changes: fixed
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
