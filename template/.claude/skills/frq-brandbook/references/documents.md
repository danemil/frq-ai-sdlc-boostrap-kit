# Word, Excel, PDF, HTML, diagrams, issues and mail

Values come from `../brand-tokens.json`. Office files use the Office HEX values and web pages the web HEX values (conflict C1).

**Classification: ask, never guess.** Every footer below (Word, Excel, HTML, diagrams) carries `Frequentis <class> | © Frequentis AG <year>`. Ask the person for the class (Public, General or Confidential) before you write it. If you cannot ask, write the literal `Frequentis [classification to be set]` and list it in the hand-over; never pick one yourself.

## Common mapping

| Element | Office (Word, Excel, PowerPoint) | Web (HTML, CSS) |
|---|---|---|
| Font | Arial (fallback Liberation Sans on Linux) | Roboto, Arial, sans-serif |
| Body text | #333333, regular | #333333 |
| Headings | #004182, regular or bold, sentence case | #004182 |
| Secondary text, captions | #626469 | #666666 |
| Lines, rules, recessed data | #9FA0A3 | #999999 |
| Backgrounds, panels | white; #C9C3BA or grey tints sparingly | same |
| Highlights, status | #73B432 / #F0A51E / #A52846, sparingly; green and orange not as text on white (WCAG, kit rule) | same |
| Legend-only BU colours | ATM #2364A0 (default), others in `brand-tokens.json` | same |

Never italics, never shadows, no tints of brand colours (grey tints are fine), left-aligned text.

## Word (with `ai-sdlc-doc-word`)

**Do this first, in every python-docx script** (else Word shows Calibri and the checker warns): `style.font.name = "Arial"` leaves `w:asciiTheme`/`w:hAnsiTheme` on the heading styles, and Word then uses the theme font (Calibri). Remove the theme attributes:

```python
from docx.oxml.ns import qn
for name in ("Normal", "Heading 1", "Heading 2", "Heading 3", "Title"):
    rpr = doc.styles[name].element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = rpr.makeelement(qn("w:rFonts"), {}); rpr.append(fonts)
    for att in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        fonts.attrib.pop(qn(att), None)
    fonts.set(qn("w:ascii"), "Arial"); fonts.set(qn("w:hAnsi"), "Arial")
```

**Customer-facing documents start from the official Word template.** The guidelines (PDF p.45) say the Word templates `Doknorme.dotm` (English) and `Doknormd.dotm` (German), from Word → *Shared Templates*, are for **all publications, manuals, descriptions and instructions delivered to customers**, and strongly recommended for internal ones. Ask the person for a copy of the `.dotm` (it is not bundled), then build on it: `Document("Doknorme.dotm")` does not open a `.dotm` directly with python-docx, so ask them to save an empty document from the template as `.docx` first, and use that file as the base. The **letterhead** (PDF p.44) and the **visitor agenda** (PDF p.48) also come from Word → Shared Templates; never rebuild them.

Use the mapping below only for internal notes, or when the person cannot get the template (say so in the hand-over):

- Styles, not direct formatting: `Normal` Arial 10.5 pt, #333333 (the letter body size, PDF p.44); `Heading 1–3` Arial, #004182, sentence case (the snippet above sets the fonts).
- Footer on every page: `Frequentis <class> | © Frequentis AG <year>` and the page number. Logo top right in the header, at least 5 mm high: `header.paragraphs[0].add_run().add_picture("../assets/logo/logo-frequentis-wordmark-blue.png", height=Mm(6))` (python-docx cannot place the SVG).
- Tables: header row fill #004182 with white text, white body, thin #9FA0A3 rules, no zebra colours. Set the fill per header cell (`w:shd w:fill="004182"`) instead of a built-in table style, which brings its own colours.
- Run `../scripts/check_brand.py file.docx`: it checks colours, fonts (including theme fonts), italics, the internal abbreviation and the classification, for styles the document uses.

## Excel (with `ai-sdlc-doc-excel`)

**Put this in every openpyxl script and call it last, just before `wb.save()`.** openpyxl writes every cell in Calibri 11 (changing the Normal style does not change that), and the checker warns on it. This keeps each cell's bold, size and colour:

```python
from openpyxl.styles import Font

def arial_everywhere(wb):
    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for c in row:
                f = c.font
                c.font = Font(name="Arial", size=f.sz, bold=f.b, color=f.color)
```

- Header row fill #004182 with white bold text; number formats with commas from four digits (2,115) and a decimal point.
- Pass/fail and status: the accents green #73B432, orange #F0A51E, red #A52846 as cell fills (conditional formatting), with #333333 text; never as text colour on white.
- Charts: 2D only; series colours in order #004182, #00AAE1, #626469, #9FA0A3, #C9C3BA; highlight one item with one accent; BU colours only in legends.
- Classification (asked, never guessed) in the sheet header or footer (Page Layout → Header/Footer) and, for shared workbooks, in a cell on the first sheet.

