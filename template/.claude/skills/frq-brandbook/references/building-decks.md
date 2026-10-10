# Building decks

## Two templates, two front ends

Both templates stay in the kit copy, not in the placed skill (`.kit-only`); the scripts find them, and you name them by exact path:

| Template | Path | Layouts | A deck on it |
|---|---|---|---|
| **Slim (the default)** | `.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/templates/frq-template-slim-core.pptx` | 25: the official template without its 66 sample slides and without the map and event layouts | about 1.2 MB |
| **Full master** | `.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/templates/frq-master.pptx` | all 44, including the seven map layouts, the event layouts and *Video Background* | about 9 MB, even with three slides |

Both carry the one slide master and the "FRQ_CORP 2024" theme (palette and Arial), 16:9, 10 × 5.625 in, with personal and tenant metadata stripped. **Use the slim template unless a slide needs a layout only the full master has** (`layouts.md` marks each layout *slim and full* or *full only*); the builder decides this itself and says so ("used the full master for: World Map | EMEA"). The person can ask for either (`--template slim|full`). When fixing an existing deck, keep its own master if it is the Frequentis one.

| Front end | Input | Use it when |
|---|---|---|
| `scripts/new_deck.py` | a Markdown outline | a text deck: title, headline-and-bullet slides, closing. Always the slim template. |
| `scripts/frq_pptx.py build` | a JSON spec (`build-spec.md`) | any layout of the 44, tables, charts, KPI donuts, key visuals, photo and icon placeholders, side-bar text. |

Both need python-pptx (ask first; venv `~/.ai-sdlc/venv`), take the classification the person gave, never overwrite a file, and set the master footer. `new_deck.py` turns the outline into a spec and calls `frq_pptx.build()`, so there is one builder.

## Rules

1. **Start from a template** (the builder does), never from a blank `Presentation()` and never from an old deck. Read it, never save over it.
2. **Pick layouts by name**, not by position: `layouts = {l.name: l for l in prs.slide_layouts}`.
3. **Fill placeholders by index** (table below). Do not move or resize them; keep content inside the content area (x 0.47 in, y 0.83 in, 9.06 × 4.25 in). If it does not fit, split the slide.
4. **Set no font, size or colour** on placeholder text (text you add outside placeholders is different: see "Shapes, free text, tables and charts"). The theme gives Arial, #333333 body text and the title style. Setting a title colour fights the master (conflict C2).
5. **Never copy a slide** from the full template or another deck: the samples carry stray Nirmala UI, Calibri and Nokia Pure overrides (C9) that the checker fails.
6. **Leave the footer shapes alone** (`FRQ_Classification`, `FRQ_Copyright`, `FRQ_Filename`, `FRQ_Pagenumber`), except their text in the master: class, current year, title, presenter (C4). `scripts/new_deck.py` does this.
7. **Close with "Closing Slide"**, never a "Thank you" slide.
8. Pictures go into shapes as fills, cropped to the shape; 1920 × 1080 is plenty. Only Frequentis key visuals (`.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/keyvisual/`; ATM by default, C14) or photos the person supplies from the Frequentis Photo stock.
9. Run `../scripts/check_brand.py` on the result, then look at it ("Look at the result" below). Report what the checker found as evidence found or not found; never call the deck "on-brand" or "compliant". A person reviews it before it is shared.

## The 25 layouts of the slim template

All 44 layouts, with previews and geometry: `layouts.md`.

`title` is the title placeholder; `#n` is a body placeholder with `placeholder_format.idx == n`. `#14` is the sub-headline, `#15`/`#16`/`#17` content columns, `#2` the title-slide sub-title.

