#!/usr/bin/env python3
"""Connectors foundation: store, http client, registry, connect/connections/disconnect,
and the connectors.py CLI, against tests/fakeserver.py (no network)."""
import base64
import contextlib
import io
import json
import os
import socket
import ssl
import stat
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import helpers
from fakeserver import ConnectorTestCase, Reply, Seq, free_port
from personal.connectors import http, manage, registry, store, text

sys.path.insert(0, str(helpers.KIT))
import connectors as connectors_cli  # noqa: E402  the kit-root connectors.py

STUB_FILE = Path(__file__).resolve().parent / "stub_connector.py"
NAME = "stub_connector"
SECRET = "s3cr3t-T0KEN-value-42"
ME = {"login": "ana", "name": "Ana Pop"}


def stub_registry():
    return registry.discover(extra=[STUB_FILE])


class Base(ConnectorTestCase):
    """Each test gets its own config folder and an environment with no AI_SDLC_* or proxy."""

    def setUp(self):
        super().setUp()
        self.connectors = stub_registry()
        self.stub = self.connectors[NAME]

    def save_stub(self, url, **extra):
        return store.save(NAME, {"url": url, "token": SECRET, **extra})

    def connect(self, *answers, secret=SECRET, isatty=True, test_only=False):
        """Run connect with scripted answers; returns (code, lines, everything shown)."""
        shown, queue = [], list(answers)

        def ask(prompt):
            shown.append(prompt)
            return queue.pop(0) if queue else ""

        def ask_secret(prompt):
            shown.append(prompt)
            return secret

        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code, lines = manage.connect(NAME, test_only=test_only, connectors=self.connectors,
                                         isatty=isatty, ask=ask, ask_secret=ask_secret,
                                         say=shown.append)
        return code, lines, "\n".join(shown + lines) + out.getvalue()


# --- store ---------------------------------------------------------------------------

class TestStore(Base):
    def test_save_makes_a_private_folder_and_file(self):
        self.addCleanup(os.umask, os.umask(0o022))
        path = self.save_stub("https://x.example")
        self.assertEqual(path, self.base / "config/connectors" / f"{NAME}.json")
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        self.assertEqual(json.loads(path.read_text())["values"]["token"], SECRET)

    def test_save_tightens_an_existing_loose_folder(self):
        folder = self.base / "config/connectors"
        folder.mkdir(parents=True, mode=0o755)
        os.chmod(folder, 0o755)
        self.save_stub("https://x.example")
        self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)

    def test_save_is_atomic_and_leaves_no_temp_file(self):
        path = self.save_stub("https://one.example")
        with mock.patch.object(store.json, "dump", side_effect=RuntimeError("disk full")):
            with self.assertRaises(RuntimeError):
                self.save_stub("https://two.example")
        self.assertEqual(json.loads(path.read_text())["values"]["url"], "https://one.example")
        self.assertEqual([p.name for p in path.parent.iterdir()], [path.name])

    def test_save_keeps_the_last_test(self):
        self.save_stub("https://x.example")
        store.record_test(NAME, True, "OK", "ana")
        self.save_stub("https://y.example")
        self.assertTrue(store.read_file(NAME)["last_test"]["ok"])

    def test_xdg_config_home_when_no_override(self):
        del os.environ["AI_SDLC_CONFIG_DIR"]
        os.environ["XDG_CONFIG_HOME"] = str(self.base / "xdg")
        self.assertEqual(store.connectors_dir(), self.base / "xdg/ai-sdlc/connectors")
        del os.environ["XDG_CONFIG_HOME"]
        self.assertEqual(store.connectors_dir(), Path.home() / ".config/ai-sdlc/connectors")

    def test_env_overrides_the_file(self):
        self.save_stub("https://file.example")
        os.environ["AI_SDLC_STUB_CONNECTOR_URL"] = "https://env.example"
        values = store.load(NAME, self.stub.keys)
        self.assertEqual(values, {"url": "https://env.example", "token": SECRET})
        self.assertEqual(store.source(NAME, self.stub.keys), "file+env")

    def test_env_alone_is_enough(self):
        os.environ["AI_SDLC_STUB_CONNECTOR_URL"] = "https://env.example"
        os.environ["AI_SDLC_STUB_CONNECTOR_TOKEN"] = SECRET
        self.assertEqual(store.load(NAME, self.stub.keys)["token"], SECRET)
        self.assertEqual(store.source(NAME, self.stub.keys), "env")
        self.assertFalse(store.file_for(NAME).exists())

    def test_bad_names_are_refused(self):
        for bad in ("../x", "Jira", "", "a/b"):
            with self.assertRaises(ValueError):
                store.file_for(bad)


