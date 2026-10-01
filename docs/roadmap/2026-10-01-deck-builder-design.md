---
title: "Deck builder: branded .pptx from code, tickets and docs (design)"
status: draft
owner: Architect
author: AI-SDLC Bootstrap Kit
created: 2026-10-01
classification: internal
ai-trust: working
---

# Deck builder: branded .pptx from code, tickets and docs

**Goal.** Give every seat, managers first, a repeatable way to turn what the project already knows into a **branded PowerPoint deck**. The sources are code, the knowledge graph, Jira work items, Bitbucket pull requests, Jama requirements, and Confluence and SharePoint docs. One invokable skill, `deck-builder`, drives four steps:
1. **Gather** the data.
2. **Compute** the numbers deterministically.
3. **Narrate** the slides as Markdown.
4. **Render** the `.pptx` with a swappable **brand pack**.

Frequentis is the first brand pack.

**Non-negotiable framing.**
- **Markdown stays the source of truth** (`template/AGENTS.md` §"Markdown is the single source of truth"). The committed artefact is the slide-by-slide Markdown. The `.pptx` is generated on demand and is never committed (`*.pptx` is already git-ignored).
- **Every number is reproducible or labelled.** A script computes it from a snapshot. If the agent had to source it live, it is tagged `agent-sourced`. If neither was possible, the slide says so. Numbers are never invented.
- **Branding is data, not code.** A new brand means a new folder under `docs/brand/`, not a new skill or renderer.

---

## 1. Decisions (resolved in brainstorming, 2026-10-01)

| # | Decision | Choice |
|---|---|---|
| 1 | Where the deck is produced | **The repo agent renders the `.pptx` directly** (python-pptx). It doesn't depend on Copilot in PowerPoint, which can't see code or tickets. |
| 2 | Brand scope | **Generic `deck-builder` skill + brand pack.** `docs/brand/frequentis/` is the default. Brand rules mirror the Frequentis Copilot-in-PowerPoint skill (Q4/2025 guideline, ATM default). |
| 3 | Deck types | **Five**: status report, architecture overview, release or sprint review, free-form, and **planning health** (twelve fixed sections, §5). |
| 4 | Trackers and tools | **Jira, Confluence, Bitbucket, Jama Connect, SharePoint.** Each will be reachable through the harness (MCP, CLI or script). |
| 5 | Who computes numbers | **Script first, agent fallback.** A deterministic script computes from a snapshot when a scripted source exists. The agent computes when it doesn't, or when fresh data is explicitly needed. Every figure carries its tier. |
| 6 | Branch and base | `feat/deck-builder` from `origin/main`. Installer-profile registration waits for `feat/brownfield-installer` to merge (§11). |

---

## 2. Architecture

Four units. Only **Gather** touches the network. **Compute**, **Lint** and **Render** are pure and offline, so they can be unit-tested.

| Unit | File(s) | Purpose | Deterministic? |
|---|---|---|---|
| **Gather** | `scripts/decks/sources/*.py` + agent fallback | Pull raw data into a normalised JSON **snapshot** | No (network) |
| **Compute** | `scripts/decks/metrics.py` | Snapshot → `metrics.json` (every count and ticket list a slide shows) | Yes |
| **Narrate** | the agent, guided by `deck-builder` and a recipe | `metrics.json` + context → `docs/decks/<date>-<type>.md` | No (LLM) |
| **Lint + Render** | `scripts/decks/lint_deck.py`, `scripts/decks/render.py` | Brand and honesty checks on the Markdown, then Markdown + brand pack → `.pptx` | Yes |

```
Jira · Bitbucket · git · knowledge graph        Confluence · Jama · SharePoint (v1)
      │  scripted sources (tier: script)              │  agent via MCP/CLI (tier: agent-sourced)
      └──────────────┬────────────────────────────────┘
                     ▼
.ai-sdlc/decks/<run>/snapshot.json        ← git-ignored, timestamped, per-source tier
                     │  metrics.py (pure)
                     ▼
.ai-sdlc/decks/<run>/metrics.json         ← every number a slide may show
                     │  agent narrates with a recipe (docs/decks/recipes/<type>.md)
                     ▼
docs/decks/<date>-<type>.md               ← committed source of truth, cites tiers
                     │  lint_deck.py → render.py (+ docs/brand/<brand>/)
                     ▼
out/decks/<date>-<type>.pptx              ← git-ignored deliverable
```

