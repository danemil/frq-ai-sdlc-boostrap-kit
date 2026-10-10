# Provenance: frq-brandbook

Written for this kit (2026-10-09) from brand materials the client owns and provided for this purpose. The skill text, `brand-tokens.json` and the scripts are MIT, like the rest of the kit. The logos, key visuals, backgrounds and template in `assets/` are **brand materials owned by Frequentis AG**: they are included so the team's own deliverables can be on-brand, and they are not licensed for any other use. Before the kit is shared outside Frequentis, Group Communications and Marketing (GCM) confirms that use.

## Sources

| Source | What it gave |
|---|---|
| *Frequentis Brand Guidelines Q4/2025* (51-page PDF, GCM) | The rules: palette (HEX, RGB, CMYK), fonts, logo, tagline, gradient, imagery, icons, writing rules, classification. The source of truth; cited as "PDF p.N" (PDF page index; from p.17 on the printed page number is N+1). |
| The official Frequentis PowerPoint template (*Corporate PowerPoint Essentials*, "FRQ-Template presentation.pptx": 1 master, 44 layouts, 66 sample slides) | The slide master, the "FRQ_CORP 2024" theme, layout names, placeholder indexes, sizes; the logo shapes and key visuals in `assets/`. Cited as "template". |
| The earlier internal Frequentis brand skill for Copilot in PowerPoint, v1.0 (2026-10-01), and its off-brand test deck | Create and Check (then "Apply") modes, the audit-then-confirm flow, Must-fix and Should-fix lists, the decisions on tints and register (C6), the six-slide off-brand deck now used as the checker's golden test (kept in the kit's tests, not in this folder). |

## What was extracted, and how

- **Facts**: read from the PDF and the template's XML, every fact cited in `references/brand-rules.md`. Contrast ratios computed (WCAG 2.x). Conflicts between the sources are listed (C1–C10) with the resolution this skill uses.
- **Logos**: the template draws the logo as vector shapes (the master's footer wordmark and the title layout's logo with tagline), not as image files. They were **converted shape for shape to SVG** (the same path coordinates, in EMU) and not redrawn; the blue, white and black variants differ only in fill colour. The PNGs are 1200 px renders of those SVGs made with rsvg-convert (a test checks their proportions and edge sharpness against the SVGs). They are a stand-in until GCM's official logo pack is available.
- **Key visuals**: the template's globe and five business-unit images, unchanged except that the globe (1920 → 1080 px) and the Public Transport image (1563 → 860 px) were downscaled to keep the skill small.
- **Backgrounds**: the three side-bar images are the template's own flat blue graphics; the gradient SVG is generated from the template's agenda layout gradient (#004182 → #00AAE1, 315°).
- **Slim template**: the template opened with python-pptx, all 66 sample slides removed and the map and event layouts dropped (25 of 44 layouts kept); then, with the Python standard library, the comment-author list, SharePoint/document-management custom XML, the sensitivity-label and custom properties, the thumbnail (a picture of a sample slide) and the author names in the document properties were removed. The master, layouts, theme and media are unchanged.
- **Tokens and checker**: `brand-tokens.json` restates the PDF palette and the template's sizes; `scripts/check_brand.py` and `scripts/new_deck.py` were written from scratch.

## Left out, and why

| Left out | Why |
|---|---|
| Photos in the template's sample slides (archive and customer-site photos) | Rights unknown or not a brand key visual. Stock photos must come from GCM (PDF p.35). (The wide ATM aircraft photo and the pictures inside the full master's layouts now ship, by owner decision: see the merge section below.) |
| Portraits of two named people | Personal data. |
| A research programme's logo and a customer banner | Third-party branding; never redistribute. |
| Font files (Arial, FF DIN, Roboto) | The template embeds none; Arial is a system font and FF DIN is commercial. |
| Tutorial screenshots and "don't" examples from the guidance slides | Not brand assets. |
| The 66 sample slides of the template | Stray fonts and pictures with unknown rights; build from layouts. (The full master with all 44 layouts now ships: see below.) |
| Icons | The template has none; icons come only from the Frequentis Icon Stock (PDF p.16). |

## Open items for Group Communications and Marketing

