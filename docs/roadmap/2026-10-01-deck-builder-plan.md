---
title: "Deck builder (implementation plan)"
status: draft
owner: Architect
author: AI-SDLC Bootstrap Kit
created: 2026-10-01
classification: internal
ai-trust: working
---

# Deck builder implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `deck-builder` skill and its pipeline. Gather data (script first, agent fallback), compute every number deterministically, have the agent narrate a slide-by-slide Markdown deck, lint it for honesty and brand, then render a branded `.pptx` with a swappable brand pack. Frequentis is the first brand pack.

**Spec:** [`2026-10-01-deck-builder-design.md`](./2026-10-01-deck-builder-design.md). Section numbers below (§n) refer to it.

**Architecture:** Four units:
1. **Gather:** `scripts/decks/sources/*.py` (network), producing a git-ignored `snapshot.json`.
2. **Compute:** `scripts/decks/metrics.py` (pure), producing `metrics.json`.
3. **Narrate:** the agent writes `docs/decks/<date>-<type>.md`.
4. **Lint + Render:** `lint_deck.py` and `render.py` (pure), producing `out/decks/*.pptx`.

`scripts/decks/deck.py` is the single CLI.

**Tech stack:** Python 3.12 stdlib for everything except `render.py`, which uses **python-pptx**. Tests use `unittest` scripts run directly, like the existing ones. GitLab CI governance gate.

## Global constraints

- **All work lives under `template/`.** Paths below are relative to `template/`. The spec and plan stay in repo-root `docs/roadmap/`.
- **Stdlib only, except `render.py`.** Import `pptx` lazily inside `render.py`. If it's missing, exit 2 with `pip install python-pptx`. No other unit imports it.
- **Pure units are total and deterministic.**
  - `metrics.py` and `lint_deck.py` do no I/O beyond their arguments.
  - Output JSON uses `sort_keys=True, indent=2`, with `\n` line endings, and lists sorted by natural key.
  - The same snapshot always gives byte-identical `metrics.json`.
- **Honesty.** A missing source yields `{"value": null, "tier": "unavailable", "note": …}`. Never use a default or estimated number. Tier order: `script` > `agent-sourced` > `unavailable`. A metric takes the weakest tier among its inputs.
- **Reuse, don't fork.** Jira access goes through `scripts/jira/export_jira.py` (`load_config`, `BACKENDS`, `fetch_all`, `normalize_issue`, `natural_key`). Don't copy its adapter.
- **No secrets in git.** Auth comes from env only (`JIRA_*`, `BITBUCKET_*`). `decks.config.json` is tracked and holds no secrets.
- **No binaries in git.** `.pptx`, `.potx`, logos and key visuals stay ignored (§11).
- **Commit trailer.** End every commit message with:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- **Branch.** `feat/deck-builder`, cut from `origin/main`. The spec and plan are its first commit.

---

## File structure

**Create:**
- `scripts/decks/deck.py`: the CLI (`snapshot | metrics | lint | render | all`).
- `scripts/decks/snapshot.py`: schema v1, `new_snapshot()`, `add_source()`, `load()`, `save()`, `validate()`.
- `scripts/decks/sources/jira_snapshot.py`: reuses `export_jira` and adds the §3.3 fields.
- `scripts/decks/sources/bitbucket_prs.py`: the Cloud and Data Center PR adapter.
- `scripts/decks/sources/git_log.py`: the commit, merge and tag fallback.
- `scripts/decks/metrics.py`: `compute(snapshot, config) -> dict`.
- `scripts/decks/deckmd.py`: deck Markdown parser (`parse(text) -> Deck`).
- `scripts/decks/lint_deck.py`: `lint(deck, metrics, brand) -> list[Finding]`.
- `scripts/decks/render.py`: `render(deck, metrics, brand, out_path)`.
- `scripts/decks/tests/`:
  - `test_snapshot.py`, `test_jira_snapshot.py`, `test_bitbucket_prs.py`, `test_git_log.py`
  - `test_metrics.py`, `test_deckmd.py`, `test_lint_deck.py`, `test_render.py`, `test_deck_cli.py`
  - `fixtures/` containing:
    - `jira_cloud_search.json`, `jira_dc_search.json`
    - `bb_cloud_prs.json`, `bb_dc_prs.json`
    - `snapshot_planning.json`, `metrics_planning.json`
    - `brand_test.json`