A single CLI, `scripts/decks/deck.py`, wraps the pure units: `snapshot`, `metrics`, `lint`, `render`, and `all`. The agent calls it, and so can a person.

---

## 3. Gather: sources, tiers and the snapshot

### 3.1 Source matrix (v1)

| Source | Used for | v1 path | Tier |
|---|---|---|---|
| **Jira** | Work items, points, sprints, links, fields | `sources/jira_snapshot.py`, which **reuses** `scripts/jira/export_jira.py` (`load_config`, `BACKENDS`, `fetch_all`, `normalize_issue`) and adds the extra fields in §3.3 | `script` |
| **Bitbucket** | Pull requests (month to date, open, merged, declined) | `sources/bitbucket_prs.py`, a new stdlib adapter for **Cloud** (`/2.0/repositories/{ws}/{repo}/pullrequests`) and **Data Center** (`/rest/api/1.0/projects/{p}/repos/{r}/pull-requests`). Confirm both endpoints against the live docs at implementation time. | `script` |
| **git** | Commits and merges when Bitbucket isn't configured. Tags for releases. | `sources/git_log.py` (`git log`, `git tag`) | `script` |
| **Knowledge graph** | Architecture: components, ADRs, traces | `scripts/knowledge/query.py` / the `knowledge` MCP (local, already in the kit) | `script` |
| **Jama Connect** | Software System Requirements (SSR) and their traces to work items | Agent via the Jama MCP or CLI once it's in the harness | `agent-sourced` |
| **Confluence** | Docs, decisions, meeting outcomes | Agent via the `docs-wiki` MCP | `agent-sourced` |
| **SharePoint** | Docs, templates, approved assets | Agent via MCP or CLI once it's in the harness | `agent-sourced` |

**Fallback rule** (decision 5):
- Use the scripted path when its config and credentials exist.
- The agent falls back to MCP or CLI when the script can't run (no config or auth, an unsupported field), or when the user asks for **fresh** data (`--live`, or "use live data").
- Either way, the source's tier and `fetched_at` are written into the snapshot. **Token note:** the scripted path keeps raw ticket JSON out of the agent's context, which is why it is preferred.

### 3.2 Snapshot schema (`snapshot.json`, version 1)

```json
{
  "schema": 1,
  "run_id": "2026-10-01T0930-planning-health",
  "scope": {"projects": ["ATM"], "sprint": "ATM Sprint 42", "release": null,
            "since": "2026-10-01", "until": "2026-10-31"},
  "sources": [
    {"name": "jira", "tier": "script", "fetched_at": "2026-10-01T09:30:12Z", "query": "<JQL>"},
    {"name": "jama", "tier": "agent-sourced", "fetched_at": "...", "via": "jama-mcp"},
    {"name": "sharepoint", "tier": "unavailable", "reason": "no MCP configured"}
  ],
  "work_items": [{
    "key": "ATM-123", "type": "Story", "title": "...", "status": "In Progress",
    "status_category": "indeterminate", "assignee": "...", "sprints": ["ATM Sprint 41", "ATM Sprint 42"],
    "epic": "ATM-100", "parent": "", "story_points": 8, "components": ["VCS"],
    "fix_versions": ["R5.2"], "labels": [], "subtask_count": 4,
    "links": [{"type": "Blocks", "direction": "inward", "key": "NAV-77", "status_category": "new"}],
    "acceptance_criteria": true, "doc_update": "missing", "requirement_links": [],
    "created": "...", "updated": "...", "resolved": "", "url": "..."
  }],
  "pull_requests": [{"repo": "vcs-core", "id": 412, "title": "...", "state": "MERGED",
                     "author": "...", "created": "...", "closed": "...", "keys": ["ATM-123"], "url": "..."}],
  "commits": [], "requirements": [], "docs": []
}
```

