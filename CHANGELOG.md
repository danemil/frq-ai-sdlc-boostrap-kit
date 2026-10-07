# Changelog

All notable changes to the AI-SDLC Bootstrap Kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions: [SemVer](https://semver.org/).

**Version policy (for maintainers):**
- **MAJOR**: an adopting repo must act by hand on upgrade (renamed or removed seat, manifest schema change, removed extension point).
- **MINOR**: new seat, skill, harness, surface, catalogue entry or gate. Upgrades apply cleanly through `./install.sh --into <repo>`.
- **PATCH**: fixes and wording, with no change to generated surfaces.
- Every PR that changes `template/` adds a line under **Unreleased**. A release moves those lines under the new version and bumps `VERSION`.

## [Unreleased]
### Added
- `install.sh --ci jenkins|github|none` installs only the CI governance gate a project runs (repeatable for both). The choice is recorded in `.ai-sdlc/manifest.json` and kept on re-run; without it, both gates ship as before. Switching removes the old gate's file only while it is unedited. `doctor` shows the choice.
- The generated `.github/workflows/ai-governance.yml` runs `validate-moments.py` and `validate-seat-profiles.py` when their manifests are installed, as the Jenkinsfile already did.

### Fixed
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
