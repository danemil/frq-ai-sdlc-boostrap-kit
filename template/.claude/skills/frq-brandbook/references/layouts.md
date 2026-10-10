# The 44 master layouts

From the full master `.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/templates/frq-master.pptx` (44 layouts, 16:9, 10 × 5.625 in; written by the kit owner for frq-4-pptx-agent v1.0 and checked against both templates). **Templates** says where a layout is: *slim and full* (25 layouts, in the slim template, the default) or *full only* (19: the map, event and design layouts). `frq_pptx.py build` takes the full master only when a slide needs a *full only* layout, and says so; a deck on the full master is about 9 MB, on the slim one about 1.2 MB.

Use the name in a spec's `layout` field (case-insensitive, trimmed). Placeholder geometry is in inches: left, top, width × height. The previews stay in the kit copy, not in the placed skill: open them by the exact path given (search tools skip `.ai-sdlc/`). Look at the preview before you use an unfamiliar layout.

Placeholder roles in `frq_pptx.py build`: idx 0 = `title`; idx 2 or 14 = `subtitle`; every other body or object placeholder is a `content` column, left to right; any idx can be set directly with `ph`. List them live with `frq_pptx.py layouts --template full`.

## 1. Standard TITLE

Default title slide: key-visual mosaic, blue band, logo + tagline. `title`, `subtitle` (author, date).

- Placeholders: idx 0 TITLE (0.90, 4.16) 7.72×0.51; idx 2 BODY (0.90, 4.75) 7.73×0.36
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/01-standard-title.jpg](../assets/layouts/01-standard-title.jpg)

## 2. Special topic TITLE

Title with a topic or event picture (set on the master). Use when a dedicated picture exists.

- Placeholders: idx 0 TITLE (2.01, 4.16) 7.24×0.51; idx 2 BODY (2.01, 4.75) 7.25×0.36
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/02-special-topic-title.jpg](../assets/layouts/02-special-topic-title.jpg)

## 3. Headline (standard)

Headline only; free content area for diagrams, processes, timelines.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/03-headline-standard.jpg](../assets/layouts/03-headline-standard.jpg)

## 4. Sub-headline (alternative)

Headline + grey sub-headline; free content area.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31; idx 14 BODY (0.47, 0.63) 9.06×0.31
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/04-sub-headline-alternative.jpg](../assets/layouts/04-sub-headline-alternative.jpg)

## 5. Headline + Categorie

Small section label (idx 14, via `subtitle`) above the headline.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31; idx 14 BODY (0.47, 0.14) 4.53×0.16
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/05-headline-categorie.jpg](../assets/layouts/05-headline-categorie.jpg)

## 6. Headline + field

One content placeholder (bullets, table, chart).

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31; idx 15 OBJECT (0.47, 0.83) 9.06×4.24
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/06-headline-field.jpg](../assets/layouts/06-headline-field.jpg)

## 7. Sub-headline + field

Sub-headline + one content placeholder.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31; idx 14 BODY (0.47, 0.63) 9.06×0.31; idx 16 OBJECT (0.47, 1.02) 9.06×4.02
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/07-sub-headline-field.jpg](../assets/layouts/07-sub-headline-field.jpg)

## 8. Sub-headline + 50:50

Two equal columns (content is placed left to right).

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31; idx 14 BODY (0.47, 0.63) 9.06×0.31; idx 15 OBJECT (5.04, 1.02) 4.49×4.04; idx 16 OBJECT (0.47, 1.02) 4.49×4.04
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/08-sub-headline-50-50.jpg](../assets/layouts/08-sub-headline-50-50.jpg)

## 9. Sub-headline + 33:67

Narrow left, wide right.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31; idx 14 BODY (0.47, 0.63) 9.06×0.32; idx 15 OBJECT (3.58, 1.02) 5.94×4.04; idx 16 OBJECT (0.47, 1.02) 2.99×4.04
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/09-sub-headline-33-67.jpg](../assets/layouts/09-sub-headline-33-67.jpg)

## 10. Sub-headline + 67:33

Wide left, narrow right.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31; idx 14 BODY (0.47, 0.63) 9.06×0.31; idx 15 OBJECT (0.47, 1.02) 5.94×4.04; idx 16 OBJECT (6.54, 1.02) 2.99×4.04
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/10-sub-headline-67-33.jpg](../assets/layouts/10-sub-headline-67-33.jpg)

