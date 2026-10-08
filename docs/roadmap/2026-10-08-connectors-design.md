Released as kit 0.5.0 on 2026-10-08 (live confirmation pending, see §5.1).

# Personal connectors — design

**Status:** approved 2026-10-08 (kit owner). Built in three phases: A foundation, B1–B5 one connector each (in parallel), C integration. Plan: [`2026-10-08-connectors-plan.md`](./2026-10-08-connectors-plan.md).
**Extends:** [onboarding, roles & skills design](./2026-10-07-onboarding-roles-and-skills-design.md) §5.0 (Jira / Confluence access without MCP). Its API knowledge is reused here; its `scripts/atlassian/` library and `JIRA_*` / `CONFLUENCE_*` env-only secrets are replaced by this design.
**Related:** [personal setup design](./2026-10-08-personal-setup-design.md) (where the kit lives in a repo; `setup.py`).

## 1. Problem

The role skills need facts from the tools the teams use: Jira issues and sprints, Confluence pages, Bitbucket pull requests, Jama requirements and test runs, Jenkins builds and test reports. MCP is not approved yet (kit rule: CLI first). Each person has their own login, and **a secret must never pass through the AI or land in a repo**.

## 2. Decisions

| # | Question | Decision |
|---|---|---|
| 1 | Which tools? | **Five connectors:** `jira` and `confluence` (Data Center and Cloud), `bitbucket` (Data Center), `jama` (Jama Connect), `jenkins`. |
| 2 | Who types the secret? | **The person, in their own terminal:** `python3 .ai-sdlc/kit/setup.py connect <name>`. URL and other fields by prompt; secrets by `getpass` (hidden). Copilot only tells them the command. |
| 3 | Where are credentials kept? | **Per user, outside every repo:** `~/.config/ai-sdlc/connectors/<name>.json` (`$XDG_CONFIG_HOME/ai-sdlc/…` when set; `$AI_SDLC_CONFIG_DIR/connectors/…` overrides both, for tests and power users). Folder 0700, file 0600, written atomically. Shared by all the person's repos. |
| 4 | CI and power users | **Environment variables** `AI_SDLC_<NAME>_<KEY>` (e.g. `AI_SDLC_JIRA_URL`, `AI_SDLC_JIRA_TOKEN`, `AI_SDLC_JAMA_CLIENT_SECRET`) work without a file and win over it. |
| 5 | Stop an AI from piping a secret in | `connect` **refuses when stdin is not a terminal**, unless every needed value is already in the environment. |
| 6 | Read or write? | **Read-only in v1.** The HTTP client sends only GET; the one POST is Jama's OAuth token request, made inside the auth object. Writes (e.g. spec-to-backlog's create) are a later design, each behind human approval. |
| 7 | Corporate network | `HTTPS_PROXY` / `HTTP_PROXY` / `NO_PROXY` through urllib's ProxyHandler (verified by test). A CA bundle per connector (`ca_bundle`) or global (`AI_SDLC_CA_BUNDLE`, else `SSL_CERT_FILE`) is **added** to the system CAs. TLS verification is never switched off. |
| 8 | Secrets in output | **Never** echoed, logged or put in an exception. Errors are scrubbed of every secret value; `AI_SDLC_DEBUG=1` prints requests with `Authorization` redacted. |
| 9 | `remove` (personal setup) | **Never touches `~/.config/ai-sdlc/connectors`**: credentials belong to the person, not the repo. |
| 10 | How Copilot reads data | **`python3 .ai-sdlc/kit/connectors.py <connector> <command> [args] [--json]`**: plain text by default, `--json` for structured data. Every item carries its source `url`, so Copilot can cite it. |
| 11 | Adding a connector | **One module, no shared edits:** `scripts/personal/connectors/<name>.py` is found by a glob (`registry.py`). |

## 3. Auth per connector

