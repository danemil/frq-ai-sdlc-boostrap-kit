# Recipes — SVG diagram idioms and the vanilla-JS toolkit

Copy these idioms verbatim; they are the gallery's exact techniques.

## SVG diagrams (hand-placed coordinates, no libraries)

General conventions:
- `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 320">` for landscape figures; `viewBox="0 0 620 920"` portrait for flowcharts. Make fluid with `svg { display:block; width:100%; height:auto; }`.
- First child: full-canvas `<rect width="720" height="320" fill="#FAF9F5"/>`.
- If downloadable/standalone: per-SVG `<defs><style>` declaring `.m` (mono 11px) and `.s` (sans 12px) font classes, and **hardcoded hex** (no `var()`). If page-bound (clickable flowchart), style via page CSS with `var()`.
- Strokes: 1.5px neutral, 2px emphasized. Boxes `rx="8"`–`rx="10"`, stadium terminals `rx="22"`. No gradients, no drop shadows.
- Labels: `text-anchor="middle"`, mono 11px inside boxes (`#3D3D3A` on light fills, `#FAF9F5` on dark), sans 12px `#87867F` annotation sentence outside/below.

### Node box
```html
<rect x="60" y="110" width="70" height="100" rx="10"
      fill="#F0EEE6" stroke="#3D3D3A" stroke-width="1.5"/>
<text x="95" y="164" text-anchor="middle" class="m" fill="#3D3D3A">job 5</text>
```
Fills by role: neutral `#F0EEE6` · emphasized/focus `#D97757` (stroke `#141413` @2px, label `#FAF9F5`) · container `#E3DACC` · success `#788C5D` (label ivory).

### Arrowheads + edges
```html
<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6"
          orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#87867F"/></marker>
  <!-- duplicate as #arrow-olive fill=#788C5D and #arrow-rust fill=#B04A3F -->
</defs>
<path class="edge" d="M310,56 L310,92"/>
```
```css
.edge     { stroke: var(--gray-500); stroke-width: 1.5; fill: none; marker-end: url(#arrow); }
.edge.yes { stroke: var(--olive); marker-end: url(#arrow-olive); }
.edge.no  { stroke: var(--rust); stroke-dasharray: 4 4; marker-end: url(#arrow-rust); }
```
Semantics: solid gray = main/sync path · olive = success branch · rust dashed = failure branch · clay dashed (`stroke-dasharray: 5 4`) = async/realtime fan-out. Edge labels are separate `<text class="lbl">` placed by hand next to the path. Straight = `M…L…`; branches/returns = cubic `C`; arcs = quadratic `Q`. `markerUnits="userSpaceOnUse"` keeps heads constant-size.

### Diamond gate
```html
<path d="M310,262 L352,294 L310,326 L268,294 Z"/>   <!-- (cx,cy-h)(cx+w,cy)(cx,cy+h)(cx-w,cy)Z -->
<text x="310" y="298" text-anchor="middle">pass?</text>
```

### Status glyphs
```html
<!-- fail: hollow clay circle + X -->
<circle cx="100" cy="190" r="8" fill="#FAF9F5" stroke="#D97757" stroke-width="2"/>
<line x1="96" y1="186" x2="104" y2="194" stroke="#D97757" stroke-width="1.5"/>
<line x1="104" y1="186" x2="96" y2="194" stroke="#D97757" stroke-width="1.5"/>
<!-- success: olive circle + white check -->
<circle cx="590" cy="190" r="9" fill="#788C5D" stroke="#141413" stroke-width="1.5"/>
<path d="M585,190 L589,194 L596,185" fill="none" stroke="#FAF9F5" stroke-width="1.5" stroke-linecap="round"/>
<!-- dashed backoff arc with label -->
<path d="M 100 182 Q 135 130 170 182" fill="none" stroke="#87867F" stroke-width="1.5" stroke-dasharray="4 4"/>
<text x="135" y="124" text-anchor="middle" class="m" fill="#87867F">+1s</text>
```

Fan-out/fan-in: N `<line>`s sharing one origin (fan-out) or one destination (fan-in), each with `marker-end`.

### Bar chart (reports)
Hand-authored `viewBox="0 0 640 180"`: gray gridlines, `<text>` axis labels, oat bars with the peak bar clay, value labels above bars. Document the math in an HTML comment (`baseline y=140, unit=40px`).

## Vanilla-JS toolkit (small, at end of body; prefer native HTML + CSS first)

