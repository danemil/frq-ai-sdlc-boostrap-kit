#!/usr/bin/env python3
"""The company brand skill (frq-brandbook): its files, its bundled assets, its placement,
and scripts/check_brand.py against a golden off-brand deck and decks built from the
bundled template.

The golden deck (fixtures/frq-brandbook/offbrand-test.pptx) comes from the earlier
internal brand skill's test set: six slides seeded with known violations. The on-brand
decks are built here with zipfile from the template the skill ships, so no python-pptx
is needed (the CI has none); the new_deck.py test runs only where python-pptx is installed.
"""
import ast
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import helpers
from personal import packs, paths

KIT = helpers.KIT
SKILL = KIT / packs.SKILLS_REL / "frq-brandbook"
CHECK = SKILL / "scripts/check_brand.py"
NEW_DECK = SKILL / "scripts/new_deck.py"
TEMPLATE = SKILL / "assets/templates/frq-template-slim-core.pptx"
TOKENS = SKILL / "brand-tokens.json"
GOLDEN = Path(__file__).resolve().parent / "fixtures/frq-brandbook/offbrand-test.pptx"
PLACED = ".agents/skills/ai-sdlc-frq-brandbook"
BUDGET = 2_500_000                     # bytes for the whole skill folder (~2 MB of assets)

NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_SLIDE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
REL_LAYOUT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout"
REL_CHART = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart"
CT_SLIDE = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
CT_CHART = "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"


def png_alpha(path):
    """(width, height, colour type, [alpha rows]) of an 8-bit RGBA, non-interlaced PNG (stdlib only)."""
    import struct
    import zlib
    b = Path(path).read_bytes()
    i, idat, w, h, ctype = 8, b"", 0, 0, None
    while i < len(b):
        n, typ = struct.unpack(">I4s", b[i:i + 8])
        data = b[i + 8:i + 8 + n]
        i += 12 + n
        if typ == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", data[:10])
            if (depth, ctype, data[12]) != (8, 6, 0):
                return w, h, (depth, ctype, data[12]), []
        elif typ == b"IDAT":
            idat += data
    raw, bpp = zlib.decompress(idat), 4
    stride, prev, rows = w * bpp, bytearray(w * bpp), []
    for y in range(h):
        f, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            up, c = prev[x], (prev[x - bpp] if x >= bpp else 0)
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + up) & 255
            elif f == 3:
                line[x] = (line[x] + (a + up) // 2) & 255
            elif f == 4:
                p_ = a + up - c
                pa, pb, pc = abs(p_ - a), abs(p_ - up), abs(p_ - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else up if pb <= pc else c)) & 255
        rows.append(line[3::4])
        prev = line
    return w, h, (8, 6, 0), rows


def svg_box(path):
    head = Path(path).read_text(encoding="utf-8")[:400]
    vb = [float(x) for x in re.search(r'viewBox="([^"]+)"', head).group(1).split()]
    w, h = (float(re.search(rf'{k}="([\d.]+)"', head).group(1)) for k in ("width", "height"))
    return vb[2] / vb[3], w / h


def run_check(path, *args, python=None):
    """Run check_brand.py as a person would: (exit code, stdout, stderr)."""
    r = subprocess.run([python or sys.executable, "-I", str(CHECK), str(path), *args],
                       capture_output=True, text=True, check=False)
    return r.returncode, r.stdout, r.stderr


def findings(path, *args):
    code, out, err = run_check(path, "--json", *args)
    data = json.loads(out)
    return code, data["findings"]


def layout_file(template, name):
    """ppt/slideLayouts/slideLayoutN.xml of the layout called `name` in `template`."""
    with zipfile.ZipFile(template) as z:
        for n in z.namelist():
            if re.fullmatch(r"ppt/slideLayouts/slideLayout\d+\.xml", n):
                if f'<p:cSld name="{name}"' in z.read(n).decode("utf-8"):
                    return n
    raise KeyError(name)


def sp(ph_type=None, idx=None, text="", rpr="", sppr="", name="Shape"):
    """A shape: a placeholder when ph_type or idx is given, else a text box."""
    ph = ""
    if ph_type or idx is not None:
        attrs = (f' type="{ph_type}"' if ph_type else "") + (f' idx="{idx}"' if idx is not None else "")
        ph = f"<p:nvPr><p:ph{attrs}/></p:nvPr>"
    else:
        ph = "<p:nvPr/>"
    paras = "".join(f"<a:p><a:r>{rpr}<a:t>{line}</a:t></a:r></a:p>" for line in text.split("\n"))
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{abs(hash(name)) % 9000 + 10}" name="{name}"/>'
            f"<p:cNvSpPr/>{ph}</p:nvSpPr><p:spPr>{sppr}</p:spPr>"
            f"<p:txBody><a:bodyPr/><a:lstStyle/>{paras}</p:txBody></p:sp>")


