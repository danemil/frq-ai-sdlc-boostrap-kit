# Frequentis brand rules: the full facts

Extracted 2026-10-09. Every fact cites its source; check a fact against the source before you rely on it for something that ships (a human validates everything). The quick reference in `../SKILL.md` summarises this file; `../brand-tokens.json` holds the same values for scripts.

**Sources and citation keys**

| Key | Source |
|---|---|
| `PDF p.N` | *Frequentis Brand Guidelines Q4/2025*, 51 pages. N is the PDF page index. **From p.17 on, the printed footer number is N+1**, because one hidden slide was skipped. |
| `TPL s.N` / `TPL L"name"` | The official Frequentis PowerPoint template ("FRQ-Template presentation.pptx"): slide N, or the slide layout with that name. The file is the *Corporate PowerPoint Essentials* deck (docProps `Template`): one master, 44 layouts, 66 sample slides (10 hidden). TPL s.1 says it is "a collection of slide layout examples and tips", not the master itself. |
| `TPL theme` / `TPL master` | `ppt/theme/theme1.xml` ("FRQ_CORP 2024", colour scheme "FRQ-new") / `ppt/slideMasters/slideMaster1.xml` |
| `SKILL §N` | The earlier internal Frequentis brand skill for Copilot in PowerPoint, v1.0 (2026-10-01) |

Conflicts are marked **⚠ CONFLICT**. They are all collected in §10.

---

## 1. Brand principles

- Show Frequentis as one company. Keep it clean, clear and simple: "less is more – always". Give the logo space and use it powerfully. Use accent colours sparingly. Tell a story rather than just showing facts. (PDF p.3)
- The headline carries the key message of each slide. The content area visualises that message. (TPL s.4, s.6; PDF p.29)
- Executive decks use one headline per slide and "reduce to max". Self-explanatory decks may carry more text and sub-headlines. (PDF p.29)

## 2. Colour palette

### 2.1 Primary colours (PDF p.7; theme slots from TPL theme)

| Name | HEX (PDF "online") | RGB (PDF "MS Office") | CMYK | Spot | Theme slot | Use (PDF p.7) |
|---|---|---|---|---|---|---|
| Blue | **#004182** | 0-65-130 | 100-60-0-6 | Pantone 286 | `dk1` (tx1) | Company lead colour; also the logo colour (p.5) |
| Light blue | **#00AAE1** | 0-170-225 | 65-5-0-0 | – | `accent3` | Secondary colour |
| Black | **#333333** | 51-51-51 | 95% black | – | `lt2` (bg2): body-text colour in the master | Text, lines, backgrounds |
| Cool grey | #666666 ⚠ | 98-100-105 (= **#626469**) | 70% black | CG11 | `dk2` = #626469 | Text, lines, backgrounds; tagline colour (p.5) |
| Mid grey | #999999 ⚠ | 159-160-163 (= **#9FA0A3**) | 40% black | CG7 | `accent1` = #9FA0A3 | Text, lines, backgrounds |
| Warm grey | **#C9C3BA** | 201-195-186 | 21-19-24-0 | WG3 | `accent2` | Text, lines, backgrounds |
| White | #FFFFFF | 255-255-255 | – | – | `lt1` | Base colour: "bright white, never cream or off-white" |

### 2.2 Accent colours (PDF p.7)

| Name | HEX | RGB | CMYK | Theme slot | Use |
|---|---|---|---|---|---|
| Green | #73B432 | 115-180-50 | 50-0-100-0 | `accent5` | Highlights, spots, "traffic light". Sparingly. |
| Orange | #F0A51E | 240-165-30 | 0-30-100-0 | `accent4` | Same |
| Red | #A52846 | 165-40-70 | 20-90-50-0 | `accent6` | Same |

### 2.3 Additional accent colours: legends only (PDF p.7)

