# Provenance: deceneus

| | |
|---|---|
| Upstream repo | https://github.com/danemil/deceneus (the kit owner's own, public) |
| Path | `skills/deceneus/SKILL.md` |
| Commit | `01de547d6dc548ad8d300870360993e168c424ae` (2026-10-08) |
| Taken | 2026-10-08 |
| Licence | MIT, © 2026 Emil Dan; the upstream `LICENSE` is in this folder |

## Local modifications

The core is unchanged: harvest the conversation, check what already exists, verify every command and path, propose the exact text with a "deliberately NOT adding" list, and write only what is approved. Adapted from one assistant's configuration files to the kit's personal, git-hidden files:

- **Description** names the kit's destinations (kit preferences, personal notes, personal skills) instead of memory, rules files and settings, and drops the slash-command trigger. The "what should be remembered from this chat?" style triggers stay, plus "what to save from this session".
- **Team files are off limits.** A new paragraph: never propose editing `AGENTS.md`, `.github/copilot-instructions.md`, `.github/instructions/` files not named `ai-sdlc-*`, `.claude/` or `.vscode/`.
- **Step 2 (check what exists)** reads `.ai-sdlc/USER.md`, the `ai-sdlc-*.instructions.md` files and the `ai-sdlc-*` skills, instead of the assistant's own config files.
- **Step 3 (destinations)** has exactly three, all personal and hidden from git: kit preferences through `setup.py change` (never by editing `USER.md`); personal notes in `.github/instructions/ai-sdlc-personal.instructions.md` (with `applyTo: '**'`); personal skills in `.agents/skills/ai-sdlc-personal-<name>/`. Permissions, environment variables and editor settings are not saved. The kit's own `ai-sdlc-*` files are never written.
- **Steps 5 and 6** show and run the exact `setup.py change` command for a preference.
- **Anti-patterns** refer to the personal notes, and add "proposing an edit to a team file or a kit file".

The kit treats the personal notes file and `ai-sdlc-personal-*` skills as the person's own: `check` does not report them as unknown, and `remove` keeps and lists them.

Setup prefixes the name to `ai-sdlc-deceneus` when it places the skill.
