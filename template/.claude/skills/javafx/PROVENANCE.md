# Provenance: javafx

Written for this kit (2026-10-10). MIT, like the rest of the kit.

Files: `SKILL.md`, `references/testing-and-packaging.md`.

## Ideas from

| Repo | Commit | Licence | Idea taken |
|---|---|---|---|
| [JohannesRabauer/javafx-skills](https://github.com/JohannesRabauer/javafx-skills) | `0a6b8f197f52` | none stated (ideas only) | Choosing between `Task` (one run) and `Service` (reusable); binding UI state to worker properties; bindings for derived values and listeners for side effects. |
| [DongZY0617/javafx-skill](https://github.com/DongZY0617/javafx-skill) | `ddc35f1935a4` | Apache-2.0 (ideas only) | A review checklist for listener and binding leaks (remove or weaken listeners, unbind when a stage closes, static references); `jpackage` per platform needs that platform's tools. |

No text was copied from any of them. The thread, FXML, MVVM/MVCI, TestFX, Monocle and
Zulu FX guidance is the kit's own, written from the JavaFX and TestFX documentation.

## Updating

The kit maintainer reviews this skill at each kit release, when the team moves to a new
JavaFX or JDK major, and when the TestFX or Monocle coordinates change. Check the
`TestJavafx` guard in `scripts/personal/tests/test_stack_skills.py` after any change.
