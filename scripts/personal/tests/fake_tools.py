#!/usr/bin/env python3
"""One fake server for every connector (Data Center flavours), for end-to-end runs.

Canned answers follow each vendor's documented shape; every route first checks the
Authorization header, so a run proves the saved secret was sent the right way. No
network: it listens on 127.0.0.1 only.

  python3 scripts/personal/tests/fake_tools.py     # prints its URL, serves until killed

`env_for(url)` gives the AI_SDLC_<NAME>_* variables a script sets to connect without
a terminal (Artifactory's URL gets the `/artifactory` context path, its routes live
under it); Black Duck's hrefs carry the address the request came to (its Host header); `SECRETS` are the values a run must never print. FAKE_JIRA_TOKEN, when
set, replaces the Jira token (CI makes a random one, so it is in no file beforehand).
Used by test_connectors_e2e.py and by the personal-e2e CI job.
"""
from __future__ import annotations

import base64
import json
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
    "sonarqube": "e2e-sonarqube-USER-S3cr3t-0007",
    "blackduck": "e2e-blackduck-API-S3cr3t-0008",
    "artifactory": None,                     # a JWT-shaped access token, set below
}


def _b64url(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")


# An Artifactory access token is a JWT; its `sub` names the user (design 2026-10-10 §4.3).
TOKENS["artifactory"] = ".".join([_b64url({"typ": "JWT", "alg": "RS256"}),
                                  _b64url({"sub": "jfrt@e2e/users/ana", "scp": "applied"}),
                                  "e2e-artifactory-SIGNATURE-S3cr3t-0009"])
JAMA_ACCESS = "e2e-jama-ACCESS-t0ken-0006"
BLACKDUCK_BEARER = "e2e-blackduck-BEARER-t0ken-0010"
SECRETS = [*TOKENS.values(), JAMA_ACCESS, BLACKDUCK_BEARER]


def env_for(url, name=None) -> dict:
    """AI_SDLC_<NAME>_* for every connector (or just `name`) against the server at `url`."""
    env = {
        "jira": {"URL": url, "TOKEN": TOKENS["jira"]},
        "confluence": {"URL": url, "TOKEN": TOKENS["confluence"]},
        "bitbucket": {"URL": url, "TOKEN": TOKENS["bitbucket"]},
        "jama": {"URL": url, "CLIENT_ID": "e2e-client", "CLIENT_SECRET": TOKENS["jama"]},
        "jenkins": {"URL": url, "USERNAME": "ana", "TOKEN": TOKENS["jenkins"]},
        "sonarqube": {"URL": url, "TOKEN": TOKENS["sonarqube"]},
        "blackduck": {"URL": url, "TOKEN": TOKENS["blackduck"]},
        "artifactory": {"URL": f"{url}/artifactory", "TOKEN": TOKENS["artifactory"],
                        "MAVEN_REPO": "maven-virtual", "NPM_REPO": "npm-virtual",
                        "GO_REPO": "go-virtual"},
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


def _guarded_by(expected, build):
    """Like `_guarded`, but the answer is built from the request (for hrefs with its host)."""
    def route(req):
        if req.headers.get("Authorization") != expected:
            return DENIED
        return build(f"http://{req.headers.get('Host')}", req)
    return route


def _text(body):
    return Reply(200, body, {"Content-Type": "text/plain"})


def _xml(body):
    return Reply(200, body, {"Content-Type": "application/xml"})


def _blackduck_routes() -> dict:
    """Black Duck: the token exchange (POST, `token <api>`), then Bearer on every GET.
    Project 'App', version '1.0', one vulnerable component with upgrade guidance."""
    bearer = f"Bearer {BLACKDUCK_BEARER}"
    p, v = "/api/projects/p1", "/api/projects/p1/versions/r1"
    cv = "/api/components/c1/versions/cv1"

    def meta(base, href, **links):
        return {"href": base + href, "links": [{"rel": k.replace("_", "-"), "href": base + h}
                                               for k, h in links.items()]}

    def exchange(req):
        if req.method != "POST" or req.headers.get("Authorization") != f"token {TOKENS['blackduck']}":
            return DENIED
        return {"bearerToken": BLACKDUCK_BEARER, "expiresInMilliseconds": 7199000}

    def projects(base, req):
        return {"totalCount": 1, "items": [{"name": "App", "description": None,
                                            "updatedAt": "2026-10-01T10:00:00.000Z",
                                            "_meta": meta(base, p, versions=p + "/versions")}]}

    def versions(base, req):
        return {"totalCount": 1, "items": [{
            "versionName": "1.0", "phase": "DEVELOPMENT", "distribution": "INTERNAL",
            "settingUpdatedAt": "2026-10-02T08:00:00.000Z",
            "_meta": meta(base, v, vulnerable_components=v + "/vulnerable-bom-components",
                          components=v + "/components", policy_status=v + "/policy-status")}]}

    def vulns(base, req):
        return {"totalCount": 1, "items": [{
            "componentName": "commons-text", "componentVersionName": "1.9",
            "componentVersion": base + cv,
            "componentVersionOriginId": "org.apache.commons:commons-text:1.9",
            "vulnerabilityWithRemediation": {
                "vulnerabilityName": "CVE-2022-42889", "source": "NVD", "severity": "CRITICAL",
                "overallScore": 9.8, "remediationStatus": "NEW"},
            "_meta": meta(base, v + "/vulnerable-bom-components/x")}]}

    def components(base, req):
        return {"totalCount": 1, "items": [{
            "componentName": "commons-text", "componentVersionName": "1.9",
            "componentVersion": base + cv,
            "origins": [{"externalId": "org.apache.commons:commons-text:1.9"}],
            "licenses": [{"licenseDisplay": "Apache License 2.0"}],
            "policyStatus": "IN_VIOLATION", "reviewStatus": "NOT_REVIEWED"}]}

    return {
        "/api/tokens/authenticate": exchange,
        "/api/current-user": _guarded(bearer, {"userName": "ana", "firstName": "Ana",
                                               "lastName": "Pop", "email": "ana@example.com"}),
        "/api/projects": _guarded_by(bearer, projects),
        p + "/versions": _guarded_by(bearer, versions),
        v + "/vulnerable-bom-components": _guarded_by(bearer, vulns),
        v + "/components": _guarded_by(bearer, components),
        v + "/policy-status": _guarded(bearer, {
            "overallStatus": "IN_VIOLATION",
            "componentVersionStatusCounts": [{"name": "IN_VIOLATION", "value": 1},
                                             {"name": "NOT_IN_VIOLATION", "value": 41}]}),
        cv + "/upgrade-guidance": _guarded(bearer, {"shortTerm": {"versionName": "1.10.0"},
                                                    "longTerm": {"versionName": "1.12.0"}}),
    }


def routes() -> dict:
    jira = f"Bearer {TOKENS['jira']}"
    wiki = f"Bearer {TOKENS['confluence']}"
    bb = f"Bearer {TOKENS['bitbucket']}"
    jama = f"Bearer {JAMA_ACCESS}"
    jenkins = _basic("ana", TOKENS["jenkins"])
    sonar = _basic(TOKENS["sonarqube"], "")          # the token as the Basic user name
    art = f"Bearer {TOKENS['artifactory']}"
    a = "/artifactory"
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
        # SonarQube 10.6: the impacts issue model
        "/api/server/version": _guarded(sonar, _text("10.6.0.92116")),
        "/api/users/current": _guarded(sonar, {"isLoggedIn": True, "login": "ana",
                                               "name": "Ana Pop", "email": "ana@example.com"}),
        "/api/qualitygates/project_status": _guarded(sonar, {"projectStatus": {
            "status": "ERROR", "conditions": [
                {"status": "ERROR", "metricKey": "new_coverage", "comparator": "LT",
                 "errorThreshold": "80", "actualValue": "61.5"},
                {"status": "OK", "metricKey": "new_reliability_rating", "comparator": "GT",
                 "errorThreshold": "1", "actualValue": "1"}]}}),
        "/api/issues/search": _guarded(sonar, {
            "paging": {"pageIndex": 1, "pageSize": 100, "total": 1}, "issues": [
                {"key": "AX1", "rule": "java:S2095", "component": "demo:src/main/java/App.java",
                 "project": "demo", "line": 42, "message": "Use try-with-resources",
                 "impacts": [{"softwareQuality": "RELIABILITY", "severity": "HIGH"}],
                 "cleanCodeAttribute": "COMPLETE", "issueStatus": "OPEN", "effort": "5min",
                 "tags": [], "creationDate": "2026-10-01T10:00:00+0000",
                 "updateDate": "2026-10-02T10:00:00+0000"}]}),
        # Black Duck
        **_blackduck_routes(),
        # Artifactory 7.x, under the /artifactory context path
        a + "/api/system/version": _guarded(art, {"version": "7.90.10", "revision": "79010"}),
        a + "/maven-virtual/org/example/lib/maven-metadata.xml": _guarded(art, _xml(
            "<metadata><groupId>org.example</groupId><artifactId>lib</artifactId>"
            "<versioning><latest>1.2.0</latest><release>1.2.0</release><versions>"
            "<version>1.0.0</version><version>1.1.0</version><version>1.2.0</version>"
            "</versions><lastUpdated>20261001100000</lastUpdated></versioning></metadata>")),
        a + "/api/npm/npm-virtual/@scope%2fpkg": _guarded(art, {
            "name": "@scope/pkg", "dist-tags": {"latest": "2.1.0"},
            "versions": {"2.0.0": {}, "2.1.0": {}},
            "time": {"2.0.0": "2026-09-01T10:00:00.000Z", "2.1.0": "2026-10-01T10:00:00.000Z"}}),
        a + "/api/go/go-virtual/github.com/!example/mod/@v/list": _guarded(art, _text(
            "v1.3.1\nv1.4.0\n")),
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