def build_pptx(dest, slides, base=TEMPLATE):
    """Copy `base` and append slides: [(layout name, shapes xml, {chart part: xml})]."""
    with zipfile.ZipFile(base) as zin:
        parts = {n: zin.read(n) for n in zin.namelist()}
    ct = parts["[Content_Types].xml"].decode("utf-8")
    prels = parts["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    pres = parts["ppt/presentation.xml"].decode("utf-8")
    ids = []
    for i, (layout, shapes, charts) in enumerate(slides, start=1):
        rels = [f'<Relationship Id="rId1" Type="{REL_LAYOUT}" '
                f'Target="../slideLayouts/{Path(layout_file(base, layout)).name}"/>']
        for j, (chart, xml) in enumerate((charts or {}).items(), start=2):
            parts[f"ppt/charts/{chart}"] = xml.encode("utf-8")
            ct = ct.replace("</Types>", f'<Override PartName="/ppt/charts/{chart}" '
                                        f'ContentType="{CT_CHART}"/></Types>')
            rels.append(f'<Relationship Id="rId{j}" Type="{REL_CHART}" Target="../charts/{chart}"/>')
            shapes += (f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{900 + j}" name="Chart {j}"/>'
                       f"<p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr><p:xfrm/>"
                       f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart">'
                       f'<c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
                       f'r:id="rId{j}"/></a:graphicData></a:graphic></p:graphicFrame>')
        parts[f"ppt/slides/slide{i}.xml"] = (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:sld xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}"><p:cSld><p:spTree>'
            f'<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
            f"{shapes}</p:spTree></p:cSld></p:sld>").encode("utf-8")
        parts[f"ppt/slides/_rels/slide{i}.xml.rels"] = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(rels) + "</Relationships>").encode("utf-8")
        ct = ct.replace("</Types>", f'<Override PartName="/ppt/slides/slide{i}.xml" '
                                    f'ContentType="{CT_SLIDE}"/></Types>')
        rid = f"rIdTest{i}"
        prels = prels.replace("</Relationships>", f'<Relationship Id="{rid}" Type="{REL_SLIDE}" '
                                                  f'Target="slides/slide{i}.xml"/></Relationships>')
        ids.append(f'<p:sldId id="{300 + i}" r:id="{rid}"/>')
    lst = "<p:sldIdLst>" + "".join(ids) + "</p:sldIdLst>"
    if "<p:sldIdLst/>" in pres:
        pres = pres.replace("<p:sldIdLst/>", lst)
    elif "<p:sldIdLst>" in pres:
        pres = pres.replace("<p:sldIdLst>", "<p:sldIdLst>" + "".join(ids), 1)
    else:
        pres = re.sub(r"(</p:sldMasterIdLst>)", r"\1" + lst, pres, count=1)
    parts["[Content_Types].xml"] = ct.encode("utf-8")
    parts["ppt/_rels/presentation.xml.rels"] = prels.encode("utf-8")
    parts["ppt/presentation.xml"] = pres.encode("utf-8")
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in parts.items():
            z.writestr(n, data)
    return Path(dest)


def on_brand_slides():
    return [
        ("Standard TITLE", sp("title", None, "Remote digital towers") + sp("body", 2, "Ana Pop, 9 October 2026"), None),
        ("Sub-headline + field", sp("title", None, "Controllers see more with fewer screens")
         + sp("body", 14, "What changes for the tower team") + sp(None, 16, "One working position\nShared voice and data"), None),
        ("Closing Slide", "", None),
    ]


def minimal_docx(dest, body_runs, footer_text=None):
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    parts = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/xml"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        "word/document.xml": f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{w}"><w:body>'
        + "".join(f"<w:p><w:r><w:rPr>{rpr}</w:rPr><w:t>{t}</w:t></w:r></w:p>" for rpr, t in body_runs)
        + "</w:body></w:document>",
    }
    if footer_text:
        parts["word/footer1.xml"] = (f'<?xml version="1.0" encoding="UTF-8"?><w:ftr xmlns:w="{w}"><w:p><w:r>'
                                     f"<w:t>{footer_text}</w:t></w:r></w:p></w:ftr>")
    with zipfile.ZipFile(dest, "w") as z:
        for n, data in parts.items():
            z.writestr(n, data)
    return Path(dest)


def minimal_xlsx(dest, font="Calibri", rgb="FF000000", strings=("Budget",)):
    m = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    parts = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/xml"/></Types>',
        "xl/styles.xml": f'<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="{m}"><fonts count="1"><font>'
        f'<sz val="11"/><color rgb="{rgb}"/><name val="{font}"/></font></fonts></styleSheet>',
        "xl/sharedStrings.xml": f'<?xml version="1.0" encoding="UTF-8"?><sst xmlns="{m}">'
        + "".join(f"<si><t>{s}</t></si>" for s in strings) + "</sst>",
        "xl/worksheets/sheet1.xml": f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="{m}"><sheetData>'
        '<row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>',
    }
    with zipfile.ZipFile(dest, "w") as z:
        for n, data in parts.items():
            z.writestr(n, data)
    return Path(dest)


def rules(found, severity=None, scope=None, location=None):
    return {f["rule"] for f in found
            if (severity is None or f["severity"] == severity)
            and (scope is None or f["scope"] == scope)
            and (location is None or f["location"] == location)}


