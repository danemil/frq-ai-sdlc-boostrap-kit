#!/usr/bin/env python3
"""Adopt the AI-SDLC kit into a repo — greenfield or brownfield, re-runnable.

Greenfield is brownfield with zero conflicts, so there is one code path. The
installer never clobbers: kit-owned files are updated only while they are
untouched, files you are meant to own are seeded once and then left alone, and
structured config is merged key-by-key with your content always winning.

Every managed path and the hash of exactly what was written are recorded in
.ai-sdlc/manifest.json, which is what makes a second run an upgrade instead of
a guess.

Usage:
  install.sh --into <repo> [--profile minimal|standard|full] [--harness NAME ...]
                           [--ci jenkins|github|none ...]
  install.sh --into <repo> --dry-run          # print the plan, change nothing
  install.sh --into <repo> --yes              # non-interactive: keep mine, write .kit-new
  install.sh --into <repo> --take-kit         # non-interactive: prefer the kit
  install.sh --into <repo> --sync             # regenerate derived harness files only
  install.sh --into <repo> doctor             # report wiring, drift, placeholders
  install.sh --into <repo> uninstall          # remove kit-owned files + blocks

Stdlib only; Python 3.9+.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harness  # noqa: E402
import manifest  # noqa: E402
import merge  # noqa: E402
import plan as planner  # noqa: E402

KIT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_REL = ".ai-sdlc/project.json"

PLACEHOLDERS = {
    "name": "<PROJECT_NAME>",
    "desc": "<ONE_LINE_DESCRIPTION>",
    "ticket": "<TICKET>",
    "language": "<PRIMARY_LANGUAGE>",
}

# Tokens an operator is genuinely expected to replace. Deliberately a closed set:
# the template also uses <NNNN>, <KEY>, <URL> and friends as *examples* inside
# prose ("ADR-<NNNN>-<topic>.md"), and flagging those trains people to ignore
# the report.
REAL_PLACEHOLDERS = set(PLACEHOLDERS.values()) | {
    "<SEATS>", "<SEAT_HOLDERS>", "<DIRECTOR_OR_SPONSOR>", "<MANDATORY_STANDARDS>",
    "<LICENSE_AND_IP_RULES>", "<KEY_DATES>", "<DOCS_WIKI_MCP_URL>", "<OTHER_AGENT>",
}

C = {"dim": "\033[2m", "b": "\033[1m", "g": "\033[32m", "y": "\033[33m",
     "r": "\033[31m", "c": "\033[36m", "0": "\033[0m"}


def paint(text, color):
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return text
    return f"{C[color]}{text}{C['0']}"


def kit_version() -> str:
    vf = KIT_ROOT / "VERSION"
    return vf.read_text(encoding="utf-8").strip() if vf.is_file() else "0.0.0"


# --- project settings ------------------------------------------------------

def load_project(root, args) -> dict:
    path = Path(root) / PROJECT_REL
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    for key in PLACEHOLDERS:
        val = getattr(args, key, None)
        if val:
            data[key] = val
    data.setdefault("name", Path(root).resolve().name)
    data.setdefault("slug", data["name"].lower().replace(" ", "-"))
    data.setdefault("desc", PLACEHOLDERS["desc"])
    data.setdefault("ticket", PLACEHOLDERS["ticket"])
    data.setdefault("language", "English")
    return data


def save_project(root, project: dict) -> None:
    path = Path(root) / PROJECT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(project, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_renderer(project: dict):
    """Substitute the project's placeholders in text files. Binaries pass through."""
    pairs = [(PLACEHOLDERS[k], str(project[k])) for k in PLACEHOLDERS if project.get(k)]

    def render(rel: str, data: bytes) -> bytes:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return data
        for token, value in pairs:
            if value != token:
                text = text.replace(token, value)
        return text.encode("utf-8")

    return render


# --- interaction -----------------------------------------------------------

PROMPT = ("  [k]eep mine  [t]ake kit's  [m]erge into .kit-new  [d]iff  "
          "[a]ll-keep  [A]ll-take  [q]uit > ")


