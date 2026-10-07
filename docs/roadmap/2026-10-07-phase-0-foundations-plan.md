# Phase 0 — Foundations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give the kit a working brownfield installer that also wires **GitHub Copilot** (CLI, VS Code, IntelliJ) from the kit's canonical sources, with a drift gate, and start versioning the kit as a product the client can own.

**Architecture:** Merge the unmerged `feat/brownfield-installer` branch, which already has a data-driven harness adapter table (`template/scripts/harness/harnesses.json`), a stdlib generator/drift checker (`sync.py`), and an upgrade-safe install manifest that records `kit_version`. Extend the Copilot adapter row with three generated surfaces:

- `.github/copilot-instructions.md`: a pointer, plus `AGENTS.md` §0 (the onboarding gate) and §3 (the hard constraints) inlined verbatim. IntelliJ's Copilot Chat does not read `AGENTS.md`.
- `.github/instructions/<rule>.instructions.md`: generated from each `.claude/rules/*.md`, with `paths:` mapped to `applyTo:`.
- `.vscode/settings.json`: sets `chat.useClaudeHooks: true`, so VS Code runs the kit's `.claude/settings.json` hooks. Copilot CLI reads them natively, and IntelliJ has no session hooks.

All generation lives in `sync.py`; the installer only consumes it. Adding a rule, harness or surface stays **one data/rule file + `python3 scripts/harness/sync.py --write`** (client-ownership constraint).

**Tech Stack:** Python 3.12 stdlib only (`json`, `re`, `pathlib`, `unittest`), JSON adapter table, Markdown, GitHub Actions (kit CI), Jenkins (example stage for FRQ), pre-commit.

**Design source:** [`2026-10-07-onboarding-roles-and-skills-design.md`](./2026-10-07-onboarding-roles-and-skills-design.md) §3.6, §4.0, §4d-1, §4d-2, §6. Brownfield design: `docs/roadmap/2026-08-28-brownfield-adoption-design.md` (arrives with the merge).

## Global constraints

- Branch: `feat/onboarding-roles-skills`. **Every commit is reviewed by a human before the next task starts** (kit rule: a human validates every AI-written line).
- Stdlib only in `template/scripts/**` and `scripts/install/**`. No new dependencies.
- In zsh, quote git revision paths with braces: `git show "${B}:path"` (a bare `$B:t` is a zsh modifier).
- Run tests by path, as kit CI does: `python3 <test_file>.py`.
- Do **not** touch the MCP surfaces in this phase. The `policy.mcp_allowed` gate is Phase 2.

---

### Task 1: Merge the brownfield installer

**Files:** merge only (28 files arrive; see `git diff --stat` below).

**Step 1: Confirm a clean merge**

Run:
```bash
git fetch origin
git merge-tree --write-tree HEAD origin/feat/brownfield-installer >/dev/null && echo CLEAN
git diff --stat "$(git merge-base HEAD origin/feat/brownfield-installer)" origin/feat/brownfield-installer | tail -1
```
Expected: `CLEAN`, then `28 files changed, 2882 insertions(+), 33 deletions(-)`.

**Step 2: Merge**

```bash
git merge --no-ff origin/feat/brownfield-installer -m "merge: brownfield installer into onboarding-roles-skills"
```

**Step 3: Remove orphaned bytecode left from the branch's earlier checkout**

```bash
find scripts/install template/scripts/harness -name '__pycache__' -type d -prune -exec rm -rf {} +
git status --short
```
Expected: no `__pycache__` entries (they were untracked).

**Step 4: Run the installer and template test suites**

```bash
for t in scripts/install/tests/test_manifest.py scripts/install/tests/test_merge.py \
         scripts/install/tests/test_harness.py scripts/install/tests/test_plan.py \
         scripts/install/tests/test_adopt.py \
         template/scripts/tests/test_validate_moments.py \
         template/scripts/tests/test_validate_seat_profiles.py; do
  python3 "$t" || { echo "FAIL $t"; break; }
done
```
Expected: every file ends `OK`.

**Step 5: Human review checkpoint.** Show `git log --oneline -3` and the test output, and wait for approval before Task 2.

---

### Task 2: Verify the Copilot surfaces on the FRQ VM (spike, decision gate)

The plan assumes four facts from the 2026-10-07 research (design note §3.6). Verify them on the Ubuntu VM with the client's Copilot versions **before** writing code. If any check fails, stop and bring the result to the human. Do not improvise around it.

**Files:**
- Modify: `docs/roadmap/2026-10-07-onboarding-roles-and-skills-design.md` (§3.6, append a "Verified on VM" table)

**Step 1: Prepare a throwaway repo on the VM**

```bash
mkdir -p ~/copilot-spike && cd ~/copilot-spike && git init -q
mkdir -p .claude/skills/spike-skill .claude .github/instructions .vscode
printf -- '---\nname: spike-skill\ndescription: Use when the user says SPIKE-SKILL.\n---\nReply exactly: SKILL-OK\n' > .claude/skills/spike-skill/SKILL.md
printf '{"hooks":{"SessionStart":[{"hooks":[{"type":"command","command":"echo HOOK-OK >> /tmp/spike-hook.log"}]}]}}\n' > .claude/settings.json
printf 'Always end every answer with the word BRIEF-OK.\n' > .github/copilot-instructions.md
printf -- "---\napplyTo: 'docs/**'\n---\nWhen editing docs, end every answer with RULE-OK.\n" > .github/instructions/spike.instructions.md
printf '{"chat.useClaudeHooks": true}\n' > .vscode/settings.json
```

**Step 2: Check each surface and record the result**

| # | Check | How | Pass when |
|---|---|---|---|
| 1 | Copilot CLI runs `.claude/settings.json` hooks | `rm -f /tmp/spike-hook.log; copilot -p "hello"` | `/tmp/spike-hook.log` contains `HOOK-OK` |
| 2 | Copilot CLI discovers `.claude/skills` | `copilot -p "SPIKE-SKILL"` | the answer contains `SKILL-OK` |
| 3 | VS Code Chat runs Claude hooks with `chat.useClaudeHooks` | open the folder in VS Code, start a chat | the log gets a second `HOOK-OK` |
| 4 | IntelliJ Chat reads `.github/copilot-instructions.md` | open in IntelliJ, ask anything | the answer ends `BRIEF-OK` |
| 5 | IntelliJ Chat applies `.github/instructions` `applyTo` | ask about a file under `docs/` | the answer ends `RULE-OK` |

**Step 3: Decision**

- **All pass** → continue to Task 3.
- **1 fails** → stop. The fallback is a generated `.github/hooks/ai-sdlc.json` in Copilot's flat format (`{"hooks":{"SessionStart":[{"type":"command","command":…,"powershell":…,"timeout":10}]}}`, the same shape Cartograph writes). It needs a design decision on double-firing, so it goes back to the human.
- **3 fails** → drop the `.vscode/settings.json` surface from Tasks 3–7, and document "VS Code: run `bash scripts/session/start.sh` at session start" in the generated brief.
- **4 or 5 fails** → stop and escalate. The IntelliJ approach needs rethinking.

**Step 4: Record and commit**

Append to §3.6 of the design note:
```markdown
**Verified on the FRQ VM (<date>, Copilot CLI <version>, VS Code <version>, IntelliJ <version> + Copilot plugin <version>):** 1 ✅/❌ · 2 ✅/❌ · 3 ✅/❌ · 4 ✅/❌ · 5 ✅/❌
```
```bash
git add docs/roadmap/2026-10-07-onboarding-roles-and-skills-design.md
git commit -m "docs(roadmap): record Copilot surface verification on the FRQ VM"
```

**Step 5: Human review checkpoint.**

---

### Task 3: Copilot adapter row: declare the new surfaces (data first)

**Files:**
- Modify: `template/scripts/harness/harnesses.json` (the `copilot-cli` row)
- Modify: `scripts/install/tests/test_harness.py` (add tests)

**Step 1: Write the failing test.** Append to `scripts/install/tests/test_harness.py`, inside `class TestTable`:

```python
    def test_copilot_generates_brief_rules_and_vscode_hooks(self):
        row = harness.load_table()["copilot-cli"]
        self.assertEqual(row["brief"]["kind"], "generated")
        self.assertEqual(row["brief"]["path"], ".github/copilot-instructions.md")
        self.assertEqual(row["brief"]["format"], "copilot-brief")
        self.assertEqual(row["brief"]["sections"], ["0", "3"])
        self.assertEqual(row["rules"]["format"], "copilot-instructions")
        self.assertEqual(row["rules"]["path"], ".github/instructions")
        self.assertEqual(row["rules"]["from"], ".claude/rules")
        self.assertEqual(row["hooks"]["format"], "vscode-claude-hooks")
        self.assertEqual(row["hooks"]["path"], ".vscode/settings.json")

    def test_copilot_is_detected_by_its_generated_brief(self):
        table = harness.load_table()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".github/instructions").mkdir(parents=True)
            self.assertIn("copilot-cli", harness.detect(tmp, table))
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/install/tests/test_harness.py`
Expected: FAIL, with `KeyError: 'rules'` or an `AssertionError` on `brief.kind`.

**Step 3: Update the row.** Replace the whole `"copilot-cli"` object in `template/scripts/harness/harnesses.json` with:

```json
  "copilot-cli": {
    "label": "GitHub Copilot (CLI, VS Code, IntelliJ)",
    "detect": ["cmd:copilot", "path:.github/copilot-instructions.md", "path:.github/instructions"],
    "brief":  {"kind": "generated", "path": ".github/copilot-instructions.md",
               "format": "copilot-brief", "sections": ["0", "3"],
               "$note": "IntelliJ Copilot Chat does not read AGENTS.md, so the onboarding gate (§0) and hard constraints (§3) are inlined verbatim. VS Code Chat and Copilot CLI also read AGENTS.md natively."},
    "rules":  {"kind": "generated", "path": ".github/instructions",
               "format": "copilot-instructions", "from": ".claude/rules",
               "$note": "One <rule>.instructions.md per .claude/rules/<rule>.md; paths: becomes applyTo:."},
    "skills": {"kind": "native", "path": ".claude/skills",
               "$note": "Copilot discovers .github/skills, .agents/skills AND .claude/skills — the kit's skills work unchanged."},
    "mcp":    {"kind": "generated", "path": ".copilot/mcp-config.json", "format": "copilot-mcp",
               "invoke": "copilot --additional-mcp-config @.copilot/mcp-config.json"},
    "hooks":  {"kind": "generated", "path": ".vscode/settings.json", "format": "vscode-claude-hooks",
               "$note": "Copilot CLI runs .claude/settings.json hooks natively; VS Code needs chat.useClaudeHooks; IntelliJ has no session hooks (the generated brief tells the agent to run scripts/session/start.sh)."}
  },
```
Also update the `$comment` date line to read: `Surfaces verified against the shipping binaries on 2026-08-28; Copilot re-verified <Task 2 date>; see …`.

**Step 4: Run the test to verify it passes**

Run: `python3 scripts/install/tests/test_harness.py`
Expected: `OK`.

**Step 5: Commit**

```bash
git add template/scripts/harness/harnesses.json scripts/install/tests/test_harness.py
git commit -m "feat(harness): declare Copilot brief, rules and VS Code hook surfaces"
```

---

### Task 4: Render the Copilot brief from AGENTS.md

**Files:**
- Modify: `template/scripts/harness/sync.py` (add renderers after the `pointer_text` function)
- Create: `template/scripts/tests/test_harness_copilot.py`

**Step 1: Write the failing test.** Create `template/scripts/tests/test_harness_copilot.py`:

```python
#!/usr/bin/env python3
"""Unit tests for the Copilot surfaces generated by scripts/harness/sync.py."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
import sync  # noqa: E402

AGENTS = """# AGENTS.md — `Demo`

Intro.

---

## 0. Startup — user identity and onboarding

1. **If `USER.md` does not exist** → follow [`ONBOARDING.md`](./ONBOARDING.md).

---

## 1. Mission

Not copied.

## 3. Hard constraints (non-negotiable)

- **No secrets in the repo.**

## 4. AI tools & the trust contract

### 4.1 Tools in use

Not copied either.
"""

BRIEF_SPEC = {"kind": "generated", "path": ".github/copilot-instructions.md",
              "format": "copilot-brief", "sections": ["0", "3"]}


def repo(tmp, agents=AGENTS):
    root = Path(tmp)
    (root / "AGENTS.md").write_text(agents, encoding="utf-8")
    return root


class TestBrief(unittest.TestCase):
    def test_inlines_only_the_requested_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = sync.render_copilot_brief(repo(tmp), BRIEF_SPEC)
            self.assertIn("## 0. Startup", text)
            self.assertIn("## 3. Hard constraints", text)
            self.assertNotIn("## 1. Mission", text)
            self.assertNotIn("### 4.1", text)

    def test_marks_itself_generated_and_points_at_agents(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = sync.render_copilot_brief(repo(tmp), BRIEF_SPEC)
            self.assertIn(sync.GENERATED_MARK, text)
            self.assertIn("](../AGENTS.md)", text)

    def test_rewrites_repo_relative_links_for_the_github_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = sync.render_copilot_brief(repo(tmp), BRIEF_SPEC)
            self.assertIn("](../ONBOARDING.md)", text)
            self.assertNotIn("](./ONBOARDING.md)", text)

    def test_drops_section_separators(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = sync.render_copilot_brief(repo(tmp), BRIEF_SPEC)
            self.assertNotIn("\n---\n\n## 3.", text)

    def test_missing_section_is_an_error_not_a_silent_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = dict(BRIEF_SPEC, sections=["0", "9"])
            with self.assertRaises(ValueError) as ctx:
                sync.render_copilot_brief(repo(tmp), spec)
            self.assertIn("9", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 template/scripts/tests/test_harness_copilot.py`
