# AI-SDLC Bootstrap Kit

A **bootstrap skeleton for AI-augmented software projects** — drop it into a new repo and you start with AI agents as governed, first-class collaborators across the whole Software Development Life Cycle.

It turns a hand-drawn operating model (one whiteboard, titled *AUTOMATIZARE*) into a runnable scaffold: a canonical agent brief, role-seat skills, scoped MCP connectors, a knowledge layer agents ground on, governance rules enforced as CI gates, an onboarding gatekeeper, and a utilization dashboard with a human-owned improvement loop.

> **New to it?** Read [`docs/SPEC.md`](./docs/SPEC.md) for the full specification, then [`template/AGENTS.md`](./template/AGENTS.md) to see the brief a generated project gets.

## Repository layout

```
AI-SDLC-Bootstrap-Kit/
├── README.md                # you are here — what the kit is, how to use it
├── install.sh               # THE INSTALLER — adopt into a new or existing repo
├── docs/                    # THE KIT's own docs (not a generated project's)
│   ├── SPEC.md              # specification of the template
│   ├── roadmap/             # design + plan records, one per theme
│   ├── visuals/             # framework diagrams (Excalidraw + Mermaid)
│   └── presentation/        # the pitch deck
├── scripts/install/         # planner, manifest, conflict resolution, doctor + tests
└── template/                # THE SKELETON — what lands in your repo
    ├── AGENTS.md  CLAUDE.md  ONBOARDING.md  WORKING-AGREEMENT.md  README.md …
    ├── .claude/skills/       # invokable role playbooks + skill-creator
    ├── .github/workflows/    # CI: AI-governance gates
    ├── scripts/harness/      # keeps every harness surface derived from one brief
    ├── scripts/              # session ritual, validators, hooks, ingest
    ├── docs/                 # the generated project's knowledge tree
    └── dashboard/            # AI-utilization dashboard (DB + web)
```

## The seven pillars

The kit operationalises an AI-augmented SDLC as seven pillars — see [`template/docs/methodology/framework.md`](./template/docs/methodology/framework.md):

| # | Pillar | Where it lives in `template/` |
|---|---|---|
| 1 | **Setup** | `install.sh` + `scripts/install/` |
| 2 | **Onboarding** | `ONBOARDING.md`, `docs/onboarding/` |
| 3 | **Governance & rules** | `AGENTS.md`, `WORKING-AGREEMENT.md`, `docs/ai-context/` |
| 4 | **CI/CD for the AI framework** | `.github/workflows/ai-governance.yml`, `scripts/validate-*.py` |
| 5 | **Knowledge layer (KG/RAG/vector)** | `docs/knowledge/`, `scripts/knowledge/ingest.py` |
| 6 | **Roles × Skills × MCP** | `.claude/skills/playbook-*`, `.mcp.json` |
| 7 | **Human methodology & continuous improvement** | `docs/methodology/continuous-improvement.md`, `dashboard/` |

## Install it — into a new repo *or* one you already have

```bash
./install.sh --into ../my-repo --profile standard \
  --name "Acme Wallet" --slug acme-wallet --ticket ACME
```

Greenfield is just the zero-conflict case of the same code path, so one command covers both. In a repo that already has content, the installer:

- **detects** which AI harnesses you use — from the CLIs on your `PATH` and the config already in the repo;
- **classifies** every file it would write as `own` (kit-maintained), `seed` (yours to edit after the first write) or `merge` (structured config combined key-by-key);
- **asks** on every conflict — `[k]eep mine · [t]ake kit's · [m]erge to .kit-new · [d]iff` — defaulting to *keep*, and never re-asks until the kit's own version changes;
- **records** what it wrote in `.ai-sdlc/manifest.json`, which is what makes a second run an **upgrade** rather than a guess.

Look before you leap, and verify afterwards:

