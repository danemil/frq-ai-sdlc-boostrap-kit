---
name: frq-brandbook
description: Apply and check the Frequentis brand on anything the team makes — PowerPoint slides and decks, Word, Excel, PDFs, HTML pages, diagrams and e-mail text. Use whenever someone says "make this on-brand", "branded", "use our template", "the company template", "in our colours", "corporate look", "check this deck against the brand", "brand check", "which blue is ours", "Frequentis colours", "Frequentis logo", "For a safer world", "classification footer", "key visual", "build a deck from this spec", "restyle or fix an existing deck", or asks for a customer-facing slide, report, one-pager or chart. When installed it is the default for every new deck, document, spreadsheet, PDF, explainer or diagram, unless the person asks for a plain file. Create builds decks from an outline or a JSON spec on the slim template, or on the full master with all 44 layouts (maps, events) when a slide needs it; Check audits a .pptx/.docx/.xlsx; Apply fixes an existing deck into a new file, only what the person confirms. ATM by default.
license: MIT for the skill text and scripts. The logos, key visuals, layout previews, examples and templates are brand materials owned by Frequentis AG; see PROVENANCE.md.
metadata:
  status: "draft"
  classification: "internal"
  ai-trust: "working"
  owner: "Architect"
---

# frq-brandbook

Make files look and read like Frequentis, and check files that should. **Brand by default:** when this skill is installed, every new deck, document, spreadsheet, PDF, explainer or diagram uses the brand unless the person asks for a plain file. **A human validates every result**: you propose, the person decides, **one question at a time**. Paths below are relative to this skill's folder (in a personal setup: `.agents/skills/ai-sdlc-frq-brandbook/`). That folder is hidden from git, so search tools skip it: read its files by exact path, never by glob or search. Run its scripts as commands; never import them.

**Big files stay in the kit copy.** Both templates, the layout previews, the example slides, the key visuals and the PNG logos are not in the placed folder: they are in `.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/` (listed in `.kit-only`). Name them by that exact path; the scripts find them by themselves. If one is missing, say "check the kit".