class Resolver:
    """Per-conflict decision, with sticky all-keep / all-take answers."""

    def __init__(self, mode="ask"):
        self.mode = mode  # ask | keep | take

    def resolve(self, action, target_root, spec) -> str:
        if self.mode == "keep":
            return "keep"
        if self.mode == "take":
            return "take"
        if not sys.stdin.isatty():
            return "keep"

        path = Path(target_root) / action.rel
        print(f"\n{paint('conflict', 'y')} {paint(action.rel, 'b')} "
              f"({action.cls}, {action.reason})")
        while True:
            try:
                answer = input(PROMPT).strip()
            except EOFError:
                return "keep"
            if answer in ("k", ""):
                return "keep"
            if answer == "t":
                return "take"
            if answer == "m":
                return "sidecar"
            if answer == "a":
                self.mode = "keep"
                return "keep"
            if answer == "A":
                self.mode = "take"
                return "take"
            if answer == "q":
                raise KeyboardInterrupt
            if answer == "d":
                show_diff(path, action.payload)


def show_diff(path: Path, kit_bytes: bytes) -> None:
    try:
        mine = path.read_text(encoding="utf-8").splitlines(keepends=True)
        theirs = kit_bytes.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        print("  (binary file — no diff)")
        return
    diff = list(difflib.unified_diff(mine, theirs, "yours", "kit's", n=2))
    if not diff:
        print("  (identical)")
        return
    for line in diff[:80]:
        color = "g" if line.startswith("+") else "r" if line.startswith("-") else "dim"
        print("  " + paint(line.rstrip("\n"), color))
    if len(diff) > 80:
        print(paint(f"  ... {len(diff) - 80} more lines", "dim"))


# --- apply -----------------------------------------------------------------

def write_file(root, rel, data: bytes) -> None:
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    if rel.endswith(".sh") or rel.startswith("scripts/") and rel.endswith(".py"):
        path.chmod(path.stat().st_mode | 0o111)


def apply(root, actions, man, spec, resolver, dry_run=False) -> dict:
    """Execute the plan. Returns a report of what happened."""
    report = {"created": [], "updated": [], "merged": [], "skipped": [],
              "kept": [], "sidecars": [], "failed": []}
    man.setdefault("deferred", {})

    for action in actions:
        rel, kind = action.rel, action.kind

        if kind == planner.SKIP:
            report["skipped"].append(rel)
            continue

        if kind == planner.CONFLICT:
            choice = resolver.resolve(action, root, spec)
            if choice == "keep":
                if not dry_run:
                    man["deferred"][rel] = manifest.sha256_bytes(action.payload)
                report["kept"].append(rel)
                continue
            if choice == "sidecar":
                if not dry_run:
                    write_file(root, rel + ".kit-new", action.payload)
                    man["deferred"][rel] = manifest.sha256_bytes(action.payload)
                report["sidecars"].append(rel + ".kit-new")
                continue
            kind = planner.CREATE  # "take" falls through to a plain write

        if kind in (planner.CREATE, planner.UPDATE):
            if not dry_run:
                write_file(root, rel, action.payload)
                manifest.record(man, rel, action.cls, action.payload)
                man["deferred"].pop(rel, None)
            report["created" if kind == planner.CREATE else "updated"].append(rel)
            continue

        if kind == planner.MERGE:
            try:
                text, conflicts = planner.merge_preview(root, action, spec)
            except ValueError as exc:
                report["failed"].append(f"{rel}: {exc}")
                if not dry_run:
                    write_file(root, rel + ".kit-new", action.payload)
                report["sidecars"].append(rel + ".kit-new")
                continue
            if not dry_run:
                write_file(root, rel, text.encode("utf-8"))
                manifest.record(man, rel, action.cls, text)
            report["merged"].append(rel + (f"  (kept yours: {', '.join(conflicts)})"
                                           if conflicts else ""))
    return report


# --- CI gate choice --------------------------------------------------------

JENKINSFILE = "ci/Jenkinsfile.ai-governance"
JENKINS_NOTE = ("Jenkins: set the job's Script Path to ci/Jenkinsfile.ai-governance "
                "(a Multibranch Pipeline looks for Jenkinsfile at the root by default)")


