# Provenance: writing-plans

| | |
|---|---|
| Upstream repo | https://github.com/obra/superpowers |
| Path | `skills/writing-plans` |
| Tag | `v6.4.2` (tag object `668b16d4d8d4…`) |
| Commit | `8ca22dba9a94f28898bbce59f2537ff4d87c747d` (2026-09-25) |
| Taken | 2026-10-08 |
| Licence | MIT; the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit | Changed? |
|---|---|---|
| `SKILL.md` | `skills/writing-plans/SKILL.md` | Yes, see below |
| `LICENSE` | `LICENSE` | No |

Upstream's `skills/writing-plans` folder holds only `SKILL.md`, so nothing was left out. The skill bundles no executable scripts.

## Local modifications

All in `SKILL.md`. The frontmatter (`name`, `description`) is unchanged; setup prefixes the name to `ai-sdlc-writing-plans` when it places the skill.

- **Overview.** "Frequent commits." became "Small, frequent commits; ask the person before each one."
- **New section "This kit's copy"** in place of upstream's isolated-workspace context line (which named an upstream skill the kit does not ship) and its "Save plans to: `docs/superpowers/plans/…`" default: the kit's git rule (never commit, push or merge on your own; follow the person's git-comfort setting and ask before each commit), plans go to `docs/plans/YYYY-MM-DD-<feature-name>.md` or where the person asks, and a person carries out each task or reviews it before the next one starts (the kit has no skill that runs a plan on its own).
- **Step Granularity.** The example step "Commit" became "Ask the person to review, then commit if they agree".
- **Plan Document Header.** The "For agentic workers: REQUIRED SUB-SKILL …" line, which named two upstream skills the kit does not ship, became a line for the person carrying out the plan: one task at a time, each carried out or reviewed by a person.
- **Task Structure.** "Step 5: Commit" became "Step 5: Ask the person to review the diff; commit only if they agree". The example `git add` / `git commit -m` lines stay as they are.
- **Hand-off.** Upstream's "Execution Handoff" (the choice between subagent-driven and native execution and the two required sub-skills) became a short "Hand-off": link the saved plan, ask the person to review it, and wait.

## Updating

Take `SKILL.md` and `LICENSE` from a newer upstream tag, re-apply the modifications above, check that no line names an upstream skill the kit does not ship or tells the AI to commit without asking, and update the tag, commit and date here.