- `docs/decks/README.md`, `docs/decks/decks.config.json`
- `docs/decks/recipes/{status,architecture,release,free-form,planning-health}.md`
- `docs/decks/examples/planning-health-sample.md` (built from `fixtures/snapshot_planning.json`)
- `docs/brand/frequentis/brand.md`, `docs/brand/frequentis/brand.json`
- `.claude/skills/deck-builder/SKILL.md`

**Modify:**
- `.gitignore`: add `/.ai-sdlc/decks/`, `/out/decks/`, `docs/brand/*/assets/` (run folders anchored to the project root).
- `.claude/skills/README.md`: add a row to *Tooling skills*.
- `.claude/skills/playbook-em/SKILL.md`: add a one-line pointer to `deck-builder`.
- `../.gitlab-ci.yml`: add the new tests, plus a python-pptx install line for the render smoke test.
- `../docs/SPEC.md`: mention the deck builder under pillar 6 (Roles × Skills × MCP).

---

## Task 1: Snapshot schema and scaffolding

**Files:** create `scripts/decks/snapshot.py` and `scripts/decks/tests/test_snapshot.py`. Modify `.gitignore`.

**Interfaces:**

```python
SCHEMA = 1
TIERS = ("script", "agent-sourced", "unavailable")          # strongest → weakest
def new_snapshot(run_id: str, scope: dict) -> dict
def add_source(snap: dict, name: str, tier: str, **meta) -> None   # fetched_at auto (UTC ISO)
def validate(snap: dict) -> list[str]                           # [] == valid
def load(path) -> dict ; def save(snap, path) -> None           # atomic write, sort_keys
def weakest(tiers: Iterable[str]) -> str
```

- [x] **Step 1: Write failing tests.** Cover these cases:
  - A new snapshot validates.
  - An unknown tier fails.
  - A `work_items` entry without `key` fails.
  - `weakest(["script", "agent-sourced"]) == "agent-sourced"`.
  - `weakest([]) == "unavailable"`.
  - `save` then `load` round-trips byte-identically.
- [x] **Step 2:** Run `python3 scripts/decks/tests/test_snapshot.py`. Expect it to fail with an import error.
- [x] **Step 3: Implement** `snapshot.py`. Write atomically: temp file plus `os.replace`.
- [x] **Step 4:** Run the tests. Expect `OK`.
- [x] **Step 5:** Add `/.ai-sdlc/decks/`, `/out/decks/` and `docs/brand/*/assets/` to `.gitignore`. Anchor the run folders to the project root so an unrelated `out/` elsewhere stays tracked.
- [x] **Step 6: Commit** `feat(decks): snapshot schema v1 and git-ignored run dirs`.

---

## Task 2: Jira snapshot source (reuses the ledger exporter)

**Files:** create `scripts/decks/sources/jira_snapshot.py`, `tests/test_jira_snapshot.py`, and the fixtures `jira_cloud_search.json` and `jira_dc_search.json`.

**Interfaces:**

```python
EXTRA_FIELDS = ["issuelinks", "components", "fixVersions", "subtasks", "resolutiondate", "status"]
def deck_jira_config(ledger_cfg: dict, deck_cfg: dict, scope: dict) -> dict
    # ledger cfg + extra fields + scoped JQL (project in …, sprint/fixVersion/updated window)
def scoped_jql(scope: dict, default_project: str) -> str     # explicit scope["jql"] wins verbatim
def normalize_work_item(raw: dict, cfg: dict, deck_cfg: dict, base_url: str) -> dict   # §3.2 work_items shape
def fetch(deck_cfg: dict, scope: dict, ledger_cfg=None, fetch_all=None) -> tuple[list[dict], dict]
    # returns (work_items, source_meta); raises SourceUnavailable(reason) on missing auth/config.
    # export_jira reports auth/HTTP failures via sys.exit; fetch converts SystemExit to SourceUnavailable.
```

**Field rules:**
- `status_category` comes from `fields.status.statusCategory.key` (`new` / `indeterminate` / `done`).
- `sprints` lists every sprint name in the sprint custom field.
- `acceptance_criteria` is True or False:
  - With a custom-field id: the field is non-empty.
  - With `"description:<Heading>"`: the heading is present in the description text (use `export_jira.adf_to_text` for Cloud).
