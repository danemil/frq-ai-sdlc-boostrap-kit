# AI-SDLC kit: onboarding

> **To Copilot.** The person said "do the onboarding", or "change my preferences", "update the kit", "check the kit", "remove the kit" or "connect <a tool>". Follow the matching section below. Run every command yourself, from the repo root; the person only answers questions. The one exception is `setup.py connect`, which asks for secrets: the person runs it in their own terminal. Speak plainly, without git or Python words unless they use them. Never edit a team file: `AGENTS.md`, `.github/copilot-instructions.md`, or anything not named `ai-sdlc-*`.

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
6. **Look for contradictions.** For each `team-…` or `skill-clash:…` warning, read the team file it names and the kit's `.github/instructions/ai-sdlc-*.instructions.md`. Tell the person only about real contradictions (one says do X, the other says don't), one sentence each, naming both files. The team's rule wins; say so.
7. **Acknowledge.** For each warning the person has understood, run `python3 .ai-sdlc/kit/setup.py ack <warning-id>`. It comes back only if that team file changes.
8. **Close.** Say: "You're set up. Say 'change my preferences', 'update the kit' or 'remove the kit' at any time." Then name the tools the setup summary lists under "Connectors for your roles" (for example Jira and Confluence) and say: "I can read these for you once you connect them; say *connect Jira* (etc.) whenever you're ready." Do not ask for a URL, login or token now.
9. **Offer to connect them now (optional).** This is an offer, not a fourth question. Only if step 8 named a tool that is not marked connected or skipped, ask once: "Would you like to connect them now? You type your login in your own terminal, not here, and you can skip any tool." If they say "not now" (or no), skip this step: say nothing more about connecting. If yes, tell them to open a terminal (a terminal window, not this chat) in this repo and run, **themselves**: `python3 .ai-sdlc/kit/setup.py connect --suggested`. It asks about each tool one at a time (`y` connects it, `s` skips it, `a` skips all the rest; Enter skips), then offers any other tool. Do not run it yourself: it asks for secrets. When they say it is done, run `python3 .ai-sdlc/kit/setup.py connections` and tell them which tools are connected. A skipped tool is not suggested again; they can still say *connect Jira* (etc.) at any time.

## Change my preferences

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

`<skill>` is the skill id without `ai-sdlc-`, for example `drawio` for `ai-sdlc-drawio`. A wrong name is refused and the available ones are listed.

Relay the summary. If it says it kept their edit, explain that the kit's newer copy is next to their file as `<file>.kit-new`, for them to compare.

## Update the kit

1. **Find the newer copy.** Run `python3 .ai-sdlc/kit/setup.py check`. A `kit-copy:<folder>` item names the kit folder the person copied into the repo. A newer copy says it is waiting; a copy with the same version number says to update from it if it was copied in for that. Either way, use it.
2. **No copy yet?** If there is no `kit-copy:` item, the person has not copied a newer kit in. Do not fail. Tell them how, in plain words, then wait for them to say "update the kit" again:
   - Get the newer kit: `git pull` in their clone of the kit, or download the ZIP again from the kit's GitHub page (**Code → Download ZIP**, or a release) and unzip it.
   - Copy it into the repo under any folder name, without its `.git` folder, for example `rsync -a --exclude .git <kit folder>/ ./ai-sdlc-kit-new/`. If they tell you where the kit is, offer to run that copy for them.
3. **Update.** Run `python3 <that folder>/setup.py update`. Relay the summary, including any kept edits: the kit's newer copy is next to their file as `<file>.kit-new`, for them to compare. If it says the copy is older, nothing changed; say so. If it says the copy is incomplete, nothing changed either: ask them to copy the whole kit folder in again (as in step 2), then update from that copy.

## Check the kit

Run `python3 .ai-sdlc/kit/setup.py check` and relay each item:

- `missing:` or `unexcluded:`: run `python3 .ai-sdlc/kit/setup.py change` with no options. It puts files back and hides them again.
- `unknown:`: a file named like the kit's that the kit did not write. Ask before deleting it. (The person's own `ai-sdlc-personal.instructions.md` and `ai-sdlc-personal-*` skills are never reported.)
- `kit-copy:`: a newer copy means "update the kit". A same-version copy: ask whether they copied it in to update; if so, update from it, otherwise it can be deleted. An older one can be deleted, after asking.
- `stale-kit`: run `python3 .ai-sdlc/kit/setup.py update`. If it says the kit folder is incomplete, ask the person to copy the whole kit folder in again (as in "Update the kit", step 2) and update from that copy.
- `team-…` and `skill-clash:…`: as in steps 6 and 7 above.

## Remove the kit

1. **See what it would do.** Run `python3 .ai-sdlc/kit/setup.py remove`, without `--yes`. It changes nothing: it says what it would remove and what it keeps (files they edited, their personal notes and skills, their connector logins).
2. **Ask, then wait.** Tell them that in plain words and ask: "Shall I remove the kit from this repo?" Wait for their answer. The request "remove the kit" is not the yes.
3. **Only after they say yes,** run `python3 .ai-sdlc/kit/setup.py remove --yes` and relay what it removed and kept. Their personal notes and skills stay hidden from git. If they say no, or you cannot ask them, do not run it: nothing has changed.

Never run `remove --yes` on your own.

## Connect a tool

The person said "connect Jira" (or Confluence, Bitbucket, Jama, Jenkins). The connector names are `jira`, `confluence`, `bitbucket`, `jama` and `jenkins`. Connectors only read. **You never ask for, see, paste, store or repeat a token, password or other secret**, and never open the saved login files.

1. Run `python3 .ai-sdlc/kit/setup.py connections` and tell them whether that tool is already connected (its URL, user and last test).
2. If it is not connected, or they want to change it, tell them to run this **themselves, in their own terminal** (a terminal window, not this chat): `python3 .ai-sdlc/kit/setup.py connect <name>`. It asks for the URL and their login, hides what they type for secrets, saves it only on this computer (in their home folder, outside every repo), and tests it once. Do not run it yourself: it refuses to ask for secrets through an assistant.
3. If they paste a token or password into the chat, do not use or repeat it. Tell them to revoke it now and create a new one, then save it themselves with the command above.
4. Only if they ask you to test the connection, run `python3 .ai-sdlc/kit/setup.py connect <name> --test`. It uses the saved login, asks nothing and makes one read-only call. Relay the answer in plain words; the `ai-sdlc-connectors` skill explains each error and its fix.
5. To forget a saved login, run `python3 .ai-sdlc/kit/setup.py disconnect <name>`, without `--yes`: it deletes nothing and says which login it would delete. Ask "Shall I delete your saved <tool> login?" and wait. Only after they say yes, run `python3 .ai-sdlc/kit/setup.py disconnect <name> --yes`. Never run `--yes` on your own.
