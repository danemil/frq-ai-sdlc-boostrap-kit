---
title: "Commit-attribution convention"
status: approved
owner: EM
author: AI-SDLC Bootstrap Kit
created: 2026-07-02
classification: internal
last-reviewed: 2026-07-02
ai-trust: working
---

# Commit-attribution convention

To make AI usage measurable (pillar 7 — the dashboard and retro loop), every commit is classifiable as **human**, **AI**, or **mixed**. The dashboard's `commits` table and `collect_commits.py` implement this.

## Line-level signal — notes at `refs/notes/ai`, when present

When a commit carries a line-level authorship note in git notes at **`refs/notes/ai`** (format `authorship/3.0.0`): an attestation block mapping files to `s_…` (AI session) / `h_…` (human) line ranges, a `---` divider, then JSON metadata (agent tool, model, author), the collector uses it and marks the commit `source: git-ai` in the dashboard. The kit does not install anything that writes these notes; without them, every commit falls back to the trailer below.

- Sync notes with the team, where a repo has them: `git fetch origin 'refs/notes/*:refs/notes/*'`.
- The collector reads these notes with plain `git notes --ref=ai show <sha>` — **no extra tool is required on the machine running the dashboard.**

Per commit: **ai** (only AI lines), **human** (only human/untracked lines), **mixed** (both).

## Fallback — the `Co-Authored-By` trailer

Commits without such a note (the default, and all existing history) are classified from the commit trailer: an AI `Co-Authored-By:` (name/email matching `anthropic`/`claude`/`copilot`/`cursor`/`windsurf`/`bot`) → **ai-assisted**; otherwise **human**. This is coarser (commit-level, not line-level) and is marked `source: trailer` in the dashboard.

## Reading it

`python3 dashboard/collect_commits.py` populates the `commits` table; the dashboard's **Commit attribution** tab shows AI/mixed/human volume next to the utilization **rework** rate — volume is never read alone. Deep defect-linkage (which bug fixed which AI-authored code) is Phase 4 (knowledge graph).
