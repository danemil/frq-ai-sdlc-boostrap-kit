---
name: visual-issue
description: Write an issue, ticket or pull-request description carrying a Mermaid diagram that explains the change, for GitHub, Bitbucket or Jira. Use when opening/creating/filing/drafting a GitHub issue or PR, a Jira issue, ticket, story or bug, a Bitbucket PR or PR description, or when the user asks to explain something visually in an issue, ticket or PR.
---

# Visual Issue

The method is the same on every tracker: decide whether a diagram is warranted, pick the diagram type that fits, write a fenced ` ```mermaid ` block, sanity-check it and **compile it**, then deliver it the way the tracker needs:

| Tracker | Renders Mermaid? | How the issue/PR gets there |
|---|---|---|
| **GitHub** (issues, PRs, comments) | Yes, natively | You file it with `gh`, after the person approves |
| **Bitbucket Data Center** (PRs, descriptions) | Depends on the server version and its plugins | You produce the text, ready to paste; the person posts it |
| **Jira** (issues, comments) | No | You produce the text plus the diagram as an image to attach; the person posts both |

Ask which tracker when it is not clear from the request or the repo (a `github.com` remote means GitHub). Nothing in this kit writes to Jira or Bitbucket (the connectors skill only reads them): never claim you filed, posted or updated anything there.

## When a diagram earns its place

Add one when structure, flow, lifecycle, or relationships are load-bearing — the reader understands the change faster from the picture than the prose. One diagram per distinct concept (e.g. a before/after pair is two blocks).

Skip it for a trivial one-line bug or a copy tweak. A diagram nobody needs is **sediment**.

## Pick the diagram type

| The situation | Mermaid type |
|---|---|
| Dependencies, call graph, before/after module shape, data flow | `flowchart` |
| A request / auth / handshake over time, N round-trips | `sequenceDiagram` |
| A status field's lifecycle, a state machine | `stateDiagram-v2` |
| Tables and their relationships, a schema change | `erDiagram` |
| Classes/types and what they hold | `classDiagram` |
| Phases over a timeline, a rollout plan | `gantt` |

Match the type to the *shape of the thing*, not to habit — a flowchart forced onto a time-ordered flow reads worse than the `sequenceDiagram` it wants to be.

## Sanity-check against the renderer's limits

GitHub **sanitizes** the markdown and runs a trailing Mermaid version; a Bitbucket Mermaid plugin and an image renderer are no more forgiving. Before filing, confirm the block survives:

- **Unique ids — never collide a node id with a subgraph id.** `GD --> VPS[...]` *and* `subgraph VPS[...]` in one diagram is fatal. Every node and subgraph needs its own id; don't reuse an id anywhere.
- **`<br/>` is the only HTML allowed in labels** — use it for line breaks. `\n` renders *literally* on GitHub, it does not break the line.
- **Quote any label with special chars.** Apostrophes (`Let's Encrypt`), curly braces (`{tenant}`), slashes, colons, parens all break the bare parser — wrap the whole label in double quotes: `N["label with /special: {chars}"]`. When in doubt, quote: prefer quoting *all* multi-word labels.
- **One statement per line** — don't pack multiple edges/nodes onto a line with `;`-juggling; line breaks are the parser's safest delimiter.
- **No raw HTML or inline SVG** — GitHub strips it. Hand-built `<div>`/`<svg>` visuals (the kind a local HTML report can show) will not render; express it in Mermaid or attach a static image instead.
- **Stay on stable syntax** — the six types above render reliably; avoid bleeding-edge diagram types/features that the trailing version may not know yet.
- **Style with `classDef`/`style`**, not external CSS — inline is all that survives.

## Validate before filing — don't ship an unrendered block

A block that fails to parse renders as a raw code box, not a diagram — and you only find out *after* the issue is public. So compile every diagram first. Write each block's body to a `.mmd` file (in a temp folder, not the repo) and run it through the Mermaid CLI; only proceed when it exits clean. Use `mmdc` when it is installed (`command -v mmdc`). **`npx` downloads mermaid-cli from the npm registry: ask the person before you run it**, every session. If they say no, or there is no Node, hand over the diagram marked **"not compiled"** and say why.

```bash
mmdc -i diagram.mmd -o "${TMPDIR:-/tmp}/check.svg"
npx -y @mermaid-js/mermaid-cli -i diagram.mmd -o "${TMPDIR:-/tmp}/check.svg"   # only after the person says yes
```

Two traps in that one line, both of which fail a *valid* diagram:

- The output path must end in `.svg`/`.png`/`.pdf`/`.md`. mermaid-cli rejects anything else (`/dev/null` included) *before* it parses the diagram — so discarding the output that way fails every run. Write a real temp file and ignore it.
- **Always write `${TMPDIR:-/tmp}`, never bare `$TMPDIR`.** macOS sets `TMPDIR`; most Linux shells and containers don't, and there the path collapses to `/check.svg` — unwritable, non-zero exit, diagram blamed for it.

A non-zero exit means the diagram is broken — fix it and re-run until it compiles. (No network/CLI, or no to `npx`? Mark the diagram "not compiled" in the hand-over. Suggest a https://mermaid.live preview only when the diagram may leave the team's machines.)

## Assemble and deliver

In every case: write the full body — prose plus the *validated* ` ```mermaid ` block(s) — to a temp markdown file, and **show the person the drafted title and body before anything is filed or handed over.** Nothing is filed, posted or attached without their approval.

**Only the person's own requirements.** Acceptance criteria, scope and decisions in the body are only the ones the person gave (or that are in the source they pointed to). Anything you would add goes in a separate section headed **"Suggested, to confirm"**, for the person to keep or delete.

### GitHub: file with `gh`

File with `--body-file`, never `--body`: the body's backticks and `$` would break shell quoting.

```bash
gh issue create --repo OWNER/REPO --title "..." --body-file "${TMPDIR:-/tmp}/issue-body.md"
```

For a pull request, `gh pr create --title "..." --body-file ...` works the same way. Creating an issue or PR is outward-facing — get approval before running `gh`. Relay the returned URL.

### Bitbucket Data Center: text ready to paste

Give the person the title and the body (prose plus the ` ```mermaid ` block) ready to paste into the PR or its description. Whether Bitbucket renders Mermaid depends on the server version and its plugins, so say: **"If your Bitbucket renders Mermaid, paste it as is; otherwise attach the rendered image."** Render that image the same way as for Jira (below) and give its path. You post nothing yourself.

### Jira: text plus an image to attach

Jira does not render Mermaid. Give the person:

1. The title and the body text, ready to paste. Keep the Mermaid source at the end as a code block, so the diagram stays editable.
2. The diagram as an image to attach. Render it with mermaid-cli when it is available:
   ```bash
   mmdc -i diagram.mmd -o "${TMPDIR:-/tmp}/diagram.png" -b white
   ```
   Give the image's path, and say where in the text it belongs.
3. No mermaid-cli? Offer a draw.io version of the diagram with the `ai-sdlc-drawio` skill, or leave the Mermaid source as a code block for the person to render.

You post and attach nothing yourself: the person does.

**Done when:** every ` ```mermaid ` block has compiled clean under the Mermaid CLI (or is marked "not compiled" and the person knows why); the body carries one block per concept, each of a type that matches its situation, all passing the limits checklist; the person has seen and approved the title and body; on GitHub the issue or PR is filed and its URL reported; on Bitbucket or Jira the text (and image, if any) is handed over with the paths, and nothing is claimed as filed.
