# Provenance: react-testing-library

| | |
|---|---|
| Upstream repo | https://github.com/itechmeat/llm-code (branch `master`) |
| Path | `skills/react-testing-library` |
| Commit | `7ae8a005245770a0fa1e10337b2eb10174c5886b` (2026-09-23) |
| Folder last changed in | `5f18228abfde` (2026-09-04) |
| Taken | 2026-10-09 |
| Licence | MIT ("Copyright (c) 2026 itechmeat"); the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit (blob) | Changed? |
|---|---|---|
| `SKILL.md` | `skills/react-testing-library/SKILL.md` (`510f6bf61feb`) | Yes, see below |
| `references/api.md` | `skills/react-testing-library/references/api.md` (`546ef447810c`) | Yes, see below |
| `references/async.md` | `skills/react-testing-library/references/async.md` (`83d0e531fd56`) | No |
| `references/config.md` | `skills/react-testing-library/references/config.md` (`4176b5b7124e`) | Yes, see below |
| `references/debugging.md` | `skills/react-testing-library/references/debugging.md` (`1c2c7d0c373d`) | No |
| `references/queries.md` | `skills/react-testing-library/references/queries.md` (`9785ac474e9f`) | No |
| `references/user-events.md` | `skills/react-testing-library/references/user-events.md` (`6208ff5d6c7f`) | Yes, see below |
| `LICENSE` | `LICENSE` (`85df337d262b`) | No |

Not bundled: nothing; the upstream folder holds only `SKILL.md` and `references/`. Upstream has no `NOTICE` file. The skill bundles no executable scripts.

## Local modifications

- **Kit section.** A new section, "This kit's copy", before "Installation" in `SKILL.md`, with the kit's rules: git only after asking, show before you change, packages only through the company mirror, and "Jest only" (this copy is for Jest with `@testing-library/jest-dom`).
- **Installation (`SKILL.md`).** The `npm install --save-dev …` line is replaced: check `package.json` first and use the Testing Library packages it already has; to add one, ask first, and it comes through the company npm mirror (`.npmrc`). The React 19 note stays.
- **Installation (`references/user-events.md`).** The `npm install` code block is replaced with the same rule for `@testing-library/user-event`.
- **Jest only (`references/api.md`).** The last section (configuration for another test runner, from the `---` before it to the end) is removed, and `cleanup` is described as called automatically in Jest.
- **Jest only (`references/config.md`).** The last section (configuration for another test runner and its manual cleanup, from the `---` before it to the end) is removed, and so is the other runner's config snippet after the Jest `setupFilesAfterEnv` example.

The frontmatter (`name`, `description`, `metadata` with upstream's version and release date) is unchanged; setup prefixes the name to `ai-sdlc-react-testing-library` when it places the skill.

Reviewed and kept (2026-10-09): `errors.push(error)` and `recoverableErrors.push(error)` in `references/api.md` are code, not git steps; the "Testing Playground" browser extension in `references/debugging.md` is the person's choice, not an AI action.

## Updating

Take `SKILL.md`, `references/` and `LICENSE` from a newer upstream commit, re-apply the changes above (keep the copy free of other test runners' sections), re-run `scripts/personal/tests/test_stack_skills.py`, and update the commit, blobs and date here.