Expected: FAIL with `AttributeError: module 'sync' has no attribute 'render_copilot_brief'`.

**Step 3: Implement.** In `template/scripts/harness/sync.py`, add after `pointer_text`:

```python
# --- Copilot surfaces ------------------------------------------------------

GENERATED_MARK = "Generated by scripts/harness/sync.py"
REGENERATE = "python3 scripts/harness/sync.py --write"

COPILOT_BRIEF = """\
<!-- {mark} from AGENTS.md — do not edit. Regenerate: {regen} -->
# GitHub Copilot — project brief

**The single source of truth is [`AGENTS.md`](../AGENTS.md). Read it in full before any project work.**
IntelliJ's Copilot Chat does not load `AGENTS.md` by itself, so the sections every
session needs are copied below verbatim. If this file and `AGENTS.md` ever disagree,
`AGENTS.md` wins.

**No session hook ran?** (IntelliJ has none.) Run `bash scripts/session/start.sh`
yourself at the start of the session and follow its output.

{sections}
"""

_SECTION = re.compile(r"^## (\d+)\.", re.M)


def agents_sections(text: str, numbers) -> str:
    """The `## N.` sections of AGENTS.md named in `numbers`, verbatim, in file order."""
    starts = [(m.group(1), m.start()) for m in _SECTION.finditer(text)]
    found = {num for num, _ in starts}
    missing = [n for n in numbers if n not in found]
    if missing:
        raise ValueError(f"AGENTS.md has no section(s): {', '.join(missing)}")
    chunks = []
    for i, (num, pos) in enumerate(starts):
        if num in numbers:
            end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
            chunk = text[pos:end].rstrip()
            if chunk.endswith("---"):
                chunk = chunk[:-3].rstrip()
            chunks.append(chunk)
    return "\n\n".join(chunks)


def render_copilot_brief(root, spec: dict) -> str:
    agents = (Path(root) / "AGENTS.md").read_text(encoding="utf-8")
    body = agents_sections(agents, spec.get("sections", ["0", "3"]))
    body = body.replace("](./", "](../")   # the brief lives in .github/
    return COPILOT_BRIEF.format(mark=GENERATED_MARK, regen=REGENERATE, sections=body)
