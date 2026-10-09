# Provenance: likec4-dsl

| | |
|---|---|
| Upstream repo | https://github.com/likec4/likec4 |
| Path | `skills/likec4-dsl` |
| Commit | `4e6ee7afc526f3dcacd2b5fb03c9d669c3b78cad` (2026-09-14) |
| Taken | 2026-10-08 |
| Licence | MIT; the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit | Changed? |
|---|---|---|
| `SKILL.md` | `skills/likec4-dsl/SKILL.md` | Yes, see below |
| `references/*.md` (15 files) | `skills/likec4-dsl/references/*.md` | No |
| `LICENSE` | `LICENSE` | No |

Not bundled: upstream `skills/likec4-dsl/evals/` (the upstream project's test material for the skill; Copilot does not need it). Upstream has no `NOTICE` file. The skill bundles no executable scripts.

The references contain no instruction to fetch anything at runtime; their links (the LikeC4 docs, the config `$schema` URL, a repository link in an example) are illustrative only.

## Local modifications

All in one new section of `SKILL.md`, "Where models go (this kit's copy)", placed after the opening paragraph. Nothing else in upstream's text is changed (the "Response Discipline (critical for evals)" section and the CLI syntax guidance stay as they are).

- **Where models go.** LikeC4 models are written to `docs/architecture/` in the person's repo, or wherever they ask; the person sees the file name and content before it is saved.
- **The CLI is optional and needs consent.** Prefer an already-installed `likec4` (a `package.json` dependency or `likec4` on the PATH). `npx`/`bunx`/`pnpm dlx likec4 …` downloads a package from the npm registry, so Copilot asks before running it the first time. Without Node or npm access, or if the person says no, the `.c4` file is kept, validation is skipped, and the person is told that validation and export need the LikeC4 CLI or the LikeC4 VS Code extension.
- **No writes to other systems unasked.** `likec4 sync leanix --apply` (which writes to LeanIX) runs only when the person asks for it.
- **No runtime fetches.** A line that the bundled `references/` are read locally and nothing is fetched from the internet at runtime.
- **Company brand by default.** One line: the brand skill's LikeC4 `specification` colours are used unless the person asks for a plain model. The line says to load `ai-sdlc-frq-brandbook`, that it is installed when it is in the skill list, and to read its files by exact path, never deciding by glob or search (the placed folder is hidden from git, so search tools skip it).

The frontmatter (`name`, `description`) is unchanged; setup prefixes the name to `ai-sdlc-likec4-dsl` when it places the skill.

## Updating

Take `SKILL.md`, `references/` and `LICENSE` from a newer upstream commit (still without `evals/`), re-apply the section above, check the references again for runtime fetches, and update the commit and date here.
