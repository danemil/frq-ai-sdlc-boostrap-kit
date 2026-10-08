# Superpowers process skills — design

**Status:** approved 2026-10-08 (kit owner: the split in §2, the role table in §3, upstream names kept; the plan's open questions answered in §6). Plan: [superpowers pack plan](./2026-10-08-superpowers-pack-plan.md). Target release: **0.7.0**.
**Resolves:** the deferred Superpowers decision in [onboarding, roles & skills design](./2026-10-07-onboarding-roles-and-skills-design.md) §5 "Deferred".
**Related:** [personal setup design](./2026-10-08-personal-setup-design.md) (role packs, placement, `change --add-skill/--drop-skill`).

## 1. Problem

The role playbooks refer to brainstorming, plans, test-driven development, debugging and code review, but the kit ships none of these process skills. Superpowers (obra/superpowers) is the most-used set of them. It was deferred on 2026-10-07 because some of its skills run work autonomously, which conflicts with the kit rule that **a human validates 100% of AI code and decisions**.

## 2. Decisions

| # | Question | Decision |
|---|---|---|
| 1 | Source | **obra/superpowers v6.4.2**, commit `8ca22dba9a94f28898bbce59f2537ff4d87c747d` (2026-09-25; annotated tag object `668b16d4d8d4d603fd257567684fbbffccbf2022`), MIT. |
| 2 | Plugin or vendored skills? | **Vendored skills**, pinned, the same way as `drawio` and `likec4-dsl`: `PROVENANCE.md`, the upstream `LICENSE`, every local change listed. Not a plugin: plugins are Claude Code only, and the client uses GitHub Copilot. |
| 3 | Names | **Upstream names kept**; setup prefixes them as usual (`ai-sdlc-brainstorming`, …). |
| 4 | Shipped (6) | `brainstorming`, `writing-plans`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `receiving-code-review`. |
| 5 | Not shipped | `subagent-driven-development` (subagents implement, commit and review without a person in between), `executing-plans` (batch execution), `finishing-a-development-branch` (offers a local merge that skips review), `using-superpowers` ("you MUST use a skill at 1% chance"; too pushy, and Copilot discovers skills itself), `requesting-code-review` and `dispatching-parallel-agents` (need subagents; Copilot support not reliable yet), `using-git-worktrees` (later, power users), `writing-skills` (the kit has `skill-creator`), `diagnosing-superpowers` (about the plugin itself). |
| 6 | Pack | A **role-level** pack, not the core pack (§3). Anyone can add or drop a skill with "change my preferences" (`--add-skill` / `--drop-skill`). |

### 2.1 Local modifications (all shipped skills)

- **No autonomous git.** The AI never commits, pushes or merges on its own. Where upstream says "commit", the kit copy says: follow the person's git-comfort setting and ask before each commit.
- **Human gates stay** exactly as upstream wrote them (brainstorming's approval steps, TDD's red/green checks).
- **No cross-references to skills not shipped.** Links to `subagent-driven-development`, `executing-plans`, `finishing-a-development-branch`, `using-superpowers`, `requesting-code-review` are removed or replaced by "a person carries out or reviews each task".

### 2.2 Per-skill changes

| Skill | Bundled | Change |
|---|---|---|
| `brainstorming` | `SKILL.md` | Leave out the visual companion (`visual-companion.md`, `scripts/`: a local Node server) and `spec-document-reviewer-prompt.md` (written for a subagent; the v6.4.2 `SKILL.md` does not link it). Specs go to `docs/specs/`. The description is softened: "You MUST use this before any creative work" becomes "Use before any creative work" (the rest of the trigger text stays). |
| `writing-plans` | `SKILL.md` | Plans go to `docs/plans/`. The "REQUIRED SUB-SKILL: subagent-driven-development / executing-plans" header becomes: a person carries out each task, or reviews it before the next one starts. |
| `test-driven-development` | `SKILL.md`, `writing-good-tests.md` | Only the commit wording (§2.1). |
| `systematic-debugging` | `SKILL.md`, `root-cause-tracing.md`, `defense-in-depth.md`, `condition-based-waiting.md` | Leave out `find-polluter.sh` (an npm-specific script), the `.ts` example, `CREATION-LOG.md` and the `test-*.md` pressure tests (upstream test material). |
| `verification-before-completion` | `SKILL.md` | Only the commit wording (§2.1). |
| `receiving-code-review` | `SKILL.md` | None expected beyond §2.1; reviews may come from Bitbucket PRs. |

### 2.3 Role playbooks

The playbooks name skills the kit does not ship (`code-review`) and use skill names without the `ai-sdlc-` prefix that setup gives them (`brainstorming`, `writing-plans`, `test-driven-development`, `systematic-debugging`, …). This release fixes them: every skill a playbook names is one the kit ships, under its placed `ai-sdlc-` name, with "(if you have it)" where a person may not have it.

## 3. Who gets what

| Role | Skills |
|---|---|
| Developer | all 6 |
| QA | `test-driven-development`, `systematic-debugging`, `verification-before-completion` |
| Architect | `brainstorming`, `writing-plans`, `receiving-code-review` |
| Engineering Manager | `writing-plans` |
| PO, PM, SM | none by default |

A person with several roles gets the union. These go into each role's `role.json` `skills` list.

## 4. Testing

- Placement: each role gets exactly its skills; the union for several roles; `--drop-skill` / `--add-skill` work for these names.
- Content: no shipped file mentions a skill that is not shipped; no shipped `SKILL.md` tells the AI to commit, push or merge without asking; brainstorming's description does not say "MUST".
- Playbooks: every skill name a playbook mentions is a skill the kit ships, written as its placed `ai-sdlc-` name.
- `validate_packs.py`, `template/scripts/validate-skills.py`, the personal tests on Python 3.13 and `/usr/bin/python3` 3.9.6, and the personal-e2e CI job.
- Manual: the owner tries the skills in Copilot on the VM before the PR is merged.

## 5. Out of scope

- The skills not shipped (§2 #5). They can be revisited when Copilot's subagent support is reliable and a human gate can be kept between tasks.
- Automatic updates from upstream: updating is manual (`PROVENANCE.md` → "Updating").

## 6. Decisions (owner, 2026-10-08)

Answers to the plan's open questions.

0. **Pin:** commit `8ca22dba9a94f28898bbce59f2537ff4d87c747d`, annotated tag object `668b16d4d8d4d603fd257567684fbbffccbf2022` (v6.4.2). §2 row 1 records both.
1. **`spec-document-reviewer-prompt.md` is dropped.** brainstorming bundles only `SKILL.md`; its `PROVENANCE.md` lists the prompt as left out (§2.2).
2. **brainstorming's description is softened:** "You MUST use this before any creative work" → "Use before any creative work"; the rest of the trigger text stays. Recorded as a local modification.
3. **The role playbooks are fixed in this release** (§2.3), with a test.
4. **Branch flow:** feature branch → `release/0.7.0` → one pull request, as for 0.6.0.
5. **Manual try first:** the owner tries the skills by hand in Copilot on the VM before the pull request is merged; the pull request stays open after CI until then.