```

**Step 4: Run the test to verify it passes**

Run: `python3 template/scripts/tests/test_harness_copilot.py`
Expected: `OK` (5 tests).

**Step 5: Commit**

```bash
git add template/scripts/harness/sync.py template/scripts/tests/test_harness_copilot.py
git commit -m "feat(harness): render the Copilot brief from AGENTS.md §0 and §3"
```

---

### Task 5: Render `.github/instructions/*` from `.claude/rules/*`

**Files:**
- Modify: `template/scripts/harness/sync.py`
- Modify: `template/scripts/tests/test_harness_copilot.py`

**Step 1: Write the failing test.** Append before `if __name__`:

```python
RULES_SPEC = {"kind": "generated", "path": ".github/instructions",
              "format": "copilot-instructions", "from": ".claude/rules"}


def rules(tmp, files):
    root = Path(tmp)
    (root / ".claude/rules").mkdir(parents=True)
    for name, text in files.items():
        (root / ".claude/rules" / name).write_text(text, encoding="utf-8")
    return root


class TestInstructions(unittest.TestCase):
    def test_paths_become_apply_to(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = rules(tmp, {"adr.md": '---\npaths:\n  - "docs/adr/**"\n  - "docs/x/**"\n---\n# ADR\nBody.\n'})
            out = sync.render_copilot_instructions(root, RULES_SPEC)
            text = out[".github/instructions/adr.instructions.md"]
            self.assertTrue(text.startswith("---\napplyTo: 'docs/adr/**,docs/x/**'\n---\n"))
            self.assertIn("# ADR\nBody.", text)
            self.assertIn(sync.GENERATED_MARK, text)

    def test_rule_without_paths_applies_everywhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = rules(tmp, {"tokens.md": "# Token economy\nRule.\n"})
            text = sync.render_copilot_instructions(root, RULES_SPEC)[
                ".github/instructions/tokens.instructions.md"]
            self.assertTrue(text.startswith("---\napplyTo: '**'\n---\n"))

    def test_orphans_are_only_our_generated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = rules(tmp, {"a.md": "# A\n"})
            out_dir = root / ".github/instructions"
            out_dir.mkdir(parents=True)
            (out_dir / "gone.instructions.md").write_text(
                f"<!-- {sync.GENERATED_MARK} -->\n", encoding="utf-8")
            (out_dir / "cartograph.instructions.md").write_text("not ours\n", encoding="utf-8")
            wanted = sync.render_copilot_instructions(root, RULES_SPEC)
            self.assertEqual(sync.orphan_instructions(root, RULES_SPEC, wanted),
                             [".github/instructions/gone.instructions.md"])
```

**Step 2: Run to verify it fails**

Run: `python3 template/scripts/tests/test_harness_copilot.py`
Expected: FAIL with `AttributeError: … render_copilot_instructions`.

**Step 3: Implement.** Add to `sync.py` after `render_copilot_brief`:

```python
def _split_frontmatter(text: str) -> tuple[str, str]:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            return text[4:end], text[end + 4:].lstrip("\n")
    return "", text


def _rule_paths(front: str) -> list[str]:
    """The `paths:` list of a .claude/rules frontmatter (the only key the rules use)."""
    out, inside = [], False
    for line in front.splitlines():
        if re.match(r"^paths:\s*$", line):
            inside = True
            continue
        if inside:
            m = re.match(r"""^\s+-\s+["']?([^"']+?)["']?\s*$""", line)
            if m:
                out.append(m.group(1))
                continue
            if line.strip():
                inside = False
    return out


def render_copilot_instructions(root, spec: dict) -> dict:
    """{repo-relative path: text} — one .instructions.md per .claude/rules/*.md."""
    src_rel = spec.get("from", ".claude/rules")
    src = Path(root) / src_rel
    files = {}
    for rule in sorted(src.glob("*.md")) if src.is_dir() else []:
        front, body = _split_frontmatter(rule.read_text(encoding="utf-8"))
        apply_to = ",".join(_rule_paths(front)) or "**"
        rel = f"{spec['path']}/{rule.stem}.instructions.md"
        files[rel] = (f"---\napplyTo: '{apply_to}'\n---\n"
                      f"<!-- {GENERATED_MARK} from {src_rel}/{rule.name} — do not edit. "
                      f"Regenerate: {REGENERATE} -->\n\n{body}")
    return files


def orphan_instructions(root, spec: dict, wanted: dict) -> list[str]:
    """Generated instruction files whose source rule was deleted. Never touches files we did not write."""
    out_dir = Path(root) / spec["path"]
    if not out_dir.is_dir():
        return []
    orphans = []
    for p in sorted(out_dir.glob("*.instructions.md")):
        rel = f"{spec['path']}/{p.name}"
        if rel not in wanted and GENERATED_MARK in p.read_text(encoding="utf-8"):
            orphans.append(rel)
    return orphans
```

**Step 4: Run to verify it passes**

Run: `python3 template/scripts/tests/test_harness_copilot.py`
Expected: `OK` (8 tests).

**Step 5: Commit**

```bash
git add template/scripts/harness/sync.py template/scripts/tests/test_harness_copilot.py
git commit -m "feat(harness): generate Copilot path instructions from .claude/rules"
```

---

### Task 6: VS Code hook switch (`chat.useClaudeHooks`)

**Files:**
- Modify: `template/scripts/harness/sync.py`
- Modify: `template/scripts/tests/test_harness_copilot.py`

**Step 1: Write the failing test.** Append before `if __name__`:

```python
class TestVscode(unittest.TestCase):
    def test_adds_the_switch_and_keeps_existing_settings(self):
        out = sync.render_vscode_settings('{"editor.tabSize": 2}')
        data = json.loads(out)
        self.assertIs(data["chat.useClaudeHooks"], True)
        self.assertEqual(data["editor.tabSize"], 2)

    def test_operator_false_wins(self):
        out = sync.render_vscode_settings('{"chat.useClaudeHooks": false}')
        self.assertIs(json.loads(out)["chat.useClaudeHooks"], False)

    def test_jsonc_is_left_untouched(self):
        jsonc = '{\n  // my comment\n  "a": 1\n}\n'
        self.assertEqual(sync.render_vscode_settings(jsonc), jsonc)

    def test_state(self):
        self.assertEqual(sync.vscode_hooks_state('{"chat.useClaudeHooks": true}'), "ok")
        self.assertEqual(sync.vscode_hooks_state('{}'), "missing")
        self.assertEqual(sync.vscode_hooks_state('{"chat.useClaudeHooks": false}'), "disabled")
        self.assertEqual(sync.vscode_hooks_state('{ // c\n}'), "unparseable")
```

**Step 2: Run to verify it fails**

Run: `python3 template/scripts/tests/test_harness_copilot.py`
Expected: FAIL with `AttributeError: … render_vscode_settings`.

**Step 3: Implement.** Add to `sync.py`:

```python
VSCODE_HOOKS_KEY = "chat.useClaudeHooks"


def render_vscode_settings(existing_text: str) -> str:
    """Union the kit's one key into .vscode/settings.json. Operator values win.

    VS Code settings are often JSONC (comments). We never rewrite a file we cannot
    parse; `check` reports it and the operator sets the key by hand.
    """
    try:
        text, _ = merge.merge_json(existing_text, json.dumps({VSCODE_HOOKS_KEY: True}))
    except ValueError:
        return existing_text
    return text


def vscode_hooks_state(text: str) -> str:
    try:
        data = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError:
        return "unparseable"
    if VSCODE_HOOKS_KEY not in data:
        return "missing"
    return "ok" if data[VSCODE_HOOKS_KEY] is True else "disabled"
```

**Step 4: Run to verify it passes**

Run: `python3 template/scripts/tests/test_harness_copilot.py`
Expected: `OK` (12 tests).

**Step 5: Commit**

```bash
git add template/scripts/harness/sync.py template/scripts/tests/test_harness_copilot.py
git commit -m "feat(harness): turn on Claude hooks for VS Code Copilot Chat"
```

---

### Task 7: Generalise `--check` / `--write` to the new surfaces

**Files:**
- Modify: `template/scripts/harness/sync.py` (`derived_surfaces`, `check`, `write`, plus a new `materialize`)
- Modify: `template/scripts/tests/test_harness_copilot.py`

**Step 1: Write the failing test.** Append before `if __name__`:

```python
class TestCheckWrite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = repo(self.tmp.name)
        (self.root / ".claude/rules").mkdir(parents=True)
        (self.root / ".claude/rules/adr.md").write_text(
            '---\npaths:\n  - "docs/adr/**"\n---\n# ADR\n', encoding="utf-8")
        self.table = sync.load_table()

    def tearDown(self):
        self.tmp.cleanup()

    def test_fresh_repo_drifts_then_write_fixes_it(self):
        problems = sync.check(self.root, self.table, ["copilot-cli"])
        self.assertTrue(any("copilot-instructions.md" in p for p in problems))
        written = sync.write(self.root, self.table, ["copilot-cli"])
        self.assertIn(".github/copilot-instructions.md", written)
        self.assertIn(".github/instructions/adr.instructions.md", written)
        self.assertIn(".vscode/settings.json", written)
        self.assertEqual([p for p in sync.check(self.root, self.table, ["copilot-cli"])
                          if "mcp" not in p], [])

    def test_editing_agents_md_is_drift(self):
        sync.write(self.root, self.table, ["copilot-cli"])
        agents = self.root / "AGENTS.md"
        agents.write_text(agents.read_text().replace("No secrets", "No secrets, ever"),
                          encoding="utf-8")
        problems = sync.check(self.root, self.table, ["copilot-cli"])
        self.assertIn(".github/copilot-instructions.md differs from its source", problems)

    def test_deleted_rule_leaves_an_orphan_that_write_removes(self):
        sync.write(self.root, self.table, ["copilot-cli"])
        (self.root / ".claude/rules/adr.md").unlink()
        self.assertIn(".github/instructions/adr.instructions.md is an orphan",
                      sync.check(self.root, self.table, ["copilot-cli"]))
        sync.write(self.root, self.table, ["copilot-cli"])
        self.assertFalse((self.root / ".github/instructions/adr.instructions.md").exists())

    def test_unparseable_vscode_settings_is_reported_not_rewritten(self):
        vs = self.root / ".vscode/settings.json"
        vs.parent.mkdir()
        vs.write_text('{ // mine\n}\n', encoding="utf-8")
        sync.write(self.root, self.table, ["copilot-cli"])
        self.assertEqual(vs.read_text(), '{ // mine\n}\n')
        self.assertTrue(any("set \"chat.useClaudeHooks\": true by hand" in p
                            for p in sync.check(self.root, self.table, ["copilot-cli"])))
```

**Step 2: Run to verify it fails**

Run: `python3 template/scripts/tests/test_harness_copilot.py`
Expected: FAIL. `check` only knows MCP surfaces, so `copilot-instructions.md` is never reported.

**Step 3: Implement.** In `sync.py`:

(a) Add `materialize` and `_instruction_specs` after the Copilot renderers:

```python
COPILOT_FORMATS = ("copilot-brief", "copilot-instructions", "vscode-claude-hooks")


def materialize(root, sspec: dict) -> list[tuple[str, str, str]]:
    """(rel, text, install-class) for a generated Copilot surface. Shared by sync and the installer."""
    fmt = sspec.get("format")
    if fmt == "copilot-brief":
        return [(sspec["path"], render_copilot_brief(root, sspec), "own")]
    if fmt == "copilot-instructions":
        return [(rel, text, "own")
                for rel, text in render_copilot_instructions(root, sspec).items()]
    if fmt == "vscode-claude-hooks":
        path = Path(root) / sspec["path"]
        have = path.read_text(encoding="utf-8") if path.is_file() else ""
        return [(sspec["path"], render_vscode_settings(have), "merge")]
    return []


def _instruction_specs(table, harnesses):
    """The generated copilot-instructions spec of each harness, found even when no rules exist."""
    for name in harnesses:
        rspec = (table.get(name) or {}).get("rules") or {}
        if rspec.get("kind") == "generated" and rspec.get("format") == "copilot-instructions":
            yield rspec
```

(b) Replace `derived_surfaces`, `check` and `write` entirely with:

```python
SURFACES = ("brief", "rules", "mcp", "hooks")


def derived_surfaces(root, table, harnesses):
    """(rel, want_text, mode, spec) for every generated surface of the given harnesses.

    mode: 'whole-file' | 'block' (TOML block) | 'json-key' (VS Code switch)
    """
    root = Path(root)
    mcp_path = root / ".mcp.json"
    mcp = json.loads(mcp_path.read_text(encoding="utf-8")) if mcp_path.is_file() else {}

    for name in harnesses:
        spec = table.get(name) or {}
        for surface in SURFACES:
            sspec = spec.get(surface) or {}
            if sspec.get("kind") != "generated":
                continue
            fmt = sspec.get("format")
            if fmt in COPILOT_FORMATS:
                mode = "json-key" if fmt == "vscode-claude-hooks" else "whole-file"
                for rel, text, _cls in materialize(root, sspec):
                    yield rel, text, mode, sspec
            elif surface == "mcp" and fmt == "copilot-mcp":
                yield sspec["path"], json.dumps(to_copilot_mcp(mcp), indent=2) + "\n", "whole-file", sspec
            elif surface == "mcp" and fmt == "toml-block":
                yield sspec["path"], to_codex_toml(mcp), "block", sspec


def check(root, table, harnesses) -> list[str]:
    root = Path(root)
    problems = []
    for rel, want, mode, sspec in derived_surfaces(root, table, harnesses):
        path = root / rel
        if mode == "json-key":
            state = vscode_hooks_state(path.read_text(encoding="utf-8") if path.is_file() else "")
            if state == "missing":
                problems.append(f'{rel} lacks "{VSCODE_HOOKS_KEY}": true')
            elif state == "unparseable":
                problems.append(f'{rel} is JSONC — set "{VSCODE_HOOKS_KEY}": true by hand')
            continue  # 'disabled' is an operator choice, not drift
        if not path.is_file():
            problems.append(f"{rel} is missing")
            continue
        have = path.read_text(encoding="utf-8")
        if mode == "whole-file" and have != want:
            problems.append(f"{rel} differs from its source")
        elif mode == "block":
            block = merge.extract_block(have)
            if block is None or want.strip() not in block:
                problems.append(f"{rel} block differs from .mcp.json")
    for rspec in _instruction_specs(table, harnesses):
        wanted = set(render_copilot_instructions(root, rspec))
        for orphan in orphan_instructions(root, rspec, wanted):
            problems.append(f"{orphan} is an orphan")
    return problems


def write(root, table, harnesses) -> list[str]:
    root = Path(root)
    written = []
    for rel, want, mode, sspec in derived_surfaces(root, table, harnesses):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        have = path.read_text(encoding="utf-8") if path.is_file() else ""
        out = merge.merge_toml_block(have, want) if mode == "block" else want
        if out != have:
            path.write_text(out, encoding="utf-8")
            written.append(rel)
    for rspec in _instruction_specs(table, harnesses):
        wanted = set(render_copilot_instructions(root, rspec))
        for orphan in orphan_instructions(root, rspec, wanted):
            (root / orphan).unlink()
            written.append(f"{orphan} (removed)")
    return written
```

(c) In `main()`, change the success line to:

```python
    print(f"harness surfaces match their sources ({len(harnesses)} harness(es))")
```
and the drift hint to:
```python
        print(f"\nRegenerate with: {REGENERATE}", file=sys.stderr)
```

Orphans are swept per harness `rules` spec, so deleting the last rule still removes its generated file (decided at the Task 7 checkpoint).

**Step 4: Run all harness tests**

Run:
```bash
python3 template/scripts/tests/test_harness_copilot.py
python3 scripts/install/tests/test_harness.py
```
Expected: both `OK`.

**Step 5: Commit**

```bash
git add template/scripts/harness/sync.py template/scripts/tests/test_harness_copilot.py
git commit -m "feat(harness): drift-check and regenerate Copilot surfaces"
```

---

### Task 8: Installer wires the Copilot surfaces

**Files:**
- Modify: `scripts/install/harness.py` (re-export `materialize`, `orphan_instructions`, `COPILOT_FORMATS`)
- Modify: `scripts/install/adopt.py` (`wire_harnesses` surface loop; `_generate`)
- Modify: `scripts/install/tests/test_adopt.py` (`test_codex_and_copilot_surfaces`, `test_check_write_roundtrip`)

**Step 1: Write the failing test.** In `scripts/install/tests/test_adopt.py`, append to the end of `test_codex_and_copilot_surfaces` (inside the `with` block):

```python
            # Copilot: generated brief carries the onboarding gate + hard constraints
            brief = (root / ".github/copilot-instructions.md").read_text()
            self.assertIn("## 0. Startup", brief)
            self.assertIn("## 3. Hard constraints", brief)
            # .claude/rules -> .github/instructions with applyTo
            adr = (root / ".github/instructions/adr-conventions.instructions.md").read_text()
            self.assertIn("applyTo: 'docs/architecture/decisions/**'", adr)
            # VS Code runs the kit's Claude hooks
            vs = json.loads((root / ".vscode/settings.json").read_text())
            self.assertIs(vs["chat.useClaudeHooks"], True)
```

and append to `test_check_write_roundtrip`, after the last assertion:

```python
            agents = Path(tmp) / "AGENTS.md"
            agents.write_text(agents.read_text() + "\n", encoding="utf-8")
            self.assertEqual(self.sync(tmp, "--check").returncode, 0,
                             "trailing newline outside §0/§3 must not drift")
            text = agents.read_text().replace("No fabrication", "No fabrication, ever")
            agents.write_text(text, encoding="utf-8")
            drifted = self.sync(tmp, "--check")
            self.assertEqual(drifted.returncode, 1)
            self.assertIn(".github/copilot-instructions.md", drifted.stderr)
```

**Step 2: Run to verify it fails**

Run: `python3 scripts/install/tests/test_adopt.py`
Expected: FAIL with `FileNotFoundError: … .github/copilot-instructions.md`.

**Step 3: Implement.**

(a) `scripts/install/harness.py`: extend the import list:

```python
from sync import (  # noqa: E402,F401
    COPILOT_FORMATS, POINTER_MD, POINTER_MDC, TABLE_REL,
    check, detect, load_table, materialize, mcp_servers, orphan_instructions,
    pointer_text, probe, to_codex_hooks, to_codex_toml, to_copilot_mcp, unconfigured,
)
```

(b) `scripts/install/adopt.py`, in `wire_harnesses`: change the loop header

```python
        for surface in ("brief", "skills", "mcp", "hooks"):
```
to
```python
        for surface in ("brief", "rules", "skills", "mcp", "hooks"):
```

(c) In `_generate`, add as the **first** statements of the function body:

```python
    if sspec.get("format") in harness.COPILOT_FORMATS:
        return _generate_copilot(root, sspec, surface, label, man, dry_run)
```

and add this function right after `_generate`:

```python
def _generate_copilot(root, sspec, surface, label, man, dry_run) -> str:
    """Write the Copilot surfaces sync.py renders. One generator, two callers."""
    classes = {"own": planner.CLASS_OWN, "merge": planner.CLASS_MERGE}
    try:
        files = harness.materialize(root, sspec)
    except ValueError as exc:          # e.g. AGENTS.md lacks a required section
        return f"{label}: {surface} -> {sspec['path']} FAILED ({exc})"
    changed = []
    for rel, text, cls in files:
        blob = text.encode("utf-8")
        if manifest.state(root, man, rel, blob) == manifest.IDENTICAL:
            continue
        if not dry_run:
            write_file(root, rel, blob)
            manifest.record(man, rel, classes[cls], blob)
        changed.append(rel)
    if sspec.get("format") == "copilot-instructions":
        for orphan in harness.orphan_instructions(root, sspec, {r for r, _, _ in files}):
            if not dry_run:
                (Path(root) / orphan).unlink()
            changed.append(f"{orphan} (removed)")
    if not changed:
        return f"{label}: {surface} -> {sspec['path']} (current)"
    return f"{label}: {surface} -> {', '.join(changed)} (generated)"
```

(d) Remove the now-wrong note: in `wire_harnesses`, the line

```python
        if spec.get("hooks") is None:
```
stays as is. Copilot's `hooks` is no longer `None`, so it no longer prints "no hook system".

**Step 4: Run to verify it passes**

Run:
```bash
python3 scripts/install/tests/test_adopt.py
python3 scripts/install/tests/test_harness.py
python3 template/scripts/tests/test_harness_copilot.py
```
Expected: all `OK`. The existing `test_second_run_changes_nothing` and `test_brownfield_rerun_is_idempotent` must also still pass, which proves the new surfaces are idempotent.

**Step 5: Commit**

```bash
git add scripts/install/harness.py scripts/install/adopt.py scripts/install/tests/test_adopt.py
git commit -m "feat(install): wire Copilot brief, path instructions and VS Code hooks"
```

---

### Task 9: Drift gate in pre-commit, CI and Jenkins

**Files:**
- Modify: `template/.pre-commit-config.yaml` (add a hook)
- Modify: `template/.github/workflows/ai-governance.yml` (add a step)
- Create: `template/ci/Jenkinsfile.ai-governance` (FRQ uses Jenkins)
- Modify: `.github/workflows/ci.yml` (kit CI runs the new unit tests)

**Step 1: pre-commit.** Add after the `validate-seat-profiles` hook in `template/.pre-commit-config.yaml`:

```yaml
      - id: harness-drift
        name: Harness surfaces match their sources (AGENTS.md, .claude/rules, .mcp.json)
        entry: python3 scripts/harness/sync.py --check
        language: system
        files: ^(AGENTS\.md|\.mcp\.json|\.claude/(rules/.*|settings\.json)|\.github/(copilot-instructions\.md|instructions/.*)|\.vscode/settings\.json|scripts/harness/.*)$
        pass_filenames: false
```

**Step 2: GitHub Actions (generated project).** In `template/.github/workflows/ai-governance.yml`, add after the seat-profiles validation step (match the file's existing indentation):

```yaml
      - name: Harness surfaces match their sources
        run: python3 scripts/harness/sync.py --check
```

Skip if the workflow already runs `sync.py --check` (it did; decided at the Task 9 checkpoint).

**Step 3: Jenkins (FRQ).** Create `template/ci/Jenkinsfile.ai-governance`:

```groovy
// AI-governance gate for Jenkins — governance validators + harness drift gate; see .github/workflows/ai-governance.yml for the full set.
// Use as a stage in your pipeline or as a standalone job on every PR.
// Requires python3 (3.10+) and pyyaml on the agent.
pipeline {
  agent any
  options { timeout(time: 10, unit: 'MINUTES') }
  stages {
    stage('AI governance') {
      steps {
        sh 'python3 -m pip install --quiet --user "pyyaml>=6"'
        sh 'python3 scripts/validate-skills.py'
        sh 'python3 scripts/validate-frontmatter.py'
        // Session manifests ship with the 'standard' profile; skip their validators when absent.
        sh '[ ! -f scripts/session/moments.json ] || python3 scripts/validate-moments.py'
        sh '[ ! -f scripts/session/seat-profiles.json ] || python3 scripts/validate-seat-profiles.py'
        sh 'python3 scripts/harness/sync.py --check'
      }
    }
  }
}
```

Then add `"ci/**"` to the `minimal` profile list in `scripts/install/file-classes.json`, right after `".github/workflows/ai-governance.yml"`.

**Step 4: Kit CI.** In `.github/workflows/ci.yml`, step "Installer unit tests (brownfield adoption)", add a line:

```yaml
          python3 template/scripts/tests/test_harness_copilot.py
```

**Step 5: Verify**

Run:
```bash
python3 scripts/install/tests/test_adopt.py
tmp=$(mktemp -d) && python3 scripts/install/adopt.py --into "$tmp" --profile minimal --yes --harness copilot-cli \
  && (cd "$tmp" && python3 scripts/harness/sync.py --check && test -f ci/Jenkinsfile.ai-governance && echo GATE-OK)
```
Expected: `OK`, then `harness surfaces match their sources (1 harness(es))` and `GATE-OK`.

**Step 6: Commit**

```bash
git add template/.pre-commit-config.yaml template/.github/workflows/ai-governance.yml \
        template/ci/Jenkinsfile.ai-governance scripts/install/file-classes.json .github/workflows/ci.yml
git commit -m "ci(governance): harness drift gate in pre-commit, Actions and Jenkins"
```

---

### Task 10: Brief and onboarding reflect Copilot

**Files:**
- Modify: `template/AGENTS.md` §4.1 (Copilot row only)
- Modify: `template/ONBOARDING.md` ("Notes for AI harnesses" section)

**Step 1: AGENTS.md §4.1.** Replace the Copilot row:

```markdown
| **GitHub Copilot** (IDE, chat) | All seats, in-flow | Honour this brief manually; point it here | In-document drafting; promote anything load-bearing into a governed file. |
```
with:
```markdown
| **GitHub Copilot** (CLI, VS Code, IntelliJ) | All seats | Yes — natively (CLI, VS Code); IntelliJ via the generated `.github/copilot-instructions.md` | Skills from `.claude/skills/`; rules via `.github/instructions/`; hooks via `.claude/settings.json` (CLI) and `chat.useClaudeHooks` (VS Code). Generated files: never edit, run `python3 scripts/harness/sync.py --write`. |
```
This edit is outside §0/§3, so the generated brief does not change. The brief-churn gate counts one commit.

**Step 2: ONBOARDING.md.** In "Notes for AI harnesses", add after the Claude Code bullet:

```markdown
- **GitHub Copilot** (CLI, VS Code, IntelliJ): interactive questions in chat, shell for commands, file-write for `USER.md`. Copilot CLI runs the SessionStart hook in interactive sessions; VS Code does when `chat.useClaudeHooks` is on (set by the installer). **IntelliJ has no session hooks** (and `copilot -p` skips them) **— run `bash scripts/session/start.sh` yourself** at the start of each session (the generated `.github/copilot-instructions.md` says so too).
```
This is the text committed in 503e0ea. It reflects Task 2's finding that `copilot -p` does not fire hooks.

**Step 3: Verify**

```bash
python3 template/scripts/check-brief-churn.py --path template/AGENTS.md
tmp=$(mktemp -d) && python3 scripts/install/adopt.py --into "$tmp" --profile minimal --yes --harness copilot-cli \
  && grep -c "GitHub Copilot" "$tmp/AGENTS.md"
```
Expected: churn below `--max` (exit 0), and a count ≥ 1.

**Step 4: Commit**

```bash
git add template/AGENTS.md template/ONBOARDING.md
git commit -m "docs(brief): Copilot reads the brief, rules and hooks via generated surfaces"
```

---

### Task 11: Versioning: changelog, bump and policy

`VERSION` (0.2.0) and the installer's `kit_version` record arrived with Task 1. This task adds the changelog and the policy the client will follow.

**Files:**
- Create: `CHANGELOG.md`
- Modify: `VERSION` → `0.3.0`
- Modify: `README.md` (add a "Versioning & upgrades" section)

**Step 1: Write `CHANGELOG.md`**

```markdown
# Changelog

All notable changes to the AI-SDLC Bootstrap Kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions: [SemVer](https://semver.org/).

**Version policy (for maintainers):**
- **MAJOR**: an adopting repo must act by hand on upgrade (renamed or removed seat, manifest schema change, removed extension point).
- **MINOR**: new seat, skill, harness, surface, catalogue entry or gate. Upgrades apply cleanly through `./install.sh --into <repo>`.
- **PATCH**: fixes and wording, with no change to generated surfaces.
- Every PR that changes `template/` adds a line under **Unreleased**. A release moves those lines under the new version and bumps `VERSION`.

## [Unreleased]

## [0.3.0] — 2026-10-07
### Added
- GitHub Copilot surfaces generated from the canonical sources: `.github/copilot-instructions.md` (AGENTS.md §0 + §3 inlined for IntelliJ), `.github/instructions/*.instructions.md` from `.claude/rules/*`, and `chat.useClaudeHooks` in `.vscode/settings.json`.
- Harness drift gate in pre-commit, GitHub Actions and Jenkins (`ci/Jenkinsfile.ai-governance`).
- `CHANGELOG.md` and the version policy above.

## [0.2.0] — 2026-08-28
### Added
- Brownfield installer (`install.sh`): idempotent adoption into existing repos, install manifest (`.ai-sdlc/manifest.json`) with upgrade states, `--dry-run`, `doctor`, uninstall.
- Data-driven harness adapter table and `scripts/harness/sync.py` (Claude Code, Codex CLI, Copilot CLI, Cursor, Gemini CLI, Windsurf, opencode).
```

**Step 2: Bump**

```bash
printf '0.3.0\n' > VERSION
```

**Step 3: README.** Add after the install section of `README.md`:

```markdown
## Versioning & upgrades

The kit is versioned with SemVer (`VERSION`, history in [`CHANGELOG.md`](./CHANGELOG.md)). The installer records the version in each adopting repo's `.ai-sdlc/manifest.json`, and `./install.sh doctor --into <repo>` shows it.

To upgrade a repo, run `./install.sh --into <repo> --dry-run` from the newer kit, review the plan, then run it without `--dry-run`. Files the kit owns and you never edited are replaced. Files you changed are flagged as conflicts: keep yours, take the kit's, or write the kit's copy alongside as `.kit-new` (press `d` to see the diff). With `--yes`, your version is kept. Nothing is overwritten silently.
```
This is the text committed in df5447e. Task H2 revises this paragraph again, because before H2 the "nothing is overwritten silently" promise did not hold for the generated Copilot files.

**Step 4: Verify the installer records the new version**

```bash
tmp=$(mktemp -d) && python3 scripts/install/adopt.py --into "$tmp" --profile minimal --yes --harness copilot-cli >/dev/null \
  && python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['kit_version'])" "$tmp/.ai-sdlc/manifest.json"
```
Expected: `0.3.0`.

**Step 5: Commit**

```bash
git add CHANGELOG.md VERSION README.md
git commit -m "chore(release): changelog, version policy, kit 0.3.0"
```

---

## Phase 0 hardening (from the Task 12 code review, 2026-10-07)

The Task 12 code review found five defects in the Copilot wiring, set out below as H1–H5. Do them in order: H4 relies on H3's error path.
Every task is test-first: write the failing test, watch it fail with the stated message, then add the minimal stdlib fix.
There is one commit per task, and a human reviews each commit before the next task starts.

The test counts before H1 are: `test_adopt` 20, `test_harness` 13, `test_harness_copilot` 16, `test_manifest` 9, `test_merge` 19, `test_plan` 11. Every task ends by running all six with this loop:

```bash
for t in scripts/install/tests/test_{adopt,harness,manifest,merge,plan}.py \
         template/scripts/tests/test_harness_copilot.py; do
  printf '%-48s ' "$t"; python3 "$t" 2>&1 | tail -3 | tr -s '\n' ' '; echo
done
```

---

### Task H1: `.vscode/settings.json` reaches git, and an ignored one is not drift

`template/.gitignore` ignores `.vscode/*` and re-includes only `extensions.json`. So the generated `.vscode/settings.json` is never committed, every clone lacks it, and `sync.py --check` fails in CI with `.vscode/settings.json lacks "chat.useClaudeHooks": true`. Two fixes are needed:

- The template re-includes the file.
- `check()` skips the VS Code switch when git ignores the file in this repo. A brownfield repo may keep `.vscode/` out of git on purpose, and once the manifest is committed CI checks copilot-cli anyway.

**Design choice: notes.** An ignored file produces no output at all, not even a stdout note. `check()` returns failures only. A non-failing note would need a second return channel through `check`, `main` and `doctor`, which is more surface than one skipped key is worth. The reason for the skip lives in a code comment.

**Known limitation (accepted).** If a developer ignores `.vscode/` only in their *global* git excludes, their clone treats the file as ignored, so they never commit it. A clean CI checkout has no such global rule, so the gate fails there. The fix is to remove the global rule or force-add the file.

**Files:**
- Modify: `template/.gitignore`
- Modify: `template/scripts/harness/sync.py` (`import subprocess`, new `_git_ignored`, `check`)
- Modify: `template/scripts/tests/test_harness_copilot.py` (imports, new `git` helper, new class `TestGitIgnoredSettings`)
- Modify: `scripts/install/tests/test_adopt.py` (`TestHarnessWiring.test_vscode_settings_is_committed`)

**Step 1: Write the failing tests.**

(a) In `template/scripts/tests/test_harness_copilot.py`, extend the imports to:

```python
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
```

then append before `if __name__`:

```python
def git(root, *args):
    """git with no user or system config, so a global excludesFile cannot skew the result."""
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                               "HOME": str(root), "GIT_CONFIG_NOSYSTEM": "1"})


@unittest.skipUnless(shutil.which("git"), "needs git")
class TestGitIgnoredSettings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = repo(self.tmp.name)
        self.table = sync.load_table()

    def tearDown(self):
        self.tmp.cleanup()

    def test_ignored_vscode_settings_is_not_drift(self):
        git(self.root, "init", "-q")
        (self.root / ".gitignore").write_text(".vscode/\n", encoding="utf-8")
        sync.write(self.root, self.table, ["copilot-cli"])
        (self.root / ".vscode/settings.json").unlink()      # what a fresh clone sees
        self.assertEqual([p for p in sync.check(self.root, self.table, ["copilot-cli"])
                          if "mcp" not in p], [])

    def test_outside_git_a_missing_switch_is_still_drift(self):
        sync.write(self.root, self.table, ["copilot-cli"])
        (self.root / ".vscode/settings.json").unlink()
        self.assertIn('.vscode/settings.json lacks "chat.useClaudeHooks": true',
                      sync.check(self.root, self.table, ["copilot-cli"]))
```

The second test passes before and after the fix. It is a guard: when there is no repo, or no git, the file counts as "not ignored".

(b) In `scripts/install/tests/test_adopt.py`, append to `class TestHarnessWiring`:

```python
    def test_vscode_settings_is_committed(self):
        with tempfile.TemporaryDirectory() as tmp:
            run("--into", tmp, "--profile", "minimal", "--yes", "--harness", "copilot-cli")
            env = {"PATH": "/usr/bin:/bin", "HOME": tmp, "GIT_CONFIG_NOSYSTEM": "1"}

            def git(*args):
                return subprocess.run(["git", *args], cwd=tmp, capture_output=True,
                                      text=True, env=env)

            git("init", "-q")
            git("add", "-A")
            self.assertIn(".vscode/settings.json", git("ls-files", ".vscode").stdout.split())
```

**Step 2: Run them to make sure they fail**

Run:
```bash
python3 template/scripts/tests/test_harness_copilot.py
python3 scripts/install/tests/test_adopt.py
```
Expected:
- `test_harness_copilot`: `Ran 18 tests`, `FAILED (failures=1)`, with `AssertionError: Lists differ: ['.vscode/settings.json lacks "chat.useClaudeHooks": true'] != []`.
- `test_adopt`: `Ran 21 tests`, `FAILED (failures=1)`, with `AssertionError: '.vscode/settings.json' not found in []`.

**Step 3: Implement.**

(a) `template/.gitignore`: after `!.vscode/extensions.json`, add:

```gitignore
!.vscode/settings.json
```

(b) `template/scripts/harness/sync.py`: add `import subprocess` after `import shutil`. Then add this after `vscode_hooks_state`:

```python
def _git_ignored(root, rel) -> bool:
    """True only when git says `rel` is ignored in this repo. No git, or no repo: False."""
    try:
        r = subprocess.run(["git", "check-ignore", "-q", rel], cwd=root,
                           capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0
```

`git check-ignore` exits 0 for ignored, 1 for not ignored, and 128 outside a repo. A file that is tracked is never reported as ignored, so a force-added `settings.json` is still checked.

(c) In `check()`, make the `json-key` branch start like this:

```python
        if mode == "json-key":
            if _git_ignored(root, rel):
                continue  # kept out of git on purpose: no clone has it, so nothing to gate
            state = vscode_hooks_state(path.read_text(encoding="utf-8") if path.is_file() else "")
```

`write()` is unchanged. It still sets the key locally, which helps the developer even when the file stays out of git.

**Step 4: Run the suites**

Run the loop from the top of this section.
Expected: `test_adopt` 21 OK · `test_harness` 13 OK · `test_manifest` 9 OK · `test_merge` 19 OK · `test_plan` 11 OK · `test_harness_copilot` 18 OK.

**Step 5: Commit**

```bash
git add template/.gitignore template/scripts/harness/sync.py \
        template/scripts/tests/test_harness_copilot.py scripts/install/tests/test_adopt.py
git commit -F - <<'EOF'
fix(harness): commit .vscode/settings.json; an ignored one is not drift

The template ignored .vscode/* except extensions.json, so the generated
settings.json never reached a clone and the drift gate failed in every CI
run. Re-include it, and skip the VS Code switch in check() when git
ignores the file (brownfield repos may keep .vscode/ out of git on purpose).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task H2: generated Copilot files never overwrite yours

`_generate_copilot` writes whenever `manifest.state` is not `IDENTICAL`. That includes `FOREIGN` (a `.github/copilot-instructions.md` the team wrote before adopting) and `MODIFIED` (a generated file someone edited). Both are overwritten silently, and once overwritten the file is recorded as kit-owned, so `uninstall` then deletes it.

The fix routes those two states through the planner's conflict contract: the same `Resolver`, the same `deferred` map, and the same `.kit-new` sidecar.

**Design choices:**
- **Same Resolver.** `wire_harnesses` takes the `Resolver` that `main()` already built for `apply()`. `--yes` gives keep, `--take-kit` gives take, and when there is no TTY the default is keep.
- **Keeping writes `.kit-new`.** `apply()` writes `.kit-new` only for `[m]`. Here, keeping (`[k]`, `[a]`, `--yes`, or no TTY) also writes the kit's copy to `<rel>.kit-new`, because a generated file has no template copy to diff against. Without the sidecar, the operator could not see what the kit wanted. The file is then recorded in `man["deferred"]` with the kit copy's hash, exactly as `apply()` does, and is not asked about again until that copy changes.
- **Uninstall needs no change.** `uninstall` deletes only paths listed in `man["files"]`. A kept file is never recorded there, so uninstall cannot delete it. The remaining uninstall gaps are listed under "Out of scope": *take* on a pre-existing file, MODIFIED own-class files, and `.kit-new` sidecars.
- **A kept file keeps failing the drift gate, with a message that says what to do.** `sync.py` reads `deferred` from `.ai-sdlc/manifest.json`, the same file `installed_harnesses` already reads, using stdlib only. `check` reports a deferred file that differs from its rendering as `<rel> is your file (kit copy in <rel>.kit-new) — merge it into its source, delete it, then run python3 scripts/harness/sync.py --write`. That line is still a failure.
- **`--write` never overwrites an existing deferred file.** It skips the file, reports the same line through a new `errors` list, and exits 1. If the operator has deleted the file, `--write` regenerates it. So the way out is:
  1. Fold what you need into `AGENTS.md` or `.claude/rules/`.
  2. Delete your file.
  3. Run `--write`.
  4. The next `install` sees the file is `IDENTICAL`, clears the deferral and records the file as kit-owned again.
- **Merge-class files are unchanged.** The merge-class `.vscode/settings.json` stays a key-union where operator values win. Keeping the operator's indent is not trivial (`merge_json` re-serialises), so it is left out of scope (see "Out of scope").
- **Dry runs ask too.** In `--dry-run` the Resolver is still asked, as `apply()` does, but nothing is written.

**Files:**
- Modify: `scripts/install/adopt.py` (`wire_harnesses`, `_generate`, `_generate_copilot`, `main`)
- Modify: `template/scripts/harness/sync.py` (new `_deferred`, `_kept`; `check`, `write`, `main`)
- Modify: `scripts/install/tests/test_adopt.py` (new class `TestCopilotConflicts`)
- Modify: `template/scripts/tests/test_harness_copilot.py` (new class `TestDeferred`)
- Modify: `README.md` (harness table, the paragraph under it, and the upgrade paragraph)

**Step 1: Write the failing tests.**

(a) In `template/scripts/tests/test_harness_copilot.py`, append before `if __name__`:

```python
class TestDeferred(unittest.TestCase):
    """A generated file the operator kept at install time is never overwritten by sync."""

    REL = ".github/copilot-instructions.md"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = repo(self.tmp.name)
        self.table = sync.load_table()
        (self.root / ".ai-sdlc").mkdir()
        (self.root / ".ai-sdlc/manifest.json").write_text(json.dumps(
            {"harnesses": ["copilot-cli"], "deferred": {self.REL: "0" * 64}}), encoding="utf-8")
        (self.root / ".github").mkdir()
        (self.root / self.REL).write_text("mine\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_check_says_how_to_hand_the_file_back(self):
        self.assertIn(f"{self.REL} is your file (kit copy in {self.REL}.kit-new) — merge it"
                      f" into its source, delete it, then run {sync.REGENERATE}",
                      sync.check(self.root, self.table, ["copilot-cli"]))

    def test_write_skips_a_kept_file_and_regenerates_a_deleted_one(self):
        errors = []
        self.assertNotIn(self.REL, sync.write(self.root, self.table, ["copilot-cli"], errors))
        self.assertEqual((self.root / self.REL).read_text(), "mine\n")
        self.assertEqual(len(errors), 1)
        (self.root / self.REL).unlink()                      # handed back to the kit
        self.assertIn(self.REL, sync.write(self.root, self.table, ["copilot-cli"], []))
```

(b) In `scripts/install/tests/test_adopt.py`, add this class before `class TestDoctorAndUninstall`:

```python
class TestCopilotConflicts(unittest.TestCase):
    """Generated Copilot files follow the planner's contract: yours are never overwritten."""

    HAND = "# Our Copilot rules\nWritten by the team before the kit.\n"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)
        (self.root / ".github").mkdir()
        (self.root / ".github/copilot-instructions.md").write_text(self.HAND, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def install(self):
        return run("--into", self.tmp, "--profile", "minimal", "--yes",
                   "--harness", "copilot-cli")

    def test_yes_keeps_a_hand_written_brief_and_writes_kit_new(self):
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.root / ".github/copilot-instructions.md").read_text(), self.HAND)
        self.assertIn("Generated by scripts/harness/sync.py",
                      (self.root / ".github/copilot-instructions.md.kit-new").read_text())
        man = manifest.load(self.tmp)
        self.assertIn(".github/copilot-instructions.md", man["deferred"])
        self.assertNotIn(".github/copilot-instructions.md", man["files"])

    def test_uninstall_leaves_a_hand_written_brief(self):
        self.install()
        run("--into", self.tmp, "uninstall")
        brief = self.root / ".github/copilot-instructions.md"
        self.assertTrue(brief.is_file())
        self.assertEqual(brief.read_text(), self.HAND)

    def test_reinstall_keeps_an_edited_instructions_file(self):
        self.install()
        adr = self.root / ".github/instructions/adr-conventions.instructions.md"
        edited = adr.read_text() + "\nTeam note: keep me.\n"
        adr.write_text(edited, encoding="utf-8")
        run("--into", self.tmp, "--yes")
        self.assertEqual(adr.read_text(), edited)
        self.assertTrue(adr.with_name(adr.name + ".kit-new").is_file())

    def test_matching_the_kit_copy_clears_the_deferral(self):
        self.install()
        brief = self.root / ".github/copilot-instructions.md"
        brief.write_text(brief.with_name(brief.name + ".kit-new").read_text(), encoding="utf-8")
        run("--into", self.tmp, "--yes")
        man = manifest.load(self.tmp)
        self.assertNotIn(".github/copilot-instructions.md", man["deferred"])
        self.assertIn(".github/copilot-instructions.md", man["files"])
```

**Step 2: Run to verify they fail**

Run:
```bash
python3 template/scripts/tests/test_harness_copilot.py
python3 scripts/install/tests/test_adopt.py
```
Expected:
- `test_harness_copilot`: `Ran 20 tests`, `FAILED (failures=1, errors=1)`. The check test fails with `AssertionError: '.github/copilot-instructions.md is your file […]' not found in ['.github/copilot-instructions.md differs from its source', …]`. The write test errors with `TypeError: write() takes 3 positional arguments but 4 were given`.
- `test_adopt`: `Ran 25 tests`, `FAILED (failures=3, errors=1)`:
  - `test_yes_keeps_…`: `AssertionError: '<!-- Generated by scripts/harness/sync.py from AGENTS.md […]' != '# Our Copilot rules\n[…]'`
  - `test_uninstall_…`: `AssertionError: False is not true`
  - `test_reinstall_…`: `AssertionError: '---\napplyTo: […]' != '---\napplyTo: […]Team note: keep me.\n'`
  - `test_matching_…`: `FileNotFoundError: […]copilot-instructions.md.kit-new` (before the fix, no sidecar is ever written)

**Step 3: Implement.** In `scripts/install/adopt.py`:

(a) Change the `wire_harnesses` signature, and the first line of its body after `root = Path(root)`:

```python
def wire_harnesses(root, names, table, man, dry_run=False, resolver=None) -> list[str]:
    """Write each harness's surface from the canonical artefacts."""
    root = Path(root)
    resolver = resolver or Resolver("keep")
```

and in the `kind == "generated"` branch, pass it on:

```python
                note = _generate(root, rel, sspec, mcp, settings, surface, label, man,
                                 dry_run, resolver)
```

(b) In `_generate`, change the signature and the Copilot hand-off:

```python
def _generate(root, rel, sspec, mcp, settings, surface, label, man, dry_run,
              resolver) -> str | None:
    if sspec.get("format") in harness.COPILOT_FORMATS:
        return _generate_copilot(root, sspec, surface, label, man, dry_run, resolver)
```

(c) Replace `_generate_copilot` entirely with:

```python
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
    except ValueError as exc:          # e.g. AGENTS.md lacks a required section
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
    if sspec.get("format") == "copilot-instructions":
        for orphan in harness.orphan_instructions(root, sspec, {r for r, _, _ in files}):
            if not dry_run:
                (Path(root) / orphan).unlink()
            changed.append(f"{orphan} (removed)")
    notes = []
    if changed:
        notes.append(f"{', '.join(changed)} (generated)")
    if kept:
        notes.append(f"{', '.join(kept)} (kept yours; kit's copy in .kit-new)")
    if not notes:
        return f"{label}: {surface} -> {sspec['path']} (current)"
    return f"{label}: {surface} -> {'; '.join(notes)}"
```

`Resolver.resolve(action, target_root, spec)` reads only `action.rel`, `.cls`, `.reason` and `.payload`, so a `planner.Action` built here is all it needs. `spec` is unused, so `None` is passed. `plan.build` checks for a deferral before it looks at the file's state. Here the order is reversed: `IDENTICAL` is checked first, because that is the moment a deferral ends.

(d) In `main()`, move `wire_harnesses` inside the `try`, so that `[q]` on a Copilot conflict aborts cleanly:

```python
    try:
        report = apply(root, actions, man, spec, resolver, dry_run=args.dry_run)
        notes = wire_harnesses(root, names, table, man, dry_run=args.dry_run,
                               resolver=resolver)
    except KeyboardInterrupt:
        print("\ninstall: aborted; nothing further written.")
        return 130

    print(f"\n{paint('Harness wiring', 'b')}")
```

(the old standalone `notes = wire_harnesses(...)` line goes away).

(e) `template/scripts/harness/sync.py`. Add these two helpers after `installed_harnesses`:

```python
def _deferred(root) -> dict:
    """Generated files the operator kept at install time (manifest `deferred`)."""
    man = Path(root) / ".ai-sdlc/manifest.json"
    try:
        data = json.loads(man.read_text(encoding="utf-8")) if man.is_file() else {}
    except (json.JSONDecodeError, OSError):
        return {}
    return (data.get("deferred") or {}) if isinstance(data, dict) else {}


def _kept(rel) -> str:
    return (f"{rel} is your file (kit copy in {rel}.kit-new) — merge it into its source, "
            f"delete it, then run {REGENERATE}")
```

`check` and `write` are defined above `installed_harnesses`. That is fine, because the helpers are only looked up at call time.

In `check`, add `deferred = _deferred(root)` after `root = Path(root)`, and change the whole-file comparison to:

```python
        if mode == "whole-file" and have != want:
            problems.append(_kept(rel) if rel in deferred else f"{rel} differs from its source")
```

Replace the head of `write` with the version below. The rest of the function is unchanged:

```python
def write(root, table, harnesses, errors: list | None = None) -> list[str]:
    root = Path(root)
    deferred = _deferred(root)
    written = []
    for rel, want, mode, sspec in derived_surfaces(root, table, harnesses):
        path = root / rel
        if rel in deferred and path.is_file() and path.read_text(encoding="utf-8") != want:
            if errors is not None:
                errors.append(_kept(rel))         # never overwrite a file you kept
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        ...                                       # unchanged
```

and replace the `--write` branch of `main` with:

```python
    if args.write:
        errors = []
        for rel in write(root, table, harnesses, errors):
            print(f"regenerated {rel}")
        for line in errors:
            print(f"not regenerated: {line}", file=sys.stderr)
        return 1 if errors else 0
```

(f) `README.md`, "One brief, every tool". Replace the table and the paragraph under it with:

```markdown
| | Claude Code | Codex CLI | GitHub Copilot (CLI · VS Code · IntelliJ) | Cursor · Gemini · Windsurf · opencode |
|---|---|---|---|---|
| Brief | `CLAUDE.md` pointer | reads `AGENTS.md` natively | reads `AGENTS.md` natively (CLI, VS Code); generated `.github/copilot-instructions.md` with §0 + §3 inlined (IntelliJ) | pointer files |
| Rules | `.claude/rules/` | — | generated `.github/instructions/*.instructions.md` (`paths:` → `applyTo:`) | — |
| Skills | `.claude/skills/` | symlinked | **reads `.claude/skills/` natively** | — |
| MCP | `.mcp.json` | generated TOML block | generated `.copilot/mcp-config.json` | merged |
| Hooks | `.claude/settings.json` | generated `.codex/hooks.json` | `.claude/settings.json` natively (CLI, interactive); `chat.useClaudeHooks` in `.vscode/settings.json` (VS Code); none in IntelliJ, where the brief says to run `scripts/session/start.sh` | — |

Because Copilot discovers `.claude/skills/` and both Codex and Copilot read `AGENTS.md` natively, three harnesses run off one brief and one skills tree. The only copies are Copilot's generated brief and path instructions; `sync.py --check` keeps them in step, and the installer never overwrites one you wrote or edited (see below).
```

and in "Versioning & upgrades", replace the second paragraph with:

```markdown
To upgrade a repo, run `./install.sh --into <repo> --dry-run` from the newer kit, review the plan, then run it without `--dry-run`. Files the kit owns and you never edited are replaced. Files you changed are flagged as conflicts: keep yours, take the kit's, or write the kit's copy alongside as `.kit-new` (press `d` to see the diff). With `--yes`, your version is kept. The generated Copilot files (`.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`) follow the same rule, including a file you had before adopting the kit. They have no template to compare against, so keeping yours always writes the kit's copy as `.kit-new`. The drift gate (`sync.py --check`) keeps failing on a kept file, and `--write` never overwrites it. To hand it back, fold what you need into its source (`AGENTS.md` or `.claude/rules/`), delete your file, and run `python3 scripts/harness/sync.py --write`. Nothing is overwritten silently.
```

**Step 4: Run the suites**

Run the loop from the top of this section.
Expected: `test_adopt` 25 OK · `test_harness` 13 OK · `test_manifest` 9 OK · `test_merge` 19 OK · `test_plan` 11 OK · `test_harness_copilot` 20 OK. The existing idempotency tests (`test_second_run_changes_nothing`, `test_brownfield_rerun_is_idempotent`) must still pass.

**Step 5: Commit**

```bash
git add scripts/install/adopt.py template/scripts/harness/sync.py README.md \
        scripts/install/tests/test_adopt.py template/scripts/tests/test_harness_copilot.py
git commit -F - <<'EOF'
fix(install): generated Copilot files never overwrite yours

A hand-written .github/copilot-instructions.md, or a generated file the
operator edited, was overwritten silently and then recorded as kit-owned,
so uninstall deleted it. Route FOREIGN/MODIFIED own-class files through the
Resolver: keeping yours writes .kit-new and defers, as the planner does.
sync.py reads the deferral: --check fails with the way out, --write never
overwrites a kept file, and matching the kit copy ends the deferral.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task H3: a missing AGENTS.md, or a missing §0/§3, is a problem line, not a crash

Two crashes, one in each caller:

- **Installer.** `adopt.py --into <empty> --dry-run --harness copilot-cli` dies with `FileNotFoundError: … AGENTS.md`. In a dry run, `apply()` writes nothing, so AGENTS.md is not on disk yet when `wire_harnesses` renders the brief. Only `ValueError` is caught.
- **Sync.** `sync.py --check` and `--write` raise `ValueError: AGENTS.md has no section(s): …` straight out of `derived_surfaces`. Brownfield repos keep their own AGENTS.md (it is a seed file), so this is the normal brownfield case.

**Design choices:**
- `derived_surfaces` yields a fourth mode, `"error"`, carrying one message per broken surface.
- `check` turns that into one problem line.
- `write` skips that surface but still writes all the others, and reports the error through the optional `errors` list that H2 added. This is the same idiom as `mcp_servers(mcp, skipped)`. `main --write` already prints those errors and exits 1.
- The orphan sweep never runs when the rules render fails, so the sweep never runs without a list of wanted files.
- `render_copilot_brief` raises `ValueError("AGENTS.md is missing")` itself, so that the problem line does not carry an absolute path.

**Files:**
- Modify: `template/scripts/harness/sync.py` (`render_copilot_brief`, `derived_surfaces`, `check`, `write`)
- Modify: `scripts/install/adopt.py` (`_generate_copilot`'s `except`)
- Modify: `template/scripts/tests/test_harness_copilot.py` (imports, new class `TestRenderErrors`)
- Modify: `scripts/install/tests/test_adopt.py` (`TestGreenfield.test_dry_run_into_an_empty_dir_wires_copilot`)

**Step 1: Write the failing tests.**

(a) In `template/scripts/tests/test_harness_copilot.py`, add `import contextlib` and `import io` to the imports (the list stays alphabetical). Then append before `if __name__`:

```python
NO_STARTUP = AGENTS.replace("## 0. Startup", "## 9. Startup")


class TestRenderErrors(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = repo(self.tmp.name, NO_STARTUP)
        self.table = sync.load_table()

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_section_is_one_problem_line(self):
        problems = sync.check(self.root, self.table, ["copilot-cli"])
        self.assertIn(".github/copilot-instructions.md: AGENTS.md has no section(s): 0"
                      " — fix the source or remove copilot-cli", problems)

    def test_write_skips_the_broken_surface_and_writes_the_rest(self):
        errors = []
        written = sync.write(self.root, self.table, ["copilot-cli"], errors)
        self.assertIn(".vscode/settings.json", written)
        self.assertIn(".copilot/mcp-config.json", written)
        self.assertFalse((self.root / ".github/copilot-instructions.md").exists())
        self.assertEqual(len(errors), 1)
        (self.root / ".ai-sdlc").mkdir()
        (self.root / ".ai-sdlc/manifest.json").write_text(
            '{"harnesses": ["copilot-cli"]}', encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(sync.main(["--root", str(self.root), "--write"]), 1)
```

(b) In `scripts/install/tests/test_adopt.py`, append to `class TestGreenfield`:

```python
    def test_dry_run_into_an_empty_dir_wires_copilot(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run("--into", tmp, "--dry-run", "--harness", "copilot-cli")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("would generate after AGENTS.md is installed", r.stdout)
```

**Step 2: Run to verify they fail**

Run:
```bash
python3 template/scripts/tests/test_harness_copilot.py
python3 scripts/install/tests/test_adopt.py
```
Expected:
- `test_harness_copilot`: `Ran 22 tests`, `FAILED (errors=2)`. Both errors are `ValueError: AGENTS.md has no section(s): 0`, raised from `derived_surfaces`.
- `test_adopt`: `Ran 26 tests`, `FAILED (failures=1)`, with `AssertionError: 1 != 0 : Traceback […] FileNotFoundError: [Errno 2] No such file or directory: '…/AGENTS.md'`.

**Step 3: Implement.**

(a) `sync.py`, `render_copilot_brief`: replace its first line with:

```python
def render_copilot_brief(root, spec: dict) -> str:
    path = Path(root) / "AGENTS.md"
    if not path.is_file():
        raise ValueError("AGENTS.md is missing")
    agents = path.read_text(encoding="utf-8")
```

(b) `derived_surfaces`: add `| 'error' (render failed; want_text is the message)` to the docstring's mode line. Then replace the `if fmt in COPILOT_FORMATS:` branch with:

```python
            if fmt in COPILOT_FORMATS:
                mode = "json-key" if fmt == "vscode-claude-hooks" else "whole-file"
                try:
                    files = materialize(root, sspec)
                except (ValueError, OSError) as exc:
                    yield (sspec["path"], f"{exc} — fix the source or remove {name}",
                           "error", sspec)
                    continue
                for rel, text, _cls in files:
                    yield rel, text, mode, sspec
```

(c) `check`: make the loop body start with:

```python
        if mode == "error":
            problems.append(f"{rel}: {want}")
            continue
```

and guard the orphan loop at the end:

```python
    for rspec in _instruction_specs(table, harnesses):
        try:
            wanted = set(render_copilot_instructions(root, rspec))
        except (ValueError, OSError):
            continue  # already one problem line; never sweep without the wanted list
        for orphan in orphan_instructions(root, rspec, wanted):
            problems.append(f"{orphan} is an orphan")
```

(d) `write`: H2 already gave it the `errors` list. Add the error branch as the first statement of the loop body, before H2's deferred skip, and guard the orphan loop in the same way:

```python
def write(root, table, harnesses, errors: list | None = None) -> list[str]:
    root = Path(root)
    deferred = _deferred(root)
    written = []
    for rel, want, mode, sspec in derived_surfaces(root, table, harnesses):
        if mode == "error":
            if errors is not None:
                errors.append(f"{rel}: {want}")
            continue
        path = root / rel
        ...                                   # unchanged (H2's deferred skip, then the write)
    for rspec in _instruction_specs(table, harnesses):
        try:
            wanted = set(render_copilot_instructions(root, rspec))
        except (ValueError, OSError):
            continue
        for orphan in orphan_instructions(root, rspec, wanted):
            (root / orphan).unlink()
            written.append(f"{orphan} (removed)")
    return written
```

(e) `main` needs no change. H2's `--write` branch already prints each entry of `errors` as `not regenerated: …` and exits 1.

(f) `scripts/install/adopt.py`, `_generate_copilot`: replace the `except` clause with:

```python
    except (ValueError, OSError) as exc:   # AGENTS.md missing or lacks a section; bad rule
        if dry_run and not (Path(root) / "AGENTS.md").is_file():
            return (f"{label}: {surface} -> {sspec['path']} "
                    f"(would generate after AGENTS.md is installed)")
        return f"{label}: {surface} -> {sspec['path']} FAILED ({exc})"
```

**Step 4: Run the suites**

Run the loop from the top of this section.
Expected: `test_adopt` 26 OK · `test_harness` 13 OK · `test_manifest` 9 OK · `test_merge` 19 OK · `test_plan` 11 OK · `test_harness_copilot` 22 OK.

**Known limitation (accepted).** In a `--dry-run` into an empty dir, the rules surface reports `(current)`, because `.claude/rules/` is not on disk yet and there is nothing to render. The real run generates the files.

**Step 5: Commit**

```bash
git add template/scripts/harness/sync.py scripts/install/adopt.py \
        template/scripts/tests/test_harness_copilot.py scripts/install/tests/test_adopt.py
git commit -F - <<'EOF'
fix(harness): a missing AGENTS.md section is a problem line, not a crash

sync.py --check/--write raised out of derived_surfaces when AGENTS.md lacked
§0/§3 (the normal brownfield case), and a --dry-run into an empty dir died
on the not-yet-installed AGENTS.md. Render errors are now one problem line;
--write skips that surface, writes the rest, and exits 1.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task H4: safer orphan sweep and rule parsing

The review found four smaller defects:

- **Orphan sweep.** `orphan_instructions` counts a file as generated if `GENERATED_MARK` appears anywhere in it. A copied or renamed generated file, or a notes file that quotes the mark, is therefore deleted.
- **Stale manifest entries.** The installer deletes orphans but leaves their manifest entries. If the operator later creates a file at that path, it reads as `MODIFIED`, not `FOREIGN`, and `uninstall` deletes it.
- **Rule parsing.** `_rule_paths` only reads an indented block list. Unindented lists, flow lists, a scalar, and comments silently become `applyTo: '**'`, which applies the rule everywhere.
- **Non-object settings.** `vscode_hooks_state('1')` raises `TypeError`.

**Design choices:**
- A file is generated only if its first body line, after the frontmatter, is the header that names *its own* source: `<!-- Generated … from {src_rel}/{stem}.md — do not edit.`. One helper, `_instruction_header`, both writes and checks this header, so the rendered bytes do not change.
- `manifest.forget` already exists (`manifest.py`), so no new function is needed.
- **The installer's sweep keeps an orphan you edited.** If `manifest.state` is `MODIFIED` (the recorded hash differs from the disk), the file is reported as kept, not deleted. Deleting a rule does not delete your edits. `sync.py --write` has no state per file, so its sweep still relies on the header alone. That gap is listed under "Out of scope".
- `_rule_paths(front, rule)` raises a `ValueError` that names the rule in two cases: `paths:` is present but yields nothing, or a brace glob holds a comma. Copilot's `applyTo` is itself comma-separated, so `*.{ts,tsx}` would split in two. Through H3, either error becomes one problem line in `check` and a `FAILED` note in the installer.

**Files:**
- Modify: `template/scripts/harness/sync.py` (`_rule_paths` and helpers, `_instruction_header`, `render_copilot_instructions`, `orphan_instructions`, `vscode_hooks_state`)
- Modify: `scripts/install/adopt.py` (`_generate_copilot` orphan loop)
- Modify: `template/scripts/tests/test_harness_copilot.py` (one fixture, a new `apply_to` helper, seven tests)
- Modify: `scripts/install/tests/test_adopt.py` (`TestHarnessWiring.test_removed_orphan_is_forgotten`, `TestHarnessWiring.test_edited_orphan_is_kept`)

**Step 1: Write the failing tests.** All of these go in `template/scripts/tests/test_harness_copilot.py` except (f).

(a) The existing fixture in `test_orphans_are_only_our_generated_files` writes a bare mark. That stops counting as generated, so give it the real header. Replace

```python
            (out_dir / "gone.instructions.md").write_text(
                f"<!-- {sync.GENERATED_MARK} -->\n", encoding="utf-8")
```
with
```python
            (out_dir / "gone.instructions.md").write_text(
                f"---\napplyTo: '**'\n---\n<!-- {sync.GENERATED_MARK} from "
                ".claude/rules/gone.md — do not edit. -->\n", encoding="utf-8")
```

(b) Add after the `rules` helper:

```python
def apply_to(front):
    """The applyTo line generated for a rule with this frontmatter."""
    with tempfile.TemporaryDirectory() as tmp:
        root = rules(tmp, {"r.md": f"---\n{front}---\n# R\n"})
        text = sync.render_copilot_instructions(root, RULES_SPEC)[
            ".github/instructions/r.instructions.md"]
        return text.splitlines()[1]
```

(c) Append to `class TestInstructions`:

```python
    def test_a_copied_generated_file_is_not_an_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = rules(tmp, {"a.md": "# A\n"})
            wanted = sync.render_copilot_instructions(root, RULES_SPEC)
            out_dir = root / ".github/instructions"
            out_dir.mkdir(parents=True)
            (out_dir / "mine.instructions.md").write_text(       # copied to start my own
                wanted[".github/instructions/a.instructions.md"], encoding="utf-8")
            self.assertEqual(sync.orphan_instructions(root, RULES_SPEC, wanted), [])

    def test_a_note_quoting_the_mark_is_not_an_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = rules(tmp, {"a.md": "# A\n"})
            out_dir = root / ".github/instructions"
            out_dir.mkdir(parents=True)
            (out_dir / "notes.instructions.md").write_text(
                "---\napplyTo: '**'\n---\n# Notes\nGenerated files start with "
                f"`<!-- {sync.GENERATED_MARK} from .claude/rules/notes.md — do not edit.`\n",
                encoding="utf-8")
            wanted = sync.render_copilot_instructions(root, RULES_SPEC)
            self.assertEqual(sync.orphan_instructions(root, RULES_SPEC, wanted), [])

    def test_paths_accepts_the_yaml_shapes_rules_use(self):
        cases = {
            'paths:\n- "a/**"\n- b/**\n': "applyTo: 'a/**,b/**'",            # unindented
            'paths: ["a/**", \'b/**\']\n': "applyTo: 'a/**,b/**'",           # flow list
            "paths: a/**\n": "applyTo: 'a/**'",                               # scalar
            '# scope\npaths:\n  # docs first\n  - "a/**"  # ADRs\n  - b/**\n':
                "applyTo: 'a/**,b/**'",                                       # comments
        }
        for front, want in cases.items():
            with self.subTest(front=front):
                self.assertEqual(apply_to(front), want)

    def test_empty_paths_is_an_error_naming_the_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = rules(tmp, {"r.md": "---\npaths:\n---\n# R\n"})
            with self.assertRaises(ValueError) as ctx:
                sync.render_copilot_instructions(root, RULES_SPEC)
            self.assertIn(".claude/rules/r.md", str(ctx.exception))

    def test_brace_glob_with_a_comma_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = rules(tmp, {"r.md": '---\npaths:\n  - "src/**/*.{ts,tsx}"\n---\n# R\n'})
            with self.assertRaises(ValueError) as ctx:
                sync.render_copilot_instructions(root, RULES_SPEC)
            self.assertIn("expand brace globs into separate paths", str(ctx.exception))
