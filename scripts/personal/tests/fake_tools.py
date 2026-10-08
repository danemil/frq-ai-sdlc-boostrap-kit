#!/usr/bin/env python3
"""One fake server for all five connectors (Data Center flavours), for end-to-end runs.

Canned answers follow each vendor's documented shape; every route first checks the
Authorization header, so a run proves the saved secret was sent the right way. No
network: it listens on 127.0.0.1 only.

  python3 scripts/personal/tests/fake_tools.py     # prints its URL, serves until killed

`env_for(url)` gives the AI_SDLC_<NAME>_* variables a script sets to connect without
a terminal; `SECRETS` are the values a run must never print. FAKE_JIRA_TOKEN, when
set, replaces the Jira token (CI makes a random one, so it is in no file beforehand).
Used by test_connectors_e2e.py and by the personal-e2e CI job.
"""
from __future__ import annotations

import base64
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakeserver import FakeServer, Reply  # noqa: E402

TOKENS = {
    "jira": os.environ.get("FAKE_JIRA_TOKEN") or "e2e-jira-PAT-S3cr3t-0001",
    "confluence": "e2e-confluence-PAT-S3cr3t-0002",
    "bitbucket": "e2e-bitbucket-HTTP-S3cr3t-0003",
    "jama": "e2e-jama-CLIENT-S3cr3t-0004",
    "jenkins": "e2e-jenkins-API-S3cr3t-0005",
}
JAMA_ACCESS = "e2e-jama-ACCESS-t0ken-0006"
SECRETS = [*TOKENS.values(), JAMA_ACCESS]


def env_for(url, name=None) -> dict:
    """AI_SDLC_<NAME>_* for every connector (or just `name`) against the server at `url`."""
    env = {
        "jira": {"URL": url, "TOKEN": TOKENS["jira"]},
        "confluence": {"URL": url, "TOKEN": TOKENS["confluence"]},
        "bitbucket": {"URL": url, "TOKEN": TOKENS["bitbucket"]},
        "jama": {"URL": url, "CLIENT_ID": "e2e-client", "CLIENT_SECRET": TOKENS["jama"]},
        "jenkins": {"URL": url, "USERNAME": "ana", "TOKEN": TOKENS["jenkins"]},
    }
    return {f"AI_SDLC_{n.upper()}_{k}": v for n, kv in env.items() if name in (None, n)
            for k, v in kv.items()}


def _basic(user, secret) -> str:
    return "Basic " + base64.b64encode(f"{user}:{secret}".encode()).decode()


DENIED = Reply(401, {"errorMessages": ["not authenticated"]})


def _guarded(expected, answer):
    """A route answering `answer` only when the request carries the `expected` header."""
    def route(req):
        return answer if req.headers.get("Authorization") == expected else DENIED
    return route


def routes() -> dict:
    jira = f"Bearer {TOKENS['jira']}"
    wiki = f"Bearer {TOKENS['confluence']}"
    bb = f"Bearer {TOKENS['bitbucket']}"
    jama = f"Bearer {JAMA_ACCESS}"
    jenkins = _basic("ana", TOKENS["jenkins"])
    ms = 1790848800000                       # 2026-10-01T10:00:00Z in epoch ms
    return {
        # Jira Data Center, REST v2
        "/rest/api/2/myself": _guarded(jira, {"name": "ana", "displayName": "Ana Pop",
                                              "emailAddress": "ana@example.com"}),
        "/rest/api/2/search": _guarded(jira, {"startAt": 0, "maxResults": 100, "total": 2,
                                              "issues": [
            {"key": "ABC-1", "fields": {"summary": "Login fails on Safari",
                                        "issuetype": {"name": "Bug"}, "status": {"name": "Open"},
                                        "assignee": {"displayName": "Ana Pop"},
                                        "priority": {"name": "High"},
                                        "updated": "2026-10-01T10:00:00.000+0000"}},
            {"key": "ABC-2", "fields": {"summary": "Export as CSV",
                                        "issuetype": {"name": "Story"},
                                        "status": {"name": "In Progress"}, "assignee": None,
                                        "priority": {"name": "Medium"},
                                        "updated": "2026-10-02T09:30:00.000+0000"}}]}),
        # Confluence Data Center
        "/rest/api/user/current": _guarded(wiki, {"type": "known", "username": "ana",
                                                  "displayName": "Ana Pop"}),
        "/rest/api/content/search": _guarded(wiki, {"results": [
            {"id": "123", "type": "page", "title": "Release runbook", "space": {"key": "OPS"},
             "version": {"when": "2026-10-01T10:00:00.000Z"},
             "_links": {"webui": "/pages/viewpage.action?pageId=123"}}],
            "size": 1, "_links": {}}),
        # Bitbucket Data Center
        "/rest/api/1.0/projects": _guarded(bb, Reply(200, {"values": [], "isLastPage": True},
                                                     {"X-AUSERNAME": "ana"})),
        "/rest/api/1.0/users/ana": _guarded(bb, {"name": "ana", "displayName": "Ana Pop",
                                                 "emailAddress": "ana@example.com"}),
        "/rest/api/1.0/projects/ABC/repos/app/pull-requests": _guarded(bb, {
            "isLastPage": True, "values": [
                {"id": 7, "title": "Fix Safari login", "state": "OPEN",
                 "author": {"user": {"displayName": "Ana Pop"}},
                 "reviewers": [{"user": {"displayName": "Dan Ion"}, "status": "UNAPPROVED"}],
                 "fromRef": {"displayId": "fix/safari"}, "toRef": {"displayId": "main"},
                 "createdDate": ms, "updatedDate": ms,
                 "links": {"self": [{"href": "https://bitbucket.example.com/projects/ABC/"
                                             "repos/app/pull-requests/7"}]}}]}),
        # Jama Connect: the token request, then Bearer
        "/rest/oauth/token": _guarded(_basic("e2e-client", TOKENS["jama"]),
                                      {"access_token": JAMA_ACCESS, "token_type": "bearer",
                                       "expires_in": 3600}),
        "/rest/v1/users/current": _guarded(jama, {"data": {
            "id": 42, "username": "ana", "firstName": "Ana", "lastName": "Pop",
            "email": "ana@example.com"}}),
        "/rest/v1/items/1001": _guarded(jama, {"data": {
            "id": 1001, "documentKey": "REQ-1", "globalId": "GID-1", "itemType": 33,
            "project": 5, "createdDate": "2026-09-01T10:00:00.000+0000",
            "modifiedDate": "2026-10-01T10:00:00.000+0000",
            "fields": {"name": "The system shall export CSV",
                       "description": "<p>Users export <b>reports</b>.</p>", "priority": 3}}}),
        # Jenkins
        "/me/api/json": _guarded(jenkins, {"id": "ana", "fullName": "Ana Pop"}),
        "/job/app/job/main/api/json": _guarded(jenkins, {
            "name": "main", "fullName": "app/main", "color": "blue", "description": None,
            "lastBuild": {"number": 12, "url": "https://jenkins.example.com/job/app/job/main/12/",
                          "result": "SUCCESS", "timestamp": ms},
            "lastSuccessfulBuild": {"number": 12, "url": "https://jenkins.example.com/job/app/"
                                                         "job/main/12/"},
            "lastFailedBuild": None, "healthReport": [{"score": 100,
                                                       "description": "Build stability"}],
            "jobs": []}),
    }


def main() -> int:
    srv = FakeServer(routes()).start()
    print(srv.url, flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        srv.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