Hierarchy of preference: native `<details>/<summary>`, radios/checkboxes, `#anchor` + `scroll-behavior:smooth` → then CSS-only (`:checked`, `[open]`, counters, `@keyframes`) → then ≤40 lines of vanilla JS.

### Controls driving CSS variables (live-tunable anything)
```js
const root = document.documentElement;
pad.addEventListener('input', () => {
  root.style.setProperty('--card-pad', pad.value + 'px');
  padOut.textContent = pad.value + 'px';
});
```
Consuming CSS just references `var(--card-pad)`. Call appliers once at load to sync. Same trick retimes whole animations via one `--ease` variable from `data-ease` buttons.

### Clickable diagram → detail panel
```js
const DETAIL = { push: {title, meta, body, code}, ci: {…} };
nodes.forEach(n => n.addEventListener('click', () => {
  nodes.forEach(x => x.classList.remove('active'));
  n.classList.add('active');
  const d = DETAIL[n.dataset.k];
  T.textContent = d.title; B.innerHTML = d.body; C.textContent = d.code;
}));
document.querySelector('.node[data-k="push"]').classList.add('active');  // default selection
```

### Deterministic interactive demo
Never `Math.random()` — use FNV-1a so positions are stable across reloads:
```js
function h(s){ let x = 2166136261; for (const c of s) { x ^= c.charCodeAt(0); x = Math.imul(x, 16777619); } return (x >>> 0) / 4294967296; }
```
The demo must end in a **quantified readout** proving the concept's claim (compare state before/after a change, print "N (X%) moved" in clay). Animate reassignment with CSS transitions on SVG attributes (300ms).

### Native drag-to-reorder / drag-between-columns
`draggable="true"`; `dragstart` stores id + adds `.dragging`; `dragover` calls `e.preventDefault()`, finds the first sibling whose vertical midpoint is below the cursor, positions a 2px clay indicator line at that gap; `drop` does `insertBefore` (or mutates the item's `col` and re-runs a full `render()`); `dragleave` guard: `if (!col.contains(e.relatedTarget))`.

### Keyboard slide nav
```js
document.addEventListener('keydown', e => {
  if (['ArrowRight','ArrowDown',' '].includes(e.key)) { e.preventDefault(); go(current + 1); }
  if (['ArrowLeft','ArrowUp'].includes(e.key))        { e.preventDefault(); go(current - 1); }
});
function go(i){ current = Math.max(0, Math.min(i, slides.length - 1)); slides[current].scrollIntoView({behavior:'smooth'}); }
```
Plus `body { scroll-snap-type: y mandatory }`, slides `scroll-snap-align: start; scroll-snap-stop: always`, and an `IntersectionObserver({threshold: 0.6})` syncing the "1 / 6" counter when the user scrolls manually.

### Export / copy button (editor invariant)
```js
function writeClipboard(txt, btn){
  (navigator.clipboard ? navigator.clipboard.writeText(txt) : Promise.reject())
    .catch(() => { const t = document.createElement('textarea'); t.value = txt;
      document.body.appendChild(t); t.select(); document.execCommand('copy'); t.remove(); })
    .then(() => flash(btn));
}
function flash(btn){ const old = btn.textContent; btn.textContent = 'Copied ✓';
  btn.classList.add('ok'); setTimeout(() => { btn.textContent = old; btn.classList.remove('ok'); }, 1200); }
```
Keep a frozen `INITIAL` state; `computeDiff()` = filter changed; serialize to markdown / JSON / diff text. `.ok` turns the button olive. Escape all data-driven `innerHTML` with an `esc()` helper; use `CSS.escape()` in attribute selectors.

### Download live SVG
```js
const src = new XMLSerializer().serializeToString(svg);
const url = URL.createObjectURL(new Blob([src], {type: 'image/svg+xml;charset=utf-8'}));
const a = Object.assign(document.createElement('a'), {href: url, download: btn.dataset.filename});
a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
```

### Glossary hover-linking
Inline `<span class="term" data-term="node">` (dotted clay underline, `cursor:help`); `mouseenter/mouseleave` toggles `.hl` (clay-tinted bg) on the sidebar `<dt data-g="node">` and its `+ dd`.

### CSS-only primitives (no JS needed)
Rotating `▸`/chevron off `details[open]`; toggle switch off `input:checked + .track` (olive, knob `translateX(16px)`, `:focus-visible` outline); checkmark drawn with two rotated borders in `::after`; speech-bubble arrow (rotated 45° square `::before`); CSS counters for numbered steps; transient focus ring `box-shadow: 0 0 0 3px rgba(217,119,87,.35)` cleared after 1400ms.