| Connector | Kind (from the URL) | Fields | Auth |
|---|---|---|---|
| `jira` | Cloud if the host is `*.atlassian.net`, else Data Center | url; email (Cloud only); token | DC: `Bearer <PAT>`. Cloud: `Basic email:API-token` |
| `confluence` | same rule | url; email (Cloud only); token | same as Jira |
| `bitbucket` | Data Center only (`bitbucket.org` is refused with a plain message) | url; token | `Bearer <HTTP access token>` (personal, project or repo token) |
| `jama` | — | url; client_id; client_secret | OAuth2 client credentials: `POST <url>/rest/oauth/token` (`grant_type=client_credentials`, Basic client_id:secret) → `Bearer <access_token>`, refreshed on expiry |
| `jenkins` | — | url; username; token | `Basic username:API-token` |

Every connector also has an optional `ca_bundle` field. Bitbucket note (from §5.0): Bitbucket **Cloud** removed app passwords on 2026-07-28, so the kit does not offer username + app password anywhere; Bitbucket Cloud is out of scope for v1.

## 4. Command surface

**Credentials (the person, in a terminal):**

```
python3 .ai-sdlc/kit/setup.py connect <name>          # ask, save, then test
python3 .ai-sdlc/kit/setup.py connect <name> --test   # one read-only identity call: OK or the exact problem
python3 .ai-sdlc/kit/setup.py connections             # URL, user, kind, last test, source (file/env); never a secret
python3 .ai-sdlc/kit/setup.py disconnect <name>       # delete the file
```

`--test` answers in plain words: 401 (credentials not accepted), 403 (signed in, no read access), TLS (certificate not verified: set `ca_bundle`), proxy (refused, 407, tunnel failed), DNS (name not found: URL or VPN), connection refused, timeout.

**Data (Copilot, read-only):** `python3 .ai-sdlc/kit/connectors.py <connector> <command> [args] [--json]`. Exit codes: 0 ok, 1 error (plain message on stderr), 2 usage, 3 not connected (the message names the `setup.py connect` command for the person to run). `--json` prints `{"connector", "command", "source", "item"}` or `{"connector", "command", "source", "items", "count", "truncated"}`.

| Connector | Commands (v1) |
|---|---|
| jira | `whoami` · `search <JQL> [--limit N] [--fields a,b]` · `issue <KEY> [--changelog] [--links]` · `sprints <board-id> [--state active,future,closed]` |
| confluence | `whoami` · `page <id> [--format text\|storage]` · `search <CQL or text> [--space KEY] [--limit N]` |
| bitbucket | `whoami` · `prs <project>/<repo> [--state OPEN\|MERGED\|DECLINED\|ALL] [--limit N]` · `pr <project>/<repo>/<id> [--diff] [--comments]` · `branches <project>/<repo> [--filter TEXT] [--limit N]` |
| jama | `whoami` · `item <id>` · `search <text> [--project ID] [--type ID] [--limit N]` · `relationships <id> [--direction up\|down\|both]` · `testruns (--cycle ID \| --plan ID) [--limit N]` |
| jenkins | `whoami` · `job <path>` · `build <path> <n\|last\|lastSuccessful\|lastFailed>` · `tests <path> <n\|last> [--all]` |

Endpoints, arguments and JSON shapes per command are in the plan (Tasks B1–B5).

**API knowledge reused from §5.0 and `template/scripts/jira/export_jira.py`:** Jira Cloud searches `GET /rest/api/3/search/jql` with a `nextPageToken` cursor; Data Center `GET /rest/api/2/search` with `startAt`/`maxResults`/`total`. Cloud descriptions are ADF (flattened to text). Boards and sprints use `/rest/agile/1.0` on both. Confluence Cloud reads pages with v2 (`/wiki/api/v2/pages/{id}`); Data Center with the content API (`/rest/api/content/{id}?expand=body.storage`). CQL search is v1 on both (`/wiki/rest/api/search` Cloud, `/rest/api/content/search` DC). Still unverified until a live call: `expand=changelog` on Cloud `/search/jql` (the plan uses the per-issue changelog endpoint instead).

## 5. Role defaults