# --- http client -------------------------------------------------------------------------

class TestHttp(Base):
    def test_bearer_header(self):
        srv = self.server({"/api/me": ME})
        http.Client(srv.url, http.bearer(SECRET)).get_json("/api/me")
        self.assertEqual(srv.requests[0].headers["Authorization"], f"Bearer {SECRET}")

    def test_basic_header(self):
        srv = self.server({"/api/me": ME})
        http.Client(srv.url, http.basic("ana@x.example", SECRET)).get_json("/api/me")
        want = base64.b64encode(f"ana@x.example:{SECRET}".encode()).decode()
        self.assertEqual(srv.requests[0].headers["Authorization"], f"Basic {want}")

    def test_oauth_client_credentials_then_bearer(self):
        srv = self.server({"/rest/oauth/token": {"access_token": "tok-123", "expires_in": 3600},
                           "/rest/v1/users/current": {"data": {"username": "ana"}}})
        c = http.Client(srv.url, http.oauth_client_credentials("cid", SECRET))
        c.get_json("/rest/v1/users/current")
        c.get_json("/rest/v1/users/current")
        token_req, call, call2 = srv.requests
        self.assertEqual((token_req.method, token_req.path), ("POST", "/rest/oauth/token"))
        self.assertEqual(token_req.body, b"grant_type=client_credentials")
        self.assertEqual(token_req.headers["Authorization"],
                         "Basic " + base64.b64encode(f"cid:{SECRET}".encode()).decode())
        self.assertEqual(call.headers["Authorization"], "Bearer tok-123")
        self.assertEqual(call2.headers["Authorization"], "Bearer tok-123")  # token reused

    def test_oauth_bad_client_secret_is_plain(self):
        srv = self.server({"/rest/oauth/token": Reply(401, {"error": "invalid_client"})})
        c = http.Client(srv.url, http.oauth_client_credentials("cid", SECRET))
        with self.assertRaises(http.ConnectorError) as cm:
            c.get_json("/x")
        self.assertIn("client ID or client secret was not accepted", str(cm.exception))

    def test_only_get_requests_are_sent(self):
        c = http.Client("https://x.example", http.bearer(SECRET))
        with self.assertRaises(http.ConnectorError) as cm:
            c._send("POST", c.url("/x"), {}, b"{}", "application/json")
        self.assertIn("read-only", str(cm.exception))

    def test_retries_429_then_succeeds(self):
        srv = self.server({"/api/me": Seq(Reply(429, {}, {"Retry-After": "2"}), Reply(200, ME))})
        waits = []
        data = http.Client(srv.url, http.bearer(SECRET), sleep=waits.append).get_json("/api/me")
        self.assertEqual(data, ME)
        self.assertEqual(len(srv.requests), 2)
        self.assertEqual(waits, [2.0])

    def test_retries_5xx_with_backoff_then_gives_up_plainly(self):
        srv = self.server({"/api/me": Reply(503, {})})
        waits = []
        c = http.Client(srv.url, http.bearer(SECRET), sleep=waits.append, retries=2, backoff=0.5)
        with self.assertRaises(http.ConnectorError) as cm:
            c.get_json("/api/me")
        self.assertEqual(waits, [0.5, 1.0])
        self.assertEqual((cm.exception.kind, cm.exception.status), ("server", 503))

    def test_retry_after_is_capped(self):
        srv = self.server({"/x": Seq(Reply(429, {}, {"Retry-After": "3600"}), Reply(200, {}))})
        waits = []
        http.Client(srv.url, http.bearer(SECRET), sleep=waits.append).get_json("/x")
        self.assertEqual(waits, [http.MAX_WAIT])

    def test_plain_errors_for_401_403_404(self):
        srv = self.server({"/a": Reply(401, {}), "/b": Reply(403, {"message": "no"}),
                           "/c": Reply(404, {})})
        c = http.Client(srv.url, http.bearer(SECRET))
        for path, kind, words in (("/a", "unauthorized", "credentials were not accepted"),
                                  ("/b", "forbidden", "may not read it"),
                                  ("/c", "not_found", "check the id")):
            with self.assertRaises(http.ConnectorError) as cm:
                c.get_json(path)
            self.assertEqual(cm.exception.kind, kind)
            self.assertIn(words, str(cm.exception))

    def test_a_secret_echoed_by_the_server_is_scrubbed(self):
        srv = self.server({"/a": Reply(400, {"message": f"bad token {SECRET}"})})
        with self.assertRaises(http.ConnectorError) as cm:
            http.Client(srv.url, http.bearer(SECRET)).get_json("/a")
        self.assertNotIn(SECRET, str(cm.exception))
        self.assertIn("<redacted>", str(cm.exception))

    def test_connection_refused_is_plain(self):
        c = http.Client(f"http://127.0.0.1:{free_port()}", http.bearer(SECRET))
        with self.assertRaises(http.ConnectorError) as cm:
            c.get_json("/x")
        self.assertEqual(cm.exception.kind, "refused")
        self.assertIn("connection refused", str(cm.exception))

    def test_tls_dns_and_proxy_failures_are_plain(self):
        c = http.Client("https://jira.example.com", http.bearer(SECRET))
        url = c.url("/x")
        cert = ssl.SSLCertVerificationError(1, "certificate verify failed")
        cert.verify_message = "self-signed certificate in certificate chain"
        e = c._net_error(urllib.error.URLError(cert), url)
        self.assertEqual(e.kind, "tls")
        self.assertIn("AI_SDLC_CA_BUNDLE", str(e))
        self.assertIn("never switched off", str(e))
        e = c._net_error(urllib.error.URLError(socket.gaierror(8, "nodename nor servname")), url)
        self.assertEqual((e.kind, "DNS" in str(e)), ("dns", True))
        e = c._net_error(OSError("Tunnel connection failed: 407 Proxy Authentication Required"),
                         url)
        self.assertEqual((e.kind, e.status), ("proxy", 407))
        e = c._net_error(urllib.error.URLError(socket.timeout("timed out")), url)
        self.assertEqual(e.kind, "timeout")

    def test_refused_proxy_is_named_without_its_credentials(self):
        os.environ["HTTPS_PROXY"] = os.environ["https_proxy"] = \
            f"http://bob:pw@127.0.0.1:{free_port()}"
        del os.environ["NO_PROXY"], os.environ["no_proxy"]
        c = http.Client("https://jira.example.com", http.bearer(SECRET))
        with self.assertRaises(http.ConnectorError) as cm:
            c.get_json("/x")
        self.assertEqual(cm.exception.kind, "proxy")
        self.assertIn("127.0.0.1", str(cm.exception))
        self.assertNotIn("pw", str(cm.exception))

    def test_http_proxy_env_is_used(self):
        srv = self.server({"/api/me": ME})
        os.environ["HTTP_PROXY"] = os.environ["http_proxy"] = srv.url
        del os.environ["NO_PROXY"], os.environ["no_proxy"]
        c = http.Client("http://jira.example.invalid", http.bearer(SECRET), allow_http=True)
        self.assertEqual(c.get_json("/api/me"), ME)
        self.assertEqual(srv.requests[0].target, "http://jira.example.invalid/api/me")

    def test_no_proxy_bypasses_the_proxy(self):
        srv = self.server({"/api/me": ME})
        os.environ["HTTP_PROXY"] = os.environ["http_proxy"] = f"http://127.0.0.1:{free_port()}"
        self.assertEqual(http.Client(srv.url, http.bearer(SECRET)).get_json("/api/me"), ME)
        self.assertEqual(srv.requests[0].target, "/api/me")

    def test_ca_bundle_goes_to_create_default_context(self):
        bundle = self.base / "corp.pem"
        bundle.write_text("pem")
        env_bundle = self.base / "env.pem"
        env_bundle.write_text("pem")
        with mock.patch.object(http.ssl, "create_default_context") as cdc:
            http.ssl_context(str(bundle))
            cdc.assert_called_with(cafile=str(bundle))
            cdc.return_value.load_default_certs.assert_called_with()  # system CAs kept
            os.environ["SSL_CERT_FILE"] = str(env_bundle)
            http.ssl_context(None)
            cdc.assert_called_with(cafile=str(env_bundle))
            os.environ["AI_SDLC_CA_BUNDLE"] = str(bundle)
            http.ssl_context(None)
            cdc.assert_called_with(cafile=str(bundle))
            del os.environ["AI_SDLC_CA_BUNDLE"], os.environ["SSL_CERT_FILE"]
            http.ssl_context(None)
            cdc.assert_called_with()

    def test_connector_ca_bundle_reaches_the_client(self):
        bundle = self.base / "corp.pem"
        bundle.write_text("pem")
        ctx = registry.open_context(self.stub, {"url": "https://x.example", "token": SECRET,
                                                "ca_bundle": str(bundle)})
        with mock.patch.object(http.ssl, "create_default_context") as cdc:
            ctx.client.opener()
        cdc.assert_called_with(cafile=str(bundle))

    def test_missing_ca_bundle_is_plain_and_verification_stays_on(self):
        with self.assertRaises(http.ConnectorError) as cm:
            http.ssl_context(str(self.base / "nope.pem"))
        self.assertIn("does not exist", str(cm.exception))
        self.assertEqual(http.ssl_context(None).verify_mode, ssl.CERT_REQUIRED)

    def test_https_is_required_except_on_loopback(self):
        with self.assertRaises(http.ConnectorError) as cm:
            http.Client("http://jira.example.com", http.bearer(SECRET))
        self.assertIn("https://", str(cm.exception))
        with self.assertRaises(http.ConnectorError):
            http.Client("https://ana:pw@jira.example.com")
        http.Client("http://127.0.0.1:8080")  # tests and local tools

    def test_links_to_another_host_are_refused(self):
        c = http.Client("https://jira.example.com", http.bearer(SECRET))
        self.assertEqual(c.url("https://jira.example.com/a?b=1", {"c": 2}),
                         "https://jira.example.com/a?b=1&c=2")
        with self.assertRaises(http.ConnectorError):
            c.url("https://evil.example.net/steal")

    def test_debug_output_redacts_authorization(self):
        srv = self.server({"/api/me": ME})
        err = io.StringIO()
        http.Client(srv.url, http.basic("ana", SECRET), debug=True, stderr=err).get_json("/api/me")
        self.assertIn("> Authorization: <redacted>", err.getvalue())
        self.assertNotIn(SECRET, err.getvalue())
        self.assertNotIn(base64.b64encode(f"ana:{SECRET}".encode()).decode(), err.getvalue())

    def test_paging_presets(self):
        pages = {"0": {"values": [1, 2], "total": 5}, "2": {"values": [3, 4], "total": 5},
                 "4": {"values": [5], "total": 5}}
        srv = self.server({"/o": lambda r: pages[r.query.get("startAt", ["0"])[0]],
                           "/b": lambda r: {"values": ["a"], "isLastPage": "start" in r.query,
                                            "nextPageStart": 7},
                           "/t": lambda r: {"issues": [r.query.get("nextPageToken", ["-"])[0]],
                                            "nextPageToken": None if "nextPageToken" in r.query
                                            else "abc"},
                           "/l": lambda r: {"results": [r.query.get("cursor", ["-"])[0]],
                                            "_links": {"base": srv.url, "next":
                                                       None if "cursor" in r.query
                                                       else "/l?cursor=z"}}})
        c = http.Client(srv.url, http.bearer(SECRET))
        self.assertEqual(c.paginate("/o", page_size=2, limit=10), ([1, 2, 3, 4, 5], False))
        self.assertEqual(c.paginate("/o", page_size=2, limit=3), ([1, 2, 3], True))
        self.assertEqual(c.paginate("/b", paging=http.BitbucketPaging()), (["a", "a"], False))
        self.assertEqual(c.paginate("/t", items="issues", paging=http.TokenPaging()),
                         (["-", "abc"], False))
        self.assertEqual(c.paginate("/l", items="results", paging=http.LinkPaging()),
                         (["-", "z"], False))

    def test_atlassian_kind(self):
        self.assertEqual(http.atlassian_kind("https://acme.atlassian.net"), "cloud")
        self.assertEqual(http.atlassian_kind("https://jira.acme.example/jira"), "dc")
        self.assertEqual(http.atlassian_kind("https://atlassian.net.evil.example"), "dc")


