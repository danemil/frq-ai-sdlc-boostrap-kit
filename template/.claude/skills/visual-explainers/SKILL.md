---
name: visual-explainers
description: Explain a concept as a self-contained HTML explainer — spatial layout, inline SVG diagrams, interactive demos — using proven HTML explainer patterns. Use when the user wants a concept, system, process, tradeoff, plan, or comparison explained or taught visually, asks for an "HTML explainer" or "visual explanation", or another skill needs a rendered artifact instead of markdown.
---

# Visual explainers

Produce one self-contained `.html` **explainer** for the given concept. The thesis: markdown flattens spatial information; an explainer trades a document the reader would skim for one they actually read.

## Steps

### 1. Frame
Name what is being explained, who reads it, and **what the reader would otherwise have to hold in their head** — a flow, a tradeoff, a counterintuitive claim, an architecture, terminology, motion. Done when that burden is stated in one sentence; it selects the pattern.

### 2. Pick patterns
Read [`references/patterns.md`](references/patterns.md) — 9 families / 20 patterns with a concept→pattern chooser table. Compose 2–4 patterns (e.g. intro prose + SVG flow diagram + comparison table + hover-linked glossary). Hard requirements:

- At least one true visual representation: inline SVG diagram, interactive demo, or spatial comparison. A prose-only page fails the skill.
- A quantifiable claim ("only K/N keys move") gets an interactive demo whose **quantified readout** proves the claim on every user interaction.
- An editor/tool page ends with a Copy/export button serializing state back to pasteable text.

Done when each chosen pattern maps to a stated reader burden.

### 3. Build
Start from [`assets/starter.html`](assets/starter.html); apply [`references/design-system.md`](references/design-system.md) for tokens/typography/surfaces and [`references/recipes.md`](references/recipes.md) for SVG idioms and the vanilla-JS toolkit. Non-negotiables:

- One file, zero external assets: inline `<style>`, inline vanilla `<script>`, system fonts, no CDNs or libraries (no mermaid, no chart libs — diagrams are hand-placed inline SVG).
- The exact ivory/slate/clay palette with its semantic mapping: olive = good/success, clay = accent/attention, rust = failure/deletion, oat = neutral. Never invent colors.
- Serif headings (weight 500) / mono metadata / sans prose; white cards with 1.5px `--gray-300` borders; clay left-border callouts.
- Header: mono uppercase eyebrow → serif h1 → gray sub-sentence. No `.prompt-box` echoing the request on a team deliverable; add one only when the person asks for it.
- Interaction preference order: native HTML (`<details>`, checkboxes, anchors) → CSS-only → small vanilla JS. Demos are deterministic (FNV-1a hash, never `Math.random()`).
- **Company brand by default:** load the `ai-sdlc-frq-brandbook` skill. If it is in your skill list, it is installed. Read its files by exact path (`.agents/skills/ai-sdlc-frq-brandbook/…`). Never decide by glob or search: the folder is hidden from git, so search tools skip it. Its palette, fonts, logo and classification footer (`references/documents.md`, HTML) replace the ones above, unless the person asks for the plain style.
- Voice: concrete counted titles ("Three ways to…"); oat-chip section numbers ("01"); every con paired with a mitigation or "choose otherwise when…"; recommendations name one winner in bold with a revisit condition.

Done when the page renders correctly offline and every color on it carries its semantic meaning.

### 4. Deliver
Save the file as `docs/explainers/<topic>-explainer.html` in the person's repo (create the folder if needed), or wherever the person asks. Show the file name before you save it. Then tell the person the path and how to open it: open the file in any browser (double-click it, or drag it into a browser window); in VS Code, right-click the file and use the "Open in browser" or Live Preview option if their editor has one. Nothing is uploaded or published: the file is self-contained, so it can be shared by sending the file itself.

Done when the final check passes: *would the reader still need a markdown version?* If yes, the page hasn't earned its format — revise before you report the path.
