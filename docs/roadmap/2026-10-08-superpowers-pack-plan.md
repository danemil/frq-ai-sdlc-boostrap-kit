# Superpowers Process Skills Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task. Tasks 2–7 are independent (one skill folder each): superpowers:dispatching-parallel-agents may run them at the same time, each in its own worktree. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Ship six Superpowers process skills (obra/superpowers v6.4.2, MIT) as vendored, role-level skills with the kit's local rules, and release kit 0.7.0.

**Architecture:** Each skill is a folder in `template/.claude/skills/<name>/` (upstream files, upstream `LICENSE`, a `PROVENANCE.md`), the same way as `drawio` and `likec4-dsl`. Role packs list them in `roles/<id>/role.json`; setup places them as `.agents/skills/ai-sdlc-<name>/`. **No placement code changes:** role-level skills already work (`po` and `pm` share `playbook-product`), `--add-skill` accepts any library skill (`commands._skill` checks `packs.available_skills`), and `--drop-skill` subtracts from the union (`packs.combine`). Only data, tests and docs change.

**Tech Stack:** Markdown skill files; Python 3.9+ stdlib `unittest` for tests; `gh` CLI to fetch upstream.

**Spec:** [`2026-10-08-superpowers-pack-design.md`](./2026-10-08-superpowers-pack-design.md) (approved 2026-10-08; owner decisions on this plan's questions: see "Decisions (owner, 2026-10-08)" at the end, also design §6).

## Global Constraints

- **Upstream pin.** Repo `https://github.com/obra/superpowers`, tag `v6.4.2`, commit **`8ca22dba9a94f28898bbce59f2537ff4d87c747d`** (2026-09-25); `668b16d4d8d4d603fd257567684fbbffccbf2022` is the **annotated tag object** that points to it. Design §2 row 1 records both (decision 0). `PROVENANCE.md` records the commit and names the tag and tag object.
- **Fetch command** (each file, into an empty scratch folder, never into the repo directly):
  `gh api "repos/obra/superpowers/contents/skills/<name>/<file>?ref=8ca22dba9a94f28898bbce59f2537ff4d87c747d" --jq .content | base64 -d > <scratch>/<name>/<file>`. Licence: `contents/LICENSE` (repo root, "Copyright (c) 2025 Jesse Vincent").
- **Line numbers** in this plan are upstream line numbers at that commit. Apply edits bottom-up so numbers stay valid.
- **Upstream names kept** for folders and `name:`; setup prefixes them. **References to another shipped skill use the placed name** (`ai-sdlc-writing-plans`) plus "(if you have it)", because a person can drop any skill.
- **The kit section.** Every shipped `SKILL.md` gets one new section, exactly:

  ```markdown
  ## This kit's copy

  - **Git:** never commit, push or merge on your own. Follow the person's git-comfort setting and ask before each commit.
  ```

  (brainstorming and writing-plans add one or two bullets, given in their tasks).
- **A human validates every commit** (kit rule). Every "Commit" step means: show `git diff --staged --stat` and the test output, **ask the owner**, commit only on yes.
- **Never delete files on your own initiative.** Leave `docs/prompts/sessions/*.md` unstaged.
- **Name screen before every commit:**
  - `git diff --staged | grep -n -i -E "$OTHER"` prints nothing (`$OTHER`: other projects' names, given by the coordinator in the task prompt, never written in the repo);
  - `git diff --staged | grep -n -E '/Users/|~/work/'` prints nothing;
  - "FRQ", "Frequentis", "Mosaix" never in Copilot-facing files: `test_roles.py::test_no_client_names_in_copilot_guidance` already scans every placed file of every library skill (`PROVENANCE.md` included), so it covers the new folders.
- **Two Pythons.** Run suites with `python3` (3.13) and `/usr/bin/python3` (3.9.6). No 3.10+ syntax in tests.
- **zsh:** quote paths (the repo is under `20 Projects/`); commit with `git commit -F - <<'EOF'`; messages end with a blank line and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Run one test class:** `python3 scripts/personal/tests/test_superpowers.py TestBrainstorming` (`unittest.main()` takes class names as arguments).

## Review Focus

1. **A person drops a skill that another one names** (QA drops `test-driven-development`; `systematic-debugging` still points to it). Pinned in Task 5: references say "(if you have it)".
2. **PO adds `brainstorming` alone** (no `writing-plans`). Pinned in Task 2: the hand-over says what to do without it.
3. **A developer on 0.6.0 updates to 0.7.0**: the new role skills must appear through `update`, with no new command. Pinned in Task 8 (`test_update.py`).
4. **A skill left out stays out after update.** Pinned in Task 8, same test.
5. **A new upstream line that mentions commit/push/merge slips in on a later update.** Pinned in Task 1: every git mention must say "ask" or be on the reviewed list, so a new one fails until a person reviews it.

Note: `writing-good-tests.md` says tests that assert text "prove only that the source is the source". Our content checks are **policy guards** on shipped text, not behaviour tests. Behaviour is checked by a manual try in Copilot (Task 10, step 9).

## Files

| File | Task | Change |
|---|---|---|
| `scripts/personal/tests/test_superpowers.py` | 1, 8 | new: content checks per skill; pack check |
| `template/.claude/skills/<6 names>/` | 2–7 | new folders |
| `roles/{dev,qa,architect,em}/role.json` | 8 | add skills |
| `roles/{dev,qa,architect,em}/instructions.md` | 8 | one line naming the skills |
| `scripts/personal/tests/test_roles.py`, `test_change.py`, `test_place.py`, `test_update.py` | 8 | new and adjusted tests |
| `CHANGELOG.md` | 8, 10 | Unreleased lines, then `[0.7.0]` |
| `template/.claude/skills/playbook-*/SKILL.md`, `scripts/personal/tests/test_roles.py` | 9 | playbooks name only shipped skills, by their placed `ai-sdlc-` names (decision 3); test |
| `README.md`, `template/.claude/skills/README.md`, `docs/how-to.md`, `.github/workflows/ci.yml` | 9, 10 | docs; one CI line |
| `VERSION`, `scripts/personal/tests/test_release.py` | 10 | 0.7.0 |

## Branches and order

```
main @f791bb0
 └─ feat/superpowers-pack      Task 0, Task 1                     (sequential)
     ├─ feat/sp-brainstorming   Task 2  ┐
     ├─ feat/sp-writing-plans   Task 3  │
     ├─ feat/sp-tdd             Task 4  │  parallel, one worktree each,
     ├─ feat/sp-debugging       Task 5  │  disjoint folders: no conflicts
     ├─ feat/sp-verification    Task 6  │
     └─ feat/sp-receiving       Task 7  ┘
 └─ feat/superpowers-pack      cherry-pick 2–7, then Task 8, Task 9 (sequential)
     └─ release/0.7.0          Task 10, one PR to main             (sequential)
```

One pull request `release/0.7.0` → `main`, as for 0.6.0 (decision 4). It stays open after CI until the owner has tried the skills in Copilot (decision 5, Task 10 step 9).

---

### Task 0: Branch and record the design (sequential)

**Files:** `docs/roadmap/2026-10-08-superpowers-pack-design.md`, this plan (both untracked in the main checkout today; the originals there are left for the coordinator).

- [ ] **Step 1:** worktree `.claude/worktrees/superpowers-pack` on a new branch `feat/superpowers-pack` from `main` (f791bb0); copy the two docs into it.
- [ ] **Step 2:** apply the owner's decisions (end of this plan) to both docs: design §2 row 1 (pin, already corrected), §2.2 brainstorming row (decisions 1, 2), new §2.3 (decision 3), §4, new §6; this plan's tasks and tests.
- [ ] **Step 3: Commit** the design and this plan only: `docs(roadmap): superpowers pack design and plan`.

### Task 1: Content checks for the six skills (sequential, test first)

**Files:** Create `scripts/personal/tests/test_superpowers.py`.

**Interfaces — Produces:** one test class per skill (`TestBrainstorming`, `TestWritingPlans`, `TestTestDrivenDevelopment`, `TestSystematicDebugging`, `TestVerificationBeforeCompletion`, `TestReceivingCodeReview`), each a `Checks` mixin + `unittest.TestCase` with `skill = "<name>"`. Tasks 2–7 each make one class pass. Constants other tasks use: `FILES`, `GIT_RULE`, `UPSTREAM_COMMIT`, `BRAINSTORMING_DESCRIPTION`.

- [ ] **Step 1: Write the module.** Constants (exact values):

```python
LIB = helpers.KIT / packs.SKILLS_REL
UPSTREAM_COMMIT = "8ca22dba9a94f28898bbce59f2537ff4d87c747d"
COMMON = ["LICENSE", "PROVENANCE.md", "SKILL.md"]
FILES = {
    "brainstorming": COMMON,                  # decision 1: no spec-document-reviewer-prompt.md
    "writing-plans": COMMON,
    "test-driven-development": COMMON + ["writing-good-tests.md"],
    "systematic-debugging": COMMON + ["condition-based-waiting.md", "defense-in-depth.md",
                                      "root-cause-tracing.md"],
    "verification-before-completion": COMMON,
    "receiving-code-review": COMMON,
}
NOT_SHIPPED = re.compile(
    r"subagent-driven-development|executing-plans|finishing-a-development-branch|"
    r"using-superpowers|requesting-code-review|dispatching-parallel-agents|using-git-worktrees|"
    r"writing-skills|diagnosing-superpowers|elements-of-style|superpowers:")
LEFT_OUT = re.compile(r"visual-companion|Visual Companion|scripts/|find-polluter|"
                      r"condition-based-waiting-example|CREATION-LOG|test-pressure|"
                      r"test-academic|docs/superpowers/|spec-document-reviewer")
GIT = re.compile(r"(?i)\bcommit(?:s|ted|ting)?\b|\bmerg(?:e|es|ed|ing)\b|"
                 r"\bpush(?:es|ed|ing)?\b(?!\s+back)")        # "push back" is review talk
GIT_RULE = ("- **Git:** never commit, push or merge on your own. Follow the person's "
            "git-comfort setting and ask before each commit.")
BRAINSTORMING_DESCRIPTION = (     # decision 2: upstream "You MUST use this before …", softened
    'description: "Use before any creative work - creating features, building components, '
    'adding functionality, or modifying behavior. Explores user intent, requirements and '
    'design before implementation."')
REVIEWED = {   # upstream lines with a git word that tell the AI to do nothing; reviewed 2026-10-08
    "brainstorming": ["recent commits"],
    "writing-plans": ['git commit -m "feat: add specific feature"'],
    "test-driven-development": ["catches bugs before commit"],
    "systematic-debugging": ["recent commits"],
    "verification-before-completion": ["before committing or creating PRs",
                                       "About to commit/push/PR without verification",
                                       "Committing, PR creation, task completion"],
    "receiving-code-review": [],
}
```

  `shipped(skill)` yields `(file name, text)` for every file in the folder **except `PROVENANCE.md` and `LICENSE`** (a human-facing record that must name what was left out, and the licence).

  `Checks` tests (each class inherits all):
  - `test_the_folder_holds_exactly_the_planned_files`: sorted relative paths of all files == `sorted(FILES[skill])`.
  - `test_the_name_is_upstream_and_setup_places_it_prefixed`: `SKILL.md` starts with `f"---\nname: {skill}\n"`; `set(place.placed_skill_files(KIT, skill))` == `{f".agents/skills/ai-sdlc-{skill}/{f}" for f in FILES[skill]}`; `place.placed_skill(KIT, skill, missing)` leaves `missing == []`.
  - `test_the_licence_is_upstream_mit`: `LICENSE` starts with `"MIT License"` and contains `"Copyright (c) 2025 Jesse Vincent"`.
  - `test_provenance_pins_upstream_and_lists_each_file`: `PROVENANCE.md` contains `"https://github.com/obra/superpowers"`, `"v6.4.2"`, `UPSTREAM_COMMIT`, `"MIT"`, `"## Local modifications"`, `"## Updating"`, and `` f"`{f}`" `` for every file in `FILES[skill]` except itself.
  - `test_no_file_names_a_skill_the_kit_does_not_ship`: `NOT_SHIPPED.search(text)` is `None` for every shipped file (message: file and match).
  - `test_no_file_points_at_upstream_material_left_out`: same with `LEFT_OUT`.
  - `test_skill_md_has_the_kit_git_rule`: `"## This kit's copy"` and `GIT_RULE` are in `SKILL.md`, the rule after the heading.
  - `test_every_git_mention_asks_first_or_was_reviewed`: every line of every shipped file where `GIT.search(line)` must contain `"ask"` (any case) or one of `REVIEWED[skill]`. Failure message lists `file:line`.

  Per-class extra tests (exact assertions):
  - `TestBrainstorming.test_specs_go_to_docs_specs_and_hand_over_to_ai_sdlc_writing_plans`: `"docs/specs/"` in `SKILL.md`; ``"`ai-sdlc-writing-plans`"`` in `SKILL.md`; `re.findall(r"(?<!ai-sdlc-)writing-plans", skill_md) == []`; `"frontend-design"` and `"mcp-builder"` not in `SKILL.md`.
  - `TestBrainstorming.test_the_description_is_softened_not_must` (decision 2): the third line of `SKILL.md` == `BRAINSTORMING_DESCRIPTION`; `"MUST"` not in it.
  - `TestBrainstorming.test_provenance_records_the_files_left_out_and_the_softer_description` (decisions 1, 2): `PROVENANCE.md` contains `` "`spec-document-reviewer-prompt.md`" ``, `` "`visual-companion.md`" ``, `"You MUST use this before any creative work"` and `"Use before any creative work"`.
  - `TestWritingPlans.test_plans_go_to_docs_plans_and_a_person_gates_each_task`: `"docs/plans/"` in text; `"A person carries out each task, or reviews it before the next one starts"` in text; `"Subagent-driven"` not in text; `"worktree"` not in `text.lower()`.
  - `TestTestDrivenDevelopment.test_the_tests_guide_link_stays_in_the_folder`: placed `SKILL.md` text contains `"](writing-good-tests.md)"`.
  - `TestSystematicDebugging.test_it_names_the_placed_skills_if_you_have_them`: ``"`ai-sdlc-test-driven-development` skill (if you have it)"`` and ``"`ai-sdlc-verification-before-completion` skill (if you have it)"`` in `SKILL.md`.
  - `TestReceivingCodeReview.test_replies_are_posted_by_the_person`: `"gh api"` not in text; `"Bitbucket"` in text.

- [ ] **Step 2: Run, expect FAIL** for all six classes ("folder holds exactly" fails: no folder yet):
  `python3 scripts/personal/tests/test_superpowers.py` → `FAILED (failures=…)`. Every other suite still passes.
- [ ] **Step 3: Commit** (ask first): `test(superpowers): failing tests for the six vendored skills`. CI on this branch is red until Tasks 2–7 land; do not push it alone.

---

### Tasks 2–7: Vendor one skill each (parallel, own worktree)

Same steps for each task; the per-skill edits follow.

**Common steps** (worktree from `feat/superpowers-pack` after Task 1, branch `feat/sp-<short>`):

- [ ] **Step 1: Red.** `python3 scripts/personal/tests/test_superpowers.py Test<Class>` → FAIL.
- [ ] **Step 2: Fetch** the files listed for the skill, and `LICENSE`, into `<scratch>/<name>/` (command in Global Constraints). Check blob SHAs match (first 12 chars, `gh api …/contents/skills/<name>/<file>?ref=… --jq .sha`), listed per task.
- [ ] **Step 3: Copy** them into `template/.claude/skills/<name>/` (only the files in `FILES[<name>]`).
- [ ] **Step 4: Apply the edits** listed for the skill, bottom-up.
- [ ] **Step 5: Write `PROVENANCE.md`**, same shape as `likec4-dsl/PROVENANCE.md`: header table (Upstream repo, Path `skills/<name>`, Tag `v6.4.2` (tag object `668b16d4d8d4…`), Commit `8ca22dba9a94f28898bbce59f2537ff4d87c747d` (2026-09-25), Taken, Licence MIT with the upstream `LICENSE` from the repo root); a Files table (each file, its upstream path, "Changed?"); "Not bundled" (the left-out files, and why); "Local modifications" (one bullet per edit below); "Updating" (take the same files from a newer tag, re-apply the edits, re-run `test_superpowers.py`, update commit and date). No client names.
- [ ] **Step 6: Green.** `python3 scripts/personal/tests/test_superpowers.py Test<Class>` and the same with `/usr/bin/python3` → OK. Also `python3 template/scripts/validate-skills.py template/.claude/skills/<name>` → conforms. Run `python3 scripts/personal/tests/test_roles.py` (client-name scan covers the new folder) → OK.
- [ ] **Step 7: Name screen** (Global Constraints), then **Commit** (ask first): `feat(skills): vendor superpowers <name> @8ca22dba (MIT)`.

#### Task 2: `brainstorming` (parallel)

Files: `SKILL.md` (e3f17885f8d5). Not bundled: `visual-companion.md`, `scripts/` (local Node server), `spec-document-reviewer-prompt.md` (written for a subagent, not linked from `SKILL.md`; decision 1).

`SKILL.md` edits:
- **L268–285** delete the whole "## Visual Companion" section.
- **L265–266** `- Invoke the writing-plans skill to create a detailed implementation plan` / `- Do NOT invoke any other skill. writing-plans is the next step.` → `- Invoke the `ai-sdlc-writing-plans` skill to create a detailed implementation plan (if you do not have it, write the plan together with the person)` / `- Do NOT invoke any other skill. `ai-sdlc-writing-plans` is the next step.`
- **L259** `"Spec written and committed to `<path>`. …"` → `"Spec written to `<path>`. …"` (rest unchanged).
- **L241–244** path `docs/superpowers/specs/` → `docs/specs/`; delete L243 `- Use elements-of-style:writing-clearly-and-concisely skill if available`; L244 `- Commit the design document to git` → `- Ask the person before committing the design document`.
- **L184–186** `the ONLY skill you invoke after brainstorming is writing-plans — never frontend-design, mcp-builder, or any other implementation skill.` → `the ONLY skill you invoke after brainstorming is `ai-sdlc-writing-plans` — never an implementation skill.`
- **L159, L180** (dot graph) `Invoke writing-plans skill` → `Invoke ai-sdlc-writing-plans skill` (both lines).
- **L138** `invoke writing-plans skill` → `invoke the `ai-sdlc-writing-plans` skill`.
- **L135** `save to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` and commit` → `save to `docs/specs/YYYY-MM-DD-<topic>-design.md`; ask before committing it`.
- **L131** delete the step "Offer the visual companion just-in-time …"; renumber steps 3–9 to 2–8.
- **L84** `then the writing-plans skill.` → `then the `ai-sdlc-writing-plans` skill.`
- **L47–49** `then reviews the written implementation plan and selects its execution method. … only permits invoking writing-plans.` → `then reviews the written implementation plan. … only permits invoking `ai-sdlc-writing-plans`.`
- **Before L14** insert the kit section, with a second bullet: `- **Specs** go to `docs/specs/`, or where the person asks.`
- **L3** (frontmatter `description:`, decision 2) → `BRAINSTORMING_DESCRIPTION` exactly: only "You MUST use this before any creative work" becomes "Use before any creative work"; the rest stays.

`PROVENANCE.md`: "Not bundled" names `visual-companion.md`, `scripts/` and `spec-document-reviewer-prompt.md`; "Local modifications" lists the softened description with the upstream and the new wording quoted.

#### Task 3: `writing-plans` (parallel)

Files: `SKILL.md` (4cf0275d88d6).

- **L179–204** replace "## Execution Handoff" (both option texts and the two "REQUIRED SUB-SKILL" lines) with:

  ```markdown
  ## Hand-off

  After saving and self-reviewing the plan, link it for the person to read and ask:

  **"Plan saved to `docs/plans/<filename>.md`. Please review it. Does it capture what you want?"**

  Wait for their review. A person carries out each task, or reviews it before the next one starts.
  ```
- **L132** `- [ ] **Step 5: Commit**` → `- [ ] **Step 5: Ask the person to review the diff; commit only if they agree**` (the `git add` / `git commit -m` lines L134–137 stay: reviewed).
- **L59** the "For agentic workers: REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development … or superpowers:executing-plans …" line → `> **For the person carrying out this plan:** one task at a time. A person carries out each task, or reviews it before the next one starts. Steps use checkbox (`- [ ]`) syntax for tracking.`
- **L50** `- "Commit" - step` → `- "Ask the person to review, then commit if they agree" - step`.
- **L14–17** (the `superpowers:using-git-worktrees` context line and "Save plans to: `docs/superpowers/plans/…`" with its override line) → the kit section, with:
  `- **Plans** go to `docs/plans/YYYY-MM-DD-<feature-name>.md`, or where the person asks.`
  `- **A person carries out each task, or reviews it before the next one starts.** This kit has no skill that runs a plan on its own.`
- **L10** `Frequent commits.` → `Small, frequent commits; ask the person before each one.`

#### Task 4: `test-driven-development` (parallel)

Files: `SKILL.md` (46838cc9e893), `writing-good-tests.md` (d3c4482fd30b).

- `writing-good-tests.md` **L50–51**: delete ` (superpowers:writing-skills)` (the sentence stays).
- `SKILL.md` **before L16** ("## When to Use"): insert the kit section. No other change: upstream never tells the AI to commit (L234 "catches bugs before commit" is reviewed).

#### Task 5: `systematic-debugging` (parallel)

Files: `SKILL.md` (095d194ac041), `root-cause-tracing.md` (0e72e8f9566b), `defense-in-depth.md` (e2483354dc2b), `condition-based-waiting.md` (70994f777c58). Not bundled: `find-polluter.sh` (npm-specific), `condition-based-waiting-example.ts`, `CREATION-LOG.md`, `test-academic.md`, `test-pressure-1..3.md` (upstream test material).

- `condition-based-waiting.md` **L82** delete `See `condition-based-waiting-example.ts` in this directory for …`.
- `root-cause-tracing.md` **L101–107** (the `find-polluter.sh` paragraph, code block and "Runs tests one-by-one…") → `Run the test files one at a time and check after each one whether the unwanted file or state appeared. The first test after which it appears is the polluter.`
- `SKILL.md` **L189** `Use the `superpowers:verification-before-completion` skill before claiming success` → `Use the `ai-sdlc-verification-before-completion` skill (if you have it) before claiming success`.
- `SKILL.md` **L177** `Use the `superpowers:test-driven-development` skill for writing proper failing tests` → `Use the `ai-sdlc-test-driven-development` skill (if you have it) for writing proper failing tests`.
- `SKILL.md` **before L14** ("## The Iron Law"): insert the kit section.
- `defense-in-depth.md`: unchanged.

#### Task 6: `verification-before-completion` (parallel)

Files: `SKILL.md` (7d45333cc4a4).

- **Before L14** ("## The Iron Law"): insert the kit section. Nothing else: L3, L54, L112 name commits only as moments to verify (reviewed).

#### Task 7: `receiving-code-review` (parallel)

Files: `SKILL.md` (950da7b74bf6).

- **L203–205** "## GitHub Thread Replies" + the `gh api …/replies` line → 

  ```markdown
  ## Replying to Review Comments

  Draft the reply. The person posts it, or you post it only when they ask. Reply in the comment's own thread (GitHub or Bitbucket), not as a top-level pull request comment.
  ```
  (Design §2.2 expected no change here; this line made the AI write to GitHub on its own.)
- **Before L14** ("## The Response Pattern"): insert the kit section.

---

### Merge Tasks 2–7 (sequential, coordinator)

- [ ] On `feat/superpowers-pack`: `git cherry-pick` the six commits (disjoint folders, no conflicts).
- [ ] `python3 scripts/personal/tests/test_superpowers.py` → OK, on both Pythons. `python3 template/scripts/validate-skills.py` → `24/24 SKILL.md files conform`.

### Task 8: Wire the skills into the roles (sequential, test first)

**Files:** `roles/{dev,qa,architect,em}/role.json`, `roles/{dev,qa,architect,em}/instructions.md`; tests `test_superpowers.py`, `test_roles.py`, `test_change.py`, `test_place.py`, `test_update.py`; `CHANGELOG.md`.

**Interfaces — Consumes:** `FILES` from `test_superpowers.py`. No code in `scripts/personal/` changes.

- [ ] **Step 1: Write the failing tests.**
  - `test_superpowers.py` new class `TestPack`:
    - `test_exactly_these_six_come_from_superpowers`: `{p.parent.name for p in LIB.glob("*/PROVENANCE.md") if "obra/superpowers" in p.read_text()}` == `set(FILES)`.
    - `test_they_are_role_skills_not_core`: `set(packs.load(KIT)["core"]["skills"]) & set(FILES) == set()`.
  - `test_roles.py`: `EXPECTED` skills become (playbook first, then alphabetical; `role.json` uses this order):
    - `dev`: `["playbook-dev", "brainstorming", "receiving-code-review", "systematic-debugging", "test-driven-development", "verification-before-completion", "writing-plans"]`
    - `qa`: `["playbook-qa", "systematic-debugging", "test-driven-development", "verification-before-completion"]`
    - `architect`: `["playbook-architect", "brainstorming", "receiving-code-review", "writing-plans"]`
    - `em`: `["playbook-em", "writing-plans"]`
    - po, pm, sm unchanged.
    
    New `test_several_roles_get_the_union_once`: roles `["architect", "em"]` → `combine(...)["skills"]` has `"writing-plans"` exactly once and its intersection with `FILES` is `{"brainstorming", "receiving-code-review", "writing-plans"}`; roles `["qa", "architect"]` → all six. (`test_instructions_name_their_skills` then also requires each role's `instructions.md` to name its new skills.)
  - `test_change.py` (setup is `po`):
    - `test_a_role_skill_can_be_dropped_and_added_back`: `change --roles po,dev` → files under `.agents/skills/ai-sdlc-brainstorming/` are exactly `LICENSE, PROVENANCE.md, SKILL.md`; `change --drop-skill brainstorming` → that folder is gone, `ai-sdlc-writing-plans/SKILL.md` stays, `USER.md` has `- **Skills left out:** brainstorming`; `change --add-skill brainstorming` → `SKILL.md` is back.
    - `test_a_process_skill_outside_the_roles_can_be_added`: `change --add-skill systematic-debugging` → folder files exactly `FILES["systematic-debugging"]` (no `find-polluter.sh`); `USER.md` has `- **Extra skills:** systematic-debugging`; `ai-sdlc-test-driven-development` does not exist.
  - `test_place.py::test_wanted_files_follow_the_choices`: the expected skill set becomes `{f"ai-sdlc-{s}" for s in (*self.packs["dev"]["skills"], *self.packs["po"]["skills"], *self.packs["core"]["skills"])}` (today it hard-codes `playbook-dev`, `playbook-product`).
  - `test_update.py` new `test_a_skill_a_newer_kit_adds_to_a_role_arrives_and_a_left_out_one_stays_out` (own temp repo): an old kit copy with `roles/dev/role.json` skills `["playbook-dev"]`; `setup --roles dev` from it → no `ai-sdlc-writing-plans`; `change --drop-skill brainstorming`; `update` from a current copy with `VERSION` 9.9.9 → `ai-sdlc-writing-plans/SKILL.md` exists, `ai-sdlc-brainstorming` does not.
- [ ] **Step 2: Run, expect FAIL**: `test_roles.py` (skills per role, union), `test_change.py` (folder missing), `test_update.py` (no writing-plans). `TestPack` and the new `test_place.py` expectation already pass: they are guards (the skill set is read from the packs).
- [ ] **Step 3: Implement.**
  - The four `role.json` `skills` lists, exactly as `EXPECTED`.
  - One line in each of the four `instructions.md`, after the first paragraph, e.g. for `qa`: `**Process skills.** Unless they left one out: `ai-sdlc-systematic-debugging`, `ai-sdlc-test-driven-development`, `ai-sdlc-verification-before-completion`. Use the one that fits the work. They never commit for the person.` Same pattern for `dev` (six), `architect` (three), `em` (one). Files stay under 60 lines.
  - `CHANGELOG.md` under `## [Unreleased]` → `### Added`: the line given in Task 10 step 3.
- [ ] **Step 4: Green, both Pythons:**
  `for py in python3 /usr/bin/python3; do for t in scripts/personal/tests/test_*.py; do $py "$t" >/dev/null 2>&1 || echo "FAIL $py $t"; done; done` → prints nothing.
  `python3 scripts/personal/validate_packs.py` → `ok    8 role pack(s) valid; their skills pass validate-skills`.
- [ ] **Step 5: Name screen, Commit** (ask first): `feat(roles): process skills for dev, qa, architect and em`.

### Task 9: Playbooks, docs and CI (sequential, playbooks test first)

**Files:** `template/.claude/skills/playbook-{architect,dev,em,product,qa,sm}/SKILL.md`, `scripts/personal/tests/test_roles.py`, `README.md`, `template/.claude/skills/README.md`, `docs/how-to.md`, `.github/workflows/ci.yml`.

- [ ] **Step 0a: Failing test** (decision 3) in `test_roles.py`, `test_playbooks_name_only_shipped_skills_by_their_placed_names`. Import `FILES` from `test_superpowers`. For every `playbook-*` in `packs.available_skills(KIT)`, take the placed text `place.placed_skill(KIT, pb)[1]` and scan `re.finditer(r"(?<![\w/.-])(ai-sdlc-)?([a-z0-9]+(?:-[a-z0-9]+)+)(?![\w/-])", text)`:
  - with the prefix, the name must be in `packs.available_skills(KIT)` (a skill the kit ships);
  - without it, the name must not be in `set(packs.available_skills(KIT)) | set(packs.UNSUPPORTED_SKILLS) | set(FILES) | {"code-review"}` (an unprefixed or not-shipped skill name).

  Failure message: playbook and the offending names. Run → FAIL. Today (before Tasks 2–7) it reports: architect `playbook-architect`, `skill-creator`; dev `code-review`, `playbook-dev`, `skill-creator`; em `code-review`, `skill-creator`; product `skill-creator`; qa `skill-creator`; sm `playbook-product`, `skill-creator`. After Tasks 2–7 it also reports the unprefixed `brainstorming`, `writing-plans`, `test-driven-development`, `systematic-debugging` (architect, dev, product).
- [ ] **Step 0b: Fix the playbooks**, "Invokable skills" lines (and any other mention): placed names; `code-review` → `ai-sdlc-receiving-code-review` (when review comments come in); the em line's "a tdd / test skill and a code-review skill where present" → `ai-sdlc-writing-plans` (and the other process skills the person has); `skill-creator` → `ai-sdlc-skill-creator` (if you have it: it is not in the core pack); qa names its three process skills. Skills a role does not get by default carry "(if you have it)". Keep each playbook's wording otherwise. Run `test_roles.py` → OK, both Pythons; `validate_packs.py` → ok. Note: team mode (`scripts/install/`) copies `template/.claude/skills/` without the prefix, so there the `ai-sdlc-` names do not match the folders; personal setup is the delivered mode (owner decision 3).

- [ ] **Step 1: `README.md`.** Role table (lines 36–45): Skills column adds the placed names per role (Task 8 lists). After the "Every role also gets ten skills" paragraph, one short paragraph: the six **process skills** (one phrase each), upstream obra/superpowers v6.4.2 (MIT), given by role, never commit/push/merge on their own, specs in `docs/specs/`, plans in `docs/plans/`; add or leave one out with "change my preferences".
- [ ] **Step 2: `template/.claude/skills/README.md`.** Replace the "Generic baseline (optional)" blockquote (line 36) with a "## Process skills" table (6 rows: skill, use it for, "Upstream MIT, see its `PROVENANCE.md`") and one line: which roles get which (design §3). Fix line 34 to: "Personal setup gives the tooling skills above, except skill-creator, to every role (the `core` pack); the process skills go by role."
- [ ] **Step 3: `docs/how-to.md` §5.** Add *"add the brainstorming skill"* to the Copilot examples (line 388). Version and counts wait for Task 10.
- [ ] **Step 4: `ci.yml`, personal-e2e**, after `test -f .agents/skills/ai-sdlc-likec4-dsl/references/cli.md` add:
  `test ! -e .agents/skills/ai-sdlc-brainstorming       # process skills are by role: PO and SM do not get them`
- [ ] **Step 5:** all suites on both Pythons (as Task 8 step 4) → nothing printed. **Name screen, Commit** (ask first), two commits: `fix(playbooks): name only shipped skills, by their placed names` (steps 0a–0b), then `docs: process skills in README, skills README, how-to; CI checks they are role-level`.

### Task 10: Release 0.7.0 (sequential, test first)

**Files:** `scripts/personal/tests/test_release.py`, `VERSION`, `CHANGELOG.md`, `docs/how-to.md`.

- [ ] **Step 1: Failing tests** in `test_release.py`: `test_version` expects `"0.7.0"`; new `test_changelog_0_7_0_has_the_process_skills`: the `[0.7.0]` entry contains `"obra/superpowers v6.4.2"`, `` "`ai-sdlc-brainstorming`" ``, `` "`ai-sdlc-writing-plans`" ``, `` "`ai-sdlc-test-driven-development`" ``, `` "`ai-sdlc-systematic-debugging`" ``, `` "`ai-sdlc-verification-before-completion`" ``, `` "`ai-sdlc-receiving-code-review`" ``, `"never commit, push or merge on their own"`.
- [ ] **Step 2:** `git switch -c release/0.7.0`; run `test_release.py` → FAIL.
- [ ] **Step 3:** `VERSION` → `0.7.0`. `CHANGELOG.md`: move the Unreleased line under `## [0.7.0] — <date>` / `### Added`, text: "Six process skills from obra/superpowers v6.4.2 (commit 8ca22dba9a94, MIT), vendored with a `PROVENANCE.md` each, given by role: `ai-sdlc-brainstorming`, `ai-sdlc-writing-plans`, `ai-sdlc-test-driven-development`, `ai-sdlc-systematic-debugging`, `ai-sdlc-verification-before-completion`, `ai-sdlc-receiving-code-review` (Developer all six; QA test-driven-development, systematic-debugging, verification-before-completion; Architect brainstorming, writing-plans, receiving-code-review; Engineering Manager writing-plans). They never commit, push or merge on their own: they follow the person's git-comfort setting and ask before each commit. Specs go to `docs/specs/`, plans to `docs/plans/`. Not taken: the skills that run work without a person in between (see the design). Add or leave one out with "change my preferences"; `update` brings them to existing setups." Unreleased stays empty.
- [ ] **Step 4: Verify the how-to example by running it** (from the kit root; scratch folder outside the repo):

  ```bash
  D="$(mktemp -d)/demo"; mkdir -p "$D" && cd "$D" && git init -q && echo x > README.md && git add -A && git -c user.name=t -c user.email=t@t commit -qm init
  rsync -a --exclude=/.git --exclude=/.claude "<kit root>/" ai-sdlc-kit/
  python3 ai-sdlc-kit/setup.py setup --protect-only
  python3 .ai-sdlc/kit/setup.py setup --name "Ana" --roles po,qa --lang en
  ```
  Expected: `Set up AI-SDLC 0.7.0 …` and `Wrote 64 file(s)` (51 today + 13: test-driven-development 4, systematic-debugging 6, verification-before-completion 3). Use the **printed** number. Update `docs/how-to.md` line 71 (`0.6.0` → `0.7.0`) and line 73 (count). Lines 139, 406, 432 are older examples: leave them. Also run `change --lang de --git-comfort guided --rituals none --add-skill skill-creator --drop-skill drawio` and confirm line 408–409 still say `Wrote 3` and `Removed 6`.
- [ ] **Step 5: Full verification, both Pythons:** all personal suites (Task 8 step 4), `validate_packs.py`, `python3 template/scripts/validate-skills.py` (24/24). Paste the summary lines in the PR.
- [ ] **Step 6: Name screen on the whole branch:** `git diff main...HEAD | grep -n -i -E "$OTHER"` and `git diff main...HEAD | grep -n -E '/Users/|~/work/'` → nothing; `grep -rn -i -E '\b(frq|frequentis|mosaix)\b' template/.claude/skills/{brainstorming,writing-plans,test-driven-development,systematic-debugging,verification-before-completion,receiving-code-review} roles/*/instructions.md` → nothing.
- [ ] **Step 7: Commit** (ask first): `chore(release): kit 0.7.0 — superpowers process skills by role`.
- [ ] **Step 8: PR** `release/0.7.0` → `main` (ask before push). Body: what ships, what is left out and why, test summary, the owner decisions; ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. CI `ai-governance` and both `personal-e2e` legs green. **Do not merge yet** (decision 5).
- [ ] **Step 9 (owner, manual, before merge — decision 5):** in the Copilot VM, set up as `dev` from the `release/0.7.0` copy, ask "let's design a small change" and "fix this failing test". Check: brainstorming is picked up without "MUST" pushing it, asks before writing a spec and never commits; a commit is always asked first. Note the result in the PR. Merge only after this (and with the owner's yes); fixes found here go on `release/0.7.0` first.

---

## Self-review

- Design §2 rows 1–6: Tasks 0, 2–7, 8. §2.1: kit section (all), git checks (Task 1), cross-reference checks (Task 1), human gates untouched. §2.2: Tasks 2–7. §3: Task 8. §4: Tasks 1, 8, 10 (placement, union, add/drop, content, validators, both Pythons, CI). §5: nothing built for it.
- Names used across tasks: `FILES`, `GIT_RULE`, `UPSTREAM_COMMIT`, test class names, `EXPECTED` lists — consistent.

## Design problems found

1. **Pin value.** `668b16d4…` is the v6.4.2 annotated tag object, not a commit. Commit: `8ca22dba9a94f28898bbce59f2537ff4d87c747d`. Same files. Fix: record both (Task 0 step 2, `PROVENANCE.md`).
2. **`receiving-code-review` writes to GitHub.** L203–205 tells the AI to reply through `gh api`. The design expected no change. Fix: the person posts replies, GitHub or Bitbucket (Task 7).
3. **`spec-document-reviewer-prompt.md`** is not linked from the v6.4.2 `SKILL.md` and is written for a subagent. Resolved: not shipped (decision 1).
4. **"Only the commit wording"** for TDD and verification: upstream never tells the AI to commit there. The change is just the uniform kit section.
5. **Cross-references.** Placed names are prefixed and any skill can be dropped. Fix: `ai-sdlc-<name>` plus "(if you have it)".
6. **Role instructions must name role skills** (`test_instructions_name_their_skills`). The design does not say so; Task 8 adds one line per role.
7. **No engine problem.** Role-level non-core skills, a skill in several roles, and `--add-skill` for a skill outside the person's roles all work today. Only `test_place.py` hard-codes the dev skill set.

## Decisions (owner, 2026-10-08)

0. **Pin:** commit `8ca22dba9a94f28898bbce59f2537ff4d87c747d`, tag object `668b16d4d8d4d603fd257567684fbbffccbf2022` (v6.4.2). Design §2 row 1 records both; `PROVENANCE.md` too.
1. **Drop `spec-document-reviewer-prompt.md`.** brainstorming bundles only `SKILL.md` (plus `LICENSE`, `PROVENANCE.md`); `PROVENANCE.md` records the prompt as left out. Tests: `FILES`, `LEFT_OUT`, `TestBrainstorming` (Task 1), `test_change.py` (Task 8).
2. **Soften brainstorming's description:** "You MUST use this before any creative work" → "Use before any creative work"; the rest of the trigger text stays. A local modification in `PROVENANCE.md`. Test: `TestBrainstorming.test_the_description_is_softened_not_must`.
3. **Fix the role playbooks in this release:** no `code-review` (not shipped), skill names with the `ai-sdlc-` prefix. Task 9 steps 0a–0b, test in `test_roles.py`.
4. **Branch flow:** feature branch → `release/0.7.0` → one PR, as in 0.6.0.
5. **Manual Copilot try before merge:** the PR stays open after CI until the owner has tried the skills on the VM (Task 10 step 9).
