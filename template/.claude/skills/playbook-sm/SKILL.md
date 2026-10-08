---
name: playbook-sm
description: The Scrum Master / Team Coach seat's role contract in a SAFe setting — what it owns end-to-end, co-owns and with whom, deliberately doesn't touch, and how it works with the other seats and with AI. Invoke whenever someone wants to reason from, act as, or get the Scrum Master's perspective, or to settle a "who owns / who decides" question about team events, PI Planning preparation, PI objectives, team flow, impediments, ART Sync / Scrum of Scrums, Inspect & Adapt, or coaching the team.
metadata:
  seat: "SM"
  status: "draft"
  classification: "internal"
  ai-trust: "working"
  owner: "Architect"
---

# Playbook: Scrum Master / Team Coach

This is the role-seat contract for the **Scrum Master / Team Coach** seat on `<PROJECT_NAME>`, framed by SAFe (Scaled Agile Framework). The seat is a servant leader and coach: it helps the team deliver value in a steady flow, improve how it works, and plan and align with the rest of its Agile Release Train (ART).

## §1 — Mandate

### 1.1 Owns end-to-end (sole decision)

1. Facilitating the team events: iteration planning, daily stand-up, iteration review, iteration retrospective, and backlog refinement when the team asks for it.
2. The team's impediment log: every impediment has an owner, an age and a next step, and is escalated when the team cannot remove it.
3. Visibility of team flow: the team board, work-in-progress limits, and flow measures with their definition, source and period.
4. Preparing the team for PI Planning and supporting it during the event: capacity, the team's draft plan, risks and dependencies.
5. Representing the team at the ART Sync / Scrum of Scrums: progress towards PI objectives, dependencies, impediments that need the train's help.
6. Coaching the team in its agreed agile practices, and running improvement items through to done.

### 1.2 Co-owns (with named partner)

| Item | Co-owner | Meaning |
|------|----------|---------|
| Team PI objectives | Product Owner + team | The team drafts and commits; the Product Owner brings business value; the SM facilitates and checks they are specific, measurable and owned. |
| Inspect & Adapt participation | Release Train Engineer | The RTE runs the event; the SM brings the team's evidence and drives the team's improvement items. |
| Definition of Done | Team + QA | The team agrees it; the SM keeps it visible and used. |
| Risk handling (ROAM) | Team + RTE | The SM prepares the risks; the team and the train decide resolved, owned, accepted or mitigated. |

### 1.3 Deliberately doesn't touch

- Backlog content and priority — **Product Owner**.
- Technical design and the architecture — **Developers** and **Architect**.
- People management, appraisals and individual performance — out of this seat entirely.
- Commitments on the team's behalf: the team commits, the SM facilitates.

## §2 — Decision-rights cheat sheet

| # | Decision | Owner | Consulted | Informed | Escalation trigger |
|---|----------|-------|-----------|----------|--------------------|
| 1 | Format and agenda of a team event | SM | Team | Product Owner | The event repeatedly misses its objective |
| 2 | Escalate an impediment to the ART | SM | Team | RTE | The team cannot remove it within the iteration |
| 3 | Team PI objectives and their business value | Team + Product Owner | SM | Business owners | Objectives exceed the team's capacity |
| 4 | Which improvement items the team takes on | Team | SM | RTE | An item needs another team or the train |
| 5 | Work-in-progress limits on the team board | Team | SM | Product Owner | Flow measures worsen for two iterations |

## §3 — Working with other seats

**SM ↔ Product Owner** — Together they keep the backlog ready for planning; the SM protects the team's capacity and focus, the Product Owner decides what comes first.

**SM ↔ Team** — The SM serves the team: removes impediments, facilitates, coaches self-organisation, and never assigns work to individuals.

**SM ↔ Release Train Engineer** — The SM brings the team's view to the ART Sync / Scrum of Scrums, PI Planning and Inspect & Adapt, and takes the train's decisions back to the team.

**SM ↔ Engineering Manager / Architect** — Technical impediments and enabler work are raised early, so they reach planning with an owner.

**Escalation** — An impediment the team and the SM cannot remove goes to the RTE; if the train cannot remove it either, to the `<DIRECTOR / SPONSOR>`.

## §4 — Working with AI (Roles × Skills × MCP)

Ties to the board's Roles × Skills × MCP matrix. See [`AGENTS.md`](../../../AGENTS.md) and [`WORKING-AGREEMENT.md`](../../../WORKING-AGREEMENT.md). AI is a `working`-trust collaborator for this seat: it prepares, the people decide.

- **Invokable skills** — this playbook; `ai-sdlc-playbook-product` (if you have it) for backlog questions; `ai-sdlc-skill-creator` (if you have it) to capture a reusable facilitation pattern.
- **What AI prepares** — in personal setup, the Scrum Master instructions (`ai-sdlc-sm.instructions.md`) list it item by item; this playbook says who owns and decides. In short: flow and impediment signals, event and PI Planning preparation, Inspect & Adapt evidence and ROAM drafts.
- **Hard line** — signals about the work and the team, never judgements about individual people: no scores, rankings or guesses about anyone's motives, mood or ability.
- **Evidence, not verdicts** — every number has a definition, a source and a period; no cause-and-effect claim without them.
- **Scoped writes only** — AI drafts; the SM or the team publishes. It never changes the board, commits a PI objective or closes an impediment on its own.

## §5 — Definition of done for this seat's artefacts

- Every impediment has an owner, an age and a next step; escalated ones name where they went.
- PI objectives are specific, measurable, owned and linked to features, with business value set by the business owners.
- Flow measures state their definition, source and period.
- Retrospective and Inspect & Adapt actions have an owner and a review date, and are followed up.
- Event outputs (decisions, risks, actions) are recorded where the team keeps them, per [`WORKING-AGREEMENT.md`](../../../WORKING-AGREEMENT.md).
