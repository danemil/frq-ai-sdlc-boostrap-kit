---
title: "Brownfield adoption + multi-harness installer (design)"
status: approved
owner: Architect
author: Technical Architecture Council session
created: 2026-08-28
classification: internal
ai-trust: working
---

# Brownfield adoption + multi-harness installer

**Goal.** Replace the greenfield-only `bootstrap.sh` with a single installer that adopts
the kit into an **existing, populated repo**: detects what is already there, asks the
operator on every conflict, merges structured config instead of clobbering it, is
**idempotent and re-runnable** (upgrade path), and wires up **every AI harness present**
— Claude Code, Codex CLI, GitHub Copilot CLI — from one source of truth.

**Framing.** Greenfield is the degenerate case of brownfield (zero conflicts). There must
be **one code path**, not two, or the two will drift — the same argument the kit already
makes for `AGENTS.md` vs `CLAUDE.md`.

---

## 1. The problem with `bootstrap.sh` today

| # | Defect | Consequence |
|---|---|---|
| 1 | `tar -xf` over the target | Silently clobbers an existing `AGENTS.md`, `CLAUDE.md`, `.mcp.json`, `.claude/settings.json`. |
| 2 | Refuses non-empty dir unless `--force`; `--force` means "clobber" | No middle ground between *abort* and *destroy*. |
| 3 | `git init && git add -A && git commit` unconditionally | In a populated workspace this commits build artefacts, archives, `node_modules`. |
| 4 | No record of what it wrote | Re-running cannot distinguish *kit changed* from *user edited*. No upgrade path, no uninstall. |
| 5 | `sed` placeholder substitution, unvalidated | Unfilled `<PLACEHOLDERS>` ship silently; cannot re-render on kit upgrade. |
| 6 | Claude Code assumed as the only harness | `.claude/settings.json` + `.mcp.json` are the sole wiring; Codex and Copilot get `AGENTS.md` by luck, nothing else. |

---

## 2. Verified harness matrix (measured 2026-08-28, not assumed)

| Surface | Claude Code 2.1.250 | Codex CLI 0.137.0 | Copilot CLI 1.0.81 |
|---|---|---|---|
| Brief | `CLAUDE.md` → `AGENTS.md` | **`AGENTS.md` native** | **`AGENTS.md` native** (+ `.github/copilot-instructions.md`) |
| Skills | `.claude/skills/<n>/SKILL.md` | `.codex/skills/` | `.github/skills/`, `.agents/skills/`, **`.claude/skills/`** |
| MCP | `.mcp.json` | `.codex/config.toml` `[mcp_servers.*]` | `~/.copilot/mcp-config.json`, or `--additional-mcp-config @<file>` |
| Hooks | `.claude/settings.json` | `.codex/config.toml` (hooks; `SessionStart`) | *(none)* |
| Repo trust | — | `[projects."<abs>"] trust_level` | `--add-dir` |

Evidence: `copilot skill --help` enumerates the three project skill dirs; the Codex binary
documents *"Project `.codex/config.toml` -> trusted-repo Codex settings such as sandbox,
MCP, hooks, model, or reasoning defaults"* and embeds a `hooks.json` schema with
`SessionStart` / `hook_event_name` / `stop_hook_active`.

**Two consequences that shape the whole design:**

1. **All three read `AGENTS.md` natively.** The kit's "one brief, every tool" bet is
   already correct. Portability is therefore *not* a briefing problem — it is only a
   **skills + MCP + hooks** problem.
2. **Copilot CLI reads `.claude/skills/` directly.** The kit's `playbook-*` skills work in
   Copilot with **zero** additional files. Codex needs `.codex/skills`, which is one
   symlink — not a copy.

---

