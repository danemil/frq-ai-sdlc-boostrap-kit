# Provenance: frq-brandbook

Written for this kit (2026-10-09) from brand materials the client owns and provided for this purpose. The skill text, `brand-tokens.json` and the scripts are MIT, like the rest of the kit. The logos, key visuals, backgrounds and template in `assets/` are **brand materials owned by Frequentis AG**: they are included so the team's own deliverables can be on-brand, and they are not licensed for any other use. Before the kit is shared outside Frequentis, Group Communications and Marketing (GCM) confirms that use.

## Sources

| Source | What it gave |
|---|---|
| *Frequentis Brand Guidelines Q4/2025* (51-page PDF, GCM) | The rules: palette (HEX, RGB, CMYK), fonts, logo, tagline, gradient, imagery, icons, writing rules, classification. The source of truth; cited as "PDF p.N" (PDF page index; from p.17 on the printed page number is N+1). |
| The official Frequentis PowerPoint template (*Corporate PowerPoint Essentials*, "FRQ-Template presentation.pptx": 1 master, 44 layouts, 66 sample slides) | The slide master, the "FRQ_CORP 2024" theme, layout names, placeholder indexes, sizes; the logo shapes and key visuals in `assets/`. Cited as "template". |
| The earlier internal Frequentis brand skill for Copilot in PowerPoint, v1.0 (2026-10-01), and its off-brand test deck | Create and Check (then "Apply") modes, the audit-then-confirm flow, Must-fix and Should-fix lists, the decisions on tints and register (C6), the six-slide off-brand deck now used as the checker's golden test (kept in the kit's tests, not in this folder). |
| Structure from another company's brand skill | **Structure and approach only**: a one-screen quick reference first, one workflow per deliverable, a source-of-truth table, depth in `references/`, a machine-readable palette, a stdlib zip/XML deck audit that separates slide-level from master-level findings, building decks from a stripped template by layout name. None of its names, colours, fonts, text or images were used. |

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
| Photos in the template (event layout pictures, archive and customer-site photos, a wide ATM aircraft photo) | Rights unknown or not a brand key visual. Stock photos must come from GCM (PDF p.35). |
| Portraits of two named people | Personal data. |
| A research programme's logo and a customer banner | Third-party branding; never redistribute. |
| Font files (Arial, FF DIN, Roboto) | The template embeds none; Arial is a system font and FF DIN is commercial. |
| Tutorial screenshots and "don't" examples from the guidance slides | Not brand assets. |
| The map and event layouts, the full 12 MB template | Size (the map layouts are 0.8–3.3 MB of XML each). Ask for the full template when a map is needed. |
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

## Validation

Extracted and written with an AI assistant; a person checks the facts in `references/brand-rules.md` against the PDF and the template before release (the kit rule: a human validates everything). The checker is tested against the golden off-brand deck and against decks built from the bundled template (`scripts/personal/tests/test_frq_brandbook.py` in the kit).