# --- registry ------------------------------------------------------------------------------

class TestRegistry(Base):
    def test_discovers_the_stub(self):
        self.assertIn(NAME, self.connectors)
        self.assertEqual(self.stub.title, "Stub")
        self.assertEqual(self.stub.keys, ["url", "user", "token", "ca_bundle"])
        self.assertEqual(list(self.stub.commands), ["things"])

    def test_the_glob_skips_foundation_and_private_modules(self):
        found = registry.names()
        for name in ("__init__", "store", "http", "registry", "manage", "text"):
            self.assertNotIn(name, found)
        self.assertFalse([n for n in found if n.startswith("_")])
        registry.discover()  # every shipped connector module loads and validates

    def test_a_folder_with_a_new_module_is_found_without_touching_shared_files(self):
        folder = self.base / "pkg"
        folder.mkdir()
        (folder / "store.py").write_text("")
        (folder / "_helper.py").write_text("")
        (folder / "newthing.py").write_text("")
        self.assertEqual(registry.names(folder), ["newthing"])

    def test_a_broken_module_is_refused_plainly(self):
        bad = type(sys)("bad")
        bad.TITLE = "Bad"
        bad.FIELDS = [registry.Field("token", "Token", secret=True)]
        with self.assertRaises(ValueError) as cm:
            registry.from_module("bad", bad)
        for words in ("first field must be 'url'", "auth(values)", "WHOAMI", "COMMANDS"):
            self.assertIn(words, str(cm.exception))