- **Why a separate snapshot, not the ledger.** `docs/product/jira/issues.csv` is a committed, stable-column ledger for the knowledge graph. Deck metrics need more fields (links, components, fix versions, sub-tasks, documentation fields) and a time-scoped query. Widening the ledger would churn every diff. The snapshot is short-lived and git-ignored (`.ai-sdlc/decks/`).
- `status_category` uses Jira's three categories (`new`, `indeterminate`, `done`). Status *names* differ per instance, so metrics never branch on them.

### 3.3 Extra Jira fields

`issuelinks`, `components`, `fixVersions`, `subtasks`, `resolutiondate`, `status.statusCategory`, plus configurable custom fields in `decks.config.json` → `jira.fields`:
- `acceptance_criteria` (a text custom field, or `"description:Acceptance criteria"` to detect a heading in the description)
- `doc_update` (a select or checkbox custom field, or a label)
- the existing `sprint`, `epic_link` and `story_points` ids, inherited from `docs/product/jira/config.json`

Jama traces are matched by a configurable regex on the Jira issue-link type or linked key (`jama.link_match`). Jira *remote* links need one extra API call per issue, so v1 doesn't fetch them. A team that traces to Jama only through remote links gets the SSR check through the agent fallback until a scripted Jama source exists.

---

## 4. Compute: `metrics.py`

`compute(snapshot: dict, config: dict) -> dict` is pure: same input, byte-identical `metrics.json`. Lists are sorted by natural key. Each metric returns:

```json
{"value": 7, "items": ["ATM-12", "ATM-31"], "tier": "script", "inputs": ["jira"], "note": ""}
```

`tier` is the **weakest** tier among its inputs (`script` > `agent-sourced` > `unavailable`). If an input is `unavailable`, the metric is `{"value": null, "tier": "unavailable", "note": "<reason>"}` and the slide renders "Not measured: <reason>".

---

## 5. Planning health deck: the twelve sections

The slide order is fixed, exactly as requested. Thresholds live in `decks.config.json` → `planning_health`.

| # | Slide | Definition (default) | Inputs | Computed by |
|---|---|---|---|---|
| 1 | **Executive summary** | Headline verdict plus the three biggest risks, drawn only from slides 2–12 | metrics | agent (narrates computed values) |
| 2 | **Operations summary (PRs month to date)** | PRs created, merged, declined and still open since the 1st of the month. Median time to merge. PRs with no ticket key. Grouped by repo. | Bitbucket (or git) | script |
| 3 | **Incomplete work items** | In-scope items with `status_category != done`, grouped by status, with age in days and the top ten oldest | Jira | script |
| 4 | **Visible dependencies** | Items with a `Blocks` or `Depends` link (configurable). Open inward blockers first, then cross-project links. | Jira | script |
| 5 | **Planning concerns** | Carry-over (in ≥2 sprints), unassigned items in the active sprint, stories with no epic, items blocked by open items | Jira | script |
| 6 | **Recommendations** | Actions, each citing the metric and ticket keys it rests on | metrics | agent |
| 7 | **Planning improvements** | Process changes (e.g. definition of ready, splitting policy), each tied to a recurring pattern in slides 3–12 | metrics | agent |
| 8 | **Mandatory missing documentation** | Per item type in `required_docs`: missing **SSR** trace (Jama), missing **acceptance criteria**, missing **documentation update** | Jira + Jama | script (Jama part `agent-sourced` in v1) |
| 9 | **Story points estimation (missing)** | Stories (types in `story_types`) not done and with no points | Jira | script |
| 10 | **Stories with 1 story point** | Count and list of `story_points == 1` (`one_point_value: 1`) | Jira | script |
| 11 | **Stories over 5 points (risk, need splitting)** | `story_points > split_above` (default **5**) | Jira | script |
| 12 | **Stories that should be epics** | Any of: points ≥ `epic_points` (13), sub-tasks ≥ `epic_subtasks` (8), components ≥ `epic_components` (3), sprints ≥ `epic_carryover` (3). Each item lists the rules it tripped. | Jira | script |

