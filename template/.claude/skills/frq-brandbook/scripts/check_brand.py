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
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path

TOKENS = Path(__file__).resolve().parent.parent / "brand-tokens.json"
# Limits against hostile files: the largest real part (a map layout) is about 3.3 MB of XML.
MAX_PART = 16 * 1024 * 1024          # one XML part, uncompressed
MAX_TOTAL = 256 * 1024 * 1024        # all XML parts read, uncompressed
MAX_RATIO = 100                      # compression ratio of a part above 1 MB (zip bombs)
MAX_SLIDES = 500
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
COLOUR_KINDS = {"srgbClr", "schemeClr", "sysClr", "prstClr"}
FILLS = {"noFill", "solidFill", "gradFill", "pattFill", "blipFill", "grpFill"}
SYS_COLOURS = {"windowText": "000000", "window": "FFFFFF", "btnText": "000000"}
PRESET_COLOURS = {"black": "000000", "white": "FFFFFF"}
# Tints of these are fine (PDF p.7: "except for greys"); tints of blue, light blue and accents are not.
GREYS = {"333333", "626469", "666666", "9FA0A3", "999999", "C9C3BA", "FFFFFF", "000000"}
SLIDE_SEVERITY = {"colour.legend-only": "INFO", "colour.tint": "WARN"}
MONTHS = ("January|February|March|April|May|June|July|August|September|October|November|December"
          "|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec")
CONTRACTIONS = (r"\b(?:\w+n['’]t|(?:it|that|there|what|let|here|who)['’]s|(?:we|you|they)['’](?:re|ve|ll|d)"
                r"|i['’](?:m|ve|ll|d))\b")
NUMBER_CONTEXT = {"page", "step", "level", "version", "v", "phase", "option", "figure", "fig", "table",
                  "slide", "chapter", "section", "sprint", "pi", "release", "item", "no", "number", "gate",
                  "iteration", "wave", "tier", "stage", "lane", "q"}
