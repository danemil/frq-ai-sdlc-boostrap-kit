---
name: deceneus
description: Review the conversation for lasting preferences, recurring instructions,
  communication style, and reusable workflows worth saving as the person's own kit
  preferences, personal notes, or personal skills. Propose exact content for approval
  BEFORE writing anything. Use when the user says "deceneus", asks what should be
  remembered from this chat, what to save from this session, or asks to turn what we
  did into a skill, or says "remember that", "from now on" or "always do X".
---

# deceneus

Turn a finished conversation into durable configuration. **Propose first, write only
what is approved.**

Everything you propose is **personal and hidden from git**, on purpose: never offer to
commit these files, and never stage them. You never propose
editing a team file: `AGENTS.md`, `.github/copilot-instructions.md`, any file in
`.github/instructions/` not named `ai-sdlc-*`, anything under `.claude/` or
`.vscode/`. If a lesson belongs in a team file, say so in one line and leave it to
the person to raise with their team.

## 1. Harvest

Re-read the conversation for four categories. Most sessions yield 0-3 items total —
that is a normal result, not a failure.

- **Lasting preferences** — how they want work delivered, not one-off task details.
- **Recurring instructions** — anything they said more than once, or corrected you on.
- **Communication style** — length, tone, how they want questions asked.
- **Reusable workflows** — a sequence you worked out that would be costly to
  re-derive. This is the richest source of Skills.

Weight *corrections* and *friction* heavily. Where the user pushed back, said
"that's not clear", or you got something wrong, is where the durable lesson is.

## 2. Check what already exists — this is the step that gets skipped

Before proposing anything, read the person's current setup:

    cat .ai-sdlc/USER.md
    cat .github/instructions/ai-sdlc-*.instructions.md
    ls .agents/skills/ | grep '^ai-sdlc-'

`USER.md` holds their kit preferences, the `ai-sdlc-*.instructions.md` files hold
the kit's rules for them (core and one per role) and their personal notes
(`ai-sdlc-personal.instructions.md`, if it exists), and `.agents/skills/ai-sdlc-*`
are their skills. Read the team's own files too, but only to avoid repeating or
contradicting them, never to edit them.

Then separate two things that feel identical and are not:

| finding | correct response |
|---|---|
| The rule does not exist | Propose adding it |
| The rule exists and you did not follow it | **Do NOT propose it.** Say so plainly |

Re-adding a rule the user already wrote is worse than useless: it grows a file they
have to maintain and implies their instruction was missing rather than ignored.
Say "your setup already says X (in <file>); I didn't follow it" and move on.

## 3. Decide scope and destination

Only these three destinations exist. All are personal and hidden from git.

| content | destination |
|---|---|
| A kit preference: name, roles, language, git comfort, session summary, a skill added or left out | `python3 .ai-sdlc/kit/setup.py change` with `--name`, `--roles`, `--lang`, `--git-comfort`, `--rituals`, `--add-skill` or `--drop-skill`. It updates `.ai-sdlc/USER.md`; never edit that file by hand |
| A one-line habit, a recurring instruction, communication style | a line in `.github/instructions/ai-sdlc-personal.instructions.md` (personal notes), NOT a Skill |
| A multi-step procedure with real recall cost | a personal skill: `.agents/skills/ai-sdlc-personal-<name>/SKILL.md`, whose frontmatter `name:` is `ai-sdlc-personal-<name>` |

Create the personal notes file with this frontmatter, so it applies everywhere:

    ---
    applyTo: '**'
    ---
    # Personal notes

The kit keeps these personal files when it updates or changes the setup, and
`remove` keeps them too (it lists them, because git then shows them). Never write
to the kit's own `ai-sdlc-*` files (core, role files, placed skills): the kit
rewrites them.

Prefer adding to the personal notes or editing an existing personal skill over
creating a near-duplicate. Something that does not fit these destinations (a
permission, an environment variable, an editor setting) is not saved: list it
under "deliberately NOT adding" with the reason.

## 4. Verify before documenting

**Any command a skill contains must be one you have actually run successfully.**
A skill that ships a plausible-but-broken command is worse than no skill: it will be
trusted and it will fail at the moment it is relied on. If you cannot verify a
command in this session, either document the exact variant you did run, or mark it
explicitly as unverified.

The same applies to file paths, container names, ports, and env var names — quote
what you observed, not what you expect.

## 5. Propose — show the full text

Show **complete, final content** for every item, in the reply, before writing:

- the exact file path, or for a kit preference the exact `setup.py change` command
- the full text or diff, not a summary of it
- one line on why it earns its place

Then add a short **"What I am deliberately NOT adding"** section covering rules that
already exist, items too situational to generalise, and anything you could not
verify. This is often the most useful part of the reflection — it shows the list was
filtered rather than padded.

End with a single question: which items to save.

## 6. Write only what is approved

Write approved items verbatim (or run the approved `setup.py change` command), then
confirm each path. If the user approves some and
edits others, apply their wording exactly — do not re-improve it.

If the user approves a batch and you are interrupted partway, **report which items
were written and which were not**, so nothing is silently lost.

## Anti-patterns

- Padding the list to look thorough. Zero-to-three real items is the normal yield.
- Saving task state ("we were mid-deploy") — that belongs in a handoff, not memory.
- Proposing a Skill for something that is one sentence in the personal notes.
- Proposing an edit to a team file, or to one of the kit's own `ai-sdlc-*` files.
- Writing anything before showing it, including "obvious" items.
- Restating the user's own existing rules back to them as new proposals.
