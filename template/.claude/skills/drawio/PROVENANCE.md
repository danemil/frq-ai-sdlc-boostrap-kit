# Provenance: drawio

| | |
|---|---|
| Upstream repo | https://github.com/jgraph/drawio-mcp |
| Path | `plugins/copilot/skills/drawio` (the Copilot variant of the skill) |
| Commit | `1da785068fdeb455f8f8cfae0b7799f1ff183894` (2026-09-24) |
| Taken | 2026-10-08 |
| Licence | Apache-2.0; the upstream `LICENSE` is in this folder |

## Files

| File here | Upstream file at that commit | Changed? |
|---|---|---|
| `SKILL.md` | `plugins/copilot/skills/drawio/SKILL.md` | Yes, see below |
| `references/mermaid-reference.md` | `shared/mermaid-reference.md` | No |
| `references/xml-reference.md` | `shared/xml-reference.md` | Two links, see below |
| `references/style-reference.md` | `shared/style-reference.md` | One link, see below |
| `LICENSE` | `LICENSE` | No |

Upstream has no `NOTICE` file. The skill bundles no executable scripts.

## Local modifications

- **No runtime fetches.** Upstream told the agent to fetch `mermaid-reference.md` and `xml-reference.md` from the repo's `main` branch. They are bundled under `references/` at the pinned commit, and `SKILL.md` links to the local copies. `xml-reference.md` linked to `style-reference.md` on `main`; that file is bundled too and the link is local. The two links to `mxfile.xsd` point at the pinned commit and are marked as not needed.
- **No browser URL mode, no upload.** The "Browser URL output" section (a `node -e` one-liner that compressed the diagram into an `app.diagrams.net` link and opened it) is removed, with the `url` examples, the `url` delivery step, the `url` file-naming rule and the two `url` troubleshooting rows.
- **Where diagrams go.** A new section: diagrams are written to `docs/diagrams/` in the person's repo, or wherever they ask; the person sees the file before it is saved; the draw.io desktop CLI is optional, and without it the `.drawio` file is kept and the person is told that export needs the desktop app.
- **Plain requests in the examples.** The `/drawio:drawio …` plugin-command examples became plain requests with `docs/diagrams/` paths.
- **MCP parameters.** A note that the references' MCP-tool parameters (`postLayout`, `routing`, `direction`) map to the CLI's `--layout`.
- **`find-drawio.ps1`** is saved in a temporary folder outside the repo.
- **Company brand by default.** One line in "Where diagrams go": if `ai-sdlc-frq-brandbook` is installed, its diagram styles are used unless the person asks for a plain diagram.

The frontmatter (`name`, `description`) is unchanged; setup prefixes the name to `ai-sdlc-drawio` when it places the skill.

## Updating

Take the same four files from a newer upstream commit, re-apply the changes above, and update the commit and date here.
