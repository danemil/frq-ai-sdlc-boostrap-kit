---
name: doc-pdf
description: Work with PDF files using pypdf — extract text and tables, merge, split, rotate and extract pages, fill simple form fields — and create a PDF from Markdown, HTML or .docx with pandoc or LibreOffice when they are installed. Use whenever someone says "extract the tables from this PDF", "what does this PDF say", "merge these PDFs", "split out pages 3 to 5", "rotate this page", "fill in this PDF form", "save this as a PDF", or names a .pdf file.
license: MIT
metadata:
  status: "approved"
  classification: "internal"
  ai-trust: "working"
  owner: "Architect"
---

# doc-pdf

Work with `.pdf` files by writing small Python snippets that use **pypdf**, run from the terminal with `python - <<'EOF' ... EOF` so no script file is left behind. To create a PDF, use **pandoc** or **LibreOffice** if installed. A human reviews every result before it is shared.

**No OCR unless a tool is there.** If a page gives no text it is probably a scanned image. Offer OCR only when `command -v ocrmypdf` or `command -v tesseract` finds one; otherwise say plainly that the PDF has no text layer and this VM cannot read it.

## 1. Get the library (ask first)

1. Check: `python3 -c "import pypdf"` and, if that fails, `~/.ai-sdlc/venv/bin/python -c "import pypdf"`. Use whichever Python works.
2. If neither works, **ask the person** before installing anything. With their yes:
   `python3 -m venv ~/.ai-sdlc/venv && ~/.ai-sdlc/venv/bin/pip install pypdf`
   The venv lives in the home folder, outside the repo, so nothing reaches git. Never use `pip install --user` or `sudo pip` (Ubuntu blocks them, PEP 668).
3. If `python3 -m venv` fails ("ensurepip is not available"), stop and say: "Please ask IT to install the `python3-venv` package on this VM." If pip cannot reach the package index, say they need the company's pip proxy/index settings from IT. Never install system packages yourself.
4. External tools are optional: `command -v pandoc soffice libreoffice pdftotext`. Use what is there; never install them.

## 2. Output rules

- Write where the person asks; default to `docs/` (or the current folder) and say the full path.
- Never overwrite an existing file: ask, or write `<name>-v2.pdf`. Check with `os.path.exists` before writing.
- Only write the output file(s). Never modify an input PDF in place.
- Finish with a short summary: path, page count, and what was done.
- Encrypted PDF (`reader.is_encrypted`): ask the person for the password; never guess or try to break it.

## 3. Extract text and tables

```python
from pypdf import PdfReader
reader = PdfReader(path)
print(len(reader.pages), "pages")
for n, page in enumerate(reader.pages, start=1):
    print(f"--- Page {n}")
    print(page.extract_text())
```

**Tables**: PDFs store positioned text, not tables. Use `page.extract_text(extraction_mode="layout")`, which keeps column alignment, then split rows on runs of two or more spaces (`re.split(r"\s{2,}", line.strip())`) and show the result as a Markdown table for the person to check. `pdftotext -layout in.pdf -` (poppler) gives similar output if installed. For complex tables, offer to install `pdfplumber` (MIT) into the same venv — ask first. Always say that extracted tables need a human check against the original.

## 4. Merge, split, rotate, extract pages

```python
from pypdf import PdfReader, PdfWriter

writer = PdfWriter()                       # merge: whole files, in order
for f in ["a.pdf", "b.pdf"]:
    writer.append(f)
writer.write(out_path)

reader = PdfReader("in.pdf")               # extract pages 3-5 (1-based for the person)
writer = PdfWriter()
for i in range(2, 5):
    writer.add_page(reader.pages[i])
writer.write(out_path)

writer = PdfWriter(clone_from="in.pdf")    # rotate page 1 by 90° clockwise
writer.pages[0].rotate(90)
writer.write(out_path)
```

Split into single pages: one `PdfWriter` per page, named `<name>-p<N>.pdf`, in the folder the person chose. Speak page numbers 1-based; pypdf indexes from 0.

## 5. Fill form fields

```python
from pypdf import PdfReader, PdfWriter
reader = PdfReader(path)
print({k: v.get("/V") for k, v in (reader.get_fields() or {}).items()})  # names and current values
writer = PdfWriter(clone_from=reader)
for page in writer.pages:
    writer.update_page_form_field_values(page, {"Name": "A. Person", "Date": "2026-10-08"},
                                         auto_regenerate=False)
writer.set_need_appearances_writer(True)   # viewers redraw the filled fields
writer.write(out_path)
```

List the fields first and confirm the mapping with the person. Checkboxes take the value from their `/_States_` list (often `/Yes`). If `get_fields()` returns nothing, the form is not fillable (flat print); say so.

## 6. Create a PDF

Check which tools exist, then pick the first that works:

- **docx, pptx, xlsx, html → PDF with LibreOffice**: `soffice --headless --convert-to pdf --outdir <out_dir> <file>` (the output takes the input's name with `.pdf`; check it does not exist first).
- **Markdown → PDF with pandoc**: `pandoc in.md -o out.pdf` needs a PDF engine (LaTeX, `wkhtmltopdf` or `weasyprint`); if it reports a missing engine, go via docx: `pandoc in.md -o tmp.docx` in a temporary folder, then LibreOffice as above.
- **Neither installed**: say so, offer a `.docx` instead (doc-word skill), and suggest asking IT for LibreOffice.

## 7. Check before handing over

Re-open each output with `PdfReader(out_path)`, report the page count and the first line of text per page (or the filled field values), and show that summary.
