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

(a) Add `materialize` after the Copilot renderers:

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
    problems, wanted_rules = [], {}
    for rel, want, mode, sspec in derived_surfaces(root, table, harnesses):
        if sspec.get("format") == "copilot-instructions":
            wanted_rules.setdefault(id(sspec), (sspec, set()))[1].add(rel)
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
    for sspec, rels in wanted_rules.values():
        for orphan in orphan_instructions(root, sspec, rels):
            problems.append(f"{orphan} is an orphan")
    return problems


def write(root, table, harnesses) -> list[str]:
    root = Path(root)
    written, wanted_rules = [], {}
    for rel, want, mode, sspec in derived_surfaces(root, table, harnesses):
        if sspec.get("format") == "copilot-instructions":
            wanted_rules.setdefault(id(sspec), (sspec, set()))[1].add(rel)
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        have = path.read_text(encoding="utf-8") if path.is_file() else ""
        out = merge.merge_toml_block(have, want) if mode == "block" else want
        if out != have:
            path.write_text(out, encoding="utf-8")
            written.append(rel)
    for sspec, rels in wanted_rules.values():
        for orphan in orphan_instructions(root, sspec, rels):
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

Note: a rules directory with **zero** rules yields no `copilot-instructions` entries, so its orphans are not swept. That is acceptable for this phase, and the kit always ships rules.

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

**Step 3: Jenkins (FRQ).** Create `template/ci/Jenkinsfile.ai-governance`:

```groovy
// AI-governance gate for Jenkins — same checks as .github/workflows/ai-governance.yml.
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
        sh 'python3 scripts/validate-moments.py'
        sh 'python3 scripts/validate-seat-profiles.py'
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
- **GitHub Copilot** (CLI, VS Code, IntelliJ): interactive questions in chat, shell for commands, file-write for `USER.md`. Copilot CLI and VS Code run the SessionStart hook; **IntelliJ has no session hooks — run `bash scripts/session/start.sh` yourself** at the start of each session (the generated `.github/copilot-instructions.md` says so too).
```

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

To upgrade a repo, run `./install.sh --into <repo> --dry-run` from the newer kit, review the plan, then run it without `--dry-run`. Files the kit owns and you never edited are replaced. Files you changed are shown as a diff for you to decide; nothing is overwritten silently.
```

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

### Task 12: Full verification and phase close-out

**Step 1: Run the whole kit CI locally**, copying every `run:` line from `.github/workflows/ci.yml`:

```bash
pip install --quiet "pyyaml>=6"
grep -E '^\s+python3 ' .github/workflows/ci.yml | sed 's/^ *//' > /tmp/ci-cmds.sh
bash -e /tmp/ci-cmds.sh && echo ALL-GREEN
```
Expected: `ALL-GREEN`. The knowledge-graph smoke commands at the end of the file are multi-line `run:` blocks, so run that step by hand from the YAML.

**Step 2: End-to-end on a real FRQ-shaped repo (human-observed).** On the VM, in a scratch clone of an existing FRQ repo:

```bash
./install.sh --into ~/scratch/frq-repo --profile standard --harness copilot-cli --dry-run   # review
./install.sh --into ~/scratch/frq-repo --profile standard --harness copilot-cli
cd ~/scratch/frq-repo && python3 scripts/harness/sync.py --check && copilot
```
Expected: dry-run shows a plan without conflicts on the client's own files, `--check` passes, and Copilot CLI starts onboarding because `USER.md` is missing (design §4.0 step 2).

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
