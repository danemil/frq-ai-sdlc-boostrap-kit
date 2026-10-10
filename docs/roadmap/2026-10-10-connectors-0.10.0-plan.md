# Connectors 0.10.0 (SonarQube, Black Duck, Artifactory) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task. Tasks B1–B3 are independent (one module and one test file each, own worktree): superpowers:dispatching-parallel-agents may run them at the same time. Task A comes first; Tasks C1–C6 run after the B merges, in order; Task D is the owner's manual re-test. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Three new read-only connectors, `sonarqube`, `blackduck` and `artifactory`, in the 0.5.0 framework; connector suggestions from the repo's files (and new role defaults); the SonarQube, Black Duck and mirror skills read through them when connected; release kit 0.10.0.

**Architecture:** One module per connector in `scripts/personal/connectors/` (found by the glob, no shared edits). `http.py` gets a token-exchange auth base class that Jama's OAuth and the new Black Duck auth share, and a stricter POST gate; data reads stay GET only. `recommend.py` learns a third rule action, `connect`, read from `roles/recommend.json`; `setup.py recommend`, the setup summary and `connect --suggested` show the connector suggestions. Skills switch between the connector and a pasted report.

**Tech Stack:** Python 3.9+ standard library only (`urllib`, `json`, `ssl`, `base64`, `xml.etree.ElementTree`, `http.server`, `unittest`). Markdown skills.

**Design source:** [`2026-10-10-connectors-0.10.0-design.md`](./2026-10-10-connectors-0.10.0-design.md) (approved 2026-10-10; its §12 lists the points the owner decided on 2026-10-10). Framework: [`2026-10-08-connectors-design.md`](./2026-10-08-connectors-design.md) and its plan (the Foundation API and the module contract are unchanged and not repeated here).

## Global constraints

