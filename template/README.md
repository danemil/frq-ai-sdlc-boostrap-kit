# `<PROJECT_NAME>`

`<ONE_LINE_DESCRIPTION>`

This repository is an **AI-augmented SDLC** workspace, bootstrapped from the [AI-SDLC Bootstrap Kit](../README.md). AI agents are first-class collaborators across the lifecycle, under explicit governance.

> **AI agents:** read [`AGENTS.md`](./AGENTS.md) first — it is the canonical brief every tool follows.

## Quick start

```bash
# 1. First-run setup (installs tooling, creates your per-user USER.md)
#    Open this folder in Claude Code and let it run ONBOARDING.retired.md, or do it manually:
pip install pre-commit && pre-commit install

# 2. (optional) Build the knowledge index so agents can ground on project sources
python3 scripts/knowledge/ingest.py --build

# 3. (optional) Run the AI-utilization dashboard
pip install -r dashboard/requirements.txt && streamlit run dashboard/app.py
```

This repo was set up by the kit's installer. To pull in later kit versions, or to
add a harness, re-run it from wherever the kit is checked out — it is idempotent
and will not overwrite anything you have edited:

```bash
/path/to/ai-sdlc-kit/install.sh --into . --dry-run   # see what would change
/path/to/ai-sdlc-kit/install.sh --into .             # apply, asking on conflicts
/path/to/ai-sdlc-kit/install.sh --into . doctor      # harnesses, drift, placeholders
```

What the installer manages here is recorded in `.ai-sdlc/manifest.json`.

## What's here

| Path | What it is |
|---|---|
| [`AGENTS.md`](./AGENTS.md) | **Canonical brief** — mission, constraints, trust tiers, MCP posture, seats. Read first. |
| [`CLAUDE.md`](./CLAUDE.md) | Thin pointer to `AGENTS.md` for Claude Code. |
| [`ONBOARDING.retired.md`](./ONBOARDING.retired.md) | First-run setup (loaded only when `USER.md` is missing). |
| [`WORKING-AGREEMENT.md`](./WORKING-AGREEMENT.md) | How we organise across tools; lifecycle & session ritual. |
| [`FOLDER-INDEX.md`](./FOLDER-INDEX.md) | Directory map. |
| [`INDEX.md`](./INDEX.md) | Cross-artefact index. |
| [`.claude/skills/`](./.claude/skills/) | Invokable role playbooks + `skill-creator`. |
| [`.github/workflows/`](./.github/workflows/) | CI — AI-governance gates. |
| [`scripts/`](./scripts/) | Session ritual, validators, git hooks, harness sync, knowledge ingest. |
| [`docs/`](./docs/) | The knowledge tree (architecture, governance, knowledge, methodology, ai-context). |
| [`dashboard/`](./dashboard/) | AI-utilization dashboard (DB + web). |

## The seven pillars

This workspace operationalises the AI-SDLC framework — see [`docs/methodology/framework.md`](./docs/methodology/framework.md):

1. **Setup** · 2. **Onboarding** · 3. **Governance & rules** · 4. **CI/CD for the AI framework** · 5. **Knowledge layer (KG/RAG/vector)** · 6. **Roles × Skills × MCP** · 7. **Human methodology & continuous improvement**

## Conventions

- **Markdown is the source of truth.** Binaries are generated on demand, not committed (`AGENTS.md` §7).
- **Every load-bearing change is attributable** to a named seat with a reviewable trail (`AGENTS.md` §4.3).
- **Frontmatter** signals maturity & trust on every long-lived doc (`AGENTS.md` §4.2).