class TestSkillFiles(unittest.TestCase):
    def test_frontmatter_and_triggers(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: frq-brandbook\n"))
        desc = re.search(r"(?m)^description: (.+)$", text).group(1)
        for word in ("Frequentis", "on-brand", "slides", "logo", "colours", "template", "check"):
            self.assertIn(word, desc)
        self.assertLessEqual(len(desc), 1024)
        self.assertLess(len(text.splitlines()), 220, "keep SKILL.md lean; move depth to references/")

    def test_quick_reference_matches_the_tokens(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        tokens = json.loads(TOKENS.read_text(encoding="utf-8"))
        for c in tokens["colours"]["primary"] + tokens["colours"]["accent"]:
            self.assertIn(c["hex"], text, c["name"])
        for c in tokens["colours"]["primary"]:
            if "web_hex" in c:
                self.assertIn(c["web_hex"], text, c["name"])
        for cls in tokens["classification"]:
            self.assertIn(cls, text)

    def test_the_expected_files_are_there(self):
        for rel in ("SKILL.md", "PROVENANCE.md", "brand-tokens.json", "scripts/check_brand.py",
                    "scripts/new_deck.py", "assets/manifest.json",
                    "assets/templates/frq-template-slim-core.pptx",
                    "references/brand-rules.md", "references/building-decks.md",
                    "references/documents.md", "references/writing-style.md", "references/assets.md"):
            self.assertTrue((SKILL / rel).is_file(), rel)

    def test_the_skill_points_to_the_doc_skills_by_their_placed_names(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for skill in ("doc-powerpoint", "doc-word", "doc-excel", "doc-pdf", "visual-explainers",
                      "drawio", "likec4-dsl"):
            self.assertIn(f"`{packs.PREFIX}{skill}`", text)

    def test_every_file_of_the_skill_is_tracked_by_git(self):
        """An ignore rule (template/.gitignore has *.pptx) must not keep a skill file out of a
        clone; a dirty worktree would hide it, so ask git, not the disk."""
        r = subprocess.run(["git", "ls-files", "--", str(SKILL.relative_to(KIT))], cwd=KIT,
                           capture_output=True, text=True, check=False)
        if r.returncode != 0 or not (KIT / ".git").exists():
            self.skipTest("not a git checkout")
        tracked = {Path(x).relative_to(SKILL.relative_to(KIT)).as_posix() for x in r.stdout.split("\n") if x}
        on_disk = {p.relative_to(SKILL).as_posix() for p in SKILL.rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts}
        self.assertEqual(sorted(on_disk - tracked), [])
        r = subprocess.run(["git", "check-ignore", "--no-index", "-q", str(TEMPLATE.relative_to(KIT))],
                           cwd=KIT, capture_output=True, check=False)
        self.assertEqual(r.returncode, 1, "the slim template is git-ignored")

    def test_logo_svgs_keep_their_proportions(self):
        for svg in sorted((SKILL / "assets/logo").glob("*.svg")):
            vb, wh = svg_box(svg)
            self.assertAlmostEqual(wh / vb, 1, delta=0.005, msg=svg.name)

    def test_logo_pngs_are_sharp_renders_of_the_svgs(self):
        for png in sorted((SKILL / "assets/logo").glob("*.png")):
            with self.subTest(png=png.name):
                w, h, mode, rows = png_alpha(png)
                self.assertEqual(mode, (8, 6, 0), "8-bit RGBA, not interlaced")
                vb, _ = svg_box(png.with_suffix(".svg"))
                self.assertAlmostEqual((w / h) / vb, 1, delta=0.006)     # same geometry as the SVG
                ink = [v for r in rows for v in r if v > 10]
                soft = sum(1 for v in ink if v < 245) / len(ink)
                self.assertLess(soft, 0.3, "soft edges: re-render the PNG from the SVG")

    def test_contrast_advice_holds(self):
        def lum(h):
            c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
            return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

        def ratio(a, b):
            hi, lo = sorted((lum(a), lum(b)), reverse=True)
            return (hi + 0.05) / (lo + 0.05)
        self.assertLess(ratio("#FFFFFF", "#00AAE1"), 3)          # fails even for large text
        self.assertGreaterEqual(ratio("#333333", "#00AAE1"), 4.5)
        self.assertGreaterEqual(ratio("#004182", "#00AAE1"), 3)
        texts = [(SKILL / f).read_text(encoding="utf-8") for f in
                 ("SKILL.md", "brand-tokens.json", "references/brand-rules.md",
                  "references/documents.md", "references/building-decks.md")]
        for text in texts:
            for line in text.splitlines():
                if "white" in line.lower():
                    self.assertNotRegex(line, r"(?i)(18 ?pt|large text)[^\n]{0,30}(only|\+)", line)

    def test_size_budget(self):
        total = sum(p.stat().st_size for p in SKILL.rglob("*") if p.is_file())
        self.assertLessEqual(total, BUDGET, f"{total} bytes")

    def test_manifest_lists_every_asset_with_its_size(self):
        man = json.loads((SKILL / "assets/manifest.json").read_text(encoding="utf-8"))
        on_disk = {p.relative_to(SKILL).as_posix(): p.stat().st_size
                   for p in (SKILL / "assets").rglob("*") if p.is_file() and p.name != "manifest.json"}
        listed = {a["file"]: a for a in man["assets"]}
        self.assertEqual(sorted(listed), sorted(on_disk))
        for rel, a in listed.items():
            self.assertEqual(a["bytes"], on_disk[rel], rel)
            self.assertEqual(a["sha256"], hashlib.sha256((SKILL / rel).read_bytes()).hexdigest(), rel)
            for key in ("file", "type", "variant", "bytes", "use"):
                self.assertIn(key, a, rel)

    def test_nothing_with_unknown_rights_is_bundled(self):
        for p in SKILL.rglob("*"):
            rel = p.relative_to(SKILL).as_posix().lower()
            self.assertNotRegex(rel, r"\.(ttf|otf|woff2?|eot)$", "never bundle font files")
            self.assertNotRegex(rel, r"(^|/)photo|portrait|sesar|fabec|screenshot|stock", rel)

    def test_the_template_is_slim_and_carries_no_personal_metadata(self):
        with zipfile.ZipFile(TEMPLATE) as z:
            names = z.namelist()
            self.assertFalse([n for n in names if n.startswith("ppt/slides/")], "no sample slides")
            layouts = [n for n in names if re.fullmatch(r"ppt/slideLayouts/slideLayout\d+\.xml", n)]
            self.assertEqual(len(layouts), 25)
            for gone in ("ppt/commentAuthors.xml", "docProps/custom.xml", "docProps/thumbnail.jpeg"):
                self.assertNotIn(gone, names)
            self.assertFalse([n for n in names if n.startswith("customXml/")])
            core = z.read("docProps/core.xml").decode("utf-8")
            self.assertIn("<dc:creator></dc:creator>", core)
            for n in names:
                if n.endswith((".xml", ".rels")):
                    self.assertNotIn("@", z.read(n).decode("utf-8").replace("@ ", ""), n)

    def test_provenance_and_name_screen(self):
        prov = (SKILL / "PROVENANCE.md").read_text(encoding="utf-8")
        for topic in ("Brand Guidelines Q4/2025", "shape for shape", "another company's brand skill",
                      "Group Communications", "Icon Stock", "C1", "C2", "C6"):
            self.assertIn(topic, prov)
        # Built from pieces, so this file does not match its own screen.
        words = ["/" + "Users/", "~" + "/work", "emi" + "dan", "Publi" + "cis", "Sap" + "ient",
                 "ps-" + "brandbook", "NOTES" + "/"]
        banned = re.compile("|".join(re.escape(w) for w in words), re.I)
        files = [p for p in SKILL.rglob("*") if p.is_file()] + [Path(__file__)]
        for p in files:
            try:
                text = p.read_bytes().decode("utf-8")
            except UnicodeDecodeError:
                continue
            with self.subTest(path=p.name):
                self.assertIsNone(banned.search(text))

    def test_tokens_are_consistent(self):
        tokens = json.loads(TOKENS.read_text(encoding="utf-8"))
        hexes = [c["hex"] for group in ("primary", "accent", "legend_only")
                 for c in tokens["colours"][group]]
        self.assertEqual(len(hexes), len(set(hexes)))
        for h in hexes:
            self.assertRegex(h, r"^#[0-9A-F]{6}$")
        for c in tokens["colours"]["primary"] + tokens["colours"]["accent"]:
            self.assertEqual("#%02X%02X%02X" % tuple(c["rgb"]), c["hex"], c["name"])
        self.assertEqual(tokens["fonts"]["office"]["family"], "Arial")
        for bu in tokens["business_units"]:
            self.assertTrue((SKILL / bu["key_visual"]).is_file(), bu["id"])


class TestCheckBrandScript(unittest.TestCase):
    def test_stdlib_only_and_python_3_9(self):
        src = CHECK.read_text(encoding="utf-8")
        tree = ast.parse(src, feature_version=(3, 9))
        allowed = {"__future__", "argparse", "datetime", "json", "re", "sys", "zipfile", "xml",
                   "pathlib", "posixpath", "os", "collections", "zlib"}
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                mods.add((node.module or "").split(".")[0])
        self.assertLessEqual(mods, allowed)

    def test_golden_off_brand_deck(self):
        code, found = findings(GOLDEN, "--year", "2026")
        self.assertEqual(code, 1)
        fail = {loc: rules(found, "FAIL", "slide", loc) for loc in
                ("slide 1", "slide 2", "slide 3", "slide 4", "slide 5", "slide 6")}
        self.assertLessEqual({"font.non-brand", "text.italic", "colour.off-palette", "text.frq"},
                             fail["slide 1"])
        self.assertLessEqual({"text.tagline", "text.italic", "colour.off-palette"}, fail["slide 2"])
        self.assertLessEqual({"font.non-brand", "colour.off-palette", "effect.shadow",
                              "gradient.non-brand"}, fail["slide 3"])
        self.assertLessEqual({"colour.off-palette", "text.italic"}, fail["slide 4"])
        self.assertLessEqual({"gradient.non-brand", "colour.off-palette"}, fail["slide 5"])
        self.assertIn("slide.thank-you", fail["slide 6"])
        warn = {loc: rules(found, "WARN", "slide", loc) for loc in fail}
        self.assertLessEqual({"text.align", "text.exclamation", "text.caps-name", "text.date"},
                             warn["slide 1"])
        self.assertLessEqual({"text.title-case", "text.us-spelling", "text.bold", "text.align",
                              "text.at-frequentis", "text.contraction", "text.number"},
                             warn["slide 2"])
        self.assertIn("shape.outline", warn["slide 3"])
        self.assertIn("text.us-spelling", warn["slide 4"])              # chart series "Defense"
        self.assertLessEqual({"slide.bullets", "text.title-case"}, warn["slide 5"])
        self.assertIn("footer.classification", rules(found, "FAIL", "file"))
        self.assertLessEqual({"theme.fonts", "theme.colours"}, rules(found, "WARN", "theme"))
        self.assertIn("text.ampersand", rules(found, "INFO", "slide", "slide 1"))

    def test_findings_carry_a_fix_and_the_text_report_is_readable(self):
        code, found = findings(GOLDEN)
        for f in found:
            self.assertTrue(f["message"] and f["fix"] and f["rule"], f)
            self.assertIn(f["severity"], ("FAIL", "WARN", "INFO"))
        code, out, _ = run_check(GOLDEN)
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)
        self.assertRegex(out, r"\d+ FAIL, \d+ WARN, \d+ INFO")

    def test_a_deck_built_from_the_template_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            deck = build_pptx(Path(tmp) / "ok.pptx", on_brand_slides())
            code, found = findings(deck, "--year", "2024")     # the template master says 2024
            self.assertEqual([f for f in found if f["severity"] != "INFO"], [])
            self.assertEqual(code, 0)
            # master and layout styles are reported, but only as INFO (conflicts C2, C3, C9)
            self.assertTrue([f for f in found if f["scope"] in ("master", "layout")])
            self.assertIn("footer.classification", rules(found, "INFO", "file"))
            code, found = findings(deck, "--year", "2026")
            self.assertEqual(code, 0)
            self.assertEqual({(f["severity"], f["rule"]) for f in found if f["severity"] != "INFO"},
                             {("WARN", "footer.year")})

    def test_slide_level_overrides_on_the_template_fail(self):
        bad = ('<a:rPr i="1"><a:solidFill><a:srgbClr val="FF00FF"/></a:solidFill>'
               '<a:latin typeface="Calibri"/></a:rPr>')
        shadow = ('<a:solidFill><a:srgbClr val="004182"/></a:solidFill>'
                  '<a:effectLst><a:outerShdw blurRad="1"><a:srgbClr val="000000"/></a:outerShdw></a:effectLst>')
        chart = ('<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
                 f'xmlns:a="{NS_A}"><c:chart><c:view3D/><c:plotArea><c:bar3DChart/></c:plotArea>'
                 "</c:chart></c:chartSpace>")
        with tempfile.TemporaryDirectory() as tmp:
            deck = build_pptx(Path(tmp) / "bad.pptx", [
                ("Headline (standard)", sp("title", None, "FRQ results", rpr=bad), None),
                ("Headline (standard)", sp(None, None, "Box", sppr=shadow), {"chart1.xml": chart}),
                ("Headline (standard)", sp("title", None, "Thank you"), None)])
            code, found = findings(deck, "--year", "2024")
            self.assertEqual(code, 1)
            self.assertLessEqual({"text.italic", "colour.off-palette", "font.non-brand"},
                                 rules(found, "FAIL", "slide", "slide 1"))
            self.assertIn("text.frq", rules(found, "WARN", "slide", "slide 1"))   # class: General
            self.assertLessEqual({"effect.shadow", "effect.3d"}, rules(found, "FAIL", "slide", "slide 2"))
            self.assertNotIn("colour.off-palette", rules(found, "FAIL", "slide", "slide 2"),
                             "a shadow's colour is the shadow finding, not a second one")
            self.assertIn("slide.thank-you", rules(found, "FAIL", "slide", "slide 3"))

    def test_theme_styles_that_python_pptx_shapes_inherit_are_seen(self):
        style = ('<p:style><a:lnRef idx="1"><a:schemeClr val="accent1"><a:shade val="50000"/></a:schemeClr></a:lnRef>'
                 '<a:fillRef idx="3"><a:schemeClr val="accent1"/></a:fillRef>'
                 '<a:effectRef idx="2"><a:schemeClr val="accent1"/></a:effectRef>'
                 '<a:fontRef idx="minor"><a:schemeClr val="lt1"/></a:fontRef></p:style>')
        default = ('<p:sp><p:nvSpPr><p:cNvPr id="40" name="Rectangle 1"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
                   '<p:spPr><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>' + style + '</p:sp>')
        clean = ('<p:sp><p:nvSpPr><p:cNvPr id="41" name="Rectangle 2"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
                 '<p:spPr><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="004182"/>'
                 '</a:solidFill><a:ln><a:noFill/></a:ln><a:effectLst/></p:spPr>' + style + '</p:sp>')
        with tempfile.TemporaryDirectory() as tmp:
            deck = build_pptx(Path(tmp) / "shapes.pptx", [("Headline (standard)", default, None),
                                                         ("Headline (standard)", clean, None)])
            code, found = findings(deck, "--year", "2024")
            self.assertEqual(code, 1)
            self.assertLessEqual({"effect.shadow", "gradient.non-brand"}, rules(found, "FAIL", "slide", "slide 1"))
            self.assertIn("shape.outline", rules(found, "WARN", "slide", "slide 1"))
            self.assertEqual(rules(found, None, "slide", "slide 2"), set())

    def test_tints_and_system_colours(self):
        tint = '<a:rPr><a:solidFill><a:schemeClr val="accent3"><a:lumMod val="60000"/></a:schemeClr></a:solidFill></a:rPr>'
        grey = '<a:rPr><a:solidFill><a:schemeClr val="bg2"><a:lumMod val="60000"/></a:schemeClr></a:solidFill></a:rPr>'
        sysc = '<a:rPr><a:solidFill><a:sysClr val="windowText" lastClr="000000"/></a:solidFill></a:rPr>'
        prst = '<a:rPr><a:solidFill><a:prstClr val="black"/></a:solidFill></a:rPr>'
        with tempfile.TemporaryDirectory() as tmp:
            deck = build_pptx(Path(tmp) / "tints.pptx", [
                ("Headline (standard)", sp(None, None, "Light blue tint", rpr=tint), None),
                ("Headline (standard)", sp(None, None, "Grey tint", rpr=grey), None),
                ("Headline (standard)", sp(None, None, "System black", rpr=sysc), None),
                ("Headline (standard)", sp(None, None, "Preset black", rpr=prst), None)])
            code, found = findings(deck, "--year", "2024")
            self.assertIn("colour.tint", rules(found, "WARN", "slide", "slide 1"))
            self.assertEqual(rules(found, None, "slide", "slide 2"), set())
            self.assertIn("colour.off-palette", rules(found, "FAIL", "slide", "slide 3"))
            self.assertIn("colour.off-palette", rules(found, "FAIL", "slide", "slide 4"))

    def test_name_and_tagline_severity_follow_the_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            internal = build_pptx(Path(tmp) / "internal.pptx", [   # the master says Frequentis General
                ("Headline (standard)", sp("title", None, "FRQ status for the team")
                 + sp(None, None, "FREQUENTIS COMSOFT GmbH supplies it.\nWe work for a safer world every day."), None),
                ("Headline (standard)", sp(None, None, "FREQUENTIS", name="Logo text"), None),
                ("Headline (standard)", sp(None, None, "For a safer world", name="Tagline"), None)])
            code, found = findings(internal, "--year", "2024")
            self.assertIn("text.frq", rules(found, "WARN", "slide", "slide 1"))
            self.assertNotIn("text.frq", rules(found, "FAIL"))
            self.assertNotIn("text.caps-name", rules(found, None, "slide", "slide 1"))
            self.assertIn("text.tagline", rules(found, "WARN", "slide", "slide 1"))
            self.assertIn("text.caps-name", rules(found, "WARN", "slide", "slide 2"))
            self.assertIn("text.tagline", rules(found, "FAIL", "slide", "slide 3"))
            public = build_pptx(Path(tmp) / "public.pptx", [
                ("Headline (standard)", sp("title", None, "FRQ results") + sp(None, None, "Frequentis Public"), None)])
            self.assertIn("text.frq", rules(findings(public, "--year", "2024")[1], "FAIL", "slide", "slide 1"))

    def test_a_questions_closing_slide_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            deck = build_pptx(Path(tmp) / "q.pptx", [("Headline (standard)", sp("title", None, "Questions?"), None)])
            self.assertIn("slide.thank-you", rules(findings(deck, "--year", "2024")[1], "FAIL", "slide", "slide 1"))

    def test_word_checks_used_styles_and_theme_fonts_only(self):
        w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        styles = (f'<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="{w}">'
                  '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:asciiTheme="minorHAnsi" w:hAnsiTheme="minorHAnsi"/>'
                  '</w:rPr></w:rPrDefault></w:docDefaults>'
                  '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/></w:rPr></w:style>'
                  '<w:style w:type="paragraph" w:styleId="Heading1"><w:basedOn w:val="Normal"/><w:rPr>'
                  '<w:rFonts w:asciiTheme="majorHAnsi" w:hAnsiTheme="majorHAnsi"/><w:color w:val="004182"/></w:rPr></w:style>'
                  '<w:style w:type="character" w:styleId="Code"><w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/>'
                  '<w:i/><w:color w:val="FF00FF"/></w:rPr></w:style></w:styles>')
        theme = ('<?xml version="1.0" encoding="UTF-8"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                 '<a:themeElements><a:clrScheme name="Office"><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
                 '<a:accent1><a:srgbClr val="4472C4"/></a:accent1></a:clrScheme><a:fontScheme name="Office">'
                 '<a:majorFont><a:latin typeface="Calibri Light"/></a:majorFont><a:minorFont><a:latin typeface="Arial"/></a:minorFont>'
                 '</a:fontScheme></a:themeElements></a:theme>')
        with tempfile.TemporaryDirectory() as tmp:
            path = minimal_docx(Path(tmp) / "doc.docx", [("", "Frequentis report")],
                                footer_text="Frequentis General | © Frequentis AG 2026")
            with zipfile.ZipFile(path, "a") as z:
                z.writestr("word/styles.xml", styles)
                z.writestr("word/theme/theme1.xml", theme)
            body = zipfile.ZipFile(path).read("word/document.xml").decode().replace(
                "<w:p><w:r>", '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r>', 1)
            parts = {n: zipfile.ZipFile(path).read(n) for n in zipfile.ZipFile(path).namelist()}
            parts["word/document.xml"] = body.encode()
            with zipfile.ZipFile(path, "w") as z:
                for n, d in parts.items():
                    z.writestr(n, d)
            code, found = findings(path, "--year", "2026")
            fonts = [f for f in found if f["rule"] == "font.non-brand"]
            self.assertTrue(fonts and "Calibri Light" in fonts[0]["message"], found)
            self.assertNotIn("Courier New", json.dumps(found))           # unused style: not reported
            self.assertNotIn("text.italic", rules(found))
            self.assertLessEqual(rules(found, None, "theme"), rules(found, "INFO", "theme"))

    def test_word_and_excel(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = minimal_docx(Path(tmp) / "bad.docx", [
                ('<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:i/><w:color w:val="FF0000"/>', "FRQ report")])
            code, found = findings(bad)
            self.assertEqual(code, 1)
            self.assertLessEqual({"font.non-brand", "text.italic", "colour.off-palette", "text.frq"},
                                 rules(found, "FAIL"))
            self.assertIn("footer.classification", rules(found, "FAIL", "file"))
            good = minimal_docx(Path(tmp) / "good.docx", [
                ('<w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:color w:val="004182"/>', "Frequentis report")],
                footer_text="Frequentis General | © Frequentis AG 2026")
            code, found = findings(good, "--year", "2026")
            self.assertEqual((code, rules(found, "FAIL")), (0, set()))
            xbad = minimal_xlsx(Path(tmp) / "bad.xlsx", strings=("FRQ budget",))
            code, found = findings(xbad)
            self.assertEqual(code, 1)
            self.assertIn("text.frq", rules(found, "FAIL"))
            self.assertIn("font.non-brand", rules(found, "WARN"))      # Excel default styles: WARN
            xgood = minimal_xlsx(Path(tmp) / "good.xlsx", font="Arial", rgb="FF004182",
                                 strings=("Budget", "Frequentis General"))
            self.assertEqual(findings(xgood)[0], 0)

    def test_errors_and_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "x.txt").write_text("hi")
            self.assertEqual(run_check(Path(tmp) / "x.txt")[0], 2)
            (Path(tmp) / "broken.pptx").write_bytes(b"not a zip")
            code, _, err = run_check(Path(tmp) / "broken.pptx")
            self.assertEqual(code, 2)
            self.assertIn("broken.pptx", err)
            self.assertEqual(run_check(Path(tmp) / "missing.pptx")[0], 2)

    def malformed(self, tmp, name, slide_bytes, compress=zipfile.ZIP_DEFLATED):
        """A copy of the golden deck whose slide1.xml is replaced by `slide_bytes`."""
        dest = Path(tmp) / name
        with zipfile.ZipFile(GOLDEN) as zin, zipfile.ZipFile(dest, "w", compress) as zout:
            for n in zin.namelist():
                zout.writestr(n, slide_bytes if n == "ppt/slides/slide1.xml" else zin.read(n))
        return dest

    def assert_refused(self, path, words):
        code, out, err = run_check(path)
        self.assertEqual(code, 2, out + err)
        self.assertNotIn("Traceback", err)
        self.assertRegex(err, words)

    def test_entity_expansion_is_refused_in_any_encoding(self):
        lol = ('<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "FRQ FRQ FRQ FRQ">'
               '<!ENTITY b "&a;&a;&a;&a;&a;&a;"><!ENTITY c "&b;&b;&b;&b;&b;&b;">]>'
               f'<p:sld xmlns:p="{NS_P}" xmlns:a="{NS_A}"><a:t>&c;</a:t></p:sld>')
        with tempfile.TemporaryDirectory() as tmp:
            self.assert_refused(self.malformed(tmp, "lol8.pptx", lol.encode("utf-8")), "DTD|entit")
            utf16 = lol.replace('version="1.0"', 'version="1.0" encoding="UTF-16"').encode("utf-16")
            self.assert_refused(self.malformed(tmp, "lol16.pptx", utf16), "UTF-8")
            nobom = lol.encode("utf-16-le")                        # no BOM: NUL bytes give it away
            self.assert_refused(self.malformed(tmp, "lol16le.pptx", nobom), "UTF-8")
            latin = ('<?xml version="1.0" encoding="ISO-8859-1"?>'
                     f'<p:sld xmlns:p="{NS_P}"/>').encode("latin-1")
            self.assert_refused(self.malformed(tmp, "latin.pptx", latin), "UTF-8")

    def test_a_corrupt_member_is_exit_2_not_a_brand_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = ("<a:t>" + "x" * 5000 + "</a:t>").encode()
            path = self.malformed(tmp, "crc.pptx", body)
            data = bytearray(path.read_bytes())
            with zipfile.ZipFile(path) as z:
                info = z.getinfo("ppt/slides/slide1.xml")
            start = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
            for k in range(start + 2, start + 12):
                data[k] ^= 0xFF
            path.write_bytes(bytes(data))
            self.assert_refused(path, "crc.pptx.*(damaged|corrupt|cannot be read)")

    def test_size_and_ratio_budgets(self):
        with tempfile.TemporaryDirectory() as tmp:
            bomb = (f'<p:sld xmlns:p="{NS_P}"><!--' + " " * 3_000_000 + "--></p:sld>").encode()
            self.assert_refused(self.malformed(tmp, "ratio.pptx", bomb), "compress")
            spec = importlib.util.spec_from_file_location("check_brand_mod", CHECK)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertLessEqual(mod.MAX_PART, 16 * 1024 * 1024)
            mod.MAX_PART = 2000                                        # a slide master is larger
            with self.assertRaisesRegex(mod.CheckError, "too large"):
                mod.check(GOLDEN)
            mod.MAX_PART, mod.MAX_TOTAL = 16 * 1024 * 1024, 20_000      # the whole file over budget
            with self.assertRaisesRegex(mod.CheckError, "budget"):
                mod.check(GOLDEN)
            mod.MAX_TOTAL, mod.MAX_SLIDES = 256 * 1024 * 1024, 3
            with self.assertRaisesRegex(mod.CheckError, "slides"):
                mod.check(GOLDEN)

    def test_an_unexpected_error_is_exit_2_with_a_plain_message(self):
        spec = importlib.util.spec_from_file_location("check_brand_mod2", CHECK)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        def boom(*_):
            raise ValueError("unexpected")
        mod.check_pptx = boom
        import contextlib
        import io
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(mod.main([str(GOLDEN)]), 2)
        self.assertIn("could not be checked", err.getvalue())

    @unittest.skipUnless(Path("/usr/bin/python3").is_file(), "no system python3")
    def test_runs_on_the_system_python_too(self):
        code, out, err = run_check(GOLDEN, "--json", python="/usr/bin/python3")
        self.assertEqual(code, 1, err)
        self.assertTrue(json.loads(out)["findings"])


@unittest.skipUnless(importlib.util.find_spec("pptx"), "python-pptx is not installed here")
class TestNewDeck(unittest.TestCase):
    def test_new_deck_from_an_outline_passes_the_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            outline = Path(tmp) / "outline.md"
            outline.write_text("# Remote digital towers\nAna Pop, 9 October 2026\n\n"
                               "## Controllers see more with fewer screens\n"
                               "> What changes for the tower team\n- One working position\n"
                               "  - Shared voice and data\n- Fewer handovers\n\n"
                               "## Next steps\n- Pilot in one tower\n", encoding="utf-8")
            out = Path(tmp) / "deck.pptx"
            r = subprocess.run([sys.executable, str(NEW_DECK), str(outline), str(out),
                                "--classification", "Frequentis General", "--year", "2026"],
                               capture_output=True, text=True, check=False)
            self.assertEqual(r.returncode, 0, r.stderr)
            from pptx import Presentation
            prs = Presentation(str(out))
            self.assertEqual([s.slide_layout.name for s in prs.slides],
                             ["Standard TITLE", "Sub-headline + field", "Headline + field", "Closing Slide"])
            code, found = findings(out, "--year", "2026")
            self.assertEqual([f for f in found if f["severity"] != "INFO"], [])
            self.assertEqual(code, 0)
            r = subprocess.run([sys.executable, str(NEW_DECK), str(outline), str(out),
                                "--classification", "Frequentis General"],
                               capture_output=True, text=True, check=False)
            self.assertNotEqual(r.returncode, 0, "never overwrites")

    def run_new_deck(self, tmp, text, *args):
        outline = Path(tmp) / "o.md"
        outline.write_text(text, encoding="utf-8")
        out = Path(tmp) / f"d{len(list(Path(tmp).iterdir()))}.pptx"
        r = subprocess.run([sys.executable, str(NEW_DECK), str(outline), str(out), *args],
                           capture_output=True, text=True, check=False)
        return r, out

    def test_the_classification_is_never_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            r, out = self.run_new_deck(tmp, "# Title\n\n## One\n- a\n")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("classification", r.stderr)
            self.assertFalse(out.exists())

    def test_numbered_lists_paragraphs_and_bold_are_kept(self):
        from pptx import Presentation
        with tempfile.TemporaryDirectory() as tmp:
            r, out = self.run_new_deck(tmp, "# Risks\n\n## Two risks need an owner\n"
                                       "1. **Alarm routing** is late\n2) Spare parts\n"
                                       "Both need a decision this sprint.\n\n## Divider only\n",
                                       "--classification", "Frequentis Confidential")
            self.assertEqual(r.returncode, 0, r.stderr)
            slides = list(Presentation(str(out)).slides)
            body = " / ".join(sh.text_frame.text for sh in slides[1].placeholders
                              if sh.placeholder_format.idx == 15)
            self.assertIn("Alarm routing is late", body)
            self.assertIn("Spare parts", body)
            self.assertIn("Both need a decision this sprint.", body)
            self.assertNotIn("**", body)
            self.assertEqual(slides[2].slide_layout.name, "Headline (standard)")

    def test_lines_it_cannot_place_are_reported_and_an_empty_slide_stops_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            r, out = self.run_new_deck(tmp, "# T\n\n## Costs\n| a | b |\n|---|---|\n",
                                       "--classification", "Frequentis General")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("| a | b |", r.stderr)
            self.assertFalse(out.exists())
            r, out = self.run_new_deck(tmp, "# T\n\n## Costs\n- one\n```\ncode\n```\n",
                                       "--classification", "Frequentis General")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("not placed", r.stderr)


class TestPlacement(unittest.TestCase):
    def test_setup_places_the_binary_assets_byte_identical_and_remove_takes_them_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = helpers.make_repo(Path(tmp).resolve() / "repo", {"README.md": "team\n"})
            before = helpers.snapshot(root)
            copy = helpers.copy_kit(root / "ai-sdlc-kit")
            kit = root / paths.KIT_REL
            helpers.cli(root, copy, "setup", "--protect-only")
            code, out = helpers.cli(root, kit, "setup", "--name", "Ana", "--roles", "po", "--lang", "en")
            self.assertEqual(code, 0, out)
            for rel in ("assets/templates/frq-template-slim-core.pptx",
                        "assets/logo/logo-frequentis-wordmark-blue.png",
                        "assets/logo/logo-frequentis-wordmark-blue.svg",
                        "assets/keyvisual/keyvisual-atm-aircraft.jpeg", "scripts/check_brand.py"):
                self.assertEqual((root / PLACED / rel).read_bytes(), (SKILL / rel).read_bytes(), rel)
            self.assertIn("name: ai-sdlc-frq-brandbook",
                          (root / PLACED / "SKILL.md").read_text(encoding="utf-8"))
            code, out = helpers.cli(root, kit, "check")
            self.assertNotIn(PLACED, out)
            # the placed checker finds its tokens next to it and runs from the placed folder
            r = subprocess.run([sys.executable, "-I", str(root / PLACED / "scripts/check_brand.py"),
                                str(GOLDEN), "--json"], capture_output=True, text=True, check=False)
            self.assertEqual(r.returncode, 1, r.stderr)
            code, out = helpers.cli(root, kit, "remove")
            self.assertEqual(code, 0, out)
            self.assertFalse((root / PLACED).exists())
            self.assertEqual(helpers.snapshot(root), before)


if __name__ == "__main__":
    unittest.main()