- `doc_update` takes the select value, `"missing"` when empty, or `"n/a"` when unconfigured.
- `links` maps `issuelinks[]` to `{type, direction (inward|outward), key, status_category}`.
- `requirement_links` keeps the linked keys whose link type or key matches `jama.link_match` (a regex).
- **Unconfigured means unknown, not missing:** with no AC field, no doc field or no `link_match`, the value is `None` / `"n/a"`, so metrics report "Not measured" rather than counting every item as missing.

- [x] **Step 1: Write failing tests.**
  - Cloud fixture: links, components, fix versions, sub-task count, statusCategory, AC via custom field, AC via description heading.
  - Data Center fixture: the same fields (v2 shape, wiki-markup description).
  - Missing `JIRA_BASE_URL` raises `SourceUnavailable`.
  - `fetch` with an injected fake `fetch_all` never touches the network.
- [x] **Step 2:** Run the tests and confirm they fail.
- [x] **Step 3: Implement.** Call `export_jira.fetch_all(cfg)` with the extended cfg. The extra field ids are appended through `cfg["fields"]`, exactly as `fetch_all` already does.
- [x] **Step 4:** Run the tests. Then run the existing `scripts/jira/tests/test_export_jira.py` to confirm the ledger exporter didn't regress.
- [x] **Step 5: Commit** `feat(decks): Jira snapshot source reusing the ledger adapter`.

---

## Task 3: Bitbucket PR source and git fallback

**Files:** create `sources/bitbucket_prs.py`, `sources/git_log.py`, and the tests `test_bitbucket_prs.py` and `test_git_log.py`, with fixtures `bb_cloud_prs.json` and `bb_dc_prs.json`.

**Interfaces:**

```python
BACKENDS = {"cloud": {...}, "datacenter": {...}}   # base path, auth header, pagination (next URL | start/isLastPage)
def normalize_pr(raw: dict, deployment: str, repo: str) -> dict   # §3.2 pull_requests shape
def extract_keys(*texts: str) -> list[str]   # Jira keys from title + source branch, KEY_RE as commit_msg_ticket.py
def fetch(deck_cfg: dict, since: str, until: str, http_get=None, env=None) -> tuple[list[dict], dict]
    # http_get(url, headers) -> dict, raising SourceUnavailable; env defaults to os.environ.
    # Window: created or closed in [since, until] (whole UTC days), or still OPEN and created by `until`.
    # Cloud has no close time in the list API, so merged/declined PRs use updated_on.
    # Cloud ignores BITBUCKET_BASE_URL unless the config names a base_url_env explicitly.
# git_log.py
def merges(since: str, until: str, cwd=".") -> list[dict]   # PR-like rows from merge commits (tier: script, source: git)
    # Dates filtered in Python: `git log --since` stops at the first older commit and would miss merges.
    # Squash/rebase merges leave no merge commit, and open/declined PRs are invisible: Bitbucket stays preferred.
def tags(cwd=".") -> list[dict]                             # newest first; tagger date for annotated tags
```

The state values are normalised: Cloud `MERGED/DECLINED/OPEN/SUPERSEDED` and Data Center `MERGED/DECLINED/OPEN` become `MERGED/DECLINED/OPEN`.

- [x] **Step 1: Write failing tests.**
  - Normalise the Cloud and Data Center fixtures.
  - Paginate both styles with a fake `http_get`.
  - Keys come from both title and branch, deduplicated and sorted.
  - Missing auth raises `SourceUnavailable`.
  - `git_log.merges` runs on a temporary repo (`git init` plus two merge commits).
- [x] **Step 2:** Run the tests and confirm they fail.
- [x] **Step 3: Implement.** Use stdlib `urllib`, with one bounded retry on 429 and 5xx, honouring `Retry-After`. Confirm the Cloud and Data Center endpoints against the live docs and note the date in a code comment.
- [x] **Step 4:** Run the tests and confirm they pass.
- [x] **Step 5: Commit** `feat(decks): Bitbucket PR source (Cloud/DC) with git fallback`.

---

## Task 4: Metrics core

