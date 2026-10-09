---
name: frq-brandbook
description: Apply and check the Frequentis brand on anything that leaves the team — PowerPoint slides and decks, Word documents, Excel spreadsheets, PDFs, HTML pages and diagrams. Use whenever someone says "make this on-brand", "use the Frequentis template", "check this deck against the brand", "brand check", "which blue is ours", "Frequentis colours", "Frequentis logo", "For a safer world", "classification footer", "key visual", or asks for a customer-facing, Frequentis-branded slide, report, one-pager or chart. Create mode builds a new file from the bundled slim template, logo and key visuals; Check mode audits a .pptx/.docx/.xlsx with a stdlib-only script and proposes fixes, changing only what the person confirms. Covers palette (HEX and Office RGB), Arial and Roboto, logo and tagline rules, the one gradient, British English writing rules and the known template conflicts.
license: MIT for the skill text and scripts. The logos, key visuals and template are brand materials owned by Frequentis AG; see PROVENANCE.md.
metadata:
  status: "draft"
  classification: "internal"
  ai-trust: "working"
  owner: "Architect"
---

# frq-brandbook

Make files look and read like Frequentis, and check files that should. **A human validates every result**: you propose, the person decides. Paths below are relative to this skill's folder (in a personal setup: `.agents/skills/ai-sdlc-frq-brandbook/`).