The agent may *interpret* slides 1, 6 and 7, but every claim there must cite a metric id or ticket key. `lint_deck.py` rejects uncited numbers (§7.2).

---

## 6. The other four deck types

Each recipe is a short Markdown file in `docs/decks/recipes/` that the skill loads on demand.

| Type | Storyline | Main sources |
|---|---|---|
| **Status report** | Title → executive summary → shipped since last report → in progress → next → blocked and risks → asks → closing | Jira, Bitbucket |
| **Architecture overview** | Title → context → building blocks → key flows → decisions (ADRs) → tech stack → risks and debt → closing | Knowledge graph, `docs/architecture/`, code |
| **Release / sprint review** | Title → goal and outcome → delivered features → fixes → known issues → demo list → metrics → next → closing | Jira (fix version or sprint), git tags, Bitbucket |
| **Free-form** | The user names the sources and the topic. The agent proposes an outline (one key message per slide) for confirmation, then builds. | any |

Every recipe starts the same way. Before gathering anything, the agent asks:
1. The scope (project, sprint, release or dates).
2. The **classification** (Frequentis Public, General or Confidential), asked every time.
3. The audience.
4. Executive or self-explanatory style (inferred, asked only if unclear).

---

## 7. Narrate: the deck Markdown format

### 7.1 Format

```markdown
---
title: "ATM planning health — Sprint 42"
status: draft
owner: EM
classification: internal          # repo vocabulary (validate-frontmatter)
ai-trust: working
deck:
  type: planning-health
  brand: frequentis
  info-class: "Frequentis General" # printed in the slide footer
  style: executive                 # executive | self-explanatory
  run: 2026-10-01T0930-planning-health
---

<!-- slide: title -->
# ATM planning health
## Sprint 42 · 1 October 2026 · Engineering management

<!-- slide: headline -->
# Seven stories need splitting before sprint 43
- Seven stories exceed five points {m:split_candidates}
- Three carry over for the third sprint {m:carryover}
<!-- chart: column metrics:points_histogram -->
<!-- notes: Lead with the split list; owners are in the appendix. -->

<!-- slide: closing -->
```

- **Layouts** (`<!-- slide: … -->`): `title`, `headline`, `subheadline`, `divider`, `sidebar-small`, `sidebar-wide`, `table`, `closing`. The brand pack maps each one to a template layout or a drawn recipe.
- **Data references:** `{m:<metric_id>}` cites a metric. `<!-- chart: bar|column|donut metrics:<id> -->` and `<!-- table: metrics:<id> -->` pull rows straight from `metrics.json`, so the renderer, not the agent, places the numbers.
- **Images:** `<!-- image: placeholder "<brief>" -->`. The renderer leaves a placeholder and writes the brief into the notes.

### 7.2 `lint_deck.py` (pure, runs before render and in CI)

- **Honesty.** Every digit in slide text must sit next to a `{m:…}` citation, or appear in a `table` or `chart` block. Every `{m:…}` must exist in `metrics.json`.
- **Brand.** It applies the `forbidden` list from `brand.json`: a "Thank you" or "Questions?" slide, "FRQ", "&" in headlines, italics (`*…*`), Title Case headlines. It checks the `deck.info-class` value and the British-English word list (`brand.json` → `spelling`).
- **Structure.** The deck must start with `title` and end with `closing`. Planning health must have all twelve sections in order.

---

## 8. Render: `render.py` and the brand pack

### 8.1 Brand pack: `docs/brand/<name>/`

| File | Content |
|---|---|
| `brand.md` | Human-readable rules with governed frontmatter. For Frequentis, this mirrors the Copilot-in-PowerPoint `frequentis` skill (Q4/2025 guideline): ATM default, palette, Arial, the single blue gradient, flat 2D shapes, logo and key-visual handling, British English, footer classification, no "Thank you" slide. |
| `brand.json` | Machine values: `colors` (primary, accent, legend-only), `fonts`, `gradient`, `chart_series_order`, `footer` pattern (`"{info_class} \| © Frequentis AG {year}"`), `layouts` (slide kind → template layout name, or a drawn recipe), `forbidden`, `spelling`, `assets` (`template`, `logo`, `key_visual`: paths or null). |
| `assets/` (optional, not committed by default) | `template.potx`, logo and key visuals. They are binaries and brand-controlled, so they are git-ignored. `brand.json` points to a local or SharePoint-synced path. |