**Files:** create `scripts/decks/metrics.py`, `tests/test_metrics.py`, `fixtures/snapshot_planning.json` and `fixtures/metrics_planning.json`. The snapshot fixture is hand-built, around 25 work items and 12 PRs, and covers every rule. The metrics fixture is its committed `compute()` output, used by the CI lint smoke test in Task 10.

**Interfaces:**

```python
def compute(snapshot: dict, config: dict, today: str) -> dict   # {metric_id: Metric}, today injected for purity
# metric ids (stable, used by {m:…} citations and recipes):
#   prs_mtd, prs_without_key, median_merge_hours,
#   incomplete_by_status, incomplete_oldest,
#   dependencies_open_blockers, dependencies_cross_project,
#   carryover, unassigned_active, no_epic, blocked_by_open,
#   missing_ac, missing_ssr, missing_doc_update,
#   missing_points, one_point_stories, split_candidates, epic_candidates,
#   points_histogram
# Metric = {"value", "items", "tier", "inputs", "note"} (+ "rules" on epic_candidates, "rows" on table/chart metrics)
```

- [ ] **Step 1: Write failing tests.** Write one test per metric id against the fixture, asserting `value`, the sorted `items` and the `tier`. Also cover:
  - `split_candidates` uses the strict `> split_above` comparison (5 is excluded, 8 is included).
  - `epic_candidates` lists the tripped rules.
  - `missing_ssr` carries tier `agent-sourced` when the Jama source is agent-sourced.
  - Every PR metric is `unavailable` when there are no PR sources.
  - Two runs produce byte-identical JSON.
  - Done items never count as `missing_points`.
- [ ] **Step 2:** Run the tests and confirm they fail.
- [ ] **Step 3: Implement** one small function per metric and a registry dict, so a recipe can list the ids it needs.
- [ ] **Step 4:** Run the tests and confirm they pass.
- [ ] **Step 5: Commit** `feat(decks): deterministic metrics for the planning-health deck`.

---

## Task 5: Deck Markdown parser and linter

**Files:** create `scripts/decks/deckmd.py`, `scripts/decks/lint_deck.py`, `tests/test_deckmd.py`, `tests/test_lint_deck.py` and `fixtures/brand_test.json`.

**Interfaces:**

```python
# deckmd.py
@dataclass class Slide: kind: str; title: str; subtitle: str; body: list[str]; blocks: list[dict]; notes: str
@dataclass class Deck: meta: dict; slides: list[Slide]
def parse(text: str) -> Deck     # frontmatter (yaml if available, else minimal parser) + <!-- slide|chart|table|image|notes --> directives
# lint_deck.py
@dataclass class Finding: slide: int; rule: str; severity: str; message: str   # severity: error | warning
def lint(deck: Deck, metrics: dict, brand: dict) -> list[Finding]
```

The rules come from design §7.2:

| Group | Rule ids |
|---|---|
| Honesty | `uncited-number`, `unknown-metric` |
| Brand | `forbidden-phrase` ("Thank you", "Questions?"), `frq-abbrev`, `ampersand-headline`, `italics`, `title-case-headline`, `us-spelling`, `missing-info-class` |
| Structure | `first-not-title`, `last-not-closing`, `planning-sections-order` |

- [ ] **Step 1: Write failing tests.**
  - Parser: all directives, notes, multiple slides, and an empty body.
  - Linter: one positive and one negative fixture per rule.
  - A digit inside a `table` or `chart` block, or next to `{m:…}`, passes.
  - "Sprint 42" in a title-slide subtitle passes (allow-list: sprint, release and version numbers, dates).
- [ ] **Step 2:** Run the tests and confirm they fail.
- [ ] **Step 3: Implement.** Keep Title Case detection conservative: flag only when at least 60% of the words longer than three letters are capitalised, ignoring known proper nouns from `brand.json` → `proper_nouns`.
- [ ] **Step 4:** Run the tests and confirm they pass.
- [ ] **Step 5: Commit** `feat(decks): deck Markdown format and honesty/brand linter`.

---

## Task 6: Frequentis brand pack

**Files:** create `docs/brand/frequentis/brand.md` and `docs/brand/frequentis/brand.json`.