## 11. Sub-headline + 33:33:33

Three equal columns.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31; idx 14 BODY (0.47, 0.63) 9.06×0.31; idx 15 OBJECT (0.47, 1.02) 2.91×4.04; idx 16 OBJECT (6.61, 1.02) 2.91×4.04; idx 17 OBJECT (3.54, 1.02) 2.91×4.04
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/11-sub-headline-33-33-33.jpg](../assets/layouts/11-sub-headline-33-33-33.jpg)

## 12. Map

World map with sub-headline.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31; idx 14 BODY (0.47, 0.63) 9.06×0.31
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/12-map.jpg](../assets/layouts/12-map.jpg)

## 13. Reference

Customer reference: title = customer + project, idx 13 = challenge, idx 11 = quote or outlook; free content between.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31; idx 13 OBJECT (0.47, 0.63) 9.06×0.33; idx 11 BODY (0.83, 4.42) 8.72×0.66
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/13-reference.jpg](../assets/layouts/13-reference.jpg)

## 14. Reference-DESIGN only

Design sample. Do not use.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31; idx 13 OBJECT (0.47, 0.63) 9.06×0.31; idx 11 BODY (0.83, 4.42) 8.72×0.66
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/14-reference-design-only.jpg](../assets/layouts/14-reference-design-only.jpg)

## 15. 1_Blanc

Blank with the blue edge strip. Rare.

- Placeholders: none (free layout)
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/15-1-blanc.jpg](../assets/layouts/15-1-blanc.jpg)

## 16. Divider blue world

Default chapter divider (gradient + globe). `title` only.

- Placeholders: idx 0 TITLE (1.46, 1.67) 7.22×2.28
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/16-divider-blue-world.jpg](../assets/layouts/16-divider-blue-world.jpg)

## 17. Speaker intro

Blue globe side panel; speaker card or agenda overview. `title`.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/17-speaker-intro.jpg](../assets/layouts/17-speaker-intro.jpg)

## 18. Small Side Bar 1

Narrow blue bar; title right of it. Data-heavy slides. Optional `sidebar_text`.

- Placeholders: idx 0 TITLE (2.36, 0.30) 7.21×0.31
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/18-small-side-bar-1.jpg](../assets/layouts/18-small-side-bar-1.jpg)

## 19. Small Side Bar 2

Narrow blue bar holding the title. Optional `sidebar_text`.

- Placeholders: idx 0 TITLE (0.16, 0.30) 1.93×1.85
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/19-small-side-bar-2.jpg](../assets/layouts/19-small-side-bar-2.jpg)

## 20. Medium Side Bar 1

Medium bar; title right of it. Optional `sidebar_text`.

- Placeholders: idx 0 TITLE (3.74, 0.30) 5.83×0.31
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/20-medium-side-bar-1.jpg](../assets/layouts/20-medium-side-bar-1.jpg)

## 21. Medium Side Bar 2

Medium bar holding the title. Optional `sidebar_text`.

- Placeholders: idx 0 TITLE (0.16, 0.30) 3.27×1.12
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/21-medium-side-bar-2.jpg](../assets/layouts/21-medium-side-bar-2.jpg)

## 22. Wide Side Bar

Wide bar holding title and intro (`sidebar_text`); narrow content column on the right.

- Placeholders: idx 0 TITLE (0.47, 0.30) 5.83×0.31
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/22-wide-side-bar.jpg](../assets/layouts/22-wide-side-bar.jpg)

## 23. Video Background

Full-slide video. Event decks.

- Placeholders: none (free layout)
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/23-video-background.jpg](../assets/layouts/23-video-background.jpg)

## 24. Closing Slide

Always last: globe, logo, tagline. No text.

- Placeholders: none (free layout)
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/24-closing-slide.jpg](../assets/layouts/24-closing-slide.jpg)

## 25. 1_Headline (standard)

Headline variant with a partner-logo picture top right. Only when asked.

- Placeholders: idx 0 TITLE (0.47, 0.30) 7.80×0.31
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/25-1-headline-standard.jpg](../assets/layouts/25-1-headline-standard.jpg)

## 26. Divider

Alternative chapter divider.

