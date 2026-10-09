#!/usr/bin/env python3
"""Check a .pptx (and, more lightly, a .docx or .xlsx) against the Frequentis brand.

    python3 check_brand.py deck.pptx            # a Markdown table of findings
    python3 check_brand.py deck.pptx --json     # the same findings as JSON
    python3 check_brand.py deck.pptx --year 2026

Python 3.9+, standard library only (zipfile + xml.etree): no install, no venv. It reads
the file and never changes it. The palette, fonts and footer come from
../brand-tokens.json, next to this script, so a palette change is made in one place.

Severity: FAIL (breaks a brand rule), WARN (probably off-brand; a person decides),
INFO (for the record). Slide-level findings are what the deck's author set and can fix.
Master, layout and theme findings come from the template the deck was built on: they are
reported once, as INFO (theme mismatches as WARN), so an on-brand deck built from the
official template does not fail on the template's own quirks.

Exit code: 0 no FAIL, 1 at least one FAIL, 2 the file could not be read.
The checker flags evidence; a person reviews every finding before anything is changed.
"""
from __future__ import annotations

import argparse
import datetime
import json
import posixpath
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

TOKENS = Path(__file__).resolve().parent.parent / "brand-tokens.json"
MAX_PART = 64 * 1024 * 1024          # refuse a single XML part above 64 MB (zip bombs)
SEVERITIES = ("FAIL", "WARN", "INFO")

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
A, P, R, C, W, S = ("{%s}" % NS[k] for k in ("a", "p", "r", "c", "w", "s"))
REL = "{%s}Relationship" % NS["rel"]

# Theme colour names -> the slot that holds them, to read gradient stops given as schemeClr.
SCHEME_ALIAS = {"tx1": "dk1", "bg1": "lt1", "tx2": "dk2", "bg2": "lt2"}
EFFECTS = {"outerShdw": "shadow", "innerShdw": "inner shadow", "prstShdw": "preset shadow",
           "reflection": "reflection", "glow": "glow"}
COLOUR_MODS = {"lumMod", "lumOff", "tint", "shade"}

# rule: (proposed fix, source in the brand guidelines Q4/2025 or template)
RULES = {
    "colour.off-palette": ("Use a brand colour from brand-tokens.json (body text #333333, lead colour #004182).", "PDF p.7"),
    "colour.legend-only": ("Use business-unit colours in chart legends only.", "PDF p.7"),
    "font.non-brand": ("Use Arial (or the theme font) in Office files; remove the explicit typeface so the theme applies.", "PDF p.8"),
    "text.italic": ("Remove italics; use size or colour for emphasis.", "PDF p.8"),
    "effect.shadow": ("Remove the shadow, glow or reflection; shapes are flat.", "PDF p.17, p.29"),
    "effect.3d": ("Use a flat 2D shape or a 2D chart.", "PDF p.18, p.29"),
    "gradient.non-brand": ("Use only the blue #004182 to light blue #00AAE1 gradient, or a flat brand colour.", "PDF p.17"),
    "text.frq": ("Write 'Frequentis'; 'FRQ' is internal only.", "PDF p.25"),
    "text.caps-name": ("Write 'Frequentis' in sentence case; never retype the logo as text, use the logo file.", "PDF p.4, p.25"),
    "text.tagline": ("Use the logo-with-tagline file on title and closing slides; never type the tagline on its own.", "PDF p.5"),
    "slide.thank-you": ("Replace it with the template's 'Closing Slide' layout (globe, logo with tagline).", "PDF p.28; template slide 10"),
    "footer.classification": ("Set 'Frequentis Public', 'Frequentis General' or 'Frequentis Confidential' in the master footer.", "PDF p.26"),
    "footer.year": ("Set the current year in the master footer: '© Frequentis AG <year>'.", "PDF p.26, p.29"),
    "footer.copyright": ("Add '© Frequentis AG <year>' to the footer.", "PDF p.26"),
    "text.bold": ("Reduce bold; build hierarchy with size, not bold.", "PDF p.8, p.22"),
    "text.align": ("Left-align text; centred or right alignment is the exception.", "PDF p.22"),
    "shape.outline": ("Remove the outline from filled shapes.", "PDF p.17"),
    "text.title-case": ("Use sentence case for headlines.", "PDF p.21"),
    "text.us-spelling": ("Use British English spelling.", "PDF p.20-21"),
    "text.exclamation": ("Use exclamation marks sparingly and only singly.", "PDF p.22"),
    "text.ampersand": ("Write 'and' unless space forces '&'.", "PDF p.22"),
    "slide.bullets": ("Split the slide or cut the text; one key message per slide.", "PDF p.29; template slide 6"),
    "image.alt-text": ("Add alt text describing the picture.", "accessibility (WCAG 2.x)"),
    "theme.colours": ("Build from the Frequentis template so the theme colours are the brand palette.", "PDF p.7; template slide 14"),
    "theme.fonts": ("Build from the Frequentis template so the theme fonts are Arial.", "PDF p.8"),
    "file.empty": ("Add content, starting from the template's layouts.", "-"),
}