| Need | Layout name | Placeholders |
|---|---|---|
| Title slide (globe + five BU tiles, logo with tagline) | `Standard TITLE` | title, #2 (sub-title, author, date) |
| Title slide for a special topic (own picture) | `Special topic TITLE` | title, #2 |
| Headline only, free content area | `Headline (standard)` | title |
| Headline and a sub-headline | `Sub-headline (alternative)` | title, #14 |
| Headline with a category label above it | `Headline + Categorie` | title, #14 (category) |
| Headline and one text field (bullets) | `Headline + field` | title, #15 |
| Sub-headline and one text field | `Sub-headline + field` | title, #14, #16 |
| Two columns | `Sub-headline + 50:50` | title, #14, #15, #16 |
| Narrow left, wide right | `Sub-headline + 33:67` | title, #14, #15, #16 |
| Wide left, narrow right | `Sub-headline + 67:33` | title, #14, #15, #16 |
| Three columns | `Sub-headline + 33:33:33` | title, #14, #15, #16, #17 |
| Customer reference (challenge, quote) | `Reference` | title, #13, #11 |
| Chapter divider on the blue world | `Divider blue world` | title |
| Speaker or agenda intro on the blue world | `Speaker intro` | title |
| Data-heavy slide with a small blue side bar | `Small Side Bar 1`, `Small Side Bar 2` | title (in the bar) |
| Medium blue side bar | `Medium Side Bar 1`, `Medium Side Bar 2` | title |
| Intro-heavy slide with a wide blue side bar | `Wide Side Bar` | title |
| Closing (globe, logo with tagline) | `Closing Slide` | none |
| Chapter divider on the gradient | `Divider` | title |
| Agenda on the gradient | `1_Agenda` | title |
| Agenda with agenda points | `2_Agenda` | #10 (points), title |
| Empty slide on the gradient | `Blanc` | none |
| Guidelines or key-message box on the gradient | `Guidelines` | title, #14 |

The PDF's layout families map to these names (C5): *Headline only* → `Headline (standard)`; *Sub-headline* → `Sub-headline (alternative)` and the `Sub-headline + …` family; *Divider/agenda* → `Divider`, `Divider blue world`, `1_Agenda`, `2_Agenda`; *Small blue side bar* → `Small Side Bar 1/2`; *Wide blue side bar* → `Wide Side Bar`; *Reference/video overview* → `Reference` (the video layout is not in the slim template).

Only in the full master: `Map` and the world and region map layouts (0.8–3.3 MB of XML each), `Reference-DESIGN only`, `1_Blanc`, `Video Background`, `1_Headline (standard)`, `4_Headline` and the event layouts (Agenda point, R&D, Teams, Next presentation, Break, Q&A). The builder takes the full master for them.

## Recipe (python-pptx)

Get python-pptx as `ai-sdlc-doc-powerpoint` describes (ask first; personal venv `~/.ai-sdlc/venv`). The quickest path is the script:

```bash
python3 scripts/new_deck.py outline.md docs/remote-towers.pptx --classification "<the class the person gave>" --author "Ana Pop"
```

Outline: `# Deck title`, the next line is the sub-title; each `## Headline` is a slide (`Headline + field`, `Sub-headline + field` when a `> sub-headline` line follows, `Headline (standard)` when it has no content); `- bullet` or `1. item`, two spaces per level; plain lines become paragraphs; `**bold**` markers are removed. Tables and code blocks are not placed: the script lists them, and stops without writing if a slide would end up empty. `--classification` is required: ask the person; if you cannot ask, pass `Frequentis [classification to be set]` and say so. Run the script as a command, never import it. It adds the `Closing Slide`, sets the footer, and refuses to overwrite.

By hand, for other layouts:

```python
from pptx import Presentation
prs = Presentation(TEMPLATE)                    # the bundled slim template, never modified
layouts = {l.name: l for l in prs.slide_layouts}

def ph(slide, idx):
    return next(p for p in slide.placeholders if p.placeholder_format.idx == idx)

s = prs.slides.add_slide(layouts["Sub-headline + 50:50"])
s.shapes.title.text = "Two options, one decision"      # the key message
ph(s, 14).text = "Both meet the safety case"
ph(s, 15).text_frame.text = "Option A: upgrade in place"
ph(s, 16).text_frame.text = "Option B: new working positions"
s.notes_slide.notes_text_frame.text = "Say why we recommend B."

prs.slides.add_slide(layouts["Closing Slide"])
prs.save(out_path)                               # a new file; check os.path.exists first
```

