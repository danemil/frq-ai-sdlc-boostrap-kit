"""Text helpers shared by connectors: HTML and Atlassian Document Format to plain text."""
from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser

_BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "pre",
               "blockquote", "table", "ul", "ol", "hr"}
_SKIP_TAGS = {"script", "style"}

# ADF block-level nodes, as in template/scripts/jira/export_jira.py.
_ADF_BLOCKS = {"paragraph", "heading", "blockquote", "codeBlock", "panel",
               "listItem", "bulletList", "orderedList", "rule", "tableRow"}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html, max_chars=None) -> str:
    """Readable text from HTML or Confluence storage format: tags dropped, blank runs folded."""
    if not html:
        return ""
    p = _Text()
    p.feed(str(html))
    p.close()
    lines = [" ".join(line.split()) for line in "".join(p.parts).splitlines()]
    text = "\n".join(line for line in lines if line)
    return text[:max_chars] if max_chars else text


def adf_to_text(node) -> str:
    """Flatten an Atlassian Document Format node (Jira Cloud descriptions) to plain text."""
    if isinstance(node, str):
        return node
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    parts = []
    for child in node.get("content", []) or []:
        text = adf_to_text(child)
        if not text:
            continue
        if parts and isinstance(child, dict) and child.get("type") in _ADF_BLOCKS:
            parts.append("\n")
        parts.append(text)
    return "".join(parts)


def clip(text, max_chars) -> str:
    text = text or ""
    return text if len(text) <= max_chars else text[:max_chars - 1] + "…"


def iso_from_ms(ms) -> str | None:
    """ISO-8601 UTC ('2026-10-08T09:30:00Z') from epoch milliseconds (Bitbucket, Jenkins)."""
    if ms in (None, ""):
        return None
    try:
        dt = datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
