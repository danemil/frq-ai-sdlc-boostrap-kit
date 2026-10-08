# AI-SDLC Bootstrap Kit

A **personal AI setup for everyone on a software team**: developers, QA, architects, engineering managers, product owners, product managers and scrum masters. Each person gets GitHub Copilot instructions and skills that fit their role, their language and how they like to work, inside the shared repo, without committing anything to it.

## Set it up: copy, then "do the onboarding"

1. Copy this kit folder anywhere into your repo (a GitHub ZIP or a colleague's copy; any folder name).
2. Open the repo in VS Code and start Copilot Chat in Agent mode, or run `copilot` in a terminal.
3. Say **"do the onboarding"**. Copilot finds the kit's [`ONBOARDING.md`](./ONBOARDING.md) and follows it.
4. Answer three questions: your name, your role(s), and your language (English, Romanian or German).

Copilot tells you what it set up. `git status` shows nothing: every file the kit adds is hidden from git through `.git/info/exclude`, so it never reaches the shared history. Setup is once per repo.

Afterwards, say **"change my preferences"**, **"update the kit"** (after copying a newer kit folder in), **"check the kit"** or **"remove the kit"** at any time.

You need Python 3.9 or newer. Copilot checks it first and tells you who to ask if it is missing.

## What ends up in your repo

```
<repo>/
├── .ai-sdlc/
│   ├── kit/            this kit folder, moved here by setup (needed for updates)
│   ├── USER.md         your name, roles, language and preferences
│   └── state.json      kit version, your choices, the files placed and their fingerprints
├── .github/
│   └── instructions/ai-sdlc-*.instructions.md   a core brief plus one file per role
└── .agents/skills/ai-sdlc-*/                    your skills (each a whole folder), prefixed so names cannot clash
```

The kit never creates or edits `AGENTS.md`, `.github/copilot-instructions.md` or `.vscode/settings.json`: the team may own them. Copilot reads the team's files and the kit's `ai-sdlc-*` files together. When they overlap, setup warns you (without blocking) and Copilot looks for real contradictions with you; where they disagree, the team's rule wins.

## Roles

| Role | Id | Skills | Git by default |
|---|---|---|---|
| Product Owner | `po` | `ai-sdlc-playbook-product` | done for you, in plain words |
| Product Manager | `pm` | `ai-sdlc-playbook-product` | done for you, in plain words |
| Scrum Master / Team Coach (SAFe) | `sm` | `ai-sdlc-playbook-sm` | done for you, explained |
| Developer | `dev` | `ai-sdlc-playbook-dev` | you drive git |
| QA | `qa` | `ai-sdlc-playbook-qa` | done for you, explained |
| Architect | `architect` | `ai-sdlc-playbook-architect` | you drive git |
| Engineering Manager | `em` | `ai-sdlc-playbook-em` | you drive git |

**Every role also gets eight skills** (the `core` pack, so a future role gets them too): `ai-sdlc-doc-word`, `ai-sdlc-doc-excel`, `ai-sdlc-doc-powerpoint` and `ai-sdlc-doc-pdf` (Word, Excel, PowerPoint and PDF files, written for this kit; libraries are installed only with your consent into `~/.ai-sdlc/venv`), `ai-sdlc-drawio` (draw.io diagrams, saved in `docs/diagrams/`), `ai-sdlc-visual-explainers` (a self-contained HTML explainer, saved in `docs/explainers/`), `ai-sdlc-visual-issue` (an issue or PR with a Mermaid diagram, for GitHub, Bitbucket or Jira) and `ai-sdlc-deceneus` (what to remember from a chat, saved only to your own hidden files after you approve). Leave one out with "change my preferences". Each skill's folder has a `PROVENANCE.md`.

Your own notes (`.github/instructions/ai-sdlc-personal.instructions.md`) and personal skills (`.agents/skills/ai-sdlc-personal-*/`) are hidden from git like the kit's files, but they are yours: the kit never changes them, and `remove` keeps and lists them.

You can hold several roles: their skills are combined, each keeps its own instructions file, and where their defaults differ the more guided one wins. Every role works under one rule: **a human validates everything** the AI writes or decides.

Role packs live in [`roles/`](./roles/), one folder per role (`role.json` + `instructions.md`). To add or change one, edit the folder and run `python3 scripts/personal/validate_packs.py`.

## Under the hood

Copilot runs the conversation from `ONBOARDING.md`; a small, tested, stdlib-only script does the file work: `python3 .ai-sdlc/kit/setup.py setup | change | update | check | ack | remove`. You never need to run it yourself.

It never uses the network, never runs a git command that changes anything (only `rev-parse`, `ls-files` and `check-ignore`), never writes to a path git tracks, and never touches a file it did not create. A file you edit is yours: `update` and `change` keep it and put the kit's newer copy next to it as `<file>.kit-new`; `remove` keeps it and tells you. After `remove`, the repo is byte for byte what it was before setup.

**Known limit:** `git add -f` can still add hidden files. The kit installs no git hooks, because they could clash with the team's own.

## Repository layout

```
├── README.md  ONBOARDING.md  setup.py  VERSION  CHANGELOG.md
├── roles/                 role packs: core + one folder per role
├── scripts/personal/      the code behind setup.py, its tests and the role-pack validator
├── template/              the skill library (.claude/skills) and the retired team-mode skeleton
├── scripts/install/       retired team-mode installer (its manifest code is reused)
└── docs/                  specification, roadmap (design and plan records), visuals, deck
```

## Verify locally

```bash
pip install "pyyaml>=6"                        # only the validators need it; setup.py does not
for t in scripts/personal/tests/test_*.py; do python3 "$t"; done
python3 scripts/personal/validate_packs.py
```

Kit CI ([`.github/workflows/ci.yml`](./.github/workflows/ci.yml)) also runs every template validator and test, and a `personal-e2e` job: a team repo with its own AI files, the kit copied in, setup, update and remove, ending byte-identical.

## Retired: team mode

Up to 0.3.x the kit was installed into a repo and committed there (`install.sh`, `scripts/install/`, the CI gates in `template/ci/` and `template/.github/workflows/`). Team mode is retired as of 0.4.0: those files stay in the repo as internal history and reused code, and are no longer offered or supported. See [`CHANGELOG.md`](./CHANGELOG.md).

## Contributing

Contributions are welcome. See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the workflow and [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) for community expectations. Security issues: please follow [`SECURITY.md`](./SECURITY.md) rather than opening a public issue.

## License

Released under the [MIT License](./LICENSE).