## PDF (with `ai-sdlc-doc-pdf`)

Make the source (Word or PowerPoint) on-brand, check the source with `check_brand.py`, then export: `soffice --headless --convert-to pdf --outdir <folder> <file>`. LibreOffice replaces Arial with Liberation Sans unless Arial (or `ttf-mscorefonts`) is installed; the shapes match but the PDF says "LiberationSans". Tell the person: for a customer PDF, export from PowerPoint or Word on their own machine. LibreOffice also draws the deck master's title gradient black and a shadow under the footer logo (both fine in PowerPoint).

## HTML and web (with `ai-sdlc-visual-explainers`)

```css
:root {
  --frq-blue: #004182;        /* lead colour */
  --frq-light-blue: #00AAE1;  /* secondary; text on it in #333333, never white (WCAG, kit rule) */
  --frq-black: #333333;       /* body text */
  --frq-cool-grey: #666666;   /* web value (Office: #626469) */
  --frq-mid-grey: #999999;    /* web value (Office: #9FA0A3); shapes and lines (WCAG, kit rule) */
  --frq-warm-grey: #C9C3BA;
  --frq-green: #73B432; --frq-orange: #F0A51E; --frq-red: #A52846;
  --frq-gradient: linear-gradient(45deg, #004182, #00AAE1);   /* the only gradient */
  --frq-font: "Roboto", Arial, sans-serif;
}
body { font-family: var(--frq-font); color: var(--frq-black); background: #FFFFFF; }
h1, h2, h3 { color: var(--frq-blue); font-weight: 400; }
```

- Footer: `Frequentis <class> | © Frequentis AG <year>`, the class asked, never guessed (see the top of this file).
- Logo: inline `../assets/logo/logo-frequentis-wordmark-blue.svg` (or the white version on blue), with `alt="Frequentis"`, at least 5 mm (about 19 px) high, clear space equal to its height.
- Roboto: use it if the system has it, else the stack falls back to Arial; do not bundle font files.
- Dark mode is not defined by the guidelines: keep white backgrounds for anything branded, or ask.
- Contrast (WCAG, kit rule): #00AAE1, #999999, warm grey, green and orange fail as text on white; use them for shapes. White on #00AAE1 fails at any size: use #333333 on it.

## Diagrams

**draw.io (with `ai-sdlc-drawio`).** Flat filled boxes with no outline (white on white may keep a thin #9FA0A3 line), no shadows, no rounded glossy styles, no 3D. Copy-ready styles:

- key node: `rounded=0;whiteSpace=wrap;fillColor=#004182;strokeColor=none;fontColor=#FFFFFF;fontFamily=Arial;shadow=0;`
- supporting node: `rounded=0;whiteSpace=wrap;fillColor=#C9C3BA;strokeColor=none;fontColor=#333333;fontFamily=Arial;shadow=0;`
- edge: `endArrow=block;endFill=1;strokeColor=#626469;strokeWidth=1;fontFamily=Arial;fontColor=#333333;edgeStyle=orthogonalEdgeStyle;`
- label or note: `text;fontFamily=Arial;fontColor=#333333;align=left;`
- footer: a label at the bottom left, `Frequentis <class> | © Frequentis AG <year>`, the class asked, never guessed.

**LikeC4 (with `ai-sdlc-likec4-dsl`).** Define the colours once in the specification and use them by kind:

```likec4
specification {
  color frq-blue #004182
  color frq-light-blue #00AAE1
  color frq-warm-grey #C9C3BA
  color frq-cool-grey #626469

  element system {
    style { color frq-blue }
  }
  element external {
    style { color frq-warm-grey }
  }
  relationship uses {
    color frq-cool-grey
  }
}
```

**Mermaid in issues and PRs (with `ai-sdlc-visual-issue`).** Issues are internal: no branding is required. If the person wants the colours, start the diagram with:
`%%{init: {'theme':'base','themeVariables':{'primaryColor':'#004182','primaryTextColor':'#FFFFFF','lineColor':'#626469','fontFamily':'Arial'}}}%%`

No product or BU logos inside diagrams: Frequentis has no logos for products, solutions or teams (PDF p.14).

## E-mail, Teams and chat text

- Apply the writing rules (`writing-style.md`): British English, sentence case, "Frequentis", numbers and dates.
- **External e-mails must carry the e-mail signature** (PDF p.47), as defined in the Global Corporate Manual, in Tahoma or Arial; internal mails may omit it. Do not build a signature yourself; ask the person to use their standard one.
- Never paste the logo as an image into a mail body or a Teams message (the event footer image above is the exception). Event e-mail footers (PDF p.39) come from GCM for GCM events; for other events, from GCM's PowerPoint footer template (Event in a Box), saved as an image and added to the signature.
- Internal abbreviations are fine internally; spell out "Frequentis" in anything that goes outside.
