# Provenance: sonarqube-findings

Written for this kit (2026-10-10). MIT, like the rest of the kit.

## Ideas from

| Repo | Commit | Licence | Idea taken |
|---|---|---|---|
| [SonarSource/sonarqube-agent-plugins](https://github.com/SonarSource/sonarqube-agent-plugins) | `6142e57738de` | Source-available (not open source): ideas only | Understand the rule before touching the code; read the whole file, not just the flagged line; the minimal change that keeps behaviour; explain what was flagged, why and what changed; for a failed quality gate, report each condition with its metric, threshold and actual value. |

No text was copied from any of them. The upstream skills call a SonarQube server through its CLI and a tool server, and can change issue status; this skill does neither. It reads SonarQube only through the kit's read-only connector (or a report the person pastes or exports), and it adds what the upstream does not cover for this team: SonarQube Community (main branch only), the kit's rules (show before you change, ask before git steps, packages through the company mirror) and the Java 17/21 check.

## Updating

The kit maintainer reviews this skill when the team's SonarQube changes edition or mode (standard or multi-quality), when the quality gate changes, and when the `sonarqube` connector's commands change. Re-check the idea source at a newer commit only for ideas; never copy its text.

## Changes

- 0.10.0 (2026-10-10): reads through the kit's read-only connector when connected; pasted report otherwise.