| Label | HEX | RGB |
|---|---|---|
| MAR (Maritime) | #19555F | 25-85-95 |
| **ATM** (default BU) | #2364A0 | 35-100-160 |
| DEF (Defence) | #641E6E | 100-30-110 |
| PS (Public Safety) | #D22832 | 210-40-50 |
| PT (Public Transport) | #DC6423 | 220-100-35 |
| AirNav dark yellow | #F0A51E | 240-165-30 |
| AirNav light yellow | #FDD217 | 253-210-23 |

The theme also sets `hlink` #0038A8 and `folHlink` #626469 (TPL theme). The PDF does not list #0038A8.

### 2.4 Usage rules

- Colour balance: mostly white, then blue, then light blue. Greys support. Accents are rare (PDF p.7 colour-balance bar; SKILL §4).
- Accents go on graphics and legends. Additional accents go on legends only. (PDF p.7)
- "Do not use gradients of our brand colours except for greys" (PDF p.7, the note on the Office colour picker). SKILL §4 reads this as: no tints or shades of brand colours, but grey tints are fine.
- When "Frequentis" is highlighted in a headline by colour, use only blue or grey (PDF p.25).
- In charts, highlight the key item with one accent and recess secondary data in greys (PDF p.18; TPL s.60–62).
- Install the corporate colours as a theme colour set named "FRQ" and use only that scheme (TPL s.14).

### 2.5 Contrast (WCAG 2.x, computed)

| Foreground on background | Ratio | Verdict |
|---|---|---|
| Blue #004182 on white | 10.1 | AAA |
| Black #333333 on white | 12.6 | AAA |
| Cool grey #666666 / #626469 on white | 5.7 / 5.9 | AA |
| White on blue #004182 | 10.1 | AAA (divider, side bar and title text) |
| White on light blue #00AAE1 | 2.7 | **Fails AA.** The template does this (TPL s.7 "Keep in mind" box), so allow it only for large text of 18 pt or more and still flag it. |
| Mid grey #999999 / #9FA0A3 on white | 2.9 / 2.6 | Fails. Use it for shapes and lines, never for body text. |
| Green, orange, warm grey on white | 2.5 / 2.1 / 1.8 | Fails. Use for fills and legends only, never as text colour. |
| Red #A52846 on white | 7.0 | AAA (usable for text) |
| Light blue on blue | 3.8 | Large text only |

## 3. Gradient

