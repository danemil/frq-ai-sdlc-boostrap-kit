# Design system — the "ivory + clay" visual language

Every page you generate uses this exact system. It is the shared DNA of all 20 gallery examples; consistency here is what makes output instantly readable and recognizable.

## Document skeleton

- Single self-contained `.html` file. No build step, no external assets, no CDN, no web fonts, no libraries.
- All CSS in one inline `<style>` in `<head>`. All JS (if any) in one small `<script>` at end of `<body>`, vanilla only.
- `<title>` is a concrete artifact title ("Debounced search — three approaches"), never generic.
- Reset is exactly: `* { margin: 0; padding: 0; box-sizing: border-box; }` plus `html { scroll-behavior: smooth; }` when using anchor navigation. Nothing else.

## Color tokens (exact hex — do not improvise)

```css
:root {
  --ivory:    #FAF9F5;   /* page background, always */
  --slate:    #141413;   /* headings, dark code-panel bg, strong text */
  --clay:     #D97757;   /* THE accent: focus, attention, primary, "look here" */
  --oat:      #E3DACC;   /* warm beige: numbered chips, neutral badges, avatars */
  --olive:    #788C5D;   /* good / add / done / success / pro */
  --rust:     #B04A3F;   /* delete / failure / negative (diffs, error paths) */
  --gray-150: #F0EEE6;   /* inline-code bg, subtle panels */
  --gray-300: #D1CFC5;   /* default border color everywhere */
  --gray-500: #87867F;   /* muted text, captions, labels */
  --gray-700: #3D3D3A;   /* body text */
  --white:    #FFFFFF;   /* card surfaces */
}
```

Semantic mapping (never deviate):
- **olive** = good / addition / done / safe / pro / success branch
- **clay** = accent / attention / blocking / primary action / "the important spot"
- **rust** = deletion / failure / negative / error branch (dashed strokes in diagrams)
- **oat** = neutral badge, numbered section chip
- Tinted badge pairs: high/danger bg `#F3D9CC` text `#8A3B1E`; low/success bg `#E4E9DC` text `#4B5C39`; medium uses oat bg + slate text.
- Alpha tints from brand colors for soft fills: `rgba(217,119,87,.14)` clay, `rgba(120,140,93,.16)` olive, `rgba(176,74,63,.10)` rust.
- Warm gold `#C9B98A` = identifiers in dark code panels.

## Typography (the strongest style signal)

```css
--serif: ui-serif, Georgia, 'Times New Roman', serif;
--sans:  system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
--mono:  ui-monospace, 'SF Mono', Menlo, Monaco, monospace;
```

Three-way rule: **serif for all headings** (h1–h3, card titles, figure captions), **mono for anything machine/meta** (eyebrows, file paths, badges, stats, timestamps, code, numeric chips), **sans for prose**.

- Body: 14.5–15.5px, line-height 1.55–1.65, `-webkit-font-smoothing: antialiased`.
- h1: 30–38px, **font-weight 500 (never 700)**, `letter-spacing: -0.01em`, color `--slate`.
- h2: 21–26px w500 serif; h3: 18–19px w500 serif.
- Eyebrow/kicker: mono 11px, uppercase, `letter-spacing: 0.08em`, `--gray-500`, slash-separated breadcrumb ("Acme / prototype / interaction").
- Emphasis in prose = `<strong>` recolored to `--slate`, never heavier headings.

## Layout

- `.page { max-width: <W>; margin: 0 auto; }` — 760–980px for reading/figure sheets, 1040–1120px for plans/tools, up to 1360px for 3-column comparisons. Header prose constrained to ~680px even inside wide pages.
- Body padding: 48–56px top, 24–32px sides, 80–120px bottom.
- Section rhythm: `margin-bottom: 40–64px`. Spacing on a loose 4px scale.
- CSS Grid + Flexbox only. `position: sticky` for toolbars/TOCs/detail panels; `position: absolute` only for tags, drop indicators, timeline dots.
- Responsive: collapse multi-column grids to `1fr` at 720/900/960px breakpoints; hide sidebars/TOCs on narrow screens.

## Surfaces

The one card recipe everything is built from:

```css
background: var(--white);
border: 1.5px solid var(--gray-300);   /* signature: 1.5px, not 1px */
border-radius: 12px;
padding: 16–28px;
```

- **No drop shadows at rest.** Flat + hairline borders. Shadow only as transient JS focus ring (`box-shadow: 0 0 0 3px rgba(217,119,87,.35)`).
- Radius scale: 12px cards, 8px chips/buttons/inputs, 6px tags, 4px inline code, 999px pills, 50% dots/avatars.
- Callout = white card + `border-left: 4px solid var(--clay)` (recommendation, TL;DR, gotcha, open question). Asymmetric radius `0 12px 12px 0` when the accent border is flush left.

## Badges & chips

- Numbered section chip: mono 12px, oat bg, slate text, `padding: 2px 8px`, radius 8px, zero-padded ("01", "02").
- Metadata chip: mono 11–12px, `--gray-150` bg, 1.5px `--gray-300` border, radius 6–8px.
- Status badge: uppercase mono ~11px, `letter-spacing: .06em`, w600, tinted bg + matching dark text (pairs above).

## Code blocks

```css
.code { background: var(--slate); border-radius: 12px; padding: 16px 20px; overflow-x: auto; }
.code pre { font-family: var(--mono); font-size: 12.5px; line-height: 1.65; color: #E8E6DE; }
```

Syntax highlighting is hand-authored spans, no library: `.kw` keywords → clay, `.str` strings → olive-ish `#A8BC8C`/olive, `.cm` comments → `--gray-500`, `.fn` identifiers → gold `#C9B98A`. Escape HTML entities by hand. Diff lines inside code: `.add { background: rgba(120,140,93,.22); display:inline-block; width:100%; }`, `.del { background: rgba(217,119,87,.18); text-decoration: line-through; }`.

Inline code in prose: mono ~0.92em, `--gray-150` bg, `padding: 1px 5px`, radius 4px.

## Header pattern (every page opens this way)

1. Eyebrow: mono uppercase breadcrumb OR gray repo/meta line.
2. Serif h1, concrete and declarative, often counted: "Three ways to implement…", "How authentication flows through…".
3. One supporting sentence (gray-500, max-width ~640px) or a metadata row.
4. Only when the person asks for it (never by default on a team deliverable): a `.prompt-box` — gray-150 card, mono uppercase "PROMPT" label, the request paraphrased in their voice.

## Theme

Light only (ivory bg). Dark `--slate` surfaces are a *device* (code panels, emphasized diagram nodes), not a mode.