- [ ] **Step 1: Write `brand.json`.** Take the values from the Frequentis Copilot skill (the guideline is the vault's `Frequentis Brand Guidelines-Q4-2025.pdf`):
  - `colors.primary`: blue `#004182`, light blue `#00AAE1`, black `#333333`, cool grey `#666666`, mid grey `#999999`, warm grey `#C9C3BA`.
  - `colors.accent`: `#73B432`, `#F0A51E`, `#A52846`.
  - `colors.legend_only`: ATM `#2364A0`, MAR `#19555F`, DEF `#641E6E`, PS `#D22832`, PT `#DC6423`, yellows `#F0A51E` and `#FDD217`.
  - `fonts`: Arial, with `italic: false`.
  - `gradient`: `#004182` → `#00AAE1`, corner to corner.
  - `chart_series_order`: blue, light blue, then the three greys.
  - `footer`: `"{info_class} | © Frequentis AG {year}"`.
  - `info_classes`: Frequentis Public, General and Confidential.
  - `layouts`: map each slide kind to `{template_layout, recipe}`.
  - `forbidden`, `spelling` (a US → UK map) and `proper_nouns`.
  - `assets`: everything null.
  - `default_bu`: `"ATM"`.
- [ ] **Step 2: Write `brand.md`.** Add governed frontmatter (status draft, owner Architect, classification internal, ai-trust working). Its body condenses the Copilot skill's sections 4 to 8, with a source line pointing to the Q4/2025 guideline.
- [ ] **Step 3:** Run `python3 scripts/validate-frontmatter.py docs/brand/frequentis/brand.md` and confirm it passes.
- [ ] **Step 4: Commit** `feat(brand): Frequentis brand pack (rules + machine values)`.

---

## Task 7: Renderer

**Files:** create `scripts/decks/render.py` and `tests/test_render.py`.

**Interfaces:**

```python
def render(deck: Deck, metrics: dict, brand: dict, out_path: Path, brand_dir: Path) -> Path
# template mode if brand["assets"]["template"] resolves to a file, else drawn mode (§8.2)
```

- [ ] **Step 1: Write failing tests.** Skip them with a clear message if `pptx` isn't importable. Render `docs/decks/examples/planning-health-sample.md` with `fixtures/snapshot_planning.json` → metrics, then reopen the result and assert:
  - The slide count matches the Markdown.
  - Every non-title, non-closing slide carries the footer `Frequentis General | © Frequentis AG <year>`.
  - No run is italic, and every run uses the Arial font.
  - Chart series colours follow `chart_series_order`.
  - The notes contain the source tiers.
  - With no logo asset, the notes contain "Insert official logo".
- [ ] **Step 2:** Run the tests and confirm they fail.
- [ ] **Step 3: Implement the drawn layouts** (title, headline, subheadline, divider, sidebar-small, sidebar-wide, table, closing), plus native 2D charts (bar, column, donut), tables and image placeholders.
  - Remove outlines and shadows on every shape (`line.fill.background()`, no effect list).
  - Template mode looks up layouts by name and only fills placeholders.
- [ ] **Step 4:** Run the tests and confirm they pass. Render the sample to `out/decks/` and convert it to PDF with `soffice --headless --convert-to pdf`. Inspect every page visually against the brand checklist before committing.
- [ ] **Step 5: Commit** `feat(decks): python-pptx renderer with drawn and template modes`.

---

## Task 8: CLI orchestrator

**Files:** create `scripts/decks/deck.py` and `tests/test_deck_cli.py`.

**Commands:**

```
deck.py snapshot --type planning-health --scope '{"projects":["ATM"],"sprint":"ATM Sprint 42"}' [--run ID] [--live]
deck.py metrics  --run ID
deck.py lint     docs/decks/<file>.md --run ID
deck.py render   docs/decks/<file>.md --run ID [--brand frequentis] [--out out/decks/]
deck.py all      docs/decks/<file>.md --run ID          # lint (fail on error) → render
deck.py add-source --run ID --name jama --tier agent-sourced --file items.json   # how the agent records fallback data
```

- **Exit codes:** 0 means OK, 1 means lint errors, and 2 means a missing dependency or config.
- **Default paths:** `snapshot` writes `.ai-sdlc/decks/<run>/snapshot.json`, and `metrics` writes `metrics.json` next to it.
- **Skipped sources:** a scripted source that raises `SourceUnavailable` is recorded as `unavailable` with the reason, and the run continues.
- **`--live`** skips the scripted sources and leaves fallback to the agent.

- [ ] **Step 1: Write failing tests.** Run end to end on the fixtures with injected fake sources: snapshot → metrics → lint → render (the render step is skipped without pptx). Test `add-source` merging and every exit code.
- [ ] **Step 2:** Run the tests and confirm they fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** Run the tests and confirm they pass.
- [ ] **Step 5: Commit** `feat(decks): deck.py CLI tying gather, compute, lint and render`.

---

## Task 9: Skill, recipes and docs

**Files:**
- Create `.claude/skills/deck-builder/SKILL.md`, `docs/decks/recipes/*.md`, `docs/decks/README.md`, `docs/decks/decks.config.json` and `docs/decks/examples/planning-health-sample.md`.
- Modify `.claude/skills/README.md` and `.claude/skills/playbook-em/SKILL.md`.

- [ ] **Step 1: Write `SKILL.md`** (§9). The description is at most 1024 characters, includes the triggers, and says what it is not for.
  - The body covers the question order: scope → classification (always asked) → audience → style (inferred).
  - It covers the gather rules (script first, fallback rules, `add-source` for agent data), the metrics → recipe → write → lint-until-clean → render loop, and the final report (deck path, Markdown path, the tier for each source).
  - It must stay under 500 lines.
- [ ] **Step 2: Write five recipes.** Each one lists the slide sequence, the metric ids or sources per slide, and what the agent may interpret. `planning-health.md` encodes the twelve sections in the spec's order, with their metric ids.
- [ ] **Step 3: Write `decks.config.json`** (spec §10, with placeholder custom-field ids) and **`README.md`**. The README covers setup, env vars, the python-pptx install, how tiers work and how to add a brand. The README and the sample deck carry governed frontmatter.
- [ ] **Step 4: Build the sample deck** from the fixture snapshot and make it lint-clean with `deck.py lint`.
- [ ] **Step 5:** Run `python3 scripts/validate-skills.py` and `python3 scripts/validate-frontmatter.py` and confirm both pass.
- [ ] **Step 6: Commit** `feat(skills): deck-builder skill, recipes and docs`.

---

## Task 10: CI wiring and spec mention

**Files:** modify `../.gitlab-ci.yml` and `../docs/SPEC.md`.

- [ ] **Step 1:** Add the nine `scripts/decks/tests/test_*.py` runs to the governance job, after the Jira tests. Add `pip install --quiet "python-pptx>=1.0"` next to the existing pyyaml install, so the render smoke test runs rather than skipping.
- [ ] **Step 2:** Add a smoke line: `python3 template/scripts/decks/deck.py lint template/docs/decks/examples/planning-health-sample.md --metrics template/scripts/decks/tests/fixtures/metrics_planning.json`. To support it, `deck.py lint` also accepts a `--metrics` file in place of `--run`.
- [ ] **Step 3:** Mention the deck builder in `docs/SPEC.md` under pillar 6, linking the spec.
- [ ] **Step 4:** Run the full CI script list locally and confirm everything passes.
- [ ] **Step 5: Commit** `ci: run deck-builder tests and lint the sample deck`.

---

## Task 11 (blocked until `feat/brownfield-installer` merges): installer profile

- [ ] Add `scripts/decks/**`, `docs/decks/**`, `docs/brand/**` and `.claude/skills/deck-builder/**` to the `full` profile in `scripts/install/file-classes.json`. Classify `docs/decks/decks.config.json` and `docs/brand/**` as `seed`.
- [ ] Run the installer tests (`scripts/install/tests/`) and a dry run into a temporary repo with `--profile full`.
- [ ] **Commit** `feat(install): ship deck-builder in the full profile`.

---

## Self-review checklist (before opening the PR)

- [ ] Every number on the sample deck traces to a metric id, and every metric traces to snapshot rows.
- [ ] Removing the Bitbucket config turns slide 2 into "Not measured: …". It never shows zero.
- [ ] No `.pptx`, `.potx` or brand binaries are staged (`git status --ignored`).
- [ ] The rendered sample was inspected visually: no italics, no outlines or shadows, only palette colours, footer present, closing slide in place of "Thank you".
- [ ] `export_jira.py` behaviour and its tests are unchanged.
- [ ] The spec's open questions (§14) are copied into the PR description for the Frequentis owners.