# --- setup.py connect / connections / disconnect -----------------------------------------

class TestManage(Base):
    def test_connect_asks_saves_and_tests(self):
        srv = self.server({"/api/me": ME})
        code, lines, shown = self.connect(srv.url, "")
        self.assertEqual(code, 0, lines)
        self.assertIn("OK: signed in to 127.0.0.1 as Ana Pop.", shown)
        values = store.read_file(NAME)["values"]
        self.assertEqual(values, {"url": srv.url, "token": SECRET})
        self.assertNotIn(SECRET, shown)
        self.assertTrue(store.read_file(NAME)["last_test"]["ok"])

    def test_connect_again_keeps_values_on_enter(self):
        srv = self.server({"/api/me": ME})
        self.connect(srv.url, "ana")
        code, _, shown = self.connect("", "", secret="")
        self.assertEqual(code, 0)
        self.assertEqual(store.read_file(NAME)["values"],
                         {"url": srv.url, "user": "ana", "token": SECRET})
        self.assertIn("Enter keeps the saved one", shown)

    def test_connect_refuses_without_a_terminal(self):
        code, lines, shown = self.connect("https://x.example", isatty=False)
        self.assertEqual(code, 2)
        self.assertIn("runs only in your own terminal", lines[0])
        self.assertIn("AI_SDLC_STUB_CONNECTOR_URL", lines[1])
        self.assertFalse(store.file_for(NAME).exists())

    def test_connect_without_a_terminal_works_when_env_has_every_value(self):
        srv = self.server({"/api/me": ME})
        os.environ["AI_SDLC_STUB_CONNECTOR_URL"] = srv.url
        os.environ["AI_SDLC_STUB_CONNECTOR_TOKEN"] = SECRET
        code, lines, shown = self.connect(isatty=False)
        self.assertEqual(code, 0, lines)
        self.assertNotIn(SECRET, shown)

    def test_connect_refuses_a_plain_http_url_and_saves_nothing(self):
        code, lines, _ = self.connect("http://jira.example.com", "")
        self.assertEqual(code, 2)
        self.assertIn("https://", lines[0])
        self.assertFalse(store.file_for(NAME).exists())

    def test_connector_check_can_refuse(self):
        code, lines, _ = self.connect("https://forbidden.example", "")
        self.assertEqual((code, lines), (2, ["The stub does not support that host."]))

    def test_unknown_connector(self):
        code, lines = manage.connect("nosuch", connectors=self.connectors)
        self.assertEqual(code, 2)
        self.assertIn("There is no connector 'nosuch'", lines[0])

    def test_test_reports_401_403_and_refused_plainly(self):
        srv = self.server({"/api/me": Reply(401, {"message": f"token {SECRET} expired"})})
        self.save_stub(srv.url)
        code, lines, shown = self.connect(test_only=True)
        self.assertEqual(code, 1)
        self.assertIn("401 Unauthorized", lines[0])
        self.assertNotIn(SECRET, shown)
        self.assertFalse(store.read_file(NAME)["last_test"]["ok"])

        srv.routes["/api/me"] = Reply(403, {})
        self.assertIn("403 Forbidden", self.connect(test_only=True)[1][0])

        self.save_stub(f"http://127.0.0.1:{free_port()}")
        code, lines, _ = self.connect(test_only=True)
        self.assertIn("connection refused", lines[0])

    def test_test_when_not_connected(self):
        code, lines, _ = self.connect(test_only=True)
        self.assertEqual(code, 1)
        self.assertIn("setup.py connect stub_connector", lines[0])

    def test_connections_lists_without_secrets(self):
        srv = self.server({"/api/me": ME})
        self.connect(srv.url, "ana")
        code, lines = manage.connections(self.connectors)
        text = "\n".join(lines)
        self.assertEqual(code, 0)
        self.assertIn(f"- {NAME}: {srv.url} · Data Center · user ana · last test OK", text)
        self.assertIn("from file", text)
        self.assertNotIn(SECRET, text)

    def test_connections_shows_not_connected_and_loose_files(self):
        self.assertIn("not connected", "\n".join(manage.connections(self.connectors)[1]))
        path = self.save_stub("https://x.example")
        os.chmod(path, 0o644)
        self.assertIn("can be read by other users",
                      "\n".join(manage.connections(self.connectors)[1]))

    def test_disconnect_deletes_the_file(self):
        self.save_stub("https://x.example")
        code, lines = manage.disconnect(NAME, self.connectors)
        self.assertEqual((code, lines), (0, ["Removed the saved Stub connection."]))
        self.assertFalse(store.file_for(NAME).exists())
        os.environ["AI_SDLC_STUB_CONNECTOR_TOKEN"] = SECRET
        _, lines = manage.disconnect(NAME, self.connectors)
        self.assertIn("There was no saved Stub connection.", lines)
        self.assertIn("still apply", lines[1])

    def test_setup_py_has_the_three_commands(self):
        root = helpers.make_repo(self.base / "repo")
        code, out = helpers.cli(root, helpers.KIT, "connect", "nosuch")
        self.assertEqual(code, 2)
        self.assertIn("There is no connector 'nosuch'", out)
        code, out = helpers.cli(root, helpers.KIT, "connections")
        self.assertEqual(code, 0)
        self.assertIn(str(self.base / "config/connectors"), out)
        self.assertEqual(helpers.cli(root, helpers.KIT, "disconnect", "nosuch")[0], 0)