- **Branches.** Task 0 and Task A on `feat/connectors-0.10.0` (cut from `main` at `36c5170`, v0.9.0). Each B task runs in its **own worktree** on `feat/c10-<name>` (`feat/c10-sonarqube`, `feat/c10-blackduck`, `feat/c10-artifactory`), cut from `feat/connectors-0.10.0` after Task A. B tasks create disjoint files, so the merges cannot conflict. The coordinator merges them back after human review. Tasks C1–C5 run on `feat/connectors-0.10.0`; C6 on `release/0.10.0`, one PR to `main`, open until Task D is done.
- **A human validates every commit** (kit rule). Every "Commit" step means: show `git diff --staged --stat` and the test output on both Pythons, **ask the owner**, commit only on yes. Never push without asking.
- **Stdlib only. Python floor 3.9:** every module starts with `from __future__ import annotations`; no `match`, no `zip(strict=)`, no `X | Y` outside annotations, no `dataclass(slots=/kw_only=)`. Run every suite on `python3` and on `/usr/bin/python3` (3.9.6 on the owner's Mac).
- **Read-only.** Connector code calls only `Client.get*` and `Client.paginate`. It never calls `_send`, `_exchange`, never names `"POST"`, never imports `urllib` or `http.client` (Task A adds a static test for this). The only POSTs are inside `http.TokenExchange` subclasses.
- **Secrets.** Never print, log, return or put in an exception a field marked `secret=True`, a token sent as a Basic user name, or a bearer token from an exchange. Never read a secret outside `auth(values)`. Each test file asserts that its known secret strings (the saved token and, for Black Duck, the bearer token) are absent from all output.
- **Every item carries `url`**, a browser link where one exists (§4 of the design says how per tool).
- **No client, employer or vendor company names** in anything Copilot reads (skills, role instructions, `ONBOARDING.md`, help texts): never "FRQ", "Frequentis", the owner's employer, or a vendor company. Product names (SonarQube, Black Duck, Artifactory) are fine. Other projects' names are forbidden everywhere. Name screen before every commit:
  - `git diff --staged | grep -n -i -E "$OTHER"` prints nothing (`$OTHER`: other projects' and the employer's names, given by the coordinator in the task prompt, never written in the repo);
  - `git diff --staged | grep -n -E '/Users/|~/work/'` prints nothing;
  - `test_roles.py::test_no_client_names_in_copilot_guidance` passes.
- **Never delete files or code on your own initiative**; leave `docs/prompts/sessions/*.md` unstaged.
- **zsh:** quote paths (the repo is under `20 Projects/`), quote globs and brackets, commit with `git commit -F - <<'EOF'`; messages end with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **The full run** (used below): `for py in python3 /usr/bin/python3; do for t in scripts/personal/tests/test_*.py; do $py "$t" >/dev/null 2>&1 || echo "FAIL $py $t"; done; done` → prints nothing; then `python3 scripts/personal/validate_packs.py` → `ok …`; `python3 template/scripts/validate-skills.py` → all conform.

## Review focus

1. **No connector command can POST** (Task A, `TestPostGate`), and Jama behaves exactly as before (its suite unchanged and green).
2. **No secret in any output**, including the SonarQube token as a Basic user name and the Black Duck bearer token (A, B1, B2).
3. **SonarQube's two issue models** map to one output, and the filter actually sent is shown (B1).
4. **Black Duck names, not ids**: projects and versions resolved by name, links followed from `_meta`, a clear error on several matches (B2).
5. **The mirror's versions are the only versions proposed** when the `artifactory` connector is connected (C2, Task D).
6. **Connector suggestions are deterministic** and never nag: not for a role default, not when connected, skipped or declined; `--decline all` still means skills only (A, C1, C3).

## Files

| File | Task | Change |
|---|---|---|
| `scripts/personal/connectors/http.py` | A1 | `token_as_user`, `TokenExchange`, `blackduck_token`, POST gate |
| `scripts/personal/tests/test_connectors_foundation.py` | A1 | new tests (token exchange, POST gate, static scan) |
| `scripts/personal/recommend.py`, `scripts/personal/commands.py`, `scripts/personal/connectors/manage.py`, `setup.py` | A2 | `connect` rules, `recommend` output and `--decline`, summary line, `connect --suggested` |
| `scripts/personal/tests/test_recommend.py`, `test_connect_suggested.py`, `test_packs.py`, `test_cli.py`, `scripts/personal/tests/fixtures/stub-connector-kit/` (or a helper that builds one) | A2 | new and adjusted tests |
| `scripts/personal/connectors/sonarqube.py`, `scripts/personal/tests/test_connector_sonarqube.py` | B1 | new |
| `scripts/personal/connectors/blackduck.py`, `scripts/personal/tests/test_connector_blackduck.py` | B2 | new |
| `scripts/personal/connectors/artifactory.py`, `scripts/personal/tests/test_connector_artifactory.py` | B3 | new |
| `roles/{dev,qa,architect}/role.json`, `roles/recommend.json`, `scripts/personal/tests/test_roles.py`, `test_recommend.py` | C1 | role defaults, the three connector rules |
| `template/.claude/skills/{sonarqube-findings,blackduck-findings,maven-via-artifactory,connectors}/**`, `roles/{core,dev,qa,architect}/instructions.md`, `scripts/personal/tests/test_stack_skills.py`, `test_skill_guidance.py` | C2 | skills switch, routing lines |
| `ONBOARDING.md`, `scripts/personal/tests/test_onboarding.py` | C3 | steps 10–11, "Recommend skills", "Connect a tool" |
| `scripts/personal/tests/fake_tools.py`, `test_connectors_e2e.py`, `.github/workflows/ci.yml` | C4 | the three tools end to end |
| `README.md`, `docs/how-to.md`, `template/.claude/skills/README.md` | C5 | docs |
| `CHANGELOG.md`, `VERSION`, `scripts/personal/tests/test_release.py` | A–C (Unreleased lines), C6 | `[0.10.0]` |

## Branches and order

```
main @36c5170 (v0.9.0)
 └─ feat/connectors-0.10.0      Task 0 → Task A1 → Task A2                       (sequential)
     ├─ feat/c10-sonarqube      Task B1  ┐
     ├─ feat/c10-blackduck      Task B2  │ parallel, one worktree each, disjoint files
     └─ feat/c10-artifactory    Task B3  ┘
 └─ feat/connectors-0.10.0      merge B1–B3, then C1 → C2 → C3 → C4 → C5           (sequential)
     └─ release/0.10.0          Task C6, one PR to main; Task D (owner, Copilot CLI) before merge
```

---

### Task 0: Branch and record the design (sequential) — DONE with this commit

- [x] `git switch -c feat/connectors-0.10.0` from `main` at `36c5170`.
- [x] Commit the design and this plan: `docs(roadmap): connectors 0.10.0 design and plan (SonarQube, Black Duck, Artifactory)`.
- [x] **Owner (2026-10-10):** design §12 items 1, 2, 4, 6, 7, 8, 9, 10 accepted as written; item 3 keeps `code` as the artifactory signal (Python repos included; a PyPI command may come later); item 5 changed: "not now" in onboarding step 11 records nothing (asked again next time; only an explicit decline stops the suggestion), as for the role tools today. Plan approved. Task A2 is unchanged by these answers (items 4 and 6 as written; `--decline all-tools` stays, for an explicit no).

---

### Task A1: `http.py` — token exchange and the POST gate (sequential, test first)

**Files:** Modify `scripts/personal/connectors/http.py`. Modify `scripts/personal/tests/test_connectors_foundation.py`. `CHANGELOG.md` (Unreleased line).

**Interfaces — Produces** (B tasks use them):

```python
http.token_as_user(token) -> Auth        # Basic base64("<token>:"); secrets() = [token, encoded]
class http.TokenExchange(Auth):          # base for auths that trade a secret for a bearer token
    kind = "exchange"
    token_path: str                      # the one path this auth may POST to
    def exchange_request(self) -> tuple[dict, bytes, str | None, str]
        # (headers, body, content_type or None, accept)
    def parse(self, data) -> tuple[str, float]          # (token, seconds it lives)
    def unauthorized_message(self, host) -> str
    # shared, not overridden: headers(client) fetches through client._exchange(self) when
    # there is no token or it expires within 30 s; secrets() = long-lived secrets + token
class http.OAuthClientCredentials(TokenExchange)      # Jama, unchanged behaviour
http.blackduck_token(api_token) -> TokenExchange
    # POST /api/tokens/authenticate, "Authorization: token <api_token>", empty body,
    # accept "application/vnd.blackducksoftware.user-4+json";
    # parse: bearerToken, expiresInMilliseconds / 1000 (default 3600 s when missing)
Client._exchange(auth) -> Response      # private; the only caller of a POST
```

- [ ] **Step 1: Failing tests** in `test_connectors_foundation.py` (use `fakeserver.FakeServer`; no network):
  - `TestTokenAsUser.test_header_is_basic_token_colon_empty` — the recorded `Authorization` is `Basic ` + base64 of `"<token>:"`.
  - `TestTokenAsUser.test_the_token_is_scrubbed` — a 400 whose JSON body echoes the token: the `ConnectorError` text has `<redacted>`, not the token; the same with `AI_SDLC_DEBUG=1` (stderr has no token).
  - `TestTokenExchange.test_blackduck_exchange_once_then_bearer` — routes `/api/tokens/authenticate` (POST) → `{"bearerToken": "BEARER-1", "expiresInMilliseconds": 7199000}` and `/api/current-user` → `{}`; two GETs → exactly one POST, recorded with `Authorization: token <api>` and `Accept: application/vnd.blackducksoftware.user-4+json`, empty body; both GETs carry `Authorization: Bearer BEARER-1`.
  - `TestTokenExchange.test_refreshes_when_expired` — `expiresInMilliseconds: 1000` and a fake clock (`time.time` patched): the second GET after 2 s makes a second POST.
  - `TestTokenExchange.test_401_on_exchange_says_api_token_not_accepted` — the message contains "API token was not accepted"; `kind == "unauthorized"`; no token in it.
  - `TestTokenExchange.test_no_bearer_in_answer_is_bad_response`.
  - `TestTokenExchange.test_bearer_token_never_printed` — with `AI_SDLC_DEBUG=1`, stderr has neither the API token nor `BEARER-1`.
  - `TestTokenExchange.test_jama_oauth_is_a_token_exchange` — `isinstance(http.oauth_client_credentials("i", "s"), http.TokenExchange)`; the existing Jama foundation tests and `test_connector_jama.py` stay green unchanged.
  - `TestPostGate.test_a_command_cannot_post` — a stub command (in the test) calls `ctx.client._send("POST", ctx.client.url("/x"), {}, b"", None)`: `ConnectorError`, `kind == "config"`, "read-only"; nothing reaches the fake server. The same with the client's auth a `blackduck_token(...)`.
  - `TestPostGate.test_exchange_only_by_the_clients_own_auth` — `client._exchange(other)` with a `TokenExchange` that is not `client.auth` → refused, nothing sent.
  - `TestPostGate.test_exchange_only_to_its_token_path` — `client._send("POST", client.url("/other"), {}, b"", None, _exchange=client.auth)` with a `blackduck_token` auth (token path `/api/tokens/authenticate`) → refused, nothing sent.
  - `TestPostGate.test_put_patch_delete_refused` — for each method, `_send` refuses.
  - `TestPostGate.test_connector_modules_never_post` — for every module in `registry.names()` plus `tests/stub_connector.py`: the source (read as text, parsed with `ast`) has no attribute `_send` or `_exchange`, no string constant `"POST"`, `"PUT"`, `"PATCH"`, `"DELETE"`, and imports nothing from `urllib` or `http.client`. (It runs again in C, when the three new modules exist.)
- [ ] **Step 2: Run, expect FAIL** (`AttributeError: module 'personal.connectors.http' has no attribute 'token_as_user'`).
- [ ] **Step 3: Implement.**
  - `TokenAsUser(Auth)`: `kind = "basic"`, header as `Basic`, `secrets() = [token, encoded]`.
  - `TokenExchange(Auth)`: holds `_token`, `_expires`; `headers(client)`: `if not self._token or time.time() >= self._expires: self._fetch(client)`; `_fetch` calls `client._exchange(self)`, maps a 401 to `ConnectorError(self.unauthorized_message(client.host), "unauthorized", 401)`, then `token, life = self.parse(resp.json())`; no token → `ConnectorError(f"{client.host} gave no token for the login.", "bad_response")`; `self._expires = time.time() + max(30, life - 30)`.
  - `OAuthClientCredentials(TokenExchange)`: `exchange_request` returns the Basic header, `b"grant_type=client_credentials"`, `"application/x-www-form-urlencoded"`, `"application/json"`; `parse` reads `access_token`, `expires_in` (default 3600); the 401 message is the 0.5.0 text, word for word.
  - `BlackDuckToken(TokenExchange)`: as in the interface; `secrets() = [api_token] + ([token] if token)`.
  - `Client._exchange(auth)`: `if auth is not self.auth or not isinstance(auth, TokenExchange): raise ConnectorError("Connectors are read-only: only GET requests are sent.", "config")`; `headers, body, ctype, accept = auth.exchange_request()`; `return self._send("POST", self.url(auth.token_path), headers, body, ctype, accept, _exchange=auth)`.
  - `_send(..., _exchange=None)`: a non-GET passes only when `method == "POST"` and `_exchange is self.auth` and `isinstance(_exchange, TokenExchange)` and the URL's path equals `urlsplit(self.url(_exchange.token_path)).path`. Everything else: the read-only error. The 0.5.0 special case for `OAuthClientCredentials` is removed (it is now covered).
  - Module docstring: "GET only. The only POSTs are token exchanges (Jama OAuth, Black Duck), made by `TokenExchange` itself through `Client._exchange`."
- [ ] **Step 4: Green** (the full run; Jama's suites unchanged).
- [ ] **Step 5:** `CHANGELOG.md` Unreleased, `### Changed`: "Connectors: one token-exchange auth for Jama's OAuth and Black Duck; a stricter POST gate (only an auth's own token request), with a test that no connector module can send a POST." **Name screen, Commit** (ask first): `feat(connectors): token-exchange auth base and a stricter POST gate; token-as-user Basic auth`.

---

### Task A2: Connector suggestions from the repo (sequential, test first)

**Files:** Modify `scripts/personal/recommend.py`, `scripts/personal/commands.py`, `scripts/personal/connectors/manage.py`, `setup.py` (help text of `--decline`). Tests: `test_recommend.py`, `test_connect_suggested.py`, `test_packs.py`, `test_cli.py`. `CHANGELOG.md`.

**Interfaces — Produces:**

```python
recommend.ACTIONS = ("add", "drop", "connect")
recommend.RULE_KEYS |= {"connector"}
recommend.compute(kit, root, st, all_packs) -> list[dict]          # unchanged: skill items only
recommend.connector_items(kit, root, st, all_packs, connected) -> list[dict]
    # connected: set of connector names with a saved login (the caller passes it)
    # each: {"id": "connect:<n>", "action": "connect", "connector": n, "title": TITLE,
    #        "reason", "evidence": [≤3 repo paths], "declined": bool, "connected": bool}
    # sorted by connector name; a rule for a role default never appears;
    # connected ones appear with connected: True (shown nowhere as open)
recommend.open_connectors(items) -> list[dict]   # not declined, not connected
commands._tools_line(kit, root, st, all_packs) -> list[str]
    # [] or ["- Tools to connect for this repo: a, b (say 'connect a')"]; never raises
manage.suggest(defaults, *, extra=(), ...)       # extra: [(name, reason)] offered after defaults
    # result gains "declined": names from extra the person skipped
```

**Why the rules are not in `roles/recommend.json` yet:** `recommend.validate` only accepts a connector the kit's registry finds, and `sonarqube`, `blackduck` and `artifactory` arrive in B1–B3. So A2 tests the engine with a **test kit** (a temp copy of the kit, as `test_packs.py` already does) that has a stub connector module `scripts/personal/connectors/stubtool.py` (copied from `tests/stub_connector.py`, `TITLE = "Stub Tool"`) and one extra rule `{"connector": "stubtool", "action": "connect", "when": ["sonar"], "reason": "this repo is analysed by the stub tool"}`. A helper `helpers.kit_with_connector_rule(tmp)` builds it. The real rules land in Task C1.

- [ ] **Step 1: Failing tests.**
  - `test_packs.py::TestValidate::test_bad_connector_rules` (temp kit, one change at a time; each gives one readable error): unknown connector; `connect` without `when`; `connect` with `unless`; `connect` with `skill`; unknown signal; unknown role in `roles`; empty reason; reason over 120 characters; two rules for one id; a connector named like a skill (a stub module `drawio.py` in the temp kit) → "a connector and a skill share the name drawio".
  - `test_packs.py::TestValidate::test_a_good_connector_rule_validates` (the helper's kit → `recommend.validate(kit) == []`).
  - `test_recommend.py::TestConnectorItems`:
    - `test_fires_on_its_signal_for_anyone` — a repo with `sonar-project.properties`; roles `po` → one item `connect:stubtool`, evidence `["sonar-project.properties"]`, `declined False`, `connected False`.
    - `test_no_signal_no_item` — a repo with only `README.md`.
    - `test_not_for_a_role_default` — a temp role pack `dev` whose `connectors` include `stubtool`: roles `dev` → no item; roles `po` → the item.
    - `test_connected_is_marked_not_open` — `connected={"stubtool"}` → the item with `connected True`; `open_connectors` → `[]`.
    - `test_skipped_and_declined_are_not_open` — `skipped_connectors=["stubtool"]` → not open (marked `declined True`); `declined_recommendations=["connect:stubtool"]` → `declined True`.
    - `test_compute_still_returns_only_skills` — `compute()` has no `connect:` id.
    - `test_same_repo_same_list` — two runs, and a run with another `HOME` → identical (`connected` passed in, no home read: `AI_SDLC_CONFIG_DIR` points at an empty temp folder).
  - `test_recommend.py::TestRecommendCommand` (CLI through `helpers.cli` in a repo set up with the helper's kit):
    - `test_text_has_a_tools_part` — after the skill part: `Tools to connect for this repo (from its files; you type the login yourself, in your own terminal):`, `1. connect:stubtool — Stub Tool: this repo is analysed by the stub tool (sonar-project.properties).`, `To connect one: python3 .ai-sdlc/kit/setup.py connect <name>   (in your own terminal), or all of them with connect --suggested`, `To say no: python3 .ai-sdlc/kit/setup.py recommend --decline connect:stubtool   (or the tool name)`; exit 0; `helpers.snapshot` unchanged.
    - `test_no_suggestions_line_unchanged` — an empty repo → exactly `No skill suggestions for this repo.` (no tools part).
    - `test_decline_by_id_and_by_name` — `--decline connect:stubtool` and, in a fresh repo, `--decline stubtool` → in `declined_recommendations` as `connect:stubtool`; then the tools part lists it under `Declined earlier (to connect one after all: python3 .ai-sdlc/kit/setup.py connect <name>, in your own terminal):`.
    - `test_decline_all_is_skills_only` — a repo with skill and tool suggestions: `--decline all` → the skill ids declined, `connect:stubtool` still open.
    - `test_decline_all_tools` — `--decline all-tools` → only connector ids declined; with none open: `Nothing to decline: there are no open tool suggestions.`, exit 0.
    - `test_json_has_connectors` — `--json` keys exactly `suggestions`, `connectors`, `others`; a connector item has exactly `id, action, connector, title, reason, evidence, declined, connected`.
    - `test_connect_clears_a_decline` — decline `connect:stubtool`, then `connect stubtool` from env (`AI_SDLC_STUBTOOL_*`, no terminal) → the id is gone from `declined_recommendations`.
  - `test_setup.py::test_setup_mentions_tools_for_this_repo` — setup as `po` in the sonar repo (helper kit) → summary has `- Tools to connect for this repo: stubtool (say 'connect stubtool')`, after the skill-suggestion line (if any); an empty repo → no such line. `test_change.py` and `test_update.py`: the same line on `change --roles` and on update (only new ones), never on `change --lang`.
  - `test_connect_suggested.py`:
    - `test_repo_tools_come_after_role_tools_with_their_reason` — roles `dev` (role defaults from the real pack) in the sonar repo of the helper kit; answers `s` for each role tool, then `y` for the stub tool: the prompt for it reads `Connect Stub Tool now? It fits this repo: this repo is analysed by the stub tool. [y = yes, s = skip, a = skip all the rest; Enter = skip]: `; `manage.connect` called for `stubtool`.
    - `test_a_skipped_repo_tool_is_declined` — answer `s` → `connect:stubtool` in `declined_recommendations`, `stubtool` **not** in `skipped_connectors`; role tools skipped as before go to `skipped_connectors`.
    - `test_a_skips_the_rest_of_both_lists` — `a` at the first role tool → role tools to `skipped_connectors`, repo tools declined.
    - `test_no_terminal_changes_nothing` — unchanged message, nothing recorded.
  - `test_cli.py::test_recommend_decline_help_mentions_tools` — the `--decline` help says "skill names or ids, all (skills), a tool name, connect:<tool> or all-tools".
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.**
  - `recommend.py`:
    - `load()` unchanged; `compute()` skips rules whose action is `connect`.
    - `connector_items()`:

```python
def connector_items(kit, root, st, all_packs, connected) -> list[dict]:
    rules = [r for r in load(kit)["rules"] if r.get("action") == "connect"]
    if not rules:
        return []                                   # no repo scan when there is no rule
    found = signals(root, kit)
    c = st["choices"]
    roles = set(c["roles"])
    defaults = set(packs.role_connectors(all_packs, [r for r in c["roles"] if r in all_packs]))
    declined = set(st.get("declined_recommendations", []))
    skipped = set(st.get("skipped_connectors", []))
    titles = _titles(kit)                           # {name: TITLE} via registry, "" on error
    out = []
    for r in sorted(rules, key=lambda r: r["connector"]):
        name = r["connector"]
        if r.get("roles") and not roles & set(r["roles"]):
            continue
        hit = [s for s in r["when"] if s in found]
        if not hit or name in defaults:
            continue
        sid = f"connect:{name}"
        out.append({"id": sid, "action": "connect", "connector": name,
                    "title": titles.get(name) or name, "reason": r["reason"],
                    "evidence": sorted({e for s in hit for e in found[s]})[:3],
                    "declined": sid in declined or name in skipped,
                    "connected": name in connected})
    return out
```

    - `validate()`: `connect` needs `connector` (a name in `packs.available_connectors(kit)`), a non-empty `when`, no `skill`, no `unless`; optional `roles` checked as now; the id `connect:<connector>` unique; after the loop, `set(packs.available_connectors(kit)) & set(packs.available_skills(kit))` → one error per shared name.
  - `commands.py`:
    - `_connected_names()` → `{n for n, c in registry.discover().items() if manage.is_connected(c)}`; `{}` on any error.
    - `cmd_recommend`: `tools = recommend.connector_items(kit, root, st, all_packs, _connected_names())`; `--decline`: `all` → open skill ids (unchanged); `all-tools` → open connector ids; other values: a skill id or name (as now), `connect:<n>` or a connector name `n` → `connect:n` when it is an open connector item; unknown → the 0.9.0 refusal, mentioning tools too. Text: the tools part after the skill part and the "Declined earlier" skill list; "No skill suggestions for this repo." printed only when there are neither skill nor open connector items (and no declined items, as now). `--json` adds `"connectors": tools`.
    - `_tools_line(...)` appended in `cmd_setup`, `cmd_update` and `cmd_change` (roles change only), right after `_suggestions_line`. `cmd_update` keeps only `connect:` ids whose connector the newer kit has (like the skill ids).
    - `cmd_connect`: when a login is saved (code 0 or 1, not `--test`), also remove `connect:<name>` from `declined_recommendations`.
    - `_connect_suggested`: `extra = [(i["connector"], i["reason"]) for i in recommend.open_connectors(connector_items(...))]`; pass to `manage.suggest(defaults, extra=extra)`; after it: role skips → `skipped_connectors` (as now), `result["declined"]` → `connect:<n>` in `declined_recommendations`, saved ones removed from both.
  - `manage.suggest`: after the role defaults loop, the same loop over `extra` with the prompt above; `s` → `result["declined"]`; `a` → the rest of the role defaults to `skipped`, all of `extra` to `declined`. The closing lines add `Not now for this repo: <names>. Say "recommend skills" to see them again.` when `declined` is not empty. "Connect another tool?" excludes the `extra` names already offered.
- [ ] **Step 4: Green** (the full run).
- [ ] **Step 5:** `CHANGELOG.md` Unreleased, `### Added`: "Connector suggestions from the repo's files: `connect` rules in `roles/recommend.json` (for anyone, never for a tool the person's roles already suggest or one already connected); `setup.py recommend` shows "Tools to connect for this repo", `--decline connect:<tool>`, `<tool>` or `all-tools` (`--decline all` stays skills only), `--json` adds `connectors`; one summary line in setup, update and a roles change; `connect --suggested` offers them after the role tools, with their reason; a skipped one is declined." **Name screen, Commit** (ask first): `feat(recommend): suggest connectors from the repo's files; recommend, summary and connect --suggested show them`.

---

### Tasks B1–B3: one connector each (parallel, own worktree)

**Every B task has the same shape** (as in 0.5.0).

**Files:**
- Create: `scripts/personal/connectors/<name>.py`
- Create: `scripts/personal/tests/test_connector_<name>.py`
- Modify: **nothing** (the registry finds the module; CI's loop finds the test). No CHANGELOG line (Task C6 writes it), so the three merges cannot conflict.

**Step 1: Write the failing tests** in `test_connector_<name>.py`: `import helpers` first, then `from fakeserver import ConnectorTestCase, Reply, Seq`. Canned JSON (or XML or text) is inline and follows the vendor's documented shape. Cover: the registry validates the module (`self.connector("<name>")`); `FIELDS`; the auth header on a recorded request; each command's request (path and query) and its output shape (**exact keys**); paging across at least two pages and `truncated`; a 404 for a missing thing; one `run_cli(..., ["<cmd>", ..., "--json"])` end to end; the secret (and any bearer token) absent from stdout, stderr and the error texts; `TestPostGate.test_connector_modules_never_post` (from the foundation suite) passes with the new module. Put a comment block at the top, "To confirm on a live server", with the module's points from design §9.

**Step 2: Run, see them fail:** `python3 scripts/personal/tests/test_connector_<name>.py` → `ModuleNotFoundError: No module named 'personal.connectors.<name>'`.

**Step 3: Implement** `connectors/<name>.py` to the spec below.

**Step 4: Run** the new suite and the full run on both Pythons.

**Step 5: Commit** on `feat/c10-<name>`, after the name screen: `feat(connectors): <name> connector (read-only)`. **Review checkpoint.**

Conventions (0.5.0): `--limit N` where a list is returned (default per command, cap 1000), setting `Result.truncated`; times as ISO-8601 strings as the server gives them; long text clipped with `text.clip` (limit stated); a missing optional value is `null`, never omitted; positional arguments identify a thing. `Result.lines` (plain text) is optional.

---

### Task B1: `sonarqube` — at least 16 tests

- `TITLE = "SonarQube"`. `kind(values) -> ""`. `FIELDS`: `url` ("SonarQube URL, e.g. https://sonar.example.com"); `token` (secret: "User token (My Account → Security → Generate Tokens; type User)"). `auth` → `http.token_as_user(values["token"])`.
- **Server version, once per run:** `_version(ctx) -> tuple[int, int] | None`, cached as `ctx._sonar_version` (Context is a plain dataclass; set with `setattr`): `ctx.client.get_text("/api/server/version")` → `"10.6.0.92116"` → `(10, 6)`; an error or an unparsable answer → `None` (treated as new, see design §5). `NEW = version is None or version >= (10, 2)`; `IMPACT_BLOCKER_INFO = version is None or version >= (2025, 1)`.
- **Paging:** module constants `PAGE = 100` (SonarQube allows 500) and `CAP = 10000` (SonarQube's search cap). A local class `PagePaging` (duck-typed like the 0.5.0 presets): `size = "ps"`; `next(data, params, got)` → `None` when `got == 0` or `p * ps >= min(paging.total, CAP)`; else `(None, {**params, "p": p + 1})`. When `paging.total > CAP` and the limit was not reached, set `truncated` and `extra.capped_at = CAP`.
- **Links:** project `web_url(f"dashboard?id={quote(project)}")`; issue `web_url(f"project/issues?id={quote(project)}&open={key}")`; hotspot `web_url(f"security_hotspots?id={quote(project)}&hotspots={key}")`; rule `web_url(f"coding_rules?open={quote(key)}&rule_key={quote(key)}")`; whoami `web_url("account")`.

| Command | Args | Request | JSON |
|---|---|---|---|
| `whoami` | — | `GET /api/users/current`; `isLoggedIn` false → `ConnectorError(kind="unauthorized")`: "SonarQube treated you as anonymous: the token was not accepted (wrong, expired or revoked)." | item `{user: login, display_name: name, email (or null), server_version: "10.6" or null, url}` |
| `gate` | `project` | `GET /api/qualitygates/project_status?projectKey=` | item `{project, status: projectStatus.status ("OK"\|"ERROR"\|"WARN"\|"NONE"), failed: [{metric: metricKey, comparator, threshold: errorThreshold, actual: actualValue}] (status "ERROR" only), conditions: [{metric, status, comparator, threshold, actual}], new_code_period: {mode, date, parameter} or null (from `period` or `periods[0]`), url: dashboard}` |
| `issues` | `project`; `--severity` (comma list of design §5 values); `--type` (comma list); `--rule KEY`; `--file PATH`; `--new-code`; `--limit` 100 | `GET /api/issues/search` with `resolved=false`, `ps`, `p`, and: component `components=` (new) or `componentKeys=` (old) = `project`, or `project:PATH` with `--file`; `rules=`; `inNewCodePeriod=true`; the translated `severities=`/`types=` (old) or `impactSeverities=`/`impactSoftwareQualities=` (new). Items key `issues` | items `{key, rule, message, severity (or null), type (or null), impacts: [{quality: softwareQuality, severity}], clean_code_attribute (or null), status (issueStatus, else status), file (component after the first ":" or null), line (or null), effort (or null), tags: [], created: creationDate, updated: updateDate, url}`; `extra: {server_version, filter_sent: {param: value}, capped_at (only when capped)}` |
| `hotspots` | `project`; `--status` `TO_REVIEW`\|`REVIEWED` (default `TO_REVIEW`); `--limit` 100 | `GET /api/hotspots/search?project=&status=` (`PagePaging`, items `hotspots`) | items `{key, rule: ruleKey, category: securityCategory, probability: vulnerabilityProbability, status, resolution (or null), message, file, line, url}` |
| `measures` | `project`; `--metrics a,b` (default `bugs,vulnerabilities,code_smells,security_hotspots,coverage,duplicated_lines_density,ncloc,reliability_rating,security_rating,sqale_rating,new_coverage,new_duplicated_lines_density,new_violations`) | `GET /api/measures/component?component=&metricKeys=` | item `{project, name: component.name, measures: {metric: value}, new_code: {metric: period.value or periods[0].value}, missing: [requested metrics the server did not return], url: dashboard}` |
| `rule` | `key` (e.g. `java:S2095`); `--max-chars` 8000 | `GET /api/rules/show?key=` | item `{key, name, language: langName, severity (or null), type (or null), impacts: [{quality, severity}], clean_code_attribute (or null), description (htmlDesc, else descriptionSections[].content joined with their keys as headings, through text.html_to_text; clipped), description_truncated, url}` |

Severity and type translation: one function `_filters(args, version) -> dict` with the tables of design §5; an unknown value → `argparse` error listing the allowed values.

Tests (minimum list): fields; header `Basic base64("tok:")`; the token absent from a 401 error and debug output; `whoami` ok and `isLoggedIn: false`; `server_version` read once for three commands in one run (one recorded `/api/server/version`); `gate` with two failed conditions (exact keys, order kept); `issues` on a 9.9 server: `componentKeys`, `severities=BLOCKER,CRITICAL` for `--severity high`, `types=BUG`; on a 10.6 server: `components`, `impactSeverities=HIGH`, `impactSoftwareQualities=RELIABILITY`; on 2025.1: `--severity blocker` → `impactSeverities=BLOCKER`; an answer with both shapes keeps both; `--file` → `components=proj:src/A.java` and `file` in the item; `--new-code` → `inNewCodePeriod=true`; two pages and `truncated`; the cap (patch `PAGE = 10`, `CAP = 30`; `paging.total: 50`, `--limit 100`) → three pages read, `truncated`, `capped_at: 30`; `hotspots` default status; `measures` with a missing metric; `rule` from `descriptionSections`; a 404 project; `run_cli issues … --json` end to end.

### Task B2: `blackduck` — at least 16 tests

- `TITLE = "Black Duck"`. `kind → ""`. `FIELDS`: `url` ("Black Duck URL, e.g. https://blackduck.example.com"); `token` (secret: "API token (your name → My Access Tokens → Create New Token; read access)"). `auth` → `http.blackduck_token(values["token"])`.
- **Media types** (module constants, design §4.2): `USER = "application/vnd.blackducksoftware.user-4+json"`, `PROJECT = "…project-detail-4+json"`, `VERSION = "…project-detail-5+json"`, `BOM = "…bill-of-materials-6+json"`, `COMPONENT = "…component-detail-5+json"`. Each request uses `ctx.client.get(path, params, accept=…)`.
- **Paging:** `http.Offset(start="offset", size="limit", total="totalCount")`, items `items`, page size 100. Because each endpoint needs its own `Accept`, add a local `_paged(ctx, href, params, accept, limit)` that mirrors `Client.paginate` but passes `accept` (the 0.5.0 `paginate` has no `accept`; do not change the foundation in a B task).
- **Resolve by name:** `_project(ctx, name)`: `GET /api/projects?q=name:<name>&limit=100` (accept `PROJECT`); exact name match, case-insensitive; none → `ConnectorError(kind="not_found")` "No Black Duck project named '<name>'. Try: connectors.py blackduck projects <part of the name>"; several exact matches → `ConnectorError(kind="config")` listing them. `_version(ctx, project, name)`: the project's `_meta.links` rel `versions` href, `q=versionName:<name>`, same rules. Links: `_link(obj, rel)` from `_meta.links[]` (`rel`, `href`); a missing link → `ConnectorError(kind="bad_response")`.
- **Links for items:** project `_meta.href`; version `_meta.href + "/components"`; vulnerability `version href + "/vulnerability-bom"`; component the BOM item's `componentVersion` href, else the version's components link. (Design §9: confirm these open in a browser.)

| Command | Args | Request | JSON |
|---|---|---|---|
| `whoami` | — | `GET /api/current-user` (accept `USER`) | item `{user: userName, display_name: "firstName lastName" (or userName), email (or null), url: base URL}` |
| `projects` | `text`; `--limit` 25 | `GET /api/projects?q=name:<text>` (accept `PROJECT`, paged) | items `{name, description (or null), updated: updatedAt (or null), url}` |
| `versions` | `project`; `--limit` 50 | the project's `versions` link, `sort=updatedAt desc` (accept `VERSION`, paged) | items `{name: versionName, phase, distribution, updated: settingUpdatedAt or updatedAt, url}` |
| `vulns` | `project`; `version`; `--severity` (comma list of `critical,high,medium,low`); `--limit` 100; `--no-fix-versions` | the version's `_meta.links` rel `vulnerable-components` (path `…/vulnerable-bom-components`), accept `BOM`, paged; then upgrade guidance (below) | items `{id: vulnerabilityWithRemediation.vulnerabilityName, source (NVD\|BDSA\|…), severity (lower case), score: overallScore or baseScore, remediation: remediationStatus, component: componentName, component_version: componentVersionName, origin: componentVersionOriginId (or null), related: relatedVulnerability name (or null), fixed_in: {short_term, long_term} or null, url}`; `extra: {fix_versions_read: n, fix_versions_skipped: m}` |
| `components` | `project`; `version`; `--violations`; `--limit` 100 | the version's `components` link, accept `BOM`, `filter=bomPolicy:in_violation` with `--violations`, paged | items `{name: componentName, version: componentVersionName, origins: [externalId], licenses: [licenseDisplay or licenseName], policy_status: policyStatus, review_status: reviewStatus (or null), url}` |
| `policy` | `project`; `version` | the version's `policy-status` link, accept `BOM` | item `{project, version, status: overallStatus, counts: {name: value} from componentVersionStatusCounts, url: version components link}` |

- **Fix versions (`vulns`):** for each distinct `componentVersion` href in the result (in order, at most `MAX_GUIDANCE = 50`), `GET <componentVersion href>/upgrade-guidance` (accept `COMPONENT`); `fixed_in = {"short_term": shortTerm.versionName, "long_term": longTerm.versionName}` (each `null` when absent); a 404 → `null`; past the cap → `null` and counted in `fix_versions_skipped`. `--no-fix-versions` skips them all.
- **Severity filter** on the client side, after paging, before `--limit` is applied (so the limit counts kept items; page through until the limit or the end).

Tests (minimum list): fields; one token exchange for a whole command (exactly one POST recorded, to `/api/tokens/authenticate`, then Bearer on every GET); the API token and the bearer token absent from all output and from a 401 error; each `Accept` header per endpoint (recorded); `whoami`; `projects` with two pages and `truncated`; project resolution: exact match among three results, none (`not_found` with the hint), two exact (`config` listing them); `versions` follows the link (recorded path equals the canned href path); `vulns`: CVE and BDSA items, exact keys, `--severity critical` keeps only those, `fixed_in` from guidance, guidance 404 → `null`, the cap (patch `MAX_GUIDANCE = 1`) → `fix_versions_skipped`, `--no-fix-versions` makes no guidance call; `components --violations` sends the filter; `policy` counts; a missing `_meta` link → `bad_response`; `run_cli vulns … --json` end to end.

### Task B3: `artifactory` — at least 15 tests

- `TITLE = "Artifactory"`. `kind → ""`. `FIELDS`: `url` ("Artifactory URL with /artifactory, e.g. https://artifactory.example.com/artifactory"); `token` (secret: "Access token or identity token (your profile → Generate an Identity Token)"); `maven_repo` (required=False: "Default Maven repository key, e.g. maven-virtual (Enter to skip)"); `npm_repo` (required=False); `go_repo` (required=False). `auth` → `http.bearer(values["token"])`.
- `check(values)`: a URL whose path does not end in `/artifactory` returns nothing (allowed: some set-ups have no context path), but `whoami` answers with a hint when `/api/system/version` gives 404: "Nothing at <url>/api/system/version: does the URL need /artifactory at the end?".
- **User from the token:** `_jwt_user(token) -> str | None`: split on `.`; three parts or `None`; base64url-decode the middle (pad with `=`), JSON; `sub` → the part after the last `/users/`, else `sub` itself; any error → `None`. It never returns or logs anything but that name.
- **Repo choice:** `_repo(ctx, args, key)` → `args.repo` or `ctx.values.get(key)` or `ConnectorError(kind="config")` "Give --repo, or save a default with connect artifactory (the repo key, e.g. maven-virtual)."
- **UI link:** `_ui(ctx, repo, path)` → the saved URL minus a trailing `/artifactory`, plus `/ui/repos/tree/General/<repo>/<path>` (quoted).
- **XML:** `_parse_metadata(text)`: refuse when `<!DOCTYPE` or `<!ENTITY` appears (`ConnectorError(kind="bad_response")`), then `xml.etree.ElementTree.fromstring`; `versioning/versions/version` texts, `versioning/latest`, `versioning/release`, `versioning/lastUpdated` (`YYYYMMDDHHMMSS` → ISO).
- **Coordinates:** `group:artifact` split once on `:`; group dots → slashes. A bad shape → `ConnectorError(kind="config")` "Give group:artifact, e.g. org.apache.commons:commons-text".
- **Go module path:** escape each upper-case letter `X` as `!x` (Go module proxy rule), keep `/`.

| Command | Args | Request | JSON |
|---|---|---|---|
| `whoami` | — | `GET /api/system/version` (any 2xx confirms the token; 401 → unauthorized) | item `{user: _jwt_user(token) or null, display_name: same or "unknown (not a JWT token)", server_version: version (or null), url: UI root (saved URL minus /artifactory, + "/ui/")}` |
| `repos` | `--type` (package type, e.g. `maven`, `npm`, `go`; optional); `--limit` 200 | `GET /api/repositories?packageType=` (a list, no paging) | items `{key, type (LOCAL\|REMOTE\|VIRTUAL\|FEDERATED), package_type: packageType, description (or null), url: _ui(key, "")}` |
| `versions` | `coords` (`g:a`); `--repo KEY` (else `maven_repo`); `--limit` 200 | `GET /<repo>/<g/as/path>/<a>/maven-metadata.xml` with `get_text(accept="application/xml", max_bytes=2_000_000)` | item `{group, artifact, repo, versions: [newest first, as listed reversed], latest (or null), release (or null), updated (or null), count, url: _ui(repo, "<g path>/<a>")}`; `truncated` when versions exceed `--limit` |
| `latest` | `coords`; `--repo KEY` (else `maven_repo`) | `GET /api/search/latestVersion?g=&a=&repos=` (`get_text`) | item `{group, artifact, repo, version (stripped text, or null on 404), url: _ui(repo, "<g path>/<a>/<version>")}` |
| `npm` | `package` (may be `@scope/name`); `--repo KEY` (else `npm_repo`); `--limit` 200 | `GET /api/npm/<repo>/<name, "/" as "%2f">` (`get_json`) | item `{package, repo, dist_tags: {tag: version}, versions: [newest first by time when present, else as listed], published: {version: time} (only the listed ones), count, url: _ui(repo, package)}` |
| `go` | `module`; `--repo KEY` (else `go_repo`); `--limit` 200 | `GET /api/go/<repo>/<escaped module>/@v/list` (`get_text`) | item `{module, repo, versions: [one per line, sorted newest first by semver, pre-releases after their release], count, url: _ui(repo, module)}` |

Tests (minimum list): fields (three optional repo fields; `connect` from env without them works); Bearer header; the token absent from all output, also when it is a JWT (the decoded name may show, the token not); `_jwt_user` for a `jfrt@…/users/ana` token, a `jfac@…/users/ana` token, a non-JWT token, and a broken base64 → `None`; `whoami` 401 and 404 messages; `repos --type maven` query; `versions` parses metadata (exact keys, newest first, `--limit 2` → `truncated`), a `DOCTYPE` answer refused; repo from `--repo` wins over `maven_repo`; no repo at all → `config` error text; `latest` text and 404 → `version: null`; `npm` scoped name sent as `@scope%2fname`, `dist_tags` kept; `go` path case-encoding (`github.com/Azure/x` → `github.com/!azure/x`) and semver sort; the UI link drops `/artifactory`; `run_cli versions … --json` end to end.

---

### Merge B1–B3 (sequential, coordinator)

- [ ] Merge `feat/c10-sonarqube`, `feat/c10-blackduck`, `feat/c10-artifactory` into `feat/connectors-0.10.0` (each after the owner's review of its commit). Disjoint files: no conflicts expected.
- [ ] The full run on both Pythons; `TestPostGate.test_connector_modules_never_post` now scans eight modules.
- [ ] Collect the "To confirm on a live server" notes from the three test files; check they match design §9; add any new point to §9 (a docs commit, asked first).

---

### Task C1: Role defaults and the connector rules (sequential, test first)

**Files:** `roles/dev/role.json`, `roles/qa/role.json`, `roles/architect/role.json`, `roles/recommend.json`; tests `test_roles.py`, `test_recommend.py`, `test_packs.py`.

- [ ] **Step 1: Failing tests.**
  - `test_roles.py`: `CONNECTORS` becomes `{"po": ["jira","confluence","jama"], "pm": [...same], "sm": ["jira","confluence"], "dev": ["bitbucket","jira","jenkins","sonarqube","blackduck","artifactory"], "qa": ["jira","jama","jenkins","sonarqube"], "architect": ["confluence","bitbucket","jira","sonarqube","blackduck"], "em": ["jenkins","bitbucket","jira"]}`; the comment names the owner approval of 2026-10-10.
  - `test_packs.py::TestRealKit::test_the_recommend_file_validates` (unchanged) now covers the connector rules.
  - `test_recommend.py::TestRealConnectorRules`:
    - `test_the_three_rules` — `[r for r in load(KIT)["rules"] if r["action"] == "connect"]` equals the three rules of design §6.2 (connector, when, reason; no roles).
    - `test_a_po_in_a_sonar_and_blackduck_maven_repo` — roles `po`, a repo with `pom.xml` (with `sonar-maven-plugin`) and a `Jenkinsfile` naming `blackduck` → connector ids `["connect:artifactory", "connect:blackduck", "connect:sonarqube"]`.
    - `test_a_developer_gets_none` — roles `dev` in that repo → `[]` (all three are role defaults).
    - `test_qa_gets_artifactory_and_blackduck` — roles `qa` → `["connect:artifactory", "connect:blackduck"]`.
    - `test_architect_gets_artifactory` — roles `architect` → `["connect:artifactory"]`.
    - `test_an_empty_repo_gets_none`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.** Append the names to the three `role.json` files (order as above). Add the three rules to `roles/recommend.json` after the skill rules, exactly as design §6.2 (owner decision 2026-10-10, §12 item 3: artifactory keeps `"when": ["code"]`, Python repos included). Update `about`: "… connect: suggest a connector when a signal is found, for anyone, unless the person's roles already suggest it or it is connected."
- [ ] **Step 4: Green** (the full run; `validate_packs.py` ok).
- [ ] **Step 5:** CHANGELOG Unreleased `### Changed`: "Role defaults: developers also get SonarQube, Black Duck and Artifactory suggested; QA SonarQube; architects SonarQube and Black Duck." **Name screen, Commit** (ask first): `feat(roles): connector defaults and repo rules for SonarQube, Black Duck and Artifactory`.

---

### Task C2: The skills switch and routing (sequential, test first)

**Files:** `template/.claude/skills/sonarqube-findings/{SKILL.md,PROVENANCE.md}`, `template/.claude/skills/blackduck-findings/{SKILL.md,PROVENANCE.md}`, `template/.claude/skills/maven-via-artifactory/{SKILL.md,PROVENANCE.md}`, `template/.claude/skills/connectors/SKILL.md`, `roles/{core,dev,qa,architect}/instructions.md`; tests `test_stack_skills.py`, `test_skill_guidance.py`, `test_roles.py`.

- [ ] **Step 1: Failing tests.**
  - `test_stack_skills.py`: `READ_ONLY_RULE` is split: the two findings skills now carry `READ_ONLY_CONNECTOR_RULE` = "- **Read-only:** work from the kit's read-only connector's output, or from a report the person pastes or exports. Never ask for, see or repeat a token or password, and never change anything in the tool: marking a finding as a false positive, accepted or ignored is the person's decision, made in the tool." (exact text; the other skills that used `READ_ONLY_RULE`, if any, keep it).
  - `TestSonarqubeFindings`: contains `connectors.py sonarqube whoami --json`, `connectors.py sonarqube gate`, `connectors.py sonarqube issues`, `connectors.py sonarqube rule`, "exit code 3", `say *connect sonarqube*`, the project-key line `grep -E '^\s*sonar\.projectKey'` and "never print the whole file"; no longer contains "You never talk to SonarQube yourself" or "## 7. Later: a connector"; never contains `setup.py connect sonarqube` run by Copilot without "in their own terminal".
  - `TestBlackduckFindings`: `connectors.py blackduck vulns`, `policy`, `components`, `--violations`, `fixed_in`, `detect.project.name` read by key only, and "check the mirror" pointing to `ai-sdlc-maven-via-artifactory`; no "## 7. Later: a connector".
  - `TestMavenViaArtifactory`: a section "Check the mirror has the version" with `connectors.py artifactory versions`, `npm`, `go`, "propose only a version in that list", and the not-connected fallback "say the version is not confirmed".
  - `test_skill_guidance.py::TestConnectors`: the connectors skill's command table has rows for `sonarqube`, `blackduck`, `artifactory` with exactly the B commands; its role table equals the packs (existing test, now with the new names); its description names the eight tools and stays at most 1,024 characters; a part "Tools for this repo" mentions `recommend` and "in their own terminal".
  - `test_roles.py`: the dev, qa and architect instructions have the routing lines of design §7.4 (dev: SonarQube, Black Duck, Artifactory; qa: SonarQube; architect: SonarQube, Black Duck); the core "Connectors" line names Jira, Confluence, Bitbucket, Jama, Jenkins, SonarQube, Black Duck and Artifactory; `test_no_client_names_in_copilot_guidance` passes.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** (plain words, short sentences; no client, employer or vendor company name):
  - `sonarqube-findings/SKILL.md`: new section "## 1. Connected?" before "Ask for the report" (renumber): run `python3 .ai-sdlc/kit/connectors.py sonarqube whoami --json`; exit 0 → section 2 "Read with the connector" (project key by key only; `gate`, `issues --file/--rule/--new-code`, `hotspots`, `rule`; cite `url`; `truncated` → offer a narrower filter; `filter_sent` and `server_version` tell which model the server uses); exit 3 → "Ask for the report" as in 0.9.0, and say once "say *connect sonarqube*; you type the login in your own terminal"; another error → relay it (the `ai-sdlc-connectors` table), then ask for a report. The Rules section takes `READ_ONLY_CONNECTOR_RULE` and "Only what you were given" becomes "Only what the connector or the person gives you: do not run the scanner, and do not guess findings". The "Read a finding" table stays (it explains both models). Section 7 is replaced by the connector sections. Description: add "reads SonarQube through the kit's read-only connector when connected" (≤ 1,024 characters).
  - `blackduck-findings/SKILL.md`: the same "Connected?" step and fallback; "Read with the connector" (`vulns <project> <version> --json`, `components … --violations`, `policy`; names asked or read by key only from `detect.project.name` / `detect.project.version.name`); section 3 step 1 takes `fixed_in` from `vulns`; step 2 "Check that the mirror has it" first uses `ai-sdlc-maven-via-artifactory` "Check the mirror has the version" (the `artifactory` connector), then the 0.9.0 manual way. Section 7 replaced.
  - `maven-via-artifactory/SKILL.md`: new section "## 6. Check the mirror has the version" (and a pointer from section 5 step 1): connected → `versions <g:a> --json` / `npm <package> --json` / `go <module> --json` (`--repo` when the person names one; the saved default otherwise); propose only a listed version; not listed → section 3 (stop and report); not connected → ask the person to check the mirror's page and say the version is not confirmed; never treat `latest` as a reason to upgrade on its own.
  - Each `PROVENANCE.md`: a "Changes" line "0.10.0 (2026-10-10): reads through the kit's read-only connector when connected; pasted report otherwise." (still "Written for this kit"; no new upstream idea source).
  - `connectors/SKILL.md`: description and intro name eight tools; three table rows (exact B commands and arguments); "Which connectors fit a role" table per design §6.1; a new short part "## Tools for this repo": `setup.py recommend` may list "Tools to connect for this repo" (a tool the person's roles do not usually use, found from the repo's files); relay it with its reason; the person connects it in their own terminal or says no (`recommend --decline <tool>`).
  - Role instructions: the lines of design §7.4, under "Stack skills", "if you have it"; core "Connectors" line lists the eight tools.
- [ ] **Step 4: Green** (the full run; `validate-skills.py`).
- [ ] **Step 5:** CHANGELOG Unreleased `### Changed`: the skills switch (three skills) and the routing lines. **Name screen, Commit** (ask first): `feat(skills): Sonar and Black Duck findings read through the connectors when connected; the mirror skill checks versions with the artifactory connector`.

---

### Task C3: Onboarding (sequential, test first)

**Files:** `ONBOARDING.md`, `scripts/personal/tests/test_onboarding.py`.

- [ ] **Step 1: Failing tests** in `test_onboarding.py`:
  - `test_close_names_tools_for_this_repo` — step 10 contains "Tools to connect for this repo" and "with its reason".
  - `test_not_now_records_nothing` — owner decision 2026-10-10 (design §12 item 5): step 11 has no `--decline` (in particular no `recommend --decline all-tools`), and says that "not now" records nothing: the tools are offered again next time.
  - `test_step_8_decline_all_is_skills_only` — step 8 still says `recommend --decline all` and adds "(this declines skills only; tools come later)".
  - `test_recommend_skills_relays_tools` — section "Recommend skills" mentions "Tools to connect for this repo", that the person connects in their own terminal, and `recommend --decline <tool>`.
  - `test_connect_a_tool_names_eight` — section "Connect a tool": the names `jira`, `confluence`, `bitbucket`, `jama`, `jenkins`, `sonarqube`, `blackduck`, `artifactory` (the existing test that compares with `registry.names()` then passes).
  - `test_every_command_named_is_real_and_its_flags_belong_to_it` (existing) passes with `--decline all-tools`.
- [ ] **Step 2: Implement.** Step 10: after the role tools, "then each tool under 'Tools to connect for this repo', in one plain sentence with its reason". Step 11: the offer covers both lists; "not now" → record nothing (no `--decline`; the tools are offered again next time), say "say *connect <tool>* at any time". Step 8: the parenthesis above. "Recommend skills": relay the tools part too; a tool is connected by the person in their own terminal (`setup.py connect <name>`), never by Copilot; a no → `recommend --decline <tool>`. "Connect a tool": eight names, and the three new token hints in one line each ("SonarQube: a user token; Black Duck: an API token; Artifactory: an access or identity token, plus your default repository keys if you know them").
- [ ] **Step 3: Green** (the full run). **Name screen, Commit** (ask first): `feat(onboarding): tools suggested for the repo at the close; eight connectors`.

---

### Task C4: End to end, fake tools and CI (sequential, test first)

**Files:** `scripts/personal/tests/fake_tools.py`, `scripts/personal/tests/test_connectors_e2e.py`, `.github/workflows/ci.yml`.

- [ ] **Step 1: Failing tests** in `test_connectors_e2e.py` (subprocesses, as for the five 0.5.0 tools):
  - `test_three_new_tools_end_to_end` — with `env_for(url)` for `sonarqube`, `blackduck`, `artifactory`: `setup.py connect <name> --test` exits 0 with "OK: signed in"; `connectors.py sonarqube gate proj --json`, `issues proj --severity high --json`, `blackduck vulns App 1.0 --json`, `artifactory versions org.example:lib --json`, `npm @scope/pkg --json`, `go github.com/Example/mod --json` each exit 0, valid JSON, every item has `url`; no value of `fake_tools.SECRETS` in any stdout or stderr.
  - `test_blackduck_posts_only_to_authenticate` — the fake server's recorded requests: every POST is to `/api/tokens/authenticate`; everything else is GET.
- [ ] **Step 2: Implement** `fake_tools.py`: `TOKENS` adds `sonarqube`, `blackduck`, `artifactory` (artifactory a JWT-shaped string with `sub` `jfrt@e2e/users/ana`); `BLACKDUCK_BEARER` in `SECRETS`; routes per B task canned answers, each checking its `Authorization` first (Basic token-as-user; `token <api>` on the POST then Bearer; Bearer); `/api/server/version` → `10.6.0.1`; `env_for` adds `AI_SDLC_SONARQUBE_URL/TOKEN`, `AI_SDLC_BLACKDUCK_URL/TOKEN`, `AI_SDLC_ARTIFACTORY_URL/TOKEN/MAVEN_REPO/NPM_REPO/GO_REPO`.
  - `ci.yml` `personal-e2e`, after the Jira lines: one step that runs `connectors.py sonarqube gate`, `blackduck policy`, `artifactory versions` against `fake_tools.py` with env logins, and greps that no token appears in the output.
- [ ] **Step 3: Green** (the full run; replay the `personal-e2e` job locally on both Pythons). **Name screen, Commit** (ask first): `test(connectors): SonarQube, Black Duck and Artifactory end to end; CI step`.

---

### Task C5: Docs (sequential)

**Files:** `README.md`, `docs/how-to.md`, `template/.claude/skills/README.md`.

- [ ] **Step 1: `README.md`**, section "Connectors": eight tools; read-only (GET only; the POSTs are Jama's and Black Duck's token requests); the role table per design §6.1; one sentence on "Tools to connect for this repo" (suggested from the repo's files, for anyone; a no is remembered). The core skill line names eight tools.
- [ ] **Step 2: `docs/how-to.md`** §3 "What each tool asks for, and where to create the token": three rows (SonarQube: URL, user token from My Account → Security; Black Duck: URL, API token from My Access Tokens, read scope; Artifactory: URL with `/artifactory`, access or identity token from the profile page, optional default repository keys). §4 examples: `connectors.py sonarqube gate my-project`, `sonarqube issues my-project --new-code --severity high --json`, `blackduck vulns "My App" 2.3 --json`, `artifactory versions org.apache.commons:commons-text --json`, `artifactory npm @scope/pkg`. Example questions by role: dev "why did the quality gate fail?", "which versions of commons-text does the mirror have?"; architect "open Black Duck policy violations for <project> <version>". §5: `recommend` shows "Tools to connect for this repo" and `--decline all-tools`.
- [ ] **Step 3: `template/.claude/skills/README.md`**: the connectors row names eight tools; the three findings and mirror rows say "reads through the connector when connected".
- [ ] **Step 4:** the full run (`test_onboarding.py` and `test_release.py` read docs). **Name screen, Commit** (ask first): `docs: SonarQube, Black Duck and Artifactory connectors; tools suggested for the repo`.

---

### Task C6: Release 0.10.0 (sequential, test first)

**Files:** `scripts/personal/tests/test_release.py`, `VERSION`, `CHANGELOG.md`, `docs/how-to.md` (version numbers in examples).

- [ ] **Step 1: Failing tests** in `test_release.py`: `test_version` expects `"0.10.0"`; new `test_changelog_0_10_0_has_the_connectors`: the `[0.10.0]` entry contains `"sonarqube"`, `"blackduck"`, `"artifactory"`, `"token exchange"`, `"POST"`, `"impacts"`, `"Tools to connect for this repo"`, `"--decline all-tools"`, `"fixed_in"`, `"maven-metadata.xml"`, `"No AQL"`, `"SharePoint"`, `"live confirmation"`. `test_the_newest_changelog_entry_is_the_version_and_unreleased_is_empty` (existing) must pass: **Unreleased empty**.
- [ ] **Step 2:** `git switch -c release/0.10.0`; run → FAIL.
- [ ] **Step 3:** `VERSION` → `0.10.0`. `CHANGELOG.md`: move every Unreleased line under `## [0.10.0] — <date>` (`### Added` / `### Changed`), and add: the three connectors (fields, auth, commands, read-only; "No AQL (it is a POST)"); SonarQube 9.x–2025.x, both issue models (`severity`/`type` and `impacts`), `filter_sent`; Black Duck token exchange once per run, names not ids, `fixed_in` from upgrade guidance; Artifactory `maven-metadata.xml`, npm dist-tags, Go list, the default repository keys; "Built against canned answers; the points in design §9 need live confirmation"; "SharePoint stays out of scope". Leave `## [Unreleased]` empty.
- [ ] **Step 4: Verify the how-to examples by running them** (a scratch folder outside the repo, `fake_tools.py` for the connector examples): `setup` prints `Set up AI-SDLC 0.10.0 …`; copy the **printed** numbers into `docs/how-to.md`.
- [ ] **Step 5: Full verification, both Pythons** (the full run, `validate_packs.py`, `validate-skills.py`, the `personal-e2e` job replayed).
- [ ] **Step 6: Name screen on the whole branch:** `git diff main...HEAD | grep -n -i -E "$OTHER"` and `git diff main...HEAD | grep -n -E '/Users/|~/work/'` → nothing; `grep -rn -i -E '\b(frq|frequentis)\b' template/.claude/skills/{connectors,sonarqube-findings,blackduck-findings,maven-via-artifactory} roles/*/instructions.md roles/recommend.json ONBOARDING.md` → nothing.
- [ ] **Step 7: Commit** (ask first): `chore(release): kit 0.10.0 — SonarQube, Black Duck and Artifactory connectors`.
- [ ] **Step 8: PR** `release/0.10.0` → `main` (ask before push). Body: what ships, the POST gate, the suggestions, the skills switch, the live-confirmation list, test summary, owner decisions; ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. CI green. **Do not merge yet.**

---

### Task D: Copilot CLI end-to-end re-test (owner, manual, before merge)

On the VM, with the Copilot CLI and a trusted folder, from the `release/0.10.0` copy. **Servers:** the live SonarQube, Black Duck and Artifactory if the owner has access (then also tick the design §9 points that the run shows); otherwise `python3 .ai-sdlc/kit/scripts/personal/tests/fake_tools.py` started in a second terminal, with the logins saved by `connect <name>` against its URL (the fake tokens are in `fake_tools.TOKENS`). Sample repos (synthetic, made by the coordinator): **A** a Maven repo with `sonar-project.properties` (`sonar.projectKey=demo`, plus a `sonar.token=` line to prove it is never printed) and a `Jenkinsfile` naming `blackduck`; **B** a Go module; **C** an npm repo. Note each result in the PR; fixes go on `release/0.10.0` first.

1. **Onboarding as PO in repo A:** step 10 names the role tools (Jira, Confluence, Jama) and "Tools to connect for this repo": SonarQube, Black Duck, Artifactory, each with its reason; step 11 offers once; "not now" → nothing recorded: `recommend` still lists the three as open; an explicit `recommend --decline all-tools` then moves them under "Declined earlier", and `update` from a 9.9.9 copy does not mention them again.
2. **Onboarding as Developer in repo A:** no "Tools to connect for this repo" line (all three are role defaults); "Connectors for your roles" lists six tools.
3. **`connect --suggested` as QA in repo A** (in the person's own terminal): role tools first, then Artifactory and Black Duck with their reasons; `s` on Black Duck → declined, not in `skipped_connectors`; Copilot never runs `connect` itself.
4. **"Why did the quality gate fail?"** in A, SonarQube connected → Copilot runs `whoami`, finds `demo` by key only (the `sonar.token` line never appears in the chat or in a tool call's output), runs `gate demo`, lists the failed conditions with links.
5. **"Fix the blocker issues in src/…"** → `issues demo --severity blocker --file … --json`; one diff per finding, wait for yes; mentions `filter_sent` when the server is 10.2+.
6. **SonarQube not connected** (disconnect first): the skill asks for a pasted report and says once "say *connect sonarqube*"; never asks for a token.
7. **"What does Black Duck say about release 1.0?"** → `vulns <project> 1.0`, `policy`; licence findings handed to the person.
8. **"Upgrade commons-text to fix CVE-…"** → `fixed_in` from `vulns`, then `artifactory versions org.apache.commons:commons-text`; the proposed version is in that list; with a version the fake mirror lacks, Copilot says so and stops (section 3), never adds a repository.
9. **npm and Go in repos C and B:** "which versions of <pkg> does the mirror have?" → `artifactory npm …` / `artifactory go …`, cites the link.
10. **A pasted token** ("here is my Black Duck token: …") → Copilot does not use it, calls it "the token you pasted", tells the person to revoke it.
11. **Read-only:** ask "mark this Sonar issue as false positive" → Copilot says it cannot change SonarQube; the person does it there.
12. **Errors:** a wrong Artifactory URL without `/artifactory` → the hint; an expired Black Duck token → "API token was not accepted"; a TLS error → the CA-bundle advice.

Merge only after this and with the owner's yes.

---

## Self-review

- Design §2 decisions 1–6: Tasks A1, B1–B3. §3 (auth; token as user; token exchange): A1, B1, B2, B3. §4 (commands): B1–B3. §5 (Sonar versions): B1. §6.1 (role defaults): C1. §6.2 (repo suggestions: rules, determinism, recommend, `--decline`, summary, `connect --suggested`, onboarding): A2, C1, C3. §7 (skills, routing, connectors skill): C2. §8 (architecture): A1, A2. §9 (live confirmation): B test-file notes, merge step, Task D. §10 (testing): every task. §11 (out of scope): CHANGELOG (C6). §12 (owner points): Task 0 owner step; C1 step 3 and C3 tests follow the owner's answers to items 3 and 5 (2026-10-10).
- Names used across tasks: `token_as_user`, `TokenExchange`, `blackduck_token`, `Client._exchange`, `TestPostGate`, `connector_items`, `open_connectors`, `_tools_line`, `_connected_names`, `PagePaging`, `_jwt_user`, `READ_ONLY_CONNECTOR_RULE`, `all-tools`, `connect:<name>` — consistent.

## Problems found while planning

1. **`http.basic(token, "")` would not scrub the token** (it is the user name, and `Basic.secrets()` lists only the password and the encoded value). Fix: `token_as_user` (A1).
2. **`Client.paginate` has no `accept`**, but Black Duck needs a vendor media type per endpoint. Fix: a local `_paged` in `blackduck.py` (B2), so the foundation does not change inside a parallel task. A later cleanup may add `accept=` to `paginate`.
3. **SonarQube pages by page number (`p`)**, not by offset, and caps at 10,000. The 0.5.0 `Offset` preset does not fit. Fix: a local `PagePaging` in `sonarqube.py` (B1).
4. **`packs.validate` rejects unknown connector names**, so the connector rules and role defaults cannot land before the B merges. Fix: A2 tests with a stub connector in a temp kit; the real data lands in C1.
5. **`--decline all` in onboarding step 8 would decline tools before step 11 offers them** if it covered tools. Fix: `all` stays skills only; `all-tools` is new (design §12 item 4).
6. **The findings skills' read-only rule is a shared constant** (`READ_ONLY_RULE` in `test_stack_skills.py`). Fix: a new constant for the two skills that now use a connector (C2).
7. **Property files can hold tokens** (`sonar.token`, `blackduck.api.token`). Fix: read the project key and names by key only (C2), proven in Task D step 4.
8. **Black Duck's vulnerable-components answer has no fix version.** Fix: upgrade guidance per distinct component version, capped at 50 (B2).

## Still open (owner)

- ~~Design §12~~ decided 2026-10-10: item 3 keeps `code`; item 5 "not now" records nothing (C1 and C3 updated); the other items as written.
- The client's SonarQube, Black Duck and Artifactory **versions and URLs** (design §11); the live checks of design §9 (Task D, or later with live access).
- SharePoint stays out of scope.
