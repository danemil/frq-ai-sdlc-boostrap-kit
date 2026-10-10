# Bundled assets

Everything here comes from the official Frequentis PowerPoint template, through this kit (0.8.0) or the kit owner's frq-4-pptx-agent v1.0 (see `../PROVENANCE.md`); sizes, checksums, origin and placement are in `../assets/manifest.json`. These are Frequentis-owned brand materials: use them for Frequentis work only. For print or anything larger than a slide, ask Group Communications and Marketing (GCM) for the official logo download.

**Where they are.** Text files (the SVG logos, the gradient SVG, the CSS, the manifest) are placed with the skill. Every binary file (both templates, layout previews, examples, key visuals, side-bar JPEGs, logo PNGs) stays only in the kit copy, `.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/` (listed in `../.kit-only`). Open those by the exact path given here: search tools skip `.ai-sdlc/`. The scripts find them by themselves.

## Logos (`../assets/logo/`; the PNGs in `.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/logo/`)

**Preferred** (C15): the vector shapes of the template, converted shape for shape to SVG (not redrawn), plus 1200 px transparent PNG renders for tools that cannot place SVG (Word through python-docx, some e-mail clients).

| File | Use |
|---|---|
| `logo-frequentis-wordmark-blue.svg` / `.png` | **Preferred**: on white. Content pages, document headers, web pages |
| `logo-frequentis-wordmark-white.svg` / `.png` | On blue #004182 or a calm dark photo |
| `logo-frequentis-wordmark-black.svg` / `.png` | Only where blue or white is not legible (light photos, one-colour print) |
| `logo-frequentis-tagline-blue.svg` / `.png` | Logo with "FOR A SAFER WORLD" on white: title and closing pages, covers, roll-ups. Tagline in #666666 (C7) |
| `logo-frequentis-tagline-white.svg` / `.png` | The same on blue or the key visual |
| `logo-frequentis-tagline-black.svg` / `.png` | The same where blue or white is not legible |

A second set, `frequentis-logo-blue.svg`, `frequentis-logo-white.svg` and `frequentis-logo-black.svg` (the wordmark traced from the master's vector, owner skill v1.0), is kept too. Use it only where a converted file does not fit; GCM's official logo pack replaces both sets when it comes.

Rules: clear space at least the logo's height (the letter F) on every side; minimum height 5 mm (about 19 px on screen); never recolour, stretch, crop, outline, shadow or put text over it; never retype it. The tagline never appears without the logo. In decks the template already places the logo: do not add another.

## Key visuals (`.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/keyvisual/`)

Brand key visuals shipped in the template (licence for use outside Frequentis: confirm with GCM). Use them as the title or cover image, full or cropped; never replace them with stock photos.

| File | Business unit | Size |
|---|---|---|
| `keyvisual-corporate-globe-1080.jpeg` | Corporate and cross-BU; closing pages | 1080 × 1080 (downscaled from 1920) |
| `keyvisual-atm-aircraft.jpeg` | Air Traffic Management (**default**) | 860 × 860 |
| `keyvisual-defence-jets.jpeg` | Defence | 860 × 860 |
| `keyvisual-public-safety-police.jpeg` | Public Safety | 860 × 860 |
| `keyvisual-public-transport-train-860.jpeg` | Public Transport | 860 × 845 (downscaled) |
| `keyvisual-maritime-vessel.jpeg` | Maritime | 860 × 860 |
| `keyvisual-corporate-globe.jpg` | Corporate globe, full size (owner skill v1.0) | 1920 × 1920 |
| `keyvisual-public-transport.jpg` | Public Transport, full size (owner skill v1.0) | 1563 × 1536 |
| `keyvisual-atm-aircraft-clouds-wide.jpg` | ATM aircraft above the clouds, wide mood image (owner skill v1.0; rights to confirm with GCM before external use) | 1920 × 1251 |

**ATM is the default business unit** (C14): use the ATM key visual and wording unless the person names another unit. `frq_pptx.py build` and `new_deck.py` put it on the *Standard TITLE* slide by themselves (`--business-unit` for another unit). Prefer the smaller files; take a full-size one only where a large picture is needed.

## Backgrounds (`../assets/background/`; the JPEGs in `.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/background/`)

| File | Use |
|---|---|
| `bg-gradient-frequentis.svg` | The one gradient (#004182 → #00AAE1, bottom-left to top-right): web hero, document divider pages |
| `bg-sidebar-small.jpg`, `bg-sidebar-medium.jpg`, `bg-sidebar-wide.jpg` | Flat blue side bar on white (plain graphics from the side-bar layouts), 1500 × 844: Word or HTML covers. In decks, use the side-bar layouts instead |

## Templates (`.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/templates/`)

`frq-template-slim-core.pptx` (25 layouts, about 1.2 MB): the default base for new decks. `frq-master.pptx` (all 44 layouts, about 8.8 MB, personal and tenant metadata stripped): only when a slide needs a layout the slim one lacks. See `building-decks.md`.

## Layout previews (`.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/`)

One JPEG per layout of the full master, `01-standard-title.jpg` to `44-world-map-uk.jpg`; `layouts.md` links each. Look at it before using an unfamiliar layout.

## Example slides (`.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/examples/`)

22 example slides from the template's tips deck: telling a story, the message pyramid, the content area, fonts and writing, the gradient, don'ts, a numbered agenda, a simple table, four-column text, an org chart, phase chevrons, a numbered steps band, a project cycle, a history timeline, roadmaps, map highlights, a highlighted bar chart, KPI donuts, a donut chart and a Venn diagram. Open the matching one before drawing such a visual by hand (`build-spec.md`).

## Stylesheet (`../assets/frequentis-brand.css`)

CSS custom properties and base styles for HTML mockups, reports and diagrams (owner skill v1.0); its colours match `../brand-tokens.json` (a test checks it).

## Not bundled, on purpose

- **Photos** from the template's sample slides (stock-looking event pictures, archive and customer-site photos): rights unknown or not a brand key visual. (The wide ATM aircraft photo now ships, by owner decision, as an open item for GCM; pictures inside the full master's layouts stay as GCM made them.) Frequentis photos come from the Frequentis Photo stock through GCM (PDF p.35).
- **Portraits** of named people: personal data.
- **Third-party logos and banners** (a research programme logo, a customer banner): never redistribute.
- **Font files**: Arial is a system font; FF DIN is commercial; neither may be bundled.
- **Icons**: the template has none; icons come only from the Frequentis Icon Stock.
- Tutorial screenshots and "don't" examples from the template's guidance slides.

Need something that is not here (an icon, a product photo, the OneATM style guide, a logo pack for print)? Leave a placeholder with a note and ask the person to request it from GCM.
