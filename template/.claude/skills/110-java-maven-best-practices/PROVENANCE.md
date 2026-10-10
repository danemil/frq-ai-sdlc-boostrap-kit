# Provenance: 110-java-maven-best-practices

| | |
|---|---|
| Upstream repo | https://github.com/jabrena/plinth |
| Path | `skills/110-java-maven-best-practices` |
| Commit | `dca88dc17dc2a86732b3360db201778e51c3a038` (2026-10-07) |
| Folder last changed in | `9569c35d7cf6` (2026-09-26) |
| Taken | 2026-10-10 |
| Licence | Apache-2.0; the upstream `LICENSE` (repo root) is in this folder |

## Files

| File here | Upstream file at that commit | Upstream blob | Changed? |
|---|---|---|---|
| `SKILL.md` | `skills/110-java-maven-best-practices/SKILL.md` | `09f59a3076ff` | Yes, see below |
| `references/110-java-maven-best-practices.md` | `skills/110-java-maven-best-practices/references/110-java-maven-best-practices.md` | `885a464f580b` | Yes, see below |
| `LICENSE` | `LICENSE` | `261eeb9e9f8b` | No |

Upstream has no `NOTICE` file. The skill bundles no scripts. Apache-2.0 section 4(b) asks for a prominent notice in each changed file: both changed files carry a "Changed for this kit" line.

## Local modifications

`SKILL.md`:
- **New section "This kit's copy"**, after the "What is covered in this Skill?" list (before "Constraints"). It starts with the change notice ("Changed for this kit (Apache-2.0, section 4); see PROVENANCE.md.") and has these bullets:
  - **Git.** Never commit, push or merge on its own; follow the person's git-comfort setting and ask before each commit.
  - **Show before you change.** Show the proposed diff or content and wait for a yes; report evidence, not just "Fixed".
  - **Packages only through the company mirror.** No `<repositories>` in a POM, no downloads from the public internet, ask before anything that downloads; load `ai-sdlc-maven-via-artifactory` if it is installed.
  - **Run Maven only after a yes.** `./mvnw` downloads Maven on its first run from `distributionUrl` in `.mvn/wrapper/maven-wrapper.properties`; check that it points at the company mirror, otherwise use the installed `mvn`. A failed resolution means stop and report.
  - **Propose, then apply.** Recommendations are proposed as a diff; nothing in a POM changes before a yes.
- **"What is covered"**: "Explicit repository declaration" became "Repositories through the company mirror (`settings.xml`), never in the POM".
- The frontmatter (`name`, `description`, `license`, `metadata`) is unchanged.

`references/110-java-maven-best-practices.md`:
- **Change notice** after the title: "Changed for this kit (Apache-2.0, section 4): the Goal paragraph, Example 6, the pom.xml section order and the APPLY step. See PROVENANCE.md."
- **Goal paragraph**: its last sentence, "Custom repositories should be declared explicitly and their use minimized, preferably managed via a central repository manager.", became "Dependencies and plugins resolve only through the company mirror (the `settings.xml` mirror of the central repository manager), never through repositories declared in the POM." (Copilot re-test 2026-10-10: it contradicted the mirror-only rule.)
- **Example 6** ("Manage Repositories Explicitly", whose good example declared `<repositories>` in the POM) is replaced by "Resolve Through the Mirror, Never Declare Repositories": the good example is a `settings.xml` mirror with `<mirrorOf>*</mirrorOf>`, the bad example is upstream's POM with a repository; a failed resolution means stop and report. The entry in the examples list is renamed to match.
- **Example 5**: "repositories" removed from the suggested pom.xml section order.
- **Output step**: "**APPLY** Maven best practices directly by implementing" became "**PROPOSE**, as a diff that is applied only after the person says yes (this kit's copy)," and the clause "add missing repository declarations" was removed from that line (it contradicts the mirror rule); the rest of the line is upstream's.

Setup prefixes the name to `ai-sdlc-110-java-maven-best-practices` when it places the skill.

## Updating

Take `SKILL.md`, `references/110-java-maven-best-practices.md` and `LICENSE` from a newer upstream commit, check for a new `NOTICE` file (it would have to be bundled), re-apply the changes above, run `python3 scripts/personal/tests/test_stack_skills.py TestMavenBestPractices`, and update the commit, blobs and date here.
