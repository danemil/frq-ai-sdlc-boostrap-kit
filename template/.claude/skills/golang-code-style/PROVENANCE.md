# Provenance: golang-code-style

| | |
|---|---|
| Upstream repo | https://github.com/samber/cc-skills-golang |
| Path | `skills/golang-code-style` |
| Commit | `8e899e20ff0cd4dc524af3993e4c62d8ee8c5717` |
| Taken | 2026-10-10 |
| Licence | MIT ("Copyright (c) 2026 Samuel Berthe"); the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit | Upstream blob | Changed? |
|---|---|---|---|
| `SKILL.md` | `skills/golang-code-style/SKILL.md` | `3e644ade46d9` | Yes, see below |
| `references/details.md` | `skills/golang-code-style/references/details.md` | `1f7dfa82a52f` | Yes, see below |
| `LICENSE` | `LICENSE` | `e01f008a1feb` | No |

Not bundled: upstream `skills/golang-code-style/evals/evals.json` (blob `df03154f257f`; the upstream project's test material for the skill, Copilot does not need it). Upstream has no `NOTICE` file. The skill bundles no executable scripts.

## Local modifications

`SKILL.md`:

- **Frontmatter trimmed** to `name`, `description`, `license` and `metadata` (author, version). Removed: `user-invocable`, `compatibility`, the `openclaw` block, `allowed-tools` and `paths`. In the description, the "Not for naming … doc comments" sentence (pointers to upstream skills) becomes "For linter configuration use `ai-sdlc-golang-lint`."
- **No multi-agent switches.** The "Orchestration mode" paragraph and the "Parallelizing Code Style Reviews" section are removed.
- **"Community default" becomes "Team default"**: a team skill that explicitly supersedes this one takes precedence.
- **New section "This kit's copy"** before "# Go Code Style": the kit's git rule, show-before-you-change rule and company-mirror rule.
- **Links to upstream skills the kit does not ship removed**: from the opening paragraph, Function Design (design patterns), Code Organization (gopls) and Cross-References. "Enforce with Linters" and Cross-References now name `ai-sdlc-golang-lint` "(if you have it)".

`references/details.md`: the two pointers to the upstream structs-interfaces skill (receiver rules) are removed.

Setup prefixes the name to `ai-sdlc-golang-code-style` when it places the skill.

## Updating

Take `SKILL.md`, `references/details.md` and `LICENSE` from a newer upstream commit (still without `evals/`), re-apply the changes above, check both files again for installs, sub-agent instructions and links to upstream skills, and update the commit, date and blobs here.