**Source of truth, in this order:** the *Frequentis Brand Guidelines Q4/2025* PDF (Group Communications and Marketing, GCM) → the official Frequentis PowerPoint template → this skill. When they disagree, the higher one wins; the known disagreements and the value to use are in [Known conflicts](#known-conflicts). Full facts with page citations: [references/brand-rules.md](references/brand-rules.md).

## Quick reference

**Colours** (machine-readable in [brand-tokens.json](brand-tokens.json)). Mostly white, then blue, then light blue; greys support; accents rare.

| Name | Office (RGB → HEX) | Web HEX | Use |
|---|---|---|---|
| Blue | 0-65-130 → #004182 | #004182 | Lead colour: headlines, key shapes, side bars, logo |
| Light blue | 0-170-225 → #00AAE1 | #00AAE1 | Secondary colour. White text on it fails contrast at any size: use #333333 text on it, or #004182 for large text (WCAG, kit rule) |
| Black | 51-51-51 → #333333 | #333333 | Body text (never pure black #000000) |
| Cool grey | 98-100-105 → #626469 | #666666 | Text, lines, tagline |
| Mid grey | 159-160-163 → #9FA0A3 | #999999 | Text, lines, backgrounds; as text on white it fails contrast, so shapes and lines (WCAG, kit rule) |
| Warm grey | 201-195-186 → #C9C3BA | #C9C3BA | Text, lines, backgrounds; not as text on white (WCAG, kit rule) |
| White | #FFFFFF | #FFFFFF | Base colour: bright white, never cream |
| Green / Orange / Red | #73B432 / #F0A51E / #A52846 | same | Accents: highlights and traffic lights, sparingly |

Business-unit colours (ATM #2364A0, Maritime #19555F, Defence #641E6E, Public Safety #D22832, Public Transport #DC6423, light yellow #FDD217) are **for chart legends only**. **One gradient only:** #004182 → #00AAE1, corner to corner, for dividers and agenda backgrounds.

**Fonts.** Office files: **Arial** (Regular; bold very selectively; **never italics**). Web: **Roboto**, then Arial. Print: FF DIN (licensed; leave print to a designer). Never bundle or embed font files. Hierarchy comes from size, not bold. Left-align text.

Charts: the key series blue, a second highlight light blue, the rest grey (order in `brand-tokens.json`); the light grey #EDF1F2 only as a KPI donut track (C12). No gridlines, no 3D.

**Logo.** Use only the logo files: the SVGs in `assets/logo/` (prefer `logo-frequentis-*`, converted shape for shape; C15), the PNGs in `.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/logo/`. In decks the template already places it. Never redraw, retype, recolour or distort it. Blue on white is preferred; white on blue #004182 is fine; black or white on calm photos only. Clear space = the logo's height; minimum height 5 mm. The tagline "FOR A SAFER WORLD" appears only as part of the logo-with-tagline file, on title and closing pages.

**Writing.** British English. Sentence case for headlines and text. "Frequentis" (sentence case, also in slide headlines); "Frequentis AG" for the legal entity; **never "FRQ" in anything external**. Numbers: one to twelve in words, 2,115, 15.50, 10m, 15bn, +10%. Dates: 25 March 2026. Active voice, "we", short sentences. More: [references/writing-style.md](references/writing-style.md).

**Classification and footer.** Every document except printed public material carries a class (PDF p.26), including public ones: **Frequentis Public**, **Frequentis General** (Inner Circle) or **Frequentis Confidential**, plus `© Frequentis AG <current year>`. Decks, set once in the slide master: `<title> | <presenter> | Frequentis <class> | © Frequentis AG <year>` (C11). Documents: `Frequentis <class> | © Frequentis AG <year>`.

**Business unit: ATM by default** (C14): the ATM key visual and wording unless the person names another business unit; corporate or cross-BU content uses the globe.

## Choose the mode

- **Create**: a new on-brand file. Go to [Create](#create).
- **Check**: audit a file, change nothing. Go to [Check](#check).
- **Apply**: restyle or fix an existing deck (or document) into a new file. Go to [Apply](#apply-an-existing-file).
- Unclear? Ask once: "Create a new file, or check this one against the brand?"

## Create

Ask one question at a time and wait for each answer.

1. **Ask the classification** (Public, General or Confidential) and wait for the answer. Never guess it, never pick a "safe" one. If you cannot ask (a one-shot run), stop, or use the literal `Frequentis [classification to be set]` wherever the class goes and list it in the hand-over. The scripts run only with one of the three classes or that placeholder.
2. **Infer the style.** *Executive* (presented live: board, steering, keynote): one message per slide, "reduce to max", detail in the notes. *Self-explanatory* (pre-read, handout, annex): sub-headlines, more text. No clear signal: ask once.
3. **Footer details and business unit.** The presentation title and the presenter, inferred from the request if possible. ATM unless the person names another unit; for an internal team deck keep `Standard TITLE` as it is. Key visuals: [references/assets.md](references/assets.md).
4. **Story first.** Build the message pyramid: one main message (it becomes the title), about three supporting messages (sections or key slides), proof points under each. Every headline states its slide's key message, not a label.
5. **Outline first, then stop.** Show one line per slide or section (headline = the key message) and wait. Build nothing until the person agrees; if you cannot ask, stop after the outline.
6. **Build from the bundled templates**, never from scratch, with the venv Python (python-pptx, installed only with consent as `ai-sdlc-doc-powerpoint` describes):
   - A text deck from the outline: `python3 scripts/new_deck.py outline.md out.pptx --classification "<the class the person gave>"`.
   - Any other deck: write a spec ([references/build-spec.md](references/build-spec.md); layouts in [references/layouts.md](references/layouts.md)), then `python3 scripts/frq_pptx.py build spec.json out.pptx --classification "<the class the person gave>"`. Default skeleton: *Standard TITLE* → *2_Agenda* → per section *Divider blue world* and content slides → *Closing Slide*.
   - **Template:** the slim one (25 layouts, about 1.2 MB a deck) by default; the full master (all 44 layouts, about 9 MB a deck) only when a slide needs a layout the slim one lacks (maps, event layouts). The builder decides and says so. More: [references/building-decks.md](references/building-decks.md).
   - Word: customer-facing documents start from the official Word template `Doknorme.dotm` (English) or `Doknormd.dotm` (German), from Word → Shared Templates (PDF p.45): ask the person for it. Excel, PDF, HTML, diagrams, issues, mail: [references/documents.md](references/documents.md).
7. **Custom visuals** (processes, timelines, org charts, maps): open the matching example in `.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/examples/` first, then add flat shapes inside the content area (recipes in build-spec.md).
8. **Check your own output** with `scripts/check_brand.py` (below), then **look at it** (render it, see step 3 of Check). Fix every FAIL and every font WARN in what you wrote; list any other WARN for the person. Report the result as evidence found or not found; never call the file "on-brand" or "compliant".
9. **Hand over** with the path, the headline list, the check result and what is left for a human (photos from the Frequentis Photo stock, icons from the Icon Stock, a classification still to be set).

## Check

1. Run the checker. It needs only Python 3.9+, no install, and changes nothing:
   `python3 <this skill's folder>/scripts/check_brand.py <file.pptx|.docx|.xlsx>` (add `--json` for machine-readable output).
2. **Show the findings as a table** (it prints one: #, severity, where, rule, finding, proposed fix, source page; keep the # so the person can pick by number). Change nothing yet.
   - **FAIL**: breaks a rule (off-palette colour, non-Arial font, italics, shadow or 3D also when inherited from theme styles, wrong gradient, the tagline typed on its own, a "Thank you" or "Questions?" slide, no classification; "FRQ" when the file is Frequentis Public or has no class; a layout not from the master, no *Closing Slide* at the end, "Presentation title" still in the footer, template leftovers).
   - **WARN**: probably off-brand, a person judges (tints of brand colours, Title Case, US spelling, contractions, dates and numbers, bold, centred text, outlines, overloaded slide, "FREQUENTIS" in capitals, footer year, "FRQ" in an internal file, theme not from the template, a label instead of a message as headline, rounded boxes, chart gridlines, more than 90 words, no title slide first). The rule list: [references/building-decks.md](references/building-decks.md), "Check rules".
   - **INFO**: for the record. Master, layout and theme findings come from the template, not the author: report them, do not "fix" the official template.
3. **Look at the file.** The checker sees colours, fonts and text in the XML, not layout, logo use or everything PowerPoint draws. If LibreOffice is available, render into `.ai-sdlc/tmp/` (hidden from git), always with these two commands: `soffice --headless --convert-to pdf --outdir .ai-sdlc/tmp <file>`, then `pdftoppm -png -r 80 .ai-sdlc/tmp/<name>.pdf .ai-sdlc/tmp/<name>`, and view the pages; otherwise ask the person to look in PowerPoint or Word. LibreOffice shows deck titles black and a shadow under the footer logo; both are right in PowerPoint. Check logo use and clear space, image sources, chart highlight logic, density and tone against [references/brand-rules.md](references/brand-rules.md).
4. To fix anything, go on with [Apply](#apply-an-existing-file).

## Apply an existing file

1. **Check it** (above) and look at it: the story and the headlines too, not only the XML.
2. **One table**: *Slide*, *Issue*, *Rule*, *Proposed fix*; **Must** fixes (the FAILs) first, then **Should** fixes (the WARNs). Keep the checker's # so the person can pick.
3. **Ask**: "Apply all fixes, only the Must fixes, or pick by slide number?" Apply **only** what the person confirmed.
4. **Fix into a new file**, `<name>-frq.pptx` (or ask); never change the original. A deck on the Frequentis master is fixed in a copy; a deck that is not is rebuilt from a spec on the slim template (the full master if it needs a full-only layout), carrying over its text and data ([references/build-spec.md](references/build-spec.md), Apply mode). Word and Excel: through the doc skill for that format.
5. **Footer**: `python3 scripts/frq_pptx.py footer in.pptx out.pptx --classification "<the class the person gave>" --title … --presenter …`.
6. **Check again** and report "evidence found" or "evidence not found" per fix, never "compliant", plus what is left for a person.

**German decks**: do not rewrite the wording; fix only the visuals, the template, the brand name, "Mio" and the footer. Other languages: visuals and template only.

## Per deliverable

The brand rules sit on top of the kit's file skills; use them for the mechanics (if you have them):

| Deliverable | Use | Brand specifics |
|---|---|---|
| PowerPoint | `ai-sdlc-doc-powerpoint` | Start from the slim template; layouts by name; never set fonts or colours on placeholders. [building-decks.md](references/building-decks.md) |
| Word | `ai-sdlc-doc-word` | Customer documents: start from `Doknorme.dotm` (ask for it). Otherwise Arial (remove python-docx's theme fonts), headings #004182, body #333333, classification in the footer. [documents.md](references/documents.md) |
| Excel | `ai-sdlc-doc-excel` | Arial in every cell (`arial_everywhere()` in [documents.md](references/documents.md), last before saving); header row #004182 with white text; series in palette order; accents as pass/fail fills. |
| PDF | `ai-sdlc-doc-pdf` | Build the Word or PowerPoint file on-brand, check it, then export (`soffice --convert-to pdf`; LibreOffice may substitute Arial). |
| HTML / web | `ai-sdlc-visual-explainers` | Roboto, web HEX values, CSS variables from [documents.md](references/documents.md). |
| Diagrams | `ai-sdlc-drawio`, `ai-sdlc-likec4-dsl` | Copy-ready draw.io styles and a LikeC4 `specification` block in [documents.md](references/documents.md). |
| Mermaid in issues | `ai-sdlc-visual-issue` | Internal: no branding needed; an optional `%%{init}%%` line in [documents.md](references/documents.md). |
| E-mail, Teams | — | Writing rules; external mail carries the standard signature (Tahoma or Arial, PDF p.47); no logo pasted into the body. |

## Known conflicts

The PDF wins unless noted. Items marked **(GCM to confirm)** are this kit's choice until Group Communications and Marketing answers. Evidence for each: [references/brand-rules.md](references/brand-rules.md) §10.

| # | Conflict | Use |
|---|---|---|
| C1 | Greys: PDF HEX #666666/#999999, but its "MS Office" RGB gives #626469/#9FA0A3 (the template's theme) | **#626469/#9FA0A3 in Office files, #666666/#999999 on the web.** The checker accepts both. (GCM to confirm) |
| C2, C3 | The master's headline gradient #00529B→#0588FF and the "Divider blue world" stops are off-palette | Leave the template alone; never copy those stops or set a title colour. Template defect. (GCM to confirm) |
| C4, C11 | Template footer: "Presentation title", "<by Presenter>", "© Frequentis AG 2024" | Set title, presenter, class and current year in the master: `<title> \| <presenter> \| Frequentis <class> \| © Frequentis AG <year>` (the scripts do). (GCM to confirm) |
| C5 | PDF names generic layout families; the template has real names | Use the template's names ([references/layouts.md](references/layouts.md)). |
| C6 | PDF p.24 "formal: third person, passive" vs p.23 "active voice, we" | **Active voice and "we"**; take only the p.24 avoid-list. (GCM to confirm) |
| C7 | Tagline grey on white is #666666; the template shows it white on the globe | Blue logo file uses #666666; on blue or photos use the white file. |
| C8, C14 | One large BU image vs the globe with five BU tiles | **ATM by default** (owner decision): the ATM key visual and wording unless the person names another unit. |
| C9 | Stray fonts in the template's samples and map layouts | Build from layouts only, never copy a sample slide. Inherited fonts are INFO. |
| C10 | White on light blue (2.7:1) is used in the template | Fails contrast at any size: use #333333 text on light blue, or blue #004182 for large text; flag the template's use. (WCAG, kit rule) |
| C12 | Track grey #EDF1F2 in the template's KPI charts | Chart tracks only; the checker warns elsewhere. (GCM to confirm) |
| C13 | The template's own gradient stops | INFO when inherited, never a FAIL; new shapes use only #004182 → #00AAE1. (GCM to confirm) |
| C15 | Two logo sets: converted and traced | Keep both; prefer the converted `logo-frequentis-*` files. |
| C16 | "FRQ" on slides | Customer-facing: FAIL; internal: WARN. |
| C17, C18 | Chart series order; content-area bottom 5.07 vs 5.08 in | The order in `brand-tokens.json`; 5.07 in for hand-placed shapes. |

## Never

- Change the person's file in place, or decide the classification for them.
- Redraw, retype, recolour or stretch the logo, or put anything on it; type "FREQUENTIS" or the tagline as text.
- Use colours outside the palette, tints of brand colours (grey tints are fine), or any gradient but #004182 → #00AAE1.
- Italics, shadows, glow, reflections, 3D shapes or 3D charts; outlines on filled shapes; rounded boxes where a square works.
- End with a "Thank you" or "Questions?" slide: use the template's "Closing Slide" (a *Q&A* slide may come before it at live events).
- Use stock or web photos, AI-generated images or Office icons in place of Frequentis material: photos come from the Frequentis Photo stock, cleared by Group Communications and Marketing; icons only from the Frequentis Icon Stock. Leave a placeholder and a note instead.
- Copy a slide from an old deck or the template's samples (it carries stray fonts); build from layouts.
- Leave template guidance in a deck (annotations, "Example" stickers, lorem ipsum, "Presentation title").

## Files

| Path | What |
|---|---|
| [references/brand-rules.md](references/brand-rules.md) | All brand facts with PDF page and template citations; conflicts C1–C18 |
| [references/building-decks.md](references/building-decks.md) | Which template, which front end, the slim template's 25 layouts, recipes, traps, the check rules |
| [references/layouts.md](references/layouts.md) | All 44 master layouts: purpose, placeholders, slim and full or full only, preview path |
| [references/build-spec.md](references/build-spec.md) | The JSON spec for `frq_pptx.py build`, python-pptx recipes, Apply mode |
| [references/documents.md](references/documents.md) | Word, Excel, PDF, HTML/CSS and diagram mapping |
| [references/writing-style.md](references/writing-style.md) | British English, sentence case, numbers, dates, names, register |
| [references/assets.md](references/assets.md) | Every logo, key visual, background, template, preview and example, and when to use it |
| `brand-tokens.json` | Palette, fonts, sizes, footer, layouts, business units (read by the scripts) |
| `scripts/check_brand.py` | The one brand check: stdlib only, .pptx/.docx/.xlsx; exit 1 on FAIL |
| `scripts/frq_pptx.py` | The builder: `layouts`, `build`, `footer`, `audit` (runs the check), `render` (python-pptx) |
| `scripts/new_deck.py` | A new deck from a Markdown outline, through `frq_pptx.py` (python-pptx) |
| `scripts/brand_assets.py` | Finds the skill's files in the placed folder, then in `.ai-sdlc/kit` |
| `assets/` | The SVG logos, the gradient SVG, `frequentis-brand.css`, `manifest.json` (every asset, its size and placement); the binaries are in `.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/` |