class CheckError(Exception):
    """The file cannot be checked (missing, not a zip, unsupported type)."""


# --- tokens -------------------------------------------------------------------------

def load_tokens(path=TOKENS) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    col = data["colours"]
    hexes = lambda items, key="hex": {c[key].lstrip("#").upper() for c in items if key in c}
    chk = data["checker"]
    return {
        "palette": hexes(col["primary"]) | hexes(col["primary"], "web_hex") | hexes(col["accent"]),
        "legend": hexes(col["legend_only"]),
        "gradient": {col["gradient"]["from"].lstrip("#").upper(), col["gradient"]["to"].lstrip("#").upper()},
        "classes": data["classification"],
        "fonts": set(chk["allowed_latin_typefaces"]),
        "us": {k.lower(): v for k, v in chk["us_spellings"].items()},
        "bold_share": float(chk["bold_share_warn"]),
        "max_bullets": int(chk["max_bullets_warn"]),
        "family": data["fonts"]["office"]["family"],
    }


# --- package helpers ----------------------------------------------------------------

class Package:
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_file():
            raise CheckError(f"{self.path}: no such file")
        try:
            self.zip = zipfile.ZipFile(self.path)
        except (zipfile.BadZipFile, OSError) as exc:
            raise CheckError(f"{self.path}: not an Office file ({exc})") from None
        self.names = set(self.zip.namelist())

    def xml(self, name):
        if name not in self.names:
            return None
        if self.zip.getinfo(name).file_size > MAX_PART:
            raise CheckError(f"{self.path}: part {name} is too large to check")
        data = self.zip.read(name)
        if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
            # OOXML never uses a DTD; refusing one blocks entity expansion (stdlib only, no defusedxml)
            raise CheckError(f"{self.path}: part {name} declares a DTD; refusing to parse it")
        try:
            return ET.fromstring(data)
        except ET.ParseError as exc:
            raise CheckError(f"{self.path}: part {name} is not valid XML ({exc})") from None

    def rels(self, part) -> dict:
        """{rId: (type tail, absolute target)} for a part."""
        folder, base = posixpath.split(part)
        root = self.xml(posixpath.join(folder, "_rels", base + ".rels"))
        out = {}
        for r in (root.iter(REL) if root is not None else []):
            target = r.get("Target", "")
            if r.get("TargetMode") != "External":
                target = posixpath.normpath(posixpath.join(folder, target)).lstrip("/")
            out[r.get("Id")] = (r.get("Type", "").rsplit("/", 1)[-1], target)
        return out


def parents_of(root) -> dict:
    return {child: parent for parent in root.iter() for child in parent}


def ancestors(el, parents):
    while el in parents:
        el = parents[el]
        yield el


def local(tag) -> str:
    return tag.rsplit("}", 1)[-1]


# --- findings -----------------------------------------------------------------------

class Report:
    def __init__(self):
        self.items = []

    def add(self, severity, scope, location, rule, message):
        fix, source = RULES[rule]
        self.items.append({"severity": severity, "scope": scope, "location": location,
                           "rule": rule, "message": message, "fix": fix, "source": source})


def listing(values, limit=6) -> str:
    values = sorted(values)
    more = f" (+{len(values) - limit} more)" if len(values) > limit else ""
    return ", ".join(values[:limit]) + more


# --- DrawingML (slides, layouts, masters, charts) ------------------------------------

