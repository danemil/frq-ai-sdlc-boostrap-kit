# Provenance: java-junit

| | |
|---|---|
| Upstream repo | https://github.com/github/awesome-copilot |
| Path | `skills/java-junit` |
| Commit | `82701c24b99488536ca399ff4789a458b7a05db7` (2026-10-09) |
| Folder last changed in | `caab1f623bb6` (2026-02-24) |
| Taken | 2026-10-10 |
| Licence | MIT, "Copyright GitHub, Inc."; the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit | Upstream blob | Changed? |
|---|---|---|---|
| `SKILL.md` | `skills/java-junit/SKILL.md` | `b5da58d17eb7` | Yes, see below |
| `LICENSE` | `LICENSE` | `89bc5e962c99` | No |

The upstream folder holds only `SKILL.md`. Upstream has no `NOTICE` file. The skill bundles no scripts.

## Local modifications

- **Description.** The one-line `description` keeps upstream's sentence and adds when to use it, with the phrases people type: "write a JUnit test", "test this class", "parameterized test", "@Test", "Mockito". The frontmatter has only `name` and `description`, as upstream.
- **New section "This kit's copy"**, placed before "Project Setup", with these bullets:
  - **Git.** Never commit, push or merge on its own; follow the person's git-comfort setting and ask before each commit.
  - **Show before you change.** Show the proposed diff or content (a new test file too) and wait for a yes; report evidence, not just "Fixed".
  - **Packages only through the company mirror.** No `<repositories>` in a POM, no downloads from the public internet, ask before anything that downloads; load `ai-sdlc-maven-via-artifactory` if it is installed.
  - **Versions first.** Read the JUnit version in the POM: `junit:junit` is JUnit 4, `org.junit.jupiter` is JUnit 5 or 6. JUnit 4 tests are not migrated unasked.
  - **No new libraries unasked.** AssertJ or Mockito only if the POM already has them; otherwise JUnit's own assertions, or ask before adding the dependency.

Nothing else in upstream's text is changed. Setup prefixes the name to `ai-sdlc-java-junit` when it places the skill.

## Updating

Take `SKILL.md` and `LICENSE` from a newer upstream commit, re-apply the description and the section above, run `python3 scripts/personal/tests/test_stack_skills.py TestJavaJunit`, and update the commit, blobs and date here.
