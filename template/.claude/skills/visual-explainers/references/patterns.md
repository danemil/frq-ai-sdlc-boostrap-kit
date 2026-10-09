# Pattern catalog — the 9 families and when to reach for each

Each pattern replaces a specific kind of markdown wall. Pick the pattern by asking: *what would the reader otherwise have to hold in their head?*

## 01 Exploration & Planning
*When you're not sure what you want yet — fan out across directions and lay them next to each other so the reader can point at one.*

- **Side-by-side approaches** — 3 equal cards in one grid, each: numbered serif title → one-liner → dark code panel → pro/con table (olive dot = pro, clay dot = con) → mono stat chips (bundle kb, testability). End with ONE clay-left-border recommendation box that names the winner in bold, gives a codebase-specific reason, and a "revisit X only if…" clause.
- **Visual design directions** — 2×2 board of artboards; each artboard = corner tag ("A — Minimal"), a fixed-height stage that *renders the variant live*, a rationale caption. Optional light/dark segmented toggle flipping per-stage theme tokens.
- **Implementation plan** — summary strip (4 key/value cells) → numbered sections: Milestones (dot+connector timeline: clay ring = pending, olive fill = done) → Data-flow SVG diagram → Mockups (fake-but-realistic UI in labeled cards) → Key code (2-up file-labeled dark panels) → Risk table (Risk/Sev/Mitigation with tinted severity badges) → Open questions (clay callouts with a mono "Decide with · <owner>, before <deadline>" line).

## 02 Code Review & Understanding
*Diffs and call-graphs are spatial; markdown flattens them.*

- **Annotated PR review** — PR head card (repo line, h1, branch pill, +/− stat) → risk map (anchor chips colored safe/medium/attention linking to file cards) → per-file: path + risk tag → hand-built diff (grid rows: line-no / mark / code; `.add` olive tint, `.del` rust tint, `.hunk` header) → review-comment speech bubbles (`.blocking` clay border, `.nit` gray). Low-risk files collapse into `<details>`. Footer: interactive checkbox checklist of fixes.
- **PR writeup** — TL;DR clay callout → Why (before/after panels, after = olive border) → file-by-file `<details>` accordions (chevron, mono path, new/mod/del badge, serif "why" sentence, optional diff) → "Where to focus" numbered clay circles pointing at exact `file:line` → test plan (CSS checkboxes) → rollout (joined step segments: internal → 10% → 100%). Include one "What I deliberately did not do" item. Sticky TOC.
- **Module map / code understanding** — SVG architecture diagram (white boxes, the critical node `.hot` = clay tint) + numbered callstack walkthrough (circular badges, mono `file:line` locators, `<details>` "show source" snippets, exclusive-open accordion) + sidebar with Key files list and a Gotchas callout (full clay border + tint — strongest warning treatment).

## 03 Design
*HTML is the medium the design system ships in.*

- **Living design system** — sections Color / Typography / Spacing / Radius & Elevation / Components. Every token shown three ways: rendered specimen + hex (mono) + token name (mono). Type scale as specimen table with `size / line-height / weight` meta. Spacing as clay bars at literal px widths. Component gallery with live HTML elements in all variants.
- **Component variants** — all states of one component on one sheet: 3-col grid of labeled cells ("A · Flat", "best for: …") + sticky toolbar whose controls (slider/segmented/checkbox) drive `:root` CSS variables so every variant re-renders live + hover-to-inspect piping each cell's `data-snippet` JSX into a dark code panel.

## 04 Prototyping
*Motion and interaction can't be described, only felt.*