def drawing_findings(root, tokens, theme) -> dict:
    """{rule: detail} of the visual rules in one DrawingML part (slide, layout, master, chart)."""
    parents = parents_of(root)
    off, legend, fonts, effects, threed, gradients = set(), set(), set(), set(), set(), set()
    italic = []
    for el in root.iter(A + "srgbClr"):
        if any(local(x.tag) in ("effectLst", "effectDag") for x in ancestors(el, parents)):
            continue                       # a shadow's colour belongs to the shadow finding
        val = (el.get("val") or "").upper()
        if val in tokens["legend"]:
            legend.add("#" + val)
        elif val and val not in tokens["palette"]:
            off.add("#" + val)
    for el in root.iter(A + "latin"):
        face = el.get("typeface", "")
        if face and face not in tokens["fonts"]:
            fonts.add(face)
    for el in root.iter(A + "rPr"):
        if el.get("i") in ("1", "true"):
            parent = parents.get(el)
            text = "".join(t.text or "" for t in parent.iter(A + "t")) if parent is not None else ""
            italic.append(text.strip()[:40])
    for el in root.iter(A + "effectLst"):
        effects |= {EFFECTS[local(x.tag)] for x in el if local(x.tag) in EFFECTS}
    for el in root.iter(A + "sp3d"):
        if el.attrib or len(el):
            threed.add("3D shape (bevel or extrusion)")
    for el in root.iter(A + "scene3d"):
        cam = el.find(A + "camera")
        if cam is not None and cam.get("prst", "orthographicFront") != "orthographicFront":
            threed.add("3D rotation")
    for el in root.iter():
        name = local(el.tag)
        if el.tag.startswith(C) and (name == "view3D" or name.endswith("3DChart")):
            threed.add("3D chart")
    for grad in root.iter(A + "gradFill"):
        stops, modded = [], False
        for gs in grad.iter(A + "gs"):
            for clr in gs:
                if local(clr.tag) == "srgbClr":
                    stops.append((clr.get("val") or "").upper())
                elif local(clr.tag) == "schemeClr":
                    v = clr.get("val", "")
                    stops.append(theme.get(SCHEME_ALIAS.get(v, v), v))
                modded |= any(local(m.tag) in COLOUR_MODS for m in clr)
        uniq = set(stops)
        if stops and (not uniq <= tokens["gradient"] or modded):
            gradients.add(" -> ".join(("#" + s if re.fullmatch(r"[0-9A-F]{6}", s) else s) for s in stops))
    out = {}
    if off:
        out["colour.off-palette"] = f"Colours outside the palette: {listing(off)}."
    if legend:
        out["colour.legend-only"] = f"Legend-only colours: {listing(legend)}."
    if fonts:
        out["font.non-brand"] = f"Fonts other than {tokens['family']}: {listing(fonts)}."
    if italic:
        sample = next((t for t in italic if t), "")
        out["text.italic"] = f"Italic text ({len(italic)} run(s))" + (f", e.g. '{sample}'." if sample else ".")
    if effects:
        out["effect.shadow"] = f"Effects: {listing(effects)}."
    if threed:
        out["effect.3d"] = f"3D: {listing(threed)}."
    if gradients:
        out["gradient.non-brand"] = f"Gradient(s) other than #004182 -> #00AAE1: {listing(gradients, 3)}."
    return out


def outline_count(root) -> int:
    n = 0
    for sppr in root.iter(P + "spPr"):
        filled = any(local(x.tag) in ("solidFill", "gradFill", "pattFill", "blipFill") for x in sppr)
        ln = sppr.find(A + "ln")
        if filled and ln is not None and ln.find(A + "noFill") is None and (
                ln.find(A + "solidFill") is not None or ln.find(A + "gradFill") is not None):
            n += 1
    return n


