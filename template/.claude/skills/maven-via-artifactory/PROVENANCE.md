# Provenance: maven-via-artifactory

Written for this kit (2026-10-10). MIT, like the rest of the kit.

Files: `SKILL.md`, `scripts/detect_stack.py` (its tests: `scripts/personal/tests/test_detect_stack.py`
in the kit). The kit's `recommend` step loads the same script from the kit copy, so there
is one detector for the kit and for Copilot.

## Ideas from

| Repo | Commit | Licence | Idea taken |
|---|---|---|---|
| [jfrog/jfrog-skills](https://github.com/jfrog/jfrog-skills) `skills/jfrog-setup-package-managers` | `a27c74da9e36` | Apache-2.0 | On a resolution failure, stop and show the error as it is; never switch to another server. Configuration holds decisions, never credentials. Confirm before a step that sets things up. |
| [decebals/claude-code-java](https://github.com/decebals/claude-code-java) `skills/maven-dependency-audit` | `0d98fe9bd629` | MIT | Read the dependency tree and the managed versions before changing one; keep versions in `<dependencyManagement>` rather than in each module. |

No text was copied from any of them. The detector is new code; neither source has one
like it (the JFrog skill drives the `jf` CLI, which this kit does not use).

## Updating

The kit maintainer reviews this skill when the mirror setup changes (for example a new
Artifactory URL scheme or a Go proxy), when `detect_stack.py` gains a field another skill
needs, and at each kit release. Changes to the script go test-first in
`test_detect_stack.py`, on Python 3.9 and the current Python.

## Changes

- 0.10.0 (2026-10-10): checks the mirror's versions through the kit's read-only `artifactory` connector when connected; the person checks the mirror's page otherwise.
