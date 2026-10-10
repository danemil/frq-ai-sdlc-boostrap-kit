# Provenance: golang-testing

| | |
|---|---|
| Upstream repo | https://github.com/samber/cc-skills-golang |
| Path | `skills/golang-testing` |
| Commit | `8e899e20ff0cd4dc524af3993e4c62d8ee8c5717` |
| Taken | 2026-10-10 |
| Licence | MIT ("Copyright (c) 2026 Samuel Berthe"); the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit | Upstream blob | Changed? |
|---|---|---|---|
| `SKILL.md` | `skills/golang-testing/SKILL.md` | `7c437a850b22` | Yes, see below |
| `references/benchmarks.md` | `skills/golang-testing/references/benchmarks.md` | `5fd29f065b6d` | Yes, see below |
| `references/coverage.md` | `skills/golang-testing/references/coverage.md` | `46618241a898` | Yes, see below |
| `references/examples.md` | `skills/golang-testing/references/examples.md` | `103889b49cab` | No |
| `references/helpers.md` | `skills/golang-testing/references/helpers.md` | `3c0487705d10` | No |
| `references/http-testing.md` | `skills/golang-testing/references/http-testing.md` | `a7ff122f3419` | No |
| `references/integration-testing.md` | `skills/golang-testing/references/integration-testing.md` | `a5d11413e313` | No |
| `references/mocking.md` | `skills/golang-testing/references/mocking.md` | `4c93e4668635` | Yes, see below |
| `LICENSE` | `LICENSE` | `e01f008a1feb` | No |

Not bundled: upstream `skills/golang-testing/evals/evals.json` (blob `9b80e02b7202`; the upstream project's test material for the skill, Copilot does not need it). Upstream has no `NOTICE` file. The skill bundles no executable scripts.

## Local modifications

`SKILL.md`:

- **Frontmatter trimmed** to `name`, `description`, `license` and `metadata` (author, version). Removed: `user-invocable`, `compatibility`, the `openclaw` block (which installed `gotests@latest`), `allowed-tools` and `paths`. The last sentence of the description (pointers to two upstream skills the kit does not ship) is removed, and trigger phrases are added to the one before it ("write a Go test", "add tests", "go test", "table-driven test"; Copilot re-test 2026-10-10: a Go test request did not load the skill).
- **No extended-thinking or multi-agent switches.** The `ultrathink` sentence and the "Orchestration mode" paragraph are removed; Audit mode works through its three concerns one after another instead of in parallel.
- **No generator installs.** Write mode writes table-driven tests and uses `gotests` only if it is already installed; the "Dependencies" block (`go install …gotests@latest`) is replaced by the kit section.
- **"Community default" becomes "Team default"**: a team skill that explicitly supersedes this one takes precedence.
- **New section "This kit's copy"** where the Dependencies block was: the kit's git rule, show-before-you-change rule and company-mirror rule, plus "Go version first" (read `go`/`toolchain` in `go.mod` and use only features that version has) and "No generators installed".
- **Links to upstream skills the kit does not ship removed**: the `golang-benchmark` pointer under Benchmarks; the lint pointer now names `ai-sdlc-golang-lint` "(if you have it)"; Cross-References keeps only that one entry.

`references/mocking.md`: the pointer to the upstream testify skill is removed, and "Install clockwork" (`go get` without a version) becomes: add clockwork only after the person agrees, through the company Go proxy, with a version chosen together, never `@latest`.

`references/coverage.md`: the pointer to the upstream CI skill is removed.

`references/benchmarks.md`: the opening line no longer points to the upstream benchmark skill, and the closing pointer to it is removed.

Setup prefixes the name to `ai-sdlc-golang-testing` when it places the skill.

## Updating

Take `SKILL.md`, the seven `references/` files and `LICENSE` from a newer upstream commit (still without `evals/`), re-apply the changes above, check every file again for installs (`go install`, `@latest`), sub-agent instructions and links to upstream skills, and update the commit, date and blobs here.
