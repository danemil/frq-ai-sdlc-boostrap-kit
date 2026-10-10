# Provenance: systematic-debugging

| | |
|---|---|
| Upstream repo | https://github.com/obra/superpowers |
| Path | `skills/systematic-debugging` |
| Tag | `v6.4.2` (tag object `668b16d4d8d4…`) |
| Commit | `8ca22dba9a94f28898bbce59f2537ff4d87c747d` (2026-09-25) |
| Taken | 2026-10-08 |
| Licence | MIT; the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit | Changed? |
|---|---|---|
| `SKILL.md` | `skills/systematic-debugging/SKILL.md` | Yes, see below |
| `root-cause-tracing.md` | `skills/systematic-debugging/root-cause-tracing.md` | Yes, see below |
| `condition-based-waiting.md` | `skills/systematic-debugging/condition-based-waiting.md` | Yes, see below |
| `defense-in-depth.md` | `skills/systematic-debugging/defense-in-depth.md` | No |
| `LICENSE` | `LICENSE` | No |

Not bundled: upstream `find-polluter.sh` (an npm-specific bisection script), `condition-based-waiting-example.ts`, `CREATION-LOG.md`, `test-academic.md` and `test-pressure-1.md` to `test-pressure-3.md` (the upstream project's test material for the skill). The skill bundles no executable scripts.

## Local modifications

- **Git rule.** `SKILL.md`: a new section "This kit's copy", placed before "The Iron Law": never commit, push or merge on your own; follow the person's git-comfort setting and ask before each commit. A second rule in that section: **Show before you change** (E2E finding, 2026-10-09: a debugging session edited code without showing it): before editing or creating any file (a new test file too, after a later E2E run created one unshown), show the proposed diff or content and wait for a yes; if the AI cannot ask, it stops after proposing; it reports evidence (the test output), never just "Fixed".
- **Test-driven development reference.** `SKILL.md`, Phase 4 step 1: `superpowers:test-driven-development` becomes `ai-sdlc-test-driven-development` (the name setup places), with "(if you have it)", since a person may leave that skill out.
- **Verification reference.** `SKILL.md`, Phase 4 step 3: `superpowers:verification-before-completion` becomes `ai-sdlc-verification-before-completion`, with "(if you have it)".
- **No polluter script.** `root-cause-tracing.md`: the paragraph and code block that call `find-polluter.sh` are replaced by one sentence telling the reader to run the test files one at a time and stop at the first one after which the unwanted file or state appears.
- **No example file.** `condition-based-waiting.md`: the line pointing to `condition-based-waiting-example.ts` (not bundled) is removed.

Reviewed and left as is: the "recent commits" mention in Phase 1 (it asks the AI to look at recent changes, not to commit anything).

- **Description: trigger phrases added** (Copilot re-test 2026-10-10: a bug report did not load the skill). Upstream's sentence is kept and followed by: and when someone says "bug", "freezes", "error", "fails", "could not", "crash" or "exception".

The frontmatter `name` is unchanged; setup prefixes the name to `ai-sdlc-systematic-debugging` when it places the skill.

## Updating

Take the five files above from a newer upstream commit (still without the files listed under "Not bundled"), re-apply the modifications above, check every line that mentions commit, push or merge, and update the tag, commit and date here. `scripts/personal/tests/test_superpowers.py` (`TestSystematicDebugging`) fails until the git rule and the references are back in place.
