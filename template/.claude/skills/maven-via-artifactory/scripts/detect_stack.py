#!/usr/bin/env python3
"""Find the stack a repo uses and the company mirrors it resolves through.

    python3 detect_stack.py                  # a short summary of the current folder
    python3 detect_stack.py --json           # the full result as JSON
    python3 detect_stack.py --root DIR       # another folder
    python3 detect_stack.py --home           # also read ~/.m2/settings.xml, ~/.npmrc and GOPROXY

What it reports: the Java build (Maven or Gradle), the Java release, Spring Boot, JUnit,
AssertJ, Mockito, TestFX and where JavaFX comes from (org.openjfx or a JDK that bundles
it); Go and its toolchain; the React, Jest, Testing Library and TypeScript versions
(declared, and locked when package-lock.json is there); signs of SonarQube and Black
Duck; the Maven mirrors, npm registries and GOPROXY.

Python 3.9+, standard library only. It only reads files: it never writes, never runs a
tool (no mvn, go or npm), never uses the network. It walks the root and three folder
levels below it, in sorted order, at most 5,000 entries, files up to 512 KB; it skips
build output, node_modules and dot-folders other than .github and .mvn, and refuses XML
with a DOCTYPE or ENTITY declaration. Secrets are never read into the result: from
settings.xml only mirror id, mirrorOf and url; from .npmrc only registry lines; user and
password are cut out of every URL.

Exit code: 0, or 2 when the root cannot be read. Written for this kit; MIT.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True                         # no __pycache__ in the placed skill

import argparse
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

SCHEMA = 1
MAX_ENTRIES = 5000
MAX_DEPTH = 3
MAX_BYTES = 512 * 1024
MAX_EVIDENCE = 20
SKIP_DIRS = {".git", ".ai-sdlc", ".agents", "node_modules", "target", "build", "dist", "out", "vendor"}
KEEP_DOT_DIRS = {".github", ".mvn"}
JDK_FILES = {".sdkmanrc", ".java-version", ".tool-versions"}
ZULU_FX = re.compile(r"(?i)fx-zulu|zulu[\w.-]*fx")
USERINFO = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/@\s]*@")
SONAR_WORDS = ("withSonarQubeEnv", "sonar-scanner", "sonar:sonar")
BLACKDUCK_WORDS = ("blackduck", "synopsys_detect", "detect.sh")
BLACKDUCK_PROP = re.compile(r"(?<![\w.])-{0,2}(detect|blackduck)\.[a-z][\w.-]*\s*[=:]", re.I)
NODE_NAMES = {"react": "react", "jest": "jest", "testing_library_react": "@testing-library/react",
              "typescript": "typescript"}
SIGNALS = ("maven", "java", "javafx", "go", "node", "jest", "react", "web", "sonar", "blackduck")


def strip_userinfo(text: Optional[str]) -> Optional[str]:
    """`https://user:pw@host/` -> `https://host/` (every URL in the string)."""
    return USERINFO.sub(r"\1", text) if text else text


class Scan:
    def __init__(self, root: Path):
        self.root = root
        self.files: List[tuple] = []          # (rel, path), in walk order
        self.skipped: List[dict] = []
        self.evidence: Dict[str, List[str]] = {s: [] for s in SIGNALS}

    # --- reading ---------------------------------------------------------------------
    def walk(self) -> None:
        count = 0

        def visit(folder: Path, prefix: str, depth: int) -> bool:
            nonlocal count
            try:
                names = sorted(os.listdir(folder))
            except OSError:
                self.skip(prefix or ".", "folder could not be read")
                return True
            for name in names:
                if count >= MAX_ENTRIES:
                    self.skip(prefix or ".", f"entry limit {MAX_ENTRIES} reached; the rest was not read")
                    return False
                count += 1
                p = folder / name
                rel = f"{prefix}{name}"
                if p.is_symlink():
                    continue                      # never follow a link out of the repo
                if p.is_dir():
                    if name in SKIP_DIRS or (name.startswith(".") and name not in KEEP_DOT_DIRS):
                        continue
                    if depth < MAX_DEPTH and not visit(p, rel + "/", depth + 1):
                        return False
                elif p.is_file():
                    self.files.append((rel, p))
            return True

        visit(self.root, "", 0)
        # Shallow files first, then by path: the root POM before a module's.
        self.files.sort(key=lambda f: (f[0].count("/"), f[0]))

    def skip(self, rel: str, reason: str) -> None:
        item = {"path": rel, "reason": reason}
        if item not in self.skipped:
            self.skipped.append(item)

    def read(self, rel: str, p: Path) -> Optional[str]:
        try:
            if p.stat().st_size > MAX_BYTES:
                self.skip(rel, f"over {MAX_BYTES // 1024} KB")
                return None
            return p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            self.skip(rel, "could not be read")
            return None

    def xml(self, rel: str, p: Path):
        text = self.read(rel, p)
        if text is None:
            return None
        if "<!DOCTYPE" in text or "<!ENTITY" in text:
            self.skip(rel, "DOCTYPE or ENTITY declaration refused")
            return None
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            self.skip(rel, "not well-formed XML")
            return None
        for el in root.iter():
            if isinstance(el.tag, str) and "}" in el.tag:
                el.tag = el.tag.split("}", 1)[1]
        return root

    def note(self, signal: str, rel: str) -> None:
        if rel not in self.evidence[signal] and len(self.evidence[signal]) < MAX_EVIDENCE:
            self.evidence[signal].append(rel)


def text_of(el, path: str) -> Optional[str]:
    found = el.find(path) if el is not None else None
    return found.text.strip() if found is not None and found.text and found.text.strip() else None


def resolve(value: Optional[str], props: Dict[str, str]) -> Optional[str]:
    """`${name}` from the POM properties, one level; an unresolved value gives None."""
    if not value:
        return None
    value = re.sub(r"\$\{([^}]+)\}", lambda m: props.get(m.group(1), m.group(0)), value)
    return None if "${" in value else value


def major(version: Optional[str]) -> Optional[str]:
    m = re.match(r"\s*(\d+)", version or "")
    return m.group(1) if m else None


# --- Java ------------------------------------------------------------------------------

def java_part(s: Scan) -> dict:
    poms = []                                    # (rel, element)
    for rel, p in s.files:
        if p.name == "pom.xml":
            el = s.xml(rel, p)
            if el is not None:
                poms.append((rel, el))
    gradle = [rel for rel, p in s.files if p.name in ("build.gradle", "build.gradle.kts")]
    java_files = [(rel, p) for rel, p in s.files if p.suffix == ".java"]

    # Properties: a module's own first, then those of the POMs above it (root first).
    shared: Dict[str, str] = {}
    for _, el in poms:
        for prop in (el.find("properties") if el.find("properties") is not None else []):
            if isinstance(prop.tag, str) and prop.text:
                shared.setdefault(prop.tag, prop.text.strip())

    def props_of(el) -> Dict[str, str]:
        own = dict(shared)
        node = el.find("properties")
        for prop in (node if node is not None else []):
            if isinstance(prop.tag, str) and prop.text:
                own[prop.tag] = prop.text.strip()
        return own

    out = {"build": "maven" if poms else ("gradle" if gradle else None),
           "poms": [rel for rel, _ in poms], "release": None, "release_from": None,
           "spring_boot": None, "junit": None, "junit_version": None,
           "assertj": False, "mockito": False, "testfx": False}
    fx = {"used": False, "source": None, "version": None, "evidence": []}
    openjfx = False
    junit4, jupiter, bom_version = None, [], None

    for rel, el in poms:
        s.note("maven", rel)
        s.note("java", rel)
        props = props_of(el)
        own = el.find("properties")
        own_props = {c.tag: (c.text or "").strip() for c in (own if own is not None else [])
                     if isinstance(c.tag, str)}
        if out["release"] is None:
            for key in ("maven.compiler.release", "maven.compiler.target", "maven.compiler.source",
                        "java.version"):
                value = resolve(own_props.get(key), props)
                if value:
                    out["release"], out["release_from"] = value, f"{rel}: {key}"
                    break
        if out["release"] is None:
            for plugin in el.iter("plugin"):
                if text_of(plugin, "artifactId") == "maven-compiler-plugin":
                    value = resolve(text_of(plugin, "configuration/release"), props)
                    if value:
                        out["release"], out["release_from"] = value, f"{rel}: maven-compiler-plugin release"
                        break
        parent = el.find("parent")
        if out["spring_boot"] is None and text_of(parent, "artifactId") == "spring-boot-starter-parent":
            out["spring_boot"] = resolve(text_of(parent, "version"), props)
        if any(k.startswith("sonar.") for k in own_props):
            s.quality["sonar"].append(f"{rel}: sonar. property")
        for d in list(el.iter("dependency")) + list(el.iter("plugin")):
            group, artifact = text_of(d, "groupId") or "", text_of(d, "artifactId") or ""
            version = resolve(text_of(d, "version"), props)
            if artifact == "spring-boot-dependencies" and out["spring_boot"] is None:
                out["spring_boot"] = version
            elif group == "junit" and artifact == "junit":
                junit4 = junit4 or version or ""
            elif artifact == "junit-bom":
                bom_version = bom_version or version
            elif artifact.startswith("junit-jupiter"):
                jupiter.append(version)
            elif group == "org.assertj":
                out["assertj"] = True
            elif group == "org.mockito":
                out["mockito"] = True
            elif group == "org.testfx":
                out["testfx"] = True
            elif artifact == "sonar-maven-plugin":
                s.quality["sonar"].append(f"{rel}: sonar-maven-plugin")
            if artifact == "javafx-maven-plugin":
                fx["evidence"].append(f"{rel}: javafx-maven-plugin")
            elif group == "org.openjfx":
                openjfx = True
                fx["evidence"].append(f"{rel}: org.openjfx:{artifact}")
                fx["version"] = fx["version"] or version

    # JUnit: Jupiter (5 or 6, same API) wins over JUnit 4 when a repo has both.
    jupiter_version = next((v for v in jupiter if v), None) or bom_version
    if jupiter or bom_version:
        out["junit_version"] = jupiter_version
        out["junit"] = major(jupiter_version) if major(jupiter_version) in ("5", "6") else None
    elif junit4 is not None:
        out["junit"], out["junit_version"] = "4", junit4 or None

    for rel in gradle:
        s.note("java", rel)
        text = s.read(rel, s.root / rel) or ""
        out["assertj"] = out["assertj"] or "org.assertj" in text
        out["mockito"] = out["mockito"] or "org.mockito" in text
        out["testfx"] = out["testfx"] or "org.testfx" in text
        if "org.openjfx" in text:
            openjfx = True
            fx["evidence"].append(f"{rel}: org.openjfx")

    jdk_fx = False
    for rel, p in s.files:
        if p.name in JDK_FILES:
            for line in (s.read(rel, p) or "").splitlines():
                if ZULU_FX.search(line):
                    jdk_fx = True
                    fx["evidence"].append(f"{rel}: {line.strip()}")
                    m = re.search(r"\d[\w.+-]*", line.split("=", 1)[-1])
                    fx_jdk_version = m.group(0) if m else None
                    if not openjfx:
                        fx["version"] = fx["version"] or fx_jdk_version
        elif p.suffix == ".fxml":
            fx["evidence"].append(rel)
    for rel, p in java_files:
        s.note("java", rel)
        text = s.read(rel, p) or ""
        if p.name == "module-info.java" and re.search(r"\brequires\s+(transitive\s+)?javafx\.", text):
            fx["evidence"].append(f"{rel}: requires javafx.")
        elif re.search(r"(?m)^\s*import\s+(static\s+)?javafx\.", text):
            fx["evidence"].append(f"{rel}: import javafx.")
    fx["evidence"] = fx["evidence"][:MAX_EVIDENCE]
    if fx["evidence"]:
        fx["used"] = True
        fx["source"] = "openjfx" if openjfx else ("jdk" if jdk_fx else "unknown")
        for e in fx["evidence"]:
            s.note("javafx", e.split(": ", 1)[0])
    out["javafx"] = fx
    return out


# --- Go and Node -------------------------------------------------------------------------

def go_part(s: Scan) -> dict:
    out = {"modules": [], "go": None, "toolchain": None}
    for rel, p in s.files:
        if p.name != "go.mod":
            continue
        out["modules"].append(rel)
        s.note("go", rel)
        text = s.read(rel, p) or ""
        g = re.search(r"(?m)^go\s+(\S+)", text)
        t = re.search(r"(?m)^toolchain\s+(\S+)", text)
        if out["go"] is None and g:
            out["go"] = g.group(1)
        if out["toolchain"] is None and t:
            out["toolchain"] = t.group(1)
    return out


def node_part(s: Scan) -> dict:
    out = {"packages": [], "react": None, "jest": None, "testing_library_react": None,
           "typescript": None, "locked": {}}
    lock_done = False
    for rel, p in s.files:
        if p.name == "package.json":
            out["packages"].append(rel)
            s.note("node", rel)
            try:
                data = json.loads(s.read(rel, p) or "{}")
            except ValueError:
                s.skip(rel, "not valid JSON")
                continue
            if not isinstance(data, dict):
                continue
            deps = {}
            for key in ("peerDependencies", "devDependencies", "dependencies"):
                if isinstance(data.get(key), dict):
                    deps.update(data[key])
            for field, name in NODE_NAMES.items():
                if out[field] is None and isinstance(deps.get(name), str):
                    out[field] = deps[name]
            if "react" in deps:
                s.note("react", rel)
                s.note("web", rel)
            if "jest" in data or any(n in deps for n in ("jest", "ts-jest", "@jest/core")):
                s.note("jest", rel)
            if not lock_done:
                lock = p.parent / "package-lock.json"
                lock_rel = rel[: -len("package.json")] + "package-lock.json"
                if lock.is_file() and not lock.is_symlink():
                    lock_done = True
                    out["locked"] = locked_versions(s, lock_rel, lock)
        elif p.name.startswith("jest.config."):
            s.note("jest", rel)
        elif p.name == "index.html" and re.match(r"(.*/)?(src|public)/index\.html$", rel):
            s.note("web", rel)
    return out


def locked_versions(s: Scan, rel: str, p: Path) -> dict:
    try:
        data = json.loads(s.read(rel, p) or "{}")
    except ValueError:
        s.skip(rel, "not valid JSON")
        return {}
    found = {}
    packages = data.get("packages") if isinstance(data, dict) else None
    legacy = data.get("dependencies") if isinstance(data, dict) else None
    for name in sorted(NODE_NAMES.values()):
        entry = None
        if isinstance(packages, dict):
            entry = packages.get(f"node_modules/{name}")
        if entry is None and isinstance(legacy, dict):
            entry = legacy.get(name)
        if isinstance(entry, dict) and isinstance(entry.get("version"), str):
            found[name] = entry["version"]
    return found


# --- quality tools ---------------------------------------------------------------------

def quality_part(s: Scan) -> None:
    for rel, p in s.files:
        ci = p.name == "Jenkinsfile" or (rel.startswith(".github/workflows/")
                                         and p.suffix in (".yml", ".yaml"))
        app = re.match(r"application[\w.-]*\.(ya?ml|properties)$", p.name) is not None
        if p.name == "sonar-project.properties":
            s.quality["sonar"].append(rel)
        if not (ci or app):
            continue
        text = s.read(rel, p) or ""
        if ci:
            for word in SONAR_WORDS:
                if word in text:
                    s.quality["sonar"].append(f"{rel}: {word}")
        lower = text.lower()
        for word in BLACKDUCK_WORDS:
            if word in lower:
                s.quality["blackduck"].append(f"{rel}: {word}")
        m = BLACKDUCK_PROP.search(text)
        if m:
            s.quality["blackduck"].append(f"{rel}: {m.group(1).lower()}. property")
    for key in ("sonar", "blackduck"):
        items = []
        for e in s.quality[key]:
            if e not in items:
                items.append(e)
        s.quality[key] = items[:MAX_EVIDENCE]
        for e in s.quality[key]:
            s.note(key, e.split(": ", 1)[0])


# --- mirrors -----------------------------------------------------------------------------

def maven_mirrors(s: Scan, label: str, p: Path) -> List[dict]:
    el = s.xml(label, p)
    if el is None:
        return []
    found = []
    for mirror in el.iter("mirror"):                 # only these three fields are read
        found.append({"file": label, "id": text_of(mirror, "id"),
                      "mirrorOf": text_of(mirror, "mirrorOf"),
                      "url": strip_userinfo(text_of(mirror, "url"))})
    return found


def npm_registries(s: Scan, label: str, p: Path) -> List[dict]:
    found = []
    for line in (s.read(label, p) or "").splitlines():
        m = re.match(r"\s*(@[\w.-]+:)?registry\s*=\s*(\S+)", line)
        if m:                                        # auth lines never match this
            found.append({"file": label, "registry": strip_userinfo(m.group(2)),
                          "scope": m.group(1)[:-1] if m.group(1) else None})
    return found


def mirrors_part(s: Scan, home: Optional[Path], env) -> dict:
    out = {"maven": [], "npm": [], "go": {"GOPROXY": None}}
    for rel, p in s.files:
        if rel == ".mvn/settings.xml":
            out["maven"] += maven_mirrors(s, rel, p)
        elif p.name == ".npmrc":
            out["npm"] += npm_registries(s, rel, p)
    if home is not None:
        m2 = Path(home) / ".m2/settings.xml"
        if m2.is_file():
            out["maven"] += maven_mirrors(s, "~/.m2/settings.xml", m2)
        npmrc = Path(home) / ".npmrc"
        if npmrc.is_file():
            out["npm"] += npm_registries(s, "~/.npmrc", npmrc)
        env = os.environ if env is None else env
        out["go"]["GOPROXY"] = strip_userinfo(env.get("GOPROXY")) or None
    return out


# --- entry points ------------------------------------------------------------------------

def scan(root: Path, home: Optional[Path] = None, env=None) -> dict:
    """The stack and mirrors of `root`. The person's files (`home`) and environment
    (`env`, default os.environ) are read only when `home` is given."""
    s = Scan(Path(root))
    s.quality = {"sonar": [], "blackduck": []}
    s.walk()
    java = java_part(s)
    go = go_part(s)
    node = node_part(s)
    quality_part(s)
    mirrors = mirrors_part(s, home, env)
    return {"schema": SCHEMA, "java": java, "go": go, "node": node, "quality": s.quality,
            "mirrors": mirrors, "files": {k: v for k, v in s.evidence.items()},
            "skipped": s.skipped}


def summary(r: dict) -> str:
    j, fx, g, n = r["java"], r["java"]["javafx"], r["go"], r["node"]
    none = "none found"
    lines = ["Stack (read from the repo's files; nothing was run or downloaded):"]
    if j["build"]:
        lines.append(f"- Java: {j['build']}, release {j['release'] or 'not found'}"
                     + (f" ({j['release_from']})" if j["release_from"] else ""))
        lines.append(f"  Spring Boot {j['spring_boot'] or none}; JUnit "
                     + (f"{j['junit']} ({j['junit_version'] or 'version not found'})" if j["junit"] else none)
                     + f"; AssertJ {'yes' if j['assertj'] else 'no'}; Mockito {'yes' if j['mockito'] else 'no'}"
                     + f"; TestFX {'yes' if j['testfx'] else 'no'}")
    if fx["used"]:
        lines.append(f"- JavaFX: from {fx['source']}, version {fx['version'] or 'not found'}")
    if g["modules"]:
        lines.append(f"- Go: {g['go'] or 'not found'}" + (f", toolchain {g['toolchain']}" if g["toolchain"] else ""))
    if n["packages"]:
        lines.append(f"- Node: react {n['react'] or none}, jest {n['jest'] or none}, "
                     f"@testing-library/react {n['testing_library_react'] or none}, "
                     f"typescript {n['typescript'] or none}")
        if n["locked"]:
            lines.append("  locked: " + ", ".join(f"{k} {v}" for k, v in sorted(n["locked"].items())))
    if len(lines) == 1:
        lines.append("- no Java, Go or Node project found")
    q = r["quality"]
    lines.append(f"- SonarQube: {', '.join(q['sonar']) or none}")
    lines.append(f"- Black Duck: {', '.join(q['blackduck']) or none}")
    m = r["mirrors"]
    lines.append("Mirrors:")
    for x in m["maven"]:
        lines.append(f"- Maven ({x['file']}): {x['id']} mirrorOf {x['mirrorOf']} -> {x['url']}")
    for x in m["npm"]:
        lines.append(f"- npm ({x['file']}): " + (f"{x['scope']} " if x["scope"] else "") + x["registry"])
    lines.append(f"- GOPROXY: {m['go']['GOPROXY'] or 'not set or not read (use --home)'}")
    if not m["maven"] and not m["npm"]:
        lines.append("- no Maven mirror or npm registry found in the repo"
                     + ("" if any(x["file"].startswith("~") for x in m["maven"] + m["npm"]) else
                        "; try --home"))
    for x in r["skipped"]:
        lines.append(f"Skipped {x['path']}: {x['reason']}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Find the repo's stack and company mirrors (read-only).")
    ap.add_argument("--root", default=".", help="the repo folder (default: the current folder)")
    ap.add_argument("--home", action="store_true",
                    help="also read ~/.m2/settings.xml, ~/.npmrc and GOPROXY (never a password or token)")
    ap.add_argument("--json", action="store_true", help="print the full result as JSON")
    args = ap.parse_args(argv)
    root = Path(args.root)
    if not root.is_dir() or not os.access(root, os.R_OK | os.X_OK):
        print(f"detect_stack: cannot read the folder {args.root}", file=sys.stderr)
        return 2
    result = scan(root, home=Path.home() if args.home else None)
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else summary(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