```

(d) Append to `class TestVscode`:

```python
    def test_non_object_settings_are_unparseable(self):
        for text in ("1", "[]", '"x"'):
            with self.subTest(text=text):
                self.assertEqual(sync.vscode_hooks_state(text), "unparseable")
```

(e) Append to `class TestCheckWrite`:

```python
    def test_a_rule_with_empty_paths_is_one_problem_line(self):
        (self.root / ".claude/rules/bad.md").write_text("---\npaths:\n---\n# Bad\n",
                                                        encoding="utf-8")
        self.assertIn(".github/instructions: .claude/rules/bad.md: paths: is present but"
                      " lists no paths — fix the source or remove copilot-cli",
                      sync.check(self.root, self.table, ["copilot-cli"]))
```

That is 7 new tests in this file: 5 from (c), 1 from (d) and 1 from (e). So 22 becomes 29.

(f) In `scripts/install/tests/test_adopt.py`, append to `class TestHarnessWiring`. It uses an operator rule: a deleted *template* rule would just be re-created by the planner.

```python
    def test_removed_orphan_is_forgotten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude/rules").mkdir(parents=True)
            (root / ".claude/rules/local.md").write_text("# Local rule\n", encoding="utf-8")
            run("--into", tmp, "--profile", "minimal", "--yes", "--harness", "copilot-cli")
            rel = ".github/instructions/local.instructions.md"
            self.assertIn(rel, manifest.load(tmp)["files"])
            (root / ".claude/rules/local.md").unlink()
            run("--into", tmp, "--yes")
            self.assertFalse((root / rel).exists())
            self.assertNotIn(rel, manifest.load(tmp)["files"])

    def test_edited_orphan_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude/rules").mkdir(parents=True)
            (root / ".claude/rules/local.md").write_text("# Local rule\n", encoding="utf-8")
            run("--into", tmp, "--profile", "minimal", "--yes", "--harness", "copilot-cli")
            gen = root / ".github/instructions/local.instructions.md"
            gen.write_text(gen.read_text() + "\nTeam note: keep me.\n", encoding="utf-8")
            (root / ".claude/rules/local.md").unlink()
            run("--into", tmp, "--yes")
            self.assertIn("Team note: keep me.", gen.read_text())
