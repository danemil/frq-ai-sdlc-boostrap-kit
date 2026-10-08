# AI-SDLC kit: onboarding

> **To Copilot.** The person said "do the onboarding", or "change my preferences", "update the kit", "check the kit" or "remove the kit". Follow the matching section below. Run every command yourself, from the repo root; the person only answers questions. Speak plainly, without git or Python words unless they use them. Never edit a team file: `AGENTS.md`, `.github/copilot-instructions.md`, or anything not named `ai-sdlc-*`.

Below, `KIT` is the folder this file is in. Before setup it is wherever the person copied it (for example `tools/ai-sdlc-kit`); after setup it is always `.ai-sdlc/kit`.

## Do the onboarding

1. **Check Python.** Run `python3 --version`. It must say 3.9 or newer. If the command is missing or older, say: "Your computer needs Python 3.9 or newer before I can set this up. Please ask your IT support to install it." Then stop. Nothing has changed.
2. **Protect the kit first.** Run `python3 KIT/setup.py setup --protect-only`. It moves the kit to `.ai-sdlc/kit` and hides it from git. From now on, run `python3 .ai-sdlc/kit/setup.py`.
3. **Ask three questions,** one at a time:
   1. "What is your name?"
   2. "What is your role here? You can pick more than one: Product Owner (`po`), Product Manager (`pm`), Scrum Master / Team Coach in SAFe (`sm`), Developer (`dev`), QA (`qa`), Architect (`architect`), Engineering Manager (`em`)."
   3. "Which language should I answer in: English (`en`), Romanian (`ro`) or German (`de`)?"

   From the answer to question 3 on, speak that language.
4. **Set up.** Run `python3 .ai-sdlc/kit/setup.py setup --name "<name>" --roles <ids, comma-separated> --lang <code>`.
5. **Relay the result** in plain words: who it is set up for, then each item under "Check", with its id in brackets.
6. **Look for contradictions.** For each `team-…` warning, read the team file it names and the kit's `.github/instructions/ai-sdlc-*.instructions.md`. Tell the person only about real contradictions (one says do X, the other says don't), one sentence each, naming both files. The team's rule wins; say so.
7. **Acknowledge.** If `setup.py` answers that this command is not built yet, tell the person in their language that it arrives in the next kit version, and go to step 8.
   For each warning the person has understood, run `python3 .ai-sdlc/kit/setup.py ack <warning-id>`. It comes back only if that team file changes.
8. **Close.** Say: "You're set up. Say 'change my preferences', 'update the kit' or 'remove the kit' at any time."

## Change my preferences

If `setup.py` answers that this command is not built yet, tell the person in their language that it arrives in the next kit version, and stop.

Ask what they want to change, then run `python3 .ai-sdlc/kit/setup.py change` with the matching option:

| They want | Option |
|---|---|
| another name | `--name "<name>"` |
| other roles | `--roles <ids>` (the full new list) |
| another language | `--lang <en, ro or de>` |
| git done for them, or not | `--git-comfort <hidden, guided, git-native or default>` |
| the one-line session summary on or off (the session-start check always runs) | `--rituals <status, none or default>` |
| an extra skill | `--add-skill <skill>` |
| a skill left out | `--drop-skill <skill>` |

Relay the summary. If it says it kept their edit, explain that the kit's newer copy is next to their file as `<file>.kit-new`, for them to compare.

## Update the kit

If `setup.py` answers that this command is not built yet, tell the person in their language that it arrives in the next kit version, and stop.

The person copied a newer kit folder into the repo; `check` names it (`kit-copy:<folder>`). Run `python3 <that folder>/setup.py update`. Relay the summary, including any kept edits.

## Check the kit

Run `python3 .ai-sdlc/kit/setup.py check` and relay each item:

- `missing:` or `unexcluded:`: run `python3 .ai-sdlc/kit/setup.py change` with no options. It puts files back and hides them again.
- `unknown:`: a file named like the kit's that the kit did not write. Ask before deleting it.
- `kit-copy:`: a newer copy means "update the kit"; an older one can be deleted, after asking.
- `stale-kit`: run `python3 .ai-sdlc/kit/setup.py update`.
- `team-…` and `skill-clash:…`: as in steps 6 and 7 above.

## Remove the kit

If `setup.py` answers that this command is not built yet, tell the person in their language that it arrives in the next kit version, and stop.

Ask first: "This removes the kit and your settings from this repo. Files you edited are kept. Continue?" On yes, run `python3 .ai-sdlc/kit/setup.py remove` and relay what it removed and kept.