def resolve_ci(flag, man, spec) -> list[str]:
    """--ci beats the manifest's record, which beats the default (every gate)."""
    if flag:
        return [] if flag == ["none"] else sorted(set(flag))
    if isinstance(man.get("ci"), list):   # a gate a later kit dropped is ignored
        return [g for g in man["ci"] if g in planner.ci_gates(spec)]
    return planner.ci_gates(spec)


def ci_label(ci) -> str:
    return ", ".join(ci) or "none"


def drop_unselected_ci(root, template_root, spec, ci, man, dry_run=False) -> list[str]:
    """Remove the kit's files of a gate that is no longer chosen — only if unedited.

    The same rule as the Copilot orphan sweep: a managed file still byte-equal to what
    the kit wrote (CLEAN) is deleted; an edited one (MODIFIED) is kept and becomes
    yours, so it leaves the manifest and uninstall will not touch it. A gate file the
    manifest never recorded was not written by the kit and is never touched.
    """
    root = Path(root)
    notes = []
    for rel in planner.unselected_ci_files(template_root, spec, ci):
        if rel not in man.get("files", {}):
            continue
        st = manifest.state(root, man, rel)
        if st == manifest.MODIFIED:
            notes.append(f"{rel} (gate not chosen; kept your edits — it is yours now, "
                         f"delete by hand if unwanted)")
        elif st == manifest.CLEAN:
            if not dry_run:
                (root / rel).unlink()
                _prune_empty_dirs(root, (root / rel).parent)
            notes.append(f"{rel} ({'would remove' if dry_run else 'removed'}; gate not chosen)")
        if not dry_run:
            manifest.forget(man, rel)
            man.get("deferred", {}).pop(rel, None)
    return notes


def _prune_empty_dirs(root: Path, directory: Path) -> None:
    while directory != root and directory.is_dir() and not any(directory.iterdir()):
        directory.rmdir()
        directory = directory.parent


# --- harness wiring --------------------------------------------------------

