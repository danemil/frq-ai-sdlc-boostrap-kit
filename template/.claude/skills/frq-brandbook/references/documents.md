# Word, Excel, PDF, HTML and diagrams

The brand has no official Word or Excel template in this skill (ask Group Communications and Marketing for one if the file is customer-facing). Until then, map the palette and fonts as below. Values come from `../brand-tokens.json`; Office files use the Office HEX values, web pages the web HEX values (conflict C1).

## Common mapping

| Element | Office (Word, Excel, PowerPoint) | Web (HTML, CSS) |
|---|---|---|
| Font | Arial (fallback Liberation Sans on Linux) | Roboto, Arial, sans-serif |
| Body text | #333333, regular | #333333 |
| Headings | #004182, regular or bold, sentence case | #004182 |
| Secondary text, captions | #626469 | #666666 |
| Lines, rules, recessed data | #9FA0A3 | #999999 |
| Backgrounds, panels | white; #C9C3BA or grey tints sparingly | same |
| Highlights, status | #73B432 / #F0A51E / #A52846, sparingly, never as text colour (red #A52846 is the exception) | same |
| Legend-only BU colours | ATM #2364A0 (default), others in `brand-tokens.json` | same |

Never italics, never shadows, no colour tints of brand colours (grey tints are fine), left-aligned text.

## Word (with `ai-sdlc-doc-word`)

- Styles, not direct formatting: set `Normal` to Arial 10.5 pt, #333333, and `Heading 1–3` to Arial, #004182, sentence case. The guidelines give 10.5 pt with 13 pt leading for letters (PDF p.44); reports have no size rule, so keep 10–11 pt body.
- Footer on every page: `Frequentis <class> | © Frequentis AG <year>` and the page number; logo top right in the header, at least 5 mm high, from `../assets/logo/logo-frequentis-wordmark-blue.png` (Word cannot place the SVG through python-docx).
- Tables: header row #004182 with white text, white body, thin #9FA0A3 rules, no zebra colours.
- Cover page (optional): a side bar from `../assets/background/bg-sidebar-*.jpg` or the key visual for the business unit; title in #004182.
- Run `../scripts/check_brand.py file.docx`: it checks colours, fonts, italics, "FRQ" and the classification.

## Excel (with `ai-sdlc-doc-excel`)

- Font Arial 10 or 11 pt for every style you add; header row fill #004182 with white bold text; number formats with commas from four digits (2,115) and a decimal point.
- Charts: 2D only; series colours in order #004182, #00AAE1, #626469, #9FA0A3, #C9C3BA; highlight one item with one accent; BU colours only in legends.
- Put the classification in the sheet header or footer (Page Layout → Header/Footer) and, for shared workbooks, in a cell on the first sheet.
- The checker reports Excel's default styles (Calibri or Aptos, black) as WARN, because every workbook has them; fix the styles you control.

## PDF (with `ai-sdlc-doc-pdf`)

Make the source (Word or PowerPoint) on-brand and export it; check the source with `check_brand.py`, since a PDF cannot be checked for fonts and colours reliably. For a PDF built directly with reportlab, use Helvetica only if Arial is not available (it is metric-compatible) and say so; set the same colours and the classification footer.

## HTML and web (with `ai-sdlc-visual-explainers`)

```css
:root {
  --frq-blue: #004182;        /* lead colour */
  --frq-light-blue: #00AAE1;  /* secondary; white text on it only at 18pt+ */
  --frq-black: #333333;       /* body text */
  --frq-cool-grey: #666666;   /* web value (Office: #626469) */
  --frq-mid-grey: #999999;    /* web value (Office: #9FA0A3); never body text */
  --frq-warm-grey: #C9C3BA;
  --frq-green: #73B432; --frq-orange: #F0A51E; --frq-red: #A52846;
  --frq-gradient: linear-gradient(45deg, #004182, #00AAE1);   /* the only gradient */
  --frq-font: "Roboto", Arial, sans-serif;
}
body { font-family: var(--frq-font); color: var(--frq-black); background: #FFFFFF; }
h1, h2, h3 { color: var(--frq-blue); font-weight: 400; }
```

- Logo: inline `../assets/logo/logo-frequentis-wordmark-blue.svg` (or the white version on blue), with `alt="Frequentis"`, at least 5 mm (about 19 px) high, clear space equal to its height.
- Load Roboto from the company's approved source or the system; do not bundle font files.
- Dark mode is not defined by the guidelines: keep white backgrounds for anything branded, or ask.
- Contrast: #00AAE1, #999999, warm grey, green and orange fail as text on white; use them for shapes.

## Diagrams (with `ai-sdlc-drawio` or `ai-sdlc-likec4-dsl`)

- Flat filled boxes with no outline (white on white may keep a thin #9FA0A3 line), no shadows (`shadow=0` in draw.io), no rounded "glossy" styles, no 3D.
- Key node #004182 with white Arial text; supporting nodes #C9C3BA or #9FA0A3 with #333333 text; one accent for the thing to notice.
- Straight or orthogonal connectors in #626469; labels Arial, sentence case.
- draw.io style snippet: `fillColor=#004182;strokeColor=none;fontColor=#FFFFFF;fontFamily=Arial;shadow=0;rounded=0;`
- LikeC4: define element colours in the `specification` block with these HEX values and apply them by kind, so one change re-colours the model.
- No product or BU logos inside diagrams: Frequentis has no logos for products, solutions or teams (PDF p.14).