def shapes_text(root):
    """[(is_title, [(paragraph text, align, bold chars, chars)])] for the text shapes of a slide."""
    out = []
    for sp in root.iter(P + "sp"):
        body = sp.find(P + "txBody")
        if body is None:
            continue
        ph = sp.find(f"{P}nvSpPr/{P}nvPr/{P}ph")
        is_title = ph is not None and ph.get("type") in ("title", "ctrTitle")
        paras = []
        for para in body.iter(A + "p"):
            ppr = para.find(A + "pPr")
            align = ppr.get("algn") if ppr is not None else None
            text, bold = "", 0
            for run in para.iter(A + "r"):
                t = "".join(x.text or "" for x in run.iter(A + "t"))
                rpr = run.find(A + "rPr")
                if rpr is not None and rpr.get("b") in ("1", "true"):
                    bold += len(t.strip())
                text += t
            paras.append((text, align, bold, len(text.strip())))
        out.append((is_title, paras))
    return out


def chart_text(root) -> str:
    texts = [v.text or "" for tx in root.iter(C + "tx") for v in tx.iter(C + "v")]
    texts += [t.text or "" for t in root.iter(A + "t")]
    return "\n".join(texts)


def looks_title_case(headline) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z'’-]*", headline)[1:]
    words = [w for w in words if not w.isupper() and w.lower() not in ("frequentis",)]
    caps = [w for w in words if w[0].isupper()]
    return len(caps) >= 2 and len(caps) / max(len(words), 1) >= 0.6


def text_findings(report, scope, where, text, tokens):
    """The writing rules on visible text (any format)."""
    if re.search(r"\bFRQ\b", text):
        report.add("FAIL", scope, where, "text.frq", "'FRQ' in visible text.")
    if re.search(r"\bFREQUENTIS\b", text):
        report.add("FAIL", scope, where, "text.caps-name", "'FREQUENTIS' typed in capitals (a retyped logo?).")
    if re.search(r"for a safer world", text, re.I):
        report.add("FAIL", scope, where, "text.tagline", "The tagline is typed as text.")
    us = {w.lower() for w in re.findall(r"[A-Za-z]+", text) if w.lower() in tokens["us"]}
    if us:
        report.add("WARN", scope, where, "text.us-spelling",
                   "US spelling: " + listing(f"{w} -> {tokens['us'][w]}" for w in us) + ".")
    if "!!" in text or text.count("!") > 1:
        report.add("WARN", scope, where, "text.exclamation", f"{text.count('!')} exclamation mark(s).")
    if re.search(r"\s&\s", text):
        report.add("INFO", scope, where, "text.ampersand", "'&' in running text.")


def theme_colours(pkg, theme_part) -> dict:
    root = pkg.xml(theme_part) if theme_part else None
    out = {}
    scheme = root.find(f".//{A}clrScheme") if root is not None else None
    for slot in (scheme if scheme is not None else []):
        clr = slot.find(A + "srgbClr")
        sys_clr = slot.find(A + "sysClr")
        if clr is not None:
            out[local(slot.tag)] = (clr.get("val") or "").upper()
        elif sys_clr is not None:
            out[local(slot.tag)] = (sys_clr.get("lastClr") or "").upper()
    return out


def theme_findings(report, pkg, theme_part, tokens):
    root = pkg.xml(theme_part) if theme_part else None
    if root is None:
        return {}
    colours = theme_colours(pkg, theme_part)
    bad = {f"{k} #{v}" for k, v in colours.items()
           if k not in ("hlink", "folHlink") and v not in tokens["palette"]}
    if bad:
        report.add("WARN", "theme", theme_part, "theme.colours",
                   f"Theme colours outside the palette: {listing(bad)}.")
    faces = {f"{local(f.tag)}: {f.find(A + 'latin').get('typeface')}"
             for f in root.iter() if local(f.tag) in ("majorFont", "minorFont")
             and f.find(A + "latin") is not None
             and f.find(A + "latin").get("typeface") != tokens["family"]}
    if faces:
        report.add("WARN", "theme", theme_part, "theme.fonts", f"Theme fonts: {listing(faces)}.")
    return colours