## 3. Decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Entry points | **One installer**, `install.sh` → `scripts/install.py`. `bootstrap.sh` becomes a thin back-compat wrapper (`--into <empty dir>`). One code path. |
| 2 | Idempotency mechanism | **Manifest** at `.ai-sdlc/manifest.json`: kit version, and for every managed path its class + the SHA-256 the installer last wrote. Re-run compares *on-disk hash* vs *manifest hash* to tell "user edited" from "kit changed". |
| 3 | Merge strategy | **Three file classes**, not one strategy. `own` (kit-owned) / `seed` (kit starts it, user owns it) / `merge` (structured, key-level combine). Declared once in `manifest-classes.json`. |
| 4 | Conflict UX | Per-file prompt: `[k]eep mine · [t]ake kit's · [m]erge · [d]iff · [a]ll-keep · [A]ll-take`. **Default `keep`.** Non-interactive writes a `.kit-new` sidecar (the `pacnew` model) and lists them in the summary. |
| 5 | Harness support | **Adapter table as data**, not code: `harnesses.json` maps harness → detection probe + the four surface paths/formats. Adding Cursor/Gemini/opencode is a table row. |
| 6 | Single source of truth | `.mcp.json` and `.claude/skills/` are **canonical**. Codex/Copilot surfaces are **generated or symlinked** from them, inside sentinel blocks, and a CI gate fails on drift — the same rule that already protects `CLAUDE.md`. |
| 7 | Dependencies | **Python 3 stdlib only** (already required by the kit's validators). TOML is *read* with `tomllib`; TOML is *written* as an append-only sentinel block — no `tomli-w`, no `yq`, no `jq`. |
| 8 | Git posture | **Never** `git init`/`git add -A` implicitly. Detect; if not a repo, offer and let the operator decline. Governance gates live in pre-commit + CI, which work regardless. |
| 9 | Scope control | `--profile minimal \| standard \| full`. `minimal` = brief + skills + validators; `full` adds dashboard, spend, jira. Anti-bloat is a stated kit principle; honour it at install time. |
| 10 | Verification | `install.py --dry-run` (plan only, zero writes), `--uninstall` (manifest-driven), and a `doctor` command. |

---

## 4. File classes

| Class | Meaning | On re-run, file unchanged since install | On re-run, file edited by user |
|---|---|---|---|
| **own** | Kit owns it end-to-end; no user content expected. `scripts/**`, `.claude/skills/**`, `.claude/rules/**`, `.github/workflows/ai-governance.yml`, `dashboard/**`, `INDEX.md`, `FOLDER-INDEX.md` | Overwrite silently (this is the upgrade path) | **Prompt** |
| **seed** | Kit provides a starting point the user is *expected* to rewrite. `AGENTS.md`, `CLAUDE.md`, `ONBOARDING.md`, `WORKING-AGREEMENT.md`, `README.md`, `docs/**/README.md` | Leave alone | Leave alone; report if the kit's version moved |
| **merge** | Structured config that must combine. `.mcp.json`, `.claude/settings.json`, `.codex/config.toml`, `.gitignore`, `.pre-commit-config.yaml` | Re-merge (idempotent) | Re-merge; kit keys namespaced, **user keys never dropped** |

Merge semantics per format:
- **JSON objects** (`.mcp.json`): union by key. Kit key already present with different value → prompt.
- **JSON hook arrays** (`.claude/settings.json`): append kit entries tagged `"_aiSdlc": true`; re-run replaces only tagged entries. Existing user hooks (e.g. the `code-review-graph` `PostToolUse`) survive untouched.
- **Line files** (`.gitignore`): append inside `# >>> ai-sdlc >>>` / `# <<< ai-sdlc <<<` sentinels.
- **TOML** (`.codex/config.toml`): append inside `# >>> ai-sdlc >>>` sentinels; read-verify with `tomllib`.

---

## 5. Harness adapter table (shape)

```jsonc
{
  "claude-code": {
    "detect": ["cmd:claude", "path:.claude"],
    "brief":  { "path": "CLAUDE.md", "kind": "pointer" },
    "skills": { "path": ".claude/skills", "kind": "canonical" },
    "mcp":    { "path": ".mcp.json", "format": "json", "kind": "canonical" },
    "hooks":  { "path": ".claude/settings.json", "format": "json-hooks" }
  },
  "codex-cli": {
    "detect": ["cmd:codex", "path:.codex"],
    "brief":  { "path": "AGENTS.md", "kind": "native" },
    "skills": { "path": ".codex/skills", "kind": "symlink", "to": ".claude/skills" },
    "mcp":    { "path": ".codex/config.toml", "format": "toml-block", "from": ".mcp.json" },
    "hooks":  { "path": ".codex/config.toml", "format": "toml-block" }
  },
  "copilot-cli": {
    "detect": ["cmd:copilot", "path:.github/copilot-instructions.md"],
    "brief":  { "path": "AGENTS.md", "kind": "native" },
    "skills": { "path": ".claude/skills", "kind": "native-reuse" },
    "mcp":    { "path": ".copilot/mcp-config.json", "format": "json",
                "from": ".mcp.json", "note": "pass with --additional-mcp-config @<path>" },
    "hooks":  null
  }
}
```

`kind: "native"` / `"native-reuse"` = **write nothing**; the harness already reads the
canonical artefact. That is the design working: three harnesses, one brief, one skills
tree, one MCP file.

---

## 6. Degradation contract

Copilot CLI has no hook system, so the session ritual cannot be hook-dependent for
correctness. Rule:

> **Governance lives in git + CI. Convenience lives in harness hooks.**

`scripts/session/*.sh` stay the interface and are invocable by hand everywhere. Hooks
(Claude Code, Codex) only make them automatic. The load-bearing gates —
`validate-skills.py`, `validate-frontmatter.py`, `check-brief-churn.py`, the commit-msg
ticket check — run from pre-commit and `ai-governance.yml`, which every harness inherits
for free.

---

## 7. Improvements bundled with this change

1. **`doctor`** — reports detected harnesses, wired surfaces, generated-file drift,
   missing prerequisites, and remaining `<PLACEHOLDERS>`. Exit non-zero in CI.
2. **`project.json`** — name / slug / ticket / language / seats / sponsor, rendered into
   the templates. Replaces blind `sed`, and makes re-render possible on kit upgrade.
3. **`--upgrade`** — re-runs class `own` only, against the manifest. Turns the kit from a
   one-shot copy into something maintainable across N repos.
4. **Drift gate** — CI check that regenerated Codex/Copilot surfaces match `.mcp.json`;
   same anti-drift rule the kit applies to `CLAUDE.md`.
5. **Profiles** — `minimal` / `standard` / `full`, so a small repo is not handed a
   dashboard, a spend importer, and a JIRA exporter it will never run.

---

## 8. Explicitly rejected

| Rejected | Why |
|---|---|
| A real 3-way merge engine for prose | Cost far exceeds value; `.kit-new` sidecars + `diff` cover it. |
| Per-harness plugin packages / separate repos | One kit, one script; adapters are data. Distribution without a distribution problem. |
| Rewriting the whole installer in Bash | JSON/TOML merging in Bash needs `jq`+`yq`; Python 3 is already a kit dependency. |
| `tomli-w` / any third-party dep | Sentinel-block append is enough and keeps the stdlib-only posture. |
| Auto-fanning the brief into `GEMINI.md`, `.cursorrules`, `.windsurfrules` | That is precisely the duplication the kit exists to prevent. Emit **pointers**, not copies. |

---

## 9. What shipped

| Path | Role |
|---|---|
| `install.sh` | Entry point. `--into`, `--profile`, `--harness`, `--dry-run`, `--yes`, `--take-kit`, `--sync`, plus `doctor` / `uninstall`. |
| `scripts/install/adopt.py` | Orchestration: render, plan, resolve conflicts, apply, wire harnesses, doctor, uninstall. |
| `scripts/install/plan.py` | Decides an action per file; reads only, so `--dry-run` is truthful. |
| `scripts/install/manifest.py` | `.ai-sdlc/manifest.json` and the six-state machine. |
| `scripts/install/file-classes.json` | Class + profile membership, as data. |
| `template/scripts/harness/sync.py` | Detection, pointer text, and the canonical→derived translations. **Lives in the template** so a generated repo can drift-check itself with no kit checked out. |
| `template/scripts/harness/merge.py` | JSON / hook-array / sentinel-block / TOML mergers. |
| `template/scripts/harness/harnesses.json` | The adapter table. |
| `scripts/install/tests/` | 70 tests, wired into the kit's CI. |

Two corrections the build forced:

1. **`hooks = "./hooks.json"` cannot be appended.** A bare TOML key written after a
   `[table]` header belongs to that table, not the document root — so Codex would
   never have seen it. `merge.set_toml_root_key` writes root keys above the first
   table *and* above our own sentinel block.
2. **Servers with unfilled placeholders must not be emitted.** The template ships
   `docs-wiki` with `<DOCS_WIKI_MCP_URL>`; generating that into Codex and Copilot
   would make both dial a bogus endpoint every session. They are skipped, and
   `doctor` names them.

Added beyond the original design, because first contact with a real repo demanded it:

3. **A ratcheting frontmatter baseline.** Any repo adopting the kit inherits docs
   written before the contract existed — nine of them in the first real adoption.
   A gate that is red on day one gets switched off, so `validate-frontmatter.py`
   gained `--write-baseline`: inherited violations are recorded once and reported
   as `debt`, **new** violations still fail, and `doctor` keeps the list visible so
   it cannot quietly become permanent.
4. **Legacy rules paths are pointed too** (`also:` in the adapter). Cursor reads
   `.cursor/rules/*.mdc` *and* `.cursorrules`; leaving the latter holding a stale
   copy of the brief is exactly the drift the kit exists to prevent.
5. **`doctor` always scans `AGENTS.md`**, even though seed files are unmanaged by
   design — it is the one file whose placeholders matter most.

## 10. Deliberate technical debt

- **Symlinked `.codex/skills`** breaks on Windows without developer mode. Exit criterion:
  first Windows adopter → fall back to copy + drift gate.
- **Copilot MCP needs a CLI flag** (no project auto-discovery in 1.0.81). Exit criterion:
  Copilot ships project-level MCP discovery → drop the generated file, mark `native`.
- **`--uninstall` only reverses class `own` + sentinel blocks.** `seed` files are the
  user's by then and are left in place, reported not removed.

## 11. Verification

- **70 unit + end-to-end tests**, run in the kit's CI: greenfield, brownfield with
  pre-existing config, idempotency, conflict deferral, `--take-kit`, uninstall,
  standalone drift-check, and the frontmatter ratchet.
- **Copilot's MCP schema checked against the binary, not the docs.** `copilot mcp add`
  run under an isolated `HOME` emits an entry byte-identical to the generator's.
- **Codex's TOML** is verified with `tomllib` on every write, and the shipped binary's
  own strings confirm `.codex/config.toml`, `.codex/skills`, the `hooks` config key and
  the event names used.
- **First real adoption**: `FRQ-COBOL-sample`, a populated non-git workspace with six
  pre-existing harness configs. 129 files created, 3 merged, 0 conflicts, nothing of
  the operator's lost. A second run compared **763 files and changed none**.
