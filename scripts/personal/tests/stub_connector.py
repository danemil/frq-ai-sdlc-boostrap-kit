"""A stub connector, used only by tests: proves the registry, setup.py connect and
connectors.py work end to end against tests/fakeserver.py. It is not in
scripts/personal/connectors/, so the kit never offers it.

It is also the smallest worked example of the connector contract (registry.py).
"""
from __future__ import annotations

from personal.connectors import http
from personal.connectors.registry import Command, Field, Result

TITLE = "Stub"
FIELDS = [
    Field("url", "Stub URL"),
    Field("user", "User name (Enter for a token-only login)", required=False, identity=True),
    Field("token", "Token", secret=True),
]


def kind(values) -> str:
    return "dc"


def auth(values) -> http.Auth:
    if values.get("user"):
        return http.basic(values["user"], values["token"])
    return http.bearer(values["token"])


def check(values):
    if "forbidden.example" in values.get("url", ""):
        return "The stub does not support that host."
    return None


def _whoami(ctx, args) -> Result:
    me = ctx.client.get_json("/api/me")
    return Result(item={"user": me.get("login", ""), "display_name": me.get("name", ""),
                        "url": ctx.client.web_url("/profile")})


def _things_args(p):
    p.add_argument("--limit", type=int, default=50)


def _things(ctx, args) -> Result:
    raw, truncated = ctx.client.paginate("/api/things", items="values",
                                         paging=http.Offset(), limit=args.limit, page_size=2)
    items = [{"id": t["id"], "name": t["name"], "url": ctx.client.web_url(f"/things/{t['id']}")}
             for t in raw]
    return Result(items=items, truncated=truncated)


WHOAMI = Command("who you are signed in as", run=_whoami)
COMMANDS = {"things": Command("list things", run=_things, args=_things_args)}
