# Connectors for SonarQube, Black Duck and Artifactory (0.10.0) — design

**Status:** approved 2026-10-10 (kit owner, in chat; this file writes that approval up). Points this file adds or decides beyond the approval are listed in §12; the owner confirms them before Task C. Built in three phases, like 0.5.0: A foundation, B1–B3 one connector each (in parallel), C integration, then the Copilot CLI re-test. Plan: [`2026-10-10-connectors-0.10.0-plan.md`](./2026-10-10-connectors-0.10.0-plan.md). Target release: **0.10.0** (MINOR: three new connectors and a new kind of suggestion).
**Extends:** [connectors design](./2026-10-08-connectors-design.md) (the framework: one module per connector, `setup.py connect`, `connectors.py`, read-only, secrets only in the person's own terminal). Everything there still holds unless this file says otherwise.
**Related:** [stack pack design](./2026-10-09-stack-pack-design.md) §3 (the skills `sonarqube-findings`, `blackduck-findings`, `maven-via-artifactory`), §5 (detection signals `sonar`, `blackduck`, `code`, and the rules in `roles/recommend.json`), §6 (teams, future), §9 (connectors deferred to 0.10.0).

## 1. Problem

In 0.9.0 the skills `sonarqube-findings` and `blackduck-findings` work only from a report the person pastes. That is slow, and a pasted report is often old or cut short. `maven-via-artifactory` cannot check which versions the company mirror really has, so an upgrade proposal can name a version the build will not find.

The FRQ teams use SonarQube Community, Black Duck and a self-hosted Artifactory. All three have a REST API that a person's own token can read. The 0.5.0 connector framework already does the hard parts (per-user secrets, proxy, CA bundle, read-only client). So 0.10.0 adds three connectors to it and lets the skills use them.

## 2. Decisions

| # | Question | Decision |
|---|---|---|
| 1 | Which tools? | **Three new read-only connectors:** `sonarqube`, `blackduck`, `artifactory`. Same framework as 0.5.0: one module each in `scripts/personal/connectors/`, found by the glob; no shared file changes to add one. |
| 2 | Who types the secret? | The person, in their own terminal: `python3 .ai-sdlc/kit/setup.py connect <name>`. Unchanged. |
| 3 | Read or write? | **Read-only.** Data reads are GET only. The one POST in 0.10.0 besides Jama's is Black Duck's token exchange, made inside the auth object (§3.2). A test proves a connector command cannot send a POST. |
| 4 | Output | `connectors.py <name> <command> [args] [--json]`, the same envelope as 0.5.0. **Every item carries `url`**, a browser link where one exists. |
| 5 | Corporate network | CA bundle and proxy exactly as 0.5.0. TLS verification is never switched off. |
| 6 | Secrets in output | Never echoed, logged or put in an exception. This includes a token sent as a Basic user name (SonarQube) and a bearer token got from an exchange (Black Duck). |
| 7 | SonarQube versions | The server version is read once per run; the old (`severity`, `type`) and the new (`impacts`, `cleanCodeAttribute`) issue shapes map to one output; `--severity` and `--type` are translated per version (§5). |
| 8 | Role defaults | dev adds `sonarqube`, `blackduck`, `artifactory`; qa adds `sonarqube`; architect adds `sonarqube`, `blackduck` (§6.1). |
| 9 | Suggestions from the repo | New **connector rules** in `roles/recommend.json`: `sonar` → `sonarqube`, `blackduck` → `blackduck`, `code` → `artifactory`, for anyone, only when the tool is not in the person's role defaults and not connected. Declines are remembered like skill declines (§6.2). |
| 10 | Skills | `sonarqube-findings` and `blackduck-findings` read through the connector when it is connected, else ask for a pasted report (the 0.9.0 way). `maven-via-artifactory` checks the mirror's versions with the `artifactory` connector before it proposes an upgrade; `blackduck-findings` uses it too for the fix version (§7). |
| 11 | Out of scope | Writes of any kind; AQL (it is a POST); SharePoint; SonarQube branch or pull-request analysis (Community has none). |

## 3. Auth per connector

| Connector | Fields | Auth |
|---|---|---|
| `sonarqube` | `url`; `token` (secret: "user token") | The token as the **Basic user name with an empty password** (`Authorization: Basic base64("<token>:")`). This works on SonarQube 9.x up to 2025.x. |
| `blackduck` | `url`; `token` (secret: "API token") | **Token exchange, once per run** (§3.2): `POST <url>/api/tokens/authenticate` with `Authorization: token <API token>` gives a `bearerToken` that lives about two hours (`expiresInMilliseconds`); then `Authorization: Bearer <bearerToken>` on every GET. Each endpoint gets its own vendor `Accept` media type (§4.2). |
| `artifactory` | `url` (with the `/artifactory` context path, e.g. `https://artifactory.example.com/artifactory`); `token` (secret: "access token or identity token"); optional `maven_repo`, `npm_repo`, `go_repo` (the default repository key for each command) | `Authorization: Bearer <token>`. |

Every connector also has the optional `ca_bundle` field that the registry adds. None of the three has an `identity` field: `connections` shows the user from the last `--test` (the 0.5.0 fallback `last_test.user`).

### 3.1 The SonarQube token as a user name

`http.basic(token, "")` builds the right header, but `Basic.secrets()` returns the password (empty here) and the encoded value, **not the user name**. An error that quoted the token would not be scrubbed. So `http.py` gets a small auth `token_as_user(token)`: the same header, and `secrets()` returns the token and the encoded value. SonarQube 10.0+ also accepts `Authorization: Bearer <token>`; we do not use it, because 9.x does not.

### 3.2 Token exchange in `http.py` (design point 1)

Today `Client._send` refuses every method but GET, except a POST when the client's auth is an `OAuthClientCredentials`. Black Duck needs the same kind of exception. Instead of a second special case, `http.py` gets one base class:

```
class TokenExchange(Auth):
    token_path: str              # the one path this auth may POST to
    def exchange_request(self) -> (headers, body, content_type, accept)
    def parse(self, data) -> (token, expires_in_seconds)
    def unauthorized_message(self, host) -> str
    # shared: headers() fetches the token when missing or expired (30 s early),
    # caches it, sends "Authorization: Bearer <token>"; secrets() lists the
    # long-lived secret and the current token.
```

- `OAuthClientCredentials` (Jama) becomes a subclass: same request, same parse (`access_token`, `expires_in`), same messages. Its behaviour and tests do not change.
- `BlackDuckToken` is the second subclass: `Authorization: token <API token>`, empty body, `Accept: application/vnd.blackducksoftware.user-4+json`; parse `bearerToken` and `expiresInMilliseconds / 1000`. A 401 says "the API token was not accepted (check it, and that it is not expired or revoked)".
- **The POST gate.** `_send` accepts a POST only from a private method `Client._exchange(auth)`, only when `auth` is a `TokenExchange` and only to `auth.token_path`. `Client.get*` and `paginate` stay GET-only. Connector code never calls `_send` or `_exchange`.
- **The proof.** Tests show: a command that calls `ctx.client._send("POST", …)` gets `ConnectorError(kind="config")`, also with a token-exchange auth; a POST to any path other than `token_path` is refused; and a static test reads every connector module (not the foundation) and finds no `_send`, `_exchange`, `"POST"`, `urllib` or `http.client`.
- `http.token_exchange` is the public name for the base class; `http.blackduck_token(token)` builds the Black Duck auth (it lives in `http.py`, not in `blackduck.py`, because the POST gate must be able to trust it).

## 4. Command surface

Data: `python3 .ai-sdlc/kit/connectors.py <connector> <command> [args] [--json]`, exit codes as 0.5.0 (0 ok, 1 error, 2 usage, 3 not connected). Endpoints, arguments and JSON shapes per command are in the plan (Tasks B1–B3).

| Connector | Commands |
|---|---|
| `sonarqube` | `whoami` · `gate <project>` · `issues <project> [--severity …] [--type …] [--rule KEY] [--file PATH] [--new-code] [--limit N]` · `hotspots <project> [--status TO_REVIEW\|REVIEWED] [--limit N]` · `measures <project> [--metrics a,b]` · `rule <key>` |
| `blackduck` | `whoami` · `projects <text> [--limit N]` · `versions <project> [--limit N]` · `vulns <project> <version> [--severity …] [--limit N]` · `components <project> <version> [--violations] [--limit N]` · `policy <project> <version>` |
| `artifactory` | `whoami` · `repos [--type maven\|npm\|go\|…]` · `versions <group:artifact> [--repo KEY]` · `latest <group:artifact> [--repo KEY]` · `npm <package> [--repo KEY]` · `go <module> [--repo KEY]` |

### 4.1 SonarQube

| Command | Endpoint | Notes |
|---|---|---|
| `whoami` | `GET /api/users/current` | `isLoggedIn: false` means the token was not accepted: a 401-style `ConnectorError(kind="unauthorized")`. |
| `gate` | `GET /api/qualitygates/project_status?projectKey=` | The status and the **failed** conditions first (metric, comparator, threshold, actual value), then all conditions. |
| `issues` | `GET /api/issues/search` | Open issues only (`resolved=false`). Paged with `p` and `ps`. SonarQube never returns more than **10,000** issues for one search: the connector stops there and says `truncated`, with a hint to narrow the filter. |
| `hotspots` | `GET /api/hotspots/search?project=` | Default status `TO_REVIEW`. |
| `measures` | `GET /api/measures/component?component=&metricKeys=` | A default metric list when `--metrics` is not given; the new-code values apart. |
| `rule` | `GET /api/rules/show?key=` | The rule text as plain text (from the HTML description or its description sections), clipped. |

`<project>` is the **project key**. The skill finds it in the repo (§7.1) or asks.

### 4.2 Black Duck

| Command | Endpoint | Accept (vendor media type) |
|---|---|---|
| `whoami` | `GET /api/current-user` | `application/vnd.blackducksoftware.user-4+json` |
| `projects` | `GET /api/projects?q=name:<text>` | `application/vnd.blackducksoftware.project-detail-4+json` |
| `versions` | the project's `versions` link | `application/vnd.blackducksoftware.project-detail-5+json` |
| `vulns` | the version's `vulnerable-components` link (path `…/vulnerable-bom-components`) | `application/vnd.blackducksoftware.bill-of-materials-6+json` |
| `components` | the version's `components` link (`filter=bomPolicy:in_violation` with `--violations`) | `application/vnd.blackducksoftware.bill-of-materials-6+json` |
| `policy` | the version's `policy-status` link | `application/vnd.blackducksoftware.bill-of-materials-6+json` |

- Projects and versions are given **by name**. The connector finds the project (exact name, case-insensitive, among the `q=name:` results; several or none → a plain error that lists the candidates) and the version (`q=versionName:`), then follows the `_meta.links` hrefs. It never builds an id path by hand when the server gave a link.
- `vulns` shows each vulnerability with its id (`CVE-…` or `BDSA-…`), its source, severity and score, the component, its version and origin, the remediation status, and **`fixed_in`**. The vulnerable-components answer has no fix version, so the connector reads the component version's **upgrade guidance** (`GET /api/components/{c}/versions/{v}/upgrade-guidance`, `application/vnd.blackducksoftware.component-detail-5+json`) once per distinct component version, at most 50 per run; `fixed_in` is `{short_term, long_term}` (version names) or `null`. Field names: §9.
- Paging: `offset` and `limit`, `totalCount`, items under `items` (the 0.5.0 `Offset` preset with those names).
- `--severity` filters on the client side (critical, high, medium, low); no server filter is assumed.

### 4.3 Artifactory

| Command | Endpoint | Notes |
|---|---|---|
| `whoami` | decode the token locally, then `GET /api/system/version` | An access token is a JWT; its `sub` claim looks like `jfrt@<service id>/users/<name>` (or `jfac@…`). The user is the part after `/users/`. Decoding does not prove the token works, so one GET confirms it (a bad token gives 401). A non-JWT (reference) token gives `user: null` and still passes when the GET passes. |
| `repos` | `GET /api/repositories?packageType=<type>` | `key`, type (local, remote, virtual), package type, description. |
| `versions` | `GET /<repo>/<group as path>/<artifact>/maven-metadata.xml` | Parsed with `xml.etree` (stdlib). A file with a `DOCTYPE` or entity declaration is refused (the 0.9.0 rule). Versions, `latest`, `release`, `lastUpdated`. |
| `latest` | `GET /api/search/latestVersion?g=&a=&repos=` | Plain text: one version. |
| `npm` | `GET /api/npm/<repo>/<package>` | A scoped name `@scope/name` is sent as `@scope%2fname`. `dist-tags` and the version list (with publish times when the answer has them). |
| `go` | `GET /api/go/<repo>/<module>/@v/list` | Plain text, one version per line. The module path is case-encoded the Go way (`A` → `!a`). |

- **No AQL.** AQL search is a POST, so the connector cannot use it (decision 3).
- **The repository.** `--repo` wins; else the saved `maven_repo` / `npm_repo` / `go_repo`; else a plain error: "Give --repo, or save a default with connect artifactory (the repo key, e.g. maven-virtual)".
- **The item link.** Artifactory's web UI lives at the host root (`<host>/ui/repos/tree/General/<repo>/<path>`), not under `/artifactory`. The connector builds it from the saved URL without its `/artifactory` part. To confirm (§9).

## 5. SonarQube versions (design point 2)

SonarQube 10.2 replaced the issue fields `severity` and `type` with `impacts` (a list of `{softwareQuality, severity}`) and `cleanCodeAttribute`. Some servers send both. The connector:

1. Reads `GET /api/server/version` (plain text, e.g. `9.9.4.87374` or `10.6.0.92116`) **once per run**, cached on the `Context`. If it cannot be read, it assumes the newer API and says so in `extra.server_version: null`.
2. Maps both answer shapes to **one output**: `severity` and `type` (the old fields, or `null`), `impacts` (a list, empty when the server has none), and `clean_code_attribute` (or `null`). When the server sends both shapes, both are kept.
3. Translates the filters per version, and **says what it sent** (`extra.filter_sent`), so the person can check it:

| `--severity` value | Server below 10.2 (`severities=`) | 10.2 and newer (`impactSeverities=`) |
|---|---|---|
| `blocker` | `BLOCKER` | `BLOCKER` on 2025.1+, else `HIGH` |
| `critical` | `CRITICAL` | `HIGH` |
| `major` | `MAJOR` | `MEDIUM` |
| `minor` | `MINOR` | `LOW` |
| `info` | `INFO` | `INFO` on 2025.1+, else `LOW` |
| `high` | `BLOCKER,CRITICAL` | `HIGH` |
| `medium` | `MAJOR` | `MEDIUM` |
| `low` | `MINOR,INFO` | `LOW` |

| `--type` value | Below 10.2 (`types=`) | 10.2 and newer (`impactSoftwareQualities=`) |
|---|---|---|
| `bug` / `reliability` | `BUG` | `RELIABILITY` |
| `vulnerability` / `security` | `VULNERABILITY` | `SECURITY` |
| `code_smell` / `maintainability` | `CODE_SMELL` | `MAINTAINABILITY` |

The mapping is not exact (the two models do not line up one to one), which is why `filter_sent` is in the output. Security **hotspots** are not issues in either model; they have their own command.

Other version differences, handled in one helper each: the component parameter (`componentKeys` below 10.2, `components` from 10.2); the new-code filter (`inNewCodePeriod=true`; `sinceLeakPeriod=true` below 9.4 is not supported: the kit's floor is 9.x LTS); the issue status (`status` below 10.4, `issueStatus` from 10.4, both read).

## 6. Suggestions (design point 3)

### 6.1 Role defaults

`roles/<id>/role.json` `connectors`, new names appended (order is the order of suggestion):

| Role | Connectors (0.10.0) |
|---|---|
| core | — |
| po, pm | jira, confluence, jama |
| sm | jira, confluence |
| dev | bitbucket, jira, jenkins, **sonarqube, blackduck, artifactory** |
| qa | jira, jama, jenkins, **sonarqube** |
| architect | confluence, bitbucket, jira, **sonarqube, blackduck** |
| em | jenkins, bitbucket, jira |

`packs.validate` accepts a connector name only when the registry finds the module in the kit's `scripts/personal/connectors/`. So the three names validate as soon as the B modules are merged; the role packs change in Task C, after the merges (before that, validation would fail).

### 6.2 Connector suggestions from the repo

Anyone may need a tool their role does not usually use: a PO in a repo with a Sonar quality gate, a QA lead whose repo is scanned by Black Duck. So the detection of 0.9.0 also suggests **connectors**.

**Rules are data**, in `roles/recommend.json`, next to the skill rules, with a new action:

```json
{"connector": "sonarqube", "action": "connect", "when": ["sonar"], "reason": "this repo is analysed by SonarQube"}
{"connector": "blackduck", "action": "connect", "when": ["blackduck"], "reason": "this repo is scanned by Black Duck"}
{"connector": "artifactory", "action": "connect", "when": ["code"], "reason": "this repo downloads packages; the connector checks which versions the company mirror has"}
```

- The id is `connect:<connector>`. One rule per id.
- A `connect` rule has `connector`, `when` and `reason`, and may have `roles` (none = for anyone, which is what 0.10.0 ships). It has no `skill`, `unless` or drop form.
- It **fires** when one of its signals is found **and** the connector is **not in the person's role defaults** (those are suggested already, by the "Connectors for your roles" line). It is **open** (shown as a suggestion) only when the person has **not connected** it, has **not declined** it, and it is not in `skipped_connectors` (a skip from `connect --suggested` counts as a no).
- `packs.validate` (through `recommend.validate`) checks: a known connector (registry), known signals, known roles, a reason of 1 to 120 characters, no `skill` key, and that no connector name equals a skill name (so `--decline <name>` can never be read two ways).

**Deterministic.** Rules are applied in a fixed order (by connector name), and the output order is fixed. The list depends on the repo's files, the person's choices (`state.json`) and **one fact from this computer**: whether a login is saved for that connector (`manage.is_connected`; it reads the saved fields' presence, never prints a value). That fact is passed in as a set, so the engine itself reads no home folder and tests control it. This is a small change from 0.9.0 §5.1 ("never the person's home folder"); see §12 item 2.

**How it shows.**

- `setup.py recommend` prints a second part after the skill suggestions, only when there is an open connector suggestion:

  ```text
  Tools to connect for this repo (from its files; you type the login yourself, in your own terminal):
  1. connect:sonarqube — SonarQube: this repo is analysed by SonarQube (sonar-project.properties).
  To connect one: python3 .ai-sdlc/kit/setup.py connect <name>   (in your own terminal), or all of them with connect --suggested
  To say no: python3 .ai-sdlc/kit/setup.py recommend --decline connect:sonarqube   (or the tool name)
  ```

  Declined ones are listed under "Declined earlier" with the connect command. With no skill suggestion and no connector suggestion, the output is the 0.9.0 line "No skill suggestions for this repo." unchanged.
- `recommend --decline` takes `connect:<name>` or the plain connector name. **`--decline all` still means the open skill suggestions only**, so onboarding step 8 (skills) cannot decline a tool before step 11 offers it. `--decline all-tools` declines every open connector suggestion.
- `recommend --json` gains a key: `{"suggestions": [...], "connectors": [...], "others": [...]}`. Each connector item has exactly `id`, `action` (`"connect"`), `connector`, `title`, `reason`, `evidence`, `declined`, `connected`. The two old keys are unchanged.
- **Summary line.** `setup`, `update` and a roles change add, after the skill-suggestion line: `- Tools to connect for this repo: sonarqube (say 'connect sonarqube')` when there are open connector suggestions. Like the skill line, `update` shows only new ones (declined ones stay declined).
- **`connect --suggested`** offers the role defaults first (as now), then the open connector suggestions, each with its reason: `Connect SonarQube now? It fits this repo: this repo is analysed by SonarQube. [y = yes, s = skip, a = skip all the rest; Enter = skip]`, then "Connect another tool?". A skipped role default goes to `skipped_connectors` (as now); a skipped repo suggestion is **declined** (`connect:<name>` in `declined_recommendations`), like a skill decline. `connect <name>` that saves a login clears both.
- **Onboarding.** Step 10 names the tools from both lines ("Connectors for your roles" and "Tools to connect for this repo"), each repo tool with its reason in one plain sentence. Step 11 is unchanged in shape (one offer, the person runs `connect --suggested` in their own terminal). If the person says "not now" in step 11, Copilot runs `recommend --decline all-tools` (the repo tools are declined; the role tools stay as they are today), and says they can say "connect <tool>" at any time. "Recommend skills" (the section) relays connector suggestions too.

## 7. The skills switch (design point 4)

All three skills keep the 0.9.0 rules. What changes:

### 7.1 `sonarqube-findings`

- New first step, **"Connected?"**: run `python3 .ai-sdlc/kit/connectors.py sonarqube whoami --json`. Exit 0: read with the connector. Exit 3 (not connected): work from a pasted report as in 0.9.0, and say once that the person can connect SonarQube themselves ("say *connect sonarqube*"). Any other error: relay it with the `ai-sdlc-connectors` table, then fall back to a pasted report.
- **The project key**: `sonar.projectKey` from `sonar-project.properties`, or the POM property `sonar.projectKey`, read **by that key only** (`grep -E '^\s*sonar\.projectKey' sonar-project.properties`); never print the whole file, because it can hold `sonar.login` or `sonar.token`. Not found: ask.
- **Read with the connector**: `gate <project>` for "quality gate failed"; `issues <project> --file <path>` or `--rule <key>` for one finding; `--new-code` for the gate's new-code conditions; `hotspots <project>`; `rule <key>` instead of asking the person to paste the rule text. Cite each item's `url`.
- The read-only rule becomes: "work from the connector's output or from a report the person gives you … never change anything in the tool". Marking a finding stays the person's decision, in SonarQube.
- Section 7 "Later: a connector" is replaced by the connector use above.

### 7.2 `blackduck-findings`

- The same "Connected?" step with `connectors.py blackduck whoami --json`, and the same fallback.
- **Project and version names**: ask the person, or read `detect.project.name` and `detect.project.version.name` from the repo **by key only** (the same files can hold `blackduck.api.token`). Then `vulns <project> <version>`, `policy <project> <version>`, `components <project> <version> --violations`.
- **The fix version**: take `fixed_in` from `vulns`; then, before proposing it, check the mirror (§7.3). Never propose a version the mirror lacks.
- Section 7 "Later: a connector" is replaced.

### 7.3 `maven-via-artifactory`

- New section **"Check the mirror has the version"**, used before any upgrade proposal: if `connectors.py artifactory whoami --json` works, run `versions <group:artifact> --json` (Maven), `npm <package> --json` or `go <module> --json`, and propose **only a version in that list**. If it is not connected, keep the 0.9.0 way: ask the person to check the mirror's page, and say the version is not confirmed.
- A version missing from the list: say so, and follow section 3 (stop and report, ask the Artifactory admins). Never work around it.

### 7.4 Routing and the connectors skill

- `roles/dev/instructions.md`, `qa`, `architect`: one line each: "SonarQube findings or a failed quality gate: `ai-sdlc-sonarqube-findings` (if you have it), which reads through the `sonarqube` connector when it is connected"; dev and architect also the Black Duck line; dev: "Before proposing a dependency version: check it with the `artifactory` connector (`ai-sdlc-maven-via-artifactory`)".
- `roles/core/instructions.md` "Connectors" line names the eight tools.
- `ai-sdlc-connectors`: the description names the three new tools (still at most 1,024 characters); the command table gets three rows; the role table matches §6.1 (a test already ties them); a short part "Tools for this repo" says that `recommend` may suggest a tool for the repo, and that the person connects it in their own terminal.

No Copilot-facing file names the client, the kit owner's employer or any vendor company. Product names (SonarQube, Black Duck, Artifactory) are fine, as Jira and Jenkins are today.

## 8. Architecture

```
connectors.py <name> <command> ──► registry.py ──► connectors/{sonarqube,blackduck,artifactory}.py
                                                          │
                                                   connectors/http.py
                                     GET client · Bearer · Basic · token_as_user (new)
                                     TokenExchange (new base) ─► OAuthClientCredentials (Jama)
                                                              └► BlackDuckToken (new)
setup.py recommend / setup / update / connect --suggested ──► recommend.py (connector rules, new)
                                                          └► commands.py, connectors/manage.py
```

- `http.py` (Task A): `token_as_user`, `TokenExchange`, `blackduck_token`, the POST gate, `Response.text()` used for plain-text answers (SonarQube version, Artifactory `latest` and Go list), and a `max_bytes` cap on `get_text` (exists).
- `recommend.py` (Task A): `connector_items(kit, root, st, all_packs, connected)`; `compute()` keeps returning skill items only (callers and its tests unchanged); `validate()` learns the `connect` action.
- `commands.py` / `manage.py` (Task A): the `recommend` output part, `--decline all-tools` and connector names, the summary line, `connect --suggested` with the repo suggestions after the role defaults.
- One module and one test file per connector (B1–B3); nothing else changes in a B task.

## 9. Needs live confirmation (like 0.5.0 §5.1)

Built and tested against canned answers in each vendor's documented shape. These points cannot be checked without a live server. Until confirmed, treat a surprise here as a likely cause before suspecting the person's setup. Each B task notes them in its test file; the Copilot re-test (plan Task D) checks the ones it can.

- **SonarQube:**
  - `GET /api/users/current` returns `isLoggedIn: false` (not a 401) for a bad token on the client's version.
  - The **token as Basic user name** with an empty password on the newest version the client runs (2025.x); Bearer is the fallback if not.
  - The **impacts field names**: `impacts[].softwareQuality`, `impacts[].severity`, `cleanCodeAttribute`; the filter parameters `impactSeverities`, `impactSoftwareQualities`; `BLOCKER` and `INFO` impact severities from 2025.1.
  - `components` versus `componentKeys` at the client's version; `issueStatus` from 10.4.
  - The 10,000-issue cap answer (a 400 past it, or an empty page).
  - The default metric keys of `measures` on 10.x and 2025.x (some were renamed `software_quality_*`).
- **Black Duck:**
  - The **media types** per endpoint (§4.2), especially `bill-of-materials-6` and `component-detail-5`; an older server may want lower numbers.
  - The token-exchange answer field names `bearerToken` and `expiresInMilliseconds`.
  - The vulnerable-components field names: `vulnerabilityWithRemediation.vulnerabilityName`, `.source`, `.severity`, `.overallScore` (or `baseScore`), `.remediationStatus`; the origin fields (`componentVersionOriginId`, `componentVersionOriginName`).
  - The **upgrade guidance** path and its fields (`shortTerm.versionName`, `longTerm.versionName`) used for `fixed_in`.
  - That the web UI uses the same `/api/projects/<id>/versions/<id>/…` paths as the API, so `_meta.href` (+ `/vulnerability-bom` or `/components`) is a working browser link.
  - `filter=bomPolicy:in_violation` on the components endpoint.
- **Artifactory:**
  - The **JWT `sub` format** (`jfrt@…/users/<name>` or `jfac@…/users/<name>`) for the client's token type (access token, identity token); reference tokens (not a JWT) give no user.
  - The **identity endpoint**: that `GET /api/system/version` answers 401 for a bad token when anonymous access is on. If not, a better read-only call that needs a login.
  - The **Go list endpoint path** `/api/go/<repo>/<module>/@v/list` (some set-ups serve it as `/<repo>/<module>/@v/list`), and the case-encoding of module paths.
  - `GET /api/search/latestVersion` on the client's edition (it may need a Pro licence; `versions` then gives `release` from `maven-metadata.xml`).
  - For a **remote or virtual** repository, which versions `maven-metadata.xml` lists (cached only, or the upstream's too).
  - The web UI link form `<host>/ui/repos/tree/General/<repo>/<path>`.

## 10. Testing

- `test_connectors_foundation.py` (Task A): `token_as_user` header and scrubbing; `TokenExchange` (fetched once, reused, refreshed on expiry, 401 message); Jama's suite unchanged and green; the POST gate (a command cannot POST, a POST to another path is refused, a GET-only auth cannot POST); the static scan of connector modules.
- `test_recommend.py`, `test_connect_suggested.py`, `test_packs.py`, `test_cli.py` (Task A): connector rules (fires; not for a role default; not when connected; not when skipped or declined; order), validation errors, `recommend` text and `--json`, `--decline connect:x`, `--decline <name>`, `--decline all` leaves connector items open, `--decline all-tools`, the summary line, `connect --suggested` offers repo tools after role defaults and records a skip as a decline. A test kit with a stub connector stands in for the B modules.
- `test_connector_sonarqube.py`, `test_connector_blackduck.py`, `test_connector_artifactory.py` (B1–B3): the 0.5.0 shape (registry validates; fields; auth header on a recorded request; each command's path, query and exact output keys; paging and `truncated`; a 404; one `run_cli … --json`; the secret absent from all output), plus each connector's own cases (plan).
- Task C: `test_roles.py`, `test_skill_guidance.py`, `test_stack_skills.py` (the read-only rule wording, the connector step), `test_onboarding.py`, `test_connectors_e2e.py` and `tests/fake_tools.py` for the three tools, `test_release.py`.
- Python 3.9 floor; every suite on `python3` and `/usr/bin/python3`; stdlib only; no network (fake servers on 127.0.0.1).
- **Manual, before merge:** the owner re-tests with the Copilot CLI on the VM (plan Task D).

## 11. Out of scope and open

- **Out of scope:** writes of any kind (marking a Sonar issue, a Black Duck override, deploying to Artifactory); AQL; Artifactory PyPI, Docker and other package types (only `repos` lists them); SonarQube branches and pull requests (Community has none); Black Duck scans (Detect); **SharePoint** (still out of scope until Online or on-premises is known); teams (stack pack §6, later).
- **Open:** the client's **versions** of SonarQube, Black Duck and Artifactory, and their **URLs**, are not known. The connectors are built for SonarQube 9.9 LTS to 2025.x, Black Duck 2023.x and newer (media types from the 2023–2025 API docs), and Artifactory 7.x. The live checks in §9 settle them.

## 12. Points this file adds to the approved design (owner to confirm)

None of these changes what was approved; each fills a gap the approval did not cover, or flags a conflict. They are marked so the owner can say no.

1. **The SonarQube token must be scrubbed as a user name** (§3.1): a new `token_as_user` auth instead of `http.basic(token, "")`, which would not hide the token in an error. Implementation detail, no behaviour change.
2. **Connector suggestions read one fact from this computer** (§6.2): whether a login is saved. 0.9.0 §5.1 says suggestions never read the home folder. The approved rule "only when not connected" needs this fact; it is passed in as a set of names, so the engine stays testable and two people with the same logins get the same list.
3. **`code` includes Python since the 0.9.0 fixes**, but the `artifactory` connector has no PyPI command. As approved, the rule fires on `code`. Alternative for the owner: `"when": ["java", "go", "node"]`, the same signals as the `maven-via-artifactory` skill rule (0.9.0 fix).
4. **`recommend --decline all` keeps its 0.9.0 meaning** (skills only), and `--decline all-tools` is new (§6.2), so the skills step in onboarding cannot decline a tool before it is offered.
5. **"Not now" in onboarding step 11 declines the repo tools** (not the role tools, which keep today's behaviour). Proposal, so `update` does not nag; the owner may prefer that "not now" records nothing.
6. **A skipped repo tool in `connect --suggested` becomes a decline** (`connect:<name>` in `declined_recommendations`), while a skipped role tool stays in `skipped_connectors` as today.
7. **`sonar-project.properties` and Detect property files can hold tokens** (§7.1, §7.2): the skills read the project key and names by key only, never the whole file.
8. **Black Duck `fixed_in` needs extra GETs** (§4.2): the vulnerable-components answer has no fix version; the connector reads upgrade guidance, once per distinct component version, at most 50 per run.
9. **Artifactory reference tokens are not JWTs** (§4.3): `whoami` then has no user name but still confirms the token.
10. **Order of work:** the connector rules and the role defaults land in Task C, after the B merges, because `packs.validate` only accepts connector names whose module exists. Task A tests the rule engine with a stub connector in a test kit.
