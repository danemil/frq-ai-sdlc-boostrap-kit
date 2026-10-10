#!/usr/bin/env python3
"""Build a new on-brand deck from a short Markdown outline and the bundled template.

    python3 new_deck.py outline.md out.pptx --classification "<the class the person gave>" [--author "Ana Pop"]

--classification is required: ask the person (Frequentis Public, Frequentis General or
Frequentis Confidential) and never guess it. If you cannot ask, pass the literal
"Frequentis [classification to be set]" and say so in the hand-over. build() and
set_footer() check the value too, so calling them from Python cannot skip the question.
Run this file as a command; do not import it (an import leaves a __pycache__ folder in the
placed skill).

Needs python-pptx (run it with ~/.ai-sdlc/venv/bin/python when python3 has no pptx; install
only with the person's consent, as ai-sdlc-doc-powerpoint describes). It never overwrites
a file and never changes the template.

Outline format:

    # Deck title                      -> "Standard TITLE" (the next plain line is the sub-title)
    Ana Pop, 9 October 2026

    ## Slide headline                 -> "Headline + field", or "Sub-headline + field"
    > Optional sub-headline              when a "> " line follows; "Headline (standard)"
    - Bullet                             when the slide has no content
      - Second-level bullet (two spaces)
    1. Numbered item (kept as a bullet; renumber by hand if the order matters)
    A plain line becomes a paragraph. **Bold** and __bold__ markers are removed (the brand
    avoids bold). Tables, code blocks and ### headings are not placed: they are listed on
    stderr, and if a slide would end up with none of its content, nothing is written.

A "Closing Slide" is added at the end (never a "Thank you" slide). Slides are filled by
layout name and placeholder index only: no font, size or colour is set, so the template's
theme applies. The master footer gets the classification, the year and the deck title.
The Markdown front end of frq_pptx.py: it turns the outline into a spec and calls
frq_pptx.build() on the slim template (found in the placed skill or in .ai-sdlc/kit).
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True                         # no __pycache__ in the placed skill

import argparse
import datetime
import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _sibling(name):
    spec = importlib.util.spec_from_file_location(f"frq_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


frq_pptx = _sibling("frq_pptx")                        # the one builder (python-pptx loaded lazily)
CLASSES = frq_pptx.CLASSES
PLACEHOLDER = frq_pptx.PLACEHOLDER                     # when the person could not be asked
ALLOWED = frq_pptx.ALLOWED
TEMPLATE = "slim"                                      # outlines always build on the slim template


def checked_classification(value):
    """The class the person gave, or the placeholder; anything else is refused."""
    return frq_pptx.checked_classification(value)


def plain(text):
    return re.sub(r"(\*\*|__)(.+?)\1", r"\2", text).strip()


def parse(text):
    """(title, subtitle, [(headline, subheadline, [(text, level)], [ignored lines])], [ignored])."""
    title, subtitle, slides, ignored, fence = "", "", [], [], False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip().startswith("```"):
            fence = not fence
            (slides[-1][3] if slides else ignored).append(line)
            continue
        if not line.strip():
            continue
        target = slides[-1][3] if slides else ignored
        if fence or line.lstrip().startswith(("|", "###", "<", "!")):
            target.append(line)
        elif line.startswith("## "):
            slides.append([plain(line[3:]), "", [], []])
        elif line.startswith("# "):
            title = plain(line[2:])
        elif slides and line.startswith("> "):
            slides[-1][1] = plain(line[2:])
        elif slides and re.match(r"^\s*([-*+]|\d+[.)]) ", line):
            indent = len(line) - len(line.lstrip())
            slides[-1][2].append((plain(re.sub(r"^\s*([-*+]|\d+[.)]) ", "", line)), min(indent // 2, 4)))
        elif slides:
            slides[-1][2].append((plain(line), 0))
        elif title and not subtitle:
            subtitle = plain(line)
        else:
            ignored.append(line)
    return title, subtitle, [tuple(s) for s in slides], ignored


def to_spec(title, subtitle, slides, author=None) -> dict:
    """The outline as a frq_pptx.py spec (layouts by name, placeholders filled by the builder)."""
    out = [{"layout": "Standard TITLE", "title": title, "subtitle": subtitle or (author or "")}]
    for headline, sub, bullets, _ in slides:
        items = [{"text": t, "level": lvl} for t, lvl in bullets]
        if not sub and not bullets:
            out.append({"layout": "Headline (standard)", "title": headline})
        elif sub:
            out.append({"layout": "Sub-headline + field", "title": headline, "subtitle": sub,
                        "content": [items]})
        else:
            out.append({"layout": "Headline + field", "title": headline, "content": [items]})
    out.append({"layout": "Closing Slide"})
    return {"title": title, "presenter": f"by {author}" if author else "", "slides": out}


def set_footer(prs, *, classification, year, title, author=None):
    """The master footer, text only (its formatting stays): class, year, title, presenter."""
    classification = checked_classification(classification)
    return frq_pptx.set_footer(prs, classification=classification, year=year, title=title,
                               presenter=f"by {author}" if author else "")


def build(outline, out, *, classification, year=None, author=None, template=TEMPLATE):
    classification = checked_classification(classification)   # before anything is read or written
    year = year or datetime.date.today().year
    title, subtitle, slides, ignored = parse(Path(outline).read_text(encoding="utf-8"))
    if not title:
        raise ValueError("the outline needs a '# Deck title' line")
    lost = ignored + [line for s in slides for line in s[3]]
    if lost:
        print("new_deck: these lines were not placed (add them by hand):\n  " + "\n  ".join(lost),
              file=sys.stderr)
    empty = [s[0] for s in slides if s[3] and not s[2]]
    if empty:
        raise ValueError("nothing of these slides could be placed, so no deck was written: "
                         + ", ".join(empty))
    return frq_pptx.build(to_spec(title, subtitle, slides, author), out, classification=classification,
                          year=year, template=template)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="New on-brand deck from an outline and the bundled template.")
    ap.add_argument("outline")
    ap.add_argument("out")
    ap.add_argument("--classification", choices=ALLOWED, required=True,
                    help="ask the person; never guess it. If you cannot ask: " + repr(PLACEHOLDER))
    ap.add_argument("--year", type=int, default=datetime.date.today().year)
    ap.add_argument("--author")
    args = ap.parse_args(argv)
    if Path(args.out).exists():
        print(f"new_deck: {args.out} exists; choose another name (it is never overwritten)", file=sys.stderr)
        return 2
    try:
        build(args.outline, args.out, classification=args.classification, year=args.year,
              author=args.author)
    except ImportError:
        print("new_deck: python-pptx is missing; with the person's yes, install it into ~/.ai-sdlc/venv as ai-sdlc-doc-powerpoint (section 1) describes", file=sys.stderr)
        return 2
    except (ValueError, KeyError, OSError, frq_pptx.brand_assets.AssetMissing) as exc:
        print(f"new_deck: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {args.out}")
    if args.classification == PLACEHOLDER:
        print(f"new_deck: the footer says '{PLACEHOLDER}': the person sets the class before the "
              "deck is shared", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
