# Provenance: test-driven-development

| | |
|---|---|
| Upstream repo | https://github.com/obra/superpowers |
| Path | `skills/test-driven-development` |
| Tag | `v6.4.2` (tag object `668b16d4d8d4…`) |
| Commit | `8ca22dba9a94f28898bbce59f2537ff4d87c747d` (2026-09-25) |
| Taken | 2026-10-08 |
| Licence | MIT; the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit | Changed? |
|---|---|---|
| `SKILL.md` | `skills/test-driven-development/SKILL.md` | Yes, see below |
| `writing-good-tests.md` | `skills/test-driven-development/writing-good-tests.md` | Yes, see below |
| `LICENSE` | `LICENSE` | No |

Upstream's folder holds only these two skill files; nothing is left out. The skill bundles no executable scripts and fetches nothing at runtime.

## Local modifications

- **`SKILL.md`: new section "This kit's copy"**, placed before "## When to Use": the AI never commits, pushes or merges on its own; it follows the person's git-comfort setting and asks before each commit. A second rule there: **Show before you change** (E2E finding, 2026-10-09: a debugging session edited code without showing it): before editing any file, show the proposed diff and wait for a yes; if the AI cannot ask, it stops after proposing; it reports evidence (the test output), never just "Fixed". Upstream never tells the AI to commit; its one git word ("catches bugs before commit", in the rationalizations table) was reviewed and left as it is.
- **`writing-good-tests.md`: removed the reference ` (superpowers:writing-skills)`** after "tested by the consuming agent's behavior", because the kit does not ship `writing-skills` (it has `skill-creator`). The sentence stays.

- **Description: trigger phrases added** (the skill never triggered in the E2E run of 2026-10-09). Upstream's sentence is kept and followed by: and when someone says "write tests first", "test-first", "TDD", "red-green", "a failing test" or "tests for this function".

Nothing else in upstream's text is changed. The frontmatter `name` is unchanged; setup prefixes the name to `ai-sdlc-test-driven-development` when it places the skill. The link from `SKILL.md` to `writing-good-tests.md` stays relative and works in the placed folder.

## Updating

Take `SKILL.md`, `writing-good-tests.md` and `LICENSE` from a newer upstream tag, re-apply the two changes above, check the new text for git instructions (commit, push, merge) and for names of superpowers skills the kit does not ship, run `python3 scripts/personal/tests/test_superpowers.py TestTestDrivenDevelopment`, and update the tag, commit and dates here.
