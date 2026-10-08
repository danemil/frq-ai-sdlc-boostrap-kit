# Personal Connectors Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Tasks B1–B5 are independent: superpowers:dispatching-parallel-agents may run them at the same time.

**Goal:** Give every role read-only access to Jira, Confluence, Bitbucket Data Center, Jama and Jenkins without MCP and without a secret ever passing through the AI: the person saves their own login once with `setup.py connect <name>` in a terminal; Copilot reads data with `connectors.py <connector> <command> [--json]` and cites each item's URL.

**Architecture:** a package `scripts/personal/connectors/` next to personal setup:

| Module | Job |
|---|---|
| `store.py` | credentials per user in `~/.config/ai-sdlc/connectors/<name>.json` (XDG and `AI_SDLC_CONFIG_DIR` honoured), env overlay `AI_SDLC_<NAME>_<KEY>`, 0700/0600, atomic write, last test |
| `http.py` | read-only `Client` (GET only), auth objects (Bearer, Basic, OAuth client credentials), paging presets, retries on 429/5xx, CA bundle, proxy, same-host redirects, plain `ConnectorError`s, redaction |
| `registry.py` | the connector contract (`Field`, `Command`, `Result`, `Context`) and glob discovery of `connectors/<name>.py` |
| `manage.py` | `setup.py connect | connections | disconnect` |
| `text.py` | HTML/storage → text, ADF → text, epoch ms → ISO, clip |
| `<name>.py` | one connector each (Tasks B1–B5) |

`connectors.py` (kit root) is the data CLI; `setup.py` gains three subcommands through `scripts/personal/commands.py`. Tests use `scripts/personal/tests/fakeserver.py` (a stdlib `http.server` in a thread) and never the network.

**Tech Stack:** Python 3.9+ standard library only (`urllib`, `json`, `ssl`, `getpass`, `os`, `stat`, `tempfile`, `http.server`, `unittest`).

**Design source:** [`2026-10-08-connectors-design.md`](./2026-10-08-connectors-design.md) (approved 2026-10-08). API notes: [onboarding, roles & skills design](./2026-10-07-onboarding-roles-and-skills-design.md) §5.0 and `template/scripts/jira/export_jira.py`.

## Global constraints

