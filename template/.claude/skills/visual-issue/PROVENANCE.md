# Provenance: visual-issue

Author: the kit owner; unpublished; contributed 2026-10-08.

## Files

`SKILL.md` and `README.md`, from the owner's own copy of the skill.

## Local modifications

The core is unchanged: decide whether a diagram is warranted, pick the diagram type, check the block against the renderer's limits, compile it with the Mermaid CLI, and show the person the title and body before anything is filed. Generalized from GitHub only to GitHub, Bitbucket Data Center and Jira:

- **Description** now also triggers on Jira issues, tickets, stories and bugs, Bitbucket PRs and PR descriptions, and GitHub PRs.
- **A tracker table** up front: GitHub renders Mermaid and is filed with `gh`; Bitbucket's rendering depends on its version and plugins, so the text is produced ready to paste ("if your Bitbucket renders Mermaid, paste it as is; otherwise attach the rendered image"); Jira does not render Mermaid, so the text comes with an image rendered by mermaid-cli (`mmdc`), or a draw.io version via `ai-sdlc-drawio`, or the Mermaid source as a code block. The kit has no Jira or Bitbucket CLI, so the skill never claims to have filed there.
- **Compile step** prefers an installed `mmdc`; `npx` (which downloads mermaid-cli) runs only after the person says yes, and without it the diagram is handed over marked "not compiled" (E2E finding, 2026-10-09: `npx` ran without asking). The `.mmd` scratch file goes to a temp folder, not the repo. The mermaid.live fallback is only for diagrams that may leave the team's machines.
- **Only the person's own requirements** (E2E finding, 2026-10-09: invented acceptance criteria): the body carries only the acceptance criteria, scope and decisions the person gave; additions go under "Suggested, to confirm".
- **Assemble and deliver** replaces "Assemble and file": approval before anything is filed or handed over, then one subsection per tracker. GitHub also covers `gh pr create`.
- **README.md** is tool-neutral (no assistant-specific install steps) and describes the per-tracker delivery.

Setup prefixes the name to `ai-sdlc-visual-issue` when it places the skill.
