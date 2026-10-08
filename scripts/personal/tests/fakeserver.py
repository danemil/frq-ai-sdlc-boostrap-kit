#!/usr/bin/env python3
"""A fake HTTP server for connector tests: no network, canned JSON, recorded requests.

    with FakeServer({"/rest/api/2/myself": {"name": "ana"}}) as srv:
        client = http.Client(srv.url, http.bearer("t"))
        client.get_json("/rest/api/2/myself")
        srv.requests[0].headers["Authorization"]     # "Bearer t"

A route maps a path (without the query string) to one of:
- a dict or list: served as JSON with status 200;
- a `Reply(status, body, headers)`: body is JSON-encoded unless it is str or bytes;
- a callable `f(request) -> Reply | dict | list`, for answers that depend on the query;
- a list of `Reply`s wrapped in `Seq(...)`: served in turn, the last one repeating
  (e.g. `Seq(Reply(429, headers={"Retry-After": "0"}), Reply(200, {...}))`).

An unknown path answers 404 with a JSON error. Requests made through the server as a
proxy (absolute-URI request lines) are recorded too; `request.target` keeps the raw
request target and `request.path` its path part. Stdlib only; runs in a thread.

`ConnectorTestCase` is the base class for connector tests (see its docstring).
Import `helpers` first, so `personal` is importable.
"""
from __future__ import annotations

import importlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.parse
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock


@dataclass
class Reply:
    status: int = 200
    body: object = None
    headers: dict = field(default_factory=dict)


class Seq:
    """Replies served in turn; the last one repeats."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.i = 0

    def next(self):
        reply = self.replies[min(self.i, len(self.replies) - 1)]
        self.i += 1
        return reply


@dataclass
class Request:
    method: str
    target: str
    path: str
    query: dict
    headers: dict
    body: bytes


class FakeServer:
    def __init__(self, routes=None):
        self.routes = dict(routes or {})
        self.requests: list[Request] = []
        self._server = None
        self._thread = None

    # -- lifecycle --
    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    def start(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):  # keep test output quiet
                pass

            def _serve(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                parts = urllib.parse.urlsplit(self.path)
                req = Request(self.command, self.path, parts.path or "/",
                              urllib.parse.parse_qs(parts.query), dict(self.headers.items()), body)
                owner.requests.append(req)
                reply = owner._answer(req)
                data = reply.body
                if data is None:
                    data = b""
                elif isinstance(data, str):
                    data = data.encode("utf-8")
                elif not isinstance(data, bytes):
                    data = json.dumps(data).encode("utf-8")
                self.send_response(reply.status)
                headers = {"Content-Type": "application/json"}
                headers.update(reply.headers)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _serve

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        kwargs={"poll_interval": 0.05}, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    # -- routing --
    def _answer(self, req) -> Reply:
        route = self.routes.get(req.path)
        if route is None:
            return Reply(404, {"errorMessages": [f"no route for {req.path}"]})
        if isinstance(route, Seq):
            route = route.next()
        if callable(route) and not isinstance(route, Reply):
            route = route(req)
        if isinstance(route, Reply):
            return route
        return Reply(200, route)


class ConnectorTestCase(unittest.TestCase):
    """A test case for connectors: its own config folder, no AI_SDLC_* or proxy variables
    from the developer's shell, and helpers to run a connector against a FakeServer.

        class TestJira(ConnectorTestCase):
            def test_whoami_dc(self):
                srv = self.server({"/rest/api/2/myself": {...}})
                c = self.connector("jira")
                ctx = self.context(c, {"url": srv.url, "token": "t"}, kind="dc")
                result = self.run_command(c, ctx, ["whoami"])
    """

    PROXY_VARS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("AI_SDLC_") and k.upper() not in self.PROXY_VARS
               and k not in ("SSL_CERT_FILE", "XDG_CONFIG_HOME")}
        env["AI_SDLC_CONFIG_DIR"] = str(self.base / "config")
        env["NO_PROXY"] = env["no_proxy"] = "127.0.0.1,localhost"
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def server(self, routes) -> FakeServer:
        srv = FakeServer(routes).start()
        self.addCleanup(srv.stop)
        return srv

    def connector(self, name):
        """The shipped connector `name`, loaded and validated by the registry."""
        from personal.connectors import registry
        return registry.from_module(name, importlib.import_module(f"personal.connectors.{name}"))

    def context(self, connector, values, kind=None, **client_kwargs):
        """A Context for `values`; `kind` forces "cloud"/"dc", auth included (the fake server
        is 127.0.0.1, which the URL rule calls Data Center)."""
        from personal.connectors import registry
        return registry.open_context(connector, values, kind=kind, sleep=lambda s: None,
                                     **client_kwargs)

    def run_command(self, connector, ctx, argv):
        """Parse `argv` with connectors.py's real parser, then run the command: a Result."""
        cli = _connectors_cli()
        args = cli.parser({connector.name: connector}).parse_args([connector.name, *argv])
        cmd = connector.whoami if args.command == "whoami" else connector.commands[args.command]
        return cmd.run(ctx, args)

    def run_cli(self, connector, argv, values=None):
        """connectors.py end to end with `values` saved: (exit code, stdout, stderr)."""
        from personal.connectors import store
        if values is not None:
            store.save(connector.name, values)
        cli = _connectors_cli()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main([connector.name, *argv], connectors={connector.name: connector},
                        out=out, err=err, client_kwargs={"sleep": lambda s: None})
        return code, out.getvalue(), err.getvalue()


def _connectors_cli():
    kit = str(Path(__file__).resolve().parents[3])
    if kit not in sys.path:
        sys.path.insert(0, kit)
    import connectors  # the kit-root connectors.py
    return connectors


def free_port() -> int:
    """A local port nothing listens on (for connection-refused tests)."""
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
