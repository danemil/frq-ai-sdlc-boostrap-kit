# Provenance: verification-before-completion

| | |
|---|---|
| Upstream repo | https://github.com/obra/superpowers |
| Path | `skills/verification-before-completion` |
| Tag | `v6.4.2` (annotated tag object `668b16d4d8d4d603fd257567684fbbffccbf2022`) |
| Commit | `8ca22dba9a94f28898bbce59f2537ff4d87c747d` (2026-09-25) |
| Taken | 2026-10-08 |
| Licence | MIT; the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit | Changed? |
|---|---|---|
| `SKILL.md` | `skills/verification-before-completion/SKILL.md` | Yes, see below |
| `LICENSE` | `LICENSE` | No |

Upstream's folder holds only `SKILL.md`, so nothing was left out. Upstream has no `NOTICE` file. The skill bundles no executable scripts and fetches nothing at runtime.

## Local modifications

One new section in `SKILL.md`, "This kit's copy", placed before "The Iron Law", and trigger phrases added to the description. Nothing else in upstream's text is changed.

- **Git.** The AI never commits, pushes or merges on its own; it follows the person's git-comfort setting and asks before each commit.

Upstream lines that name commits, pushes or PRs only as moments to verify are kept as they are (reviewed 2026-10-08): the description ("before committing or creating PRs"), the red flag "About to commit/push/PR without verification", and "Committing, PR creation, task completion".

- **Description: trigger phrases added** (E2E run of 2026-10-09). Upstream's sentence is kept and followed by: Also when you are about to say "fixed", "done", "tests pass" or "ready to merge".

The frontmatter `name` is unchanged; setup prefixes the name to `ai-sdlc-verification-before-completion` when it places the skill.

## Updating

Take `SKILL.md` and `LICENSE` from a newer upstream commit, re-apply the section above, check any new git wording (commit, push, merge) against the kit's rule that the AI asks first, and update the tag, commit and date here.