### 8.2 Renderer behaviour

- **With a template** (`assets.template` exists): open the `.potx`/`.pptx` and use its layouts by name (`brand.json.layouts`). Fill placeholders only. Never draw the logo or footer.
- **Without a template:** draw each layout from `brand.json`: 16:9, white base, blue headlines, Arial, flat shapes with no outline or shadow, and the blue side bars, divider and closing recipes from the Frequentis skill §8. The logo and key-visual areas are left **empty**, and the speaker notes say "Insert official logo / key visual". The renderer never fakes a logo.
- **Charts:** native PowerPoint charts (bar, column, donut, all 2D), coloured in `chart_series_order`. The highlight metric is blue and the rest are grey. Light gridlines, no 3D.
- **Tables:** blue header row with white Arial, white body, thin grey separators.
- **Footer** on every slide except title and closing: `{info_class} | © Frequentis AG {year}` and the page number.
- **Notes:** the source tiers for each slide ("Data: Jira (script, 09:30Z), Jama (agent-sourced)") plus any image or icon briefs.
- **Output:** `out/decks/<date>-<type>.pptx` (git-ignored). The path is printed.

### 8.3 Relation to the Copilot-in-PowerPoint `frequentis` skill

The same rules are used in two places:
- **In PowerPoint:** the `frequentis` Copilot skill restyles decks people already have.
- **In the repo:** `deck-builder` creates decks from project data.

`brand.md` is the canonical copy for the kit. Generating the PowerPoint `SKILL.md` from `brand.md` is a follow-up (§13), not v1.

---

## 9. The skill: `.claude/skills/deck-builder/SKILL.md`

