---
name: doc-word
description: Create, read and edit Word documents (.docx) with python-docx, and convert Markdown to and from .docx with pandoc. Use whenever someone says "make a Word document", "write this up as a .docx", "export this to Word", "fill in this Word template", "what does this .docx say", "pull the tables out of this Word file", or names a .docx file — for example an HLD, ADR, decision brief, release notes or a test report.
license: MIT
metadata:
  status: "approved"
  classification: "internal"
  ai-trust: "working"
  owner: "Architect"
---

# doc-word

Work with `.docx` files by writing small Python snippets that use **python-docx** (import name `docx`), run from the terminal with `python - <<'EOF' ... EOF` so no script file is left behind. Use **pandoc** for Markdown ↔ docx when it is installed. A human reviews every document before it is shared.

## 1. Get the library (ask first)

1. Check: `python3 -c "import docx"` and, if that fails, `~/.ai-sdlc/venv/bin/python -c "import docx"`. Use whichever Python works.
2. If neither works, **ask the person** before installing anything. With their yes:
   `python3 -m venv ~/.ai-sdlc/venv && ~/.ai-sdlc/venv/bin/pip install python-docx`
   The venv lives in the home folder, outside the repo, so nothing reaches git. Never use `pip install --user` or `sudo pip` (Ubuntu blocks them, PEP 668).
3. If `python3 -m venv` fails ("ensurepip is not available"), stop and say: "Please ask IT to install the `python3-venv` package on this VM." If pip cannot reach the package index, say they need the company's pip proxy/index settings from IT. Never install system packages yourself.
4. pandoc is optional: `command -v pandoc`. If it is missing, use python-docx only.

## 2. Output rules

- Write where the person asks; default to `docs/` (or the current folder) and say the full path.
- Never overwrite an existing file: ask, or write `<name>-v2.docx`. Check with `os.path.exists` before saving.
- Only write the output file. Read inputs, never modify them in place.
- Finish with a short summary: path, headings, number of tables/images, anything that needs a manual step (for example "update the table of contents in Word").
- **Company brand by default:** if `ai-sdlc-frq-brandbook` is installed, every new document follows its Word guidance (the official template for customer documents), fonts and colours, unless the person asks for a plain file.

## 3. Create a document

```python
from docx import Document
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

doc = Document()                      # or Document("team-template.docx") to inherit its styles
doc.add_heading("Payment Service — High-Level Design", level=0)   # level 0 = Title

def add_toc(doc, levels="1-3"):
    """A Word TOC field. Word fills it when the field is updated (F9, or on open — see below)."""
    run = doc.add_paragraph().add_run()
    for kind, text in (("begin", None), (None, f'TOC \\o "{levels}" \\h \\z \\u'),
                       ("separate", None), (None, None), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), kind)
        elif text:
            el = OxmlElement("w:instrText"); el.set(qn("xml:space"), "preserve"); el.text = text
        else:
            el = OxmlElement("w:t"); el.text = "Right-click and choose Update Field to build the contents."
        run._r.append(el)
    upd = OxmlElement("w:updateFields"); upd.set(qn("w:val"), "true")
    doc.settings.element.append(upd)  # Word offers to update fields when the file opens

add_toc(doc)
doc.add_page_break()
doc.add_heading("1. Context", level=1)
doc.add_paragraph("Why this design exists.")
doc.add_paragraph("First point", style="List Bullet")
doc.add_paragraph("First step", style="List Number")

rows = [("Component", "Owner"), ("API", "Team A"), ("DB", "Team B")]
table = doc.add_table(rows=len(rows), cols=len(rows[0]), style="Table Grid")
for r, row in enumerate(rows):
    for c, value in enumerate(row):
        table.cell(r, c).text = value
for cell in table.rows[0].cells:                 # bold header row
    for run in cell.paragraphs[0].runs:
        run.bold = True

# doc.add_picture("diagram.png", width=Inches(6))
section = doc.sections[0]
section.header.paragraphs[0].text = "Internal — draft"
section.footer.paragraphs[0].text = "Payment Service HLD v0.1"
doc.save(out_path)
```

From Markdown or an outline: parse `#` levels to `add_heading`, `-`/`*` to `List Bullet`, `1.` to `List Number`, `|` tables to `add_table`. If pandoc is present it is quicker and keeps more formatting: `pandoc in.md -o out.docx --toc` (add `--reference-doc=template.docx` to use the team's styles).

Built-in style names in the default template: `Title`, `Heading 1`–`Heading 9`, `List Bullet`, `List Number`, `Table Grid`, `Quote`. A custom template may lack some; check `[s.name for s in doc.styles]`.

## 4. Read and extract

```python
from docx import Document
doc = Document(path)
for block in doc.iter_inner_content():       # paragraphs and tables in document order (python-docx >= 1.1)
    if hasattr(block, "rows"):
        print([[c.text for c in row.cells] for row in block.rows])
    elif block.text.strip():
        print(f"[{block.style.name}] {block.text}")
```

On older python-docx use `doc.paragraphs` and `doc.tables` (not interleaved). Headers and footers: `doc.sections[i].header.paragraphs`. For a Markdown copy: `pandoc in.docx -t gfm -o out.md --extract-media=media`.

## 5. Edit an existing document

Save edits to a new file (`<name>-v2.docx`) unless the person says otherwise.

- **Find and replace, keeping formatting**: replace inside each run, so the run's bold/italic/font survive. Word often splits a word across runs; if the text is not found in a single run but is in `paragraph.text`, put the replaced paragraph text into the first run and empty the others (that paragraph keeps the first run's formatting — say so).
- Cover body paragraphs, every table cell (`for t in doc.tables: for row in t.rows: for cell in row.cells: cell.paragraphs`), and each section's header and footer.
- **Fill a template**: same replace for placeholders such as `{{PROJECT}}` or `<DATE>`; afterwards list any placeholder still present.
- **Add a section**: `doc.add_heading(...)` / `doc.add_paragraph(...)` append at the end. To insert after a given paragraph `p`, create the new one and move it: `new = doc.add_paragraph(text); p._p.addnext(new._p)`.

python-docx does not handle tracked changes or comments; if the file has them, say so and leave them alone.

## 6. Check before handing over

Re-open the saved file with `Document(out_path)` and print headings, table count and the first lines, then show that summary. The TOC is filled by Word when fields are updated; python-docx cannot render it — tell the person.
