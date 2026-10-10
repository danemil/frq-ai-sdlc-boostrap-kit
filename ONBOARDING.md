# AI-SDLC kit: onboarding

> **To Copilot.** The person said "do the onboarding", or "change my preferences", "recommend skills", "show me the other skills", "update the kit", "check the kit", "remove the kit" or "connect <a tool>". Follow the matching section below. Run every command yourself, from the repo root; the person only answers questions. The one exception is `setup.py connect`, which asks for secrets: the person runs it in their own terminal. Speak plainly, without git, Python or command-line words unless they use them first. Ask one question per message and wait for the answer. Never invent an answer or a default for the person, and never treat their request as a yes to a question you have not asked. Never edit a team file: `AGENTS.md`, `.github/copilot-instructions.md`, or anything not named `ai-sdlc-*`.

Below, `KIT` is the folder this file is in. Before setup it is wherever the person copied it (for example `tools/ai-sdlc-kit`); after setup it is always `.ai-sdlc/kit`. Use this file, the `ONBOARDING.md` next to `setup.py`; ignore any other onboarding file in the kit.

## Do the onboarding

0. **Already set up here?** If `.ai-sdlc/USER.md` exists, the kit is already set up in this repo and the person wants to do the onboarding again (for example with other roles). Do not say it is already done, and do not stop:
   1. Run `python3 .ai-sdlc/kit/setup.py check`. If it has a `kit-copy:` item saying a newer kit is waiting, ask first: "A newer version of the kit is waiting in <folder>. Shall I update the kit first?" If yes, follow "Update the kit" below, then come back here. If no, go on.
   2. Read `.ai-sdlc/USER.md` and say who it is set up for now (name, roles, language), and that you will ask the three questions again.
   3. Skip steps 1 and 2 (no `--protect-only`): go straight to step 3, then run step 4 and the rest as written. Files for new roles are added and the ones no longer needed are removed.
1. **Check Python.** Run `python3 --version`. It must say 3.9 or newer. If the command is missing or older, say: "Your computer needs Python 3.9 or newer before I can set this up. Please ask your IT support to install it." Then stop. Nothing has changed.
2. **Protect the kit first.** Run `python3 KIT/setup.py setup --protect-only`. It moves the kit to `.ai-sdlc/kit` and hides it from git. From now on, run `python3 .ai-sdlc/kit/setup.py`.
3. **Ask three questions,** one at a time: ask the first, wait for the answer, then ask the next. Never put two questions in one message. Do not offer defaults or suggested answers, and never fill an answer in yourself (not from `USER.md`, the git settings or an earlier setup): use only what the person says.
   1. "What is your name?"
   2. "What is your role here? You can pick more than one: Product Owner (`po`), Product Manager (`pm`), Scrum Master / Team Coach in SAFe (`sm`), Developer (`dev`), QA (`qa`), Architect (`architect`), Engineering Manager (`em`)."
   3. "Which language should I answer in: English (`en`), Romanian (`ro`) or German (`de`)?"

   From the answer to question 3 on, speak that language.