- **Branches.** Task A is on `feat/connectors` (cut from `main` at a5d40ff). Each B task runs in its own worktree on `feat/connectors-<name>`, cut from `feat/connectors` after Task A, and is merged back into `feat/connectors` by the coordinator after human review. B tasks create disjoint files, so the merges cannot conflict. Task C runs on `feat/connectors` after all five B merges and opens the one PR to `main`.
- **A human validates every commit** (kit rule). Each task ends with a review checkpoint: `git show --stat HEAD`, the test output on both Pythons, and wait.
- **Stdlib only. Python floor 3.9**: every module starts with `from __future__ import annotations`; no `match`, no `zip(strict=)`, no `X | Y` outside annotations, no `dataclass(slots=/kw_only=)`. Run every suite on `python3` and on `/usr/bin/python3` (3.9.6 on the owner's Mac).
- **Read-only.** Connector code calls only `Client.get*` and `Client.paginate`. No connector sends POST, PUT, PATCH or DELETE (the client refuses them; Jama's token POST lives inside `http.OAuthClientCredentials`).
- **Secrets.** Never print, log, return or put in an exception a field marked `secret=True`. Never read a secret outside `auth(values)`. Tests assert a known secret string is absent from all output.
- **Every item carries `url`**, a browser link (not an API link) where one exists, built with `ctx.client.web_url(...)` or taken from the server's own link.
- **Branch on `ctx.kind`, never on the URL** inside commands (tests force `kind="cloud"` against a 127.0.0.1 fake server).
- **No client or product names** in anything Copilot reads as guidance (skills, instructions, `ONBOARDING.md`, help texts). Other clients' names are forbidden everywhere. Before each commit, grep the staged diff for other projects' names; the coordinator gives the pattern in the task prompt (it is kept out of the repo, since it would itself name them), and the grep must print nothing.
- **Never delete files or code on your own initiative**; leave `docs/prompts/sessions/*.md` unstaged.
- **zsh**: quote paths (the repo is under `20 Projects/`), quote globs and brackets, commit with `git commit -F - <<'EOF'`.
- **Commit messages** end with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Run tests by path:** `python3 scripts/personal/tests/test_<name>.py`. The CI loop `for t in scripts/personal/tests/test_*.py` picks up new suites with no CI change.

---

### Task A: Foundation — DONE (this phase)

**Files (created):** `scripts/personal/connectors/{__init__,store,http,registry,manage,text}.py`, `connectors.py`, `scripts/personal/tests/fakeserver.py`, `scripts/personal/tests/stub_connector.py`, `scripts/personal/tests/test_connectors_foundation.py`. **Modified:** `setup.py` (three subparsers, docstring), `scripts/personal/commands.py` (three handlers).

**Tests:** `test_connectors_foundation.py`, 58 tests: store perms 0600/0700 and atomic save; env override and env-only; XDG and override paths; `connections` without secrets; `disconnect`; non-TTY refusal (and env-complete acceptance); secrets absent from stdout, stderr, exceptions and debug output; Bearer / Basic / OAuth headers; `HTTP_PROXY` used and `NO_PROXY` bypass (the fake server acts as the proxy); the CA bundle passed to `ssl.create_default_context(cafile=…)` with system CAs kept, per connector > `AI_SDLC_CA_BUNDLE` > `SSL_CERT_FILE`; retries on 429 (Retry-After honoured, capped) and 5xx with backoff; `--test` messages for 401, 403, connection refused against the fake server, and TLS, DNS, 407 proxy and timeout mapped from the exceptions; `remove` leaves the credentials folder intact; the registry discovers the stub and validates modules; the `connectors.py` CLI end to end with paging, `--json` envelope and exit codes. All other personal suites unchanged.

#### Foundation API (what B tasks use)

```python
# scripts/personal/connectors/registry.py
Field(key, prompt, secret=False, required=True, identity=False, when=None, help="")
    # when: Callable[[dict], bool] — ask only if true of the values so far (e.g. email on Cloud)
    # identity: shown as "user" by `connections`; env var: AI_SDLC_<NAME>_<KEY>
Command(help, run, args=None)      # run(ctx, args) -> Result; args(parser) adds argparse arguments
Result(item=None, items=None, truncated=False, lines=None, extra={})
    # item: one dict, or items: list of dicts; every dict has "url"; lines: optional plain text
Context(name, client, values, kind)  # kind: "cloud" | "dc" | ""
discover(extra=()) -> dict[str, Connector]     # glob of connectors/*.py, minus FOUNDATION and _*
from_module(name, module) -> Connector         # validates the contract; ValueError lists problems
open_context(connector, values, **client_kwargs) -> Context
load_values(connector) -> dict | None          # file + env

# scripts/personal/connectors/http.py
ConnectorError(message, kind="http", status=None)
    # kind: unauthorized forbidden not_found rate_limited server http tls dns refused proxy
    #       timeout network bad_response config
bearer(token) / basic(user, secret) / oauth_client_credentials(client_id, client_secret,
                                                                token_path="/rest/oauth/token")
Client(base_url, auth=None, *, ca_bundle=None, timeout=30.0, retries=3, backoff=1.0,
       sleep=time.sleep, debug=None, allow_http=False, stderr=None)
    .base_url  .host
    .url(path, params=None) -> str          # relative, or absolute on the same host only
    .web_url(path) -> str                   # base_url + "/" + path, for an item's "url"
    .get(path, params=None, *, accept="application/json") -> Response  # .status .headers .body .json() .text()
    .get_json(path, params=None)
    .get_text(path, params=None, *, accept="text/plain", max_bytes=None) -> (text, truncated)
    .paginate(path, params=None, *, items="values", paging=None, limit=50, page_size=50)
        -> (items, truncated)               # items: dotted key into each page
Offset(start="startAt", size="maxResults", total="total", last=None)   # last: e.g. "isLast"
BitbucketPaging()                          # start/limit, isLastPage, nextPageStart
TokenPaging(key="nextPageToken", param="nextPageToken", size="maxResults")
LinkPaging(key="_links.next", base="_links.base", size="limit")
dig(data, "a.b", default=None)   atlassian_kind(url) -> "cloud" | "dc"

# scripts/personal/connectors/text.py
html_to_text(html, max_chars=None)   adf_to_text(node)   clip(text, max_chars)   iso_from_ms(ms)

# scripts/personal/connectors/manage.py  (setup.py side; B tasks do not call it)
connect(name, *, test_only=False, connectors=None, isatty=None, ask=input,
        ask_secret=getpass.getpass, say=print, client_kwargs=None) -> (code, lines)
connections(connectors=None) -> (code, lines)    disconnect(name, connectors=None) -> (code, lines)
test(connector, values, **client_kwargs) -> (ok, message, user)

# scripts/personal/tests/fakeserver.py
FakeServer(routes)  .url  .requests[i].{method, target, path, query, headers, body}
Reply(status=200, body=None, headers={})   Seq(reply, reply, ...)   free_port()
    # a route is a dict/list (200 JSON), a Reply, a Seq, or f(request) -> any of those
ConnectorTestCase   # isolated config dir and env; helpers:
    .server(routes) -> FakeServer
    .connector(name) -> Connector                       # the shipped module, validated
    .context(connector, values, kind=None) -> Context   # kind forces "cloud"/"dc"
    .run_command(connector, ctx, argv) -> Result        # argv parsed by connectors.py's parser
    .run_cli(connector, argv, values=None) -> (code, stdout, stderr)
```

**The module contract** (also the docstring of `registry.py`; `tests/stub_connector.py` is a worked example):

```python
TITLE = "Jira"
FIELDS = [Field("url", ...), ...]           # first field is "url"; "ca_bundle" is added for you
def auth(values) -> http.Auth: ...
def kind(values) -> str: ...                # optional, default ""
def check(values) -> str | None: ...        # optional: a plain reason the values are unusable
WHOAMI = Command("who you are signed in as", run=_whoami)   # item has "user" and "display_name"
COMMANDS = {"search": Command("...", run=_search, args=_search_args), ...}
```

Conventions for every command: `--limit N` (default given per command; cap 1000) where a list is returned, setting `Result.truncated`; times as ISO-8601 strings (as the server gives them, or `text.iso_from_ms`); long text clipped (`text.clip`) with the limit stated below; a missing optional value is `null` in JSON, never omitted. Arguments that identify a thing are positional.

---

### Tasks B1–B5: one connector each (parallel)

**Every B task has the same shape.**

**Files:**
- Create: `scripts/personal/connectors/<name>.py`
- Create: `scripts/personal/tests/test_connector_<name>.py`
- Modify: **nothing** (the registry finds the module by its file name; CI's loop finds the test).

**Step 1: Write the failing tests** in `test_connector_<name>.py`: `import helpers` first, then `from fakeserver import ConnectorTestCase, Reply, Seq`. Canned JSON is inline in the test file and follows the vendor's documented response shape. Cover: the registry validates the module (`self.connector("<name>")`); `FIELDS` (and `applicable()` for kind-dependent fields); the auth header on a recorded request; each command's request (path and query) and its output shape (exact keys); paging across at least two pages and `truncated`; a 404 for a missing item; one `run_cli(..., ["<cmd>", ..., "--json"])` end to end; the secret absent from all output.

**Step 2: Run them and see them fail:** `python3 scripts/personal/tests/test_connector_<name>.py` → `ModuleNotFoundError: No module named 'personal.connectors.<name>'`.

**Step 3: Implement** `connectors/<name>.py` to the spec below.

**Step 4: Run** the new suite and every personal suite on both Pythons, and `python3 scripts/personal/validate_packs.py`:

```bash
for py in python3 /usr/bin/python3; do for t in scripts/personal/tests/test_*.py; do
  printf '%-52s ' "$t"; $py "$t" 2>&1 | tail -1; done; done
```

**Step 5: Commit** on `feat/connectors-<name>`: `feat(connectors): <name> connector (read-only)`, after the forbidden-names grep. **Review checkpoint.**

Plain-text output (`Result.lines`) is optional: when absent, `connectors.py` prints a generic form. Each spec lists the minimum test count.

---

### Task B1: `jira` (Data Center and Cloud) — at least 14 tests

- `TITLE = "Jira"`. `kind(values) = http.atlassian_kind(values["url"])`.
- `FIELDS`: `url` ("Jira URL, e.g. https://jira.example.com or https://example.atlassian.net"); `email` (identity, `when=` Cloud: "Atlassian account email"); `token` (secret: "API token (Cloud) or personal access token (Data Center)").
- `auth`: Cloud → `basic(email, token)`; DC → `bearer(token)`.
- API version `v`: `"3"` on Cloud, `"2"` on DC. Issue URL: `web_url(f"browse/{key}")`.

| Command | Args | Request | JSON |
|---|---|---|---|
| `whoami` | — | `GET /rest/api/{v}/myself` | item `{user: accountId (Cloud) or name (DC), display_name, email (or null), kind, url: Cloud web_url("jira/people/<accountId>"), DC web_url("secure/ViewProfile.jspa?name=<name>")}` |
| `search` | `jql` (positional); `--limit` 50; `--fields a,b` (extra field ids) | Cloud `GET /rest/api/3/search/jql` (`jql`, `fields`, `maxResults`, `nextPageToken`; `TokenPaging()`); DC `GET /rest/api/2/search` (`jql`, `fields`, `startAt`, `maxResults`; `Offset()`); items key `issues`; base fields `summary,issuetype,status,assignee,priority,updated` | items `{key, summary, type, status, assignee, priority, updated, url}` + `fields: {id: raw value}` only when `--fields` is given |
| `issue` | `key`; `--changelog`; `--links` | `GET /rest/api/{v}/issue/{key}?fields=summary,issuetype,status,assignee,reporter,priority,labels,created,updated,resolution,parent,description,components,fixVersions,issuelinks` | item `{key, summary, type, status, assignee, reporter, priority, labels[], components[], fix_versions[], created, updated, resolution, parent (key or null), description (ADF flattened on Cloud with text.adf_to_text; clip 4000), url}` |
| ↳ `--links` | | from `issuelinks` | `links: [{type (link type name), direction: "outward"\|"inward", relation (the outward/inward phrase, e.g. "blocks"), key, summary, status, url}]` |
| ↳ `--changelog` | | Cloud `GET /rest/api/3/issue/{key}/changelog` (`Offset(last="isLast")`, items `values`, limit 1000); DC the same issue request with `expand=changelog` (`changelog.histories`) | `changelog: [{at, author, field, from, to}]` oldest first, one entry per changed field (`fromString`/`toString`) |
| `sprints` | `board` (id); `--state` `active,future`; `--limit` 50 | `GET /rest/agile/1.0/board/{board}/sprint` (`state`, `startAt`, `maxResults`; `Offset(last="isLast")`) | items `{id, name, state, start, end, complete, goal, board, url: web_url("secure/RapidBoard.jspa?rapidView=<board>&sprint=<id>")}` |

Notes: Cloud `/search/jql` ignores `startAt`; never mix the paging styles. A Cloud issue's description is ADF; DC's is wiki text (keep as is, clipped).

### Task B2: `confluence` (Data Center and Cloud) — at least 10 tests

- `TITLE = "Confluence"`. `kind` as Jira. `FIELDS`: `url` ("Confluence URL, e.g. https://confluence.example.com or https://example.atlassian.net/wiki"); `email` (identity, Cloud only); `token` (secret). `auth` as Jira.
- API root: Cloud paths are under `/wiki` unless the saved URL already ends in `/wiki`; DC paths are under the saved URL (which may carry a context path such as `/confluence`). Keep this in one helper `_root(ctx)`.
- Page URL: `_links.base` (else the site root, plus `/wiki` on Cloud) + `_links.webui`.

| Command | Args | Request | JSON |
|---|---|---|---|
| `whoami` | — | `GET {root}/rest/api/user/current`; a `type` of `anonymous` raises `ConnectorError(kind="unauthorized")` | item `{user: accountId (Cloud) or username (DC), display_name, email (or null), kind, url: base URL}` |
| `page` | `id`; `--format` `text`\|`storage` (default `text`); `--max-chars` 20000 | Cloud `GET {root}/api/v2/pages/{id}?body-format=storage`; DC `GET /rest/api/content/{id}?expand=body.storage,version,space` | item `{id, title, space (key on DC, spaceId on Cloud), version, updated, body (text.html_to_text or raw storage, clipped), body_truncated, url}` |
| `search` | `query`; `--space KEY`; `--limit` 25 | `query` is CQL when it contains `=`, `~`, ` AND `, ` OR `, ` ORDER BY ` or ` in (`; otherwise `text ~ "<query, quotes escaped>" AND type = page`; `--space` adds `AND space = "KEY"`. Cloud `GET {root}/rest/api/search?cql=&limit=`; DC `GET /rest/api/content/search?cql=&limit=&expand=space,version`; `LinkPaging()`, items `results` | items `{id, type, title, space, updated, excerpt (Cloud: text, clip 300; DC: null), url}` (on Cloud the content is under `results[].content`) |

### Task B3: `bitbucket` (Data Center) — at least 11 tests

- `TITLE = "Bitbucket"`. `kind` → `"dc"`. `FIELDS`: `url` ("Bitbucket URL, e.g. https://bitbucket.example.com"); `token` (secret: "HTTP access token (personal, project or repository)"). `auth` → `bearer(token)`.
- `check(values)`: a `bitbucket.org` host returns "Bitbucket Cloud is not supported yet; this connector is for Bitbucket Data Center." (Cloud app passwords were removed on 2026-07-28; see design §3.)
- `<project>/<repo>[/<id>]` is parsed by one helper; a bad shape raises `ConnectorError(kind="config")` with the expected form. API prefix `/rest/api/1.0/projects/{P}/repos/{r}`. Times: `text.iso_from_ms`.

| Command | Args | Request | JSON |
|---|---|---|---|
| `whoami` | — | `GET /rest/api/1.0/projects?limit=1`, read the `X-AUSERNAME` response header (no header → `ConnectorError(kind="unauthorized")`, "Bitbucket did not say who you are"); then `GET /rest/api/1.0/users/{slug}` for the name (a 404 there is tolerated) | item `{user, display_name, email (or null), url: web_url("users/<slug>")}` |
| `prs` | `repo` (`P/r`); `--state` `OPEN`\|`MERGED`\|`DECLINED`\|`ALL` (default `OPEN`); `--limit` 25 | `GET {prefix}/pull-requests?state=&order=NEWEST` (`BitbucketPaging()`) | items `{id, title, state, author, reviewers: [{name, status}], from_branch, to_branch, created, updated, url: links.self[0].href}` |
| `pr` | `ref` (`P/r/id`); `--diff`; `--comments`; `--max-diff-bytes` 200000 | `GET {prefix}/pull-requests/{id}` | item: the `prs` fields + `description` |
| ↳ `--diff` | | `GET {prefix}/pull-requests/{id}.diff` with `accept="text/plain"`, `get_text(max_bytes=…)` | `diff`, `diff_truncated` |
| ↳ `--comments` | | `GET {prefix}/pull-requests/{id}/activities` (`BitbucketPaging()`, limit 500), keep `action == "COMMENTED"` | `comments: [{id, author, text, created, path (or null), line (or null), url: pr url + "/overview?commentId=<id>"}]` |
| `branches` | `repo` (`P/r`); `--filter TEXT`; `--limit` 50 | `GET {prefix}/branches?filterText=&orderBy=MODIFICATION` (`BitbucketPaging()`) | items `{name: displayId, id, latest_commit, is_default, url: web_url("projects/<P>/repos/<r>/browse?at=<quoted id>")}` |

To confirm on a live server (note it in the test file): the `X-AUSERNAME` header for HTTP access tokens, and the raw `.diff` endpoint (Bitbucket DC 6.7+).

### Task B4: `jama` (Jama Connect) — at least 11 tests

- `TITLE = "Jama"`. `kind` → `""`. `FIELDS`: `url` ("Jama URL, e.g. https://example.jamacloud.com"); `client_id` (identity: "API client ID"); `client_secret` (secret: "API client secret"). `auth` → `oauth_client_credentials(client_id, client_secret)` (token from `<url>/rest/oauth/token`). Tests must show the token request is made once and reused.
- REST root `/rest/v1`. Lists: `Offset(start="startAt", size="maxResults", total="meta.pageInfo.totalResults")`, items `data`, `page_size=50` (Jama's maximum). Item URL: `web_url(f"perspective.req#/items/{id}?projectId={project}")`.

| Command | Args | Request | JSON |
|---|---|---|---|
| `whoami` | — | `GET /rest/v1/users/current` | item `{user: username, display_name: "first last", email, id, url: base URL}` |
| `item` | `id` | `GET /rest/v1/items/{id}` | item `{id, key: documentKey, global_id, name: fields.name, type_id: itemType, project_id: project, created: createdDate, modified: modifiedDate, description (fields.description through html_to_text, clip 4000), fields: {the other fields, raw}, url}` |
| `search` | `text`; `--project ID`; `--type ID`; `--limit` 50 | `GET /rest/v1/abstractitems?contains=&project=&itemType=` | items `{id, key, name, type_id, project_id, modified, url}` |
| `relationships` | `id`; `--direction` `up`\|`down`\|`both` (default `both`); `--limit` 200 | `GET /rest/v1/items/{id}/upstreamrelationships` and/or `/downstreamrelationships`, with `include=data.fromItem,data.toItem` (names from `linked.items`) | items `{id, direction: "upstream"\|"downstream", type_id: relationshipType, suspect, from: {id, key, name, url}, to: {id, key, name, url}, url: the other item's url}` |
| `testruns` | exactly one of `--cycle ID` / `--plan ID`; `--limit` 200 | cycle: `GET /rest/v1/testcycles/{id}/testruns`; plan: `GET /rest/v1/testplans/{id}/testcycles`, then each cycle's test runs until the limit | items `{id, key, name, status: fields.testRunStatus, test_case_id: fields.testCase, cycle_id: fields.testCycle, executed: fields.executionDate, assigned_to: fields.assignedTo, url}` |

To confirm on a live instance (note it in the test file): the test-run field names, which can be renamed per Jama configuration.

### Task B5: `jenkins` — at least 11 tests

- `TITLE = "Jenkins"`. `kind` → `""`. `FIELDS`: `url` ("Jenkins URL, e.g. https://jenkins.example.com"); `username` (identity); `token` (secret: "API token (your name → Security → API Token)"). `auth` → `basic(username, token)`.
- A job path `a/b/c` (or `job/a/job/b/job/c`) becomes `/job/a/job/b/job/c`, each segment quoted with `urllib.parse.quote(seg, safe="")`. A build ref is a number or `last` / `lastSuccessful` / `lastFailed` (→ `lastBuild`, `lastSuccessfulBuild`, `lastFailedBuild`). Times: `text.iso_from_ms`; durations in seconds.
- Status from `color`: `blue`→`success`, `red`→`failed`, `yellow`→`unstable`, `aborted`→`aborted`, `disabled`→`disabled`, `notbuilt`→`not built`; a `_anime` suffix sets `building: true`.

| Command | Args | Request | JSON |
|---|---|---|---|
| `whoami` | — | `GET /me/api/json?tree=id,fullName`; `id == "anonymous"` raises `ConnectorError(kind="unauthorized")` ("Jenkins treated you as anonymous") | item `{user: id, display_name: fullName, url: web_url("user/<id>")}` |
| `job` | `path` | `GET {job}/api/json?tree=name,fullName,url,color,description,lastBuild[number,url,result,timestamp],lastSuccessfulBuild[number,url],lastFailedBuild[number,url],healthReport[description,score],jobs[name,url,color]` | item `{name, full_name, status, building, health: [{score, description}], last_build: {number, result, at, url} or null, last_success: {number, url} or null, last_failure: {number, url} or null, children: [{name, status, url}], url}` |
| `build` | `path`; `ref` | `GET {job}/{ref}/api/json?tree=number,url,result,building,timestamp,duration,displayName,description,changeSet[items[commitId,msg,author[fullName]]],changeSets[items[commitId,msg,author[fullName]]],actions[causes[shortDescription],parameters[_class,name,value]]` | item `{number, display_name, result, building, started, duration_s, causes[], parameters: [{name, value}] (password parameters, `_class` containing `Password`, are dropped), changes: [{commit, message, author}], url}` |
| `tests` | `path`; `ref`; `--all` | `GET {job}/{ref}/testReport/api/json?tree=failCount,passCount,skipCount,duration,suites[name,cases[className,name,status,duration,errorDetails]]`; a 404 raises `ConnectorError(kind="not_found")`: "Build <ref> of <path> has no test report." | item `{fail, pass, skip, duration_s, cases: [{class, name, status, duration_s, error (clip 2000)}] (FAILED and REGRESSION only unless --all), url: build url + "testReport/"}` |

---

### Task C: Integration (after B1–B5 are merged into `feat/connectors`)

**Files:**
- Create: `template/.claude/skills/connectors/SKILL.md` (placed as `ai-sdlc-connectors`; generic, no client or product names): when to use; run `connectors.py … --json` and cite each item's `url`; read-only; on exit code 3 or a 401, tell the person the exact `setup.py connect <name>` command to run **in their own terminal** and never ask for, accept or repeat a token, password or secret in the chat; never set `AI_SDLC_*` secret variables on the person's behalf; summarise, never invent fields.
- Create: `scripts/personal/tests/test_connectors_e2e.py`: all five connectors through `connectors.py` and `setup.py connect --test` as **subprocesses**, with `AI_SDLC_<NAME>_*` env vars pointing at one `FakeServer` that serves canned answers for every endpoint; `setup.py connect jira < /dev/null` exits 2 with the terminal message; `setup.py remove` keeps `$AI_SDLC_CONFIG_DIR/connectors`.
- Modify: `roles/core/role.json` (`skills` += `connectors`); `roles/*/role.json` `connectors` per design §5 (after the owner confirms the table); `scripts/personal/packs.py` (`connectors` must be a list of names from `registry.names()`, replacing "must be [] until Phase 3"); `scripts/personal/tests/test_packs.py` and `test_roles.py` for that rule; `scripts/personal/commands.py` `_summary` (one line: "Connectors for your roles: … — connect each in your own terminal: python3 .ai-sdlc/kit/setup.py connect <name>"); `ONBOARDING.md` (one line: connectors are set up by the person in their own terminal; never paste a secret into the chat); `README.md` (a short "Connectors" section: the four commands, where credentials live, env vars, proxy and CA bundle); `CHANGELOG.md` (an entry; version bump to 0.5.0 only if the owner agrees, then `VERSION` and `test_release.py`); `.github/workflows/ci.yml` `personal-e2e` (one step: run `test_connectors_e2e.py` by name, so a failure is visible on its own; the loop already runs it too).

**Steps:** test first (the e2e suite and the pack rule fail), implement, both Pythons, `validate_packs.py`, the forbidden-names grep, commit `feat(connectors): skill, role defaults, onboarding, docs and CI`, push, open the PR to `main` with the review checklist. **Review checkpoint.**