`roles/<id>/role.json` `connectors` lists the connectors a role usually needs. Onboarding mentions them once, the setup summary names them (marking the ones already connected), and the connectors skill suggests them; nothing connects by itself, since only the person can type the secret. **Defaults only drive suggestions: any person can connect any connector.** The pack validator (`packs.validate`) accepts only names the registry discovers in `scripts/personal/connectors/`. **Approved by the owner 2026-10-08** (it replaces the table proposed in the first draft of this design):

| Role | Connectors |
|---|---|
| core | — |
| po | jira, confluence, jama |
| pm | jira, confluence, jama |
| sm | jira, confluence |
| dev | bitbucket, jira, jenkins |
| qa | jira, jama, jenkins |
| architect | confluence, bitbucket, jira |
| em | jenkins, bitbucket, jira |

## 5.1 Needs live confirmation

Built and tested against canned answers in each vendor's documented shape; these points could not be checked without a live server (collected from the B task reports). Until confirmed, treat a surprise here as a likely cause before suspecting the person's setup:

- **Bitbucket Data Center:** that the `X-AUSERNAME` response header (used by `whoami`) is sent for HTTP access tokens; and the raw `pull-requests/{id}.diff` endpoint (Bitbucket 6.7+) used by `pr --diff`.
- **Jama Connect:** the test-run field names (`testRunStatus`, `testCase`, `testCycle`, `executionDate`, `assignedTo`), which a Jama configuration can rename; and the item URL format `perspective.req#/items/<id>?projectId=<project>` (test runs may have their own view); also that `include` is accepted as a repeated parameter (`include=data.fromItem&include=data.toItem`).
- **Jenkins:** test reports that put their results under `childReports` rather than `suites` (multi-configuration and some aggregated jobs; `tests` reads `suites` only); and the host of the `url` Jenkins returns for jobs and builds, which the connector uses as each item's link: it comes from the Jenkins root URL setting and may differ from the saved URL.
- **Confluence Cloud:** that `expand=content.space,content.version` on `/wiki/rest/api/search` returns the space key and version; and the highlight markers (`@@@hl@@@` … `@@@endhl@@@`) stripped from excerpts.
- **Jira:** on Data Center, that `issue --changelog` (`expand=changelog`) returns every history entry, uncapped (Cloud pages it through its own endpoint); on Cloud, the people URL (`/jira/people/<accountId>`) and the board/sprint URL (`secure/RapidBoard.jspa?rapidView=<board>&sprint=<id>`).

## 6. Architecture

```
setup.py connect|connections|disconnect ──► scripts/personal/commands.py ──► connectors/manage.py
connectors.py <connector> <command>     ──► connectors/registry.py ──► connectors/<name>.py
                                                    │                         │
                                         connectors/store.py         connectors/http.py (+ text.py)
                                   (~/.config/ai-sdlc/connectors)   (GET, auth, TLS, proxy, retries)
```

- `store.py`: paths (override → XDG → home), env overlay, atomic 0600 save, last test, delete, list.
- `http.py`: `Client` (GET JSON/text, paging presets, retries on 429/5xx with capped backoff, same-host redirects only, https required except loopback), auth objects, plain `ConnectorError`s, CA bundle and proxy handling, redaction.
- `registry.py`: the connector contract (`Field`, `Command`, `Result`, `Context`), validation, glob discovery.
- `manage.py`: the three `setup.py` subcommands.
- `text.py`: HTML/storage and ADF to plain text.
- Tests: `scripts/personal/tests/fakeserver.py` (stdlib `http.server` in a thread, canned JSON, recorded requests, also usable as a proxy) and `tests/stub_connector.py` (an example connector, never shipped as one).

## 7. Out of scope (v1)

Writes of any kind; Bitbucket Cloud; Jama write-back of test results; Jenkins console logs and triggering builds; caching; MCP. The evidence correlator (skill #9 in the 2026-10-07 design) and the Jira/Confluence-based skills (#1, #4, #5) consume `connectors.py` when they are built.