4. **Set up.** Run `python3 .ai-sdlc/kit/setup.py setup --name "<name>" --roles <ids, comma-separated> --lang <code>`.
5. **Relay the result** in plain words: who it is set up for, then each item under "Check", with its id in brackets.
6. **Look for contradictions.** For each `team-…` or `skill-clash:…` warning, read the team file it names and the kit's `.github/instructions/ai-sdlc-*.instructions.md`. Tell the person only about real contradictions (one says do X, the other says don't), one sentence each, naming both files. The team's rule wins; say so.
7. **Mark them as seen, only if they agree.** If there were `team-…` or `skill-clash:…` warnings, ask: "Shall I mark these as seen? They come back only if that team file changes." Wait for the answer. Only after a yes, run `python3 .ai-sdlc/kit/setup.py ack <warning-id>` for each one. If they say no, leave them: nothing breaks.
8. **Suggest skills for this repo (optional).** Run `python3 .ai-sdlc/kit/setup.py recommend`. It reads the repo's files and changes nothing. If it says there are no suggestions, say nothing and go on. Otherwise tell the person each suggestion in one plain sentence with its reason (for example "add the JavaFX skill: this repo uses JavaFX"), then ask once: "Would you like these skills? You can take all, some or none." This is an offer, not a fourth question. Wait for the answer. All or some: run the `change` command the output gives, with only the skills they chose; then, if they left some out, run `python3 .ai-sdlc/kit/setup.py recommend --decline <the skill names they did not take, comma-separated>` (for example `--decline javafx,java-junit`). None, or "not now": run `python3 .ai-sdlc/kit/setup.py recommend --decline all` and say they can say "recommend skills" at any time. Never apply a suggestion they did not choose.
9. **Other skills (optional).** Run `python3 .ai-sdlc/kit/setup.py recommend --all` and show only its part "Other skills you can add": the groups and one line per skill, as printed. Ask once: "Would you like any of these as well? 'None' is fine." Wait for the answer. For the skills they pick, run `python3 .ai-sdlc/kit/setup.py change --add-skill <name>` (one `--add-skill` per skill). For "none", run nothing: nothing is stored, and the list is only shown again when they say "show me the other skills". Never add a skill they did not pick.
10. **Close.** Say: "You're set up. Say 'change my preferences', 'update the kit' or 'remove the kit' at any time." Then name the tools the setup summary lists under "Connectors for your roles" (for example Jira and Confluence), exactly as listed, and say: "I can read these for you once you connect them; say *connect Jira* (etc.) whenever you're ready." Do not ask for a URL, login or token now.
11. **Offer to connect them now (optional).** This is an offer, not a fourth question. Only if step 10 named a tool that is not marked connected or skipped, ask once: "Would you like to connect them now? You type your login in your own terminal, not here, and you can skip any tool." Wait for the answer. If they say "not now" (or no), skip this step: say nothing more about connecting. Only if they say yes, tell them to open a terminal (a terminal window, not this chat) in this repo and run, **themselves**: `python3 .ai-sdlc/kit/setup.py connect --suggested`. It asks about each tool one at a time (`y` connects it, `s` skips it, `a` skips all the rest; Enter skips), then offers any other tool. Do not run it yourself: it asks for secrets. When they say it is done, run `python3 .ai-sdlc/kit/setup.py connections` and tell them which tools are connected. A skipped tool is not suggested again; they can still say *connect Jira* (etc.) at any time.

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

Relay the summary as it is. If it says it kept their edit and the kit's newer copy is next to it as `<file>.kit-new`, explain that they can compare the two. If it says there is nothing to compare, there is no `.kit-new` file; do not mention one.

## Recommend skills

The person said "recommend skills", "which skills fit this repo?" or "show me the other skills".

1. For suggestions, run `python3 .ai-sdlc/kit/setup.py recommend`; for the other skills, run `python3 .ai-sdlc/kit/setup.py recommend --all`. Both read the repo's files and change nothing.
2. Relay the open suggestions, each in one plain sentence with its reason, and the ones under "Declined earlier". With `--all`, also the part "Other skills you can add", grouped, one line per skill, as printed.
3. Ask one question: "Would you like any of these? You can take all, some or none." Wait for the answer. Then do as in onboarding steps 8 and 9: run `python3 .ai-sdlc/kit/setup.py change --add-skill <name>` for each skill they chose (a declined suggestion is taken the same way), and `python3 .ai-sdlc/kit/setup.py recommend --decline <skill names>` for open suggestions they said no to. Never apply a suggestion they did not choose. Never add a skill they did not pick.

## Update the kit

1. **Find the newer copy.** Run `python3 .ai-sdlc/kit/setup.py check`. A `kit-copy:<folder>` item names the kit folder the person copied into the repo. A newer copy says it is waiting; a copy with the same version number says to update from it if it was copied in for that. Either way, use it.
2. **No copy yet?** If there is no `kit-copy:` item, the person has not copied a newer kit in. Do not fail. Tell them how, in plain words, then wait for them to say "update the kit" again:
   - Get the newer kit from the kit's GitHub page: read its address in the kit's `README.md` (next to `setup.py`, section "Get the latest version from GitHub") and give it to them. There they open **Releases**, take the newest one (marked **Latest**) as **Source code (zip)**, and unzip it. If they keep a clone of the kit, a `git pull` there does the same.
   - Put it into this repo, in a new folder with any name. If they tell you where the unzipped kit is, offer to copy it in for them (leave out its `.git` folder, if it has one). Use plain words: no command names unless they ask how to do it themselves.
