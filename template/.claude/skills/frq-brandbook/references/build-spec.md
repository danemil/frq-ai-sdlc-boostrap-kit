# Build spec and manual recipes

From the kit owner's frq-4-pptx-agent v1.0, adapted to this kit's rules. `frq_pptx.py` needs python-pptx: ask the person first, then install it into the personal venv `~/.ai-sdlc/venv` as `ai-sdlc-doc-powerpoint` describes, and run the script with that Python. Below, `<skill>` is `.agents/skills/ai-sdlc-frq-brandbook` (the placed skill) and `<kit>` is `.ai-sdlc/kit/template/.claude/skills/frq-brandbook` (the kit copy, which holds the templates and pictures).

## `frq_pptx.py build SPEC.json OUT.pptx --classification "<class>"`

```bash
~/.ai-sdlc/venv/bin/python <skill>/scripts/frq_pptx.py build SPEC.json docs/remote-towers.pptx --classification "<the class the person gave>"
```

- `--classification` is required: ask the person (*Frequentis Public*, *Frequentis General* or *Frequentis Confidential*) and never guess it. If you cannot ask, pass `Frequentis [classification to be set]` and say so in the hand-over. A `classification` field in the spec must say the same.
- The deck goes on the slim template (`.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/templates/frq-template-slim-core.pptx`, 25 layouts) unless a slide needs a layout only the full master has (`.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/templates/frq-master.pptx`, 44 layouts); then it prints `used the full master for: <layouts>`. `--template slim|full` forces one. `layouts.md` marks each layout.
- `OUT.pptx` must not exist: the script never overwrites a file. It sets the master footer (C11): `<title> | <presenter> | <class> | © Frequentis AG <year>`.

The spec is a JSON file:

```json
{
  "title": "Remote digital towers",
  "presenter": "by Ana Pop",
  "year": 2026,
  "slides": [
    {"layout": "Standard TITLE", "title": "Remote digital towers for regional airports",
     "subtitle": "Customer briefing | 9 October 2026"},
    {"layout": "2_Agenda", "title": "Agenda",
     "content": [["Why remote towers now", "How the solution works", "Business case", "Next steps"]]},
    {"layout": "Divider blue world", "title": "Why remote towers now"},
    {"layout": "Sub-headline + field",
     "title": "Remote towers cut tower staffing costs by a third",
     "subtitle": "One centre serves several regional airports",
     "content": [["Controllers work from one remote tower centre",
                  "Cameras replace the out-of-window view", ["Overlays add safety information"]]],
     "notes": "Speaker notes go here."},
    {"layout": "Closing Slide"}
  ]
}
```

