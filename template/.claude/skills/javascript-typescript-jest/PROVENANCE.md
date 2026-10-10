# Provenance: javascript-typescript-jest

| | |
|---|---|
| Upstream repo | https://github.com/github/awesome-copilot |
| Path | `skills/javascript-typescript-jest` |
| Commit | `82701c24b99488536ca399ff4789a458b7a05db7` (2026-10-09) |
| Folder last changed in | `caab1f623bb6` (2026-02-24) |
| Taken | 2026-10-09 |
| Licence | MIT ("Copyright GitHub, Inc."); the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit (blob) | Changed? |
|---|---|---|
| `SKILL.md` | `skills/javascript-typescript-jest/SKILL.md` (`9552d7cb7b74`) | Yes, see below |
| `LICENSE` | `LICENSE` (`89bc5e962c99`) | No |

Not bundled: nothing; the upstream folder holds only `SKILL.md`. Upstream has no `NOTICE` file. The skill bundles no executable scripts.

## Local modifications

- **Description.** The frontmatter `description` keeps upstream's sentence and adds the trigger phrases: "write a Jest test", "test this function", "mock this module", "jest.mock", "snapshot test". The frontmatter has only `name` and `description`, as upstream; setup prefixes the name to `ai-sdlc-javascript-typescript-jest` when it places the skill.
- **Kit section.** A new section, "This kit's copy", before upstream's first heading ("Test Structure"), with the kit's rules: git only after asking, show before you change, packages only through the company mirror, and read the Jest version in `package.json` (Jest 29 and 30 differ in some defaults) and follow the repo's Jest config.
- **`## Practices` heading.** Upstream's first headings are `###`; a `## Practices` heading follows the kit section so they are not nested under it.

The line "Review snapshot changes carefully before committing" stays: it tells the AI to do nothing on its own (reviewed 2026-10-09).

## Updating

Take `SKILL.md` and `LICENSE` from a newer upstream commit, re-apply the changes above, re-run `scripts/personal/tests/test_stack_skills.py`, and update the commit, blobs and date here.
