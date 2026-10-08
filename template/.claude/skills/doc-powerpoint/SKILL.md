---
name: doc-powerpoint
description: Create, read and edit PowerPoint decks (.pptx) with python-pptx — title and section slides, bullets, tables, images and speaker notes, on the default layouts or a provided template. Use whenever someone says "turn this into slides", "make a deck", "make a PowerPoint", "build the sprint review slides", "what's in this presentation", "pull the speaker notes out", or names a .pptx file — for example a PI Planning summary, an iteration review or a status deck.
license: MIT
metadata:
  status: "approved"
  classification: "internal"
  ai-trust: "working"
  owner: "Architect"
---

# doc-powerpoint

Work with `.pptx` files by writing small Python snippets that use **python-pptx** (import name `pptx`), run from the terminal with `python - <<'EOF' ... EOF` so no script file is left behind. A human reviews every deck before it is shown.

## 1. Get the library (ask first)

1. Check: `python3 -c "import pptx"` and, if that fails, `~/.ai-sdlc/venv/bin/python -c "import pptx"`. Use whichever Python works.
2. If neither works, **ask the person** before installing anything. With their yes:
   `python3 -m venv ~/.ai-sdlc/venv && ~/.ai-sdlc/venv/bin/pip install python-pptx`
   The venv lives in the home folder, outside the repo, so nothing reaches git. Never use `pip install --user` or `sudo pip` (Ubuntu blocks them, PEP 668).
3. If `python3 -m venv` fails ("ensurepip is not available"), stop and say: "Please ask IT to install the `python3-venv` package on this VM." If pip cannot reach the package index, say they need the company's pip proxy/index settings from IT. Never install system packages yourself.

## 2. Output rules

- Write where the person asks; default to `docs/` (or the current folder) and say the full path.
- Never overwrite an existing file: ask, or write `<name>-v2.pptx`. Check with `os.path.exists` before saving.
- Only write the output file. Read inputs and templates, never modify them in place.
- Finish with a short summary: path, one line per slide (number, title), and which slides have notes.

## 3. Plan, then create

First turn the person's material into an outline and show it: one line per slide, a title, at most ~6 bullets per slide, and the speaker notes. Build the deck once they agree.

```python
from pptx import Presentation
from pptx.util import Inches, Pt

prs = Presentation()                   # or Presentation("team-template.pptx") for its theme and layouts
layouts = {l.name: l for l in prs.slide_layouts}
print(list(layouts))                   # a template may name its layouts differently

def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text

s = prs.slides.add_slide(layouts["Title Slide"])
s.shapes.title.text = "Iteration 4 Review"
s.placeholders[1].text = "Team Blue — 8 October"
notes(s, "Welcome; agenda in one sentence.")

s = prs.slides.add_slide(layouts["Section Header"])
s.shapes.title.text = "What we delivered"

s = prs.slides.add_slide(layouts["Title and Content"])
s.shapes.title.text = "Highlights"
body = s.placeholders[1].text_frame
body.text = "Checkout flow live behind a flag"          # first bullet
for text, level in [("Error rate under 0.1%", 1), ("Search latency halved", 0)]:
    p = body.add_paragraph(); p.text = text; p.level = level
notes(s, "Mention the flag rollout plan.")

s = prs.slides.add_slide(layouts["Title Only"])
s.shapes.title.text = "Objectives status"
rows = [("Objective", "Status"), ("Checkout", "Done"), ("Search", "At risk")]
tbl = s.shapes.add_table(len(rows), 2, Inches(0.5), Inches(1.5), Inches(9), Inches(0.4) * len(rows)).table
for r, row in enumerate(rows):
    for c, value in enumerate(row):
        tbl.cell(r, c).text = value
# s.shapes.add_picture("burnup.png", Inches(1), Inches(1.5), width=Inches(8))
prs.save(out_path)
```

The default layouts are `Title Slide`, `Title and Content`, `Section Header`, `Two Content`, `Comparison`, `Title Only`, `Blank`, `Content with Caption`, `Picture with Caption`. In a template, pick the closest by name and check which placeholders it has: `[(p.placeholder_format.idx, p.name) for p in layout.placeholders]`. Default slides are 10 × 7.5 inches; read `prs.slide_width` / `prs.slide_height` before placing shapes on a template. Font size, if needed: `run.font.size = Pt(18)` on `p.runs`.

## 4. Read and extract

```python
from pptx import Presentation
prs = Presentation(path)
for n, slide in enumerate(prs.slides, start=1):
    print(f"--- Slide {n}")
    for shape in slide.shapes:
        if shape.has_text_frame and shape.text_frame.text.strip():
            print(shape.text_frame.text)
        if shape.has_table:
            print([[c.text for c in row.cells] for row in shape.table.rows])
    if slide.has_notes_slide:
        print("Notes:", slide.notes_slide.notes_text_frame.text)
```

Text inside grouped shapes sits in `shape.shapes` when `shape.shape_type == MSO_SHAPE_TYPE.GROUP` (`from pptx.enum.shapes import MSO_SHAPE_TYPE`).

## 5. Edit text on existing slides

Save to a new file (`<name>-v2.pptx`) unless the person says otherwise. Replace inside each run (`for p in shape.text_frame.paragraphs: for r in p.runs: r.text = r.text.replace(old, new)`) so formatting survives; do the same in table cells and in notes. If the text is split across runs, set the joined text on the first run and empty the others, and say that paragraph took the first run's formatting. Add new slides with `prs.slides.add_slide(...)` as in step 3 (they go at the end). python-pptx has no supported call to delete or reorder slides; ask the person to do that in PowerPoint.

## 6. Check before handing over

Re-open the saved file with `Presentation(out_path)`, print each slide's title and notes, and show that summary. python-pptx cannot render slides; ask the person to look at the deck for overflowing text.
