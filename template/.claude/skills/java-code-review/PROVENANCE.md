# Provenance: java-code-review

| | |
|---|---|
| Upstream repo | https://github.com/decebals/claude-code-java |
| Path | `skills/java-code-review` |
| Commit | `0d98fe9bd62923e819568ee1e041a1bf320f74d4` (2026-09-06) |
| Folder last changed in | `702770a755fb` (2026-08-28) |
| Taken | 2026-10-10 |
| Licence | MIT, "Copyright (c) 2026 Decebal Suiu"; the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit | Upstream blob | Changed? |
|---|---|---|---|
| `SKILL.md` | `skills/java-code-review/SKILL.md` | `66fe7ee9e1cf` | Yes, see below |
| `LICENSE` | `LICENSE` | `85c2f8765b2a` | No |

Not bundled: upstream `skills/java-code-review/README.md` (blob `c40d509fe31e`): it is for people browsing the upstream repo, and its loading line works in Claude Code only. Upstream has no `NOTICE` file. The skill bundles no scripts.

## Local modifications

One new section of `SKILL.md`, "This kit's copy", placed before "When to Use". Nothing else in upstream's text is changed; the frontmatter (`name`, `description`, `license`) is already trimmed upstream and stays as it is. The two upstream lines that mention merging ("or before merging changes" in the description, "Before merging a PR" under "When to Use") only say when to review, so they stay.

- **Git.** Never commit, push or merge on its own; follow the person's git-comfort setting and ask before each commit.
- **Show before you change.** Show the proposed diff or content and wait for a yes; report evidence, not just "Fixed".
- **Packages only through the company mirror.** No `<repositories>` in a POM, no downloads from the public internet, ask before anything that downloads; load `ai-sdlc-maven-via-artifactory` if it is installed.
- **Review only.** Findings are listed in the skill's output format; code changes only when the person asks, as a diff they approve.
- **Java 17 and 21.** Check the project's release first: pattern matching for `switch`, record patterns and virtual threads need Java 21.

Setup prefixes the name to `ai-sdlc-java-code-review` when it places the skill.

## Updating

Take `SKILL.md` and `LICENSE` from a newer upstream commit (still without `README.md`), re-apply the section above, run `python3 scripts/personal/tests/test_stack_skills.py TestJavaCodeReview`, and update the commit, blobs and date here.
