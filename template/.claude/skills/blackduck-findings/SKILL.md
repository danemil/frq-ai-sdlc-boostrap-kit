---
name: blackduck-findings
description: 'Understand and fix Black Duck findings from a report the person pastes or exports: vulnerable components (CVE, BDSA), policy violations, licence risks, and upgrade paths through the company mirror. Read-only. Use when the person says "Black Duck", "BDSA", "vulnerable dependency", "policy violation", "licence risk".'
license: MIT
---

# Black Duck findings (from a report)

Help the person understand what Black Duck found in the project's open-source components and fix it with the smallest safe upgrade. You work only from what they give you: rows copied from Black Duck, or a CSV or JSON file they exported. You never talk to Black Duck yourself.

## Rules

- **Git:** never commit, push or merge on your own. Follow the person's git-comfort setting and ask before each commit.
- **Show before you change:** before editing or creating any file (a new test file too), show the proposed diff or content and wait for a yes; if you can't ask, stop after proposing. Report evidence (the test output), never just "Fixed".
- **Packages only through the company mirror:** never add `<repositories>` to a POM, never use `@latest`, and never run `npx` or `go install` against the public internet. Ask before anything that downloads. Load `ai-sdlc-maven-via-artifactory` (if you have it) to find the mirror and the versions this repo uses.
- **Read-only:** work from the report the person pastes or exports. Never ask for, see or repeat a token or password, and never change anything in the tool: marking a finding as a false positive, accepted or ignored is the person's decision, made in the tool.
- **Only versions the mirror has:** propose an upgrade only to a version that is available in the company mirror. If you cannot confirm it, say so and ask the person to check.
- **Licences are not yours to decide:** explain what a licence asks; the person (and the company's legal or open-source contact) decides.
- **Never `npm audit fix`**, with or without `--force`: it changes many packages at once and can jump major versions. Propose each change yourself, as a diff.

## 1. Ask for the report

If the person has not given you findings yet, ask for rows or an export from the project version in Black Duck: the bill of materials (BOM) or the vulnerability report. The useful columns are:

| Column | Example |
|---|---|
| Component and version | Apache Commons Text 1.9 |
| Origin id (the package coordinates) | `org.apache.commons:commons-text:1.9`, `lodash@4.17.20`, `golang.org/x/net v0.17.0` |
| Vulnerability id | `CVE-2022-42889`, `BDSA-2022-2737` |
| Severity (and score) | Critical 9.8 |
| Policy violated | for example, "no high or critical vulnerabilities" |
| Licence | Apache-2.0, LGPL-2.1, unknown |
| Upgrade guidance, if shown | the fixed-in version, short and long term |

If the origin id is missing, ask for it: a component name alone can match the wrong package. Never ask for a login, an access key or a link that only works with one.

**CVE and BDSA:** a CVE is the public id. A BDSA is Black Duck's own advisory; it often comes earlier or with more detail, and may have no CVE yet. Treat both the same way.

## 2. Find where the component comes from

First decide whether the component is a **direct** dependency (declared in this repo) or **transitive** (brought in by another one). The fix differs.

- **Maven:** look for it in the POMs (and in a parent's `<dependencyManagement>`). If it is not declared, it is transitive. To see which dependency brings it in, `mvn dependency:tree -Dincludes=<groupId>:<artifactId>` helps, but ask first and run it only after a yes: it may download from the mirror.
- **Go:** `go mod why -m <module>` and `go mod graph` show the path. Ask first: they may download modules that are not in the local cache (through `GOPROXY`).
- **npm:** `npm ls <package>` shows the path from `package-lock.json` and `node_modules`; it does not download.

Prefer the locked version (`package-lock.json`, `go.sum`, the resolved tree) over the declared range: that is what Black Duck scanned.

## 3. The smallest upgrade that fixes it

1. **Find the fixed version** from the report (fixed-in or upgrade guidance) or the advisory text the person pastes. Prefer the closest version in the same major line.
2. **Check that the mirror has it.** Ask the person to look it up in the company mirror, or, after a yes, list the versions through the mirror: `npm view <package> versions` (uses `.npmrc`) or `go list -m -versions <module>` (uses `GOPROXY`). For Maven, the person checks the mirror's web page for the artifact.
3. **Check it fits the project:** the Java release (17 or 21), the Spring Boot line if there is one, the Go version in `go.mod`, the Node version. A new major usually means code changes; say so before proposing it.
4. **Propose the change as a diff**, in the right place:

| Ecosystem | Where the fix goes |
|---|---|
| Maven, direct | the version of that dependency (or its property), once, where the repo already manages it |
| Maven, transitive | upgrade the direct dependency that brings it in, if a fixed release exists; otherwise one entry in `<dependencyManagement>` of the parent POM, not a pin in every module |
| Maven with a Spring Boot parent or BOM | override the managed version property (for example `<jackson-bom.version>`) instead of adding a new pin |
| Go | the version in `go.mod` (`go get <module>@<version>` after a yes, then `go mod tidy`); a higher requirement wins for the whole build |
| npm, direct | the version range in `package.json` |
| npm, transitive | upgrade the parent package if a fixed release exists; otherwise an entry in `overrides` in `package.json` |

5. **After a yes, verify:** ask before the build that refreshes the lock file or downloads (`npm install`, the Maven build), then show the resolved version (`npm ls`, the dependency tree, `go list -m`) and the test output.

A new Black Duck scan (from the team's pipeline) confirms the fix. Do not say a finding is closed until it does.

If no fixed version exists, say so and list the options for the person: replace the component, limit the use of the vulnerable part, or accept the risk for now (their decision, recorded in Black Duck).

## 4. Is the vulnerable code used?

Read the advisory (or ask the person to paste it): which function, class or setting is affected. Search the repo for it. Report what you found, with file and line: "used here", "not found in this repo", or "cannot tell" (for example, used through reflection or a framework). This helps the person set the priority; it never replaces the upgrade, and setting a finding to "not affected" or ignored is the person's decision, made in Black Duck.

## 5. Licence risks

For a licence finding, explain in plain words what the licence asks, for example:

- **Permissive** (MIT, BSD, Apache-2.0): keep the copyright and licence notices; Apache-2.0 also has a notice file and a patent clause.
- **Weak copyleft** (LGPL, MPL, EPL): changes to that component itself must be shared under the same licence; how it is linked or bundled matters.
- **Strong copyleft** (GPL, AGPL): shipping it can oblige the team to share the source of the whole program; AGPL also covers use over a network.
- **Unknown or no licence, or "dual" licences:** say what is unclear.

Then hand it to the person: legal or the company's open-source contact decides whether the component may stay. Never say a licence is "fine", "allowed" or "safe". If they decide to replace it, help find an alternative (through the mirror, as in section 3).

## 6. Policy violations

A policy violation names a rule the company set in Black Duck (for example, a severity limit, a banned licence, or a component too old). Say which rule it is, which finding triggers it, and what would clear it (usually the upgrade from section 3). Policy overrides and exceptions are the person's decision, made in Black Duck.

## A short answer per finding

```
commons-text 1.9  (transitive, via my-lib 2.3)   CVE-2022-42889, Critical
Used?   StringSubstitutor.createInterpolator() not found in this repo.
Fix:    my-lib 2.5 brings commons-text 1.10.0 (in the mirror: please confirm).
        Diff for the parent POM below, waiting for your yes.
```

## 7. Later: a connector

A later kit version can read Black Duck directly (a read-only connector). Until then, use only what the person gives you, and never change anything in Black Duck.
