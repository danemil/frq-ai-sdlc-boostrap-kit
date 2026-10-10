# Provenance: accessibility

| | |
|---|---|
| Upstream repo | https://github.com/addyosmani/web-quality-skills |
| Path | `skills/accessibility` |
| Commit | `afa8da942115f2961fdbfa80807ea0b232ff6c00` (2026-08-24) |
| Folder last changed in | `c6b06ad1285c` (2026-08-24) |
| Taken | 2026-10-09 |
| Licence | MIT ("Copyright (c) 2026 Addy Osmani"); the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit (blob) | Changed? |
|---|---|---|
| `SKILL.md` | `skills/accessibility/SKILL.md` (`22a244430f89`) | Yes, see below |
| `references/A11Y-PATTERNS.md` | `skills/accessibility/references/A11Y-PATTERNS.md` (`6d500efb3eb2`) | No |
| `references/WCAG.md` | `skills/accessibility/references/WCAG.md` (`a0bd65fa7494`) | No |
| `LICENSE` | `LICENSE` (`90715bb429f3`) | No |

Not bundled: nothing; the upstream folder holds only `SKILL.md` and `references/`. Upstream has no `NOTICE` file. The skill bundles no executable scripts.

## Local modifications

All in `SKILL.md`:

- **Kit section.** A new section, "This kit's copy", before "Evidence-led audit workflow", with the kit's rules: git only after asking, show before you change, packages only through the company mirror, and a pointer for desktop UI (this skill is about web pages; JavaFX screens go to `ai-sdlc-javafx`, if you have it).
- **No browser-automation tools.** In the audit workflow, steps 1 and 3 no longer name the Chrome DevTools tool server and its two tools; the steps themselves stay.
- **Fallback without downloads.** The "If the live tools are unavailable" sentence now says: use the browser's Lighthouse panel, or Lighthouse or axe if the project already has them (ask before installing anything).
- **Automated testing.** The paragraph and bash block that ran Lighthouse through `npx` and installed the axe CLI globally are replaced with: the browser's built-in Lighthouse panel, `lighthouse … --only-categories=accessibility` if it is installed, and `npx --no-install axe …` if `@axe-core/cli` is already in the project's devDependencies.
- **References list.** The "Web Quality Audit" link (`../web-quality-audit/SKILL.md`, a sibling skill upstream) is removed: the kit does not ship that skill, so the link had no target.

The frontmatter (`name`, `description`, `license`, `metadata` with author and version) is unchanged; setup prefixes the name to `ai-sdlc-accessibility` when it places the skill.

Reviewed and kept (2026-10-09): the tool table in `references/WCAG.md` names tools, it does not install them.
## Updating

Take `SKILL.md`, `references/` and `LICENSE` from a newer upstream commit, re-apply the changes above, re-run `scripts/personal/tests/test_stack_skills.py`, and update the commit, blobs and date here.