- **Animation sandbox** — one real interactive element (click to toggle the animated state) + easing buttons that swap a single `--ease` variable retiming the whole sequence + a keyframe timeline (2px track, absolute dots labeling each stage's ms) + copy-paste CSS block.
- **Clickable interaction** — the real interaction (e.g. native drag-to-reorder, ~40 lines vanilla JS) beside an annotation column: "What you're feeling" design-decision bullets + numbered "Open questions" in an oat box. The rationale column is the real content — the prototype exists so the reader can push back.

## 05 Illustrations & Diagrams
*Inline SVG gives the agent a real pen.*

- **SVG figure sheet** — 2–3 standalone `<figure>`s, each a 720×320 inline SVG with its own `<defs><style>` and background rect (so it exports standalone), serif caption + Download-SVG button (XMLSerializer → Blob). End with an explicit "Palette & rules" rubric.
- **Clickable flowchart** — one portrait SVG (`viewBox 0 0 620 920`, top-to-bottom) beside a sticky detail panel. Nodes = `<g class="node" data-k="…">`; clicking swaps `.active` and loads a `DETAIL[k]` object into the panel. Node semantics: process rect / stadium terminal (`rx:22`) / diamond gate / `.ok` olive tint / `.bad` rust tint. Edges: gray solid default, olive `.yes`, rust dashed `.no`, each with its own colored arrowhead marker. Legend row at bottom.

## 06 Decks
*A handful of `<section>` tags and twenty lines of JS is a slide deck.*

- **Arrow-key deck** — each slide a `100vw×100vh <section>`, CSS scroll-snap (`y mandatory`, `snap-stop: always`), keyboard nav via `scrollIntoView`, IntersectionObserver-synced "1 / 6" counter. `.slide.invert` (slate bg) for the decision slide. Content devices: olive-dot shipped lists, progress bars, metric grids (serif 52px numbers, olive/clay deltas), inline polyline sparklines, decision card with option chips (`.lean` = clay).

## 07 Research & Learning  ← the concept-explainer core
*Scaffolding that makes a new topic navigable.*

- **Feature explainer** — sticky left nav (anchor links + a mono "Files read" provenance list) → TL;DR clay callout → collapsible steps via native `<details>` (clay ▸ rotating on open, mono `file:line` ref right-aligned in each summary, first one `open`) → tabbed code samples (`.on` class swap) → oat callout with ★ → FAQ as semantic `<dl>`.
- **Interactive concept explainer** — the centerpiece for teaching abstractions. Structure: prose intro → **live parameterized demo** → comparison table (`.bad` rust / `.good` olive cells) → hover-linked glossary in a sticky sidebar. The demo pattern: an SVG model of the concept + range sliders/buttons that change its parameters + **a quantified readout that proves the concept's claim** (e.g. consistent-hashing ring: "7 (12%) keys moved on last change" in clay). Use a deterministic hash (FNV-1a), never `Math.random()`, so the demo is stable across reloads. Glossary: inline `<span class="term" data-term="x">` (dotted clay underline, `cursor:help`) hover-highlights the matching `<dt>` in the sidebar.

## 08 Reports
*Recurring documents benefit most from a bit of structure and color.*

- **Status report** — h1 + "auto-generated" pill + mono repo/date line → 4-up metric band (serif 44px numbers, uppercase labels, olive/gray deltas; one card `.warn` with clay left-border) → highlights → shipped `<table>` (mono clay PR links, risk dots olive/clay/rust) → hand-drawn SVG bar chart (oat bars, peak bar clay) → oat carryover panel (In review / Blocked / Slipped tags + owners) → mono footer citing sources.
- **Incident report** — mono incident id + severity/resolved pills → slate inverted TL;DR → **rail timeline**: 2px vertical rail, 12px dots punched through with ivory borders, dot color = event type (gray default, clay = impact starts, olive = mitigated), mono time chips, bold lead-ins ("**Impact starts.**") → root-cause code diff → impact key/value table → action items (CSS checkboxes + initials avatars + due dates).

## 09 Custom Editing Interfaces
*When it's hard to describe what you want in a text box — and always end with an export button.*

- **Triage board** — 4 columns from a JS `COLUMNS` array (color-coded border-top), ticket cards with native HTML5 drag-drop, tag-click filtering, live point rollups, "Copy as markdown" export.
- **Feature-flag editor** — pure-CSS toggle switches, `requires` dependency warnings (row turns clay + banner aggregates count), changed-vs-INITIAL dots, dual export: Copy diff (only changes, `- / +` lines) and Copy full JSON.
- **Prompt tuner** — contenteditable template with live `{{slot}}` highlighting (oat = known, dashed clay = unknown) + live preview resolving the template against 3 sample inputs simultaneously + Copy prompt.
- Editor invariants: keep a frozen `INITIAL` state, provide Reset, and **always end with a Copy/export button** that serializes UI state back into something pasteable into the next prompt. "You stay in the loop; the loop gets tighter."

## Choosing for a *concept explanation* (the primary use case)

Most concept explainers compose 2–4 patterns:

| The concept is… | Lead with |
|---|---|
| A process / lifecycle / pipeline | Clickable flowchart (05) or SVG figure sheet |
| An abstraction with a counterintuitive claim | Interactive concept explainer (07) — demo + quantified readout |
| A tradeoff between alternatives | Side-by-side approaches (01) with pro/con tables + recommendation |
| A system / architecture | Module map (02) — SVG boxes-and-arrows + numbered walkthrough |
| Something felt, not read (motion, UX) | Prototype (04) with annotation column |
| A body of terminology | Feature explainer (07) with hover-linked glossary |
| Numbers over time / status | Report devices (08): metric bands, SVG charts, rail timelines |
| Something the reader should manipulate | Editor (09) with export button |