```

**Step 2: Run to verify they fail**

Run:
```bash
python3 template/scripts/tests/test_harness_copilot.py
python3 scripts/install/tests/test_adopt.py
```
Expected:
- `test_harness_copilot`: `Ran 29 tests`, `FAILED (failures=11, errors=1)`. The edited fixture (a) still passes. The failures:
  - both orphan tests, each with `AssertionError: Lists differ: ['.github/instructions/mine.instructions.md'] != []` (or `notes…`);
  - all 4 YAML subtests, each with `AssertionError: "applyTo: '**'" != "applyTo: 'a/**,b/**'"` (or `'a/**'`);
  - the `"[]"` and `'"x"'` subtests, each with `AssertionError: 'missing' != 'unparseable'`;
  - `AssertionError: ValueError not raised`, twice;
  - the problem-line test's `AssertionError: '.github/instructions: …' not found in […]`.

  The one error is the `"1"` subtest: `TypeError: argument of type 'int' is not iterable`.
- `test_adopt`: `Ran 28 tests`, `FAILED (failures=1, errors=1)`:
  - the forgotten-orphan test fails with `AssertionError: '.github/instructions/local.instructions.md' unexpectedly found in {…}`;
  - the edited-orphan test errors with `FileNotFoundError: […]local.instructions.md`, because the sweep deleted the edited file.

**Step 3: Implement.** In `template/scripts/harness/sync.py`:

(a) Replace `_rule_paths` with:

```python
_COMMENT = re.compile(r"(?:^|\s+)#.*$")
_BRACE_LIST = re.compile(r"\{[^{}]*,[^{}]*\}")