def footer_findings(report, texts_slides, texts_template, tokens, year, kind):
    """Classification and copyright year, over the whole file. texts_*: [(where, text)]."""
    cls = re.compile("|".join(re.escape(c) for c in tokens["classes"]))
    on_slides = [(w, m.group(0)) for w, t in texts_slides for m in [cls.search(t)] if m]
    inherited = [(w, m.group(0)) for w, t in texts_template for m in [cls.search(t)] if m]
    if not on_slides and inherited:
        report.add("INFO", "file", inherited[0][0], "footer.classification",
                   f"Classification '{inherited[0][1]}' comes from the {inherited[0][0]}; confirm it is the right class.")
    elif not on_slides and not inherited:
        severity = "WARN" if kind == "xlsx" else "FAIL"
        report.add(severity, "file", "footer", "footer.classification", "No classification found.")
    years = [(w, int(m.group(1))) for w, t in texts_slides + texts_template
             for m in re.finditer(r"©\s*Frequentis AG\s*(\d{4})", t)]
    if years:
        old = sorted({f"{y} ({w})" for w, y in years if y != year})
        if old:
            report.add("WARN", "file", "footer", "footer.year",
                       f"Copyright year is not {year}: {listing(old, 3)}.")
    elif kind != "xlsx":
        report.add("WARN", "file", "footer", "footer.copyright", "No '© Frequentis AG <year>' line found.")


def check_pptx(pkg, tokens, year) -> Report:
    report = Report()
    pres = "ppt/presentation.xml"
    root = pkg.xml(pres)
    if root is None:
        raise CheckError(f"{pkg.path}: no ppt/presentation.xml")
    prels = pkg.rels(pres)
    slides = []
    lst = root.find(P + "sldIdLst")
    for sid in (lst if lst is not None else []):
        rid = sid.get(R + "id")
        if rid in prels:
            slides.append(prels[rid][1])
    masters = sorted(t for typ, t in prels.values() if typ == "slideMaster")
    theme_part = next((t for m in masters for typ, t in pkg.rels(m).values() if typ == "theme"), None)
    theme = theme_findings(report, pkg, theme_part, tokens)

    template_texts, inherited = [], {}
    layouts = sorted({t for m in masters for typ, t in pkg.rels(m).values() if typ == "slideLayout"},
                     key=lambda n: int(re.sub(r"\D", "", posixpath.basename(n)) or 0))
    for part, scope in [(m, "master") for m in masters] + [(l, "layout") for l in layouts]:
        xml = pkg.xml(part)
        if xml is None:
            continue
        csld = xml.find(P + "cSld")
        name = csld.get("name", "") if csld is not None else ""
        where = "slide master" if scope == "master" else f"layout '{name}'"
        template_texts.append((where, "\n".join(t.text or "" for t in xml.iter(A + "t"))))
        for rule, detail in drawing_findings(xml, tokens, theme).items():
            inherited.setdefault((scope, rule), []).append((where, detail))
    for (scope, rule), hits in sorted(inherited.items()):
        where = hits[0][0] if len(hits) == 1 else f"{len(hits)} {scope}s"
        names = "; ".join(f"{w}: {d}" for w, d in hits[:3]) + (" …" if len(hits) > 3 else "")
        report.add("INFO", scope, where, rule, f"From the template, inherited (not the slide's): {names}")

    slide_texts = []
    for n, part in enumerate(slides, start=1):
        xml = pkg.xml(part)
        if xml is None:
            continue
        where = f"slide {n}" + (" (hidden)" if xml.get("show") in ("0", "false") else "")
        found = drawing_findings(xml, tokens, theme)
        text = "\n".join(t.text or "" for t in xml.iter(A + "t"))
        for typ, target in pkg.rels(part).values():
            if typ == "chart" and target in pkg.names:
                chart = pkg.xml(target)
                for rule, detail in drawing_findings(chart, tokens, theme).items():
                    found[rule] = (found[rule] + " Chart: " + detail) if rule in found else "Chart: " + detail
                text += "\n" + chart_text(chart)
        severity = {"colour.legend-only": "INFO"}
        for rule, detail in found.items():
            report.add(severity.get(rule, "FAIL"), "slide", where, rule, detail)
        slide_texts.append((where, text))
        if re.search(r"\bthank(s| you)\b", text, re.I):
            report.add("FAIL", "slide", where, "slide.thank-you", "A 'Thank you' slide.")
        text_findings(report, "slide", where, text, tokens)
        shapes = shapes_text(xml)
        paras = [p for _, ps in shapes for p in ps if p[3]]
        headline = next((ps[0][0] for t, ps in shapes if t and ps and ps[0][3]), None)
        if headline is None:
            headline = next((p[0] for p in paras), "")
        if looks_title_case(headline):
            report.add("WARN", "slide", where, "text.title-case", f"Headline in Title Case: '{headline[:60]}'.")
        aligned = [p[0] for p in paras if p[1] in ("ctr", "r", "just", "dist")]
        if aligned:
            report.add("WARN", "slide", where, "text.align",
                       f"{len(aligned)} centred or right-aligned paragraph(s), e.g. '{aligned[0][:40]}'.")
        chars = sum(p[3] for p in paras)
        bold = sum(p[2] for p in paras)
        if chars > 20 and bold / chars > tokens["bold_share"]:
            report.add("WARN", "slide", where, "text.bold", f"{round(100 * bold / chars)}% of the text is bold.")
        most = max((sum(1 for p in ps if p[3]) for t, ps in shapes if not t), default=0)
        if most > tokens["max_bullets"]:
            report.add("WARN", "slide", where, "slide.bullets", f"{most} paragraphs in one text box.")
        outlines = outline_count(xml)
        if outlines:
            report.add("WARN", "slide", where, "shape.outline", f"{outlines} filled shape(s) with an outline.")
        no_alt = [c for c in (pic.find(f"{P}nvPicPr/{P}cNvPr") for pic in xml.iter(P + "pic"))
                  if c is not None and not (c.get("descr") or "").strip()]
        if no_alt:
            report.add("INFO", "slide", where, "image.alt-text", f"{len(no_alt)} picture(s) without alt text.")
    if not slides:
        report.add("INFO", "file", "deck", "file.empty", "The deck has no slides.")
    footer_findings(report, slide_texts, template_texts, tokens, year, "pptx")
    return report