3. **Update.** Run `python3 <that folder>/setup.py update`. Relay the summary as it is: the folder they copied in has been moved into the kit's place (the summary says so; it is not left behind), and for each kept edit, whether the kit's newer copy waits next to it as `<file>.kit-new` or there is nothing to compare. Mention a `.kit-new` file only if the summary names one. If it says the copy is older, nothing changed; say so. If it says the copy is incomplete, nothing changed either: ask them to copy the whole kit folder in again (as in step 2), then update from that copy. If the summary has a line "Skill suggestions for this repo", offer them as in onboarding step 8.

## Check the kit

Run `python3 .ai-sdlc/kit/setup.py check` and relay each item:

- `missing:` or `unexcluded:`: run `python3 .ai-sdlc/kit/setup.py change` with no options. It puts files back and hides them again.
  If the `missing:` path is under `.ai-sdlc/kit`, the kit folder itself is incomplete (a skill keeps that file only there): follow "Update the kit" with a whole copy of the kit.
- `unknown:`: a file named like the kit's that the kit did not write. Ask before deleting it. (The person's own `ai-sdlc-personal.instructions.md` and `ai-sdlc-personal-*` skills are never reported.)
- `kept-edit:`: a file they edited that their choices no longer need; the kit kept it instead of deleting their edit. Say so, and that they can delete it if they don't need it. Ask before deleting it.
- `kit-copy:`: a newer copy means "update the kit". A same-version copy: ask whether they copied it in to update; if so, update from it, otherwise it can be deleted. An older one can be deleted, after asking.
- `stale-kit`: run `python3 .ai-sdlc/kit/setup.py update`. If it says the kit folder is incomplete, ask the person to copy the whole kit folder in again (as in "Update the kit", step 2) and update from that copy.
- `team-…` and `skill-clash:…`: as in steps 6 and 7 above.
- The line "Connectors for your roles" names the tools their roles usually use, marking the ones connected or skipped. Relay it as it is; do not guess which tools are connected.

## Remove the kit

1. **See what it would do.** Run `python3 .ai-sdlc/kit/setup.py remove`, without `--yes`. It changes nothing: it says what it would remove and what it keeps (files they edited, their personal notes and skills, their connector logins).
2. **Ask, then wait.** Tell them that in plain words and ask: "Shall I remove the kit from this repo?" Wait for their answer. The request "remove the kit" is not the yes.
3. **Only after they say yes,** run `python3 .ai-sdlc/kit/setup.py remove --yes` and relay what it removed and kept. Their personal notes and skills stay hidden from git. If they say no, or you cannot ask them, do not run it: nothing has changed.

Never run `remove --yes` on your own.

## Connect a tool

The person said "connect Jira" (or Confluence, Bitbucket, Jama, Jenkins). The connector names are `jira`, `confluence`, `bitbucket`, `jama` and `jenkins`. Connectors only read. **You never ask for, see, paste, store or repeat a token, password or other secret**, and never open the saved login files.

1. Run `python3 .ai-sdlc/kit/setup.py connections` and tell them whether that tool is already connected (its URL, user and last test).
2. If it is not connected, or they want to change it, tell them to run this **themselves, in their own terminal** (a terminal window, not this chat): `python3 .ai-sdlc/kit/setup.py connect <name>`. It asks for the URL and their login, hides what they type for secrets, saves it only on this computer (in their home folder, outside every repo), and tests it once. Do not run it yourself: it refuses to ask for secrets through an assistant.
3. If they paste a token or password into the chat, do not use or repeat it, and never quote it: say "the token you pasted". Tell them to revoke it now and create a new one, then save it themselves with the command above.
4. Only if they ask you to test the connection, run `python3 .ai-sdlc/kit/setup.py connect <name> --test`. It uses the saved login, asks nothing and makes one read-only call. Relay the answer in plain words; the `ai-sdlc-connectors` skill explains each error and its fix.
5. To forget a saved login, run `python3 .ai-sdlc/kit/setup.py disconnect <name>`, without `--yes`: it deletes nothing and says which login it would delete. Ask "Shall I delete your saved <tool> login?" and wait. Only after they say yes, run `python3 .ai-sdlc/kit/setup.py disconnect <name> --yes`. Never run `--yes` on your own.
