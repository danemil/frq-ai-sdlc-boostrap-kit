# Provenance: blackduck-findings

Written for this kit (2026-10-10). MIT, like the rest of the kit.

## Ideas from

| Repo | Commit | Licence | Idea taken |
|---|---|---|---|
| [AgentSecOps/SecOpsAgentKit](https://github.com/AgentSecOps/SecOpsAgentKit) `skills/appsec/sca-blackduck` | `6e25a4bc5743` | Not stated: ideas only | The order of remediation options (upgrade, patch, replace, mitigate, accept the risk); handling a transitive dependency by upgrading its parent; licence risk grouped as permissive, weak copyleft and strong copyleft. |
| [OWASP/secure-agent-playbook](https://github.com/OWASP/secure-agent-playbook) `sca-audit` | `1b5fd4cff760` | Not stated: ideas only | Prefer lock files for the exact resolved versions; check whether the vulnerable code path is used before setting a priority; prefer a patch release over a major bump. |

No text was copied from any of them. The upstream skills run scanners (Black Duck Detect, which downloads from the internet, or other tools) and suggest installs; this skill does neither. It works only from a report the person pastes or exports, and it adds what the upstream does not cover for this team: upgrades only to versions in the company mirror (Maven, npm, Go), `<dependencyManagement>` and Spring Boot version properties, npm `overrides`, never `npm audit fix`, and licence and policy decisions left to the person.

## Updating

The kit maintainer reviews this skill when the team changes how it runs Black Duck or its policies, and when the read-only connector arrives (planned for kit 0.10.0): then section 7 points to it and section 1 offers it before asking for a pasted report. Re-check the idea sources at newer commits only for ideas; never copy their text.