`title` and `presenter` fill the footer (the presenter may be empty); `year` defaults to `--year`, then the current year. `business_unit` (`ATM` by default; `DEF`, `PS`, `PT`, `MAR`, or `CORP` for the template's globe; `--business-unit` on the command line wins) puts that unit's key visual in the big square of the *Standard TITLE* slide; `"key_visual": false` keeps the template's globe.

### Slide fields

| Field | Meaning |
|---|---|
| `layout` | Master layout name (`layouts.md`). Case-insensitive, trimmed. |
| `title` | Headline: the slide's key message. |
| `subtitle` | Placeholder idx 2 (title slides) or idx 14 (sub-headline, or the category label on *Headline + Categorie*). |
| `content` | A list of **columns**. They fill the layout's content placeholders left to right, or the free content area (split evenly) on layouts without placeholders. A plain list of strings is one column of bullets. |
| `ph` | `{"<idx>": text or bullets}`: writes to one placeholder, for example *Reference* idx 13 (challenge) and idx 11 (quote). |
| `sidebar_text` | White intro text on the blue bar of the *Side Bar* layouts. |
| `notes` | Speaker notes. Notes for photographs and icons are added automatically. |

### Column (block) types

| Block | Result |
|---|---|
| `["a", "b", ["sub-bullet"]]` or `{"bullets": [...]}` | Bullets. A nested list is one level deeper; `{"text": "…", "level": 1}` sets a level. |
| `{"table": {"header": [...], "rows": [[...]], "col_widths": [2,1,1], "font_size": 12}}` | Brand table: blue header with white text, white body, thin grey row separators, no grid. |
| `{"chart": {"type": "column", "categories": [...], "series": [{"name": "...", "values": [...], "highlight": true}]}}` | 2D chart. Types: `column`, `bar`, `stacked`, `line`, `doughnut`, `pie`. Highlighted series blue (`highlight: 2` light blue), the rest in the recessed greys of `brand-tokens.json` (C17). No gridlines, value axis hidden, values labelled. Options: `number_format`, `labels: false`, `hide_value_axis: false`, `point_colors` (doughnut, pie). |
| `{"chart": {"type": "kpi", "value": 45, "label": "45%", "color": "00AAE1"}}` | KPI donut as in the template's examples: the value in colour on the light grey track #EDF1F2 (chart tracks only, C12), the number in the centre. |
| `{"image": {"path": ".ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/keyvisual/keyvisual-atm-aircraft-clouds-wide.jpg", "alt": "Aircraft above the clouds"}}` | Picture cropped to fill the box. Key visuals and mood images only (Pillow needed). |
| `{"photo_request": "controller working position"}` | Warm-grey placeholder plus the speaker note "Request real photo … Frequentis Photo Stock (GCM)". Use it for every product, system, customer-site or people photograph. |
| `{"icons": ["Analysis", "Planning"]}` | Blue icon-placeholder squares with descriptors, plus the speaker note "Insert icon from Frequentis Icon Stock: …". |

**Map pins.** A slide on `World Map`, `Map`, `World Map | Americas`, `1_MAP APAC` or `World Map | EMEA` takes `"pins": [{"lat": 48.21, "lon": 16.37, "label": "Vienna"}]`: a light blue marker at that place and the label on a white chip. The maps are a Robinson projection, calibrated on the layouts' country shapes (`map_point()` in `frq_pptx.py`): within about 0.02 in on average, 0.07 in at worst (South America). A place outside the EMEA map is refused; use `World Map`. The Europe, Germany and UK layouts are not calibrated: place markers there by hand.

For anything the builder does not cover (process chevrons, timelines, org charts, maps), build the slide on *Headline (standard)* (a map on its map layout), then add shapes with python-pptx as below, after looking at the matching example in `.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/examples/` (for example `33-phases-chevrons.jpg`, `38-history-timeline.jpg`, `32-org-chart.jpg`, `42-map-highlight-region.jpg`).

## Manual python-pptx recipes

Run them with the venv Python, in a script file you show the person first. The builder is loaded by path, so nothing is imported from the repo:

```python
import importlib.util
spec = importlib.util.spec_from_file_location("frq_pptx", ".agents/skills/ai-sdlc-frq-brandbook/scripts/frq_pptx.py")
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation("docs/remote-towers.pptx")          # a deck the builder wrote
slide = prs.slides.add_slide(F.find_layout(prs, "Headline (standard)"))
slide.shapes.title.text_frame.text = "Delivery runs in five phases"

# A flat filled box, no outline or shadow: the Frequentis square look
box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.47), Inches(1.0), Inches(1.7), Inches(0.5))
box.fill.solid(); box.fill.fore_color.rgb = F.rgb(F.BLUE); F.flat(box)
box.text_frame.text = "Phase 1"; F.style_run(box.text_frame.paragraphs[0].runs[0], 12, "FFFFFF")

# Process chevrons: the current phase light blue, the others grey
for i, name in enumerate(["Analysis", "Design", "Build", "Test", "Operate"]):
    c = slide.shapes.add_shape(MSO_SHAPE.CHEVRON, Inches(0.47 + i * 1.8), Inches(1.2), Inches(1.75), Inches(0.5))
    c.fill.solid(); c.fill.fore_color.rgb = F.rgb(F.LIGHT_BLUE if i == 1 else F.WARM_GREY); F.flat(c)

# Connector or timeline axis: one line weight throughout, no shadow
ln = slide.shapes.add_connector(1, Inches(0.47), Inches(3), Inches(9.53), Inches(3))
ln.line.color.rgb = F.rgb(F.BLUE); ln.line.width = Pt(1.5); ln.shadow.inherit = False

prs.save("docs/remote-towers-v2.pptx")                  # always a new file
```

Move the new slide before the *Closing Slide* if needed, and re-run the check. Content-area limits for hand-placed shapes (`brand-tokens.json`, `pptx.content_area_in`): left 0.47 in, right 9.53 in, top 0.83 in (1.02 in with a sub-headline), bottom 5.07 in (C18). Never go below 5.07 in: the footer and the logo sit there.

## Apply mode: fixing an existing deck

The person's file is never changed: every fix goes into a new file, `<name>-frq.pptx`.

- **Not on the Frequentis master** (`template.not-company`, `layout.not-company`): rebuild it from a spec on the slim template (the full master if it needs a *full only* layout), carrying over the text and data rather than restyling the old shapes.
- **On the master**: fix a copy. `frq_pptx.py footer IN.pptx OUT.pptx --classification "<class>" --title … --presenter … --year …` sets the footer into a new file.
- **Fonts and italics**: for every run, `font.name = "Arial"` and `font.italic = False`. Keep sizes; if the slide is overcrowded, split it.
- **Colours**: map each off-palette fill to the nearest role: key to blue, secondary to light blue, supporting to greys. Green, orange and red only when they mean status.
- **Effects**: `F.flat(shape)` removes outlines and shadows. Replace rounded rectangles with rectangles: re-create the shape (`auto_shape_type` is read-only).
- **"Thank you" slide**: delete it and add *Closing Slide*.
- After the fixes: `frq_pptx.py audit <name>-frq.pptx` (it runs `scripts/check_brand.py`) and report what changed and what is left for a person.
