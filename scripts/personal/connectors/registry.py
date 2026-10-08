"""Data-driven connector discovery, and the contract every connector module follows.

Every `scripts/personal/connectors/<name>.py` that is not a foundation module (and
does not start with `_`) is a connector. Adding one touches no shared file. It declares:

    TITLE = "Jira"                         # shown to the person
    FIELDS = [Field("url", "Jira URL"), Field("token", "Token", secret=True), ...]
    def auth(values) -> http.Auth          # from the saved values
    def kind(values) -> str                # optional: "cloud", "dc" or "" (default "")
    def check(values) -> str | None        # optional: a plain reason the values are unusable
    WHOAMI = Command("who you are signed in as", run=...)   # read-only identity call
    COMMANDS = {"search": Command("...", run=..., args=...), ...}

The first field must be `url`. Every connector also gets an optional `ca_bundle`
field. A command's `run(ctx, args)` gets a `Context` (client, values, kind, name)
and the parsed argparse namespace, and returns a `Result`. WHOAMI's item must carry
"user" (a login or account id) and "display_name".
"""
from __future__ import annotations

import importlib
import importlib.util
import re
import sys
from argparse import Namespace
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from . import http, store

FOUNDATION = {"__init__", "store", "http", "registry", "manage", "text"}
HERE = Path(__file__).resolve().parent
CA_FIELD_KEY = "ca_bundle"
_KEY = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class Field:
    key: str                                   # stored key; env var AI_SDLC_<NAME>_<KEY>
    prompt: str                                # what connect asks
    secret: bool = False                       # asked with getpass, never printed
    required: bool = True
    identity: bool = False                     # shown as "user" by `connections`
    when: Optional[Callable[[dict], bool]] = None   # ask only when this is true of the values so far
    help: str = ""                             # one line shown before the prompt


@dataclass(frozen=True)
class Command:
    help: str
    run: Callable[[Any, Namespace], "Result"]
    args: Optional[Callable[[Any], None]] = None   # args(argparse parser): add arguments


@dataclass
class Result:
    item: Optional[dict] = None                # one thing (issue, page, build) ...
    items: Optional[list] = None               # ... or a list; every dict carries "url"
    truncated: bool = False                    # more items exist than `--limit` allowed
    lines: Optional[list] = None               # plain-text form; a generic one when None
    extra: dict = field(default_factory=dict)  # more top-level keys for --json


@dataclass
class Context:
    name: str
    client: http.Client
    values: dict                               # saved values; read secrets only for auth
    kind: str


CA_FIELD = Field(CA_FIELD_KEY, "CA bundle file for your company's certificates "
                 "(Enter to skip)", required=False,
                 help="Only if your company inspects TLS traffic; a PEM file path.")


@dataclass(frozen=True)
class Connector:
    name: str
    title: str
    fields: tuple
    auth: Callable[[dict], http.Auth]
    kind: Callable[[dict], str]
    check: Callable[[dict], Optional[str]]
    whoami: Command
    commands: dict
    module: Any

    @property
    def keys(self) -> list[str]:
        return [f.key for f in self.fields]

    def applicable(self, values) -> list[Field]:
        """The fields that apply given `values` (a field's `when` decides)."""
        return [f for f in self.fields if f.when is None or f.when(values)]

    def missing(self, values) -> list[Field]:
        return [f for f in self.applicable(values) if f.required and not values.get(f.key)]

    def identity(self, values) -> str:
        for f in self.fields:
            if f.identity and values.get(f.key):
                return values[f.key]
        return ""


def _module_errors(name, mod) -> list[str]:
    errs = []
    if not isinstance(getattr(mod, "TITLE", None), str):
        errs.append("TITLE must be a string")
    fields = getattr(mod, "FIELDS", None)
    if not isinstance(fields, (list, tuple)) or not fields or \
            not all(isinstance(f, Field) for f in fields):
        errs.append("FIELDS must be a non-empty list of registry.Field")
    else:
        keys = [f.key for f in fields]
        if keys[0] != "url":
            errs.append("the first field must be 'url'")
        if len(set(keys)) != len(keys) or any(not _KEY.match(k) for k in keys):
            errs.append("field keys must be unique lower_snake_case")
        if CA_FIELD_KEY in keys:
            errs.append(f"'{CA_FIELD_KEY}' is added by the registry; do not declare it")
    if not callable(getattr(mod, "auth", None)):
        errs.append("auth(values) must be defined")
    if not isinstance(getattr(mod, "WHOAMI", None), Command):
        errs.append("WHOAMI must be a registry.Command")
    cmds = getattr(mod, "COMMANDS", None)
    if not isinstance(cmds, dict) or not all(isinstance(c, Command) for c in cmds.values()):
        errs.append("COMMANDS must be a dict of registry.Command")
    elif "whoami" in cmds:
        errs.append("'whoami' comes from WHOAMI; do not put it in COMMANDS")
    return [f"connector {name}: {e}" for e in errs]


def from_module(name, mod) -> Connector:
    errs = _module_errors(name, mod)
    if errs:
        raise ValueError("; ".join(errs))
    return Connector(
        name=name, title=mod.TITLE, fields=tuple(mod.FIELDS) + (CA_FIELD,), auth=mod.auth,
        kind=getattr(mod, "kind", None) or (lambda values: ""),
        check=getattr(mod, "check", None) or (lambda values: None),
        whoami=mod.WHOAMI, commands=dict(mod.COMMANDS), module=mod)


def _load_file(path) -> Any:
    path = Path(path)
    mod_name = f"personal.connectors._extra_{path.stem}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def names(folder=HERE) -> list[str]:
    """The connector module names in `folder` (a glob; foundation and _private skipped)."""
    return sorted(p.stem for p in Path(folder).glob("*.py")
                  if p.stem not in FOUNDATION and not p.stem.startswith("_"))


def discover(extra=()) -> dict[str, Connector]:
    """{name: Connector} for every connector module, plus `extra` module files (tests)."""
    out = {}
    for name in names():
        out[name] = from_module(name, importlib.import_module(f"{__package__}.{name}"))
    for path in extra:
        name = Path(path).stem
        out[name] = from_module(name, _load_file(path))
    return dict(sorted(out.items()))


def open_context(connector, values, **client_kwargs) -> Context:
    """A Context with a client for the saved `values` (raises http.ConnectorError)."""
    client = http.Client(values.get("url", ""), connector.auth(values),
                         ca_bundle=values.get(CA_FIELD_KEY) or None, **client_kwargs)
    return Context(connector.name, client, dict(values), connector.kind(values) or "")


def load_values(connector) -> dict | None:
    return store.load(connector.name, connector.keys)