# --- WordprocessingML and SpreadsheetML (lighter) -----------------------------------

def check_docx(pkg, tokens, year) -> Report:
    report = Report()
    parts = ["word/document.xml"] + sorted(n for n in pkg.names
                                           if re.fullmatch(r"word/(header|footer)\d*\.xml", n))
    texts = []
    for part in parts + ["word/styles.xml"]:
        root = pkg.xml(part)
        if root is None:
            continue
        styles = part == "word/styles.xml"
        scope, where = ("styles", "styles") if styles else ("document", posixpath.basename(part)[:-4])
        sev = "WARN" if styles else "FAIL"
        off, legend, fonts, italic = set(), set(), set(), 0
        for el in root.iter():
            name = local(el.tag)
            if name == "color" or name == "shd":
                val = (el.get(W + "val") if name == "color" else el.get(W + "fill")) or ""
                val = val.upper()
                if re.fullmatch(r"[0-9A-F]{6}", val):
                    (legend if val in tokens["legend"] else off if val not in tokens["palette"] else set()).add("#" + val)
            elif name == "rFonts":
                fonts |= {el.get(W + k) for k in ("ascii", "hAnsi") if el.get(W + k)} - tokens["fonts"]
            elif name == "i" and el.get(W + "val", "1") not in ("0", "false", "off"):
                italic += 1
        if off:
            report.add(sev, scope, where, "colour.off-palette", f"Colours outside the palette: {listing(off)}.")
        if legend:
            report.add("INFO", scope, where, "colour.legend-only", f"Legend-only colours: {listing(legend)}.")
        if fonts:
            report.add(sev, scope, where, "font.non-brand", f"Fonts other than {tokens['family']}: {listing(fonts)}.")
        if italic:
            report.add(sev, scope, where, "text.italic", f"{italic} italic run(s) or style(s).")
        if not styles:
            text = "\n".join(t.text or "" for t in root.iter(W + "t"))
            texts.append((where, text))
            text_findings(report, scope, where, text, tokens)
    theme_findings(report, pkg, "word/theme/theme1.xml" if "word/theme/theme1.xml" in pkg.names else None, tokens)
    footer_findings(report, texts, [], tokens, year, "docx")
    return report