class TestRemoveKeepsCredentials(Base):
    def test_remove_leaves_the_credentials_folder(self):
        path = self.save_stub("https://x.example")
        root = helpers.make_repo(self.base / "repo", {"README.md": "team\n"})
        copy = helpers.copy_kit(root / "ai-sdlc-kit")
        kit = root / ".ai-sdlc/kit"
        helpers.cli(root, copy, "setup", "--protect-only")
        helpers.cli(root, kit, "setup", "--name", "Ana", "--roles", "dev", "--lang", "en")
        code, out = helpers.cli(root, kit, "remove")
        self.assertEqual(code, 0, out)
        self.assertTrue(path.is_file())
        self.assertEqual(json.loads(path.read_text())["values"]["token"], SECRET)


# --- connectors.py --------------------------------------------------------------------------

class TestConnectorsCli(Base):
    def run_cli(self, *argv, **kw):
        out, err = io.StringIO(), io.StringIO()
        code = connectors_cli.main(list(argv), connectors=self.connectors, out=out, err=err, **kw)
        return code, out.getvalue(), err.getvalue()

    def test_lists_connectors_and_commands(self):
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn(f"- {NAME} (Stub): whoami, things", out)

    def test_whoami_and_paged_list_as_json(self):
        things = [{"id": i, "name": f"t{i}"} for i in range(1, 6)]
        srv = self.server({"/api/me": ME, "/api/things": lambda r: {
            "values": things[int(r.query.get("startAt", ["0"])[0]):][
                :int(r.query["maxResults"][0])], "total": 5}})
        self.save_stub(srv.url)
        code, out, err = self.run_cli(NAME, "whoami", "--json")
        self.assertEqual(code, 0, err)
        doc = json.loads(out)
        self.assertEqual(doc["item"]["user"], "ana")
        self.assertEqual((doc["connector"], doc["command"], doc["source"]),
                         (NAME, "whoami", srv.url))
        code, out, _ = self.run_cli(NAME, "things", "--limit", "3", "--json")
        doc = json.loads(out)
        self.assertEqual([t["id"] for t in doc["items"]], [1, 2, 3])
        self.assertEqual((doc["count"], doc["truncated"]), (3, True))
        self.assertTrue(all(t["url"].startswith(srv.url + "/things/") for t in doc["items"]))
        code, out, _ = self.run_cli(NAME, "things")
        self.assertIn(f"- t1  {srv.url}/things/1", out)
        self.assertIn("(5 shown)", out)
        self.assertTrue(all(r.method == "GET" for r in srv.requests))

    def test_not_connected_points_at_setup_connect(self):
        code, _, err = self.run_cli(NAME, "whoami")
        self.assertEqual(code, connectors_cli.EXIT_NOT_CONNECTED)
        self.assertIn("setup.py connect stub_connector", err)
        self.assertIn("never through the assistant", err)

    def test_errors_are_plain_and_never_carry_a_secret(self):
        srv = self.server({"/api/me": Reply(401, {"message": f"bad {SECRET}"})})
        self.save_stub(srv.url, user="ana")
        debug = io.StringIO()
        with contextlib.redirect_stderr(debug):
            code, out, err = self.run_cli(NAME, "whoami", "--json", client_kwargs={"debug": True})
        self.assertEqual(code, connectors_cli.EXIT_ERROR)
        self.assertIn("401 Unauthorized", err)
        self.assertIn("setup.py connect stub_connector", err)
        self.assertIn("> Authorization: <redacted>", debug.getvalue())
        self.assertNotIn(SECRET, out + err + debug.getvalue())

    def test_unexpected_errors_are_scrubbed(self):
        self.save_stub("https://x.example")
        boom = registry.Command("boom", run=lambda ctx, a: (_ for _ in ()).throw(
            RuntimeError(f"leak {SECRET}")))
        self.connectors[NAME].commands["boom"] = boom
        code, out, err = self.run_cli(NAME, "boom")
        self.assertEqual(code, connectors_cli.EXIT_ERROR)
        self.assertIn("unexpected error (RuntimeError)", err)
        self.assertNotIn(SECRET, out + err)


