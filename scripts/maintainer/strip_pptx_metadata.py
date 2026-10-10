#!/usr/bin/env python3
"""Remove personal and tenant data from a PowerPoint template, keeping everything else.

    python3 -I scripts/maintainer/strip_pptx_metadata.py IN.pptx OUT.pptx

For the kit maintainer, when Group Communications and Marketing ships a new master for the
brand skill (design 2026-10-09 §8.3). Not placed in repos: it lives outside template/.
Python 3.9+, standard library only. It copies the package member by member, in the same
order, and:

- removes ppt/commentAuthors.xml (names and e-mail addresses), docProps/custom.xml
  (sensitivity-label properties with the tenant id), every customXml/ part (SharePoint
  document management) and docProps/thumbnail.jpeg, with their relationships and
  content-type entries;
- empties dc:creator and cp:lastModifiedBy in docProps/core.xml (revision and dates stay);
- reduces docProps/app.xml to the application and the presentation format.

Every other member is copied byte for byte (the slide master, the layouts, the theme and
the media). It never overwrites its input or an existing file, and refuses any part that
declares a DTD or an entity. Exit 0 on success, 2 with a plain message otherwise.
"""
from __future__ import annotations

import argparse
import posixpath
import re
import sys
import zipfile
from pathlib import Path

REMOVED = ("ppt/commentAuthors.xml", "docProps/custom.xml", "docProps/thumbnail.jpeg")
REMOVED_PREFIX = ("customXml/",)
APP_KEEP = ("Application", "PresentationFormat")
APP_NS = ('xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
          'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"')


class StripError(Exception):
    """The input cannot be cleaned (missing, not a zip, a DTD, a part we cannot read)."""


def removed(name: str) -> bool:
    return name in REMOVED or name.startswith(REMOVED_PREFIX)


def text_of(name: str, data: bytes) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise StripError(f"part {name} is not UTF-8") from None
    if re.search(r"<!\s*(DOCTYPE|ENTITY)", text, re.I):
        raise StripError(f"part {name} declares a DTD or an entity; refusing it")
    return text


def rels_source_folder(rels_name: str) -> str:
    """The folder a .rels file's relative targets start from ('_rels/.rels' -> '')."""
    folder = posixpath.dirname(posixpath.dirname(rels_name))
    return folder


def clean_rels(name: str, text: str) -> str:
    base = rels_source_folder(name)

    def keep(m):
        target = re.search(r'\bTarget="([^"]*)"', m.group(0))
        mode = re.search(r'\bTargetMode="External"', m.group(0))
        if not target or mode:
            return m.group(0)
        resolved = posixpath.normpath(posixpath.join(base, target.group(1))).lstrip("/")
        return "" if removed(resolved) else m.group(0)
    return re.sub(r"<Relationship\b[^>]*?/>", keep, text)


def clean_content_types(text: str) -> str:
    def keep(m):
        part = re.search(r'\bPartName="/?([^"]*)"', m.group(0))
        return "" if part and removed(part.group(1)) else m.group(0)
    return re.sub(r"<Override\b[^>]*?/>", keep, text)


def clean_core(text: str) -> str:
    for tag in ("dc:creator", "cp:lastModifiedBy"):
        text = re.sub(rf"<{tag}>[^<]*</{tag}>", f"<{tag}></{tag}>", text)
        text = re.sub(rf"<{tag}\s*/>", f"<{tag}></{tag}>", text)
    return text


def clean_app(text: str) -> str:
    head = re.match(r"\s*<\?xml[^>]*\?>", text)
    keep = []
    for tag in APP_KEEP:
        m = re.search(rf"<{tag}>[^<]*</{tag}>", text)
        if m:
            keep.append(m.group(0))
    return ((head.group(0) if head else '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
            + f"<Properties {APP_NS}>" + "".join(keep) + "</Properties>")


def clean_member(name: str, data: bytes) -> bytes:
    """The bytes to write for one kept member (unchanged unless it is a metadata part)."""
    if name.endswith((".xml", ".rels")):
        text = text_of(name, data)           # every XML part: refuse a DTD, even if unchanged
    else:
        return data
    if name == "[Content_Types].xml":
        new = clean_content_types(text)
    elif name.endswith(".rels"):
        new = clean_rels(name, text)
    elif name == "docProps/core.xml":
        new = clean_core(text)
    elif name == "docProps/app.xml":
        new = clean_app(text)
    else:
        return data
    return data if new == text else new.encode("utf-8")


def strip(src, dest) -> list:
    """Write the cleaned copy of `src` to `dest`; returns the removed member names."""
    src, dest = Path(src), Path(dest)
    if not src.is_file():
        raise StripError(f"{src}: no such file")
    if dest.exists() or dest.resolve() == src.resolve():
        raise StripError(f"{dest} exists; it is never overwritten (and the input never changes)")
    try:
        zin = zipfile.ZipFile(src)
    except (zipfile.BadZipFile, OSError) as exc:
        raise StripError(f"{src}: not a .pptx, or it is damaged ({exc})") from None
    out, gone = [], []
    with zin:
        for info in zin.infolist():
            if removed(info.filename):
                gone.append(info.filename)
                continue
            try:
                data = zin.read(info.filename)
            except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
                raise StripError(f"{src}: part {info.filename} cannot be read ({exc})") from None
            out.append((info, clean_member(info.filename, data)))
    tmp = dest.with_name(dest.name + ".partial")
    try:
        with zipfile.ZipFile(tmp, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
            for info, data in out:
                new = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                new.compress_type = info.compress_type
                new.external_attr = info.external_attr
                zout.writestr(new, data)
        tmp.replace(dest)
    finally:
        if tmp.exists():
            tmp.unlink()
    return gone


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Remove personal and tenant data from a .pptx template.")
    ap.add_argument("src", help="the template as received")
    ap.add_argument("dest", help="the cleaned copy (must not exist)")
    args = ap.parse_args(argv)
    try:
        gone = strip(args.src, args.dest)
    except StripError as exc:
        print(f"strip_pptx_metadata: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {args.dest}; removed {len(gone)} part(s): " + ", ".join(gone))
    return 0


if __name__ == "__main__":
    sys.exit(main())
