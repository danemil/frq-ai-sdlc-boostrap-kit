#!/usr/bin/env python3
"""scripts/maintainer/strip_pptx_metadata.py: removes personal and tenant data from a
.pptx template and leaves every other part byte for byte.

The maintainer runs it when Group Communications and Marketing ships a new master
(design 2026-10-09 §8.3). The tests build a small .pptx with zipfile that carries the same
kinds of parts as the real master (comment authors, SharePoint customXml, sensitivity-label
properties, a thumbnail, named people in the core properties). The values are made up.
Plan: docs/roadmap/2026-10-09-stack-pack-plan.md, Task B1.
"""
import ast
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import helpers

SCRIPT = helpers.KIT / "scripts/maintainer/strip_pptx_metadata.py"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OD = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
GONE = ("ppt/commentAuthors.xml", "docProps/custom.xml", "docProps/thumbnail.jpeg",
        "customXml/item1.xml", "customXml/itemProps1.xml", "customXml/_rels/item1.xml.rels")


def sample_parts():
    person = "A. Person"          # a made-up name; the real value never appears in the kit
    return {
        "[Content_Types].xml": (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="{CT_NS}">'
            '<Default Extension="jpeg" ContentType="image/jpeg"/>'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/customXml/itemProps1.xml" ContentType="application/vnd.openxmlformats-officedocument.customXmlProperties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/>'
            '<Override PartName="/ppt/commentAuthors.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.commentAuthors+xml"/>'
            '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
            '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
            "</Types>"),
        "_rels/.rels": (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{REL_NS}">'
            f'<Relationship Id="rId1" Type="{OD}/officeDocument" Target="ppt/presentation.xml"/>'
            f'<Relationship Id="rId2" Type="{PKG}/metadata/thumbnail" Target="docProps/thumbnail.jpeg"/>'
            f'<Relationship Id="rId3" Type="{PKG}/metadata/core-properties" Target="docProps/core.xml"/>'
            f'<Relationship Id="rId4" Type="{OD}/extended-properties" Target="docProps/app.xml"/>'
            f'<Relationship Id="rId5" Type="{OD}/custom-properties" Target="docProps/custom.xml"/>'
            "</Relationships>"),
        "docProps/core.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title/>'
            f"<dc:creator>{person}</dc:creator><cp:lastModifiedBy>{person}</cp:lastModifiedBy>"
            "<cp:revision>7</cp:revision>"
            '<dcterms:created xsi:type="dcterms:W3CDTF">2026-10-07T07:57:08Z</dcterms:created>'
            "</cp:coreProperties>"),
        "docProps/app.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties '
            'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            "<Template>Old template</Template><Words>5109</Words>"
            "<Application>Microsoft Office PowerPoint</Application>"
            "<PresentationFormat>On-screen Show (16:9)</PresentationFormat><Slides>66</Slides>"
            '<TitlesOfParts><vt:vector size="1" baseType="lpstr"><vt:lpstr>An old slide title</vt:lpstr>'
            "</vt:vector></TitlesOfParts><Company>A company</Company></Properties>"),
        "docProps/custom.xml": '<?xml version="1.0"?><Properties><property name="MSIP_Label_x_TenantId"/></Properties>',
        "docProps/thumbnail.jpeg": b"\xff\xd8\xff\xe0 not really a jpeg",
        "customXml/item1.xml": "<p:properties>a SharePoint part</p:properties>",
        "customXml/itemProps1.xml": "<ds:datastoreItem/>",
        "customXml/_rels/item1.xml.rels": f'<Relationships xmlns="{REL_NS}"/>',
        "ppt/presentation.xml": '<?xml version="1.0"?><p:presentation xmlns:p="x"/>',
        "ppt/_rels/presentation.xml.rels": (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{REL_NS}">'
            f'<Relationship Id="rId1" Type="{OD}/customXml" Target="../customXml/item1.xml"/>'
            f'<Relationship Id="rId2" Type="{OD}/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
            f'<Relationship Id="rId3" Type="{OD}/commentAuthors" Target="commentAuthors.xml"/>'
            "</Relationships>"),
        "ppt/commentAuthors.xml": f'<p:cmAuthorLst><p:cmAuthor name="{person}" initials="AP"/></p:cmAuthorLst>',
        "ppt/slideMasters/slideMaster1.xml": "<p:sldMaster>master</p:sldMaster>",
        "ppt/slideLayouts/slideLayout1.xml": '<p:sldLayout><p:cSld name="Standard TITLE"/></p:sldLayout>',
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": (
            f'<Relationships xmlns="{REL_NS}"><Relationship Id="rId1" Type="{OD}/image" '
            'Target="../media/image1.jpeg"/></Relationships>'),
        "ppt/media/image1.jpeg": b"\xff\xd8\xff\xe0 layout picture",
        "ppt/theme/theme1.xml": "<a:theme name='Brand'/>",
    }