- **One Frequentis gradient only:** dark blue #004182 to light blue #00AAE1, corner to corner. Never create a gradation from any grey or any other colour. No "muddy" combinations. (PDF p.17)
- Use it as a distinct background (agenda, divider, deep-dive) and selectively as a design element. Never build a whole presentation on it. (PDF p.17; TPL s.9)
- Template implementation: the backgrounds of TPL L"1_Agenda", L"Divider", L"2_Agenda" and L"Guidelines" run from `tx1`→`accent3` at an angle of 315° (bottom-left to top-right). Reproduced in `../assets/background/bg-gradient-frequentis.svg`.
- ⚠ CONFLICT: TPL L"Divider blue world" uses other gradient stops (#2F88C2, #2C82BD, #105A98, then tx1), and the **master title style fills headline text with a gradient #00529B→#0588FF** (TPL master `titleStyle/lvl1pPr`). Neither stop set is in the PDF palette. See §10.

## 4. Typography

| Context | Font | Source |
|---|---|---|
| MS Office (PowerPoint, Word, Excel) | **Arial** Regular. Bold "very selectively". **No italics.** | PDF p.8; TPL s.7 ("Do not use any other fonts in your presentations") |
| External print (data sheets, folders, reports) | FF DIN regular / medium / bold | PDF p.8 |
| Online / web | Roboto | PDF p.8 |
| Logo stand-in below 5 mm | FF DIN Black, width 90%, in blue, grey or white | PDF p.4 |
| E-mail signature | Tahoma or Arial | PDF p.47 |
| Social media and video | Separate guidelines, not provided | PDF p.8 |

- Theme fonts: major = Arial, minor = Arial (TPL theme, font scheme "Larissa Klassisch 2").
- Hierarchy comes from size, not bold: "reduce the use of bold text as much as possible" (PDF p.8, p.22).
- Left alignment; centred or right alignment only as an exception (PDF p.22).
- **Sizes in the template** (TPL master `txStyles`): title 18 pt, regular (not bold); body level 1 18 pt, levels 2–3 16 pt, levels 4–5 14 pt, body colour #333333 (bg2); footer and classification 6 pt. Title-slide and divider titles are 44 pt white (TPL L"Divider blue world"). The PDF gives no PowerPoint point sizes (SKILL §4 notes this as well).
- Other documented sizes: icon descriptors Arial 6 pt in Frequentis black (PDF p.16); letter body text Arial 10.5 pt with 13 pt leading (PDF p.44); business cards FF DIN 8.5/10 pt and 7/9 pt (PDF p.43).
- **Font files and licences**: the template embeds **no fonts** (no `ppt/fonts/`, no `embeddedFontLst` in `presentation.xml`). Arial is a Monotype font that ships with Windows and macOS: use it as a system font and never bundle it. FF DIN is a commercial Monotype/FontFont typeface: never bundle it. Roboto is under the Apache 2.0 / SIL OFL licences and could be bundled, but it is web-only for Frequentis. Fallbacks:
  - Office/Python output: Arial, then Liberation Sans (metric-compatible, OFL, the usual font on Linux VMs), then Helvetica, then sans-serif.
  - Web: Roboto, then Arial, then sans-serif.
  - Print, when FF DIN is not licensed on the machine: say so and leave it to the designer. Do not substitute silently.
- ⚠ The template's sample slides and map layouts carry stray typeface overrides: Nirmala UI (1,093 latin runs, mostly in the map layouts), Calibri (291), Nokia Pure Text/Headline (proprietary Nokia fonts), Arial Narrow (navigation links in the master) and Japanese/East-Asian fallbacks. Never copy a sample slide; build from layouts so the theme fonts apply (a common trap in corporate templates).

## 5. Logo, tagline and key visuals

- **Logo**: the FREQUENTIS striped wordmark. Preferred version: blue on white. White on blue is also fine. On photos or other colours use black or white, and only on a calm background where the logo stays legible. (PDF p.4)
- **Clear space**: at least the height of the logo, measured by the letter F. **Minimum height: 5 mm.** Below that, use the typographic logo. (PDF p.4)
- **Don'ts**: never redraw or recreate the logo, and never add, reproduce or place text or elements over it (PDF p.4). Never retype it as a text stand-in (SKILL §5). No other logos for products, solutions, teams or sub-organisations (PDF p.14).
- **Tagline "FOR A SAFER WORLD"** always comes with the logo as one lock-up, never on its own (video sequences are the only exception). Use it on title and closing pages, event booths, roll-ups, invitations, collateral and videos. Colours: logo #004182, tagline #666666 (CG11). (PDF p.5)
- **Template placement**: the footer logo sits bottom right at x 8.37 in, y 5.29 in, 1.16 × 0.20 in (≈ 29 × 5.1 mm, so exactly the 5 mm minimum) (TPL master shape "Freihandform: Form 49"). The logo with tagline sits top right on the title and closing layouts (TPL L"Standard TITLE", L"Closing Slide"). In the template the logos are **vector shapes, not image files**.
- **Key visuals**: the corporate key visual is the **globe**, for corporate and cross-BU material, full or zoomed, with regional zooms available. Each SBU has its own key visual: ATM = aircraft, Defence = jet formation, Public Safety = police car and crowd, Public Transport = high-speed train, Maritime = rescue vessel. (PDF p.9; TPL L"Standard TITLE" carries all six)
- **Closing**: use the closing slide (globe, logo with tagline). **Never use a "Thank you" slide.** (PDF p.28; TPL s.10)
- **Co-branding**: keep the sizes balanced. Place Frequentis to the right of the partner logo. Portrait partner logos up to 3× the X-height, landscape logos 1×, square or round logos 2×. Do not co-brand with Frequentis Group companies. (PDF p.13)
- **Group branding**: Frequentis AG and regional companies use the FREQUENTIS logo. Group companies follow the table on PDF p.11–12. Contact GCM for anything else.

## 6. Layout and grid (PowerPoint)

- Slide size 16:9, 10 × 5.625 in (9144000 × 5143500 EMU) (TPL `presentation.xml`).
- Content area: title at x 0.47 in, y 0.30 in, width 9.06 in. Body from y 0.83 in, height 4.25 in. Side margins 0.47 in (12 mm) on both sides. Footer band at y ≈ 5.36 in. (TPL master placeholders) Do not place content outside the content area. If it does not fit, split the slide. (TPL s.6)
- Footer (master): page number · presentation title · "<by Presenter>" · classification "Frequentis General" · "© Frequentis AG 2024" ⚠ (the year is out of date; see §10). Update the name, classification and year in the master (PDF p.29).
- **Layouts** (TPL, 44). The name is followed by its placeholders: `title`, then `body#idx`.

| # | Layout | Placeholders | Keep in slim base? |
|---|---|---|---|
| 1 | Standard TITLE | title, body#2 (sub-title, author) | yes |
| 2 | Special topic TITLE | title, body#2 | yes |
| 3 | Headline (standard) | title | yes |
| 4 | Sub-headline (alternative) | title, body#14 (sub-headline) | yes |
| 5 | Headline + Categorie | title, body#14 (category) | yes |
| 6 | Headline + field | title, body#15 | yes |
| 7 | Sub-headline + field | title, #14, #16 | yes |
| 8 | Sub-headline + 50:50 | title, #14, #15, #16 | yes |
| 9 | Sub-headline + 33:67 | title, #14, #15, #16 | yes |
| 10 | Sub-headline + 67:33 | title, #14, #15, #16 | yes |
| 11 | Sub-headline + 33:33:33 | title, #14, #15, #16, #17 | yes |
| 12 | Map | title, #14 | no (3.3 MB XML) |
| 13 | Reference | title, #13, #11 | yes |
| 14 | Reference-DESIGN only | title, #13, #11 | no |
| 15 | 1_Blanc | – | no |
| 16 | Divider blue world | title | yes |
| 17 | Speaker intro (blue world content) | title | yes |
| 18–19 | Small Side Bar 1 / 2 | title | yes |
| 20–21 | Medium Side Bar 1 / 2 | title | yes |
| 22 | Wide Side Bar | title | yes |
| 23 | Video Background | – | no |
| 24 | Closing Slide | – | yes |
| 25 | 1_Headline (standard) (DEV 2021 banner) | title | no |
| 26 | Divider (gradient) | title | yes |
| 27 | 1_Agenda (gradient) | title | yes |
| 28 | 4_Headline | title | no |
| 29 | Blanc (gradient) | – | yes |
| 30 | Guidelines (gradient + box) | title, #14 | yes |
| 31 | 2_Agenda (gradient) | body#10, title | yes |
| 32–37 | Agenda point, R&D, Teams, Next presentation, Break, Q&A (event layouts) | various | no |
| 38–44 | World Map, Americas, APAC, EMEA, Europe, Germany, UK | title | no (0.8–3.3 MB XML each) |

  Placeholder convention: `#14` is the sub-headline, `#15`/`#16`/`#17` are content columns, `#2` is the title-slide subtitle. Leave the footer shapes (`FRQ_*`) alone.
- The PDF names the layout families *Headline only, Sub-headline, Divider/agenda, Small blue side bar, Wide blue side bar, Reference/video overview* (PDF p.28). The real names are in the table above (see §10).
- Shapes: boxes and other shapes are filled with colour and have **no outline** (exception: white on white). The square is a key design element. (PDF p.17) Insert pictures as shape fills, cropped to the shape; 1920×1080 is "more than efficient" (TPL s.8).
- No shadows, mirror effects or 3D, except where they carry meaning, such as an overlay or a state (PDF p.17, p.18, p.29). Charts are always 2D (PDF p.18). No extra lines or decoration that add weight without value (PDF p.18; TPL s.10, s.60).
- Tables: keep them simple, with no extra colours, font styles or sizes (TPL s.34). The template uses a blue header row with white text, a white body and thin grey rules (TPL s.34; SKILL §4).
- Animations only when they support the story. No busy transitions. (TPL s.10)
- Print presentations with "print in greyscale", never black-and-white (PDF p.29).

## 7. Imagery and iconography

- "No image is better than a bad one." Images must be relevant and authentic: no tired metaphors, no "high-glossy" models, aware of cultural context. Use real product photos rather than generated illustrations, and screenshots large enough to read. Themes: user-centricity, internationality, aesthetics of technology, communication and interaction, safety-critical relevance, safety and order. (PDF p.35)
- **Stock photos must be requested from Group Communications and Marketing**, for legal reasons. Frequentis holds commercial usage rights only for photos in the Frequentis Photo stock. Never use images from unofficial or web sources without cleared rights. (PDF p.35)
- Icons come only from the **Frequentis Icon Stock**. New icons are made only with Group Marketing. Icons can sit with or without a square background, with an Arial 6 pt descriptor in Frequentis black, centred, at a distance of 0.1. (PDF p.16)
- The BU identifiers are pictograms for ATM (aircraft), Defence (jet), Public Safety (car), Public Transport (train) and Maritime (ship) (PDF p.16). **The template contains no icon files**, so this skill bundles no icons.
- Infographics follow the same clean, reduced rules (PDF p.19).

## 8. Tone of voice and writing rules

- **British English** (PDF p.20–21; TPL s.7). The exception is material for US use only, under the regionalisation rules (PDF p.21). Regional terms: SESAR vs NextGen, 112 vs 9-1-1, Defence vs Defense (PDF p.40).
- **Sentence case** for text and headlines. No random capitals. Expanding an abbreviation does not capitalise a common noun ("digital scanning (DS)"). (PDF p.21; TPL s.7, s.10)
- Colon: no space before it, one space after it, and no capital after it. The sentence that introduces a bullet list ends with a colon. Each bullet starts with a capital. A full stop is allowed only after the last bullet. (PDF p.21)
- Avoid bold. Use exclamation marks sparingly and only singly. Avoid "&" unless space forces it. Possessive "Frequentis'" (no extra s). Use "communications" on its own or at the end of a compound, and "communication" + noun. (PDF p.22)
- Numbers: spell out one to twelve, and any number that starts a sentence. Hyphenate compounds (twenty-three). Spell out fractions, except in tables. Use a decimal point (15.50) and commas from four digits (2,115). Write 10m and 15bn ("Mio" only in German text). Changes as +10%, €-4.3m. Dates as 25 March 2022 (no "th", no comma). Times as 12:30. (PDF p.22)
- Tone: shorter is better (at least 30% shorter). One sentence per idea. Lead with the story. Know the reader. Avoid jargon. Use active voice and the present tense. Use "we", but not "At Frequentis we…". Be bold and precise. (PDF p.23)
- Formal register (press, web, customer material) vs casual register (social, intranet). The formal register avoids contractions, colloquialisms, clichés, "you", abbreviated words and the imperative, and spells out acronyms at first use (PDF p.24). ⚠ The PDF's formal column also says "write in third person" and "use passive voice", which clashes with p.23. See §10.
- Company name: "Frequentis" in sentence case in running text **and in PPT headlines**. "FREQUENTIS" in capitals only in print headlines. Legal entity: Frequentis AG. **"FRQ" is internal only**; avoid it in external communication. (PDF p.25)
- Classification on every non-public document: Frequentis Public, Frequentis General (Inner Circle) or Frequentis Confidential. Set it in the slide master. Copyright line: "© Frequentis AG [year]", plus "all rights reserved" in print. Printed publications carry the standard disclaimer. (PDF p.26)
- Storytelling advice in the template: start with the unexpected, make it about the audience, keep it short (use speaker notes), get to the point (TPL s.3). Do not turn slides into a reading lesson (TPL s.10).

## 9. Business units

- SBUs: Air Traffic Management (ATM), Defence (DEF), Public Safety (PS), Public Transport (PT), Maritime (MAR). Each has a key visual (PDF p.9), a legend colour (PDF p.7) and an icon identifier (PDF p.16).
- **Default BU: ATM** (SKILL front matter, §5): the ATM aircraft key visual on title slides and #2364A0 as the extra legend colour. Corporate or cross-BU content uses the globe.
- BU presentations reuse the existing BU template structure (PDF p.28). OneATM and DEF style guides are "being updated" (PDF p.41) and were not available for this extraction.
- Footer/brand: SBU names in running text such as "Frequentis ATM offers …" (PDF p.25).

## 10. Conflicts and gaps

The chosen resolution for each is in `../SKILL.md` (Known conflicts); this table keeps the evidence.

| # | Topic | PDF | Template | Earlier skill | Proposed resolution |
|---|---|---|---|---|---|
| C1 | Cool grey and mid grey HEX | HEX #666666 / #999999, but its own RGB values give #626469 / #9FA0A3 (p.7) | Theme uses #626469 / #9FA0A3 | #666666 / #999999 | The PDF labels RGB as "MS Office" and HEX as "online". Use **#626469 / #9FA0A3 in Office files** (match the theme) and #666666 / #999999 on the web. The checker accepts both. |
| C2 | Headline colour | Blue is the lead colour; the only gradient is #004182→#00AAE1 (p.7, p.17) | Master title text is filled with a **gradient #00529B→#0588FF** (off-palette). LibreOffice renders it black. | "Blue headlines" (#004182) | Leave the master alone, and never override title colour in generated slides. Flag it to GCM as a template defect. A checker should not report inherited master styles. |
| C3 | Divider gradient | Only #004182→#00AAE1 (p.17) | L"Divider blue world" uses #2F88C2/#2C82BD/#105A98→tx1 | Only the PDF gradient | Using the layout is fine. Do not copy those stops into new shapes. |
| C4 | Footer year | Footer shows "© Frequentis AG 2025" | Master says "© Frequentis AG 2024" and "<by Presenter>" | "Frequentis <class> \| © Frequentis AG <year>" | Generator sets the current year and the classification. |
| C5 | Layout names | Generic family names (p.28) | Real names, e.g. "Headline (standard)", "Sub-headline (alternative)", "Small Side Bar 1" | Lists the PDF names (§2.3) | Use the real template names and map the PDF families to them. |
| C6 | Formal register | p.24 formal: third person, passive voice. p.23 tone: active voice, "we". | – | Follows p.23 and takes only the "avoid" rules from p.24 | Keep the earlier skill's decision; a human confirms it. |
| C7 | Tagline grey | Tagline #666666 (p.5) | Tagline shape on title layouts is white over the globe | – | The blue lock-up SVG uses #666666 per the PDF. |
| C8 | Key visual on the title slide | BU title slides show one large BU image (p.28) | L"Standard TITLE" = globe plus five small SBU tiles | ATM aircraft on the title slide | For ATM decks keep the ATM tile, or use the ATM image as the hero. A human picks. |
| C9 | Fonts in the template | Arial only for Office (p.8) | Stray Nirmala UI, Calibri, Nokia Pure, Arial Narrow overrides in samples and maps | Arial only | Build from layouts only. The checker fails explicit non-Arial typefaces on slides and reports inherited ones as INFO. |
| C10 | White on light blue | – | Used in TPL s.7 | – | WCAG fail (2.7:1). Warn, do not block. |
| G1 | Gaps | No PowerPoint point sizes, no logo SVG/PNG in the package (only links to "Logo download"), no icon files, no audio. OneATM and DEF guides are pending. | – | – | Ask GCM for the official logo pack, Icon Stock access and the ATM style guide. |
