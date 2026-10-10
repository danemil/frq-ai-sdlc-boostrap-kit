# How to use the kit (common tasks)

A step-by-step guide for everyone on the team: developers, QA, product owners, product managers and scrum masters. Every task has two paths:

- **(a) Say it to Copilot.** In VS Code, open Copilot Chat in **Agent** mode (or run `copilot` in a terminal) and type the sentence shown.
- **(b) Terminal.** The exact commands, for when you prefer the terminal or Copilot is not available. Open one in VS Code with **Terminal → New Terminal**. It opens on the VM, in your repo.

Run every terminal command from the **top folder of your repo** (the folder that holds `.git`). Example output in this guide comes from real runs of the kit; long lists are shortened with `…`, and server addresses and home folders are replaced with example ones.

**Contents**

1. [First-time setup in a repo](#1-first-time-setup-in-a-repo)
2. [Update the kit to a newer version](#2-update-the-kit-to-a-newer-version)
3. [Connect a tool](#3-connect-a-tool)
4. [Use the connectors](#4-use-the-connectors)
5. [Change your preferences](#5-change-your-preferences)
6. [Check your setup](#6-check-your-setup)
7. [Personal notes and skills](#7-personal-notes-and-skills)
8. [Remove the kit from a repo](#8-remove-the-kit-from-a-repo)
9. [Troubleshooting](#9-troubleshooting)

You need **Python 3.9 or newer** on the VM. Check it with `python3 --version`. If it is missing or older, ask IT (see [Troubleshooting](#9-troubleshooting)).

---

## 1. First-time setup in a repo

Do this **once per repo**. After that, use [update](#2-update-the-kit-to-a-newer-version) for a newer kit and [change](#5-change-your-preferences) for other choices. To answer the three questions again (for example, with other roles), say **"do the onboarding"** again; see [Redo the onboarding](#redo-the-onboarding) below.

### Step 1: get the kit

Pick one:

- **ZIP.** On the kit's GitHub page, click **Code → Download ZIP** (or, under **Releases**, a release's **Source code (zip)**). Unzip it. To get it onto the VM, drag the ZIP or the unzipped folder into VS Code's Explorer, or download it on the VM with `curl -L -o kit.zip <ZIP link>` and then `unzip kit.zip`.
- **git clone.** Keep a clone of the kit outside your repo. It makes later updates a one-line `git pull`:

  ```bash
  git clone <kit repo URL> ~/ai-sdlc-kit-source
  ```

### Step 2: copy it into your repo, without `.git`

Any folder name inside the repo works. Leave out the kit's own `.git` folder. The ZIP has none; a clone does:

```bash
cd ~/repos/my-repo                                         # your repo's top folder
rsync -a --exclude .git ~/ai-sdlc-kit-source/ ./ai-sdlc-kit/
```

Keep the `/` after the source folder: it copies the folder's *contents* into `ai-sdlc-kit/`. No `rsync`? Use `mkdir ai-sdlc-kit && cp -r ~/ai-sdlc-kit-source/. ai-sdlc-kit/ && rm -rf ai-sdlc-kit/.git` instead.

For a moment `git status` shows `?? ai-sdlc-kit/`. The next step moves the folder and hides it.

### Step 3: set up

**(a) Copilot:** say **"do the onboarding"**. Copilot checks Python, then asks three questions (your name, your role or roles, your language) and sets everything up. If it cannot find the instructions, or picks another file, say: *"follow ai-sdlc-kit/ONBOARDING.md"* (use your folder name: it is the `ONBOARDING.md` next to `setup.py`).

**(b) Terminal:** two commands. The first moves the kit to `.ai-sdlc/kit` and hides it from git. The second places your files:

```bash
python3 ai-sdlc-kit/setup.py setup --protect-only
python3 .ai-sdlc/kit/setup.py setup --name "Ana" --roles po,qa --lang en
```

- `--roles`: one or more of `po` (Product Owner), `pm` (Product Manager), `sm` (Scrum Master / Team Coach), `dev` (Developer), `qa` (QA), `architect` (Architect), `em` (Engineering Manager), separated by commas.
- `--lang`: `en` (English), `ro` (Romanian) or `de` (German).

```text
The kit is now in .ai-sdlc/kit and hidden from git.
Next: python3 .ai-sdlc/kit/setup.py setup --name … --roles … --lang …
Set up AI-SDLC 0.9.0 for Ana: Product Owner, QA · English.
- Hidden from git: .ai-sdlc/ and every ai-sdlc-* file.
- Wrote 91 file(s): .agents/skills/ (86 in 16 skills), .ai-sdlc/ (1), .github/hooks/ (1), .github/instructions/ (3)
- Skills: ai-sdlc-connectors, ai-sdlc-deceneus, …, ai-sdlc-playbook-product, ai-sdlc-playbook-qa, … · git: hidden · session summary: on
- Connectors for your roles: jira, confluence, jama, jenkins (say 'connect jira')
Say "change my preferences", "update the kit" or "remove the kit" at any time.
Check: all good.
```

Now `git status` shows nothing new. Everything the kit added is hidden through `.git/info/exclude`, on your computer only. The summary counts the files per folder; add `--verbose` to `setup`, `change` or `update` to list every file.

### Redo the onboarding

Say **"do the onboarding"** again. Copilot sees the kit is already set up, checks it (and offers to update first if a newer kit copy is waiting), tells you who it is set up for, and asks the three questions again. Files for new roles are added, the ones no longer needed removed. Your other preferences and your connector logins stay. In the terminal, run `setup` again from the kit's place, with the new answers:

```bash
python3 .ai-sdlc/kit/setup.py setup --name "Ana" --roles po,sm --lang en
```

> **A newer kit copy goes through `update`, not `setup`.** Running `setup` from a newly copied kit folder in a repo that is already set up is refused: *"A kit is already set up in this repo (.ai-sdlc/kit). To use this newer copy, say "update the kit"."* For a newer kit use [update](#2-update-the-kit-to-a-newer-version); for single choices use [change](#5-change-your-preferences). `setup` is also not the connect command. `setup.py setup jira` fails with `unrecognized arguments: jira`.

---

## 2. Update the kit to a newer version

### How to tell you need it

- `check` (or the line Copilot shows at the start of a session) reports **`stale-kit`**, or **`kit-copy:<folder>`** with *"A newer kit (…) is waiting"* (or *"Another copy of the kit (same version …)"*, if you copied it in to update).
- A command fails with **`invalid choice`**. For example, `setup.py connect jira` gives `invalid choice: 'connect' (choose from setup, change, update, check, ack, remove)`. Your kit is older than the command.
- The README or this guide describes a feature your kit lacks. To see what you have, run `cat .ai-sdlc/kit/VERSION`, or check for a file such as `ls .ai-sdlc/kit/connectors.py`. Features on `main` can arrive before the version number changes, so a newer kit may show the **same** number.

### Step 1: get the newer kit

- **You have a clone:** `cd ~/ai-sdlc-kit-source && git pull`
- **You use ZIPs:** download it again, from **Code → Download ZIP** (the latest `main`) or from a release, and unzip it.

### Step 2: copy it into your repo, without `.git`

Use any folder name inside the repo:

```bash
cd ~/repos/my-repo
rsync -a --exclude .git ~/ai-sdlc-kit-source/ ./ai-sdlc-kit-new/
```

### Step 3: update

**(a) Copilot:** say **"update the kit"**.

**(b) Terminal:** run the `setup.py` **of the newer copy**, with `update`:

```bash
python3 ai-sdlc-kit-new/setup.py update
```

The whole recipe, for a clone:

```bash
(cd ~/ai-sdlc-kit-source && git pull)
rsync -a --exclude .git ~/ai-sdlc-kit-source/ ./ai-sdlc-kit-new/
python3 ai-sdlc-kit-new/setup.py update
```

### What happens

- `.ai-sdlc/kit` is replaced by the newer copy, and the copied folder (`ai-sdlc-kit-new/`) disappears: it was moved there.
- Your choices stay: name, roles, language, git comfort, session summary, skills added or left out. Files you never edited are refreshed.
- A file **you edited** is kept as it is. If the kit's version of it changed, the new one is put next to it as `<file>.kit-new`, and the summary says so; otherwise it says there is nothing to compare.
- An **older** copy is refused and nothing changes: *"This copy is older (0.4.0) than the kit set up here (0.4.1). Nothing was changed."*
- A copy **outside** the repo is refused: *"Copy the newer kit folder into the repo first; it is at …"*
- `git status` stays clean.

Example output, with one edited file:

```text
$ python3 ai-sdlc-kit-new/setup.py update
Updated to AI-SDLC 0.9.1 for Ana: Product Owner, QA · English.
- Moved ai-sdlc-kit-new into .ai-sdlc/kit (replaced 0.9.0).
- Hidden from git: .ai-sdlc/ and every ai-sdlc-* file.
- Wrote 1 file(s): .github/instructions/ (1)
- Kept your edit in .github/instructions/ai-sdlc-po.instructions.md. The kit's newer copy is next to it as .github/instructions/ai-sdlc-po.instructions.md.kit-new, for you to compare.
- Skills: … · git: hidden · session summary: on
- Connectors for your roles: jira, confluence, jama, jenkins (say 'connect jira')
Check: all good.
$ git status --short
$
```

> **Same version number?** If the newer copy has the same number as your kit (common when you take the latest `main`), `check` says *"Another copy of the kit (same version …) is in <folder>. If you copied it in to update, say "update the kit"; otherwise delete it."* Running `update` from it works, and adds whatever the newer copy has.

### Compare a `.kit-new` file with your edited one, and choose

See the difference:

```bash
F=.github/instructions/ai-sdlc-po.instructions.md        # the file the summary named
diff "$F" "$F.kit-new"                                   # or: code --diff "$F" "$F.kit-new"
```

`code --diff` opens a side-by-side view in VS Code. Or say to Copilot: *"compare my ai-sdlc-po instructions with the .kit-new and explain the differences"*.

Then choose:

- **Take the kit's version** (recommended). Move any personal lines to your [personal notes](#7-personal-notes-and-skills) first, so you keep them. Then:

  ```bash
  mv "$F.kit-new" "$F"
  python3 .ai-sdlc/kit/setup.py change          # no options: records the file; check is clean again
  ```

  Until you run `change`, `check` reports `missing:<file>.kit-new`. That is expected.
- **Keep your version.** Leave both files as they are. The `.kit-new` file is hidden from git and harmless. If you delete it, `check` reports it as `missing:`, and the next `change` or `update` puts it back. To keep your own rules without this, put them in your personal notes and take the kit's version.

---

## 3. Connect a tool

Copilot can **read** Jira, Confluence, Bitbucket (Data Center), Jama and Jenkins for you. The connectors only read: nothing is created, changed or posted in those tools.

> **Never paste a token or password into the chat.** Copilot never needs one. If one ends up in a chat anyway, revoke it in the tool, create a new one, and save it with `connect` yourself.

### Run `connect` yourself, in a terminal

**(a) Copilot:** say **"connect Jira"**. Copilot tells you whether it is already connected and gives you the command. It does not run it for you, because the command asks for your login.

**(b) Terminal:** in a terminal on the VM (**Terminal → New Terminal**), in your repo:

```bash
python3 .ai-sdlc/kit/setup.py connect jira
```

The names are `jira`, `confluence`, `bitbucket`, `jama` and `jenkins`. The command asks its questions one at a time. **Secrets do not show while you type or paste them.** That is normal: press Enter when done. It saves your answers and tests them with one read-only call:

```text
$ python3 .ai-sdlc/kit/setup.py connect jira
Connect Jira. Secrets are typed hidden and saved only on this computer, in /home/ana/.config/ai-sdlc/connectors/jira.json.
Jira URL, e.g. https://jira.example.com or https://example.atlassian.net: https://jira.example.com
API token (Cloud) or personal access token (Data Center):
Only if your company inspects TLS traffic; a PEM file path.
CA bundle file for your company's certificates (Enter to skip):
Saved Jira (Data Center) at https://jira.example.com in /home/ana/.config/ai-sdlc/connectors/jira.json.
Test: OK: signed in to jira.example.com as Ana Pop.
```

Run it again at any time to change something. Press Enter to keep a saved value.

### Connect your role's tools in one go

At the end of the onboarding Copilot offers this; say "not now" and it does not ask again. You can run it at any time, **in your own terminal**:

```bash
python3 .ai-sdlc/kit/setup.py connect --suggested
```

It goes through the tools your roles usually use (the "Connectors for your roles" line of the setup summary), **one at a time**, leaving out the ones already connected. For each it asks `y` (connect it now, with exactly the questions of `connect <name>`), `s` (skip this one) or `a` (skip all the rest). **Pressing Enter skips.** Then it offers the other tools: type a name to connect it, or press Enter to finish.

```text
$ python3 .ai-sdlc/kit/setup.py connect --suggested
Connect the tools your roles usually use, one at a time. Logins are typed here, secrets hidden, and saved only on this computer.
Connect Jira now? [y = yes, s = skip, a = skip all the rest; Enter = skip]: y
Connect Jira. Secrets are typed hidden and saved only on this computer, in /home/ana/.config/ai-sdlc/connectors/jira.json.
…
Test: OK: signed in to jira.example.com as Ana Pop.
Connect Confluence now? [y = yes, s = skip, a = skip all the rest; Enter = skip]: s
Connect another tool? Available: bitbucket, jama, jenkins (type its name; Enter = done):
Connected: jira.
Skipped: confluence. They are no longer suggested; connect one any time with python3 .ai-sdlc/kit/setup.py connect <name>
```

**Skips are remembered** for this repo: the setup summary shows the tool as "(skipped)" and stops suggesting it, and `connections` shows "not connected, skipped". Running `connect --suggested` again asks about skipped tools again, and `connect <name>` clears that tool's skip. Without a terminal (for example, if Copilot tried to run it) it asks nothing and changes nothing.

### What each tool asks for, and where to create the token

| Tool | It asks for | Where to create the token |
|---|---|---|
| **Jira** | URL; then, for Cloud (`*.atlassian.net`) only, your account email; then a token | **Data Center:** your profile picture → **Profile** → **Personal Access Tokens** → Create token. **Cloud:** id.atlassian.com → **Security** → **API tokens** → Create API token. |
| **Confluence** | URL (Cloud: `https://<site>.atlassian.net/wiki`); for Cloud your email; a token | Same as Jira: a personal access token in your Confluence profile (Data Center), or an Atlassian API token (Cloud). |
| **Bitbucket** (Data Center) | URL, an HTTP access token | Your profile picture → **Manage account** → **HTTP access tokens** → Create token. *Read* permission is enough. A project or repository token also works. Bitbucket Cloud (`bitbucket.org`) is not supported. |
| **Jama** | URL, API client ID, API client secret | An **OAuth API client**: in Jama, your profile → **Set API credentials** (or ask your Jama admin). Copy the secret when it is shown; you cannot see it again. |
| **Jenkins** | URL, your Jenkins user name, an API token | Your name (top right) → **Security** (older Jenkins: **Configure**) → **API Token** → Add new token. |

Every tool also asks for an optional **CA bundle**. Press Enter to skip it, unless you are on a company network that needs one (see below).

Use the URL you open in the browser, without a page path: `https://jira.example.com`, not `…/browse/ABC-1`.

### Test, list and disconnect

```bash
python3 .ai-sdlc/kit/setup.py connect jira --test     # test the saved login; asks nothing
python3 .ai-sdlc/kit/setup.py connections             # what is connected; never shows a secret
python3 .ai-sdlc/kit/setup.py disconnect jira         # what it would delete; deletes nothing
python3 .ai-sdlc/kit/setup.py disconnect jira --yes   # delete the saved login
```

```text
$ python3 .ai-sdlc/kit/setup.py connect jira --test
Jira: OK: signed in to jira.example.com as Ana Pop.
$ python3 .ai-sdlc/kit/setup.py connections
Connectors (saved in /home/ana/.config/ai-sdlc/connectors):
- bitbucket: not connected (python3 .ai-sdlc/kit/setup.py connect bitbucket)
- confluence: not connected (python3 .ai-sdlc/kit/setup.py connect confluence)
- jama: not connected (python3 .ai-sdlc/kit/setup.py connect jama)
- jenkins: not connected (python3 .ai-sdlc/kit/setup.py connect jenkins)
- jira: https://jira.example.com · Data Center · user ana · last test OK 2026-10-08T12:30:26Z · from file
$ python3 .ai-sdlc/kit/setup.py disconnect jira --yes
Removed the saved Jira connection.
```

Copilot can run `--test`, `connections` and `disconnect` for you: say *"test my Jira connection"*, *"what is connected?"* or *"disconnect Jira"*. For `disconnect`, Copilot asks you first and adds `--yes` only after you say yes.

Your login is saved **on this computer only**, outside every repo: `~/.config/ai-sdlc/connectors/<name>.json` (folder readable only by you; file mode 600). All your repos share it, so you connect once per computer, not once per repo.

> **Working as root?** Then "you" is the root account: the login goes to root's home folder, and everyone who uses root on this computer (for example, everyone who logs in to a shared VM as root) can use it. `connect` warns you when it runs as root. If you can, log in as your own user and connect there; otherwise use a token with read access only, and disconnect when you are done.

### Corporate network: proxy and company certificates

- **Proxy.** If the VM reaches the internet or intranet through a proxy, set it in `~/.bashrc` (ask IT for the address):

  ```bash
  export HTTPS_PROXY=http://proxy.example.com:8080
  export HTTP_PROXY=http://proxy.example.com:8080
  export NO_PROXY=localhost,127.0.0.1,.example.internal     # hosts reached directly
  ```

  Then open a new terminal. If Copilot still does not see the proxy, close the VS Code remote window and connect again.
- **Company certificates (CA bundle).** Some companies inspect TLS traffic with their own certificate authority. You then get a *"TLS certificate … could not be verified"* error. Get the company's CA bundle as a **PEM file** from IT, save it, for example as `~/certs/company-ca.pem`, and either give that path when `connect` asks for the CA bundle, or add `export AI_SDLC_CA_BUNDLE=~/certs/company-ca.pem` to `~/.bashrc`. The bundle is *added* to the system's certificates. Certificate checks are never switched off.

---

## 4. Use the connectors

Once a tool is connected, ask Copilot in plain words. It reads the data, gives a link for every item it uses, and tells you when it found nothing. It never creates or changes anything in the tool.

### Example questions by role

| Role | Ask Copilot |
|---|---|
| Developer | "Which Jira issues are assigned to me and not done?" · "Show the open pull requests in PRJ/app and summarise PR 42 with its comments." · "Why did the last build of team/app/main fail? Show the failing tests." |
| QA | "List the bugs in project ABC updated this week." · "Show Jama item 1001 and what it is traced to." · "Which test runs failed in test cycle 77?" · "Show the failed tests of the last build of team/app/main." |
| Product Owner / Product Manager | "Summarise ABC-123 with its linked issues." · "Find the Confluence pages about 'release plan' in space ENG." · "Find Jama requirements that mention 'export'." |
| Scrum Master | "Which sprints are active on board 42?" · "List the open issues of the current sprint by status." · "Summarise the retrospective page 123456." |

### The same in the terminal

Copilot runs these commands. You can run them too. Add `--json` for structured output, as Copilot uses it; leave it off for plain text. To list every command, run `python3 .ai-sdlc/kit/connectors.py`.

```bash
K=.ai-sdlc/kit       # shorthand used below
```

**Jira**

```bash
python3 $K/connectors.py jira whoami
python3 $K/connectors.py jira search "assignee = currentUser() AND statusCategory != Done" --json
python3 $K/connectors.py jira search "project = ABC AND type = Bug ORDER BY updated DESC" --limit 20
python3 $K/connectors.py jira issue ABC-123 --links --changelog --json
python3 $K/connectors.py jira sprints 42 --state active
```

**Confluence**

```bash
python3 $K/connectors.py confluence page 123456 --json            # the number in the page's URL
python3 $K/connectors.py confluence search "release plan" --space ENG
python3 $K/connectors.py confluence search 'space = ENG AND title ~ "runbook"' --json
```

**Bitbucket** (Data Center)

```bash
python3 $K/connectors.py bitbucket prs PRJ/repo --json                  # open PRs
python3 $K/connectors.py bitbucket prs PRJ/repo --state MERGED --limit 10
python3 $K/connectors.py bitbucket pr PRJ/repo/42 --comments --diff --json
python3 $K/connectors.py bitbucket branches PRJ/repo --filter feature
```

**Jama**

```bash
python3 $K/connectors.py jama item 1001 --json                          # the item's API id
python3 $K/connectors.py jama search "export" --project 5
python3 $K/connectors.py jama relationships 1001 --direction down
python3 $K/connectors.py jama testruns --cycle 77 --json                # or --plan <id>
```

**Jenkins**

```bash
python3 $K/connectors.py jenkins job team/app/main
python3 $K/connectors.py jenkins build team/app/main last --json        # or a number, lastSuccessful, lastFailed
python3 $K/connectors.py jenkins tests team/app/main lastFailed         # --all: every test case
```

Real output (plain text, then `--json`):

```text
$ python3 .ai-sdlc/kit/connectors.py jira search "assignee = currentUser() AND statusCategory != Done"
- ABC-1  https://jira.example.com/browse/ABC-1
- ABC-2  https://jira.example.com/browse/ABC-2
(2 shown)
$ python3 .ai-sdlc/kit/connectors.py jira search "project = ABC" --json
{
  "connector": "jira",
  "command": "search",
  "source": "https://jira.example.com",
  "items": [
    {
      "key": "ABC-1",
      "summary": "Login fails on Safari",
      "type": "Bug",
      "status": "Open",
      "assignee": "Ana Pop",
      …
      "url": "https://jira.example.com/browse/ABC-1"
    },
    …
  ],
  "count": 2,
  "truncated": false
}
```

`"truncated": true` means more items exist: add `--limit` with a higher number (up to 1000). Exit codes: `0` OK, `1` an error from the tool or the network (the message says what to do), `2` a wrong command or argument, `3` not connected yet.

---

## 5. Change your preferences

**(a) Copilot:** say **"change my preferences"** and say what you want: *"answer me in German"*, *"add the dev role"*, *"stop doing git for me"*, *"turn off the session summary"*, *"leave out the drawio skill"*, *"add the brainstorming skill"*, *"add the javafx skill"*.

**(b) Terminal:** `python3 .ai-sdlc/kit/setup.py change` with one or more of these options. Only the affected files change.

| You want | Option |
|---|---|
| another name | `--name "Ana Pop"` |
| other roles | `--roles po,sm` (the **full** new list) |
| another language | `--lang de` (`en`, `ro` or `de`) |
| git done for you, or not | `--git-comfort hidden` (Copilot does git in plain words), `guided` (does it, explains, asks before commit and push), `git-native` (you drive git), or `default` (your roles decide) |
| the one-line session summary on or off | `--rituals status` (on), `none` (off), or `default` (your roles decide). The short check at the start of a session always runs. |
| an extra skill | `--add-skill skill-creator` |
| a skill left out | `--drop-skill drawio` |

`--add-skill` and `--drop-skill` can be repeated. The skill names are the folder names in `.ai-sdlc/kit/template/.claude/skills/`, such as `drawio` (`ai-sdlc-drawio` works too); a wrong name, for either option, lists the available ones. `git-verbs` cannot be added.

```text
$ python3 .ai-sdlc/kit/setup.py change --lang de --git-comfort guided --rituals none --add-skill skill-creator --drop-skill drawio
Updated AI-SDLC 0.9.0 for Ana: Product Owner, QA · German (Deutsch).
- Hidden from git: .ai-sdlc/ and every ai-sdlc-* file.
- Wrote 3 file(s): .agents/skills/ (1 in 1 skill), .ai-sdlc/ (1), .github/instructions/ (1)
- Removed 6 file(s) no longer needed: .agents/skills/ (6 in 1 skill)
- Skills: … · git: guided · session summary: off
- Connectors for your roles: jira, confluence, jama, jenkins (say 'connect jira')
Check: all good.
```

### Skill suggestions and the other skills

**(a) Copilot:** say **"recommend skills"** (which skills fit this repo?) or **"show me the other skills"** (everything else you can add). Copilot lists them and asks once; say *"take javafx and java-junit"*, *"all of them"*, *"none"* or *"add the javafx skill"*. Nothing changes without your yes.

**(b) Terminal:** `recommend` reads the repo's files and changes nothing:

```text
$ python3 .ai-sdlc/kit/setup.py recommend
Skill suggestions for this repo (from its files; nothing is changed yet):
1. add:110-java-maven-best-practices — add ai-sdlc-110-java-maven-best-practices: this repo builds with Maven (pom.xml).
2. add:java-code-review — add ai-sdlc-java-code-review: this repo has Java code (pom.xml).
3. add:java-junit — add ai-sdlc-java-junit: this repo has Java code (pom.xml).
4. add:javafx — add ai-sdlc-javafx: this repo uses JavaFX (pom.xml).
5. add:maven-via-artifactory — add ai-sdlc-maven-via-artifactory: this repo downloads packages; they come only through the company mirror (pom.xml).
To take them all: python3 .ai-sdlc/kit/setup.py change --add-skill 110-java-maven-best-practices --add-skill java-code-review --add-skill java-junit --add-skill javafx --add-skill maven-via-artifactory
To take some: the same command with only those skills.
To say no to the rest: python3 .ai-sdlc/kit/setup.py recommend --decline <skill names or ids, comma-separated>  (or --decline all)
```

- `recommend --all` adds "Other skills you can add": every skill you do not have, grouped (Java, Go, React and web, Quality and security, Ways of working, Role playbooks, Other), one line each, and the `change --add-skill` command.
- `recommend --decline javafx` (a skill name, or the id `add:javafx`; or `--decline all`) remembers a no in `.ai-sdlc/state.json`; that suggestion is not offered again by setup or update, and `recommend` lists it under "Declined earlier". Taking it later with `change --add-skill javafx` clears the no.
- `recommend --json` prints `{"suggestions": [...], "others": [...]}`.

Suggestions depend only on the repo and your roles, never on your home folder: two people with the same roles in the same repo get the same list. Setup, update and a change of roles add one line when there are open suggestions: `- Skill suggestions for this repo: 5 (say "recommend skills")`.

Your current choices are in `.ai-sdlc/USER.md`. Read it, but do not edit it by hand: use `change`. `change` with no options repairs the setup: it puts back missing files and hides them again.

---

## 6. Check your setup

**(a) Copilot:** say **"check the kit"**. Copilot also runs the short check at the start of each session and mentions anything it finds. In the Copilot CLI the kit's session hook (`.github/hooks/ai-sdlc-session.json`, hidden from git) runs it before your first message, in a folder you trusted when the CLI asked; elsewhere Copilot runs it because the instructions say so.

**(b) Terminal:**

```bash
python3 .ai-sdlc/kit/setup.py check           # full list, one finding per line, with its id
python3 .ai-sdlc/kit/setup.py check --quiet   # one line, as at the start of a session
python3 .ai-sdlc/kit/setup.py check --quiet --hook   # the same line as JSON, for the session hook
```

```text
$ python3 .ai-sdlc/kit/setup.py check --quiet
AI-SDLC 0.9.0 · roles: PO, QA · en · ok
$ python3 .ai-sdlc/kit/setup.py check
Check: 3 to look at:
- [missing:.github/instructions/ai-sdlc-qa.instructions.md] .github/instructions/ai-sdlc-qa.instructions.md is missing.
- [unknown:.github/instructions/ai-sdlc-extra.instructions.md] .github/instructions/ai-sdlc-extra.instructions.md looks like a kit file, but the kit did not write it.
- [team-agents-md] The team has its own AGENTS.md. Copilot reads it together with the kit's instructions.
- Connectors for your roles: jira, confluence, jama, jenkins (say 'connect jira')
```

`check` also names the tools your roles usually connect to, marking the ones connected or skipped.

**Notices and problems.** `team-…`, `skill-clash:…` and `kit-copy:…` are *notices*: something to read, nothing is broken. With notices only, `check` says *"Check: nothing to fix; N notice(s) to read:"* and exits `0`. Every other finding is a *problem* to fix, and `check` exits `1`.

| Finding id | What it means | What to do |
|---|---|---|
| `not-set-up` | The kit is not set up in this repo. | [First-time setup](#1-first-time-setup-in-a-repo). |
| `missing:<file>` | A file the kit placed is gone. | `python3 .ai-sdlc/kit/setup.py change` (no options) puts it back. After taking a `.kit-new`, this is expected until you run `change`. |
| `unknown:<file>` | A file named like the kit's (`ai-sdlc-*`) that the kit did not write, for example one Copilot made. Your personal notes and personal skills are never reported. | Look at it. Delete it if you don't need it, or rename it to a personal file. |
| `unexcluded:<file>` | A kit file that git does not hide (it could end up in a commit). | `python3 .ai-sdlc/kit/setup.py change` (no options) hides it again. |
| `kit-copy:<folder>` | Another kit folder in the repo that git does not hide. *"A newer kit (…) is waiting"*: it is newer. *"Another copy of the kit (same version …)"*: it has your version. Otherwise it is older. | Newer: [update](#2-update-the-kit-to-a-newer-version). Same version: update if you copied it in for that, otherwise delete the folder. Older: delete the folder. |
| `stale-kit` | The kit folder and your setup disagree on the version (an update did not finish, or the kit folder was replaced by hand). | `python3 .ai-sdlc/kit/setup.py update` |
| `team-agents-md` | The team has its own `AGENTS.md`; Copilot reads it together with the kit's files. | Information only. Ask Copilot to look for real contradictions; the team's rule wins. Then acknowledge it (below). |
| `team-copilot-instructions` | The same, for the team's `.github/copilot-instructions.md`. | As above. |
| `team-instructions:<file>` | A team instructions file applies to the same files as the kit's. | As above. |
| `skill-clash:<folder>` | The team has a skill with the same name as one the kit adds; Copilot sees both. | As above. |

To acknowledge a `team-…` or `skill-clash:…` warning you have read: `python3 .ai-sdlc/kit/setup.py ack team-agents-md` (any number of ids). It comes back only if that team file changes. Or say to Copilot: *"I've seen the AGENTS.md warning"*.

---

## 7. Personal notes and skills

Things you want Copilot to remember about how *you* work go into two places. Both are yours: hidden from git like the kit's files, but the kit never changes or deletes them.

| What | Where |
|---|---|
| Personal notes: one-line habits, recurring instructions, style | `.github/instructions/ai-sdlc-personal.instructions.md` |
| Personal skills: a multi-step procedure you repeat | `.agents/skills/ai-sdlc-personal-<name>/SKILL.md` |

**(a) Copilot:** at the end of a useful chat, say **"deceneus"** or *"what should you remember from this chat?"*. The `ai-sdlc-deceneus` skill proposes the exact text and where it goes, and writes **only after you approve**. It also sends kit preferences (language, roles, …) to `change` instead of a file.

**(b) Terminal:** edit the files yourself. The notes file needs this header so it applies everywhere:

```markdown
---
applyTo: '**'
---
# Personal notes

- Answer in short bullet points.
```

`update` and `change` leave these files alone, and `check` never reports them. `remove` keeps them and lists them (see below). They belong to this repo's working copy; to use them in another repo, copy them there.

---

## 8. Remove the kit from a repo

**(a) Copilot:** say **"remove the kit"**. Copilot tells you what would be removed and kept, and asks you to confirm. It removes nothing until you say yes.

**(b) Terminal:** two steps. Without `--yes`, `remove` changes nothing: it says what it would do and asks. With `--yes` it removes.

```bash
python3 .ai-sdlc/kit/setup.py remove           # what it would do; changes nothing
python3 .ai-sdlc/kit/setup.py remove --yes     # remove it
```

```text
$ python3 .ai-sdlc/kit/setup.py remove
Nothing was removed yet. remove takes out 27 kit file(s) you never edited, the kit folder .ai-sdlc/kit and your settings.
Kept, because you edited them: .github/instructions/ai-sdlc-qa.instructions.md
Kept, your personal notes and skills: .github/instructions/ai-sdlc-personal.instructions.md, .agents/skills/ai-sdlc-personal-standup/SKILL.md
Your connector logins stay.
Remove the kit from this repo? Only after a yes: python3 .ai-sdlc/kit/setup.py remove --yes
$ python3 .ai-sdlc/kit/setup.py remove --yes
Removed the kit: 27 file(s), the kit folder and your settings.
Kept, because you edited them (git now shows them; delete them if you don't need them): .github/instructions/ai-sdlc-qa.instructions.md
Kept your personal notes and skills, still hidden from git: .github/instructions/ai-sdlc-personal.instructions.md, .agents/skills/ai-sdlc-personal-standup/SKILL.md. If you set the kit up again it uses them; delete them if you don't need them.
```

| Removed | Kept |
|---|---|
| every kit file you never edited | files you edited (listed) |
| `.ai-sdlc/kit`, `USER.md`, `state.json` | your personal notes and personal skills (listed), still hidden from git |
| the kit's block in `.git/info/exclude` (a two-line entry stays while you keep personal notes or skills) | your connector logins in `~/.config/ai-sdlc/connectors/` |

Edited kit files are no longer hidden, so `git status` shows them. Delete them, or move them somewhere safe, before you commit. Your personal notes and skills stay hidden by a two-line entry in `.git/info/exclude`; a later setup uses them again, and once you delete them, the next setup and remove take that entry away too. With nothing kept, the repo is back to exactly how it was before setup: *"The repo is back to how it was before setup."*

**Connector logins are not removed.** They live in your home folder and are shared by all your repos. To delete them, run this **before** `remove`, while the kit is still there, for each connected tool:

```bash
python3 .ai-sdlc/kit/setup.py connections             # which ones are saved
python3 .ai-sdlc/kit/setup.py disconnect jira --yes   # repeat per tool
```

Already removed the kit? Run `disconnect` from the kit in another repo or from your kit clone (`python3 ~/ai-sdlc-kit-source/setup.py disconnect jira --yes`), or delete the file: `rm ~/.config/ai-sdlc/connectors/jira.json`. Revoke the token in the tool too if you no longer need it.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `invalid choice: 'connect' (choose from setup, change, update, check, ack, remove)` | Your kit is older than the command. | [Update the kit](#2-update-the-kit-to-a-newer-version): get the latest kit, copy it in without `.git`, run `python3 <copy>/setup.py update`. |
| `setup.py: error: unrecognized arguments: jira` (after `setup.py setup jira`) | `setup` is the one-time setup, not the connect command. | `python3 .ai-sdlc/kit/setup.py connect jira` |
| `A kit is already set up in this repo (.ai-sdlc/kit)` | You ran `setup` with a newer copy. | Run `update` instead: `python3 <copy>/setup.py update`. |
| `This copy is older (…) than the kit set up here (…)` | The copy you used is older than your kit. | Nothing changed. Delete that copy; get the latest one. |
| `This kit copy is incomplete (missing …)` or `The kit folder .ai-sdlc/kit is incomplete (missing …)` | Some files did not come along when the kit was copied (an interrupted copy or unzip, or only part of the folder). | Nothing changed. Copy the whole kit folder into the repo again, without `.git` (`rsync -a --exclude .git <kit>/ ./ai-sdlc-kit-new/`), and run `setup` or `update` from that copy. |
| `AI-SDLC stopped on an unexpected problem: …` (exit code 4) | Something the kit did not expect, such as a full disk or a file it could not read. | Run the command it names (for an update: `python3 .ai-sdlc/kit/setup.py update`). If it happens again, share the message and the output of `check` with the kit owner. |
| `Copy the newer kit folder into the repo first` | The copy is outside the repo. | `rsync -a --exclude .git <kit>/ ./ai-sdlc-kit-new/`, then run `ai-sdlc-kit-new/setup.py update`. |
| `Git refuses to work in <folder> (git says: fatal: detected dubious ownership …)` | The repo folder belongs to another user on this computer (for example, it was made as root or by another account), so git will not read it. The kit stops rather than leave its files visible to git. | Nothing changed. Ask IT to give the folder to your user. If you trust the folder, run the command the message names: `git config --global --add safe.directory <folder>`. |
| `python3: command not found`, or `AI-SDLC needs Python 3.9 or newer` | Python is missing or older than 3.9 (`python3 --version`). | Ask IT to install Python 3.9 or newer on the VM. Nothing was changed. |
| `git status` shows kit files | (1) A kit copy you put in is waiting for `setup` or `update`. (2) After `remove`: files you edited were kept. (3) `check` reports `unexcluded:`. (4) Someone ran `git add -f`. | (1) Finish the setup or update, or delete the copy. (2) Delete or move them. (3) `python3 .ai-sdlc/kit/setup.py change`. (4) `git restore --staged <file>`; never commit them. |
| `The TLS certificate of <host> could not be verified` | Your company inspects TLS traffic with its own certificate authority. | Get the CA bundle (PEM) from IT, then run `connect <name>` again and give its path, or set `AI_SDLC_CA_BUNDLE`. See [Corporate network](#corporate-network-proxy-and-company-certificates). |
| `The proxy … asks for credentials (407 Proxy Authentication Required)` | The proxy needs a login. | Ask IT how to set the proxy for command-line tools on the VM (often `HTTPS_PROXY=http://user:password@proxy:port`, or a proxy that does not need a login). |
| `The proxy … refused the connection` / `could not be found`, or a `timeout` | Wrong proxy address, VPN off, or the tool's host must bypass the proxy. | Check `HTTPS_PROXY` and the VPN. For an internal host, add it to `NO_PROXY`. |
| `The name <host> could not be found (DNS)` | Wrong URL, or you need the VPN. | Check the URL in `connections`; connect the VPN. |
| `401 Unauthorized from <host>` | The token is wrong or expired, or the wrong user or email. For Jama: the client ID or secret. | Create a new token and run `connect <name>` again. Atlassian Cloud needs your **email** plus an API token; Data Center needs a personal access token. |
| `403 Forbidden from <host> for <path>` | You are signed in, but this account may not read it. | Ask for read access. After several failed logins, some servers want one sign-in in the browser first. |
| `404 Not Found from <host> for <path>` | The id, key or path is wrong, or your account cannot see it. Or the URL in `connect` has an extra path. | Check the id (Confluence page id, Jama API id, `PRJ/repo`, Jenkins job path). Check the saved URL with `connections`. |
| `<Tool> is not connected` (exit code 3) | No saved login for that tool. | `python3 .ai-sdlc/kit/setup.py connect <name>`, in your own terminal. |
| `connect asks for secrets, so it runs only in your own terminal` (exit code 2; the same for `connect --suggested`) | `connect` was run through Copilot or a script, without a terminal. | Open a terminal (**Terminal → New Terminal**) and run it there yourself. For scripts and CI, `python3 .ai-sdlc/kit/setup.py connect --help` names the environment variables to set instead. |
| `Bitbucket Cloud is not supported yet` | The URL is `bitbucket.org`. | Only Bitbucket Data Center is supported. |
| The document skills (Word, Excel, PowerPoint, PDF) cannot install their library: `ensurepip is not available`, or `python3 -m venv` fails | The `python3-venv` package is missing on the VM. | Ask IT to install `python3-venv`. The skills install into `~/.ai-sdlc/venv` only, and only with your consent. |
| The document skills: `pip` cannot reach the package index | A company proxy or internal package mirror is needed. | Ask IT for the pip proxy or index settings (for example `HTTPS_PROXY`, or `pip config set global.index-url <mirror>`), then try again. |
| The LikeC4 skill cannot validate or export a `.c4` model: `npx` cannot reach the npm registry, or Node is not installed | The `likec4` CLI comes from npm, which the VM may block. | The `.c4` file is still kept. Validate and export with the LikeC4 VS Code extension, or ask IT for npm registry access. Copilot asks before it downloads the CLI. |
| Copilot says it cannot find `ONBOARDING.md`, says the onboarding is already done, or does something else when you say "do the onboarding" | Copilot did not look in the kit folder, or read another file. Its file search may skip folders that git ignores, such as `.ai-sdlc/kit/` after setup. | Point it there: *"follow ai-sdlc-kit/ONBOARDING.md"* before setup (your folder name), or *"follow .ai-sdlc/kit/ONBOARDING.md"* after setup. It is the `ONBOARDING.md` next to `setup.py`. |
| `There is no skill <name>. Available: …` | A wrong skill name in `--add-skill` or `--drop-skill`. | Use a name from the list it prints. |
| `The kit is not set up in this repo yet` | `change`, `update`, `ack` or `remove` in a repo without the kit. | Check you are in the right repo (`git rev-parse --show-toplevel`), or do the [first-time setup](#1-first-time-setup-in-a-repo). |

Still stuck? Run `python3 .ai-sdlc/kit/setup.py check` and `python3 .ai-sdlc/kit/setup.py connections`, and share the output with the kit owner. It never contains a secret. For connector problems, `AI_SDLC_DEBUG=1 python3 .ai-sdlc/kit/connectors.py <name> whoami` also prints each request, with the login hidden.