- Placeholders: idx 0 TITLE (0.46, 1.62) 9.06×2.30
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/26-divider.jpg](../assets/layouts/26-divider.jpg)

## 27. 1_Agenda

Agenda on gradient with square motif; add content as free text.

- Placeholders: idx 0 TITLE (0.47, 0.30) 5.47×0.32
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/27-1-agenda.jpg](../assets/layouts/27-1-agenda.jpg)

## 28. 4_Headline

Headline only, without the edge strip.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/28-4-headline.jpg](../assets/layouts/28-4-headline.jpg)

## 29. Blanc

Blank. Rare.

- Placeholders: none (free layout)
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/29-blanc.jpg](../assets/layouts/29-blanc.jpg)

## 30. Guidelines

Guidance layout from the tips deck. Do not use for content.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31; idx 14 BODY (0.39, 0.95) 2.76×4.12
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/30-guidelines.jpg](../assets/layouts/30-guidelines.jpg)

## 31. 2_Agenda

Default agenda: title left, numbered agenda points (idx 10).

- Placeholders: idx 10 BODY (3.82, 1.75) 5.83×3.35; idx 0 TITLE (0.47, 1.00) 2.48×0.75
- Templates: **slim and full**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/31-2-agenda.jpg](../assets/layouts/31-2-agenda.jpg)

## 32. Agenda point

Event session page: speaker photo panel + session title.

- Placeholders: idx 0 TITLE (3.90, 1.46) 5.43×2.68
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/32-agenda-point.jpg](../assets/layouts/32-agenda-point.jpg)

## 33. R&D

Event track intro.

- Placeholders: idx 0 TITLE (3.90, 1.46) 5.43×2.68
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/33-r-and-d.jpg](../assets/layouts/33-r-and-d.jpg)

## 34. Teams

Event team intro.

- Placeholders: idx 0 TITLE (3.90, 1.46) 5.43×2.68
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/34-teams.jpg](../assets/layouts/34-teams.jpg)

## 35. Next presentation

Event: next session and presenter(s) (idx 11, 12).

- Placeholders: idx 11 BODY (6.21, 1.36) 3.33×1.12; idx 12 BODY (6.21, 2.78) 3.33×1.12
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/35-next-presentation.jpg](../assets/layouts/35-next-presentation.jpg)

## 36. Break

Event: break type and duration (idx 16), next session (idx 14, 15).

- Placeholders: idx 0 TITLE (0.46, -0.35) 2.63×0.24; idx 14 BODY (6.21, 2.83) 3.33×0.76; idx 15 BODY (6.21, 3.73) 3.33×0.56; idx 16 BODY (6.21, 0.48) 3.33×0.25
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/36-break.jpg](../assets/layouts/36-break.jpg)

## 37. Q&A

Q&A pause before the closing slide (events).

- Placeholders: idx 0 TITLE (6.46, 1.75) 2.94×2.12
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/37-q-and-a.jpg](../assets/layouts/37-q-and-a.jpg)

## 38. World Map

Global footprint; colour countries in the map.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/38-world-map.jpg](../assets/layouts/38-world-map.jpg)

## 39. World Map | Americas

Regional footprint: Americas.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/39-world-map-americas.jpg](../assets/layouts/39-world-map-americas.jpg)

## 40. 1_MAP APAC

Regional footprint: APAC.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/40-1-map-apac.jpg](../assets/layouts/40-1-map-apac.jpg)

## 41. World Map | EMEA

Regional footprint: EMEA.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/41-world-map-emea.jpg](../assets/layouts/41-world-map-emea.jpg)

## 42. 1_World Map | Europe

Regional footprint: Europe / Nordics.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/42-1-world-map-europe.jpg](../assets/layouts/42-1-world-map-europe.jpg)

## 43. World Map | Germany

Country footprint: Germany.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/43-world-map-germany.jpg](../assets/layouts/43-world-map-germany.jpg)

## 44. World Map | UK

Country footprint: UK and Ireland.

- Placeholders: idx 0 TITLE (0.47, 0.30) 9.06×0.31
- Templates: **full only**
- Preview: [.ai-sdlc/kit/template/.claude/skills/frq-brandbook/assets/layouts/44-world-map-uk.jpg](../assets/layouts/44-world-map-uk.jpg)
