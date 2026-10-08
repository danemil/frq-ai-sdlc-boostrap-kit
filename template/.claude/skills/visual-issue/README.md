# visual-issue

An agent skill that writes issues, tickets and pull-request descriptions carrying a **Mermaid diagram** that explains the change, for GitHub, Bitbucket Data Center or Jira.

GitHub renders fenced ` ```mermaid ` blocks natively in issues, PRs and comments; Bitbucket may, depending on its version and plugins; Jira does not. Most issues never use a diagram. The skill makes the assistant reach for one when structure, flow or lifecycle is load-bearing — and, importantly, **compile the diagram before filing** so you never publish an issue where the block fell back to a raw code box.

## Install

The AI-SDLC kit places it for every role as `.agents/skills/ai-sdlc-visual-issue/`. Nothing else to install.

## Use

Nothing to invoke. Ask for an issue the way you normally would:

> open an issue on `owner/repo` about the auth refactor

> draft a Jira story for the checkout redirect loop, with a diagram

> write the Bitbucket PR description for this branch

> file a bug for the checkout redirect loop, explain it visually

The skill activates on issue, ticket and PR writing, and on "explain this visually".

## What it actually does

- **Decides whether a diagram is warranted at all.** A trivial one-line bug or copy tweak gets no diagram — the skill treats an unnecessary diagram as sediment.
- **Matches diagram type to the shape of the thing** — `flowchart`, `sequenceDiagram`, `stateDiagram-v2`, `erDiagram`, `classDiagram`, `gantt` — rather than defaulting to flowchart for everything.
- **Applies a checklist of GitHub-specific Mermaid gotchas**, the ones that cost you a public, broken issue:
  - node ids colliding with subgraph ids (fatal, and non-obvious)
  - `<br/>` is the only HTML allowed in labels — `\n` renders literally
  - labels with apostrophes, braces, slashes, colons or parens must be quoted
  - raw HTML and inline SVG are stripped by GitHub's sanitizer
- **Compiles every block through the Mermaid CLI** and refuses to file until it exits clean.
- **Delivers per tracker:** files on GitHub with `gh`; for Bitbucket, text ready to paste (plus a rendered image in case your Bitbucket does not render Mermaid); for Jira, text plus a rendered image to attach, or a draw.io version via `ai-sdlc-drawio`. It never claims to have filed anything on Jira or Bitbucket.
- **Shows you the drafted title and body for approval** before anything is filed or handed over — an issue is outward-facing.

## Requirements

- An agent that reads skills (for example GitHub Copilot in VS Code)
- For GitHub: [`gh`](https://cli.github.com/) CLI, authenticated
- `mmdc` (mermaid-cli) or `npx` (the Mermaid CLI is fetched on demand) — the skill falls back to a [mermaid.live](https://mermaid.live) preview if unavailable, but the CLI is the bar

## Notes

Single file, no scripts, no dependencies to vendor — `SKILL.md` is the whole skill and the entire contract.