class TestTestingHelpers(Base):
    """The ConnectorTestCase helpers the B tasks use."""

    def test_run_command_and_run_cli(self):
        srv = self.server({"/api/me": ME, "/api/things": {"values": [{"id": 1, "name": "a"}],
                                                          "total": 1}})
        ctx = self.context(self.stub, {"url": srv.url, "token": SECRET}, kind="cloud")
        self.assertEqual(ctx.kind, "cloud")
        self.assertEqual(self.run_command(self.stub, ctx, ["whoami"]).item["user"], "ana")
        result = self.run_command(self.stub, ctx, ["things", "--limit", "1"])
        self.assertEqual((len(result.items), result.truncated), (1, False))
        code, out, err = self.run_cli(self.stub, ["things", "--json"],
                                      values={"url": srv.url, "token": SECRET})
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["items"][0]["name"], "a")


class TestText(unittest.TestCase):
    def test_html_to_text(self):
        html = "<h1>Title</h1><p>One &amp; <b>two</b></p><script>x()</script><ul><li>a</li></ul>"
        self.assertEqual(text.html_to_text(html), "Title\nOne & two\na")
        self.assertEqual(text.html_to_text(html, max_chars=5), "Title")
        self.assertEqual(text.html_to_text(None), "")

    def test_adf_to_text(self):
        adf = {"type": "doc", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Hello"}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "world"}]}]}
        self.assertEqual(text.adf_to_text(adf), "Hello\nworld")

    def test_iso_from_ms_and_clip(self):
        self.assertEqual(text.iso_from_ms(1791451800000), "2026-10-08T09:30:00Z")
        self.assertIsNone(text.iso_from_ms(None))
        self.assertEqual(text.clip("abcdef", 4), "abc…")


if __name__ == "__main__":
    unittest.main()