**Source of truth, in this order:** the *Frequentis Brand Guidelines Q4/2025* PDF (Group Communications and Marketing, GCM) → the official Frequentis PowerPoint template → this skill. When they disagree, the higher one wins; the known disagreements and the value to use are in [Known conflicts](#known-conflicts). Full facts with page citations: [references/brand-rules.md](references/brand-rules.md).

## Quick reference

**Colours** (machine-readable in [brand-tokens.json](brand-tokens.json)). Mostly white, then blue, then light blue; greys support; accents rare.

| Name | Office (RGB → HEX) | Web HEX | Use |
|---|---|---|---|
| Blue | 0-65-130 → #004182 | #004182 | Lead colour: headlines, key shapes, side bars, logo |
| Light blue | 0-170-225 → #00AAE1 | #00AAE1 | Secondary colour. White text on it fails contrast: large text only |
| Black | 51-51-51 → #333333 | #333333 | Body text (never pure black #000000) |
| Cool grey | 98-100-105 → #626469 | #666666 | Text, lines, tagline |
| Mid grey | 159-160-163 → #9FA0A3 | #999999 | Shapes, lines, recessed data; never body text |
| Warm grey | 201-195-186 → #C9C3BA | #C9C3BA | Shapes, backgrounds; never text |
| White | #FFFFFF | #FFFFFF | Base colour: bright white, never cream |
| Green / Orange / Red | #73B432 / #F0A51E / #A52846 | same | Accents: highlights and traffic lights, sparingly |

Business-unit colours (ATM #2364A0, Maritime #19555F, Defence #641E6E, Public Safety #D22832, Public Transport #DC6423, light yellow #FDD217) are **for chart legends only**. **One gradient only:** #004182 → #00AAE1, corner to corner, for dividers and agenda backgrounds.

**Fonts.** Office files: **Arial** (Regular; bold very selectively; **never italics**). Web: **Roboto**, then Arial. Print: FF DIN (licensed; leave print to a designer). Never bundle or embed font files. Hierarchy comes from size, not bold. Left-align text.

**Logo.** Use only the files in `assets/logo/`, never redraw, retype, recolour or distort them. Blue on white is preferred; white on blue #004182 is fine; black or white on calm photos only. Clear space = the logo's height; minimum height 5 mm. The tagline "FOR A SAFER WORLD" appears only as part of the logo-with-tagline file, on title and closing pages.

**Writing.** British English. Sentence case for headlines and text. "Frequentis" (sentence case, also in slide headlines); "Frequentis AG" for the legal entity; **never "FRQ" in anything external**. Numbers: one to twelve in words, 2,115, 15.50, 10m, 15bn, +10%. Dates: 25 March 2026. Active voice, "we", short sentences. More: [references/writing-style.md](references/writing-style.md).

**Classification and footer.** Every non-public file carries one class: **Frequentis Public**, **Frequentis General** (Inner Circle) or **Frequentis Confidential**, plus `© Frequentis AG <current year>`. Footer format: `Frequentis <class> | © Frequentis AG <year>`. In decks it is set once, in the slide master.

## Choose the mode

- **Create**: a new on-brand file. Go to [Create](#create).
- **Check**: audit an existing file and fix what the person approves. Go to [Check](#check).
- Unclear? Ask once: "Create a new file, or check this one against the brand?"

## Create

1. **Ask the classification** (Public, General or Confidential). Never guess it.
2. **Infer the style.** Executive (board, steering, keynote): one headline per slide, "reduce to max". Self-explanatory (pre-read, handout, annex): more text and sub-headlines. No clear signal: ask once.
3. **Business unit.** Default ATM; corporate or cross-BU content uses the globe. The key visual for each is in `assets/keyvisual/` ([references/assets.md](references/assets.md)).
4. **Outline first.** Show one line per slide or section (headline = the key message) and build only after the person agrees.
5. **Build from the bundled template**, never from scratch:
   - Deck: `assets/templates/frq-template-slim-core.pptx` (25 layouts, no sample slides). Quickest: `scripts/new_deck.py outline.md out.pptx --classification "Frequentis General"` (python-pptx; see [references/building-decks.md](references/building-decks.md) for the outline format, layouts by name and placeholder indexes).
   - Word, Excel, PDF, HTML, diagrams: the colour and font mapping in [references/documents.md](references/documents.md).
6. **Check your own output** with `scripts/check_brand.py` (below). Fix every FAIL in what you wrote, then hand over with the path, a one-line summary per slide or section, and what is left for a human (photos from the Frequentis Photo stock, icons from the Icon Stock, the classification).

## Check

1. Run the checker. It needs only Python 3.9+, no install, and changes nothing:
   `python3 <this skill's folder>/scripts/check_brand.py <file.pptx|.docx|.xlsx>` (add `--json` for machine-readable output).
2. **Show the findings as a table** (it prints one: severity, where, rule, finding, proposed fix, source page). Change nothing yet.
   - **FAIL**: breaks a rule (off-palette colour, non-Arial font, italics, shadow or 3D, wrong gradient, "FRQ", a retyped logo or tagline, a "Thank you" slide, no classification).
   - **WARN**: probably off-brand, a person judges (Title Case, US spelling, bold, centred text, outlines, overloaded slide, footer year, theme not from the template).
   - **INFO**: for the record. Master, layout and theme findings come from the template, not the author: report them, do not "fix" the official template.
3. Add what the script cannot see, from a look at the slides: logo use and clear space, image sources, chart highlight logic, density, tone. Use [references/brand-rules.md](references/brand-rules.md).
4. **Ask**: "Fix all, only the FAILs, or pick by number?" Apply **only** what the person confirmed, through the doc skill for that format, and never overwrite the original: write `<name>-on-brand.pptx` (or ask).
5. Re-run the checker on the new file and report "evidence found" or "evidence not found" per fix, never "compliant".

## Per deliverable

The brand rules sit on top of the kit's file skills; use them for the mechanics (if you have them):

| Deliverable | Use | Brand specifics |
|---|---|---|
| PowerPoint | `ai-sdlc-doc-powerpoint` | Start from the slim template; layouts by name; never set fonts or colours on placeholders. [building-decks.md](references/building-decks.md) |
| Word | `ai-sdlc-doc-word` | Arial, headings #004182, body #333333, classification in the footer. [documents.md](references/documents.md) |
| Excel | `ai-sdlc-doc-excel` | Arial; header row #004182 with white text; series in palette order. |
| PDF | `ai-sdlc-doc-pdf` | Build the Word or PowerPoint file on-brand, then export; check the source file. |
| HTML / web | `ai-sdlc-visual-explainers` | Roboto, web HEX values, CSS variables from [documents.md](references/documents.md). |
| Diagrams | `ai-sdlc-drawio`, `ai-sdlc-likec4-dsl` | Flat boxes, no shadows, blue for the key node, greys for the rest, Arial. |

## Known conflicts

The PDF wins unless noted. Items marked **(GCM to confirm)** are this kit's choice until Group Communications and Marketing answers.

| # | Conflict | Use |
|---|---|---|
| C1 | Greys: PDF HEX #666666/#999999, but its "MS Office" RGB gives #626469/#9FA0A3 (the template's theme) | **#626469/#9FA0A3 in Office files, #666666/#999999 on the web.** The checker accepts both. (GCM to confirm) |
| C2 | Template master fills headline text with an off-palette gradient #00529B→#0588FF | Leave the master alone; never set a title colour in generated slides. Report it as a template defect. (GCM to confirm) |
| C3 | Layout "Divider blue world" uses other gradient stops | Using the layout is fine; never copy those stops into new shapes. |
| C4 | Template footer says "© Frequentis AG 2024" and "<by Presenter>" | Set the current year, class and title in the master (`new_deck.py` does). |
| C5 | PDF names generic layout families; the template has real names | Use the template's names ([building-decks.md](references/building-decks.md) maps them). |
| C6 | PDF p.24 "formal: third person, passive" vs p.23 "active voice, we" | **Active voice and "we"**; take only the p.24 avoid-list (no contractions, clichés, abbreviated words). (GCM to confirm) |
| C7 | Tagline grey on white is #666666 in the PDF; the template shows it white on the globe | Blue logo file uses #666666; on blue or photos use the white file. |
| C8 | PDF: BU title slide with one large BU image; template: globe plus five BU tiles | ATM decks keep the template title layout (ATM tile included) unless the person wants the ATM image as hero. A human picks. |
| C9 | Stray fonts (Nirmala UI, Calibri, Nokia Pure, Arial Narrow) in the template's samples and navigation | Build from layouts only, never copy a sample slide. The checker reports inherited fonts as INFO. |
| C10 | White on light blue (2.7:1) is used in the template | Large text (18 pt or more) only; the checker cannot see it, so look. |

## Never

- Redraw, retype, recolour or stretch the logo, or put anything on it; type "FREQUENTIS" or the tagline as text.
- Use colours outside the palette, tints of brand colours (grey tints are fine), or any gradient but #004182 → #00AAE1.
- Italics, shadows, glow, reflections, 3D shapes or 3D charts; outlines on filled shapes.
- End with a "Thank you" or "Questions?" slide: use the template's "Closing Slide".
- Use stock or web photos, AI-generated images or Office icons in place of Frequentis material: photos come from the Frequentis Photo stock, cleared by Group Communications and Marketing; icons only from the Frequentis Icon Stock. Leave a placeholder and a note instead.
- Copy a slide from an old deck or the full template (it carries stray fonts); build from layouts.
- Change the person's file in place, or decide the classification for them.

## Files

| Path | What |
|---|---|
| [references/brand-rules.md](references/brand-rules.md) | All brand facts with PDF page and template citations |
| [references/building-decks.md](references/building-decks.md) | The template's 25 layouts, placeholder indexes, python-pptx recipe, traps |
| [references/documents.md](references/documents.md) | Word, Excel, PDF, HTML/CSS and diagram mapping |
| [references/writing-style.md](references/writing-style.md) | British English, sentence case, numbers, dates, names, register |
| [references/assets.md](references/assets.md) | Every bundled logo, key visual and background, and when to use it |
| `brand-tokens.json` | Palette, fonts, sizes, footer, business units (read by the scripts) |
| `scripts/check_brand.py` | Stdlib-only checker for .pptx/.docx/.xlsx; exit 1 on FAIL |
| `scripts/new_deck.py` | New deck from an outline and the template (python-pptx) |
| `assets/` | Logos (SVG, PNG), key visuals, backgrounds, the slim template; listed in `assets/manifest.json` |