def _unquote(item: str) -> str:
    item = item.strip()
    if len(item) >= 2 and item[0] == item[-1] and item[0] in "\"'":
        return item[1:-1]
    return item


def _rule_paths(front: str, rule: str) -> list[str]:
    """The `paths:` of a .claude/rules frontmatter (the only key the rules use).

    Accepts a block list (indented or not), a one-line flow list, or one scalar,
    with `#` comments. Raises ValueError naming `rule` when `paths:` is present but
    yields nothing, or when a brace glob holds a comma: Copilot's applyTo is itself
    comma-separated, so `*.{ts,tsx}` would be split in two.
    """
    out, inside, present = [], False, False
    for raw in front.splitlines():
        line = _COMMENT.sub("", raw).rstrip()
        m = re.match(r"^paths:\s*(.*)$", line)
        if m:
            present, value = True, m.group(1)
            inside = not value
        elif inside and re.match(r"^\s*-\s", line):
            value = line.split("-", 1)[1]
        else:
            inside = inside and not line      # blank and comment lines keep the list open
            continue
        if _BRACE_LIST.search(value):
            raise ValueError(f"{rule}: {value.strip()} — applyTo is comma-separated; "
                             "expand brace globs into separate paths")
        if value.startswith("[") and value.endswith("]"):
            out += [_unquote(v) for v in value[1:-1].split(",") if v.strip()]
        elif value.strip():
            out.append(_unquote(value))
    if present and not out:
        raise ValueError(f"{rule}: paths: is present but lists no paths")
    return out