1. The official **logo pack** (vector and print files) to replace the converted logos.
2. Access to the **Frequentis Icon Stock** and the **Frequentis Photo stock**, and whether any icons or photos may be bundled.
3. The **OneATM style guide** (and the Defence guide), both "being updated" per PDF p.41.
4. Confirmation of **C1** (which grey HEX values to use in Office files), **C2** (the master's off-palette title gradient, a template defect) and **C6** (formal register: active voice and "we", or third person and passive).
5. A copy of the Word templates `Doknorme.dotm` and `Doknormd.dotm` (Word → Shared Templates, PDF p.45) and the "creating documents using templates" training material, whether a stripped copy may be bundled with this skill, whether there is an Excel template, and whether the key visuals may be used in material shared outside Frequentis.
6. **Rights (gating before the kit leaves Frequentis):** permission for the kit to carry the logos, key visuals and slim template, and for the client to version and extend them.
7. **White on light blue** is used in the official template (C10) but fails WCAG contrast at any size; GCM should know.
8. The policy on **"FRQ" in internal documents**, and which classification makes a file "external" (the checker fails "FRQ" only in Frequentis Public or unclassified files).
9. A **link or request process for the Icon Stock and Photo stock** that the skill can point people to.
10. A small-size logo rule for screens (below 5 mm the guidelines ask for a typographic logo in FF DIN Black, which cannot be bundled).

## Merged from the kit owner's own skill frq-4-pptx-agent v1.0, 2026-10-09

The kit owner wrote a second brand skill for Copilot agents, frq-4-pptx-agent v1.0 (84 files, about 12 MB): the full official master, a JSON-spec builder with an audit and a renderer, 44 layout previews, 22 example slides, seven key visuals, traced logo SVGs, brand tokens and a CSS file. By owner decision (2026-10-09/10) it is merged into this skill, **nothing lost**, and never becomes a skill name of its own (design 2026-10-09 §8). The in-app variant and a duplicate folder were not part of it. A source inventory with the SHA-256 of all 84 files is kept in the kit's tests (`scripts/personal/tests/fixtures/frq-brandbook/source-inventory.json`); the tests prove every binary is here byte for byte and every text file is mapped.

### Files

| Owner skill | Here | Note |
|---|---|---|
| `assets/frq-master.pptx` (44 layouts, no slides) | `assets/templates/frq-master.pptx` | Cleaned, see below. Used when a slide needs a layout the slim template lacks. |
| `assets/layouts/*.jpg` (44) | `assets/layouts/` | Unchanged; `references/layouts.md` links each. |
| `assets/examples/*.jpg` (22) | `assets/examples/` | Unchanged. |
| `assets/key-visuals/atm-aircraft.jpg`, `defence.jpg`, `maritime.jpg`, `public-safety.jpg` | the 0.8.0 files `keyvisual-atm-aircraft.jpeg`, `keyvisual-defence-jets.jpeg`, `keyvisual-maritime-vessel.jpeg`, `keyvisual-public-safety-police.jpeg` | Byte-identical: kept once, the owner's path as an alias in `assets/manifest.json`. |
| `assets/key-visuals/corporate-globe.jpg`, `public-transport.jpg` | `assets/keyvisual/keyvisual-corporate-globe.jpg`, `keyvisual-public-transport.jpg` | Full size, next to the 0.8.0 downscaled ones. |
| `assets/key-visuals/atm-aircraft-clouds-wide.jpg` | `assets/keyvisual/keyvisual-atm-aircraft-clouds-wide.jpg` | New; an open item for GCM (below). |
| `assets/logo/frequentis-logo-{blue,white,black}.svg` | `assets/logo/` | Traced wordmark, kept next to the converted 0.8.0 logos, which are preferred (C15). |
| `assets/brand-tokens.json` | `brand-tokens.json` | Merged into the one tokens file: chart series (C17), track grey (C12), content area (C18), full footer (C11), the full master, the 44 layout names, ATM by default (C14). |
| `assets/frequentis-brand.css` | `assets/frequentis-brand.css` | Unchanged; a test checks its colours against the tokens. |
| `scripts/frq_pptx.py` | `scripts/frq_pptx.py` | The builder, under the kit's rules: classification required and checked, never overwrites, render only under `.ai-sdlc/tmp/`, palette from the tokens, slim template by default, assets through `scripts/brand_assets.py`. Its audit rules moved into `scripts/check_brand.py` (`frq_pptx.py audit` runs it; the mapping is in `references/building-decks.md`). |
| `references/layouts.md`, `references/build-spec.md` | `references/` | Paths to the merged tree; kit-only files by exact path; each layout marked slim and full or full only. |
| `references/brand-rules.md`, `SKILL.md` | `references/brand-rules.md`, `SKILL.md` | Merged section by section (table below). New facts are tagged "(owner skill v1.0)". |

### Where each heading went

| Owner heading | Now in |
|---|---|
| Frequentis decks and artifacts (agent version) | `SKILL.md` (title and intro) |
| Bundled resources | `SKILL.md` Files; `references/assets.md` |
| Non-negotiables | `SKILL.md` Never (the stricter rule wins) |
| Workflow: Create | `SKILL.md` Create (steps 1–9) |
| Workflow: Apply (existing deck) | `SKILL.md` Apply an existing file |
| Other artifacts (HTML, diagrams, documents) | `references/documents.md`; `assets/frequentis-brand.css` in `references/assets.md` |
| Known limits | `SKILL.md` Check, step 3 (the check is heuristic; LibreOffice renders differ) |
| Frequentis brand rules (full reference) | `references/brand-rules.md` |
| Story and slide format | `references/brand-rules.md` §1.1, §6 |
| Story first | `references/brand-rules.md` §1.1 |
| Slide format and content area | `references/brand-rules.md` §6 (C18) |
| Master typography | `references/brand-rules.md` §4, §6 |
| Gradient background (divider, agenda, deep dive) | `references/brand-rules.md` §3 |
| Pictures in the template | `references/brand-rules.md` §6 |
| Footer and housekeeping | `references/brand-rules.md` §6 (C11) |
| Colours | `references/brand-rules.md` §2 (C12) |
| Typography, shapes and effects | `references/brand-rules.md` §4, §6 |
| Tables, charts, diagrams, maps and visuals | `references/brand-rules.md` §6.1 (C17) |
| Logo, tagline, key visuals, icons and images | `references/brand-rules.md` §5, §7 |
| Logo | `references/brand-rules.md` §5, §7 |
| Tagline "FOR A SAFER WORLD" | `references/brand-rules.md` §5 |
| Key visuals | `references/brand-rules.md` §5, §9 (C14) |
| Icons | `references/brand-rules.md` §7 |
| Images | `references/brand-rules.md` §7 |
| Writing rules (English decks) | `references/brand-rules.md` §8; `references/writing-style.md` |
| German and other languages | `references/brand-rules.md` §8.1; `SKILL.md` Apply |

### Cleaning the full master

Done with the kit's stdlib maintainer script `scripts/maintainer/strip_pptx_metadata.py` (not placed in repos), the same cleaning as the slim template, so it can be redone when GCM ships a new master: `ppt/commentAuthors.xml` removed (a named employee and an e-mail address), `docProps/custom.xml` removed (MSIP sensitivity-label properties with the tenant id), the four SharePoint `customXml/` parts and `docProps/thumbnail.jpeg` removed, each with its relationship and content type; `dc:creator` and `cp:lastModifiedBy` emptied; `docProps/app.xml` reduced to the application and the presentation format. The slide master, the 44 layouts, the theme and the media are byte-identical to the owner's file (a test compares them).

### Conflicts found in the merge

C11 (footer text), C12 (track grey), C13 (gradients), C14 (ATM by default), C15 (two logo sets), C16 ("FRQ" severity), C17 (chart series order) and C18 (content-area bottom), with the resolutions the kit owner accepted on 2026-10-10: `references/brand-rules.md` §10. C11, C12 and C13 go to GCM for confirmation.

### Open items for GCM from the merge

11. **Pictures inside the full master's layouts** (event and topic pictures, the title mosaic) whose rights are unclear: they stay, by owner decision, until GCM says otherwise.
12. **The wide ATM aircraft photo** (`.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/keyvisual/keyvisual-atm-aircraft-clouds-wide.jpg`): ships by owner decision (2026-10-10); rights for use outside Frequentis to confirm.
13. Confirmation of **C11, C12 and C13**.
14. The official **logo pack**, to replace both logo sets (C15).

### Size

The whole folder is about 14.3 MB, kept once per repo in `.ai-sdlc/kit`; every binary is listed in `.kit-only` and stays there, so the placed skill is about 0.3 MB (design §8.7).

## Validation

Extracted and written with an AI assistant; a person checks the facts in `references/brand-rules.md` against the PDF and the template before release (the kit rule: a human validates everything). The checker is tested against the golden off-brand deck and against decks built from the bundled template (`scripts/personal/tests/test_frq_brandbook.py` in the kit).