def wire_harnesses(root, names, table, man, dry_run=False, resolver=None) -> list[str]:
    """Write each harness's surface from the canonical artefacts."""
    root = Path(root)
    resolver = resolver or Resolver("keep")
    notes: list[str] = []
    mcp = {}
    mcp_path = root / ".mcp.json"
    if mcp_path.is_file():
        try:
            mcp = json.loads(mcp_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            notes.append("!! .mcp.json is not valid JSON — MCP surfaces not generated")
    settings = {}
    settings_path = root / ".claude/settings.json"
    if settings_path.is_file():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    for name in names:
        spec = table.get(name)
        if not spec:
            notes.append(f"!! unknown harness: {name}")
            continue
        label = spec.get("label", name)

        for surface in ("brief", "rules", "skills", "mcp", "hooks"):
            sspec = spec.get(surface)
            if not sspec:
                continue
            kind, rel = sspec.get("kind"), sspec.get("path")

            if kind in ("native", "canonical", "shipped"):
                notes.append(f"{label}: {surface} -> {rel} (no file written)")
                continue

            if kind == "symlink":
                notes.append(_symlink(root, rel, sspec["to"], label, surface, dry_run))
                continue

            if kind == "pointer":
                # `also` covers a harness's legacy rules path, so a stale copy of
                # the brief cannot survive there.
                for target in [rel, *sspec.get("also", [])]:
                    style = "mdc" if target.endswith(".mdc") else None
                    text = harness.pointer_text(
                        {"label": label, "style": style}).encode("utf-8")
                    if manifest.state(root, man, target, text) == manifest.IDENTICAL:
                        notes.append(f"{label}: {surface} -> {target} (current)")
                        continue
                    if not dry_run:
                        write_file(root, target, text)
                        manifest.record(man, target, planner.CLASS_OWN, text)
                    notes.append(f"{label}: {surface} -> {target} (pointer written)")
                continue

            if kind == "generated":
                note = _generate(root, rel, sspec, mcp, settings, surface, label, man,
                                 dry_run, resolver)
                if note:
                    notes.append(note)

        if spec.get("mcp", {}) and spec["mcp"].get("invoke"):
            notes.append(f"{label}: run with  {spec['mcp']['invoke']}")
        if spec.get("hooks") is None:
            notes.append(f"{label}: no hook system — session ritual stays manual "
                         f"(scripts/session/*.sh)")
    return notes


def _symlink(root, rel, to, label, surface, dry_run) -> str:
    link, target = root / rel, root / to
    if not target.is_dir():
        return f"{label}: {surface} -> {rel} SKIPPED ({to} missing)"
    want = os.path.relpath(target, link.parent)
    if link.is_symlink() and os.readlink(link) == want:
        return f"{label}: {surface} -> {rel} (current)"
    if link.exists() and not link.is_symlink():
        return f"{label}: {surface} -> {rel} SKIPPED (a real directory is there)"
    if not dry_run:
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink():
            link.unlink()
        try:
            link.symlink_to(want, target_is_directory=True)
        except OSError:
            shutil.copytree(target, link, dirs_exist_ok=True)
            return f"{label}: {surface} -> {rel} (copied; symlinks unavailable)"
    return f"{label}: {surface} -> {rel} -> {want}"


def _generate(root, rel, sspec, mcp, settings, surface, label, man, dry_run,
              resolver) -> str | None:
    if sspec.get("format") in harness.COPILOT_FORMATS:
        return _generate_copilot(root, sspec, surface, label, man, dry_run, resolver)
    fmt = sspec.get("format")
    path = root / rel

    if fmt == "toml-block":
        block = harness.to_codex_toml(mcp)
        existing = path.read_text(encoding="utf-8") if path.is_file() else ""
        try:
            text = merge.merge_toml_block(existing, block)
        except ValueError as exc:
            return f"{label}: {surface} -> {rel} FAILED ({exc})"
        if text == existing:
            return f"{label}: {surface} -> {rel} (current)"
        if not dry_run:
            write_file(root, rel, text.encode("utf-8"))
            manifest.record(man, rel, planner.CLASS_MERGE, text)
        return f"{label}: {surface} -> {rel} (generated from .mcp.json)"

    if fmt == "copilot-mcp":
        data = json.dumps(harness.to_copilot_mcp(mcp), indent=2) + "\n"
    elif fmt == "json" and surface == "mcp":
        existing = path.read_text(encoding="utf-8") if path.is_file() else ""
        data, _ = merge.merge_json(existing, json.dumps({"mcpServers": harness.mcp_servers(mcp)}))
    elif fmt == "json" and surface == "hooks":
        data = json.dumps(harness.to_codex_hooks(settings), indent=2) + "\n"
    else:
        return None

    blob = data.encode("utf-8")
    fresh = manifest.state(root, man, rel, blob) != manifest.IDENTICAL
    if fresh and not dry_run:
        write_file(root, rel, blob)
        manifest.record(man, rel, planner.CLASS_OWN, blob)

    # Some surfaces need a key in the harness's main config pointing at the file
    # we just wrote (Codex: `hooks = "./hooks.json"`). A top-level TOML key must
    # live above the first [table], so it is set in place, not appended.
    note = _write_pointer_key(root, sspec.get("pointer"), man, dry_run)
    suffix = f"; {note}" if note else ""
    if not fresh:
        return f"{label}: {surface} -> {rel} (current{suffix})"
    return f"{label}: {surface} -> {rel} (generated{suffix})"


def _generate_copilot(root, sspec, surface, label, man, dry_run, resolver) -> str:
    """Write the Copilot surfaces sync.py renders. One generator, two callers.

    Own-class files follow the planner's contract: a file you wrote before adopting
    (FOREIGN) or a generated file you edited (MODIFIED) is a conflict for the
    Resolver. Keeping yours writes the kit's copy to <rel>.kit-new, since a generated
    file has no template to diff against, and defers it until that copy changes.
    Merge-class files (the VS Code switch) stay a key-union where your values win.
    """
    classes = {"own": planner.CLASS_OWN, "merge": planner.CLASS_MERGE}
    try:
        files = harness.materialize(root, sspec)
    except (ValueError, OSError) as exc:   # AGENTS.md missing or lacks a section; bad rule
        if dry_run and not (Path(root) / "AGENTS.md").is_file():
            return (f"{label}: {surface} -> {sspec['path']} "
                    f"(would generate after AGENTS.md is installed)")
        return f"{label}: {surface} -> {sspec['path']} FAILED ({exc})"
    deferred = man.setdefault("deferred", {})
    changed, kept = [], []
    for rel, text, cls in files:
        blob = text.encode("utf-8")
        st = manifest.state(root, man, rel, blob)
        if st == manifest.IDENTICAL:
            if rel in deferred and not dry_run:   # you handed it back: kit-owned again
                deferred.pop(rel)
                manifest.record(man, rel, classes[cls], blob)
            continue
        if deferred.get(rel) == manifest.sha256_bytes(blob):
            continue
        if cls == "own" and st in (manifest.FOREIGN, manifest.MODIFIED):
            action = planner.Action(rel, classes[cls], planner.CONFLICT, st, blob)
            if resolver.resolve(action, root, None) != "take":
                if not dry_run:
                    write_file(root, rel + ".kit-new", blob)
                    deferred[rel] = manifest.sha256_bytes(blob)
                kept.append(rel)
                continue
        if not dry_run:
            write_file(root, rel, blob)
            manifest.record(man, rel, classes[cls], blob)
            deferred.pop(rel, None)
        changed.append(rel)
    edited, removed = [], []
    if sspec.get("format") == "copilot-instructions":
        for orphan in harness.orphan_instructions(root, sspec, {r for r, _, _ in files}):
            if manifest.state(root, man, orphan) == manifest.MODIFIED:
                edited.append(orphan)          # its rule is gone, your edits are not
                continue
            if not dry_run:
                (Path(root) / orphan).unlink()
                manifest.forget(man, orphan)
            removed.append(orphan)
    notes = []
    if changed:
        notes.append(f"{', '.join(changed)} (generated)")
    if kept:
        notes.append(f"{', '.join(kept)} (kept yours; kit's copy in .kit-new)")
    if edited:
        notes.append(f"{', '.join(edited)} (source rule deleted; kept your edits — "
                     f"delete by hand if unwanted)")
    if removed:
        notes.append(f"{', '.join(removed)} (removed)")
    if not notes:
        return f"{label}: {surface} -> {sspec['path']} (current)"
    return f"{label}: {surface} -> {'; '.join(notes)}"


def _write_pointer_key(root, pointer, man, dry_run) -> str | None:
    if not pointer:
        return None
    target = Path(root) / pointer["path"]
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    try:
        text = merge.set_toml_root_key(existing, pointer["key"], pointer["value"])
    except ValueError as exc:
        return f"could not set {pointer['key']} in {pointer['path']}: {exc}"
    if text == existing:
        return None
    if not dry_run:
        write_file(root, pointer["path"], text.encode("utf-8"))
        manifest.record(man, pointer["path"], planner.CLASS_MERGE, text)
    return f'{pointer["key"]} set in {pointer["path"]}' 


def baseline_inherited_debt(root) -> int:
    """Record pre-existing frontmatter violations once, at adoption time."""
    validator = Path(root) / "scripts/validate-frontmatter.py"
    baseline = Path(root) / ".ai-sdlc/frontmatter-baseline.txt"
    if not validator.is_file() or baseline.is_file():
        return 0
    try:
        import subprocess
        subprocess.run([sys.executable, str(validator), "--write-baseline"],
                       cwd=root, capture_output=True, timeout=120, check=False)
    except (OSError, Exception):
        return 0
    if not baseline.is_file():
        return 0
    return len([l for l in baseline.read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")])


# --- doctor ----------------------------------------------------------------

def doctor(root, table, spec) -> int:
    """Report wiring, drift and unfinished setup. Non-zero exit on a real problem."""
    root = Path(root)
    man = manifest.load(root, kit_version())
    problems = 0

    print(paint(f"AI-SDLC doctor — {root}", "b"))
    ci = resolve_ci(None, man, spec)
    ci_note = "" if isinstance(man.get("ci"), list) else " (default)"
    print(paint(f"  kit {man.get('kit_version', '?')} · profile {man.get('profile', '-')} "
                f"· ci {ci_label(ci)}{ci_note} "
                f"· {len(man.get('files', {}))} managed files", "dim"))
    if "jenkins" in ci:
        print(paint(f"  {JENKINS_NOTE}", "dim"))

    print(f"\n{paint('Harnesses', 'b')}")
    detected = harness.detect(root, table)
    wired = man.get("harnesses", [])
    for name, hspec in table.items():
        label = hspec.get("label", name)
        if name in wired:
            mark, note = paint("wired", "g"), ""
        elif name in detected:
            mark, note = paint("detected", "y"), " — not wired; re-run the installer"
        else:
            mark, note = paint("absent", "dim"), ""
        print(f"  {label:<22} {mark}{note}")

    print(f"\n{paint('Prerequisites', 'b')}")
    for tool, why in (("git", "attribution, churn gate, commit hooks"),
                      ("python3", "validators, knowledge layer"),
                      ("pre-commit", "local governance gates")):
        found = shutil.which(tool)
        print(f"  {tool:<22} {paint('ok', 'g') if found else paint('missing', 'y')}"
              f"  {paint(why, 'dim')}")
        if not found and tool != "pre-commit":
            problems += 1
    if not (root / ".git").exists():
        print(f"  {'git repo':<22} {paint('no', 'y')}  "
              f"{paint('governance gates need git; run git init when ready', 'dim')}")

    print(f"\n{paint('MCP servers', 'b')}")
    skipped = []
    mcp_path = root / ".mcp.json"
    if mcp_path.is_file():
        try:
            live = harness.mcp_servers(json.loads(mcp_path.read_text(encoding="utf-8")), skipped)
            print(f"  active: {', '.join(sorted(live)) or paint('none', 'y')}")
            for name in skipped:
                print(f"  {paint('skipped', 'y')} {name} "
                      f"{paint('— not emitted to any harness', 'dim')}")
        except json.JSONDecodeError:
            print(f"  {paint('.mcp.json is not valid JSON', 'r')}")
            problems += 1
    if "codex-cli" in wired:
        print(paint("  note: Codex loads .codex/config.toml only in a trusted directory — "
                    "answer 'Yes, continue' on first run.", "dim"))

    print(f"\n{paint('Generated-surface drift', 'b')}")
    drift = check_drift(root, table, man)
    if not drift:
        print(f"  {paint('none', 'g')} — derived harness files match their sources")
    for line in drift:
        print(f"  {paint('drift', 'r')} {line}")
        problems += 1

    print(f"\n{paint('Unfilled placeholders', 'b')}")
    stale = find_placeholders(root, man)
    if not stale:
        print(f"  {paint('none', 'g')}")
    for rel, tokens in sorted(stale.items())[:20]:
        print(f"  {rel}: {', '.join(sorted(tokens))}")
        problems += 1

    baseline = root / ".ai-sdlc/frontmatter-baseline.txt"
    if baseline.is_file():
        debt = [l for l in baseline.read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")]
        if debt:
            print(f"\n{paint('Inherited doc debt', 'b')} "
                  f"{paint('(baselined — gate passes, list should shrink)', 'dim')}")
            for rel in debt[:10]:
                print(f"  {rel}")
            if len(debt) > 10:
                print(paint(f"  ... {len(debt) - 10} more", "dim"))

    deferred = man.get("deferred", {})
    if deferred:
        print(f"\n{paint('Deferred conflicts', 'b')} "
              f"{paint('(you kept yours; re-run to revisit)', 'dim')}")
        for rel in sorted(deferred):
            print(f"  {rel}")

    print()
    print(paint("doctor: ok", "g") if problems == 0
          else paint(f"doctor: {problems} problem(s)", "y"))
    return 0 if problems == 0 else 1


def check_drift(root, table, man) -> list[str]:
    """Derived harness surfaces that no longer match their sources.

    The same check as `scripts/harness/sync.py --check` and the CI gate: AGENTS.md
    -> Copilot brief, .claude/rules -> path instructions, the VS Code switch, and
    .mcp.json -> the MCP files.
    """
    try:
        return harness.check(root, table, man.get("harnesses", []))
    except json.JSONDecodeError:
        return [".mcp.json is not valid JSON"]


# Seed files are unmanaged by design — but AGENTS.md is the one file whose
# placeholders matter most, so the brief is always scanned, manifest or not.
ALWAYS_SCAN = ("AGENTS.md", "WORKING-AGREEMENT.md", "README.md", ".mcp.json")


def find_placeholders(root, man) -> dict:
    """Files still carrying a token the operator is expected to fill in."""
    out: dict[str, set] = {}
    for rel in [*man.get("files", {}), *ALWAYS_SCAN]:
        path = Path(root) / rel
        if not path.is_file() or path.suffix in (".png", ".pptx", ".zip", ".db"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        found = {t for t in REAL_PLACEHOLDERS if t in text}
        if found:
            out[rel] = found
    return out


# --- uninstall -------------------------------------------------------------

def uninstall(root, dry_run=False) -> int:
    """Remove kit-owned files and sentinel blocks. Seed files are yours; kept."""
    root = Path(root)
    man = manifest.load(root, kit_version())
    removed, kept, changed = [], [], []

    for rel, entry in sorted(man.get("files", {}).items()):
        path = root / rel
        cls = entry.get("class")
        if cls == planner.CLASS_SEED:
            kept.append(rel)
            continue
        if cls == planner.CLASS_MERGE and path.is_file():
            text = path.read_text(encoding="utf-8")
            if merge.extract_block(text) is not None:
                stripped = merge.merge_block(text, "").replace(
                    f"{merge.BEGIN}\n\n{merge.END}\n", "")
                if not dry_run:
                    path.write_text(stripped, encoding="utf-8")
                changed.append(rel)
            else:
                kept.append(rel)
            continue
        if path.is_symlink() or path.exists():
            if not dry_run:
                if path.is_symlink() or path.is_file():
                    path.unlink()
                else:
                    shutil.rmtree(path)
            removed.append(rel)

    if not dry_run:
        shutil.rmtree(root / ".ai-sdlc", ignore_errors=True)

    print(f"{'would remove' if dry_run else 'removed'}: {len(removed)} kit-owned files")
    print(f"stripped sentinel blocks from: {len(changed)}")
    print(f"left in place (yours): {len(kept)}")
    for rel in kept:
        print(f"  {rel}")
    return 0


# --- CLI -------------------------------------------------------------------

def print_plan(actions, report=None) -> None:
    order = [planner.CREATE, planner.UPDATE, planner.MERGE, planner.CONFLICT, planner.SKIP]
    colors = {planner.CREATE: "g", planner.UPDATE: "c", planner.MERGE: "c",
              planner.CONFLICT: "y", planner.SKIP: "dim"}
    for kind in order:
        items = [a for a in actions if a.kind == kind]
        if not items:
            continue
        print(f"\n{paint(kind, colors[kind])} ({len(items)})")
        for a in items[:200]:
            note = f"  {paint(a.reason, 'dim')}" if kind != planner.CREATE else ""
            print(f"  {a.rel}{note}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="install.sh", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="install",
                    choices=["install", "doctor", "uninstall"])
    ap.add_argument("--into", default=".", help="target repo (default: cwd)")
    ap.add_argument("--profile", default=None,
                    choices=["minimal", "standard", "full"])
    ap.add_argument("--harness", action="append", default=None,
                    help="harness to wire (repeatable); default: auto-detect")
    ap.add_argument("--ci", action="append", default=None,
                    choices=["jenkins", "github", "none"],
                    help="CI gate to install (repeatable); default: the recorded "
                         "choice, else all")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    ap.add_argument("--yes", action="store_true", help="non-interactive; keep yours on conflict")
    ap.add_argument("--take-kit", action="store_true", help="non-interactive; prefer the kit")
    ap.add_argument("--sync", action="store_true",
                    help="only regenerate derived harness surfaces")
    ap.add_argument("--name"), ap.add_argument("--slug")
    ap.add_argument("--desc"), ap.add_argument("--ticket"), ap.add_argument("--language")
    args = ap.parse_args(argv)
    if args.ci and "none" in args.ci and len(set(args.ci)) > 1:
        ap.error("--ci none cannot be combined with a gate")

    root = Path(args.into).resolve()
    if not root.is_dir():
        print(f"install: target is not a directory: {root}", file=sys.stderr)
        return 2

    table = harness.load_table()
    spec = planner.load_classes()

    if args.command == "doctor":
        return doctor(root, table, spec)
    if args.command == "uninstall":
        return uninstall(root, args.dry_run)

    template_root = KIT_ROOT / "template"
    if not (template_root / "AGENTS.md").is_file():
        print(f"install: no template at {template_root}", file=sys.stderr)
        return 2

    man = manifest.load(root, kit_version())
    first_install_done = bool(man.get("files"))
    profile = args.profile or man.get("profile") or "standard"
    project = load_project(root, args)
    names = args.harness or man.get("harnesses") or harness.detect(root, table)
    ci = resolve_ci(args.ci, man, spec)

    print(paint(f"AI-SDLC kit {kit_version()} -> {root}", "b"))
    print(paint(f"  profile {profile} · ci {ci_label(ci)} · "
                f"harnesses: {', '.join(names) or 'none detected'}", "dim"))
    if not (root / ".git").exists():
        print(paint("  note: not a git repo — the installer will not run git init for you.", "y"))

    actions = []
    if not args.sync:
        actions = planner.build(template_root, root, spec, profile, man,
                                render=make_renderer(project), ci=ci)
        print_plan(actions)
        if args.dry_run:
            counts = planner.summarize(actions)
            print(f"\n{paint('dry run', 'c')} — nothing written. {counts}")

    mode = "keep" if args.yes else "take" if args.take_kit else "ask"
    resolver = Resolver(mode)

    try:
        report = apply(root, actions, man, spec, resolver, dry_run=args.dry_run)
        ci_notes = [] if args.sync else drop_unselected_ci(
            root, template_root, spec, ci, man, dry_run=args.dry_run)
        notes = wire_harnesses(root, names, table, man, dry_run=args.dry_run,
                               resolver=resolver)
    except KeyboardInterrupt:
        print("\ninstall: aborted; nothing further written.")
        return 130

    if ci_notes:
        print(f"\n{paint('CI gate', 'b')}")
        for note in ci_notes:
            print(f"  {note}")
    if JENKINSFILE in report.get("created", []):
        print(paint(f"\n  {JENKINS_NOTE}", "dim"))

    print(f"\n{paint('Harness wiring', 'b')}")
    for note in notes:
        print(f"  {note}")

    if not args.dry_run and not first_install_done:
        baselined = baseline_inherited_debt(root)
        if baselined:
            print(f"\n{paint('Inherited docs', 'b')}")
            print(f"  {baselined} pre-existing file(s) recorded in "
                  f".ai-sdlc/frontmatter-baseline.txt as known debt.")
            print(paint("  The gate passes; the list only shrinks. `doctor` keeps it visible.",
                        "dim"))

    if not args.dry_run:
        man["kit_version"] = kit_version()
        man["profile"] = profile
        man["harnesses"] = names
        man["ci"] = ci
        manifest.save(root, man)
        save_project(root, project)

    print(f"\n{paint('Result', 'b')}")
    for key in ("created", "updated", "merged", "kept", "sidecars", "failed"):
        items = report.get(key) or []
        if items:
            print(f"  {key}: {len(items)}")
            if key in ("merged", "sidecars", "failed", "kept"):
                for item in items:
                    print(f"    {item}")
    print(f"  skipped: {len(report.get('skipped') or [])}")

    if not args.dry_run:
        print(f"\nNext: {paint('./install.sh --into . doctor', 'c')} to verify, then open the "
              f"repo in your harness — ONBOARDING.md runs on first session.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