```

(b) Add `_instruction_header`, and use it in `render_copilot_instructions`, which now also passes the rule's name. The rendered bytes do not change:

```python
def _instruction_header(src_rel: str, stem: str) -> str:
    """First body line of a generated instruction file. It names its own source rule."""
    return f"<!-- {GENERATED_MARK} from {src_rel}/{stem}.md — do not edit."


def render_copilot_instructions(root, spec: dict) -> dict:
    """{repo-relative path: text} — one .instructions.md per .claude/rules/*.md."""
    src_rel = spec.get("from", ".claude/rules")
    src = Path(root) / src_rel
    files = {}
    for rule in sorted(src.glob("*.md")) if src.is_dir() else []:
        front, body = _split_frontmatter(rule.read_text(encoding="utf-8"))
        apply_to = ",".join(_rule_paths(front, f"{src_rel}/{rule.name}")) or "**"
        rel = f"{spec['path']}/{rule.stem}.instructions.md"
        files[rel] = (f"---\napplyTo: '{apply_to}'\n---\n"
                      f"{_instruction_header(src_rel, rule.stem)} "
                      f"Regenerate: {REGENERATE} -->\n\n{body}")
    return files
```

(c) Replace `orphan_instructions` with:

```python
def orphan_instructions(root, spec: dict, wanted: dict) -> list[str]:
    """Generated instruction files whose source rule was deleted.

    A file counts as ours only if its first body line is the header naming its own
    source (`<stem>.instructions.md` <- `<from>/<stem>.md`). A copied or renamed
    file, or a note that quotes the mark, is never touched.
    """
    out_dir = Path(root) / spec["path"]
    if not out_dir.is_dir():
        return []
    src_rel = spec.get("from", ".claude/rules")
    orphans = []
    for p in sorted(out_dir.glob("*.instructions.md")):
        rel = f"{spec['path']}/{p.name}"
        if rel in wanted:
            continue
        stem = p.name[: -len(".instructions.md")]
        body = _split_frontmatter(p.read_text(encoding="utf-8"))[1]
        if body.startswith(_instruction_header(src_rel, stem)):
            orphans.append(rel)
    return orphans
