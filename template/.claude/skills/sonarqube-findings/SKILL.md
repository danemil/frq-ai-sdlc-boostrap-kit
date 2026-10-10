---
name: sonarqube-findings
description: 'Understand and fix SonarQube findings from a report the person pastes or exports (rule keys like java:S2095, quality gate failures, security hotspots). Read-only: never changes SonarQube. Use when the person says "Sonar", "quality gate failed", "code smell", "fix this Sonar issue".'
license: MIT
---

# SonarQube findings (from a report)

Help the person understand what SonarQube found and fix it in the code. You work only from what they give you: rows copied from SonarQube, a file they exported, or lines from a CI log. You never talk to SonarQube yourself.

## Rules

- **Git:** never commit, push or merge on your own. Follow the person's git-comfort setting and ask before each commit.
- **Show before you change:** before editing or creating any file (a new test file too), show the proposed diff or content and wait for a yes; if you can't ask, stop after proposing. Report evidence (the test output), never just "Fixed".
- **Packages only through the company mirror:** never add `<repositories>` to a POM, never use `@latest`, and never run `npx` or `go install` against the public internet. Ask before anything that downloads. Load `ai-sdlc-maven-via-artifactory` (if you have it) to find the mirror and the versions this repo uses.
- **Read-only:** work from the report the person pastes or exports. Never ask for, see or repeat a token or password, and never change anything in the tool: marking a finding as a false positive, accepted or ignored is the person's decision, made in the tool.
- **Only what you were given:** do not call the SonarQube server, do not run the scanner, and do not guess findings that are not in the report. Ask before running the build or the tests.
- **One finding, one small fix:** fix what the rule flags and nothing else. No drive-by refactoring, no change in behaviour.

## 1. Ask for the report

If the person has not given you findings yet, ask for one of these:

- **Rows from the issue list** in SonarQube (copied from the page): rule key, file, line, message, severity, and type or software quality. One row per finding is enough.
- **A JSON file they already have** (for example, saved output of the issue search). Read it; do not fetch a fresh one.
- **The scanner or quality-gate lines from a CI log**, for example the `QUALITY GATE STATUS: FAILED` line and the conditions printed with it.
- **Security hotspots** copied from the hotspot page: the category, the file and line, and the "What is the risk?" text.

If something you need is missing (the file path, the line, or which rule), ask for it. Never ask for a login, an access key or a link that only works with one.

## 2. Read a finding

A SonarQube rule key has two parts: the language repository and the rule number. `java:S2095` is the Java rule S2095 ("resources should be closed"). The same number can exist for other languages (`javascript:`, `typescript:`, `go:`).

The report shows the impact in one of two ways, depending on the server's mode:

| Mode | What you see |
|---|---|
| Standard | Type (Bug, Vulnerability, Code Smell) and severity (Blocker, Critical, Major, Minor, Info) |
| Multi-quality | Software quality (Security, Reliability, Maintainability) and severity (Blocker, High, Medium, Low, Info) |

Treat Bugs, Vulnerabilities, Security and Reliability first; code smells and Maintainability after.

If you are not sure what a rule asks, do not guess. Ask the person to open the rule in SonarQube ("Why is this an issue?" and "How can I fix it?") and paste the text.

## 3. For each finding

Work through findings one at a time, in this order:

1. **Read the whole file**, not just the flagged line. The fix depends on how the code around it is used.
2. **Say what the rule means**, in one or two plain sentences.
3. **Say why it matters here**: what could go wrong in this code (a leaked connection, a null at runtime, a value an attacker controls). If the risk is small in this place, say so.
4. **Propose the smallest fix as a diff.** Wait for a yes before you change the file.
5. **Or explain why it may be a false positive**: the rule cannot see something you can (a guard elsewhere, a framework that closes the resource). Give the evidence (file and line). Marking it as a false positive or accepted is the person's decision, made in SonarQube. Do not add `// NOSONAR` or `@SuppressWarnings` unless the person asks for it and the team allows it.
6. **After the change**, ask before running the tests that cover the file, and show their output.

Before you use a newer language feature in a fix, check the Java release this repo builds for (Java 17 and 21 are both in use; `ai-sdlc-maven-via-artifactory`, if you have it, finds it). Pattern matching for `switch` and record patterns need Java 21.

Example: `java:S2095` on a `FileInputStream` opened in a method and closed only on the happy path. The smallest fix is try-with-resources around that stream, nothing else in the method.

### A short answer per finding

```
java:S2095  src/main/java/.../ReportReader.java:42  (Bug, Blocker)
What:   the stream is not closed if read() throws.
Why:    each failed read leaks a file handle; under load the service runs out.
Fix:    try-with-resources around the stream (diff below, waiting for your yes).
```

## 4. Security hotspots

A hotspot is not a confirmed problem: it is code that a person must review (for example, a regular expression on user input, a cookie without `Secure`, a hard-coded IP). For each one:

- Say what the risk would be, and whether this code is exposed to it.
- If it is a real problem, propose the fix as a diff.
- If it is safe, say why, with evidence. Setting the hotspot to safe, fixed or acknowledged is the person's decision, made in SonarQube.

Never treat a hotspot as reviewed because you looked at it.

## 5. The quality gate

When the gate failed, find which **condition** failed. A condition has a metric, a threshold and the actual value. The common ones, on new code:

| Condition | What moves it |
|---|---|
| Coverage on new code below the threshold | Tests for the lines changed since the new-code baseline. Ask which lines are uncovered (the person can copy them from the coverage view). |
| Duplicated lines on new code above the threshold | Extract the repeated block into one method or class. |
| New issues, or a rating worse than A (reliability, security, maintainability) | Fix the new findings behind that rating, worst first. |
| Security hotspots reviewed below 100% | The person reviews each new hotspot in SonarQube (section 4 helps). |

The thresholds belong to the gate the server uses; do not assume them. Read them from the report, or ask.

Say what would make the gate pass, in a short list, and how much work each item is. Do not promise a pass: only the next analysis decides.

## 6. What SonarQube Community does not do

This server runs SonarQube Community. It has **no branch analysis and no pull-request analysis**: only the main branch is analysed. So:

- The findings in the report refer to the main branch as it was at the last analysis, not to the person's branch. Check that the flagged code still looks the same before you fix it.
- A fix shows up in SonarQube only after it lands on the main branch and the next analysis runs.
- "New code" means code changed since the new-code baseline set on the server (a version, a number of days, or a date), not "the code in this branch".

If the person already uses SonarQube for IDE (SonarLint) in their editor, it shows many of the same rules while they type. Do not install it for them.

## 7. Later: a connector

A later kit version can read SonarQube directly (a read-only connector). Until then, use only what the person gives you, and never change anything in SonarQube.
