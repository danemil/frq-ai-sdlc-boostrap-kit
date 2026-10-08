# Provenance: receiving-code-review

| | |
|---|---|
| Upstream repo | https://github.com/obra/superpowers |
| Path | `skills/receiving-code-review` |
| Tag | `v6.4.2` (tag object `668b16d4d8d4…`) |
| Commit | `8ca22dba9a94f28898bbce59f2537ff4d87c747d` (2026-09-25) |
| Taken | 2026-10-08 |
| Licence | MIT; the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit | Changed? |
|---|---|---|
| `SKILL.md` | `skills/receiving-code-review/SKILL.md` | Yes, see below |
| `LICENSE` | `LICENSE` | No |

Not bundled: nothing. Upstream's folder holds only `SKILL.md`. The skill bundles no executable scripts.

## Local modifications

Two edits to `SKILL.md`. The frontmatter (`name`, `description`) is unchanged; setup prefixes the name to `ai-sdlc-receiving-code-review` when it places the skill.

- **New section "This kit's copy"**, placed before "## The Response Pattern": the AI never commits, pushes or merges on its own; it follows the person's git-comfort setting and asks before each commit.
- **"GitHub Thread Replies" became "Replying to Review Comments".** Upstream told the AI to reply to inline review comments itself with a `gh api …/comments/{id}/replies` call. The kit's copy has the AI draft the reply; the person posts it, or the AI posts it only when asked, in the comment's own thread (GitHub or Bitbucket), not as a top-level pull request comment.

The rest of upstream's text is unchanged ("push back" in the review sense is not a git operation).

## Updating

Take `SKILL.md` and `LICENSE` from a newer upstream tag, re-apply the two edits above, re-run `scripts/personal/tests/test_superpowers.py TestReceivingCodeReview`, and update the tag, commit and date here.