```

(d) In `vscode_hooks_state`, after the `try/except`, add:

```python
    if not isinstance(data, dict):
        return "unparseable"
```

(e) `scripts/install/adopt.py`, `_generate_copilot`. Replace the orphan loop, and the notes after it, with:

```python
    edited = []
    if sspec.get("format") == "copilot-instructions":
        for orphan in harness.orphan_instructions(root, sspec, {r for r, _, _ in files}):
            if manifest.state(root, man, orphan) == manifest.MODIFIED:
                edited.append(orphan)          # its rule is gone, your edits are not
                continue
            if not dry_run:
                (Path(root) / orphan).unlink()
                manifest.forget(man, orphan)
            changed.append(f"{orphan} (removed)")
    notes = []
    if changed:
        notes.append(f"{', '.join(changed)} (generated)")
    if kept:
        notes.append(f"{', '.join(kept)} (kept yours; kit's copy in .kit-new)")
    if edited:
        notes.append(f"{', '.join(edited)} (source rule deleted; kept your edits — "
                     f"delete by hand if unwanted)")
```

The `if not notes:` lines and the final `return` stay as H2 left them. `manifest.state(root, man, rel)` with no kit bytes returns `CLEAN` if the disk matches the recorded hash and `MODIFIED` if it does not. A file that was never recorded returns `FOREIGN`; its header already proves it was generated, so it is still removed.

**Step 4: Run the suites**

Run the loop from the top of this section.
Expected: `test_adopt` 28 OK · `test_harness` 13 OK · `test_manifest` 9 OK · `test_merge` 19 OK · `test_plan` 11 OK · `test_harness_copilot` 29 OK. The existing `test_paths_become_apply_to` and `test_codex_and_copilot_surfaces` (`applyTo: 'docs/architecture/decisions/**'`) still pass, so the shipped rules' indented, quoted lists render as before.

**Step 5: Commit**

```bash
git add template/scripts/harness/sync.py scripts/install/adopt.py \
        template/scripts/tests/test_harness_copilot.py scripts/install/tests/test_adopt.py
git commit -F - <<'EOF'
fix(harness): orphan sweep checks the source header; rules parse all list shapes

The orphan sweep deleted any *.instructions.md that merely contained the
generated mark (copies, renames, notes quoting it); it now requires the
header naming its own source rule. The installer forgets what it removes
and keeps an orphan the operator edited. paths: accepts block, flow and scalar forms with comments; an
empty paths: or a comma brace glob is a named error, not applyTo '**'.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task H5: `doctor` reports drift for every generated surface

`doctor`'s "Generated-surface drift" section calls `check_drift`, which only compares the two MCP formats against `.mcp.json`. Drift in the Copilot brief, the path instructions or the VS Code switch passes `doctor` but fails CI.

**Design choice:** `check_drift` becomes a thin wrapper over `harness.check(root, table, man["harnesses"])`, the function that `sync.py --check` and the CI gate already run. The MCP-only body is redundant and goes: `sync.check` does the same `copilot-mcp` whole-file and `toml-block` comparisons. The output format is unchanged (`none` / `drift <line>`, with one problem counted per line). The one behaviour that `check` lacks is surviving an invalid `.mcp.json` (`derived_surfaces` would raise), so the wrapper keeps that line. One difference to note: with `.mcp.json` deleted, the old check reported nothing, while `check` reports an MCP file that still lists servers. That matches what CI already says.

**Files:**
- Modify: `scripts/install/adopt.py` (`check_drift`, one `doctor` line)
- Modify: `scripts/install/tests/test_adopt.py` (`TestDoctorAndUninstall.test_doctor_flags_copilot_brief_drift`)

**Step 1: Write the failing test.** Append to `class TestDoctorAndUninstall`:

```python
    def test_doctor_flags_copilot_brief_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            run("--into", tmp, "--profile", "minimal", "--yes", "--harness", "copilot-cli")
            agents = Path(tmp) / "AGENTS.md"
            agents.write_text(agents.read_text().replace("No fabrication", "No fabrication, ever"),
                              encoding="utf-8")
            out = run("--into", tmp, "doctor")
            self.assertIn("drift .github/copilot-instructions.md differs from its source",
                          out.stdout)
            self.assertEqual(out.returncode, 1)
```

**Step 2: Run to verify it fails**

Run: `python3 scripts/install/tests/test_adopt.py`
Expected: `Ran 29 tests`, `FAILED (failures=1)`, with `AssertionError: 'drift .github/copilot-instructions.md differs from its source' not found in 'AI-SDLC doctor — …'`.

**Step 3: Implement.** In `scripts/install/adopt.py`:

(a) Replace `check_drift` entirely with:

```python
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
```

(b) In `doctor`, change the "no drift" line to:

```python
        print(f"  {paint('none', 'g')} — derived harness files match their sources")
```

**Step 4: Run the suites**

Run the loop from the top of this section.
Expected: `test_adopt` 29 OK · `test_harness` 13 OK · `test_manifest` 9 OK · `test_merge` 19 OK · `test_plan` 11 OK · `test_harness_copilot` 29 OK. The existing `test_doctor_flags_drift` (an emptied `.copilot/mcp-config.json`) still passes, now through `sync.check`.

**Step 5: Commit**

```bash
git add scripts/install/adopt.py scripts/install/tests/test_adopt.py
git commit -F - <<'EOF'
fix(install): doctor reports drift for every generated surface

doctor's drift section only compared the MCP files with .mcp.json, so a
stale Copilot brief, path instruction or VS Code switch passed doctor and
failed CI. check_drift now wraps harness.check, the same check sync.py
--check and the CI gate run.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 12: Full verification and phase close-out

**Step 1: Run the whole kit CI locally**, copying every `run:` line from `.github/workflows/ci.yml`:

```bash
pip install --quiet "pyyaml>=6"
grep -E '^\s+(run: )?python3 ' .github/workflows/ci.yml | sed -E 's/^ *(run: )?//' > /tmp/ci-cmds.sh
wc -l < /tmp/ci-cmds.sh
bash -e /tmp/ci-cmds.sh && echo ALL-GREEN
```
Expected: `40`, then `ALL-GREEN`. The pattern catches both the one-line `run: python3 …` steps and the lines inside multi-line `run: |` blocks, including the knowledge-graph smoke pipes at the end of the file. The old pattern (`^\s+python3 `) found only 31 commands. The count was verified at df5447e; if `ci.yml` has gained steps since, the count grows to match.

**Step 2: End-to-end on a real FRQ-shaped repo (human-observed).** On the VM, in a scratch clone of an existing FRQ repo:

```bash
./install.sh --into ~/scratch/frq-repo --profile standard --harness copilot-cli --dry-run   # review
./install.sh --into ~/scratch/frq-repo --profile standard --harness copilot-cli
cd ~/scratch/frq-repo && python3 scripts/harness/sync.py --check && copilot
```
Expected: dry-run shows a plan without conflicts on the client's own files, `--check` passes, and Copilot CLI starts onboarding because `USER.md` is missing (design §4.0 step 2).

Then prove the gate passes on a **clean checkout**, which is what CI sees. This verifies H1: before H1, `.vscode/settings.json` was gitignored, so it never reached a clone and the gate failed on every one.

```bash
cd ~/scratch/frq-repo && git add -A && git commit -qm "chore: adopt AI-SDLC kit (scratch)"
git ls-files .vscode/settings.json
rm -rf ~/scratch/frq-repo-clean && git clone -q ~/scratch/frq-repo ~/scratch/frq-repo-clean
cd ~/scratch/frq-repo-clean && python3 scripts/harness/sync.py --check
```
Expected: `git ls-files` prints `.vscode/settings.json` (it is committed, not ignored), and `--check` passes in the clone. Then the human pushes the scratch repo to a throwaway remote branch, so that the Jenkins job (`ci/Jenkinsfile.ai-governance`) or the Actions workflow (`ai-governance.yml`) runs on a checkout it made itself. The `sync.py --check` stage must be green. If no throwaway remote is available, run the Jenkinsfile's `sh` steps by hand in `~/scratch/frq-repo-clean` instead, and say so in the record.

**VM checks 3–5 from Task 2 (deferred to here).** Task 2 recorded them as ⏸. Run them now in the `~/copilot-spike` repo from Task 2 Step 1, with the same "Pass when" column:

| # | Check | How | Pass when |
|---|---|---|---|
| 3 | VS Code Chat runs Claude hooks with `chat.useClaudeHooks` | `rm -f /tmp/spike-hook.log`, open the folder in VS Code, start a Copilot Chat | `/tmp/spike-hook.log` contains `HOOK-OK` |
| 4 | IntelliJ Chat reads `.github/copilot-instructions.md` | open in IntelliJ, ask anything | the answer ends `BRIEF-OK` |
| 5 | IntelliJ Chat applies `.github/instructions` `applyTo` | ask about a file under `docs/` | the answer ends `RULE-OK` |

Update the "Verified on the FRQ VM" line in §3.6 of the design note: replace the ⏸ marks, and add the IntelliJ and plugin versions. If 3 fails, apply Task 2 Step 3's "3 fails" fallback. If 4 or 5 fails, stop and escalate, as Task 2 Step 3 says.

**Step 3: Record the outcome.** In `docs/roadmap/2026-10-07-onboarding-roles-and-skills-design.md` §6, change the Phase 0 row to start with `✅ 0. Foundations (done <date>, kit 0.3.0)`.

**Step 4: Commit and hand back**

```bash
git add docs/roadmap/2026-10-07-onboarding-roles-and-skills-design.md
git commit -m "docs(roadmap): Phase 0 foundations complete"
```
Then use superpowers:requesting-code-review on the Phase 0 range, and stop for the human's go-ahead on Phase 1.

---

## Out of scope for Phase 0 (by design)

- **MCP policy gate (`policy.mcp_allowed`)**: Phase 2. Until then the Copilot MCP file is still generated but only used if someone passes `--additional-mcp-config`.
- **Seat model, multi-seat, re-run onboarding, catalogue**: Phases 1–2.
- **`CONTRIBUTING-KIT.md` recipes**: Phase 5. This phase only sets the version policy that the recipes reference.

Minor items deferred by the Task 12 code review (2026-10-07). Each one is known and none blocks Phase 0:

- **Link rewriting in the Copilot brief** only handles `](./`. Bare relative links (`](docs/x.md)`), `](../`, and reference-style links inside §0/§3 still resolve against `.github/`.
- **PEP 668 and pip in the Jenkinsfile**: `python3 -m pip install --user` fails on an "externally managed" system Python (Debian/Ubuntu 23.04+). It needs a venv or `--break-system-packages`, depending on the FRQ agents.
- **A deletion-only commit skips the `harness-drift` pre-commit hook**: when the only staged change is a removed rule, `files:` matches nothing. The fix is `always_run: true` (or a `types`/`files` tweak), weighed against the cost of running the hook on every commit.
- **`.vscode/settings.json` formatting**: `merge_json` rewrites with `indent=2` and `ensure_ascii=True`, so an operator's tab or 4-space indent, and any non-ASCII characters (escaped as `\uXXXX`), are rewritten the first time the key is added.
- **Uninstall leaves `chat.useClaudeHooks` behind**: `.vscode/settings.json` is merge-class with no sentinel block, so uninstall keeps the file as it is, key included.
- **"Take" on a pre-existing file records it as kit-owned, so `uninstall` deletes it.** This applies to template files through `apply()` and to generated Copilot files through H2. It needs a `preexisting` flag on the manifest entry.
- **`uninstall` deletes MODIFIED own-class files**, so an operator's edits to a kit-owned file are lost on uninstall.
- **`uninstall` leaves `.kit-new` sidecars behind.** They are never recorded in the manifest.
- **False conflict after `sync --write`**: `sync --write` rewrites generated files without updating the install manifest hash, so a later `install` (after another source change) can treat the brief as user-edited and defer it with a `.kit-new`. Fix: have `sync --write` refresh the manifest hash of files it rewrites. The pre-commit drift gate makes this unlikely.
- **`sync.py --write`'s orphan sweep relies on the header alone.** Unlike the installer after H4, it does not check the manifest hash, so an edited orphan is still removed by `--write`.
- **The session-hook tests (`test_session*`) append to the real `template/scripts/session/.usage-errors.log`**, the relative `errlog` path in `collect-usage.sh`. The file is gitignored but grows in the kit checkout. The tests should run the hook from a temp dir.
