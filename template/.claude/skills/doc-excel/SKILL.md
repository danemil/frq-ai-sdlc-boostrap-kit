---
name: doc-excel
description: Create, read and edit Excel workbooks (.xlsx) and CSV files with openpyxl — sheets, headers, formatting, formulas, number formats, column widths, freeze panes and simple charts. Use whenever someone says "export this to Excel", "make a spreadsheet", "put this in a .xlsx", "summarise this spreadsheet", "update the capacity sheet", "convert this CSV", or names a .xlsx or .csv file — for example a backlog or dependency export, a capacity table or a test matrix.
license: MIT
metadata:
  status: "approved"
  classification: "internal"
  ai-trust: "working"
  owner: "Architect"
---

# doc-excel

Work with `.xlsx` files by writing small Python snippets that use **openpyxl**, run from the terminal with `python - <<'EOF' ... EOF` so no script file is left behind. CSV uses the standard `csv` module. A human reviews every workbook before it is shared.

**Formulas, not pasted numbers.** Where a value is computed (totals, sums, percentages, lookups), write the Excel formula (`"=SUM(B2:B20)"`), never a number you worked out yourself. openpyxl stores formulas but does not calculate them, so always verify them (step 6).

## 1. Get the library (ask first)

1. Check: `python3 -c "import openpyxl"` and, if that fails, `~/.ai-sdlc/venv/bin/python -c "import openpyxl"`. Use whichever Python works.
2. If neither works, **ask the person** before installing anything. With their yes:
   `python3 -m venv ~/.ai-sdlc/venv && ~/.ai-sdlc/venv/bin/pip install openpyxl`
   The venv lives in the home folder, outside the repo, so nothing reaches git. Never use `pip install --user` or `sudo pip` (Ubuntu blocks them, PEP 668).
3. If `python3 -m venv` fails ("ensurepip is not available"), stop and say: "Please ask IT to install the `python3-venv` package on this VM." If pip cannot reach the package index, say they need the company's pip proxy/index settings from IT. Never install system packages yourself.

## 2. Output rules

- Write where the person asks; default to `docs/` (or the current folder) and say the full path.
- Never overwrite an existing file: ask, or write `<name>-v2.xlsx`. Check with `os.path.exists` before saving.
- Only write the output file. Read inputs, never modify them in place.
- Finish with a short summary: path, sheets, rows per sheet, formulas used, charts.
- **Company brand by default:** load the `ai-sdlc-frq-brandbook` skill. If it is in your skill list, it is installed. Read its files by exact path (`.agents/skills/ai-sdlc-frq-brandbook/…`). Never decide by glob or search: the folder is hidden from git, so search tools skip it. Every new workbook uses its fonts, colours and classification (`references/documents.md`), unless the person asks for a plain file.

## 3. Create a workbook

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import BarChart, Reference

wb = Workbook()
ws = wb.active
ws.title = "Capacity"
ws.append(["Team member", "Days available", "Focus factor", "Capacity"])
data = [("Ana", 9, 0.8), ("Ben", 10, 0.7), ("Chen", 8, 0.8)]
for i, (name, days, focus) in enumerate(data, start=2):
    ws.append([name, days, focus, f"=B{i}*C{i}"])          # formula per row
last = len(data) + 1
ws.append(["Total", f"=SUM(B2:B{last})", None, f"=SUM(D2:D{last})"])

for cell in ws[1]:                                          # header style
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="305496")
    cell.alignment = Alignment(horizontal="center")
for row in ws.iter_rows(min_row=2, min_col=3, max_col=3):
    row[0].number_format = "0%"
for row in ws.iter_rows(min_row=2, min_col=4, max_col=4):
    row[0].number_format = "0.0"
for col, width in {"A": 18, "B": 15, "C": 13, "D": 11}.items():
    ws.column_dimensions[col].width = width
ws.freeze_panes = "A2"                                      # keep the header visible
ws.auto_filter.ref = f"A1:D{last}"

chart = BarChart()
chart.title = "Capacity per person"
chart.y_axis.title = "Days"
chart.add_data(Reference(ws, min_col=4, min_row=1, max_row=last), titles_from_data=True)
chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=last))
ws.add_chart(chart, "F2")
wb.save(out_path)
```

More sheets: `wb.create_sheet("Backlog")`. Other charts: `LineChart`, `PieChart` from `openpyxl.chart`, used the same way. Common number formats: `"#,##0"`, `"#,##0.00"`, `"0%"`, `"yyyy-mm-dd"`. Dates: write `datetime.date` values, not strings.

## 4. Read and summarise

```python
from openpyxl import load_workbook
wb = load_workbook(path, read_only=True, data_only=True)    # data_only: last values Excel saved
for ws in wb.worksheets:
    rows = list(ws.iter_rows(values_only=True))
    print(ws.title, ws.max_row, "rows x", ws.max_column, "cols")
    print(rows[:5])                                         # header + first rows
```

Summarise from the rows (counts, totals, groups by a column) and say which sheet and range each figure came from. `data_only=True` gives `None` for formulas in a file that was never opened and saved in Excel; read without it to see the formulas themselves.

## 5. Edit, keeping formulas

- Open with `load_workbook(path)` — **not** `data_only=True`, which would replace every formula with its cached value when you save. For `.xlsm` add `keep_vba=True` and save as `.xlsm`.
- Change cells by address (`ws["B7"] = 12`, `ws["D9"] = "=SUM(D2:D8)"`). When you add rows, extend the ranges of the formulas that should include them, and report which formulas you changed.
- openpyxl does not keep everything: existing charts, images, pivot tables and some conditional formatting can be lost on save. If the workbook has any, warn the person first and always save to `<name>-v2.xlsx` so the original stays intact.

## 6. Verify formulas

1. Re-open the saved file with `load_workbook(out_path)` and list every formula (`cell.data_type == "f"`); check each range covers the rows it should and that no `#REF!` is present.
2. If LibreOffice is installed (`command -v soffice`), recalculate a copy in a temporary folder and read the values: `soffice --headless --convert-to csv --outdir "$(mktemp -d)" out.xlsx` (first sheet), then compare totals with the same sum computed in Python from the data. Report any mismatch.
3. Without LibreOffice, compute the expected totals in Python, show them next to the formulas, and tell the person Excel will calculate the values when they open the file.

## 7. CSV in and out

- Read: `csv.DictReader(open(path, newline="", encoding="utf-8-sig"))` (the `-sig` drops Excel's BOM). Detect `;` separators with `csv.Sniffer().sniff(sample)`.
- To Excel: `ws.append(row)` per CSV row; convert numeric strings to `int`/`float` so Excel can calculate with them.
- From Excel: write with `csv.writer(open(out, "w", newline="", encoding="utf-8-sig"))` so Excel opens accents correctly. CSV keeps values only: formulas, formatting and other sheets are not kept — say so.