UNITS = {"m", "bn", "pt", "px", "mm", "cm", "kg", "km", "h", "min", "s", "ms", "gb", "mb", "tb", "x"}
GROUP_COMPANY = r"FREQUENTIS(\s+[A-Z][\w.&-]*){0,3}\s+(AG|GmbH|Ltd\.?|s\.r\.o\.|Pty|Inc\.?|SAS|S\.A\.|B\.V\.)"
DOCX_THEME_FIX = {
    "theme.colours": "Start customer documents from Doknorme.dotm (Word -> Shared Templates); otherwise set colours per style.",
    "theme.fonts": "Set the document's theme fonts to Arial, or start from Doknorme.dotm (Word -> Shared Templates).",
}
XLSX_FONT_FIX = "Set the workbook's Normal style to Arial (openpyxl: wb._named_styles['Normal'].font = Font(name='Arial'))."

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
    "text.caps-name": ("Write 'Frequentis' in sentence case (capitals only in print headlines and group company names); never retype the logo, use the logo file.", "PDF p.4, p.25"),
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
    "colour.tint": ("Use the brand colour itself, not a lighter or darker tint (grey tints are fine).", "PDF p.7"),
    "text.at-frequentis": ("Write 'we' without 'At Frequentis we…'.", "PDF p.23"),
    "text.contraction": ("Write the words out in formal (customer) material: 'we are', 'do not'.", "PDF p.24"),
    "text.date": ("Write dates as '25 March 2026': no 'th', no comma.", "PDF p.22"),
    "text.number": ("One to twelve in words; 2,115; 15.50; 10m; 15bn; +10%.", "PDF p.22"),
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
            self.names = set(self.zip.namelist())
        except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, ValueError) as exc:
            raise CheckError(f"{self.path}: not an Office file, or it is damaged ({exc})") from None
        self.read_total = 0
        self.cache = {}

    def read(self, name) -> bytes:
        """The bytes of one XML part, within the size, ratio and total budgets."""
        info = self.zip.getinfo(name)
        if info.file_size > MAX_PART:
            raise CheckError(f"{self.path}: part {name} is too large to check ({info.file_size} bytes)")
        if info.file_size > 1024 * 1024 and info.file_size > MAX_RATIO * max(info.compress_size, 1):
            raise CheckError(f"{self.path}: part {name} is compressed more than {MAX_RATIO}:1; "
                             "refusing it (a zip bomb?)")
        self.read_total += info.file_size
        if self.read_total > MAX_TOTAL:
            raise CheckError(f"{self.path}: the file is larger than the checker's budget "
                             f"({MAX_TOTAL // (1024 * 1024)} MB of XML)")
        try:
            return self.zip.read(name)
        except (zipfile.BadZipFile, zlib.error, EOFError, RuntimeError, NotImplementedError,
                OSError) as exc:
            raise CheckError(f"{self.path}: part {name} is damaged or encrypted and cannot be read "
                             f"({exc})") from None

    def xml(self, name):
        if name not in self.names:
            return None
        if name in self.cache:
            return self.cache[name]
        data = self.read(name)
        # Office writes UTF-8. Anything else (UTF-16 with or without a BOM, Latin-1) is refused
        # before the DTD check, so an entity declaration cannot hide in another encoding.
        decl = re.match(rb"\s*<\?xml[^>]*?encoding=[\"']([A-Za-z0-9._-]+)", data)
        if (data[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in data[:400]
                or (decl and decl.group(1).lower() not in (b"utf-8", b"utf8"))):
            raise CheckError(f"{self.path}: part {name} is not UTF-8; refusing to parse it")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise CheckError(f"{self.path}: part {name} is not UTF-8; refusing to parse it") from None
        if re.search(rb"<!\s*(DOCTYPE|ENTITY)", data, re.I):
            # OOXML never uses a DTD; refusing one blocks entity expansion (stdlib only, no defusedxml)
            raise CheckError(f"{self.path}: part {name} declares a DTD or an entity; refusing to parse it")
        try:
            root = ET.fromstring(data)
        except ET.ParseError as exc:
            raise CheckError(f"{self.path}: part {name} is not valid XML ({exc})") from None
        self.cache[name] = root
        return root

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

    def add(self, severity, scope, location, rule, message, fix=None):
        default_fix, source = RULES[rule]
        self.items.append({"severity": severity, "scope": scope, "location": location,
                           "rule": rule, "message": message, "fix": fix or default_fix,
                           "source": source})


def listing(values, limit=6) -> str:
    values = sorted(values)
    more = f" (+{len(values) - limit} more)" if len(values) > limit else ""
    return ", ".join(values[:limit]) + more


# --- themes -------------------------------------------------------------------------

def read_theme(pkg, theme_part) -> dict:
    """Colours, font scheme and the shape styles (fill, line, effect) a theme defines."""
    theme = {"colours": {}, "major": None, "minor": None, "fills": [], "bgfills": [],
             "lines": [], "effects": [], "part": theme_part}
    root = pkg.xml(theme_part) if theme_part else None
    if root is None:
        return theme
    scheme = root.find(f".//{A}clrScheme")
    for slot in (scheme if scheme is not None else []):
        clr, sys_clr = slot.find(A + "srgbClr"), slot.find(A + "sysClr")
        if clr is not None:
            theme["colours"][local(slot.tag)] = (clr.get("val") or "").upper()
        elif sys_clr is not None:
            theme["colours"][local(slot.tag)] = (sys_clr.get("lastClr") or "").upper()
    for kind in ("major", "minor"):
        latin = root.find(f".//{A}{kind}Font/{A}latin")
        theme[kind] = latin.get("typeface") if latin is not None else None
    fmt = root.find(f".//{A}fmtScheme")
    if fmt is not None:
        for name, key in (("fillStyleLst", "fills"), ("bgFillStyleLst", "bgfills")):
            lst = fmt.find(A + name)
            theme[key] = list(lst) if lst is not None else []
        lst = fmt.find(A + "lnStyleLst")
        theme["lines"] = [ln.find(A + "noFill") is None for ln in (lst if lst is not None else [])]
        lst = fmt.find(A + "effectStyleLst")
        theme["effects"] = [{EFFECTS[local(x.tag)] for x in es.iter() if local(x.tag) in EFFECTS}
                            for es in (lst if lst is not None else [])]
    return theme


def theme_findings(report, theme, tokens, severity="WARN", fixes=None):
    if theme["part"] is None:
        return
    fixes = fixes or {}
    bad = {f"{k} #{v}" for k, v in theme["colours"].items()
           if k not in ("hlink", "folHlink") and v not in tokens["palette"]}
    if bad:
        report.add(severity, "theme", theme["part"], "theme.colours",
                   f"Theme colours outside the palette: {listing(bad)}.", fixes.get("theme.colours"))
    faces = {f"{k}: {theme[k]}" for k in ("major", "minor") if theme[k] and theme[k] != tokens["family"]}
    if faces:
        report.add(severity, "theme", theme["part"], "theme.fonts", f"Theme fonts: {listing(faces)}.",
                   fixes.get("theme.fonts"))


# --- DrawingML (slides, layouts, masters, charts) ------------------------------------

def scheme_hex(theme, name) -> str:
    return theme["colours"].get(SCHEME_ALIAS.get(name, name), name)


def colour_hex(el, theme, placeholder=None) -> str:
    """The HEX of a DrawingML colour element (srgbClr, schemeClr, sysClr, prstClr)."""
    kind = local(el.tag)
    if kind == "srgbClr":
        return (el.get("val") or "").upper()
    if kind == "schemeClr":
        val = el.get("val", "")
        if val == "phClr" and placeholder:
            return placeholder
        return scheme_hex(theme, val)
    if kind == "sysClr":
        return (el.get("lastClr") or SYS_COLOURS.get(el.get("val", ""), "")).upper()
    if kind == "prstClr":
        return PRESET_COLOURS.get(el.get("val", ""), el.get("val", ""))
    return ""


def gradient_label(grad, tokens, theme, placeholder=None):
    """None for the brand gradient (or one brand colour), else a description of the stops."""
    stops, modded = [], False
    for gs in grad.iter(A + "gs"):
        for clr in gs:
            if local(clr.tag) in COLOUR_KINDS:
                stops.append(colour_hex(clr, theme, placeholder))
                modded |= any(local(m.tag) in COLOUR_MODS for m in clr)
    if not stops or (set(stops) <= tokens["gradient"] and not modded):
        return None
    label = " -> ".join(("#" + s if re.fullmatch(r"[0-9A-F]{6}", s) else s) for s in stops)
    return label + (" (tinted)" if modded else "")


def shape_style(sp, theme, tokens):
    """What a shape inherits from the theme through <p:style> (python-pptx's add_shape writes
    one): (effects, gradient label or None, filled, theme line visible)."""
    sppr, style = sp.find(P + "spPr"), sp.find(P + "style")
    effects, gradient, filled, line = set(), None, False, False
    has_fill = sppr is not None and any(local(x.tag) in FILLS for x in sppr)
    if sppr is not None:
        filled = any(local(x.tag) in FILLS and local(x.tag) != "noFill" for x in sppr)
    if style is None:
        return effects, gradient, filled, line
    ref = style.find(A + "effectRef")
    if ref is not None and (sppr is None or (sppr.find(A + "effectLst") is None
                                             and sppr.find(A + "effectDag") is None)):
        idx = int(ref.get("idx", "0") or 0)
        if 0 < idx <= len(theme["effects"]):
            effects = {e + " (from the theme style)" for e in theme["effects"][idx - 1]}
    ref = style.find(A + "fillRef")
    if ref is not None and not has_fill:
        idx = int(ref.get("idx", "0") or 0)
        pool, i = (theme["bgfills"], idx - 1001) if idx > 1000 else (theme["fills"], idx - 1)
        if idx > 0 and 0 <= i < len(pool):
            fill = pool[i]
            filled = local(fill.tag) != "noFill"
            if local(fill.tag) == "gradFill":
                clr = next((c for c in ref if local(c.tag) in COLOUR_KINDS), None)
                ph = colour_hex(clr, theme) if clr is not None else None
                label = gradient_label(fill, tokens, theme, ph)
                gradient = f"{label} (from the theme style)" if label else None
    ref = style.find(A + "lnRef")
    ln = sppr.find(A + "ln") if sppr is not None else None
    own_line = ln is not None and any(local(x.tag) in FILLS for x in ln)
    if own_line:
        line = ln.find(A + "noFill") is None
    elif ref is not None:
        idx = int(ref.get("idx", "0") or 0)
        line = 0 < idx <= len(theme["lines"]) and theme["lines"][idx - 1]
    return effects, gradient, filled, line


def drawing_findings(root, tokens, theme) -> dict:
    """{rule: detail} of the visual rules in one DrawingML part (slide, layout, master, chart)."""
    parents = parents_of(root)
    off, legend, fonts, effects, threed, gradients, tints = (set() for _ in range(7))
    italic = []
    for el in root.iter():
        kind = local(el.tag)
        if kind not in COLOUR_KINDS or not el.tag.startswith(A):
            continue
        up = [local(x.tag) for x in ancestors(el, parents)]
        if "effectLst" in up or "effectDag" in up or "style" in up:
            continue                       # shadow colours and style refs are judged elsewhere
        val = colour_hex(el, theme)
        if kind != "schemeClr":
            if val in tokens["legend"]:
                legend.add("#" + val)
            elif val and val not in tokens["palette"]:
                off.add("#" + val if re.fullmatch(r"[0-9A-F]{6}", val) else val)
        if "gradFill" not in up and any(local(m.tag) in COLOUR_MODS for m in el):
            if val not in GREYS:
                tints.add("#" + val if re.fullmatch(r"[0-9A-F]{6}", val) else val)
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
        if any(local(x.tag) == "style" for x in ancestors(grad, parents)):
            continue
        label = gradient_label(grad, tokens, theme)
        if label:
            gradients.add(label)
    for sp in list(root.iter(P + "sp")) + list(root.iter(P + "cxnSp")):
        eff, grad, _, _ = shape_style(sp, theme, tokens)
        effects |= eff
        if grad:
            gradients.add(grad)
    out = {}
    if off:
        out["colour.off-palette"] = f"Colours outside the palette: {listing(off)}."
    if legend:
        out["colour.legend-only"] = f"Legend-only colours: {listing(legend)}."
    if tints:
        out["colour.tint"] = f"Tints or shades of brand colours: {listing(tints)}."
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


def outline_count(root, theme, tokens) -> int:
    n = 0
    for sp in root.iter(P + "sp"):
        _, _, filled, line = shape_style(sp, theme, tokens)
        if filled and line:
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


# --- writing rules (any format) -----------------------------------------------------

def small_numbers(text) -> list:
    """Digits for one to twelve in running text (not dates, times, units, list numbers)."""
    hits = []
    for m in re.finditer(r"(?<![\w.,€$£#/:+\-])([1-9]|1[0-2])(?![\w.,%:/)\-])", text):
        before = re.findall(r"[A-Za-z]+", text[max(0, m.start() - 15):m.start()])
        after = re.match(r"\s*([A-Za-z]+)", text[m.end():])
        if before and before[-1].lower() in NUMBER_CONTEXT:
            continue
        if after and (re.fullmatch(MONTHS, after.group(1), re.I) or after.group(1).lower() in UNITS):
            continue
        hits.append(m.group(1))
    return hits


def text_findings(report, scope, where, text, tokens, public, shape_texts=()):
    """The writing rules on visible text. `public`: the file is Frequentis Public or has no class."""
    if re.search(r"\bFRQ\b", text):
        report.add("FAIL" if public else "WARN", scope, where, "text.frq",
                   "'FRQ' in visible text" + ("" if public else " (fine internally; not in anything external)") + ".")
    caps = [m for m in re.finditer(r"\bFREQUENTIS\b", text)
            if not re.match(GROUP_COMPANY, text[m.start():])]
    if caps:
        report.add("WARN", scope, where, "text.caps-name",
                   "'FREQUENTIS' in capitals (a retyped logo? capitals are for print headlines only).")
    if re.search(r"for a safer world", text, re.I):
        alone = any(re.fullmatch(r"\s*for a safer world[.!]?\s*", s, re.I) for s in shape_texts)
        report.add("FAIL" if alone else "WARN", scope, where, "text.tagline",
                   "The tagline is typed as text on its own." if alone else "The tagline appears in running text.")
    us = {w.lower() for w in re.findall(r"[A-Za-z]+", text) if w.lower() in tokens["us"]}
    if us:
        report.add("WARN", scope, where, "text.us-spelling",
                   "US spelling: " + listing(f"{w} -> {tokens['us'][w]}" for w in us) + ".")
    if "!!" in text or text.count("!") > 1:
        report.add("WARN", scope, where, "text.exclamation", f"{text.count('!')} exclamation mark(s).")
    if re.search(r"\s&\s", text):
        report.add("INFO", scope, where, "text.ampersand", "'&' in running text.")
    if re.search(r"\bAt Frequentis,? we\b", text, re.I):
        report.add("WARN", scope, where, "text.at-frequentis", "'At Frequentis we…'.")
    contractions = re.findall(CONTRACTIONS, text, re.I)
    if contractions:
        report.add("WARN", scope, where, "text.contraction",
                   f"Contractions (avoid in formal material): {listing(set(contractions))}.")
    if re.search(rf"\b\d{{1,2}}(st|nd|rd|th)\b|\b({MONTHS})\s+\d{{1,2}}(st|nd|rd|th)?,", text, re.I):
        report.add("WARN", scope, where, "text.date", "Date not written as '25 March 2026'.")
    numbers = []
    if re.search(r"\bMio\b", text):
        numbers.append("'Mio' (write 10m in English)")
    if re.search(r"\d\s*(percent|per cent)\b", text, re.I):
        numbers.append("'percent' (write +10%)")
    if re.search(r"\d\s*(million|billion)\b", text, re.I):
        numbers.append("'million/billion' (write 10m, 15bn)")
    if re.search(r"(?<![\d.,])\d{1,3}\.\d{3}(?![\d.,])", text):
        numbers.append("a point as thousands separator (write 2,115)")
    if re.search(r"(?<![\d.,])\d+,\d{1,2}(?![\d,])", text):
        numbers.append("a decimal comma (write 15.50)")
    small = small_numbers(text)
    if small:
        numbers.append(f"digits for one to twelve ({listing(set(small), 4)})")
    if numbers:
        report.add("WARN", scope, where, "text.number", "Number style: " + "; ".join(numbers) + ".")


def classes_in(texts, tokens) -> set:
    cls = re.compile("|".join(re.escape(c) for c in tokens["classes"]))
    return {m.group(0) for _, t in texts for m in cls.finditer(t)}


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
    if len(slides) > MAX_SLIDES:
        raise CheckError(f"{pkg.path}: {len(slides)} slides; the checker reads at most {MAX_SLIDES}")
    masters = sorted(t for typ, t in prels.values() if typ == "slideMaster")
    theme_part = next((t for m in masters for typ, t in pkg.rels(m).values() if typ == "theme"), None)
    theme = read_theme(pkg, theme_part)
    theme_findings(report, theme, tokens)

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

    parsed = []
    for n, part in enumerate(slides, start=1):
        xml = pkg.xml(part)
        if xml is None:
            continue
        text = "\n".join(t.text or "" for t in xml.iter(A + "t"))
        charts = [pkg.xml(t) for typ, t in pkg.rels(part).values() if typ == "chart" and t in pkg.names]
        text += "".join("\n" + chart_text(c) for c in charts)
        parsed.append((n, xml, charts, text))
    found_classes = classes_in([(None, p[3]) for p in parsed] + template_texts, tokens)
    public = not found_classes or "Frequentis Public" in found_classes

    slide_texts = []
    for n, xml, charts, text in parsed:
        where = f"slide {n}" + (" (hidden)" if xml.get("show") in ("0", "false") else "")
        found = drawing_findings(xml, tokens, theme)
        for chart in charts:
            for rule, detail in drawing_findings(chart, tokens, theme).items():
                found[rule] = (found[rule] + " Chart: " + detail) if rule in found else "Chart: " + detail
        for rule, detail in found.items():
            report.add(SLIDE_SEVERITY.get(rule, "FAIL"), "slide", where, rule, detail)
        slide_texts.append((where, text))
        short = len(re.findall(r"\w+", text)) <= 12           # a closing slide, not a sentence
        if re.search(r"\bthank(s| you)\b", text, re.I):
            report.add("FAIL" if short else "WARN", "slide", where, "slide.thank-you",
                       "A 'Thank you' slide." if short else "'Thank you' on a content slide; is it a closing slide?")
        elif short and re.search(r"\bquestions\s*\?", text, re.I):
            report.add("FAIL", "slide", where, "slide.thank-you", "A 'Questions?' closing slide.")
        shapes = shapes_text(xml)
        whole = ["\n".join(p[0] for p in ps) for _, ps in shapes]
        text_findings(report, "slide", where, text, tokens, public, whole)
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
        outlines = outline_count(xml, theme, tokens)
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

def word_findings(root, theme, tokens) -> tuple:
    """(off-palette, legend, fonts, italic count) of a WordprocessingML element tree."""
    off, legend, fonts, italic = set(), set(), set(), 0
    for el in root.iter():
        name = local(el.tag)
        if name in ("color", "shd"):
            val = ((el.get(W + "val") if name == "color" else el.get(W + "fill")) or "").upper()
            if re.fullmatch(r"[0-9A-F]{6}", val):
                if val in tokens["legend"]:
                    legend.add("#" + val)
                elif val not in tokens["palette"]:
                    off.add("#" + val)
        elif name == "rFonts":
            faces = {el.get(W + k) for k in ("ascii", "hAnsi") if el.get(W + k)}
            for k in ("asciiTheme", "hAnsiTheme"):
                ref = el.get(W + k)
                if ref:
                    faces.add(theme["major" if ref.startswith("major") else "minor"] or ref)
            fonts |= {f for f in faces if f} - tokens["fonts"]
        elif name == "i" and el.get(W + "val", "1") not in ("0", "false", "off"):
            italic += 1
    return off, legend, fonts, italic


def used_word_styles(styles, bodies) -> list:
    """The style elements the document uses (directly or through basedOn), plus docDefaults."""
    if styles is None:
        return []
    by_id = {s.get(W + "styleId"): s for s in styles.iter(W + "style")}
    wanted = {el.get(W + "val") for b in bodies for el in b.iter()
              if local(el.tag) in ("pStyle", "rStyle", "tblStyle")}
    wanted |= {sid for sid, s in by_id.items() if s.get(W + "default") in ("1", "true")
               and s.get(W + "type") in ("paragraph", "character", "table")}
    seen, todo = set(), list(wanted)
    while todo:
        sid = todo.pop()
        if sid in seen or sid not in by_id:
            continue
        seen.add(sid)
        based = by_id[sid].find(W + "basedOn")
        if based is not None:
            todo.append(based.get(W + "val"))
    out = [by_id[s] for s in sorted(seen)]
    defaults = styles.find(W + "docDefaults")
    return ([defaults] if defaults is not None else []) + out


def check_docx(pkg, tokens, year) -> Report:
    report = Report()
    theme_part = "word/theme/theme1.xml" if "word/theme/theme1.xml" in pkg.names else None
    theme = read_theme(pkg, theme_part)
    theme_findings(report, theme, tokens, "INFO", DOCX_THEME_FIX)
    parts = ["word/document.xml"] + sorted(n for n in pkg.names
                                           if re.fullmatch(r"word/(header|footer)\d*\.xml", n))
    bodies = [(p, pkg.xml(p)) for p in parts]
    bodies = [(p, r) for p, r in bodies if r is not None]
    texts = [(posixpath.basename(p)[:-4], "\n".join(t.text or "" for t in r.iter(W + "t"))) for p, r in bodies]
    found_classes = classes_in(texts, tokens)
    public = not found_classes or "Frequentis Public" in found_classes
    checks = [("document", posixpath.basename(p)[:-4], r, "FAIL") for p, r in bodies]
    styles = used_word_styles(pkg.xml("word/styles.xml"), [r for _, r in bodies])
    for el in styles:
        sid = el.get(W + "styleId") or "document defaults"
        checks.append(("styles", f"style '{sid}'", el, "WARN"))
    for scope, where, root, sev in checks:
        off, legend, fonts, italic = word_findings(root, theme, tokens)
        if off:
            report.add(sev, scope, where, "colour.off-palette", f"Colours outside the palette: {listing(off)}.")
        if legend:
            report.add("INFO", scope, where, "colour.legend-only", f"Legend-only colours: {listing(legend)}.")
        if fonts:
            report.add(sev, scope, where, "font.non-brand", f"Fonts other than {tokens['family']}: {listing(fonts)}.")
        if italic:
            report.add(sev, scope, where, "text.italic", f"{italic} italic run(s) or style(s).")
    for where, text in texts:
        text_findings(report, "document", where, text, tokens, public)
    footer_findings(report, texts, [], tokens, year, "docx")
    return report


def check_xlsx(pkg, tokens, year) -> Report:
    report = Report()
    sheets = [(p, pkg.xml(p)) for p in sorted(n for n in pkg.names
                                              if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))]
    used = set()
    for _, root in sheets:
        for c in root.iter(S + "c"):
            used.add(int(c.get("s", "0") or 0))
    styles = pkg.xml("xl/styles.xml")
    if styles is not None and used:
        fonts_el = styles.find(S + "fonts")
        fills_el = styles.find(S + "fills")
        xfs_el = styles.find(S + "cellXfs")
        fonts_l = list(fonts_el) if fonts_el is not None else []
        fills_l = list(fills_el) if fills_el is not None else []
        xfs = list(xfs_el) if xfs_el is not None else []
        font_ids = {int(xfs[i].get("fontId", "0")) for i in used if i < len(xfs)} or ({0} if fonts_l else set())
        fill_ids = {int(xfs[i].get("fillId", "0")) for i in used if i < len(xfs)}
        off, legend, faces = set(), set(), set()
        targets = [fonts_l[i] for i in font_ids if i < len(fonts_l)] + [fills_l[i] for i in fill_ids if i < len(fills_l)]
        for el in (e for t in targets for e in t.iter()):
            name = local(el.tag)
            if name in ("color", "fgColor", "bgColor") and el.get("rgb"):
                val = el.get("rgb").upper()[-6:]
                if val in tokens["legend"]:
                    legend.add("#" + val)
                elif val not in tokens["palette"]:
                    off.add("#" + val)
            elif name == "name" and el.get("val") and el.get("val") not in tokens["fonts"]:
                faces.add(el.get("val"))
        if off:
            report.add("WARN", "styles", "cell styles in use", "colour.off-palette", f"Colours outside the palette: {listing(off)}.")
        if legend:
            report.add("INFO", "styles", "cell styles in use", "colour.legend-only", f"Legend-only colours: {listing(legend)}.")
        if faces:
            report.add("WARN", "styles", "cell styles in use", "font.non-brand",
                       f"Fonts other than {tokens['family']}: {listing(faces)}.", XLSX_FONT_FIX)
    texts = []
    sst = pkg.xml("xl/sharedStrings.xml")
    if sst is not None:
        texts.append(("shared strings", "\n".join(t.text or "" for t in sst.iter(S + "t"))))
    for part, root in sheets:
        hf = [e.text or "" for e in root.iter() if local(e.tag) in ("oddHeader", "oddFooter", "evenHeader",
                                                                   "evenFooter", "firstHeader", "firstFooter")]
        inline = [t.text or "" for t in root.iter(S + "t")]
        if hf or inline:
            texts.append((posixpath.basename(part)[:-4], "\n".join(hf + inline)))
    found_classes = classes_in(texts, tokens)
    public = not found_classes or "Frequentis Public" in found_classes
    for where, text in texts:
        text_findings(report, "sheet", where, text, tokens, public)
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
    except Exception as exc:  # noqa: BLE001  a damaged or unusual file must not read as a brand FAIL
        print(f"check_brand: {args.file} could not be checked ({type(exc).__name__}: {exc}). "
              "Open it in Office and save it again, or check it by eye.", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=1, ensure_ascii=False) if args.json
          else as_markdown(args.file, result["findings"]))
    return 1 if result["summary"]["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