- **Description triggers:** "make a deck/presentation/slides from …", "status report deck", "planning health", "sprint review deck", "architecture overview slides", "backlog health", "stories need splitting", "what did we merge this month, as slides". It also says what it is **not** for: restyling an existing `.pptx` in PowerPoint, which is the Copilot `frequentis` skill.
- **Body:** the flow from §6 (questions) → gather (script first, fallback rules) → `deck.py metrics` → choose a recipe → write the Markdown → `deck.py lint` (fix until it's clean) → `deck.py render` → report the deck path, the Markdown path and each source's tier.
- **Owner seat:** EM. Usable by every seat. `playbook-em` gains a one-line pointer.
- **Validated** by `scripts/validate-skills.py` (agentskills.io). Recipes and brand rules live outside the skill body, so it stays under 500 lines.

---

## 10. Configuration and secrets

`docs/decks/decks.config.json` (tracked, no secrets):

```json
{
  "brand": "frequentis",
  "jira": {"config": "docs/product/jira/config.json",
           "fields": {"acceptance_criteria": "customfield_XXXXX", "doc_update": "customfield_YYYYY"},
           "dependency_link_types": ["Blocks", "Depends"]},
  "bitbucket": {"deployment": "datacenter", "base_url_env": "BITBUCKET_BASE_URL",
                "project": "ATM", "repos": ["vcs-core"]},
  "jama": {"link_match": "Jama", "via": "agent"},
  "planning_health": {"story_types": ["Story"], "split_above": 5, "one_point_value": 1,
                      "epic_points": 13, "epic_subtasks": 8, "epic_components": 3, "epic_carryover": 3,
                      "carryover_sprints": 2,
                      "required_docs": {"Story": ["acceptance_criteria", "ssr_trace", "doc_update"]}},
  "output_dir": "out/decks"
}
```

Auth is env-only, mirroring the Jira ledger: `JIRA_*` as today, plus `BITBUCKET_BASE_URL` and either `BITBUCKET_TOKEN` (Data Center PAT or Cloud access token) or `BITBUCKET_USER` + `BITBUCKET_APP_PASSWORD`. Missing auth makes that source `unavailable` and triggers the fallback rule. The run never crashes.

---

## 11. Dependencies, install and git hygiene

- **One new runtime dependency:** `python-pptx`, used only by `render.py`. Every other unit is stdlib (plus `pyyaml`, which the validators already use). This is the kit's first non-stdlib runtime dependency, so it's documented in `docs/decks/README.md`, and `render.py` fails with an install hint if the package is missing.
- `.gitignore`: add `/.ai-sdlc/decks/`, `/out/decks/` (both anchored to the project root) and `docs/brand/*/assets/`. `*.pptx` is already ignored.
- **Installer profile:** once `feat/brownfield-installer` merges, add `scripts/decks/**`, `docs/decks/**`, `docs/brand/**` and `.claude/skills/deck-builder/**` to the **`full`** profile in `scripts/install/file-classes.json`, with `docs/decks/decks.config.json` and `docs/brand/**` as `seed` (yours after the first write). Until then, the files simply ship in `template/`.

---

## 12. Testing

- `metrics.py`: one test per planning-health metric on a fixture snapshot, including edge cases (no points, unknown status category, a missing source → `unavailable`, byte-identical output).
- `jira_snapshot.py`: normaliser tests on captured **Cloud and Data Center** JSON fixtures (links, components, fix versions, sub-tasks, AC and doc fields). No network.
- `bitbucket_prs.py`: normaliser and pagination tests on Cloud and Data Center fixtures. Ticket-key extraction from title and branch.
- `lint_deck.py`: honesty (an uncited digit fails), brand (Thank-you, FRQ, italics, Title Case, US spelling), structure (section order).
- `render.py`: smoke test that renders the sample deck, reopens it with python-pptx, and checks slide count, footer text, fonts and that there are no italics. CI installs python-pptx for this job only.
- `deck-builder` passes `validate-skills.py`. The sample deck passes `validate-frontmatter.py`.
- Everything is wired into `.gitlab-ci.yml` next to the Jira-ledger tests.

---

## 13. Non-goals (v1) and follow-ups

- Scripted Confluence, Jama and SharePoint sources (agent fallback only until their MCPs or CLIs land in the harness).
- Writing back to Jira or Bitbucket (read-only).
- Charts beyond 2D bar, column and donut. No images fetched from the web or generated.
- Editing existing `.pptx` files (that's the Copilot `frequentis` skill's job).
- **Follow-ups:**
  1. Generate the Copilot-in-PowerPoint `SKILL.md` from `brand.md`, and teach `skill-creator` and `validate-skills.py` the Copilot-in-PowerPoint target (folder = name, only `name`/`description`, allowed file types, no nested zips).
  2. Scripted Jama source.
  3. Trend metrics across snapshots.

---

## 14. Open questions (need Frequentis facts, not design decisions)

1. The Jira custom-field ids for **acceptance criteria** and **documentation update**, and whether Jira is Cloud or Data Center.
2. How Jira items trace to **Jama SSRs**: a link type, a remote link, or a Jama-side trace only.
3. Bitbucket **Cloud or Data Center**, and the project and repo list.
4. Where the official `.potx`, logo and key visuals will live (SharePoint path), and whether brand assets may be stored in the repo at all.
5. Whether committed deck Markdown may contain ticket titles at the `internal` classification, or whether some decks belong in `docs/drafts/`.

---

## 15. Deliverables

1. `scripts/decks/`: `deck.py`, `snapshot.py`, `metrics.py`, `lint_deck.py`, `render.py`, `sources/{jira_snapshot,bitbucket_prs,git_log}.py`, plus tests and fixtures.
2. `docs/decks/`: `README.md`, `decks.config.json`, `recipes/{status,architecture,release,free-form,planning-health}.md`, and a fixture-built sample deck `examples/planning-health-sample.md`.
3. `docs/brand/frequentis/`: `brand.md` and `brand.json`.
4. `.claude/skills/deck-builder/SKILL.md`, a row in the skills `README.md`, and a pointer in `playbook-em`.
5. `.gitignore` entries and `.gitlab-ci.yml` wiring.
6. A `docs/SPEC.md` mention. Installer profile entries come after the installer merges.
