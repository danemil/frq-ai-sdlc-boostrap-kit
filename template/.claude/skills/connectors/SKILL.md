---
name: connectors
description: Read facts from Jira, Confluence, Bitbucket Data Center, Jama and Jenkins through the kit's read-only connectors, and cite each item's link. Use when the person asks about issues, sprints, pages, pull requests, branches, requirements, test runs, builds or test reports in those tools, says "connect Jira" (or another tool), or a connector command fails or says it is not connected.
---

# Connectors (read-only)

The kit reads five tools from the command line: `jira`, `confluence`, `bitbucket` (Data Center), `jama` and `jenkins`. The person saves their own login once, in their own terminal. You only run the read commands below, from the repo root, and relay what they return.

## Rules

- **Never touch a secret.** Never ask for, accept, look at, paste, store, repeat or write down a token, password, API key or client secret. Never set an `AI_SDLC_*` variable for the person, and never open or print the files in `~/.config/ai-sdlc/connectors/` (or `$AI_SDLC_CONFIG_DIR`). If the person pastes a secret into the chat, do not use it or repeat it. Tell them: "Please revoke that token now (it was shared in a chat) and create a new one; then save it yourself with the connect command in your own terminal."
- **Read-only.** These commands only read. Never say you created, changed, moved, commented on, approved, posted or triggered anything in those tools. To change something there, write the text for the person to post themselves.
- **Cite every item.** Every item in the output has a `url`. Put the link next to each fact you use. No link, no claim.
- **Facts only.** Summarise what the output says; never invent an issue, field, status, date or person. If a field is `null` or missing, say it is not set. If `truncated` is `true`, say there are more and offer a higher `--limit`.
- **Evidence, not verdicts.** Say "evidence found" or "evidence not found", never "compliant", "done" or "approved". The person decides.
- **The team, not individuals.** Talk about the work, the flow and the team. Never rank, compare or judge people by their issues, pull requests, builds or test results.

## Is it connected?

Run `python3 .ai-sdlc/kit/setup.py connections`. It lists each connector with its URL, user, kind, last test and source (file or environment), never a secret.

If the one you need is not connected (or a command exits with code 3), tell the person to run this **themselves, in their own terminal** (not through you). It asks for the URL and login, and types secrets hidden:

```
python3 .ai-sdlc/kit/setup.py connect <name>
```

When they say it is done, or ask you to test it, run `python3 .ai-sdlc/kit/setup.py connect <name> --test`. It uses the saved login, asks nothing, and makes one read-only call. `python3 .ai-sdlc/kit/setup.py disconnect <name>` deletes a saved login, if they ask.

## Read data

```
python3 .ai-sdlc/kit/connectors.py <name> <command> [arguments] --json
```

Always add `--json`. The output is `{"connector", "command", "source", "item"}` for one thing, or `{"connector", "command", "source", "items", "count", "truncated"}` for a list. Quote JQL, CQL and other text with spaces in double quotes. `python3 .ai-sdlc/kit/connectors.py <name> <command> -h` shows every option.

| Connector | Commands |
|---|---|
| `jira` | `whoami` · `search "<JQL>" [--limit N] [--fields a,b]` · `issue <KEY> [--changelog] [--links]` · `sprints <board-id> [--state active,future,closed] [--limit N]` |
| `confluence` | `whoami` · `page <id> [--format text\|storage] [--max-chars N]` · `search "<CQL or words>" [--space KEY] [--limit N]` |
| `bitbucket` | `whoami` · `prs <project>/<repo> [--state OPEN\|MERGED\|DECLINED\|ALL] [--limit N]` · `pr <project>/<repo>/<id> [--diff] [--comments]` · `branches <project>/<repo> [--filter TEXT] [--limit N]` |
| `jama` | `whoami` · `item <id>` · `search "<words>" [--project ID] [--type ID] [--limit N]` · `relationships <id> [--direction up\|down\|both]` · `testruns (--cycle ID \| --plan ID) [--limit N]` |
| `jenkins` | `whoami` · `job <folder/job>` · `build <folder/job> <number\|last\|lastSuccessful\|lastFailed>` · `tests <folder/job> <number\|last> [--all]` |

Exit codes: `0` ok, `1` error (a plain message on stderr), `2` wrong arguments, `3` not connected.

## When it fails

Relay the message in plain words, then the fix:

| The message says | Tell the person |
|---|---|
| not connected (exit 3) | Run `python3 .ai-sdlc/kit/setup.py connect <name>` in your own terminal. |
| 401 Unauthorized | The login was not accepted (wrong or expired token, or the wrong user or email). Create a new token and run the connect command again, in your own terminal. |
| 403 Forbidden | You are signed in, but this account may not read that. Ask the tool's admin for read access. |
| 404 Not Found | Check the key, id or path, and that this account can see it. |
| TLS certificate could not be verified | Your company probably uses its own certificate authority. Ask IT for its PEM file, then run the connect command again and give that file as the CA bundle. Verification is never switched off. |
| proxy, 407, tunnel failed | The company proxy blocked or wants a login. Check `HTTPS_PROXY` / `NO_PROXY` with IT. |
| name could not be found (DNS), timeout, connection refused | Check the URL, and whether the VPN is on. |
| 429 or 5xx | The server is busy or had a problem. Try again in a minute. |

Never work around an error by asking for the login, by calling the tool's web API another way, or by switching certificate checks off.

## Which connectors fit a role

The person's setup summary names the connectors their roles usually need. Suggest those first; anyone may connect any of the five.