def write_pptx(dest, parts):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in parts.items():
            z.writestr(n, data if isinstance(data, bytes) else data.encode("utf-8"))
    return Path(dest)


def run(*args):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True, check=False)


class TestStripPptxMetadata(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.src = write_pptx(Path(self.tmp.name) / "in.pptx", sample_parts())
        self.out = Path(self.tmp.name) / "out.pptx"
        r = run(self.src, self.out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.z = zipfile.ZipFile(self.out)
        self.addCleanup(self.z.close)

    def read(self, name):
        return self.z.read(name).decode("utf-8")

    def test_personal_and_tenant_parts_are_removed(self):
        names = self.z.namelist()
        for gone in GONE:
            self.assertNotIn(gone, names)
        self.assertFalse([n for n in names if n.startswith("customXml/")])
        ct = self.read("[Content_Types].xml")
        for gone in ("/ppt/commentAuthors.xml", "/docProps/custom.xml", "/customXml/"):
            self.assertNotIn(gone, ct)
        self.assertIn('<Default Extension="jpeg"', ct, "other pictures still need the jpeg type")
        for n in names:
            if n.endswith(".rels"):
                text = self.read(n)
                for gone in ("commentAuthors", "custom.xml", "thumbnail", "customXml"):
                    self.assertNotIn(gone, text, n)
        self.assertIn("slideMasters/slideMaster1.xml", self.read("ppt/_rels/presentation.xml.rels"))
        self.assertIn("docProps/core.xml", self.read("_rels/.rels"))

    def test_core_properties_lose_the_people(self):
        core = self.read("docProps/core.xml")
        self.assertIn("<dc:creator></dc:creator>", core)
        self.assertIn("<cp:lastModifiedBy></cp:lastModifiedBy>", core)
        self.assertIn("<cp:revision>7</cp:revision>", core)
        self.assertIn("2026-10-07T07:57:08Z", core)
        self.assertNotIn("Person", core)

    def test_app_properties_are_reduced(self):
        app = self.read("docProps/app.xml")
        self.assertIn("<Application>Microsoft Office PowerPoint</Application>", app)
        self.assertIn("<PresentationFormat>On-screen Show (16:9)</PresentationFormat>", app)
        for gone in ("Template", "Words", "Slides", "TitlesOfParts", "old slide title", "Company"):
            self.assertNotIn(gone, app)

    def test_every_other_part_is_byte_identical(self):
        src = sample_parts()
        changed = {"[Content_Types].xml", "_rels/.rels", "docProps/core.xml", "docProps/app.xml",
                   "ppt/_rels/presentation.xml.rels"}
        kept = [n for n in src if n not in changed and n not in GONE]
        self.assertEqual([n for n in self.z.namelist() if n not in changed], kept, "same members, same order")
        for n in kept:
            data = src[n] if isinstance(src[n], bytes) else src[n].encode("utf-8")
            self.assertEqual(self.z.read(n), data, n)

    def test_it_refuses_to_overwrite_its_input(self):
        before = self.src.read_bytes()
        r = run(self.src, self.src)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self.src.read_bytes(), before)
        r = run(self.src, self.out)                       # an existing output is never replaced
        self.assertEqual(r.returncode, 2)
        self.assertIn("exists", r.stderr)

    def test_it_refuses_entity_declarations(self):
        parts = sample_parts()
        parts["docProps/core.xml"] = ('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]>'
                                      "<cp:coreProperties>&a;</cp:coreProperties>")
        bad = write_pptx(Path(self.tmp.name) / "bad.pptx", parts)
        dest = Path(self.tmp.name) / "bad-out.pptx"
        r = run(bad, dest)
        self.assertEqual(r.returncode, 2)
        self.assertRegex(r.stderr, "DTD|entit")
        self.assertNotIn("Traceback", r.stderr)
        self.assertFalse(dest.exists())

    def test_a_bad_input_is_a_plain_message(self):
        junk = Path(self.tmp.name) / "junk.pptx"
        junk.write_bytes(b"not a zip")
        r = run(junk, Path(self.tmp.name) / "j-out.pptx")
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("junk.pptx", r.stderr)

    def test_stdlib_only(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), feature_version=(3, 9))
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                mods.add((node.module or "").split(".")[0])
        self.assertLessEqual(mods, {"__future__", "argparse", "posixpath", "re", "sys", "zipfile",
                                    "pathlib"})
        self.assertFalse(str(SCRIPT.relative_to(helpers.KIT)).startswith("template/"),
                         "a maintainer script, never placed in a repo")


if __name__ == "__main__":
    unittest.main()
