# Provenance: visual-explainers

Author: the kit owner; unpublished; contributed 2026-10-08.

## Files

`SKILL.md`, `references/patterns.md`, `references/recipes.md`, `references/design-system.md` and `assets/starter.html`, from the owner's own copy of the skill.

## Local modifications

- **Deliver (step 4) is tool-neutral.** The original sent the file with an assistant-specific file-sending tool and, for sharing, published it with an assistant-specific publishing tool (after loading a design skill). This copy saves the file to `docs/explainers/<topic>-explainer.html` in the person's repo (or wherever they ask), shows the file name first, and tells the person the path and how to open it: in a browser, or from VS Code ("Open in browser" or Live Preview). Nothing is uploaded or published.
- The final check says "before you report the path" instead of "before sending".
- The description and the opening lines of `SKILL.md` and `references/patterns.md` no longer name the source gallery the patterns came from.
- **Company brand by default.** One line in step 3: the brand skill's palette, fonts, logo and classification footer replace the design system's unless the person asks for the plain style. The line says to load `ai-sdlc-frq-brandbook`, that it is installed when it is in the skill list, and to read its files by exact path, never deciding by glob or search (the placed folder is hidden from git, so search tools skip it).
- **No prompt panel by default.** Step 3's header, `references/design-system.md` and `assets/starter.html`: the `.prompt-box` echoing the request is added only when the person asks for it (team deliverables leave it out); its CSS stays in the starter.

Everything else (the rest of the frontmatter, steps 1–3 apart from those lines, and the references and the starter page apart from the prompt panel) is unchanged. Setup prefixes the name to `ai-sdlc-visual-explainers` when it places the skill.