```bash
./install.sh --into ../my-repo --dry-run    # print the plan, write nothing
./install.sh --into ../my-repo doctor       # harnesses, drift, placeholders, doc debt
./install.sh --into ../my-repo uninstall    # remove kit-owned files; yours stay
```

Useful flags: `--profile minimal|standard|full` (a small repo should not inherit a dashboard it will never run), `--yes` / `--take-kit` for CI, `--sync` to regenerate derived harness files only, `--harness NAME` to override detection.

Then open the repo in your harness — it runs `ONBOARDING.md` to create your per-user `USER.md`, and you fill the remaining placeholders (`AGENTS.md` §1 mission, §3 constraints, §4 connectors). `doctor` lists exactly which are left.

### One brief, every tool

`AGENTS.md`, `.claude/skills/` and `.mcp.json` are canonical; every other harness surface is derived from them, and `scripts/harness/sync.py --check` fails CI if a copy drifts.

| | Claude Code | Codex CLI | Copilot CLI | Cursor · Gemini · Windsurf · opencode |
|---|---|---|---|---|
| Brief | `CLAUDE.md` pointer | reads `AGENTS.md` natively | reads `AGENTS.md` natively | pointer files |
| Skills | `.claude/skills/` | symlinked | **reads `.claude/skills/` natively** | — |
| MCP | `.mcp.json` | generated TOML block | generated `.copilot/mcp-config.json` | merged |
| Hooks | `.claude/settings.json` | generated `.codex/hooks.json` | *none — ritual stays manual* | — |

Because Copilot CLI discovers `.claude/skills/` and both Codex and Copilot read `AGENTS.md` natively, three harnesses run off one brief and one skills tree with no duplicated files at all.

> **Upgrading from `bootstrap.sh`?** That script only ever handled a *strictly empty*
> target: it `tar`-extracted over whatever was there and ran `git init && git add -A`,
> so pointing it at a populated repo destroyed existing config. `install.sh` replaces
> it and covers both cases. `bootstrap.sh` is kept for backward compatibility only.

## Verify the template locally

```bash
pip install "pyyaml>=6"

# The installer: unit + end-to-end (greenfield, brownfield, idempotency, uninstall)
for t in scripts/install/tests/test_*.py; do python3 "$t"; done

cd template
python3 scripts/validate-skills.py          # skills conform to agentskills.io
python3 scripts/validate-frontmatter.py     # doc maturity/trust contract
python3 scripts/harness/sync.py --check     # derived harness configs match .mcp.json
python3 scripts/knowledge/ingest.py --build # knowledge layer builds
```

These are the same gates the generated project's CI runs ([`template/.github/workflows/ai-governance.yml`](./template/.github/workflows/ai-governance.yml)).

## Design principles

- **One brief, every tool.** `AGENTS.md` is canonical; `CLAUDE.md` and friends are thin pointers that can't drift.
- **Attributable, never silent.** Every AI change to a load-bearing artefact has a named seat and a reviewable trail (scoped-write MCP posture).
- **Rules as code.** Governance is expressed as scripts and enforced as merge gates.
- **Ground, don't guess.** Agents answer from the project's knowledge layer, with the source's trust tier.
- **Human owns the loop.** Promotion, sign-off, and curation stay human; the dashboard + retro turn usage into improvements.
- **Anti-bloat.** A rule earns its place only by removing a recurring real question.
- **Adopt, never clobber.** The installer merges into a repo that already has a life; what it wrote is recorded, so a second run is an upgrade and every change is reversible.

## Provenance

Distilled from a real multi-repo programme's governance setup, generalised and stripped of all project specifics, and aligned to the *AUTOMATIZARE* whiteboard model.

## Contributing

Contributions are welcome — see [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the
workflow, local checks, and conventions, and [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md)
for community expectations. Security issues: please follow [`SECURITY.md`](./SECURITY.md)
rather than opening a public issue.

## License

Released under the [MIT License](./LICENSE) — you are free to use, copy, modify,
and distribute this kit, including in commercial and closed-source projects.