### Shapes, free text, tables and charts

python-pptx's defaults are not on-brand in this template: `add_shape()` inherits a **drop shadow** and a **grey gradient with an outline** from the theme styles, `add_textbox()` text is **blue** (the theme's text colour is #004182), charts come out **grey** with a bold title and heavy gridlines (the theme's accent1 is mid grey), and `add_table()` uses a built-in style with a grey header. Set everything explicitly:

```python
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
BLUE, LIGHT, BLACK, GREY, MID, WARM, WHITE = (RGBColor.from_string(h) for h in
    ("004182", "00AAE1", "333333", "626469", "9FA0A3", "C9C3BA", "FFFFFF"))

def flat_box(slide, x, y, w, h, colour=BLUE):
    shape = slide.shapes.add_shape(1, x, y, w, h)          # 1 = rectangle: the square is a brand element
    style = shape._element.find(qn("p:style"))
    if style is not None:
        shape._element.remove(style)                          # no theme shadow, gradient or outline
    shape.fill.solid(); shape.fill.fore_color.rgb = colour
    shape.line.fill.background()                              # no outline
    return shape

def text_box(slide, x, y, w, h, text):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tb.text_frame.text = text
    for p in tb.text_frame.paragraphs:
        for r in p.runs:
            r.font.color.rgb = BLACK                          # body text #333333; leave the font to the theme
    return tb

def brand_table(slide, rows, x, y, w, row_h=Inches(0.35)):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), x, y, w, row_h * len(rows))
    tbl = shape.table
    tbl.first_row = True
    tbl.horz_banding = False                                  # no zebra colours
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = str(value)
            cell.fill.solid(); cell.fill.fore_color.rgb = BLUE if r == 0 else WHITE
            for run in (run for p in cell.text_frame.paragraphs for run in p.runs):
                run.font.color.rgb = WHITE if r == 0 else BLACK
                run.font.size = Pt(14)
    return tbl

def brand_chart(chart, highlight=None):
    """2D chart: series in palette order (or one highlighted, the rest grey), no chart title."""
    order = [BLUE, LIGHT, MID, WARM, GREY]                    # brand-tokens.json charts.series (C17)
    chart.has_title = False                                   # the slide headline carries the message
    for i, series in enumerate(chart.plots[0].series):
        colour = (BLUE if i == highlight else MID) if highlight is not None else order[i % len(order)]
        series.format.fill.solid(); series.format.fill.fore_color.rgb = colour
        series.format.line.fill.background()
    chart.has_legend = len(chart.plots[0].series) > 1
    if chart.has_legend:
        chart.legend.include_in_layout = False
        chart.legend.font.color.rgb = BLACK
    for ax in (chart.category_axis, chart.value_axis):
        ax.tick_labels.font.color.rgb = BLACK                 # not the theme's blue text colour
    chart.value_axis.has_major_gridlines = False              # no gridlines (check rule chart.gridlines)
    chart.category_axis.has_major_gridlines = False
```

## Look at the result

The checker reads XML; it does not see layout, overlaps, logo use or what PowerPoint draws from theme styles. Look at the slides before you hand over:

1. If LibreOffice and poppler are available: `frq_pptx.py render deck.pptx` writes one PNG per slide under `.ai-sdlc/tmp/deck/` (hidden from git; never `/tmp`), or use the two commands in `../SKILL.md` (Check, step 3). View the PNGs.
2. Otherwise ask the person to open it in PowerPoint and look, slide by slide.
3. Check: one message per slide, nothing outside the content area, no overlaps, the logo untouched, key visual and closing slide in place, text readable.

## Traps

