---
name: maven-via-artifactory
description: 'Get Maven, npm and Go packages only through the company mirror (Artifactory): Maven settings.xml mirrors, .npmrc, GOPROXY; find the versions this repo uses (Java release, Spring Boot, JUnit, Go, React, Jest), and check which versions the mirror has through the read-only artifactory connector when connected. Use first, before adding or upgrading a dependency or any build that downloads, and when the person says "could not resolve", "could not find artifact", "dependency not found", "add a dependency", "upgrade a dependency", "which mirror", "which Java version", "which JUnit".'
license: MIT
---

# Packages through the company mirror

This team has no direct internet access for packages. Every Maven artifact, npm package
and Go module comes from the company's Artifactory. This skill helps you find that
mirror, stay on it, and read the versions the repo already uses, so you never guess.

## Rules

- **Git:** never commit, push or merge on your own. Follow the person's git-comfort setting and ask before each commit.
- **Show before you change:** before editing or creating any file (a new test file too), show the proposed diff or content and wait for a yes; if you can't ask, stop after proposing. Report evidence (the test output), never just "Fixed".
- **The mirror is the only source:** never add a `<repositories>` or `<pluginRepositories>` block to a POM, never point npm or Go at a public registry, and never change the mirror settings yourself.
- **No secrets:** never `cat`, `grep` or print `settings.xml`, `.npmrc`, `.netrc` or similar credential files, in the repo or the home folder. They can hold passwords and tokens. Read the mirrors with the script below (`detect_stack.py`, `--home` for the home folder); it reads only the mirror lines.

## 1. Find the mirror

Run the detector (it only reads files; it runs no tool and uses no network):

```bash
python3 .agents/skills/ai-sdlc-maven-via-artifactory/scripts/detect_stack.py --home
```

The script is [scripts/detect_stack.py](scripts/detect_stack.py). It lists:

- **Maven mirrors** from the repo's `.mvn/settings.xml`, then the person's
  `~/.m2/settings.xml`: id, `mirrorOf` and URL. A mirror with `mirrorOf` `*` takes every
  request.
- **npm registries** from `.npmrc` files in the repo, then `~/.npmrc`, scoped ones too.
- **`GOPROXY`** from the environment.

It never shows a username, password or token, and it cuts them out of URLs. Without
`--home` it reads only the repo. The repo's `.mvn/settings.xml` and `.npmrc` count as much
as the home folder: **never say there is no mirror after looking only in the home
folder.** If neither has one, say what the detector read and ask the person how their
machine reaches Artifactory. Do not invent a URL.

## 2. Resolve only through it

- **Maven:** dependencies and plugins come through the `settings.xml` mirror. A missing
  version is fixed in `<dependencyManagement>` or a property, never by a new repository.
- **npm:** the registry in `.npmrc`. Pin an exact version or a range the team already
  uses; never use `@latest`. Use `npx --no-install` only, so nothing is fetched.
- **Go:** modules come through `GOPROXY`. Pick a version with the person; never use
  `@latest`, and never run `go install` to fetch a tool from the internet.
- **Ask before anything that downloads:** a first `mvn` build, `npm ci`, `go mod download`
  and wrapper scripts (`./mvnw` fetches Maven from `distributionUrl` in
  `.mvn/wrapper/maven-wrapper.properties`). Say what it will fetch and wait for a yes.

## 3. When something does not resolve: stop and report

Errors like "Could not resolve", "Could not find artifact", `E404` or
`410 Gone` from the proxy mean the mirror does not have it, or the person has no access.
Stop and report, in this shape:

- the artifact or package and its version (`group:artifact:version`, `name@version`);
- the mirror URL the build used (from the detector);
- the exact error line.

Then suggest the person asks the Artifactory admins to add or proxy it. Never add a
repository, another registry or a `GOPROXY=direct` to get around it, and never retry
with a different server. A different version that the mirror already has is a fine
proposal, as a diff the person approves.

## 4. Versions this repo uses

Run the detector with `--json` and read these fields. Other skills use them instead of
guessing:

| Field | What it holds |
|---|---|
| `java.build` | `maven`, `gradle` or none |
| `java.release`, `java.release_from` | the Java release (17 or 21 here) and where it was found |
| `java.spring_boot` | the Spring Boot version, or `null`: no Spring Boot is an answer, not a gap |
| `java.junit`, `java.junit_version` | `4`, `5` or `6` (5 and 6 share the Jupiter API) |
| `java.assertj`, `java.mockito`, `java.testfx` | whether the build already has them |
| `java.javafx` | used, where it comes from (`openjfx` or `jdk`), version, evidence |
| `go.go`, `go.toolchain` | the `go` and `toolchain` lines of `go.mod` |
| `node.react`, `node.jest`, `node.testing_library_react`, `node.typescript` | declared ranges |
| `node.locked` | exact versions from `package-lock.json`, when it is there |
| `quality.sonar`, `quality.blackduck` | signs that SonarQube or Black Duck run on this repo |

How to use them:

- Write code for the Java release found. Pattern matching for `switch`, record patterns
  and virtual threads need Java 21; on 17, use the older forms.
- Use the JUnit major the POM has. Do not mix JUnit 4 and Jupiter in new tests, and do
  not migrate old tests unasked.
- Add AssertJ, Mockito or TestFX only if the build already has them, or after the person
  agrees (then the version comes from the mirror, as in section 2).
- When a value is `null`, say it was not found and ask. Do not assume a default.

The detector reads the repo root and three folder levels below it, and skips build
output and `node_modules`. If a module sits deeper, read its POM or `package.json`
directly.

## 5. Adding or upgrading a dependency

1. Read the versions (section 4) and the existing `<dependencyManagement>` or BOM. Before
   you name a new version, run section 6,
   "Check the mirror has the version".
2. Propose the change as a diff: the version in one place (a property or the managed
   section), not repeated in each module.
3. After a yes, and after the person agrees to the download, build or run the tests.
4. If it does not resolve, follow section 3.

## 6. Check the mirror has the version

Use this before any upgrade proposal, also when another skill (for example
`ai-sdlc-blackduck-findings`) found the fixed version.

1. Run `python3 .ai-sdlc/kit/connectors.py artifactory whoami --json`.
2. **Connected** (exit code 0): list the versions the mirror has, with `--json`:
   - Maven: `python3 .ai-sdlc/kit/connectors.py artifactory versions <group:artifact> --json`
   - npm: `python3 .ai-sdlc/kit/connectors.py artifactory npm <package> --json`
   - Go: `python3 .ai-sdlc/kit/connectors.py artifactory go <module> --json`

   Add `--repo <key>` when the person names a repository; otherwise the connector uses the
   default they saved. Then propose only a version in that list, and cite the item's `url`.
   A newer `latest` is not a reason to upgrade on its own.
   Say which version the repo uses now (the POM, or detect_stack output) next to the mirror's list.
3. **The version is not in the list:** say so, and follow section 3 (stop and report; the
   Artifactory admins add or proxy it). Never work around it.
4. **Not connected** (exit code 3) or another error: ask the person to check the mirror's
   web page for that artifact, and say the version is not confirmed. They can connect
   Artifactory themselves: say *connect artifactory*; they type the login in their own
   terminal.
