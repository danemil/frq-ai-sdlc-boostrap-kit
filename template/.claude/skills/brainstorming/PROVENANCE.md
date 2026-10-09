# Provenance: brainstorming

| | |
|---|---|
| Upstream repo | https://github.com/obra/superpowers |
| Path | `skills/brainstorming` |
| Tag | `v6.4.2` (tag object `668b16d4d8d4…`) |
| Commit | `8ca22dba9a94f28898bbce59f2537ff4d87c747d` (2026-09-25) |
| Taken | 2026-10-08 |
| Licence | MIT; the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit | Changed? |
|---|---|---|
| `SKILL.md` | `skills/brainstorming/SKILL.md` (blob `e3f17885f8d5`) | Yes, see below |
| `LICENSE` | `LICENSE` | No |

Not bundled: upstream `visual-companion.md` and `scripts/` (a browser companion served by a local Node server), and `spec-document-reviewer-prompt.md` (written for a subagent and not linked from `SKILL.md`). The skill bundles no executable scripts.

## Local modifications

All in `SKILL.md`, listed top to bottom:

- **Description softened.** The frontmatter `description` starts "Use before any creative work" instead of "You MUST use this before any creative work"; the rest is unchanged.
- **New section "This kit's copy"** before "Establish Shared Understanding": never commit, push or merge on its own, follow the person's git-comfort setting and ask before each commit; specs go to `docs/specs/`, or where the person asks; after a spec, the next step offered is always a plan with `ai-sdlc-writing-plans`, never implementation, a branch or skipping the plan (E2E finding, 2026-10-09: the AI offered to skip the plan).
- **Hard gate.** The architectural path no longer "selects its execution method" after the plan review; written-spec approval only permits invoking `ai-sdlc-writing-plans`.
- **Three Paths.** The architectural path ends with the `ai-sdlc-writing-plans` skill.
- **Architectural checklist.** The visual-companion step is removed and the steps renumbered 1–8; the design doc is saved to `docs/specs/YYYY-MM-DD-<topic>-design.md` and the AI asks before committing it; the last step invokes the `ai-sdlc-writing-plans` skill.
- **Process flow (dot graph).** Both nodes that invoke the planning skill now name it "ai-sdlc-writing-plans".
- **Terminal states.** The only skill invoked after brainstorming is `ai-sdlc-writing-plans`, never an implementation skill (the named upstream implementation skills are not in this kit).
- **Documentation.** Spec path `docs/superpowers/specs/` becomes `docs/specs/`; the line about the elements-of-style skill (not in this kit) is removed; "Commit the design document to git" becomes "Ask the person before committing the design document".
- **User review gate.** "Spec written and committed to `<path>`." becomes "Spec written to `<path>`."; the rest of the message is unchanged.
- **Implementation.** Invoke the `ai-sdlc-writing-plans` skill (if it is not installed, write the plan together with the person); no other skill.
- **Visual Companion section removed**, since its guide and server are not bundled.

The frontmatter `name` is unchanged; setup prefixes it to `ai-sdlc-brainstorming` when it places the skill. The skill refers to `ai-sdlc-writing-plans` by its placed name.

## Updating

Take `SKILL.md` and `LICENSE` from a newer upstream commit (still without `visual-companion.md`, `scripts/` and `spec-document-reviewer-prompt.md`), re-apply the modifications above, check for new git, skill or visual-companion mentions, run `scripts/personal/tests/test_superpowers.py`, and update the tag, commit and date here.