- LibreOffice renders the master's gradient-filled titles black (C2) and draws a shadow under the footer logo (the master's empty effect override is ignored); PowerPoint shows both correctly. Judge colours in PowerPoint, or trust the checker.
- Rendering replaces Arial with Liberation Sans unless Arial is installed; the layout matches, the font name in a PDF does not.
- `Standard TITLE` already shows the globe and the five BU tiles; do not add a second key visual on top.
- The template has no icon files. Where an icon helps, leave a blue #004182 square with an Arial descriptor below and a speaker note: "Insert icon from the Frequentis Icon Stock: <meaning>".
- White text on light blue (#00AAE1) fails contrast at any size (C10): in new slides put #333333 text on light blue, or #004182 for large text (WCAG, kit rule).

## Check rules

`scripts/check_brand.py` is the one brand check (stdlib, no install); `frq_pptx.py audit` only runs it. Every rule of the kit owner's `frq-4-pptx-agent` v1.0 audit is covered. Severity: the owner's *Must* is FAIL and *Should* is WARN, except where the 0.8.0 rule was kept (marked).

| # | Owner audit rule | `check_brand.py` id | Severity |
|---|---|---|---|
| 1 | No Frequentis master footer | `template.not-company` (new) | FAIL |
| 2 | Footer title still "Presentation title" | `footer.placeholder` (new) | FAIL |
| 3 | Footer presenter still "<by Presenter>" | `footer.placeholder` (new) | FAIL |
| 4 | Copyright year not the current year | `footer.year` | WARN (0.8.0 kept) |
| 5 | Layout not from the Frequentis master | `layout.not-company` (new; names in `brand-tokens.json`) | FAIL |
| 6 | Deck does not start on *Standard TITLE* | `deck.first-slide` (new; *Special topic TITLE* also fine) | WARN |
| 7 | Deck does not end on *Closing Slide* | `deck.last-slide` (new) | FAIL |
| 8 | Title Case headline | `text.title-case` | WARN |
| 9 | Headline is a label, not a message (two words or fewer; dividers, agendas, Q&A and closing exempt) | `text.label-headline` (new) | WARN |
| 10 | Centred or right-aligned body text | `text.align` | WARN |
| 11 | Italic text | `text.italic` | FAIL |
| 12 | Non-Arial fonts | `font.non-brand` | FAIL |
| 13 | Most text bold | `text.bold` | WARN |
| 14 | Overcrowded: more than 90 words | `slide.words` (new) | WARN |
| 15 | Overcrowded: too many paragraphs | `slide.bullets` | WARN |
| 16 | "FRQ" or "FREQUENTIS" on slides | `text.frq`, `text.caps-name` | FAIL customer-facing, WARN internal (C16, 0.8.0 kept) |
| 17 | "Thank you" or "Questions?" slide | `slide.thank-you` | FAIL |
| 18 | Template leftovers (lorem ipsum, "Click to add", annotations, NOTE, xxx, event image, special topic picture) | `text.leftover` (new) | FAIL |
| 19 | US spelling | `text.us-spelling` | WARN |
| 20 | Contractions | `text.contraction` | WARN (0.8.0 pattern kept: it does not flag possessives) |
| 21 | "&" in text | `text.ampersand` | INFO (0.8.0 kept: the PDF allows it when space forces it) |
| 22 | Several exclamation marks | `text.exclamation` | WARN |
| 23 | US date format | `text.date` | WARN |
| 24 | Off-palette colours | `colour.off-palette` | FAIL |
| 25 | Gradient other than blue to light blue | `gradient.non-brand` | FAIL on slides; the template's own stops INFO (C13) |
| 26 | Shadow, glow or reflection | `effect.shadow` | FAIL |
| 27 | 3D effect | `effect.3d` | FAIL |
| 28 | Outline on a filled shape | `shape.outline` | WARN |
| 29 | Rounded rectangle | `shape.rounded` (new) | WARN |
| 30 | 3D chart | `effect.3d` | FAIL |
| 31 | Off-palette chart colours | `colour.off-palette`; the track grey #EDF1F2 is fine in charts, `colour.chart-only` elsewhere (new, C12) | FAIL / WARN |
| 32 | Chart gridlines | `chart.gridlines` (new) | WARN |