def check_xlsx(pkg, tokens, year) -> Report:
    report = Report()
    styles = pkg.xml("xl/styles.xml")
    if styles is not None:
        off, legend, fonts = set(), set(), set()
        for el in styles.iter():
            name = local(el.tag)
            if name in ("color", "fgColor", "bgColor") and el.get("rgb"):
                val = el.get("rgb").upper()[-6:]
                if val in tokens["legend"]:
                    legend.add("#" + val)
                elif val not in tokens["palette"]:
                    off.add("#" + val)
            elif name == "name" and el.get("val"):
                if el.get("val") not in tokens["fonts"]:
                    fonts.add(el.get("val"))
        if off:
            report.add("WARN", "styles", "styles", "colour.off-palette", f"Colours outside the palette: {listing(off)}.")
        if legend:
            report.add("INFO", "styles", "styles", "colour.legend-only", f"Legend-only colours: {listing(legend)}.")
        if fonts:
            report.add("WARN", "styles", "styles", "font.non-brand", f"Fonts other than {tokens['family']}: {listing(fonts)}.")
    texts = []
    sst = pkg.xml("xl/sharedStrings.xml")
    if sst is not None:
        texts.append(("shared strings", "\n".join(t.text or "" for t in sst.iter(S + "t"))))
    for part in sorted(n for n in pkg.names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)):
        root = pkg.xml(part)
        hf = [e.text or "" for e in root.iter() if local(e.tag) in ("oddHeader", "oddFooter", "evenHeader",
                                                                   "evenFooter", "firstHeader", "firstFooter")]
        inline = [t.text or "" for t in root.iter(S + "t")]
        if hf or inline:
            texts.append((posixpath.basename(part)[:-4], "\n".join(hf + inline)))
    for where, text in texts:
        text_findings(report, "sheet", where, text, tokens)
    footer_findings(report, texts, [], tokens, year, "xlsx")
    return report


# --- output -------------------------------------------------------------------------

def _order(f):
    m = re.match(r"slide (\d+)", f["location"])
    scope_rank = ["slide", "document", "sheet", "styles", "file", "theme", "master", "layout"]
    return (SEVERITIES.index(f["severity"]), scope_rank.index(f["scope"]) if f["scope"] in scope_rank else 99,
            int(m.group(1)) if m else 0, f["location"], f["rule"])


def summary(items) -> dict:
    return {s: sum(1 for f in items if f["severity"] == s) for s in SEVERITIES}


def as_markdown(path, items) -> str:
    cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
    lines = [f"Brand check: {path}", ""]
    if items:
        lines += ["| Severity | Where | Rule | Finding | Proposed fix | Source |",
                  "|---|---|---|---|---|---|"]
        lines += [f"| {f['severity']} | {cell(f['location'])} | {f['rule']} | {cell(f['message'])} "
                  f"| {cell(f['fix'])} | {f['source']} |" for f in items]
        lines.append("")
    s = summary(items)
    lines.append(f"{s['FAIL']} FAIL, {s['WARN']} WARN, {s['INFO']} INFO. "
                 "Master, layout and theme findings come from the template. "
                 "Nothing was changed: a person decides which fixes to make.")
    return "\n".join(lines)


def check(path, year=None, tokens_path=TOKENS) -> dict:
    tokens = load_tokens(tokens_path)
    year = year or datetime.date.today().year
    kind = Path(path).suffix.lower().lstrip(".")
    checkers = {"pptx": check_pptx, "potx": check_pptx, "docx": check_docx, "dotx": check_docx,
                "xlsx": check_xlsx, "xltx": check_xlsx}
    if kind not in checkers:
        raise CheckError(f"{path}: not a .pptx, .docx or .xlsx file")
    pkg = Package(path)
    report = checkers[kind](pkg, tokens, year)
    items = sorted(report.items, key=_order)
    return {"file": str(path), "kind": kind, "year": year, "summary": summary(items), "findings": items}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check a .pptx/.docx/.xlsx against the Frequentis brand.")
    ap.add_argument("file")
    ap.add_argument("--json", action="store_true", help="print the findings as JSON")
    ap.add_argument("--year", type=int, help="the expected copyright year (default: this year)")
    ap.add_argument("--tokens", default=str(TOKENS), help="brand-tokens.json to use")
    args = ap.parse_args(argv)
    try:
        result = check(args.file, args.year, args.tokens)
    except CheckError as exc:
        print(f"check_brand: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=1, ensure_ascii=False) if args.json
          else as_markdown(args.file, result["findings"]))
    return 1 if result["summary"]["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
