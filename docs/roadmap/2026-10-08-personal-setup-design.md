# Personal setup — design

**Status:** approved 2026-10-08 (brainstormed section by section with the kit owner).
**Supersedes:** team mode (committed kit files, `install.sh`, CI gates) from [Phase 0](./2026-10-07-phase-0-foundations-plan.md). That work stays in git history; the parts reused here move into the new helper.
**Related:** [onboarding, roles & skills design](./2026-10-07-onboarding-roles-and-skills-design.md) (seat model, role discovery idea).

## 1. Problem

The audience is mixed: developers, QA, architects, product owners, project managers, scrum masters. Several of them work in the same shared repo, but each wants an AI setup that fits their role and their own way of working. Phase 0's team mode asked a technical person to run an installer with flags, committed kit files to the shared repo, and relied on a CI gate. That is too many manual steps for most of the audience, and it puts personal setup into a shared history.

## 2. Decisions

| # | Question | Decision |
|---|---|---|
| 1 | Is anything from the kit committed to the shared repo? | **No.** The kit lives only in each person's working copy. |
| 2 | Where does a person's setup live? | **Inside each repo folder, hidden from git** via `.git/info/exclude`. Set up once per repo. |
| 3 | How does the kit get into a repo? | **Copy the kit folder in, then tell Copilot "do the onboarding".** (A fixed install location may be added later as a second source.) |
| 4 | What differs between roles? | **Behaviour and skills now; connectors later** (after Phase 3's Atlassian CLI work). |
| 5 | What can each person tailor? | **All of:** language (English, Romanian, German), git/terminal comfort, extra or fewer skills, several roles, session rituals. |
| 6 | The team already has its own AI files | **Never edit them; add kit files alongside.** Warn on overlaps and contradictions, without blocking. |
| 7 | Where do role packs come from? | **Layered:** hand-written core packs, sourced from `docs/FRQ-Roles/`; role discovery (v2) proposes new or changed packs in the same format; personal tweaks on top. |
| 8 | How long is the first onboarding? | **Three questions:** name, role(s), language. Everything else defaults by role; "change my preferences" any time. |
| 9 | Team mode | **Retired.** Personal mode only, for now. |
| — | How to build it | **Copilot runs the conversation; a small tested script does the file work.** |
| — | Session-start hook | **Dropped after the VM spike (2026-10-08):** VS Code doesn't run hooks and their output doesn't reach the model. The core instructions make Copilot run `check --quiet` instead (§6). |

## 3. What the person does

1. Copy the kit folder anywhere into the repo (a GitHub ZIP or a colleague's copy, any folder name).
2. Open the repo in VS Code; start Copilot Chat (Agent mode) or `copilot` in the terminal.
3. Say **"do the onboarding"**. Copilot finds the kit's `ONBOARDING.md` and follows it.
4. Answer three questions: name, role(s), language.
5. Copilot reports what was set up and that "change my preferences" and "update the kit" work at any time.

## 4. What ends up on disk

Every file is new and kit-named, and every path is listed in `.git/info/exclude`, so `git status` shows nothing.

```
<repo>/
├── .ai-sdlc/
│   ├── kit/            the copied kit folder, moved here (needed for updates and role packs)
│   ├── USER.md         name, roles, language, preferences
│   └── state.json      kit version, packs, placed files + fingerprints, acknowledged warnings
├── .github/
│   └── instructions/ai-sdlc-*.instructions.md   core brief + one file per role
└── .agents/skills/ai-sdlc-*/SKILL.md            the role's skills, prefixed so names cannot clash
```

The kit never creates or edits `AGENTS.md`, `.github/copilot-instructions.md` or `.vscode/settings.json`; the team may own them. Copilot reads the team's files and the kit's `ai-sdlc-*` files together.

**To verify before building (spike):** that Copilot CLI and VS Code read `.github/instructions/*.instructions.md`, `.github/hooks/*.json` and `.agents/skills/`. Cartograph relies on the same locations, which makes it likely but not proven.

**Verified on the VM (2026-10-08, Copilot CLI 1.0.93, VS Code 1.138 + Copilot Chat):** 1 ✅ · 2 ✅ · 3 ✅ (shapes A and B) · 4 ❌ · 5 ❌ · 6 ✅ · 7 ✅ · 8 ✅ · 9 ✅ · 10 ❌ (informational). Hooks: CLI ran both shapes; VS Code ran none; output never reached the model. So no hook is placed (decision A, §2 and §6).

## 5. Components

### 5.1 `setup.py` (kit root, stdlib only)

Copilot calls it; people never need to.

| Command | Does |
|---|---|
| `setup --name … --roles po,sm --lang de` | Move the kit to `.ai-sdlc/kit/`, place the packs' files, write the exclude block, record `state.json`, run `check` |
| `change --roles … / --lang … / --skill +x -y / --git-comfort … / --rituals …` | Update choices; add or remove only the affected files |
| `update` | Run from a newer kit copy: refresh unedited kit files, keep choices; an edited file is kept and the kit's version is written as `<file>.kit-new` |
| `check [--quiet]` | Files present, all excluded, nothing stale, team-overlap warnings; one plain-language line |
| `ack <warning-id>` | Record that a warning was seen, with the team file's fingerprint |
| `remove` | Delete only files whose fingerprint still matches, remove the exclude block; the repo ends exactly as before setup |

Every command prints a short, plain summary that Copilot can relay.

### 5.2 Role packs (`roles/<id>/`)

```
role.json        id, label, source document (docs/FRQ-Roles/…), skills, defaults (git comfort, rituals), connectors ([] until Phase 3)
instructions.md  how Copilot behaves for this role → ai-sdlc-<id>.instructions.md
```

A **core pack** applies to everyone: the kit's working rules, the reply language, the gate "if `.ai-sdlc/USER.md` is missing, do the onboarding first", and the session-start line "run `python3 .ai-sdlc/kit/setup.py check --quiet` once and mention any warning". All packs share one format, so v2 role discovery can generate packs without migration.

With several roles: skills are combined; each role keeps its own instructions file; where defaults disagree, the more guided one wins (e.g. "do git for me").

### 5.3 `ONBOARDING.md` (kit root)

The conversation script for Copilot: check `python3`, ask the three questions, run `setup.py`, relay the result and warnings in plain words. It holds no file-placement logic.

### 5.4 Reused from Phase 0

Fingerprint states (unchanged / edited / foreign), the safe orphan sweep, the frontmatter parser and the skill validator. Not carried over: install profiles, `--ci`, the Jenkinsfile, team-mode file classes.

## 6. Flows

**First time.** Copilot follows `ONBOARDING.md` → asks three questions (then speaks the chosen language) → runs `setup` → relays the summary and two kinds of warnings: precise ones from the script (the team has its own `AGENTS.md`; the team's rules also cover `docs/**`; a skill name clashes) and judgement ones from Copilot reading both sets of instructions for real contradictions → the person acknowledges each → `setup.py ack <id>`.

**Every session.** The core instructions tell Copilot to run `python3 .ai-sdlc/kit/setup.py check --quiet` once at the start of a session and mention any warning. The command prints one line, e.g. `AI-SDLC 0.4 · roles: PO, SM · de · ok`, or a warning (a team file it overlaps changed; a kit file is missing or no longer excluded; a newer kit is waiting for `update`).

**Change.** "Change my preferences" → Copilot asks what → `setup.py change …`.

**Update.** Copy a newer kit folder in → "update the kit" → Copilot runs the new folder's `setup.py update`.

**Language.** The core instructions file carries "Always answer in <language>"; it works the same in Copilot Chat and the CLI.

## 7. Safety

| Situation | Handling |
|---|---|
| The copied kit folder before onboarding (untracked, `git add -A` would take it) | Moving and excluding it is the first thing `setup` does, before any question. `check` warns about any unprotected kit copy. |
| The team already committed a file at a kit path | `git ls-files` first; never write to a tracked path; skip and report. |
| Team files overlap or contradict kit files | Warning only; nothing changed or blocked. |
| Not a git repo | Setup works; it says nothing is protected by git-exclude. |
| `python3` missing or older than 3.9 | `ONBOARDING.md` checks first and explains in plain words who to ask; nothing changed. |
| Interrupted setup | Re-running completes it without duplicates; `state.json` is written last. |
| Copilot writes kit files itself | `check` lists unknown or unexcluded `ai-sdlc` files and offers to fix them. |
| The person edited a kit file | `update` and `change` keep it (kit version as `.kit-new`); `remove` keeps and lists it. |

The script never uses the network, never runs a git command that changes anything (only `ls-files`, `check-ignore`, `rev-parse`), never writes outside the repo, and never touches a file it did not create.

**Accepted limit:** `git add -f` bypasses git-exclude. No local git hooks are installed, because they can clash with the team's own.

## 8. Testing

1. **VM spike before building:** the Copilot locations in §4, in VS Code and the CLI. If one fails, revisit the layout with the owner before writing code. Done 2026-10-08 (results in §4).
2. **Unit tests for `setup.py`** in temporary git repos: every command, several roles, each language, tracked-path skip, non-git folder, interrupted run, kept edits. The strictest: after `remove`, the repo is byte-for-byte what it was before setup, including `.git/info/exclude`.
3. **End-to-end CI job** (replaces `adopt-e2e`): a fake team repo with its own `AGENTS.md`, `.github/instructions` and a clashing skill → copy the kit → `setup` → `git status` is empty, team files unchanged, warnings present → `update` from a newer copy → `remove` restores the original.
4. **Role-pack validator:** every `role.json` is valid, its source document exists, its skills exist and pass the skill validator.
5. **Pilot:** the owner, then one non-technical person (PO or PM), each saying "do the onboarding" on the VM. Their experience is the acceptance test.

## 9. Scope

| v1 | Later |
|---|---|
| Core pack; PO, PM, SM (from `docs/FRQ-Roles/`); Dev, QA, Architect, EM (from the existing playbooks) | RTE/SAFe pack; connectors (Phase 3); role discovery (v2) |
| English, Romanian, German | Other languages |
| Session status line and drift check | More rituals (save reminders, summaries) |
| The six commands | Promoting a personal setup to a shared team setup (only on request) |

Kit version **0.4.0**, with a CHANGELOG entry saying team mode is retired. The README is rewritten around "copy, then *do the onboarding*". Kit-owned docs stay in English; Copilot replies in each person's language.
