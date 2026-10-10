# Provenance: golang-lint

| | |
|---|---|
| Upstream repo | https://github.com/samber/cc-skills-golang |
| Path | `skills/golang-lint` |
| Commit | `8e899e20ff0cd4dc524af3993e4c62d8ee8c5717` |
| Taken | 2026-10-10 |
| Licence | MIT ("Copyright (c) 2026 Samuel Berthe"); the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit | Upstream blob | Changed? |
|---|---|---|---|
| `SKILL.md` | `skills/golang-lint/SKILL.md` | `63837c1b06e9` | Yes, see below |
| `assets/golangci.yml` | `skills/golang-lint/assets/.golangci.yml` | `4af14a017269` | Renamed only (setup skips dotfiles); content unchanged |
| `references/linter-reference.md` | `skills/golang-lint/references/linter-reference.md` | `a789d54baf71` | Yes, see below |
| `references/nolint-directives.md` | `skills/golang-lint/references/nolint-directives.md` | `4600c68d7736` | No |
| `LICENSE` | `LICENSE` | `e01f008a1feb` | No |

Not bundled: upstream `skills/golang-lint/evals/evals.json` (blob `868dc5e501a7`; the upstream project's test material for the skill, Copilot does not need it). Upstream has no `NOTICE` file. The skill bundles no executable scripts.

## Local modifications

`SKILL.md`:

- **Frontmatter trimmed** to `name`, `description`, `license` and `metadata` (author, version). Removed: `user-invocable`, `compatibility`, the `openclaw` block (which installed golangci-lint with brew), `allowed-tools` and `paths`. The last sentence of the description (a pointer to the upstream CI skill) is removed, and trigger phrases are added to the one before it ("lint", "run the linter", "fix the lint errors" in a Go repo; Copilot re-test 2026-10-10: a lint request did not load the skill).
- **No multi-agent switches.** The "Orchestration mode" paragraph and the "Parallelizing Legacy Codebase Cleanup" section are removed. Coding mode runs `golangci-lint run` on the changed packages and shows the findings, fixing them only after a yes (upstream: a background agent running `--fix`). Interpret/fix mode no longer suggests parallel agents.
- **No installs.** The "Dependencies" block (`go install …golangci-lint@latest`) is replaced by the kit section.
- **New section "This kit's copy"** before "# Go Linting": the kit's git rule, show-before-you-change rule and company-mirror rule, plus "golangci-lint must already be installed" (never install it; if missing, say so and stop) and "Fixes after a yes" (`--fix`, `fmt`, `migrate`).
- **Every file-changing command waits for a yes**: the Quick Reference `--fix` comment, Development Workflow steps 2 and 3, the Makefile `lint-fix` target (a trailing `# only after a yes`), and copying the recommended config to the repo root.
- **Config path** `./assets/.golangci.yml` becomes `./assets/golangci.yml` (two links).
- **Links to upstream skills the kit does not ship removed**: the CI pointer after the Makefile block and the Cross-References, which keep only `ai-sdlc-golang-code-style` "(if you have it)".

`references/linter-reference.md`: the link to `../assets/.golangci.yml` becomes `../assets/golangci.yml`.

Setup prefixes the name to `ai-sdlc-golang-lint` when it places the skill.

## Updating

Take `SKILL.md`, `assets/.golangci.yml` (saved as `assets/golangci.yml`), both `references/` files and `LICENSE` from a newer upstream commit (still without `evals/`), re-apply the changes above, check every file again for installs, sub-agent instructions, `--fix` without a yes and links to upstream skills, and update the commit, date and blobs here.
