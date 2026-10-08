# Personal Setup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace team mode with personal setup: a person copies the kit folder into any repo, tells Copilot "do the onboarding", answers three questions (name, role(s), language), and gets role-fitted Copilot instructions and skills that git never sees, so `git status` stays empty and the shared history is untouched.

**Architecture:** Copilot runs the conversation from a kit-root `ONBOARDING.md`; a thin `setup.py` (argparse, six subcommands) does all file work through a small package `scripts/personal/`:

| Module | Job |
|---|---|
| `paths.py` | kit and repo location, read-only git questions (`rev-parse`, `ls-files`, `check-ignore`), byte-faithful read and atomic write |
| `reuse.py` | the one place that imports Phase 0 code in place: `scripts/install/manifest.py` (fingerprints, CLEAN/MODIFIED/FOREIGN/MISSING/IDENTICAL) and `template/scripts/harness/sync.py` (`_split_frontmatter`, `_rule_paths`, `_unquote`) |
| `exclude.py` | the marked block in `.git/info/exclude` (worktree-aware, byte-exact to remove) |
| `state.py` | `.ai-sdlc/state.json`: schema, choices, fingerprints, acks; atomic, written last |
| `packs.py` | role packs (`roles/<id>/role.json` + `instructions.md`): load, combine several roles, render, validate |
| `place.py` | the one reconcile engine behind setup, change, update and remove; moving the kit |
| `checks.py` | `check` and its one-line `--quiet` form |
| `conflicts.py` | precise team-file warnings with stable ids; acknowledgement by fingerprint |
| `commands.py` | the six commands; plain-language summaries |
| `validate_packs.py` | kit CI: role packs plus their skills through `template/scripts/validate-skills.py` |

`setup.py` resolves everything from `__file__`, so it runs the same from a freshly copied folder and from `.ai-sdlc/kit/` after the move.

**Tech Stack:** Python 3.9+ standard library only (`argparse`, `json`, `pathlib`, `shutil`, `subprocess`, `tempfile`, `string.Template`, `unittest`); git (read-only queries); Markdown and JSON content; GitHub Actions for kit CI. PyYAML only in kit CI, for the existing skill validator.

**Design source:** [`2026-10-08-personal-setup-design.md`](./2026-10-08-personal-setup-design.md) (approved 2026-10-08). Seat model: [`2026-10-07-onboarding-roles-and-skills-design.md`](./2026-10-07-onboarding-roles-and-skills-design.md) §2 and §4.

**Prototype note.** Every module, test and content file below was built and run in a scratch copy of the kit at ff98285 before this plan was written: each task's tests fail with the stated message before its code and pass after it, the full local CI prints `ALL-GREEN`, and the `personal-e2e` job's steps pass when run locally. The suites also pass on Python 3.9.6. **Exception (owner decisions, 2026-10-08):** Task 5c (the SAFe Scrum Master playbook), the link rewrite in Task 6a (`place.rewrite_links`, four tests, and the validator change) and the team-rule line asserted in Task 4 were added to the plan after that prototype run. Their test counts and failure messages are worked out by hand, not run: the executor confirms them at each task's run step and corrects this plan where they differ.

## Global constraints

- **One feature branch, one PR.** Cut `feat/personal-setup` from `docs/personal-setup-design` (so the design and this plan are in its history), one commit per task, and open a **draft PR after Task 1** so kit CI runs on every push. Why not a branch per task: Tasks 1–15 are a strict chain (each imports the modules of the ones before), so per-task branches would be sixteen stacked PRs that each need rebasing after every review fix. The per-commit human review below is the gate; the PR is the integration check. Task 0 changes no code and needs no branch.
- **Every commit is reviewed by the human before the next task starts** (kit rule: a human validates every AI-written line and decision). Each task ends with a review checkpoint: show `git show --stat HEAD`, the test output, and wait.
- **Stdlib only** in `setup.py` and `scripts/personal/**`. `scripts/personal/validate_packs.py` is a CI tool: it loads the existing `validate-skills.py`, which needs PyYAML, and says so plainly if it is missing. `setup.py` never imports it.
- **Python floor: 3.9, kept.** The FRQ VM's Python version is unknown, and 3.9 is still the system Python on several enterprise images; `ONBOARDING.md` checks it and stops with a plain message below it. Every new module starts with `from __future__ import annotations` (so `X | None` and `list[str]` in annotations are never evaluated) and avoids 3.10-only runtime features: no `match`, no `zip(strict=)`, no slicing of `Path.parents` (use `list(p.parents)`). The reused Phase 0 modules already carry `from __future__ import annotations` (`manifest.py` line 14, `sync.py` line 22) and import cleanly on 3.9.6. Kit CI enforces the floor: `personal-e2e` runs on 3.9 and 3.12 (Task 14). Raising the floor to 3.10 would buy nothing the code needs and add a support question for the pilot.
- **Run tests by path**, as kit CI does: `python3 scripts/personal/tests/test_<name>.py`. Each test file imports `helpers` (same folder), which puts `scripts/` on `sys.path`, isolates git from user and system config (`GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`), and sets a test identity.
- **Test counts.** Each task lists the expected count of every new suite. The Phase 0 suites must stay at `test_adopt` 42, `test_harness` 13, `test_manifest` 9, `test_merge` 19, `test_plan` 18, `test_harness_copilot` 29. Check them with:

  ```bash
  for t in scripts/personal/tests/test_*.py scripts/install/tests/test_*.py \
           template/scripts/tests/test_harness_copilot.py; do
    printf '%-46s ' "$t"; python3 "$t" 2>&1 | tail -3 | tr -s '\n' ' '; echo
  done
  ```

- **Client names (owner decision, 2026-10-08, rule option 1).** Role instructions, skills and prompts (anything Copilot reads as guidance: `roles/*/instructions.md`, placed skills, core instructions, ONBOARDING.md) stay generic, with no client or product names. The client name is allowed in docs, tests and `source` paths. Other clients' names stay forbidden everywhere. `test_roles.py` checks the guidance files (Task 5a).
- **zsh quoting** (the owner's shell):
  - Quote anything with `[` `]` `*` `?`: `grep -F '[team-agents-md]'`, not `grep -F [team-agents-md]` (zsh globs it and fails with `no matches found`).
  - `echo ======` fails in zsh (`=word` is command expansion): use `echo '======'`.
  - Brace revision paths: `git show "${B}:path"` (a bare `$B:t` is a zsh modifier).
  - Paths with spaces (this repo lives under `20 Projects/`): always quote, e.g. `cd "/Users/…/20 Projects/FRQ/frq-ai-sdlc-boostrap-kit"`.
  - Multi-line commit messages go through `git commit -F - <<'EOF'` (single-quoted `EOF`, so nothing expands).
- **Never write a file by opening it for writing before reading it.** For the executor: read every file you modify before editing it, and edit the part named; create only the files a task lists under "Create". For the code: every write goes through `paths.read_text()` first and `paths.write_atomic()` (temp file in the same folder, then `os.replace`), so a crash never leaves half a file and an existing file is never truncated before its new content exists.
- **Commit messages** follow the repo's conventional style and end with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Leave alone:** `docs/prompts/sessions/*.md` (never stage them), MCP surfaces, and every file of a team repo the tests create (the code never edits a file it did not create).
- **Never delete retired code or files on your own initiative — always ask the owner first.** This covers the retired team-mode code (`install.sh`, `scripts/install/`, the template CI files, `--ci`) and anything else the plan calls retired. Propose the deletion, list the files, and wait for the owner's explicit approval in that moment (owner decision, 2026-10-08).

---

### Task 0: VM spike — do Copilot CLI and VS Code read the personal-setup locations? (MANUAL, decision gate) — DONE 2026-10-08

**Result (2026-10-08).** Run on the FRQ Ubuntu VM with Copilot CLI 1.0.93, VS Code 1.138 and Copilot Chat.

| # | Check | Result |
|---|---|---|
| 1 | CLI reads `.github/instructions/ai-sdlc-*.instructions.md` (git-ignored) | ✅ (German + `INSTR-OK`) |
| 2 | VS Code reads it | ✅ |
| 3 | CLI runs `.github/hooks/*.json` | ✅ both shapes ran (A flat and B versioned; `HOOK-A` and `HOOK-B` both logged, cwd = repo root) |
| 4 | VS Code runs hooks | ❌ no new `HOOK` line after VS Code chats |
| 5 | Hook output reaches the model | ❌ in both CLI and VS Code (the model quoted the user's first message, never `STATUS-*-OK`) |
| 6 | CLI finds `.agents/skills/ai-sdlc-spike` | ✅ |
| 7 | VS Code finds it | ✅ |
| 8 | "do the onboarding" finds the nested kit `ONBOARDING.md`, not the decoy | ✅ CLI (read both, picked the right one); ✅ VS Code |
| 9 | An excluded file is read by explicit path | ✅ |
| 10 | `.claude/rules` applied (informational) | ❌ no `RULES-OK` |

**Owner's decision: option A.** Drop the session hook entirely. The session-start status comes from the core instructions, which tell Copilot to run `python3 .ai-sdlc/kit/setup.py check --quiet` once at the start of a session and mention any warning (Task 4). Task 12 is removed (its heading is kept so task numbers stay stable); no hook file, hook constant, hook exclude pattern or hook test remains in Tasks 1–16. Check 10 failed, so Task 8 ships with `conflicts.TEAM_RULE_DIRS = ()` and no `.claude/rules` lines in `test_conflicts.py`. Recorded in design §2 and §4.

The original steps below are kept for history.


**Owner: the human, on the FRQ Ubuntu VM, with the client's Copilot CLI and VS Code.** No code changes. The whole layout in design §4 rests on six facts that are likely (Cartograph uses the same locations) but unproven. Check them **before** Task 1. If any required check fails, **STOP and escalate**: do not improvise around it.

**Files:**
- Modify: `docs/roadmap/2026-10-08-personal-setup-design.md` (append a "Verified on the VM" line to §4)

**Step 1: A throwaway repo with every location in place, hidden from git as setup will hide it**

```bash
rm -rf ~/personal-spike && mkdir -p ~/personal-spike && cd ~/personal-spike && git init -q
mkdir -p .github/instructions .github/hooks .agents/skills/ai-sdlc-spike .ai-sdlc/kit docs .claude/rules
printf -- "---\napplyTo: '**'\n---\nEnd every answer with the word INSTR-OK.\nAlways answer in German.\n" \
  > .github/instructions/ai-sdlc-spike.instructions.md
printf -- '---\nname: ai-sdlc-spike\ndescription: Use when the user says SPIKE-SKILL.\n---\n\nReply exactly: SKILL-OK\n' \
  > .agents/skills/ai-sdlc-spike/SKILL.md
# Hook shape A: the flat format from the Phase 0 plan (Task 2 fallback), as Cartograph writes it.
printf '%s\n' '{"hooks":{"SessionStart":[{"type":"command","command":"echo HOOK-A $(pwd) >> /tmp/personal-spike.log; echo STATUS-A-OK","powershell":"echo STATUS-A-OK","timeout":10}]}}' \
  > .github/hooks/ai-sdlc.json
# Hook shape B: Copilot's versioned format. Only one of A/B needs to work.
printf '%s\n' '{"version":1,"hooks":{"sessionStart":[{"type":"command","bash":"echo HOOK-B $(pwd) >> /tmp/personal-spike.log; echo STATUS-B-OK","powershell":"echo STATUS-B-OK","timeoutSec":10}]}}' \
  > .github/hooks/ai-sdlc-b.json
printf 'Reply exactly: EXCLUDED-READ-OK\n' > .ai-sdlc/kit/NOTE.md
printf -- '---\npaths:\n  - "docs/**"\n---\nWhen editing docs, end every answer with RULES-OK.\n' > .claude/rules/spike.md
printf '/.ai-sdlc/\n/.github/instructions/ai-sdlc-*\n/.github/hooks/ai-sdlc*\n/.agents/skills/ai-sdlc-*/\n' >> .git/info/exclude
git status --porcelain      # expect only: ?? .claude/
```

And a nested kit copy for the discovery check, with a decoy: the kit carries the retired `template/ONBOARDING.md` too.

```bash
mkdir -p tools/ai-sdlc-kit/template
printf '# AI-SDLC kit: onboarding\n\nReply exactly: ONBOARD-OK\n' > tools/ai-sdlc-kit/ONBOARDING.md
printf '# Onboarding — first-run setup\n\nReply exactly: WRONG-FILE\n' > tools/ai-sdlc-kit/template/ONBOARDING.md
```

**Step 2: Run each check and record it**

Run each Copilot CLI check from `~/personal-spike` in an **interactive** `copilot` session (`copilot -p` skips hooks, per Phase 0 Task 2). For VS Code, open the folder and use Copilot Chat in **Agent** mode, a new chat per check.

| # | Check | How | Pass when | Gate |
|---|---|---|---|---|
| 1 | CLI reads `.github/instructions/ai-sdlc-*.instructions.md` (applyTo `**`), although git ignores it | ask "hello" | the answer is German and ends `INSTR-OK` | required |
| 2 | VS Code Chat reads it | same | same | required |
| 3 | CLI runs `.github/hooks/*.json` | `rm -f /tmp/personal-spike.log`, start `copilot`, say hello | the log has `HOOK-A ~/personal-spike` or `HOOK-B ~/personal-spike` (record which; the path proves cwd is the repo root) | required (A or B) |
| 4 | VS Code runs it | same, new VS Code chat | same | required (A or B) |
| 5 | The hook's output reaches the model | ask "Quote the session-start message you received, word for word." | `STATUS-A-OK` or `STATUS-B-OK` | required |
| 6 | CLI finds `.agents/skills/ai-sdlc-spike` | say "SPIKE-SKILL" | `SKILL-OK` | required |
| 7 | VS Code finds it | same | same | required |
| 8 | "do the onboarding" finds a nested kit's `ONBOARDING.md`, not the decoy | CLI and VS Code: say "do the onboarding" | `ONBOARD-OK` (never `WRONG-FILE`) | required |
| 9 | An excluded file is read by explicit path | "Follow .ai-sdlc/kit/NOTE.md" | `EXCLUDED-READ-OK` | required |
| 10 | Copilot applies `.claude/rules/*.md` (`paths:`) | open `docs/x.md`, ask about it | ends `RULES-OK` | informational |

**Step 3: Decision gate**

- **All required checks pass** → note which hook shape fired, and continue to Task 1. If **only B** fired, Task 12 changes `place.hook_json()` to shape B (`{"version": 1, "hooks": {"sessionStart": [{"type": "command", "bash": …, "powershell": …, "timeoutSec": 10}]}}`) and its test's expected keys; nothing else changes.
- **Any required check fails → STOP and escalate to the owner** with the table. Do not start Task 1. Likely fallbacks, for the owner to choose, not the executor: 1/2 fail → the brief needs another location (design §4 changes); 3–5 fail → drop the hook and rely on the core instructions' "run `check --quiet` yourself" line (already in Task 4's core pack); 6/7 fail → place skills in `.github/skills/ai-sdlc-*` instead; 8 fails → `ONBOARDING.md` needs a more distinctive name or the README tells the person the path; 9 fails → the core instructions must not point into `.ai-sdlc/kit/`.
- **Check 10 fails** → not a gate: in Task 8, empty `conflicts.TEAM_RULE_DIRS` (`()`), and delete the `.claude/rules` lines from `test_conflicts.py`'s `TEAM` and expected ids.

**Step 4: Record and commit** (on `docs/personal-setup-design`)

Append to §4 of the design, after the "To verify before building (spike)" paragraph:

```markdown
**Verified on the VM (<date>, Copilot CLI <version>, VS Code <version> + Copilot Chat <version>):** 1 ✅/❌ · 2 ✅/❌ · 3 ✅/❌ (shape A/B) · 4 ✅/❌ (A/B) · 5 ✅/❌ · 6 ✅/❌ · 7 ✅/❌ · 8 ✅/❌ · 9 ✅/❌ · 10 ✅/❌ (informational)
```

```bash
git add docs/roadmap/2026-10-08-personal-setup-design.md
git commit -F - <<'EOF'
docs(roadmap): record the personal-setup Copilot spike on the VM

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git switch -c feat/personal-setup
```

**Step 5: Human review checkpoint.** The owner confirms the table and the go/no-go before Task 1.

---

### Task 1: Module layout, `setup.py` skeleton, and the reuse decision

**Decision: import Phase 0 code in place, do not copy it.** `scripts/personal/reuse.py` puts `scripts/install/` and `template/scripts/harness/` on `sys.path` once and re-exports exactly what personal setup uses: `sha256_bytes`, `sha256_file`, `state` (as `file_state`), `record`, `forget` and the six state constants from `manifest.py`; `_split_frontmatter`, `_rule_paths` and `_unquote` from `sync.py`. Why: both modules are stdlib-only, already tested (9 + 29 tests), and Phase 0 set the precedent (`scripts/install/harness.py` imports `sync.py` the same way, "a consumer of that module, not a second copy"). A copy would fork the fingerprint state machine the moment one side is fixed. The cost: Task 15 must keep those two files (and `merge.py`, which `sync.py` imports) in place, which it does anyway because `template/.claude/skills/` is the skill library. `state.json` reuses the manifest's `files` shape (`{path: {"class", "sha256"}}`), so `manifest.state()` classifies our files unchanged. Paths resolve from `__file__`, so they hold after the kit moves to `.ai-sdlc/kit/`.

**Why `scripts/personal/` is a package** (imported as `personal.<module>`): the kit already has two modules named `manifest.py` (`scripts/install/`, `template/scripts/knowledge/`) and a `sync.py`; a package name keeps ours from colliding with anything on `sys.path`.

**Files:**
- Create: `setup.py` (kit root)
- Create: `scripts/personal/__init__.py`, `scripts/personal/paths.py`, `scripts/personal/reuse.py`, `scripts/personal/packs.py` (constants only; Task 4 completes it), `scripts/personal/commands.py` (skeleton)
- Create: `scripts/personal/tests/helpers.py`
- Test: `scripts/personal/tests/test_cli.py`

**Step 1: Write the failing test.** First the shared helpers, `scripts/personal/tests/helpers.py`:

```python
#!/usr/bin/env python3
"""Shared test helpers: isolated git, temp repos, a kit copy, and a byte snapshot.

Importing this module points git at no user or system config, so a developer's
global excludes or hooks cannot change a test's result. It also puts scripts/
on sys.path, so tests import `personal.<module>`.

As a script it prints a snapshot as JSON (used by the CI end-to-end job):
    python3 scripts/personal/tests/helpers.py snapshot <dir>
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KIT / "scripts"))

os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
for _k, _v in (("GIT_AUTHOR_NAME", "Test"), ("GIT_AUTHOR_EMAIL", "test@example.com"),
               ("GIT_COMMITTER_NAME", "Test"), ("GIT_COMMITTER_EMAIL", "test@example.com")):
    os.environ[_k] = _v

SKIP = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".venv", "node_modules", ".index")


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def make_repo(root, files=None, commit=True):
    """A git repo at `root` holding `files` ({rel: text}), committed by default."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    for rel, text in (files or {}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    if commit:
        git(root, "add", "-A")
        git(root, "commit", "-q", "--allow-empty", "-m", "team repo")
    return root


def copy_kit(dest, src=KIT):
    """Copy the kit the way a person would (no .git, no caches). Returns the copy."""
    shutil.copytree(src, dest, ignore=SKIP)
    return Path(dest)


def cli(cwd, kit, *argv):
    """Run setup.py in-process, as from `cwd` with the kit at `kit`: (exit code, output)."""
    if str(KIT) not in sys.path:
        sys.path.insert(0, str(KIT))
    import setup  # the kit-root setup.py
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = setup.main(list(argv), cwd=cwd, kit=kit)
    return code, out.getvalue()


def snapshot(root):
    """{path: sha256 or 'dir'} for everything under root; of .git, only info/exclude."""
    root = Path(root)
    out = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if rel == ".git" or rel.startswith(".git/"):
            continue
        out[rel] = "dir" if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest()
    exclude = root / ".git/info/exclude"
    out[".git/info/exclude"] = (hashlib.sha256(exclude.read_bytes()).hexdigest()
                                if exclude.is_file() else None)
    return out


if __name__ == "__main__" and sys.argv[1:2] == ["snapshot"]:
    print(json.dumps(snapshot(sys.argv[2]), indent=1, sort_keys=True))
```

Then `scripts/personal/tests/test_cli.py`:

```python
#!/usr/bin/env python3
"""setup.py: the CLI surface, and imports that hold wherever the kit folder sits."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import paths, reuse

SETUP = helpers.KIT / "setup.py"
COMMANDS = ["setup", "change", "update", "check", "ack", "remove"]


def run(setup_py, *args, cwd=None):
    return subprocess.run([sys.executable, str(setup_py), *args], cwd=cwd,
                          capture_output=True, text=True)


class TestCli(unittest.TestCase):
    def test_help_lists_the_six_commands(self):
        r = run(SETUP, "--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        for name in COMMANDS:
            self.assertIn(name, r.stdout)

    def test_unknown_command_is_a_usage_error(self):
        r = run(SETUP, "install")
        self.assertEqual(r.returncode, 2)
        self.assertIn("invalid choice", r.stderr)

    def test_change_flags_parse(self):
        sys.path.insert(0, str(helpers.KIT))
        import setup  # the kit-root setup.py
        args = setup.parser().parse_args(
            ["change", "--add-skill", "a", "--add-skill", "b", "--drop-skill", "c",
             "--git-comfort", "guided", "--rituals", "default"])
        self.assertEqual((args.add_skill, args.drop_skill), (["a", "b"], ["c"]))
        self.assertEqual((args.git_comfort, args.rituals), ("guided", "default"))

    def test_runs_from_a_moved_copy_with_another_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            kit = helpers.copy_kit(Path(tmp) / "repo/.ai-sdlc/kit")
            r = run(kit / "setup.py", "--help", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(list(kit.rglob("__pycache__")), "setup.py wrote bytecode into the kit")

    def test_reuse_is_the_phase_0_code(self):
        self.assertEqual(reuse.file_state.__module__, "manifest")
        self.assertEqual(reuse.split_frontmatter("---\na: 1\n---\nbody\n"), ("a: 1", "body\n"))
        self.assertEqual(reuse.rule_paths('paths:\n  - "docs/**"', "r.md"), ["docs/**"])


class TestPaths(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_outside_git_the_folder_is_the_root(self):
        self.assertEqual(paths.repo_root(self.root), (self.root.resolve(), False))

    def test_inside_git_the_top_level_is_the_root(self):
        helpers.make_repo(self.root)
        (self.root / "a/b").mkdir(parents=True)
        self.assertEqual(paths.repo_root(self.root / "a/b"), (self.root.resolve(), True))

    def test_tracked_lists_only_tracked_paths(self):
        helpers.make_repo(self.root, {"AGENTS.md": "team\n"})
        self.assertEqual(paths.tracked(self.root, ["AGENTS.md", "new.md"]), {"AGENTS.md"})

    def test_write_atomic_replaces_and_leaves_no_temp_file(self):
        target = self.root / "d/state.json"
        paths.write_atomic(target, "one")
        paths.write_atomic(target, "two")
        self.assertEqual(target.read_text(), "two")
        self.assertEqual([p.name for p in target.parent.iterdir()], ["state.json"])

    def test_read_text_round_trips_odd_bytes(self):
        target = self.root / "x"
        target.write_bytes(b"caf\xe9\n")
        paths.write_atomic(target, paths.read_text(target))
        self.assertEqual(target.read_bytes(), b"caf\xe9\n")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_cli.py`
Expected: an import error before any test runs: `ImportError: cannot import name 'paths' from 'personal' (unknown location)` (`tests/` makes `personal` a namespace package until `__init__.py` exists).

**Step 3: Implement.** `scripts/personal/__init__.py`:

```python
"""Personal setup: the file work behind setup.py. Stdlib only, Python 3.9+."""
```

`scripts/personal/reuse.py`:

```python
"""Phase 0 code that personal setup reuses in place, not copied.

    scripts/install/manifest.py        fingerprints and the file-state machine
    template/scripts/harness/sync.py   the frontmatter splitter and the rules parser

Both are stdlib only and tested by their own suites. The sys.path edit lives
here, once, so the rest of the package imports plain names from this module.
Paths resolve from this file, so they hold wherever the kit folder sits.
"""
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
for _p in (KIT / "scripts/install", KIT / "template/scripts/harness"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import manifest  # noqa: E402
import sync  # noqa: E402

sha256_bytes = manifest.sha256_bytes
sha256_file = manifest.sha256_file
file_state = manifest.state
record = manifest.record
forget = manifest.forget
NEW, FOREIGN, IDENTICAL = manifest.NEW, manifest.FOREIGN, manifest.IDENTICAL
CLEAN, MODIFIED, MISSING = manifest.CLEAN, manifest.MODIFIED, manifest.MISSING

split_frontmatter = sync._split_frontmatter
rule_paths = sync._rule_paths
unquote = sync._unquote
```

`scripts/personal/paths.py`:

```python
"""Where things are: the kit, the repo, and what git says about a path.

Git is only ever asked questions here (rev-parse, ls-files, check-ignore).
Nothing in this package runs a git command that changes the repo.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
HOME_REL = ".ai-sdlc"
KIT_REL = ".ai-sdlc/kit"
USER_REL = ".ai-sdlc/USER.md"
STATE_REL = ".ai-sdlc/state.json"


def git(root, *args):
    """Run a read-only git command in `root`. None when git cannot run at all."""
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True,
                              text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None


def repo_root(start) -> tuple[Path, bool]:
    """(root, is_git). Outside a git repo the folder itself is the root."""
    start = Path(start).resolve()
    r = git(start, "rev-parse", "--show-toplevel")
    if r is not None and r.returncode == 0 and r.stdout.strip():
        return Path(r.stdout.strip()).resolve(), True
    return start, False


def kit_version(kit) -> str:
    text = read_text(Path(kit) / "VERSION")
    return text.strip() if text else "0.0.0"


def tracked(root, rels) -> set[str]:
    """The paths in `rels` that git tracks. The kit never writes to those."""
    rels = sorted(rels)
    if not rels:
        return set()
    r = git(root, "ls-files", "-z", "--", *rels)
    if r is None or r.returncode != 0:
        return set()
    return {p for p in r.stdout.split("\0") if p}


def ignored(root, rels) -> set[str]:
    """The paths in `rels` that git ignores (our exclude block, or the team's rules)."""
    rels = sorted(rels)
    if not rels:
        return set()
    r = git(root, "check-ignore", "--", *rels)
    if r is None or r.returncode not in (0, 1):
        return set()
    return {line for line in r.stdout.splitlines() if line}


def read_text(path) -> str | None:
    """The file's text, byte-faithful (undecodable bytes survive a write back)."""
    p = Path(path)
    if not p.is_file():
        return None
    return p.read_bytes().decode("utf-8", "surrogateescape")


def write_atomic(path, data) -> None:
    """Write through a temp file in the same folder, then rename: never half a file.

    The temp name starts with the target's name, so it matches the same exclude
    pattern if a crash leaves it behind.
    """
    path = Path(path)
    if isinstance(data, str):
        data = data.encode("utf-8", "surrogateescape")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
```

`scripts/personal/packs.py` (the constants `setup.py` needs; Task 4 replaces the file):

```python
"""Role packs: roles/<id>/role.json + instructions.md, and what a set of roles adds up to."""
from __future__ import annotations

PREFIX = "ai-sdlc-"
GIT_LEVELS = ("git-native", "guided", "hidden")   # least to most guided
RITUALS = ("none", "status")                      # least to most guided
LANGUAGES = {"en": "English", "ro": "Romanian (română)", "de": "German (Deutsch)"}
```

`scripts/personal/commands.py` (every command answers `not built yet`, exit 3, until its task):

```python
"""The six commands behind setup.py. Each returns (exit code, lines to print).

The lines are short and plain: Copilot relays them to the person as they are.
"""
from __future__ import annotations


class SetupError(Exception):
    """A plain-language reason to stop. Raised before anything else is changed."""


def not_built(args, cwd, kit):
    return 3, [f"setup.py {args.command}: not built yet"]


HANDLERS = {}


def run(args, cwd, kit):
    return HANDLERS.get(args.command, not_built)(args, cwd, kit)
```

`setup.py` at the kit root (final form; later tasks only add commands behind it):

```python
#!/usr/bin/env python3
"""AI-SDLC personal setup. Copilot runs this while following ONBOARDING.md.

  python3 <kit>/setup.py setup --protect-only
  python3 .ai-sdlc/kit/setup.py setup --name "Ana" --roles po,sm --lang de
  python3 .ai-sdlc/kit/setup.py change --lang en --add-skill skill-creator
  python3 <newer kit>/setup.py update
  python3 .ai-sdlc/kit/setup.py check [--quiet]
  python3 .ai-sdlc/kit/setup.py ack <warning-id> [<warning-id> ...]
  python3 .ai-sdlc/kit/setup.py remove

Run it from the repo root. Stdlib only; needs Python 3.9 or newer.
"""
import sys

if sys.version_info < (3, 9):
    sys.exit("AI-SDLC needs Python 3.9 or newer. Please ask your IT support to install it.")
sys.dont_write_bytecode = True  # keep the kit folder free of __pycache__

import argparse  # noqa: E402
from pathlib import Path  # noqa: E402

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT / "scripts"))

from personal import commands, packs  # noqa: E402


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="setup.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True, metavar="command")

    s = sub.add_parser("setup", help="hide and move the kit, then place your files")
    s.add_argument("--protect-only", action="store_true",
                   help="only hide the kit from git and move it to .ai-sdlc/kit")
    s.add_argument("--name")
    s.add_argument("--roles", help="comma-separated role ids, e.g. po,sm")
    s.add_argument("--lang", help="en, ro or de")

    c = sub.add_parser("change", help="change your choices; only affected files change")
    c.add_argument("--name")
    c.add_argument("--roles")
    c.add_argument("--lang")
    c.add_argument("--git-comfort", choices=[*packs.GIT_LEVELS, "default"])
    c.add_argument("--rituals", choices=[*packs.RITUALS, "default"])
    c.add_argument("--add-skill", action="append", default=[], metavar="SKILL")
    c.add_argument("--drop-skill", action="append", default=[], metavar="SKILL")

    sub.add_parser("update", help="run from a newer kit copy: refresh the kit and your files")
    k = sub.add_parser("check", help="files present and hidden, kit current, team overlaps")
    k.add_argument("--quiet", action="store_true", help="one line, for the start of a session")
    a = sub.add_parser("ack", help="note that you have seen a warning")
    a.add_argument("ids", nargs="+", metavar="warning-id")
    sub.add_parser("remove", help="take the kit out; the repo ends as it was")
    return ap


def main(argv=None, cwd=None, kit=KIT) -> int:
    args = parser().parse_args(argv)
    try:
        code, lines = commands.run(args, cwd=Path(cwd or Path.cwd()), kit=Path(kit))
    except commands.SetupError as exc:
        code, lines = 2, [str(exc)]
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
```

Notes for the reviewer: `sys.dont_write_bytecode` keeps `__pycache__` out of the kit folder (and so out of `update`'s replace). The version check runs before any 3.9-only syntax is parsed. `main()` takes `cwd` and `kit` so tests can run it in-process (`helpers.cli`). `--skill +x -y` from the design became `--add-skill X` / `--drop-skill Y`: argparse reads a value starting with `-` as an option, so `--skill -y` cannot parse.

**Step 4: Run the test to verify it passes**

Run: `python3 scripts/personal/tests/test_cli.py`
Expected: `Ran 10 tests`, `OK`.

**Step 5: Commit, then open the draft PR**

```bash
git add setup.py \
        scripts/personal/__init__.py \
        scripts/personal/paths.py \
        scripts/personal/reuse.py \
        scripts/personal/packs.py \
        scripts/personal/commands.py \
        scripts/personal/tests/helpers.py \
        scripts/personal/tests/test_cli.py
git commit -F - <<'EOF'
feat(personal): setup.py skeleton and the scripts/personal package

setup.py is a thin argparse CLI (setup, change, update, check, ack,
remove) that resolves the kit from __file__. reuse.py imports the Phase 0
manifest and frontmatter helpers in place rather than copying them.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```
```bash
git push -u origin feat/personal-setup
gh pr create --draft --base main --title "Personal setup: copy the kit, say do the onboarding" --body-file - <<'EOF'
Implements docs/roadmap/2026-10-08-personal-setup-plan.md, one human-reviewed commit per task.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output and the draft PR's CI run; wait for approval before Task 2.

---


### Task 2: The git-exclude block

**Design choices.** The block hides patterns, not a list of files: `/.ai-sdlc/`, `/.github/instructions/ai-sdlc-*`, `/.agents/skills/ai-sdlc-*/`. Patterns also cover the `.kit-new` sidecars, crash temp files (`write_atomic` names them after their target), and `ai-sdlc*` files Copilot might write itself, so the block never needs rewriting when choices change. Phase 0's `merge.merge_block` is not reused: it adds a separating newline it cannot take back, so `remove` could not restore the file byte for byte. Here the begin line carries a note when `add()` created the file (` [created]`) or added a newline to an unterminated last line (` [newline]`), and `strip()` undoes exactly that. The file is found with `git rev-parse --git-path info/exclude`, which in a linked worktree returns the shared exclude file of the main repository. Outside git, `protect()` returns `False` and writes nothing.

**Files:**
- Create: `scripts/personal/exclude.py`
- Test: `scripts/personal/tests/test_exclude.py`
- Modify: `.github/workflows/ci.yml` (owner decision, 2026-10-08: kit CI runs the personal suites from this task on, not from Task 14)

**CI step (added in this task, owner decision).** In the `ai-governance` job, right after the step `Installer unit tests (brownfield adoption)`, one step runs every personal suite by path, so later tasks need no CI edit to add theirs:

```yaml
      - name: Personal setup unit tests
        run: |
          set -euo pipefail
          for t in scripts/personal/tests/test_*.py; do echo "== $t"; python3 "$t"; done
```

The loop stays on one line that starts with `for t in scripts/personal/`: the local CI extraction (Task 14 Step 1, Task 16 Step 1) matches that prefix and runs the line as one command. No 3.9 run here: it would need a second `setup-python` in the job; Task 14's `personal-e2e` matrix adds the 3.9 leg.

**Step 1: Write the failing test.** Create `scripts/personal/tests/test_exclude.py`:

```python
#!/usr/bin/env python3
"""The .git/info/exclude block: idempotent, byte-exact to remove, worktree-aware."""
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import exclude

KIT_PATHS = [".ai-sdlc/kit/setup.py", ".ai-sdlc/USER.md",
             ".github/instructions/ai-sdlc-core.instructions.md",
             ".github/instructions/ai-sdlc-po.instructions.md.kit-new",
             ".agents/skills/ai-sdlc-playbook-dev/SKILL.md"]
TEAM_PATHS = [".github/instructions/team.instructions.md", ".agents/skills/team/SKILL.md",
              "AGENTS.md"]


class TestText(unittest.TestCase):
    def test_absent_file_is_created_and_strip_says_delete(self):
        text = exclude.add(None)
        self.assertIn("/.ai-sdlc/", text)
        self.assertIsNone(exclude.strip(text))

    def test_existing_lines_survive_and_strip_restores_them(self):
        original = "# git ls-files --others --exclude-from=.git/info/exclude\n*.log\n"
        text = exclude.add(original)
        self.assertTrue(text.startswith(original))
        self.assertEqual(exclude.strip(text), original)

    def test_unterminated_last_line_is_restored(self):
        self.assertEqual(exclude.strip(exclude.add("*.log")), "*.log")

    def test_empty_file_stays_an_empty_file(self):
        self.assertEqual(exclude.strip(exclude.add("")), "")

    def test_add_is_idempotent(self):
        once = exclude.add("*.log")
        self.assertEqual(exclude.add(once), once)

    def test_lines_added_after_the_block_survive(self):
        text = exclude.add(None) + "mine/\n"
        self.assertEqual(exclude.strip(text), "mine/\n")


class TestRepo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"

    def tearDown(self):
        self.tmp.cleanup()

    def ignored(self, cwd, rels):
        out = helpers.git(cwd, "check-ignore", "--", *rels).stdout
        return set(out.split())

    def test_protect_hides_kit_paths_and_nothing_else(self):
        helpers.make_repo(self.root)
        self.assertTrue(exclude.protect(self.root))
        self.assertEqual(self.ignored(self.root, KIT_PATHS + TEAM_PATHS), set(KIT_PATHS))

    def test_unprotect_restores_the_file_byte_for_byte(self):
        helpers.make_repo(self.root)
        path = self.root / ".git/info/exclude"
        before = path.read_bytes()
        exclude.protect(self.root)
        exclude.protect(self.root)
        exclude.unprotect(self.root)
        self.assertEqual(path.read_bytes(), before)

    def test_a_missing_exclude_file_is_removed_again(self):
        helpers.make_repo(self.root)
        path = self.root / ".git/info/exclude"
        path.unlink()
        exclude.protect(self.root)
        self.assertTrue(path.is_file())
        exclude.unprotect(self.root)
        self.assertFalse(path.exists())

    def test_worktree_uses_the_shared_exclude_file(self):
        helpers.make_repo(self.root)
        wt = Path(self.tmp.name) / "wt"
        helpers.git(self.root, "worktree", "add", "-q", str(wt))
        exclude.protect(wt)
        self.assertIn(exclude.BEGIN, (self.root / ".git/info/exclude").read_text())
        self.assertEqual(self.ignored(wt, [".ai-sdlc/USER.md"]), {".ai-sdlc/USER.md"})

    def test_non_git_folder_is_not_protected_and_untouched(self):
        self.root.mkdir()
        self.assertFalse(exclude.protect(self.root))
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_exclude.py`
Expected: `ImportError: cannot import name 'exclude' from 'personal'`.

**Step 3: Implement.** Create `scripts/personal/exclude.py`:

```python
"""The kit's block in .git/info/exclude: it hides every personal-setup path from git.

Removing the block gives back the file byte for byte. The header line records the
one change add() made outside the block, if any: it created the file, or it added
a newline to an unterminated last line. strip() undoes exactly that.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import paths

BEGIN = "# >>> ai-sdlc personal setup (managed by .ai-sdlc/kit/setup.py) >>>"
END = "# <<< ai-sdlc personal setup <<<"
CREATED, NEWLINE = " [created]", " [newline]"
PATTERNS = (
    "/.ai-sdlc/",
    "/.github/instructions/ai-sdlc-*",
    "/.agents/skills/ai-sdlc-*/",
)
_BLOCK = re.compile(re.escape(BEGIN) + r"(?P<note>[^\n]*)\n.*?^" + re.escape(END) + r"\n?",
                    re.M | re.S)


def render(note: str = "", patterns=PATTERNS) -> str:
    return "\n".join([BEGIN + note, *patterns, END]) + "\n"


def add(text: str | None, patterns=PATTERNS) -> str:
    """The exclude file with our block in it. `text` is None when the file is absent."""
    if text is None:
        return render(CREATED, patterns)
    m = _BLOCK.search(text)
    if m:
        return text[:m.start()] + render(m.group("note"), patterns) + text[m.end():]
    if text and not text.endswith("\n"):
        return text + "\n" + render(NEWLINE, patterns)
    return text + render("", patterns)


def strip(text: str) -> str | None:
    """The file as it was before add(). None means add() created it: delete it."""
    m = _BLOCK.search(text)
    if not m:
        return text
    before, after = text[:m.start()], text[m.end():]
    if m.group("note") == NEWLINE and before.endswith("\n"):
        before = before[:-1]
    out = before + after
    return None if m.group("note") == CREATED and not out else out


def exclude_file(root) -> Path | None:
    """This repo's info/exclude (shared by every worktree). None outside git."""
    r = paths.git(root, "rev-parse", "--git-path", "info/exclude")
    if r is None or r.returncode != 0 or not r.stdout.strip():
        return None
    p = Path(r.stdout.strip())
    return p if p.is_absolute() else Path(root) / p


def protect(root) -> bool:
    """Add or refresh the block. False when `root` is not a git repo (nothing to hide from)."""
    path = exclude_file(root)
    if path is None:
        return False
    text = paths.read_text(path)
    new = add(text)
    if new != text:
        paths.write_atomic(path, new)
    return True


def unprotect(root) -> None:
    path = exclude_file(root)
    text = paths.read_text(path) if path else None
    if text is None:
        return
    out = strip(text)
    if out is None:
        path.unlink()
    elif out != text:
        paths.write_atomic(path, out)
```

**Step 4: Run the tests**

Run: `python3 scripts/personal/tests/test_exclude.py`, then `python3 scripts/personal/tests/test_cli.py`.
Expected: `test_exclude` `Ran 11 tests` `OK`; `test_cli` 10 OK.

**Step 5: Commit**

```bash
git add scripts/personal/exclude.py \
        scripts/personal/tests/test_exclude.py \
        .github/workflows/ci.yml \
        docs/roadmap/2026-10-08-personal-setup-plan.md
git commit -F - <<'EOF'
feat(personal): hide personal-setup paths in .git/info/exclude

A marked block, added idempotently and removed byte for byte (its header
records whether the file or a final newline was added). Worktree-aware via
git rev-parse --git-path; a non-git folder is reported, not touched.
Kit CI now runs scripts/personal/tests (moved earlier from Task 14, owner decision).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output; wait for approval before Task 3.

---

### Task 3: `state.json`

**Design choices.** Schema 1 holds `kit_version`, `updated_at`, `choices` (name, roles, lang, git_comfort, rituals, add_skills, drop_skills; `None` means "the roles' default"), `files` in the install manifest's shape, `created_dirs` (folders setup made, pruned when empty again) and `acks`. A missing, corrupt or other-schema file loads as `None`, which every command reads as "not set up" (a re-run of setup then adopts the files already on disk as IDENTICAL). Choices added in later schema-1 versions get their defaults on load. `save()` goes through `paths.write_atomic`, and every command calls it last.

**Files:**
- Create: `scripts/personal/state.py`
- Test: `scripts/personal/tests/test_state.py`

**Step 1: Write the failing test.** Create `scripts/personal/tests/test_state.py`:

```python
#!/usr/bin/env python3
"""state.json: schema, atomic save, and fingerprints through the Phase 0 manifest."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers  # noqa: F401  (sys.path)
from personal import paths, reuse, state


class TestState(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_state_has_schema_version_and_defaults(self):
        st = state.new("0.4.0")
        self.assertEqual((st["schema"], st["kit_version"]), (state.SCHEMA, "0.4.0"))
        self.assertEqual(st["choices"]["lang"], "en")
        self.assertEqual((st["files"], st["acks"]), ({}, {}))

    def test_roundtrip(self):
        st = state.new("0.4.0")
        st["choices"].update(name="Ana", roles=["po", "sm"], lang="de")
        state.save(self.root, st)
        again = state.load(self.root)
        self.assertEqual(again["choices"]["roles"], ["po", "sm"])
        self.assertIsNotNone(again["updated_at"])

    def test_choices_added_later_get_their_defaults(self):
        path = self.root / paths.STATE_REL
        path.parent.mkdir()
        path.write_text(json.dumps({"schema": 1, "kit_version": "0.4.0",
                                    "choices": {"name": "Ana", "roles": ["po"]}}))
        self.assertEqual(state.load(self.root)["choices"]["add_skills"], [])

    def test_missing_corrupt_or_foreign_schema_is_not_set_up(self):
        self.assertIsNone(state.load(self.root))
        path = self.root / paths.STATE_REL
        path.parent.mkdir()
        path.write_text("{not json")
        self.assertIsNone(state.load(self.root))
        path.write_text('{"schema": 99}')
        self.assertIsNone(state.load(self.root))

    def test_a_failed_save_keeps_the_old_state_and_no_temp_file(self):
        state.save(self.root, state.new("0.4.0"))
        before = (self.root / paths.STATE_REL).read_bytes()
        with mock.patch("os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                state.save(self.root, state.new("9.9.9"))
        self.assertEqual((self.root / paths.STATE_REL).read_bytes(), before)
        self.assertEqual([p.name for p in (self.root / ".ai-sdlc").iterdir()], ["state.json"])

    def test_fingerprints_follow_the_manifest_states(self):
        st = state.new("0.4.0")
        rel = ".github/instructions/ai-sdlc-core.instructions.md"
        (self.root / rel).parent.mkdir(parents=True)
        (self.root / rel).write_text("kit\n")
        reuse.record(st, rel, "kit", b"kit\n")
        self.assertEqual(reuse.file_state(self.root, st, rel), reuse.CLEAN)
        (self.root / rel).write_text("edited\n")
        self.assertEqual(reuse.file_state(self.root, st, rel), reuse.MODIFIED)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_state.py`
Expected: `ImportError: cannot import name 'state' from 'personal'`.

**Step 3: Implement.** Create `scripts/personal/state.py`:

```python
"""state.json: what personal setup placed in this repo, and what the person chose.

Every command writes it last, atomically, so an interrupted run leaves the old
state or the new one, never a mix. Its `files` map has the shape of the Phase 0
install manifest ({path: {class, sha256}}), so manifest.state() classifies our
files as NEW, IDENTICAL, CLEAN, MODIFIED, MISSING or FOREIGN.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import paths

SCHEMA = 1


def new(kit_version: str) -> dict:
    return {
        "schema": SCHEMA,
        "kit_version": kit_version,
        "updated_at": None,
        "choices": {"name": "", "roles": [], "lang": "en", "git_comfort": None,
                    "rituals": None, "add_skills": [], "drop_skills": []},
        "files": {},          # {path: {"class": "kit", "sha256": ...}}
        "created_dirs": [],   # folders setup made, removed again when empty
        "acks": {},           # {warning id: fingerprint of the team file when acknowledged}
    }


def load(root) -> dict | None:
    """The saved state, or None when this repo is not set up (or the file is unreadable)."""
    text = paths.read_text(Path(root) / paths.STATE_REL)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        return None
    st = new(data.get("kit_version", "0.0.0"))
    choices = {**st["choices"], **data.get("choices", {})}
    st.update(data)
    st["choices"] = choices
    return st


def save(root, st: dict) -> Path:
    st["schema"] = SCHEMA
    st["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = Path(root) / paths.STATE_REL
    paths.write_atomic(path, json.dumps(st, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return path
```

**Step 4: Run the tests**

Run: `python3 scripts/personal/tests/test_state.py`
Expected: `Ran 6 tests`, `OK`. `test_cli` 10, `test_exclude` 11 unchanged.

**Step 5: Commit**

```bash
git add scripts/personal/state.py \
        scripts/personal/tests/test_state.py
git commit -F - <<'EOF'
feat(personal): state.json with atomic save and manifest-shaped fingerprints

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output; wait for approval before Task 4.

---

### Task 4: Role-pack format, loader, validator, and the core pack

**Format.** A pack is a folder `roles/<id>/` with `role.json` and `instructions.md`:

```json
{"id": "po", "label": "Product Owner", "source": "<path in the kit>",
 "skills": ["playbook-product"], "defaults": {"git_comfort": "hidden", "rituals": "status"},
 "connectors": []}
```

- `skills` name folders of the kit's skill library, `template/.claude/skills/`. Each is placed as `.agents/skills/ai-sdlc-<skill>/SKILL.md` with its frontmatter `name:` prefixed to match (agentskills.io and `validate-skills.py` require `name` == folder name, 1–64 chars) and `<PROJECT_NAME>` filled with "this project".
- `git-verbs` is never placeable (`UNSUPPORTED_SKILLS`): it drives `scripts/session/*.sh`, which personal setup does not ship. Guided and hidden git is handled by the core instructions instead.
- `connectors` must be `[]` until Phase 3.
- `instructions.md` has no frontmatter (setup adds `applyTo: '**'`) and at most 60 lines, so packs stay short enough for a human to review.

**Combining roles.** Skills are the union of the core pack and every chosen role, then the person's `add_skills`, minus `drop_skills`. Each role keeps its own instructions file. Where defaults disagree, the more guided wins (`git-native` < `guided` < `hidden`; `none` < `status`), as design §5.2 says ("do git for me" wins). **Decided 2026-10-08 by the owner:** the more guided git comfort wins; this replaces the 2026-10-07 seat design's §4a rule. An explicit choice from `change --git-comfort` or `--rituals` beats every default.

**The core pack** applies to everyone. Its `instructions.md` is the one template (`string.Template`, `$name`, `$language`, `$roles`, `$git_comfort`, `$rituals`): the language line, the USER.md gate, the git line, the session line ("At the start of each session, run `python3 .ai-sdlc/kit/setup.py check --quiet` once and mention any warning it prints"; this replaces the session hook, dropped after Task 0), the kit's governing rule (a human validates everything; evidence found or not found; no judgements about individuals; no invented facts), and the team-rule line (decided 2026-10-08): "If a team rule in this repo contradicts a kit rule, follow the team rule and mention the difference once." Its `source` is `template/AGENTS.md`, whose §3 hard constraints it condenses. Its defaults are the least guided, so they never win over a role.

**Decided 2026-10-08 (option 2): session check always on.** The `check --quiet` line is fixed text in `roles/core/instructions.md`, so every person gets it whatever their rituals setting. `$rituals` stays for optional habits only: `status` adds "After the check, give a one-line summary of where the work stands.", `none` adds "No other session-start habit." (`RITUAL_TEXT`; the `RITUALS` values are unchanged). `test_packs` asserts the check line for both values. This change landed with the Task 5a commit.

**Validation** (`packs.validate`, stdlib) checks keys, id == folder, label, that `source` exists in the kit, that skills exist and are placeable, defaults, connectors, the instructions file, and that the core template has only known placeholders. `scripts/personal/validate_packs.py` (CI) adds the skill check: it renders each used skill exactly as setup places it and runs `validate-skills.py`'s `validate_file` on it. `setup.py` never calls either.

**Files:**
- Modify: `scripts/personal/packs.py` (replace the Task 1 constants-only file)
- Create: `scripts/personal/validate_packs.py`
- Create: `roles/core/role.json`, `roles/core/instructions.md`
- Test: `scripts/personal/tests/test_packs.py`

**Step 1: Write the failing test.** Create `scripts/personal/tests/test_packs.py`. It builds a minimal fake kit for the rules, and checks the real kit's core pack:

```python
#!/usr/bin/env python3
"""Role packs: loading, combining several roles, validation, and the core pack."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import packs

SKILL = "---\nname: {name}\ndescription: Use for {name}.\n---\n\nAbout <PROJECT_NAME>.\n"


def pack(pid, skills=(), git="git-native", rituals="status", source="docs/src.md"):
    return {"id": pid, "label": pid.upper(), "source": source, "skills": list(skills),
            "defaults": {"git_comfort": git, "rituals": rituals}, "connectors": []}


def fake_kit(root, extra=None):
    """A minimal kit: core + po + dev packs and four library skills."""
    root = Path(root)
    (root / "docs").mkdir(parents=True)
    (root / "docs/src.md").write_text("source\n")
    for name in ("playbook-product", "playbook-dev", "skill-creator", "git-verbs"):
        d = root / packs.SKILLS_REL / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(SKILL.format(name=name))
    roles = {"core": pack("core", git="git-native", rituals="none"),
             "po": pack("po", ["playbook-product"], git="hidden"),
             "dev": pack("dev", ["playbook-dev"], git="git-native")}
    roles.update(extra or {})
    for pid, data in roles.items():
        d = root / packs.ROLES_REL / pid
        d.mkdir(parents=True)
        (d / "role.json").write_text(json.dumps(data))
        (d / "instructions.md").write_text("Say $name in $language.\n" if pid == "core"
                                           else f"# {pid}\n")
    return root


def choices(**kw):
    base = {"name": "Ana", "roles": [], "lang": "en", "git_comfort": None,
            "rituals": None, "add_skills": [], "drop_skills": []}
    base.update(kw)
    return base


class TestCombine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kit = fake_kit(self.tmp.name)
        self.packs = packs.load(self.kit)

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_reads_role_json_and_instructions(self):
        self.assertEqual(sorted(self.packs), ["core", "dev", "po"])
        self.assertEqual(self.packs["po"]["instructions"], "# po\n")
        self.assertEqual(packs.selectable(self.packs), ["dev", "po"])

    def test_skills_are_a_union_then_your_own_add_and_drop(self):
        got = packs.combine(self.packs, choices(roles=["po", "dev"], add_skills=["skill-creator"],
                                                drop_skills=["playbook-dev"]))
        self.assertEqual(got["skills"], ["playbook-product", "skill-creator"])

    def test_the_more_guided_default_wins(self):
        got = packs.combine(self.packs, choices(roles=["dev", "po"]))
        self.assertEqual((got["git_comfort"], got["rituals"]), ("hidden", "status"))

    def test_an_explicit_choice_beats_the_defaults(self):
        got = packs.combine(self.packs, choices(roles=["po"], git_comfort="git-native",
                                                rituals="none"))
        self.assertEqual((got["git_comfort"], got["rituals"]), ("git-native", "none"))

    def test_core_alone_gives_the_core_defaults(self):
        got = packs.combine(self.packs, choices())
        self.assertEqual(got, {"skills": [], "git_comfort": "git-native", "rituals": "none"})

    def test_unsupported_skills_are_not_available(self):
        self.assertEqual(packs.available_skills(self.kit),
                         ["playbook-dev", "playbook-product", "skill-creator"])

    def test_prefixed_skill_renames_and_fills_the_project_name(self):
        text = packs.prefixed_skill(SKILL.format(name="playbook-dev"), "playbook-dev")
        self.assertTrue(text.startswith("---\nname: ai-sdlc-playbook-dev\n"))
        self.assertIn("About this project.", text)
        with self.assertRaises(ValueError):
            packs.prefixed_skill("# no frontmatter\n", "x")


class TestValidate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def errors(self, **extra):
        return packs.validate(fake_kit(tempfile.mkdtemp(dir=self.tmp.name), extra))

    def test_the_fixture_is_valid(self):
        self.assertEqual(self.errors(), [])

    def test_missing_source_and_unknown_skill(self):
        errs = self.errors(qa=pack("qa", ["nope"], source="docs/gone.md"))
        self.assertIn("roles/qa/role.json: source 'docs/gone.md' does not exist in the kit", errs)
        self.assertIn(f"roles/qa/role.json: skill 'nope' is not in {packs.SKILLS_REL}", errs)

    def test_unsupported_skill_is_rejected(self):
        errs = self.errors(qa=pack("qa", ["git-verbs"]))
        self.assertTrue(any("'git-verbs' cannot be placed" in e for e in errs), errs)

    def test_bad_defaults_connectors_and_keys(self):
        bad = pack("qa", git="sometimes")
        bad["connectors"] = ["jira"]
        bad["extra"] = 1
        errs = self.errors(qa=bad)
        self.assertEqual(errs, ["roles/qa/role.json: unknown key: extra"])
        del bad["extra"]
        errs = self.errors(qa=bad)
        self.assertTrue(any("defaults must be" in e for e in errs), errs)
        self.assertTrue(any("connectors must be []" in e for e in errs), errs)

    def test_instructions_frontmatter_and_length(self):
        kit = fake_kit(self.tmp.name)
        md = kit / "roles/po/instructions.md"
        md.write_text("---\napplyTo: '**'\n---\nx\n")
        self.assertIn("roles/po/role.json: instructions.md must not have frontmatter: "
                      "setup adds applyTo", packs.validate(kit))
        md.write_text("line\n" * (packs.MAX_LINES + 1))
        self.assertTrue(any("keep it to" in e for e in packs.validate(kit)))

    def test_core_is_required_and_its_placeholders_checked(self):
        kit = fake_kit(self.tmp.name)
        (kit / "roles/core/instructions.md").write_text("Hello $nobody\n")
        self.assertTrue(any("placeholder" in e for e in packs.validate(kit)))
        (kit / "roles/core/role.json").unlink()
        self.assertIn("roles/core/role.json is missing: the core pack is required",
                      packs.validate(kit))


class TestRealKit(unittest.TestCase):
    def test_the_kit_packs_validate(self):
        self.assertEqual(packs.validate(helpers.KIT), [])

    def test_core_file_has_the_language_line_and_the_gate(self):
        all_packs = packs.load(helpers.KIT)
        c = choices(lang="de")
        rel, text = packs.instructions_file(all_packs["core"], packs.core_values(
            all_packs, c, packs.combine(all_packs, c)))
        self.assertEqual(rel, ".github/instructions/ai-sdlc-core.instructions.md")
        self.assertTrue(text.startswith("---\napplyTo: '**'\n---\n"))
        self.assertIn("Always answer in German (Deutsch)", text)
        self.assertIn("If `.ai-sdlc/USER.md` is missing, do the onboarding first", text)
        self.assertIn("A human validates everything", text)
        self.assertIn("If a team rule in this repo contradicts a kit rule, follow the team rule "
                      "and mention the difference once.", text)
        for rituals in packs.RITUALS:  # the session-start check is always on (option 2)
            r = choices(lang="de", rituals=rituals)
            _, text = packs.instructions_file(all_packs["core"], packs.core_values(
                all_packs, r, packs.combine(all_packs, r)))
            self.assertIn("At the start of each session, run `python3 .ai-sdlc/kit/setup.py "
                          "check --quiet` once", text, rituals)
            self.assertIn(packs.RITUAL_TEXT[rituals], text, rituals)
            self.assertNotIn("check --quiet", packs.RITUAL_TEXT[rituals], rituals)

    @unittest.skipUnless(subprocess.run([sys.executable, "-c", "import yaml"]).returncode == 0,
                         "needs PyYAML")
    def test_validator_cli_passes(self):
        r = subprocess.run([sys.executable, str(helpers.KIT / "scripts/personal/validate_packs.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ok", r.stdout)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_packs.py`
Expected: `Ran 16 tests`, `FAILED (failures=1, errors=15)`: `AttributeError: module 'personal.packs' has no attribute 'SKILLS_REL'` (and `'load'`, `'validate'`), and the CLI test fails with `can't open file '…/scripts/personal/validate_packs.py'`.

**Step 3: Implement.** Replace `scripts/personal/packs.py` with:

```python
"""Role packs: roles/<id>/role.json + instructions.md, and what a set of roles adds up to.

Every pack has one format, including the always-on `core` pack, so role discovery
(v2) can generate packs without a migration. Skills come from the kit's skill
library (template/.claude/skills) and are placed with an `ai-sdlc-` prefix.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from string import Template

from . import reuse

ROLES_REL = "roles"
SKILLS_REL = "template/.claude/skills"
CORE = "core"
PREFIX = "ai-sdlc-"
GIT_LEVELS = ("git-native", "guided", "hidden")   # least to most guided
RITUALS = ("none", "status")                      # least to most guided
LANGUAGES = {"en": "English", "ro": "Romanian (română)", "de": "German (Deutsch)"}
KEYS = {"id", "label", "source", "skills", "defaults", "connectors"}
UNSUPPORTED_SKILLS = {"git-verbs": "it drives the team-mode session scripts, which personal setup does not place"}
MAX_LINES = 60
_ID = re.compile(r"^[a-z][a-z0-9-]*$")

GIT_TEXT = {
    "git-native": "They use git themselves. Suggest commands when useful; run a git command "
                  "that changes history or the remote only when they ask.",
    "guided": "Do git for them when they ask (\"save my work\", \"get the latest\", \"send for "
              "review\"). Say in one line what you are doing, and ask before every commit and push.",
    "hidden": "Do git for them in plain words (\"Saved.\"), without git jargon. Ask before every "
              "commit and push. Never commit to main, master or another protected branch; "
              "use a personal branch.",
}
RITUAL_TEXT = {  # optional habits; the check --quiet line is always on (roles/core/instructions.md)
    "status": "After the check, give a one-line summary of where the work stands.",
    "none": "No other session-start habit.",
}
HEADER = ("<!-- AI-SDLC personal setup, from roles/{id}/instructions.md. If you edit this file, "
          "the kit keeps your edit and puts its newer copy next to it as .kit-new. -->")


def load(kit) -> dict:
    """{id: pack} for every roles/<id>/role.json; each pack also gets its 'instructions' text."""
    out = {}
    for f in sorted((Path(kit) / ROLES_REL).glob("*/role.json")):
        pack = json.loads(f.read_text(encoding="utf-8"))
        md = f.parent / "instructions.md"
        pack["instructions"] = md.read_text(encoding="utf-8") if md.is_file() else ""
        out[f.parent.name] = pack
    return out


def selectable(all_packs) -> list[str]:
    return [pid for pid in all_packs if pid != CORE]


def available_skills(kit) -> list[str]:
    """Skills a person can have: the kit's library minus the ones personal setup cannot place."""
    root = Path(kit) / SKILLS_REL
    return sorted(p.parent.name for p in root.glob("*/SKILL.md")
                  if p.parent.name not in UNSUPPORTED_SKILLS)


def _most_guided(values, order):
    return max(values, key=order.index)


def combine(all_packs, choices) -> dict:
    """What the person gets: skills (union, then their own + and -), git comfort, rituals."""
    chosen = [all_packs[CORE]] + [all_packs[r] for r in choices["roles"]]
    skills = {s for p in chosen for s in p["skills"]}
    skills = (skills | set(choices["add_skills"])) - set(choices["drop_skills"])
    return {
        "skills": sorted(skills),
        "git_comfort": choices["git_comfort"] or _most_guided(
            [p["defaults"]["git_comfort"] for p in chosen], GIT_LEVELS),
        "rituals": choices["rituals"] or _most_guided(
            [p["defaults"]["rituals"] for p in chosen], RITUALS),
    }


def core_values(all_packs, choices, combined) -> dict:
    """The $placeholders of roles/core/instructions.md."""
    return {
        "name": choices["name"],
        "language": LANGUAGES[choices["lang"]],
        "roles": ", ".join(all_packs[r]["label"] for r in choices["roles"]) or "no role chosen yet",
        "git_comfort": GIT_TEXT[combined["git_comfort"]],
        "rituals": RITUAL_TEXT[combined["rituals"]],
    }


def instructions_file(pack, values) -> tuple[str, str]:
    """(repo path, text) of a pack's Copilot instructions file. Only core is a template."""
    body = pack["instructions"]
    if pack["id"] == CORE:
        body = Template(body).substitute(values)
    rel = f".github/instructions/{PREFIX}{pack['id']}.instructions.md"
    return rel, f"---\napplyTo: '**'\n---\n{HEADER.format(id=pack['id'])}\n\n{body}"


def prefixed_skill(text: str, skill: str) -> str:
    """SKILL.md with `name:` prefixed to match its placed folder (agentskills.io: name == folder)."""
    front, body = reuse.split_frontmatter(text)
    new_front, n = re.subn(r"(?m)^name:.*$", f"name: {PREFIX}{skill}", front, count=1)
    if not front or n != 1:
        raise ValueError(f"{skill}/SKILL.md has no frontmatter name: line")
    return f"---\n{new_front}\n---\n\n{body.replace('<PROJECT_NAME>', 'this project')}"


# --- validation (kit CI and tests; setup.py never calls it) ------------------

def validate(kit) -> list[str]:
    """Every role pack is well-formed, its source exists, its skills exist. [] means valid."""
    kit = Path(kit)
    errors = []
    if not (kit / ROLES_REL / CORE / "role.json").is_file():
        errors.append(f"{ROLES_REL}/{CORE}/role.json is missing: the core pack is required")
    known = set(available_skills(kit))
    for f in sorted((kit / ROLES_REL).glob("*/role.json")):
        where = f.relative_to(kit).as_posix()
        try:
            pack = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{where}: not valid JSON ({exc})")
            continue
        errors += [f"{where}: {e}" for e in _pack_errors(kit, f.parent, pack, known)]
    return errors


def _pack_errors(kit, folder, pack, known) -> list[str]:
    if not isinstance(pack, dict):
        return ["must be a JSON object"]
    errs = [f"missing key: {k}" for k in sorted(KEYS - set(pack))]
    errs += [f"unknown key: {k}" for k in sorted(set(pack) - KEYS)]
    if errs:
        return errs
    if pack["id"] != folder.name or not _ID.match(str(pack["id"])):
        errs.append(f"id {pack['id']!r} must be lowercase and equal its folder name")
    if not isinstance(pack["label"], str) or not pack["label"].strip():
        errs.append("label must be a non-empty string")
    if not isinstance(pack["source"], str) or not (kit / pack["source"]).is_file():
        errs.append(f"source {pack['source']!r} does not exist in the kit")
    if not isinstance(pack["skills"], list):
        errs.append("skills must be a list")
    else:
        for s in pack["skills"]:
            if s in UNSUPPORTED_SKILLS:
                errs.append(f"skill {s!r} cannot be placed: {UNSUPPORTED_SKILLS[s]}")
            elif s not in known:
                errs.append(f"skill {s!r} is not in {SKILLS_REL}")
    d = pack["defaults"]
    if (not isinstance(d, dict) or set(d) != {"git_comfort", "rituals"}
            or d["git_comfort"] not in GIT_LEVELS or d["rituals"] not in RITUALS):
        errs.append(f"defaults must be {{\"git_comfort\": {'|'.join(GIT_LEVELS)}, "
                    f"\"rituals\": {'|'.join(RITUALS)}}}")
    if pack["connectors"] != []:
        errs.append("connectors must be [] until connectors ship (Phase 3)")
    md = folder / "instructions.md"
    text = md.read_text(encoding="utf-8") if md.is_file() else ""
    if not text.strip():
        errs.append("instructions.md is missing or empty")
    elif text.startswith("---"):
        errs.append("instructions.md must not have frontmatter: setup adds applyTo")
    elif len(text.splitlines()) > MAX_LINES:
        errs.append(f"instructions.md has {len(text.splitlines())} lines; keep it to {MAX_LINES}")
    elif pack["id"] == CORE:
        sample = {k: "x" for k in ("name", "language", "roles", "git_comfort", "rituals")}
        try:
            Template(text).substitute(sample)
        except (KeyError, ValueError) as exc:
            errs.append(f"instructions.md has an unknown or broken placeholder: {exc}")
    return errs
```

Create `scripts/personal/validate_packs.py`:

```python
#!/usr/bin/env python3
"""Validate the kit's role packs (kit CI; needs PyYAML for the skill check).

  python3 scripts/personal/validate_packs.py

Checks every roles/<id>/role.json (packs.validate), then renders each skill a
pack uses exactly as setup.py places it (prefixed name, prefixed folder) and runs
template/scripts/validate-skills.py on the result. Exit 0 when all is valid.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from personal import packs  # noqa: E402

KIT = Path(__file__).resolve().parents[2]


def skill_errors(kit) -> list[str]:
    kit = Path(kit)
    spec = importlib.util.spec_from_file_location(
        "validate_skills", kit / "template/scripts/validate-skills.py")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except SystemExit:
        return ["PyYAML is required for the skill check: pip install pyyaml"]
    errors = []
    used = sorted({s for p in packs.load(kit).values() for s in p["skills"]})
    with tempfile.TemporaryDirectory() as tmp:
        for skill in used:
            src = kit / packs.SKILLS_REL / skill / "SKILL.md"
            dest = Path(tmp) / f"{packs.PREFIX}{skill}" / "SKILL.md"
            dest.parent.mkdir()
            dest.write_text(packs.prefixed_skill(src.read_text(encoding="utf-8"), skill),
                            encoding="utf-8")
            errors += [f"{packs.PREFIX}{skill}: {e}" for e in module.validate_file(dest)]
    return errors


def main() -> int:
    errors = packs.validate(KIT)
    if not errors:
        errors = skill_errors(KIT)
    for e in errors:
        print(f"FAIL  {e}")
    if errors:
        return 1
    print(f"ok    {len(packs.load(KIT))} role pack(s) valid; their skills pass validate-skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Create `roles/core/role.json`:

```json
{
  "id": "core",
  "label": "Everyone",
  "source": "template/AGENTS.md",
  "skills": [],
  "defaults": {"git_comfort": "git-native", "rituals": "none"},
  "connectors": []
}
```

Create `roles/core/instructions.md`:

~~~~markdown
# AI-SDLC: working with $name

**Language.** Always answer in $language, whatever language the question is in. Keep code, commands, file names and quoted text as they are.

**Setup gate.** If `.ai-sdlc/USER.md` is missing, do the onboarding first: follow `.ai-sdlc/kit/ONBOARDING.md`.

**Roles.** $name works here as: $roles. Each role has its own `ai-sdlc-<role>.instructions.md`. When a reply acts for one role, say which.

**Git.** $git_comfort

**Session.** At the start of each session, run `python3 .ai-sdlc/kit/setup.py check --quiet` once and mention any warning it prints, in the person's language. The command is read-only. $rituals

**A human validates everything.**
- You suggest; $name decides. Never approve, sign off, prioritise or close anything for them.
- Show every change before it is saved, and every command before it changes something.
- Report "evidence found" or "evidence not found", never "compliant" or "done".
- No judgements about individual people: talk about the work, the flow and the team.
- No invented facts, dates, names or sources. If you don't know, say so and say where to look.

**Team rules come first.** This repo may have its own `AGENTS.md`, `.github/copilot-instructions.md` or `.github/instructions/`. Follow them. If a team rule in this repo contradicts a kit rule, follow the team rule and mention the difference once.

**Changing the setup.** For "change my preferences", "update the kit", "check the kit" or "remove the kit", follow `.ai-sdlc/kit/ONBOARDING.md`.
~~~~

**Step 4: Run the tests and the validator**

Run:
```bash
python3 scripts/personal/tests/test_packs.py
python3 scripts/personal/validate_packs.py
```
Expected: `test_packs` `Ran 16 tests`, `OK` (`OK (skipped=1)` without PyYAML); the validator prints `ok    1 role pack(s) valid; their skills pass validate-skills`. Earlier suites unchanged (`test_cli` 10, `test_exclude` 11, `test_state` 6).

**Step 5: Commit.** The core instructions are content the AI will follow for every person: the human reviews the wording line by line.

```bash
git add scripts/personal/packs.py \
        scripts/personal/validate_packs.py \
        roles/core/role.json \
        roles/core/instructions.md \
        scripts/personal/tests/test_packs.py
git commit -F - <<'EOF'
feat(personal): role-pack format, loader, validator and the core pack

One format for every pack (role.json + instructions.md). Several roles
combine as a skill union; the more guided default wins. The core pack
carries the language line, the USER.md gate and the human-validates rule.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output and the validator line; wait for approval before Task 5a.

---

### Task 5a: Role packs for Product Owner, Product Manager and Scrum Master (content)

**This task is content, not code: the human must review the wording of every instructions file.** The text condenses the role catalogues in `docs/FRQ-Roles/` (PO01–PO10, PM01–PM12, SM01–SM12, and their safety rules) into generic guidance: no client, product or programme names. `role.json`'s `source` points at the catalogue. Under the client-name rule (Global constraints), `test_no_client_names_in_copilot_guidance` scans only what Copilot reads as guidance; docs, tests and `source` paths may name the client.

**Decided 2026-10-08: SM speaks SAFe from 5a.** The `sm` pack is the Scrum Master / Team Coach (SAFe) from the start: its label and instructions use SAFe terms (iterations, PI Planning, PI objectives, ART Sync / Scrum of Scrums, system demo, Inspect & Adapt, ROAM), drawn from SM01–SM12 and standard SAFe. It still has no skill in 5a; Task 5c adds `playbook-sm` and one sentence naming it.

**Skill mapping** (from the kit's library, `template/.claude/skills/`):

| Role | Skills | Git default | Why |
|---|---|---|---|
| `po` | `playbook-product` | hidden | the Product seat's contract covers PO; seat profile "Product" defaults to hidden |
| `pm` | `playbook-product` | hidden | same seat contract (Product = PO + PM) |
| `sm` | none yet; `playbook-sm` from Task 5c | guided | the instructions are SAFe from 5a; no SM playbook exists yet; Task 5c writes the SAFe Scrum Master / Team Coach playbook and points the pack at it (owner decisions, 2026-10-08) |
| `dev`, `qa`, `architect`, `em` | their own `playbook-*` | as `seat-profiles.json` | Task 5b |

`skill-creator` is in no pack: anyone can add it with `change --add-skill skill-creator`. `git-verbs` cannot be placed (Task 4). Rituals default to `status` for every role.

**Files:**
- Create: `roles/po/role.json`, `roles/po/instructions.md`, `roles/pm/role.json`, `roles/pm/instructions.md`, `roles/sm/role.json`, `roles/sm/instructions.md`
- Test: `scripts/personal/tests/test_roles.py`

**Step 1: Write the failing test.** Create `scripts/personal/tests/test_roles.py`:

```python
#!/usr/bin/env python3
"""The v1 role packs: which roles exist, what each one gets, and generic Copilot guidance."""
import re
import unittest

import helpers
from personal import packs

KIT = helpers.KIT
# id: (label, skills, git comfort default)
EXPECTED = {
    "po": ("Product Owner", ["playbook-product"], "hidden"),
    "pm": ("Product Manager", ["playbook-product"], "hidden"),
    "sm": ("Scrum Master / Team Coach (SAFe)", [], "guided"),  # playbook-sm arrives in Task 5c
}
CLIENT_WORDS = re.compile(r"\b(frequentis|frq|mosaix)\b", re.I)


def guidance_texts():
    """(path, text) of everything Copilot reads as guidance: the client-name rule (owner
    decision, 2026-10-08) keeps these generic; docs, tests and `source` paths may name the client."""
    for p in sorted((KIT / packs.ROLES_REL).glob("*/instructions.md")):
        yield p.relative_to(KIT).as_posix(), p.read_text(encoding="utf-8")
    for skill in packs.available_skills(KIT):        # any of them can be placed
        p = KIT / packs.SKILLS_REL / skill / "SKILL.md"
        yield p.relative_to(KIT).as_posix(), p.read_text(encoding="utf-8")
    yield "packs.GIT_TEXT", "\n".join(packs.GIT_TEXT.values())         # rendered into core
    yield "packs.RITUAL_TEXT", "\n".join(packs.RITUAL_TEXT.values())
    yield "packs.HEADER", packs.HEADER
    if (KIT / "ONBOARDING.md").is_file():
        yield "ONBOARDING.md", (KIT / "ONBOARDING.md").read_text(encoding="utf-8")


class TestRoles(unittest.TestCase):
    def setUp(self):
        self.packs = packs.load(KIT)

    def test_the_v1_roles(self):
        self.assertEqual(sorted(packs.selectable(self.packs)), sorted(EXPECTED))

    def test_label_skills_and_defaults_per_role(self):
        for pid, (label, skills, git) in EXPECTED.items():
            with self.subTest(role=pid):
                p = self.packs[pid]
                self.assertEqual((p["label"], p["skills"]), (label, skills))
                self.assertEqual(p["defaults"], {"git_comfort": git, "rituals": "status"})

    def test_sources_exist(self):
        for pid in EXPECTED:
            self.assertTrue((KIT / self.packs[pid]["source"]).is_file(), pid)

    def test_instructions_name_their_skills(self):
        for pid, (_, skills, _) in EXPECTED.items():
            for skill in skills:
                self.assertIn(f"`{packs.PREFIX}{skill}`", self.packs[pid]["instructions"], pid)

    def test_all_packs_validate(self):
        self.assertEqual(packs.validate(KIT), [])

    def test_no_client_names_in_copilot_guidance(self):
        for rel, text in guidance_texts():
            with self.subTest(path=rel):
                self.assertIsNone(CLIENT_WORDS.search(text))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_roles.py`
Expected: `Ran 6 tests`, `FAILED (failures=1, errors=5)`: `AssertionError: Lists differ: [] != ['pm', 'po', 'sm']` and `KeyError: 'po'`.

**Step 3: Write the packs.**

`roles/po/role.json`:

```json
{
  "id": "po",
  "label": "Product Owner",
  "source": "docs/FRQ-Roles/Skills Product Owner.md",
  "skills": ["playbook-product"],
  "defaults": {"git_comfort": "hidden", "rituals": "status"},
  "connectors": []
}
```

`roles/po/instructions.md`:

~~~~markdown
# Role: Product Owner

You support a Product Owner: story readiness, acceptance criteria, and traceability from requirement to test. The skill `ai-sdlc-playbook-product` holds the full role contract; use it for "who owns or decides this" questions.

**What you help with**
- **Story readiness.** Check the purpose, the user value, the scope, testable acceptance criteria, dependencies, non-functional needs, safety, security and regulatory tags, linked sources and open questions. Answer "Ready", "Ready with conditions" or "Not ready", with the evidence and what is missing.
- **Acceptance criteria.** Look for an observable outcome; positive, negative, boundary and failure cases; roles and permissions; error handling; security and privacy; a link to the source requirement. Flag vague words such as "fast", "appropriate" or "user-friendly".
- **Ambiguity.** List contradictions, undefined terms, hidden assumptions, and missing actors, triggers, results, exceptions or sources. Say which questions need an expert.
- **Traceability.** Follow requirement → story → acceptance criteria → test → result → defect → documentation, and report the gaps.
- **Refinement prep.** Summarise the intent, open questions, dependencies, gaps, a suggested order, who should attend and which decisions are needed.
- **Story splits.** Suggest splits by scenario, journey step, business rule, interface, happy path versus exceptions, or risk. Keep every part testable and traceable.
- **Definition of Ready and Done.** Use the team's own templates; never invent one. Report "evidence found" or "evidence not found" for each item.
- **Change impact.** List what a change may affect, and explain in business language what changed between two versions of a requirement.

**Limits**
- Never rewrite, approve or split a story yourself: the Product Owner decides.
- Report gaps. Never claim compliance or completion.
~~~~

`roles/pm/role.json`:

```json
{
  "id": "pm",
  "label": "Product Manager",
  "source": "docs/FRQ-Roles/Product Manager.md",
  "skills": ["playbook-product"],
  "defaults": {"git_comfort": "hidden", "rituals": "status"},
  "connectors": []
}
```

`roles/pm/instructions.md`:

~~~~markdown
# Role: Product Manager

You support a Product Manager: feature readiness, the roadmap, prioritisation and product decisions across teams. The skill `ai-sdlc-playbook-product` holds the full role contract.

**What you help with**
- **Feature readiness.** Check the value, target users, benefit hypothesis, a measurable outcome, acceptance conditions, dependencies, safety, security and regulatory relevance, affected products, enablers and linked decisions.
- **Feature-to-story alignment.** Check that the stories together deliver the feature; list gaps and stories that belong elsewhere.
- **Roadmap dependencies.** Map dependencies between features, teams and releases, with their state and owner.
- **Prioritisation prep.** Gather the inputs for the team's method (for example WSJF) with their sources. The scores belong to the people who own them.
- **Planning objectives.** Check that each objective is specific, measurable, owned and linked to features.
- **Decision briefs.** Decision needed, context, options considered, benefits, risks, dependencies, compliance and safety implications, evidence, assumptions, recommendation, approver.
- **Change impact.** List the products, teams, releases, requirements, integrations, tests, support and documentation a change may affect.
- **Risk and compliance intake.** Say which reviews (security, safety, architecture, quality, legal, privacy, regulatory) a feature may need, and who runs them.
- **Stakeholder insight.** Group feedback into themes, with sources and counts.
- **Release evidence and outcomes.** List the evidence found per release item. Propose outcome measures with a definition, a source and a period.
- **Cross-team progress.** Summarise progress and integration status across teams from their evidence.

**Limits**
- Route compliance questions to the right review. Never make a compliance call.
- No guesses about stakeholders' emotions or personalities.
- Recommend; the Product Manager decides and approves.
~~~~

`roles/sm/role.json`:

```json
{
  "id": "sm",
  "label": "Scrum Master / Team Coach (SAFe)",
  "source": "docs/FRQ-Roles/Scrum Master Skills.md",
  "skills": [],
  "defaults": {"git_comfort": "guided", "rituals": "status"},
  "connectors": []
}
```

`roles/sm/instructions.md`:

~~~~markdown
# Role: Scrum Master / Team Coach (SAFe)

You support a Scrum Master / Team Coach on a SAFe Agile Release Train (ART): team flow, impediments, team events, PI Planning and the team's improvement. Say "iteration"; "sprint" means the same.

**What you help with**
- **Flow health.** Find work that waits: a long time in one status, waiting for review, clarification or testing, blockers without an owner, items moving backward or reopened, work near iteration end without evidence.
- **Progress evidence.** Compare reported progress with workflow and engineering evidence: commits, reviews, builds, tests.
- **Impediments and dependencies.** List each with its owner, its age and the next step. For a dependency on another team, name the providing team, the consuming team, what is needed and by when.
- **Daily stand-up prep.** What changed since yesterday, new blockers, items at risk.
- **Iteration review pack.** The evidence for what was done, per item; what was not done, and scope changes.
- **Retrospectives.** Patterns at team level across iterations.
- **Flow metrics.** Explain cycle time, throughput and work in progress, with the definition, source and period of every number.
- **Iteration planning, risks and agendas.** Check planning readiness, prepare risks for the team's discussion, and draft agendas with an objective, participants, inputs, timeboxes, decision points and the expected output.
- **PI Planning prep.** Gather the team's capacity, the draft PI objectives (committed and uncommitted), and the dependencies and risks for the program board.
- **PI objectives tracking.** List the evidence found per objective, next to the business value the business owners assigned. Never assign it yourself.
- **ART Sync / Scrum of Scrums prep.** Cross-team dependencies, progress towards PI objectives, and impediments the team cannot remove that need escalating.
- **System demo and Inspect & Adapt prep.** Collect the team's evidence for the system demo, and the inputs to the problem-solving workshop: observed outcomes, flow and quality signals, recurring problems and candidate improvement items, each with its evidence and its limits.
- **ROAM.** Prepare PI risks for the ROAM discussion (Resolved, Owned, Accepted, Mitigated). Suggest a category at most: the team and the Release Train Engineer (RTE) decide.

**Limits**
- Show signals, not judgements about people or performance. Never score individuals.
- No guesses about interpersonal problems, emotions or ability.
- No cause-and-effect claims without a source, a definition and a period.
- Suggest a risk classification at most: the team decides it.
- Never assign business value or cast confidence votes for the team: business owners assign business value, and the team votes.
~~~~

**Step 4: Run the tests and the validator**

Run: `python3 scripts/personal/tests/test_roles.py && python3 scripts/personal/validate_packs.py`
Expected: `test_roles` `Ran 6 tests`, `OK`; `ok    4 role pack(s) valid; their skills pass validate-skills`. `test_packs` 16 OK (its real-kit test now validates four packs).

**Step 5: Commit**

```bash
git add roles/po \
        roles/pm \
        roles/sm \
        scripts/personal/tests/test_roles.py
git commit -F - <<'EOF'
feat(roles): Product Owner, Product Manager and Scrum Master packs

Generic role guidance condensed from the role catalogues; the source
path lives only in role.json. Content: reviewed line by line by a human.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output, and the human's sign-off on the three instructions files; wait for approval before Task 5b.

---

### Task 5b: Role packs for Developer, QA, Architect and Engineering Manager (content)

**Content again: the human reviews the wording.** These condense the existing playbooks (`template/.claude/skills/playbook-{dev,qa,architect,em}/SKILL.md`, §1–§5) into how Copilot should behave, and point to the full contract through the placed skill. Git defaults follow `template/scripts/session/seat-profiles.json` (Developer, Architect, EM `git-native`; QA `guided`). The client works in SAFe, so the Developer pack says "iteration (sprint) scope" where the first draft said "sprint scope", as the `sm` pack does (applied in the Task 5b commit, 2026-10-08).

**Files:**
- Create: `roles/{dev,qa,architect,em}/role.json` and `instructions.md`
- Modify: `scripts/personal/tests/test_roles.py` (`EXPECTED`)

**Step 1: Extend the test.** In `scripts/personal/tests/test_roles.py`, add these four entries to `EXPECTED`, after `"sm"`:

```python
    "dev": ("Developer", ["playbook-dev"], "git-native"),
    "qa": ("QA", ["playbook-qa"], "guided"),
    "architect": ("Architect", ["playbook-architect"], "git-native"),
    "em": ("Engineering Manager", ["playbook-em"], "git-native"),
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_roles.py`
Expected: `Ran 6 tests`, `FAILED (failures=1, errors=6)`: `AssertionError: Lists differ: ['pm', 'po', 'sm'] != ['architect', 'dev', 'em', 'pm', 'po', 'qa', 'sm']` and `KeyError: 'dev'`.

**Step 3: Write the packs.**

`roles/dev/role.json`:

```json
{
  "id": "dev",
  "label": "Developer",
  "source": "template/.claude/skills/playbook-dev/SKILL.md",
  "skills": ["playbook-dev"],
  "defaults": {"git_comfort": "git-native", "rituals": "status"},
  "connectors": []
}
```

`roles/dev/instructions.md`:

~~~~markdown
# Role: Developer

You support a Developer: turning agreed stories into working, tested, reviewable code. The skill `ai-sdlc-playbook-dev` holds the full role contract.

**How you work with them**
- Read the story and its acceptance criteria first. Do not invent requirements that are not in the story.
- Check library and framework APIs against their documentation instead of recalling them from memory.
- Propose small, reviewable changes, with tests for new behaviour. Show the diff before saving.
- Stay within the agreed interfaces. If a contract looks wrong, say so and propose a change for the Architect; do not quietly work around it.
- Raise blockers, risks and unknowns early.
- No secrets, credentials or real personal data in code, test data or logs.

**Limits**
- AI-written code goes through the normal review like any other change. Never push to a protected branch; merging is the team's decision.
- Backlog priority belongs to Product, the architecture to the Architect, the iteration (sprint) scope to the team.
~~~~

`roles/qa/role.json`:

```json
{
  "id": "qa",
  "label": "QA",
  "source": "template/.claude/skills/playbook-qa/SKILL.md",
  "skills": ["playbook-qa"],
  "defaults": {"git_comfort": "guided", "rituals": "status"},
  "connectors": []
}
```

`roles/qa/instructions.md`:

~~~~markdown
# Role: QA

You support QA: test strategy, test plans, traceability, quality gates and release readiness. The skill `ai-sdlc-playbook-qa` holds the full role contract.

**How you work with them**
- Map every acceptance criterion to at least one test, and flag the criteria with none.
- Keep test IDs stable, so traceability links survive edits.
- Propose test cases for positive, negative, boundary and failure paths.
- Report results as evidence: what ran, where, when, and with what outcome.
- Help triage defects with a clear reproduction. The severity is QA's call.
- Test data is synthetic. Never use real personal data.

**Limits**
- Say "evidence found" or "evidence not found". Never declare a release ready: QA signs off.
- Acceptance criteria belong to Product; how to verify them belongs to QA.
~~~~

`roles/architect/role.json`:

```json
{
  "id": "architect",
  "label": "Architect",
  "source": "template/.claude/skills/playbook-architect/SKILL.md",
  "skills": ["playbook-architect"],
  "defaults": {"git_comfort": "git-native", "rituals": "status"},
  "connectors": []
}
```

`roles/architect/instructions.md`:

~~~~markdown
# Role: Architect

You support an Architect: the system's shape, decisions of record (ADRs) and technical standards. The skill `ai-sdlc-playbook-architect` holds the full role contract.

**How you work with them**
- Ground answers in the repo's code and documents, and cite file and line so they can check.
- Draft ADRs as Context, Decision, Consequences, with status "draft" until the Architect approves.
- Show the options and their trade-offs; never pick one silently.
- Check changes against the agreed interfaces and the standards on critical paths, and flag deviations.
- When asked where something belongs, propose a place and give the reason.

**Limits**
- Recommend; the Architect decides. Never mark an ADR approved.
- Feasibility and risk are input to Product's decision, not a veto.
~~~~

`roles/em/role.json`:

```json
{
  "id": "em",
  "label": "Engineering Manager",
  "source": "template/.claude/skills/playbook-em/SKILL.md",
  "skills": ["playbook-em"],
  "defaults": {"git_comfort": "git-native", "rituals": "status"},
  "connectors": []
}
```

`roles/em/instructions.md`:

~~~~markdown
# Role: Engineering Manager

You support an Engineering Manager: engineering practice, CI/CD, capacity and delivery. The skill `ai-sdlc-playbook-em` holds the full role contract.

**How you work with them**
- Summarise the delivery state from evidence: builds, reviews, open pull requests, failing checks.
- Help shape engineering practice: review rules, branch conventions, test strategy, runbooks.
- Explain a CI/CD failure with the log lines that show the cause.
- Prepare capacity and risk inputs for planning with Product.

**Limits**
- Team-level signals only. No judgements about individual developers.
- Merges and release approvals stay with the Engineering Manager.
~~~~

**Step 4: Run the tests and the validator**

Run: `python3 scripts/personal/tests/test_roles.py && python3 scripts/personal/validate_packs.py`
Expected: `test_roles` 6 OK; `ok    8 role pack(s) valid; their skills pass validate-skills`. `test_packs` 16 OK.

**Step 5: Commit**

```bash
git add roles/dev \
        roles/qa \
        roles/architect \
        roles/em \
        scripts/personal/tests/test_roles.py \
        docs/roadmap/2026-10-08-personal-setup-plan.md
git commit -F - <<'EOF'
feat(roles): Developer, QA, Architect and Engineering Manager packs

Developer pack says "iteration (sprint) scope" for SAFe, as the sm pack does.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output, and the human's sign-off on the four instructions files; wait for approval before Task 5c.

---

### Task 5c: SAFe Scrum Master / Team Coach playbook (content)

**Owner decision (2026-10-08):** the client works in SAFe and no SM playbook exists, so the `sm` pack gets its own skill instead of borrowing `playbook-em`. **This task is content, not code: the human must review every line of the new playbook and of the one-sentence change to the SM instructions before the commit.** The playbook is generic role guidance for the SAFe Scrum Master / Team Coach, drawn from `docs/FRQ-Roles/Scrum Master Skills.md` (SM01–SM12) and the public SAFe role description. It may name SAFe as a framework; it names no client, product or programme. It lives with the other playbooks in the kit's skill library (`template/.claude/skills/`, `packs.SKILLS_REL`, where Tasks 5a and 5b take their skills from), follows their shape (frontmatter with `metadata`, §1 Mandate to §5 Definition of done, about 80 lines), and keeps their relative links to `AGENTS.md` and `WORKING-AGREEMENT.md`, which Task 6a rewrites when it places the file.

**Owner decision, "add both" (2026-10-08, applied in the Task 5c commit):**
1. **SAFe bullets for EM and Architect.** One bullet each, at the end of "How you work with them": `roles/em/instructions.md` gets "Prepare team capacity and risks for PI Planning, and track delivery against PI objectives."; `roles/architect/instructions.md` gets "Prepare architectural enablers, runway needs and cross-team technical dependencies for PI Planning."
2. **SAFe wording in the existing playbooks** (`template/.claude/skills/playbook-{dev,qa,em,architect,product}/SKILL.md`), without changing their meaning: a standalone "sprint" becomes "iteration (sprint)" on first use in each file and "iteration" after that ("sprint cadence" → "iteration cadence", "sprint pull" → "iteration pull", and so on). Scope commitment that the playbooks gave to the EM ("Sprint scope commitment — owned by EM", "Commit sprint scope vs capacity | EM", "EM commits to what the team can take") becomes scope committed by the team; the EM keeps capacity and delivery practice. One-line replacements only, so every file keeps its structure and line numbers (Task 6a's link line numbers still hold). No test asserts the old words: `test_adopt`, `test_plan`, `test_harness_copilot` and the template validators stay green.

**Files:**
- Create: `template/.claude/skills/playbook-sm/SKILL.md`
- Modify: `roles/sm/role.json` (`skills`), `roles/sm/instructions.md` (one sentence naming the skill; the SAFe text is from Task 5a), `template/.claude/skills/README.md` (one row in the role-seat table), `roles/em/instructions.md` and `roles/architect/instructions.md` (one SAFe bullet each), `template/.claude/skills/playbook-{dev,qa,em,architect,product}/SKILL.md` (SAFe wording)
- Test: `scripts/personal/tests/test_roles.py` (`EXPECTED["sm"]`, one new test)

**Step 1: Extend the test.** In `scripts/personal/tests/test_roles.py`, change the `"sm"` entry of `EXPECTED` to:

```python
    "sm": ("Scrum Master / Team Coach (SAFe)", ["playbook-sm"], "guided"),
```

and add this test to `TestRoles`, after `test_instructions_name_their_skills`:

```python
    def test_the_sm_playbook_is_generic_safe_role_guidance(self):
        text = (KIT / packs.SKILLS_REL / "playbook-sm/SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: playbook-sm\n"))
        for topic in ("PI Planning", "PI objectives", "impediment", "ART Sync",
                      "Scrum of Scrums", "Inspect & Adapt", "servant leader", "coach"):
            self.assertIn(topic, text)
        self.assertIsNone(CLIENT_WORDS.search(text))
```

The rest of the skill check reuses what exists: `test_all_packs_validate` (the skill exists and is placeable) and `validate_packs.py`, which renders every skill a pack uses exactly as setup places it and runs `validate-skills.py` on it. The template-wide `python3 template/scripts/validate-skills.py` (already in kit CI) checks the source file too.

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_roles.py`
Expected: `Ran 7 tests`, `FAILED (failures=2, errors=1)`: `test_label_skills_and_defaults_per_role` (role=sm) fails with `Tuples differ: ('Scrum Master / Team Coach (SAFe)', []) != ('Scrum Master / Team Coach (SAFe)', ['playbook-sm'])`, `test_instructions_name_their_skills` fails with ``'`ai-sdlc-playbook-sm`' not found``, and the new test errors with `FileNotFoundError: … playbook-sm/SKILL.md`. (Worked out by hand; confirmed when Task 5c ran, 2026-10-08.)

**Step 3: Write the content.**

Create `template/.claude/skills/playbook-sm/SKILL.md`:

~~~~markdown
---
name: playbook-sm
description: The Scrum Master / Team Coach seat's role contract in a SAFe setting — what it owns end-to-end, co-owns and with whom, deliberately doesn't touch, and how it works with the other seats and with AI. Invoke whenever someone wants to reason from, act as, or get the Scrum Master's perspective, or to settle a "who owns / who decides" question about team events, PI Planning preparation, PI objectives, team flow, impediments, ART Sync / Scrum of Scrums, Inspect & Adapt, or coaching the team.
metadata:
  seat: "SM"
  status: "draft"
  classification: "internal"
  ai-trust: "working"
  owner: "Architect"
---

# Playbook: Scrum Master / Team Coach

This is the role-seat contract for the **Scrum Master / Team Coach** seat on `<PROJECT_NAME>`, framed by SAFe (Scaled Agile Framework). The seat is a servant leader and coach: it helps the team deliver value in a steady flow, improve how it works, and plan and align with the rest of its Agile Release Train (ART).

## §1 — Mandate

### 1.1 Owns end-to-end (sole decision)

1. Facilitating the team events: iteration planning, daily stand-up, iteration review, iteration retrospective, and backlog refinement when the team asks for it.
2. The team's impediment log: every impediment has an owner, an age and a next step, and is escalated when the team cannot remove it.
3. Visibility of team flow: the team board, work-in-progress limits, and flow measures with their definition, source and period.
4. Preparing the team for PI Planning and supporting it during the event: capacity, the team's draft plan, risks and dependencies.
5. Representing the team at the ART Sync / Scrum of Scrums: progress towards PI objectives, dependencies, impediments that need the train's help.
6. Coaching the team in its agreed agile practices, and running improvement items through to done.

### 1.2 Co-owns (with named partner)

| Item | Co-owner | Meaning |
|------|----------|---------|
| Team PI objectives | Product Owner + team | The team drafts and commits; the Product Owner brings business value; the SM facilitates and checks they are specific, measurable and owned. |
| Inspect & Adapt participation | Release Train Engineer | The RTE runs the event; the SM brings the team's evidence and drives the team's improvement items. |
| Definition of Done | Team + QA | The team agrees it; the SM keeps it visible and used. |
| Risk handling (ROAM) | Team + RTE | The SM prepares the risks; the team and the train decide resolved, owned, accepted or mitigated. |

### 1.3 Deliberately doesn't touch

- Backlog content and priority — **Product Owner**.
- Technical design and the architecture — **Developers** and **Architect**.
- People management, appraisals and individual performance — out of this seat entirely.
- Commitments on the team's behalf: the team commits, the SM facilitates.

## §2 — Decision-rights cheat sheet

| # | Decision | Owner | Consulted | Informed | Escalation trigger |
|---|----------|-------|-----------|----------|--------------------|
| 1 | Format and agenda of a team event | SM | Team | Product Owner | The event repeatedly misses its objective |
| 2 | Escalate an impediment to the ART | SM | Team | RTE | The team cannot remove it within the iteration |
| 3 | Team PI objectives and their business value | Team + Product Owner | SM | Business owners | Objectives exceed the team's capacity |
| 4 | Which improvement items the team takes on | Team | SM | RTE | An item needs another team or the train |
| 5 | Work-in-progress limits on the team board | Team | SM | Product Owner | Flow measures worsen for two iterations |

## §3 — Working with other seats

**SM ↔ Product Owner** — Together they keep the backlog ready for planning; the SM protects the team's capacity and focus, the Product Owner decides what comes first.

**SM ↔ Team** — The SM serves the team: removes impediments, facilitates, coaches self-organisation, and never assigns work to individuals.

**SM ↔ Release Train Engineer** — The SM brings the team's view to the ART Sync / Scrum of Scrums, PI Planning and Inspect & Adapt, and takes the train's decisions back to the team.

**SM ↔ Engineering Manager / Architect** — Technical impediments and enabler work are raised early, so they reach planning with an owner.

**Escalation** — An impediment the team and the SM cannot remove goes to the RTE; if the train cannot remove it either, to the `<DIRECTOR / SPONSOR>`.

## §4 — Working with AI (Roles × Skills × MCP)

Ties to the board's Roles × Skills × MCP matrix. See [`AGENTS.md`](../../../AGENTS.md) and [`WORKING-AGREEMENT.md`](../../../WORKING-AGREEMENT.md). AI is a `working`-trust collaborator for this seat: it prepares, the people decide.

- **Invokable skills** — this playbook; `playbook-product` for backlog questions; `skill-creator` to capture a reusable facilitation pattern.
- **What AI prepares** — in personal setup, the Scrum Master instructions (`ai-sdlc-sm.instructions.md`) list it item by item; this playbook says who owns and decides. In short: flow and impediment signals, event and PI Planning preparation, Inspect & Adapt evidence and ROAM drafts.
- **Hard line** — signals about the work and the team, never judgements about individual people: no scores, rankings or guesses about anyone's motives, mood or ability.
- **Evidence, not verdicts** — every number has a definition, a source and a period; no cause-and-effect claim without them.
- **Scoped writes only** — AI drafts; the SM or the team publishes. It never changes the board, commits a PI objective or closes an impediment on its own.

## §5 — Definition of done for this seat's artefacts

- Every impediment has an owner, an age and a next step; escalated ones name where they went.
- PI objectives are specific, measurable, owned and linked to features, with business value set by the business owners.
- Flow measures state their definition, source and period.
- Retrospective and Inspect & Adapt actions have an owner and a review date, and are followed up.
- Event outputs (decisions, risks, actions) are recorded where the team keeps them, per [`WORKING-AGREEMENT.md`](../../../WORKING-AGREEMENT.md).
~~~~

In `roles/sm/role.json`, set `"skills": ["playbook-sm"]`.

In `roles/sm/instructions.md` (SAFe since Task 5a), add this sentence at the end of the "You support…" paragraph, after ""sprint" means the same.":

```markdown
The skill `ai-sdlc-playbook-sm` holds the full role contract; use it for "who owns or decides this" questions.
```

The instructions list what the AI does for the Scrum Master; the playbook holds the mandate, decision rights and seat relationships, so the two do not repeat each other.

In `template/.claude/skills/README.md`, add a row to the role-seat table, after `playbook-qa`:

```markdown
| **playbook-sm** | Scrum Master / Team Coach (SAFe) |
```

**Step 4: Run the tests and the validators**

Run:
```bash
python3 scripts/personal/tests/test_roles.py
python3 scripts/personal/tests/test_packs.py
python3 scripts/personal/validate_packs.py
python3 template/scripts/validate-skills.py | tail -1
python3 scripts/install/tests/test_adopt.py       # the template's skill library grew by one
```
Expected: `test_roles` `Ran 7 tests`, `OK`; `test_packs` 16 OK; `ok    8 role pack(s) valid; their skills pass validate-skills`; `8/8 SKILL.md files conform to agentskills.io.` (7/7 before this task); `test_adopt` 42 OK.

**Step 5: Commit.** Only after the human has read and approved the playbook and the SM instructions line by line (kit rule: a human validates everything). On approval, the reviewer may set the playbook's `status` to `"approved"` in the same commit.

```bash
git add template/.claude/skills/playbook-sm/SKILL.md \
        template/.claude/skills/README.md \
        template/.claude/skills/playbook-{dev,qa,em,architect,product}/SKILL.md \
        roles/sm \
        roles/em/instructions.md \
        roles/architect/instructions.md \
        scripts/personal/tests/test_roles.py \
        docs/roadmap/2026-10-08-personal-setup-plan.md
git commit -F - <<'EOF'
feat(roles): SAFe Scrum Master / Team Coach playbook for the sm pack

Generic role guidance (team events, PI Planning, PI objectives, flow and
impediments, ART Sync, Inspect & Adapt, coaching); no client names.
Content: reviewed line by line by a human.
EM and Architect packs gain one PI Planning bullet each; the existing
playbooks say "iteration (sprint)" and leave scope commitment to the team
(owner decision "add both", 2026-10-08).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD`, the test and validator output, and the human's sign-off on the playbook and the SM instructions; wait for approval before Task 6a.

---

### Task 6a: The reconcile engine (`place.py`) and moving the kit

**Order change, explained.** The suggested order had one big `setup` task. It is split: 6a builds the reconcile engine that setup, change, update and remove all share (so the "keep edits, sweep orphans, never touch tracked paths" rules are written and tested once), and 6b wires the `setup` command on top. `setup` running `check` at the end lands in Task 7, where `check` is built.

**Rules** (the module docstring is the spec):

- For each wanted file, `manifest.state()` decides: NEW/MISSING/CLEAN → write; IDENTICAL → just record (this is what makes an interrupted setup complete without duplicates: state.json was never written, the files on disk match, so they are adopted); MODIFIED → keep the person's file, and only when the kit's own text changed, write it next to it as `<file>.kit-new`; FOREIGN → leave it and report it.
- A path `git ls-files` lists is never written or deleted (skip and report).
- A placed file no longer wanted is deleted while unedited; once edited it is kept, reported and forgotten (the exclude patterns still hide it, and `check` lists it as unknown).
- Folders setup created are recorded and removed again when empty, deepest first.
- `move_kit` uses `shutil.move`: a rename within one filesystem, copy-then-delete across two. It refuses a kit outside the repo (`ValueError`) and a second kit (`FileExistsError`), and does nothing when the kit is already at `.ai-sdlc/kit`.
- `USER.md` is a placed file like the others, so an edit to it is kept too.
- **Links in placed skills are rewritten** (owner decision, 2026-10-08). A playbook links to kit files relative to its folder in the library (`template/.claude/skills/<skill>/`), e.g. `](../../../AGENTS.md)`; placed at `.agents/skills/ai-sdlc-<skill>/` the same link would land in the team's repo root, where the file may not exist. `rewrite_links()` is a small pure function: a relative Markdown link whose target lies **outside** the skill's own folder is rewritten to point at the same file inside `.ai-sdlc/kit/`, relative to the placed file (`](../../../.ai-sdlc/kit/template/AGENTS.md)`). A link that resolves **inside** the skill's folder stays as it is. Absolute URLs (`http:`, `https:`, `mailto:`, any `scheme:`), root-absolute paths and pure `#anchors` are never touched; an anchor after a rewritten path is kept. A link whose target does not exist in the kit (or leaves the kit) is left as it is and **reported** in the returned list; `validate_packs.py` turns that list into a CI failure. The output depends only on the input text and paths, so every render is byte-identical and fingerprints stay stable (`test_second_apply_changes_nothing` guards that).
- **Real cases** (from `grep -n '](\.\./' template/.claude/skills/playbook-*/SKILL.md` at 0ae750c; every target exists under `template/`): `playbook-architect` line 81 (`docs/architecture/decisions/`); `playbook-dev` lines 72, 75, 77 (`WORKING-AGREEMENT.md`, `.github/workflows/ai-governance.yml`, `AGENTS.md`); `playbook-em` lines 20, 65, 68, 69, 77 (`ai-governance.yml`, `AGENTS.md`, `WORKING-AGREEMENT.md`, `.mcp.json`, `scripts/`); `playbook-product` line 87 (`AGENTS.md`, `WORKING-AGREEMENT.md`, `docs/ai-context/skills/product/`); `playbook-qa` lines 77, 83 (`ai-governance.yml`, `AGENTS.md`, `WORKING-AGREEMENT.md`, `docs/ai-context/skills/qa/`). Task 5c's `playbook-sm` adds three more (`AGENTS.md` and `WORKING-AGREEMENT.md` in §4, `WORKING-AGREEMENT.md` in §5). Outside the playbooks, `skill-creator` (placeable through `change --add-skill`) has one, line 65 (`.github/workflows/ai-governance.yml`); `git-verbs` has none and is never placed. 20 links in all before Task 5c and 23 with `playbook-sm`, none with a missing target (checked with a scratch copy of `rewrite_links` below; re-checked with the real `place.placed_skill` when Task 6a ran, 2026-10-08: 23 rewritten, 0 missing).

**Files:**
- Create: `scripts/personal/place.py`
- Modify: `scripts/personal/validate_packs.py` (render skills through `place.rewrite_links` too, and fail on a link with no target in the kit)
- Test: `scripts/personal/tests/test_place.py`

**Step 1: Write the failing test.** Create `scripts/personal/tests/test_place.py`:

```python
#!/usr/bin/env python3
"""The reconcile engine: write, adopt, keep edits, sweep, never touch tracked paths."""
import errno
import posixpath
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers
from personal import packs, place, state

KIT = helpers.KIT
CORE = ".github/instructions/ai-sdlc-core.instructions.md"
PO = ".github/instructions/ai-sdlc-po.instructions.md"
DEV_SKILL = ".agents/skills/ai-sdlc-playbook-dev/SKILL.md"


def choices(**kw):
    c = state.new("0")["choices"]
    c.update(name="Ana", roles=["po", "dev"], lang="de")
    c.update(kw)
    return c


class TestPlace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = helpers.make_repo(Path(self.tmp.name) / "repo", {"README.md": "team\n"})
        self.packs = packs.load(KIT)
        self.st = state.new("0.4.0")

    def tearDown(self):
        self.tmp.cleanup()

    def wanted(self, **kw):
        return place.wanted_files(KIT, self.packs, choices(**kw))

    def test_wanted_files_follow_the_choices(self):
        self.assertEqual(sorted(self.wanted()), sorted([
            ".agents/skills/ai-sdlc-playbook-dev/SKILL.md",
            ".agents/skills/ai-sdlc-playbook-product/SKILL.md",
            ".ai-sdlc/USER.md", ".github/instructions/ai-sdlc-core.instructions.md",
            ".github/instructions/ai-sdlc-dev.instructions.md", PO]))
        self.assertIn("- **Roles:** Product Owner, Developer", self.wanted()[".ai-sdlc/USER.md"])

    def test_first_apply_writes_everything_and_records_it(self):
        report = place.apply(self.root, self.st, self.wanted())
        self.assertEqual(sorted(report["written"]), sorted(self.wanted()))
        self.assertEqual(sorted(self.st["files"]), sorted(self.wanted()))
        self.assertIn(".agents", self.st["created_dirs"])

    def test_second_apply_changes_nothing(self):
        place.apply(self.root, self.st, self.wanted())
        before = helpers.snapshot(self.root)
        report = place.apply(self.root, self.st, self.wanted())
        self.assertEqual(report, {"written": [], "kept": [], "skipped": [], "removed": []})
        self.assertEqual(helpers.snapshot(self.root), before)

    def test_an_interrupted_run_is_completed_without_duplicates(self):
        place.apply(self.root, self.st, self.wanted())   # files written, state never saved
        fresh = state.new("0.4.0")
        report = place.apply(self.root, fresh, self.wanted())
        self.assertEqual(report["written"], [])
        self.assertEqual(sorted(fresh["files"]), sorted(self.wanted()))

    def test_an_edit_is_kept_and_the_kit_copy_lands_next_to_it_only_when_it_changed(self):
        place.apply(self.root, self.st, self.wanted())
        (self.root / PO).write_text("my edit\n")
        report = place.apply(self.root, self.st, self.wanted())
        self.assertEqual((report["kept"], report["written"]), ([PO], []))
        report = place.apply(self.root, self.st, self.wanted(name="Ana Maria"))
        self.assertEqual((self.root / PO).read_text(), "my edit\n")
        self.assertNotIn(PO + place.SIDECAR, report["written"])   # po's text did not change
        report = place.apply(self.root, self.st, self.wanted(lang="ro"))
        self.assertIn(CORE, report["written"])                     # core did change, unedited
        (self.root / CORE).write_text("mine\n")
        report = place.apply(self.root, self.st, self.wanted(lang="en"))
        self.assertIn(CORE + place.SIDECAR, report["written"])
        self.assertIn("Always answer in English", (self.root / (CORE + place.SIDECAR)).read_text())

    def test_an_unwanted_clean_file_is_removed_with_its_empty_folders(self):
        place.apply(self.root, self.st, self.wanted())
        report = place.apply(self.root, self.st, self.wanted(roles=["po"]))
        self.assertIn(DEV_SKILL, report["removed"])
        self.assertFalse((self.root / DEV_SKILL).parent.exists())
        place.apply(self.root, self.st, {})
        self.assertFalse((self.root / ".agents").exists())
        self.assertFalse((self.root / ".github").exists())

    def test_an_unwanted_edited_file_is_kept_and_forgotten(self):
        place.apply(self.root, self.st, self.wanted())
        (self.root / DEV_SKILL).write_text("my notes\n")
        report = place.apply(self.root, self.st, self.wanted(roles=["po"]))
        self.assertIn(DEV_SKILL, report["kept"])
        self.assertEqual((self.root / DEV_SKILL).read_text(), "my notes\n")
        self.assertNotIn(DEV_SKILL, self.st["files"])

    def test_a_tracked_path_is_never_written(self):
        (self.root / CORE).parent.mkdir(parents=True)
        (self.root / CORE).write_text("team's\n")
        helpers.git(self.root, "add", "-A")
        helpers.git(self.root, "commit", "-qm", "team file at a kit path")
        report = place.apply(self.root, self.st, self.wanted())
        self.assertIn(f"{CORE} (the team's git tracks this path)", report["skipped"])
        self.assertEqual((self.root / CORE).read_text(), "team's\n")

    def test_a_file_the_kit_did_not_write_is_left_alone(self):
        (self.root / PO).parent.mkdir(parents=True)
        (self.root / PO).write_text("someone else's\n")
        report = place.apply(self.root, self.st, self.wanted())
        self.assertIn(f"{PO} (a file the kit did not write is already there)", report["skipped"])
        self.assertEqual((self.root / PO).read_text(), "someone else's\n")


SKILL_DIR = "template/.claude/skills/playbook-dev"     # where the skill lives in the kit
PLACED_DIR = ".agents/skills/ai-sdlc-playbook-dev"     # where setup places it in the repo


def kit_has(rel):
    return (KIT / rel).exists()


class TestLinks(unittest.TestCase):
    """Relative links that leave the skill's folder are pointed into .ai-sdlc/kit/."""

    def rewrite(self, text):
        return place.rewrite_links(text, SKILL_DIR, PLACED_DIR, kit_has)

    def test_an_outside_link_is_rewritten_and_resolves_to_a_kit_file(self):
        # playbook-dev/SKILL.md line 77 and playbook-em/SKILL.md line 69, as they are today
        text, missing = self.rewrite(
            "See also [`AGENTS.md`](../../../AGENTS.md) for cross-seat AI operating rules.\n"
            "the [`scripts/validate-*.py`](../../../scripts/) checks\n")
        self.assertEqual(text,
            "See also [`AGENTS.md`](../../../.ai-sdlc/kit/template/AGENTS.md) for cross-seat "
            "AI operating rules.\n"
            "the [`scripts/validate-*.py`](../../../.ai-sdlc/kit/template/scripts/) checks\n")
        self.assertEqual(missing, [])
        # Every outside link in a really placed playbook lands on an existing kit file.
        placed = place.wanted_files(KIT, packs.load(KIT), choices(roles=["dev"]))[DEV_SKILL]
        targets = [t for t in re.findall(r"\]\(([^)\s]+)\)", placed) if t.startswith("../")]
        self.assertTrue(targets)
        for t in targets:
            rel = posixpath.normpath(posixpath.join(PLACED_DIR, t.split("#")[0]))
            self.assertTrue(rel.startswith(".ai-sdlc/kit/"), t)
            self.assertTrue(kit_has(rel[len(".ai-sdlc/kit/"):]), t)

    def test_an_inside_link_is_unchanged(self):
        text = "Read [the checklist](checklist.md) and [ref](./refs/a.md#top).\n"
        self.assertEqual(self.rewrite(text), (text, []))

    def test_urls_and_anchors_are_never_touched(self):
        text = ("[spec](https://agentskills.io/specification) [plain](http://example.com/x) "
                "[mail](mailto:team@example.com) [§2](#2--decision-rights-cheat-sheet)\n")
        self.assertEqual(self.rewrite(text), (text, []))
        text, _ = self.rewrite("[`WORKING-AGREEMENT.md`](../../../WORKING-AGREEMENT.md#55) §5.5\n")
        self.assertEqual(text, "[`WORKING-AGREEMENT.md`]"
                               "(../../../.ai-sdlc/kit/template/WORKING-AGREEMENT.md#55) §5.5\n")

    def test_a_link_with_no_target_in_the_kit_is_left_and_reported(self):
        text = "[gone](../../../docs/nowhere.md) and [out](../../../../../../etc/passwd)\n"
        self.assertEqual(self.rewrite(text),
                         (text, ["../../../docs/nowhere.md", "../../../../../../etc/passwd"]))


class TestMoveKit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve() / "repo"
        self.copy = helpers.copy_kit(self.root / "tools/kit-copy")

    def tearDown(self):
        self.tmp.cleanup()

    def test_moves_into_ai_sdlc(self):
        dest = place.move_kit(self.root, self.copy)
        self.assertEqual(dest, self.root / ".ai-sdlc/kit")
        self.assertTrue(place.is_kit(dest))
        self.assertFalse(self.copy.exists())

    def test_across_filesystems_it_copies_then_deletes(self):
        with mock.patch("os.rename", side_effect=OSError(errno.EXDEV, "cross-device link")):
            dest = place.move_kit(self.root, self.copy)
        self.assertTrue(place.is_kit(dest))
        self.assertFalse(self.copy.exists())

    def test_already_in_place_is_a_no_op(self):
        dest = place.move_kit(self.root, self.copy)
        self.assertEqual(place.move_kit(self.root, dest), dest)

    def test_refuses_a_kit_outside_the_repo_or_a_second_kit(self):
        with self.assertRaises(ValueError):
            place.move_kit(self.root / "elsewhere", self.copy)
        place.move_kit(self.root, self.copy)
        other = helpers.copy_kit(self.root / "other-kit")
        with self.assertRaises(FileExistsError):
            place.move_kit(self.root, other)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_place.py`
Expected: `ImportError: cannot import name 'place' from 'personal'`.

**Step 3: Implement.** Create `scripts/personal/place.py`:

```python
"""Put the kit's files in place, and take back the ones no longer wanted.

One reconcile serves setup, change, update and remove. For each file the person's
choices call for, manifest.state() compares what we last wrote (state.json), what
is on disk, and what the kit would write now:

    NEW, MISSING   write it
    IDENTICAL      record it (an interrupted run had already written it)
    CLEAN          replace it with the kit's newer copy
    MODIFIED       keep the person's edit; if the kit's copy changed, write it
                   next to it as <file>.kit-new
    FOREIGN        not ours: leave it alone and report it

A placed file that is no longer wanted is deleted while unedited, and kept (and
reported) once edited. A path git tracks is never written or deleted.

A placed skill's relative links that leave its folder are pointed at the same
file inside .ai-sdlc/kit/ (rewrite_links), so they still resolve after the move.
"""
from __future__ import annotations

import posixpath
import re
import shutil
from pathlib import Path

from . import packs, paths, reuse

KIT_CLASS = "kit"
SIDECAR = ".kit-new"
_LINK = re.compile(r"\]\(([^)\s]+)\)")              # ](target) of a Markdown link
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")  # http:, https:, mailto:, …


def rewrite_links(text, skill_dir, placed_dir, exists) -> tuple[str, list[str]]:
    """Point relative links that leave the skill's folder at the same file in .ai-sdlc/kit/.

    skill_dir is the skill's folder in the kit (template/.claude/skills/<skill>),
    placed_dir its folder in the repo (.agents/skills/ai-sdlc-<skill>), and
    exists(kit_rel) says whether a kit path exists. Links inside the skill's
    folder, URLs, root-absolute paths and #anchors are left alone. Returns the new
    text and the links whose target is not in the kit, which are left as they are.
    Pure and deterministic: the same input always renders the same bytes.
    """
    missing = []

    def fix(m):
        target = m.group(1)
        if _SCHEME.match(target) or target.startswith(("#", "/")):
            return m.group(0)
        path, hash_, anchor = target.partition("#")
        kit_rel = posixpath.normpath(posixpath.join(skill_dir, path))
        if kit_rel == skill_dir or kit_rel.startswith(skill_dir + "/"):
            return m.group(0)
        if kit_rel == ".." or kit_rel.startswith("../") or not exists(kit_rel):
            missing.append(target)
            return m.group(0)
        new = posixpath.relpath(posixpath.join(paths.KIT_REL, kit_rel), placed_dir)
        if path.endswith("/"):
            new += "/"
        return f"]({new}{hash_}{anchor})"

    return _LINK.sub(fix, text), missing


def user_md(all_packs, choices, combined) -> str:
    extra = ", ".join(choices["add_skills"]) or "none"
    fewer = ", ".join(choices["drop_skills"]) or "none"
    return (
        "# AI-SDLC: about me\n\n"
        f"- **Name:** {choices['name']}\n"
        f"- **Roles:** {', '.join(all_packs[r]['label'] for r in choices['roles'])}\n"
        f"- **Language:** {packs.LANGUAGES[choices['lang']]}\n"
        f"- **Git comfort:** {combined['git_comfort']}\n"
        f"- **Session summary:** {'on' if combined['rituals'] == 'status' else 'off'}\n"
        f"- **Extra skills:** {extra}\n"
        f"- **Skills left out:** {fewer}\n\n"
        "Written by the kit. To change it, say \"change my preferences\".\n"
    )


def placed_skill(kit, skill, missing=None) -> tuple[str, str]:
    """(repo path, text) of a library skill as setup places it: prefixed name, links into the kit.

    Links with no target in the kit are appended to `missing` when a list is given
    (validate_packs.py reports them); setup itself places the text either way.
    """
    src_dir = f"{packs.SKILLS_REL}/{skill}"
    dest_dir = f".agents/skills/{packs.PREFIX}{skill}"
    text = packs.prefixed_skill((Path(kit) / src_dir / "SKILL.md").read_text(encoding="utf-8"), skill)
    text, lost = rewrite_links(text, src_dir, dest_dir, lambda rel: (Path(kit) / rel).exists())
    if missing is not None:
        missing += lost
    return f"{dest_dir}/SKILL.md", text


def wanted_files(kit, all_packs, choices) -> dict[str, str]:
    """{repo path: text} of every file these choices call for."""
    combined = packs.combine(all_packs, choices)
    values = packs.core_values(all_packs, choices, combined)
    files = dict(packs.instructions_file(all_packs[pid], values)
                 for pid in [packs.CORE, *choices["roles"]])
    for skill in combined["skills"]:
        rel, text = placed_skill(kit, skill)
        files[rel] = text
    files[paths.USER_REL] = user_md(all_packs, choices, combined)
    return files


def _write(root, st, rel, data: bytes) -> None:
    for parent in reversed(list(Path(rel).parents)[:-1]):
        if not (root / parent).exists():
            st["created_dirs"].append(parent.as_posix())
    paths.write_atomic(root / rel, data)
    reuse.record(st, rel, KIT_CLASS, data)


def prune_dirs(root, st) -> None:
    """Remove folders setup created once they are empty again (deepest first)."""
    for d in sorted(st["created_dirs"], key=lambda p: p.count("/"), reverse=True):
        path = Path(root) / d
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
        if not path.exists():
            st["created_dirs"].remove(d)


def apply(root, st, wanted: dict[str, str]) -> dict[str, list[str]]:
    """Make the repo hold `wanted`; returns what was written, kept, skipped and removed."""
    root = Path(root)
    report = {"written": [], "kept": [], "skipped": [], "removed": []}
    tracked = paths.tracked(root, set(wanted) | set(st["files"]))
    keep = set(wanted)
    for rel, text in sorted(wanted.items()):
        data = text.encode("utf-8")
        if rel in tracked:
            report["skipped"].append(f"{rel} (the team's git tracks this path)")
            continue
        state = reuse.file_state(root, st, rel, data)
        if state in (reuse.NEW, reuse.MISSING, reuse.CLEAN):
            _write(root, st, rel, data)
            report["written"].append(rel)
        elif state == reuse.IDENTICAL:
            reuse.record(st, rel, KIT_CLASS, data)
        elif state == reuse.MODIFIED:
            report["kept"].append(rel)
            if reuse.sha256_bytes(data) != st["files"][rel]["sha256"]:
                keep.add(rel + SIDECAR)
                _write(root, st, rel + SIDECAR, data)
                report["written"].append(rel + SIDECAR)
        else:
            report["skipped"].append(f"{rel} (a file the kit did not write is already there)")
    for rel in sorted(set(st["files"]) - keep):
        if rel not in tracked and reuse.file_state(root, st, rel) == reuse.CLEAN:
            (root / rel).unlink()
            report["removed"].append(rel)
        elif reuse.file_state(root, st, rel) == reuse.MODIFIED:
            report["kept"].append(rel)
        reuse.forget(st, rel)
    prune_dirs(root, st)
    return report


def is_kit(path) -> bool:
    path = Path(path)
    return all((path / p).exists() for p in ("setup.py", "VERSION", packs.ROLES_REL))


def move_kit(root, kit) -> Path:
    """Move the copied kit folder to .ai-sdlc/kit (nothing to do when it is already there).

    shutil.move renames within one filesystem and copies then deletes across two.
    """
    root, kit = Path(root).resolve(), Path(kit).resolve()
    dest = root / paths.KIT_REL
    if kit == dest:
        return dest
    if root not in kit.parents:
        raise ValueError(f"the kit folder must be inside the repo: {kit} is not in {root}")
    if dest.exists():
        raise FileExistsError(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(kit), str(dest))
    return dest
```

In `scripts/personal/validate_packs.py`, render each skill exactly as setup now places it, and fail on a link with no target in the kit. Add `place` to the import (`from personal import packs, place  # noqa: E402`), and replace the body of the `for skill in used:` loop in `skill_errors` with:

```python
        for skill in used:
            missing = []
            _, text = place.placed_skill(kit, skill, missing)
            dest = Path(tmp) / f"{packs.PREFIX}{skill}" / "SKILL.md"
            dest.parent.mkdir()
            dest.write_text(text, encoding="utf-8")
            errors += [f"{packs.PREFIX}{skill}: {e}" for e in module.validate_file(dest)]
            errors += [f"{packs.PREFIX}{skill}: link '{t}' has no target in the kit; "
                       "it was placed unchanged" for t in missing]
```

**Step 4: Run the tests**

Run:
```bash
python3 scripts/personal/tests/test_place.py
python3 scripts/personal/tests/test_packs.py
python3 scripts/personal/validate_packs.py
```
Expected: `test_place` `Ran 17 tests`, `OK` (13 for the engine and the move, 4 for the links); `test_packs` 16 OK; `ok    8 role pack(s) valid; their skills pass validate-skills`. Earlier suites unchanged (`test_roles` 7). (Confirmed when Task 6a ran, 2026-10-08, on Python 3.13 and 3.9.6.)

**Step 5: Commit**

```bash
git add scripts/personal/place.py \
        scripts/personal/validate_packs.py \
        scripts/personal/tests/test_place.py
git commit -F - <<'EOF'
feat(personal): one reconcile engine for placing and sweeping kit files

manifest.state() decides per file: write, adopt, keep an edit (with a
.kit-new only when the kit's copy changed), or leave a foreign file alone.
Tracked paths are never touched; empty folders setup made are pruned.
Placed skills' links that leave their folder now point into .ai-sdlc/kit/.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output; wait for approval before Task 6b.

---

### Task 6b: The `setup` command

**Order inside `setup`, and one adjustment.** The design says moving and excluding the kit is the very first thing, before any question; the suggested order says "move first", then "write the exclude block before anything else". Here the exclude block is written first and the move second, both before anything else: writing the block first means `.ai-sdlc/` is already hidden at the instant the kit lands there, and the block is a single atomic write. To honour "before any question", `setup --protect-only` does exactly those two steps and nothing else; `ONBOARDING.md` (Task 13) runs it right after the Python check and only then asks the three questions. From then on every command runs from the stable path `.ai-sdlc/kit/setup.py`.

Then: load the packs from the moved kit, validate name, roles and language (plain errors, exit 2), place the files through `place.apply`, write `state.json` **last**, print the summary. A re-run with the same answers changes nothing but `updated_at`. A second kit copy is refused with "say update the kit". In a non-git folder, setup works and says nothing hides the files.

The kit path in all later code comes from the move's return value, never from `paths.KIT`: after the move, the running `setup.py`'s own folder no longer exists (all modules are imported at start-up, so the process is unaffected).

**Files:**
- Modify: `scripts/personal/commands.py` (replace the Task 1 skeleton)
- Test: `scripts/personal/tests/test_setup.py`

**Step 1: Write the failing test.** Create `scripts/personal/tests/test_setup.py`:

```python
#!/usr/bin/env python3
"""`setup`: hide and move the kit first, place the files, write state last."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import paths

ARGS = ["setup", "--name", "Ana Pop", "--roles", "po,sm", "--lang", "de"]


class TestSetup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = helpers.make_repo(Path(self.tmp.name).resolve() / "repo",
                                      {"README.md": "team\n"})
        self.copy = helpers.copy_kit(self.root / "tools/ai-sdlc-kit")
        self.kit = self.root / paths.KIT_REL

    def tearDown(self):
        self.tmp.cleanup()

    def status(self):
        return helpers.git(self.root, "status", "--porcelain").stdout

    def test_protect_only_moves_and_hides_the_kit(self):
        code, out = helpers.cli(self.root, self.copy, "setup", "--protect-only")
        self.assertEqual(code, 0, out)
        self.assertIn("The kit is now in .ai-sdlc/kit and hidden from git.", out)
        self.assertFalse(self.copy.exists())
        self.assertTrue((self.kit / "setup.py").is_file())
        self.assertEqual(self.status(), "")
        self.assertFalse((self.root / paths.STATE_REL).exists())

    def test_setup_places_the_files_and_git_sees_nothing(self):
        code, out = helpers.cli(self.root, self.copy, *ARGS)
        self.assertEqual(code, 0, out)
        self.assertIn("Set up AI-SDLC", out)
        self.assertIn("for Ana Pop: Product Owner, Scrum Master / Team Coach (SAFe) · German (Deutsch).", out)
        for rel in (".github/instructions/ai-sdlc-core.instructions.md",
                    ".github/instructions/ai-sdlc-po.instructions.md",
                    ".github/instructions/ai-sdlc-sm.instructions.md",
                    ".agents/skills/ai-sdlc-playbook-product/SKILL.md",
                    ".agents/skills/ai-sdlc-playbook-sm/SKILL.md", paths.USER_REL):
            self.assertTrue((self.root / rel).is_file(), rel)
        self.assertEqual(self.status(), "")

    def test_state_records_the_choices_the_version_and_every_file(self):
        helpers.cli(self.root, self.copy, *ARGS)
        st = json.loads((self.root / paths.STATE_REL).read_text())
        self.assertEqual(st["choices"]["roles"], ["po", "sm"])
        self.assertEqual(st["kit_version"], paths.kit_version(self.kit))
        self.assertIn(paths.USER_REL, st["files"])

    def test_running_setup_again_changes_nothing_but_the_timestamp(self):
        helpers.cli(self.root, self.copy, *ARGS)
        before = helpers.snapshot(self.root)
        code, out = helpers.cli(self.root, self.kit, *ARGS)
        self.assertEqual(code, 0, out)
        after = helpers.snapshot(self.root)
        for snap in (before, after):
            snap.pop(paths.STATE_REL)
        self.assertEqual(after, before)

    def test_a_bad_role_or_language_is_a_plain_error(self):
        code, out = helpers.cli(self.root, self.copy, "setup", "--name", "Ana",
                                "--roles", "po,boss", "--lang", "de")
        self.assertEqual(code, 2)
        self.assertIn("(not known: boss)", out)
        code, out = helpers.cli(self.root, self.kit, "setup", "--name", "Ana",
                                "--roles", "po", "--lang", "fr")
        self.assertEqual(code, 2)
        self.assertIn("Choose a language from: en, ro, de.", out)
        self.assertFalse((self.root / ".github").exists())

    def test_a_second_kit_copy_is_sent_to_update(self):
        helpers.cli(self.root, self.copy, *ARGS)
        newer = helpers.copy_kit(self.root / "newer-kit")
        code, out = helpers.cli(self.root, newer, *ARGS)
        self.assertEqual(code, 2)
        self.assertIn('say "update the kit"', out)

    def test_a_non_git_folder_works_and_says_so(self):
        plain = Path(self.tmp.name).resolve() / "plain"
        copy = helpers.copy_kit(plain / "kit")
        code, out = helpers.cli(plain, copy, *ARGS)
        self.assertEqual(code, 0, out)
        self.assertIn("not a git repo, so nothing hides these files from git", out)

    def test_the_real_cli_from_a_copied_folder(self):
        r = subprocess.run([sys.executable, str(self.copy / "setup.py"), "setup", "--protect-only"],
                           cwd=self.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = subprocess.run([sys.executable, ".ai-sdlc/kit/setup.py", *ARGS],
                           cwd=self.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.status(), "")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_setup.py`
Expected: `Ran 8 tests`, `FAILED (failures=7, errors=1)`, mostly `AssertionError: 3 != 0 : setup.py setup: not built yet`.

**Step 3: Implement.** Replace `scripts/personal/commands.py` with:

```python
"""The six commands behind setup.py. Each returns (exit code, lines to print).

The lines are short and plain: Copilot relays them to the person as they are.
"""
from __future__ import annotations

from pathlib import Path

from . import exclude, packs, paths, place, state


class SetupError(Exception):
    """A plain-language reason to stop. Raised before anything else is changed."""


# --- argument checks ---------------------------------------------------------

def _name(value) -> str:
    name = " ".join((value or "").split())
    if not name or len(name) > 80:
        raise SetupError("Please give a name (1 to 80 characters).")
    return name


def _roles(all_packs, value) -> list[str]:
    roles = [r.strip().lower() for r in (value or "").split(",") if r.strip()]
    known = packs.selectable(all_packs)
    unknown = [r for r in roles if r not in known]
    if not roles or unknown:
        raise SetupError(f"Choose one or more roles from: {', '.join(known)}"
                         + (f" (not known: {', '.join(unknown)})." if unknown else "."))
    return list(dict.fromkeys(roles))


def _lang(value) -> str:
    if value not in packs.LANGUAGES:
        raise SetupError(f"Choose a language from: {', '.join(packs.LANGUAGES)}.")
    return value


def _need_state(root) -> dict:
    st = state.load(root)
    if st is None:
        raise SetupError('The kit is not set up in this repo yet. Say "do the onboarding".')
    return st


# --- summaries -----------------------------------------------------------------

def _summary(verb, root, is_git, kit, all_packs, st, report) -> list[str]:
    c = st["choices"]
    combined = packs.combine(all_packs, c)
    roles = ", ".join(all_packs[r]["label"] for r in c["roles"])
    lines = [f"{verb} AI-SDLC {paths.kit_version(kit)} for {c['name']}: {roles} · "
             f"{packs.LANGUAGES[c['lang']]}."]
    lines.append("- Hidden from git: .ai-sdlc/ and every ai-sdlc-* file." if is_git else
                 "- This folder is not a git repo, so nothing hides these files from git.")
    if report["written"]:
        lines.append(f"- Wrote {len(report['written'])} file(s): {', '.join(report['written'])}")
    if report["removed"]:
        lines.append(f"- Removed {len(report['removed'])} file(s) no longer needed: "
                     f"{', '.join(report['removed'])}")
    for rel in report["kept"]:
        lines.append(f"- Kept your edit in {rel}. The kit's copy, if it changed, is next to it "
                     f"as {rel}{place.SIDECAR}.")
    for item in report["skipped"]:
        lines.append(f"- Left alone: {item}")
    skills = ", ".join(packs.PREFIX + s for s in combined["skills"]) or "none"
    lines.append(f"- Skills: {skills} · git: {combined['git_comfort']} · session summary: "
                 f"{'on' if combined['rituals'] == 'status' else 'off'}")
    return lines


# --- commands -------------------------------------------------------------------

def cmd_setup(args, cwd, kit):
    root, is_git = paths.repo_root(cwd)
    kit = Path(kit).resolve()
    if not place.is_kit(kit):
        raise SetupError(f"{kit} is not a complete kit folder (setup.py, VERSION, roles/).")
    if is_git:
        exclude.protect(root)                       # first: hide the destination
    try:
        kit = place.move_kit(root, kit)             # second: move the copied kit there
    except ValueError:
        raise SetupError(f"Copy the kit folder into the repo first; it is at {kit}, "
                         f"outside {root}.") from None
    except FileExistsError:
        raise SetupError('A kit is already set up in this repo (.ai-sdlc/kit). To use this '
                         'newer copy, say "update the kit".') from None
    if args.protect_only:
        return 0, ["The kit is now in .ai-sdlc/kit" + (" and hidden from git." if is_git else
                   ". This folder is not a git repo, so nothing hides it from git."),
                   "Next: python3 .ai-sdlc/kit/setup.py setup --name … --roles … --lang …"]
    all_packs = packs.load(kit)
    choices = {"name": _name(args.name), "roles": _roles(all_packs, args.roles),
               "lang": _lang(args.lang)}
    st = state.load(root) or state.new(paths.kit_version(kit))
    st["choices"].update(choices)
    report = place.apply(root, st, place.wanted_files(kit, all_packs, st["choices"]))
    st["kit_version"] = paths.kit_version(kit)
    state.save(root, st)                            # last
    lines = _summary("Set up", root, is_git, kit, all_packs, st, report)
    lines.append('Say "change my preferences", "update the kit" or "remove the kit" at any time.')
    return 0, lines


def not_built(args, cwd, kit):
    return 3, [f"setup.py {args.command}: not built yet"]


HANDLERS = {
    "setup": cmd_setup,
}


def run(args, cwd, kit):
    return HANDLERS.get(args.command, not_built)(args, cwd, kit)
```

**Step 4: Run the tests**

Run: `python3 scripts/personal/tests/test_setup.py`
Expected: `Ran 8 tests`, `OK`. All earlier suites unchanged: `test_cli` 10, `test_exclude` 11, `test_state` 6, `test_packs` 16, `test_roles` 7, `test_place` 17.

**Step 5: Commit**

```bash
git add scripts/personal/commands.py \
        scripts/personal/tests/test_setup.py
git commit -F - <<'EOF'
feat(personal): setup hides and moves the kit, then places the files

The exclude block, then the move to .ai-sdlc/kit, come before anything
else (--protect-only stops there, before onboarding asks its questions).
state.json is written last, so an interrupted run completes on re-run.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output; wait for approval before Task 7.

---

### Task 7: `check`, and `setup` ends with it

**What `check` reports** (stable ids, so `ONBOARDING.md` maps each to a fix):

| Id | Meaning |
|---|---|
| `missing:<path>` | a file the kit placed is gone |
| `unknown:<path>` | an `ai-sdlc*` file in `.github/instructions`, `.github/skills`, `.agents/skills` or `.claude/skills` that the kit did not write (Copilot may have made it) |
| `unexcluded:<path>` | an `ai-sdlc*` file (or the kit folder) that git neither ignores nor tracks (`git check-ignore`) |
| `kit-copy:<dir>` | another kit folder git does not hide: "a newer kit is waiting, say update the kit", or "delete it". Found with `git ls-files --others --exclude-standard --directory` (exactly the unprotected folders), up to two levels deep, by its `setup.py` + `VERSION` + `roles/` |
| `stale-kit` | `.ai-sdlc/kit/VERSION` differs from `state.json` (an interrupted update) |

`check` exits 1 when there is anything to look at. `check --quiet` is the one line Copilot runs at the start of a session (the core instructions' session line), e.g. `AI-SDLC 0.4.0 · roles: PO, SM · de · ok`, always exits 0, and never raises (a session-start check must not derail the conversation). Team-file warnings join the list in Task 8.

**Files:**
- Create: `scripts/personal/checks.py`
- Modify: `scripts/personal/commands.py` (import, `_check_lines`, `cmd_check`, `setup`'s last line, `HANDLERS`)
- Test: `scripts/personal/tests/test_checks.py`

**Step 1: Write the failing test.** Create `scripts/personal/tests/test_checks.py`:

```python
#!/usr/bin/env python3
"""`check`: missing, unknown and unhidden files, kit copies, a stale kit, the one-liner."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers
from personal import checks, exclude, paths

ARGS = ["setup", "--name", "Ana", "--roles", "po,sm", "--lang", "de"]
CORE = ".github/instructions/ai-sdlc-core.instructions.md"


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = helpers.make_repo(Path(self.tmp.name).resolve() / "repo", {"README.md": "x\n"})
        self.kit = self.root / paths.KIT_REL
        code, self.setup_out = helpers.cli(self.root, helpers.copy_kit(self.root / "kit-copy"), *ARGS)
        self.assertEqual(code, 0, self.setup_out)

    def tearDown(self):
        self.tmp.cleanup()

    def ids(self):
        return [fid for fid, _ in checks.run(self.root)[1]]

    def test_a_fresh_setup_is_clean_and_the_one_liner_says_ok(self):
        self.assertEqual(self.ids(), [])
        self.assertIn("Check: all good.", self.setup_out)
        code, out = helpers.cli(self.root, self.kit, "check", "--quiet")
        version = paths.kit_version(self.kit)
        self.assertEqual((code, out), (0, f"AI-SDLC {version} · roles: PO, SM · de · ok\n"))

    def test_a_deleted_file_is_missing(self):
        (self.root / CORE).unlink()
        self.assertEqual(self.ids(), [f"missing:{CORE}"])

    def test_files_the_kit_did_not_write_are_unknown(self):
        (self.root / ".github/instructions/ai-sdlc-extra.instructions.md").write_text("x\n")
        stray = self.root / ".claude/skills/ai-sdlc-notes/SKILL.md"
        stray.parent.mkdir(parents=True)
        stray.write_text("x\n")
        self.assertEqual(sorted(self.ids()), [
            "unexcluded:.claude/skills/ai-sdlc-notes/SKILL.md",
            "unknown:.claude/skills/ai-sdlc-notes/SKILL.md",
            "unknown:.github/instructions/ai-sdlc-extra.instructions.md"])

    def test_a_removed_exclude_block_is_reported(self):
        exclude.unprotect(self.root)
        ids = self.ids()
        self.assertIn(f"unexcluded:{CORE}", ids)
        self.assertIn(f"unexcluded:{paths.USER_REL}", ids)
        self.assertIn(f"unexcluded:{paths.KIT_REL}", ids)

    def test_kit_copies_are_reported_and_a_newer_one_waits(self):
        newer = helpers.copy_kit(self.root / "downloads/ai-sdlc-kit")
        (newer / "VERSION").write_text("9.9.9\n")
        found = dict(checks.run(self.root)[1])
        self.assertEqual(found["kit-copy:downloads/ai-sdlc-kit"],
                         'A newer kit (9.9.9) is waiting in downloads/ai-sdlc-kit. Say "update the kit".')
        (newer / "VERSION").write_text("0.0.1\n")
        found = dict(checks.run(self.root)[1])
        self.assertIn("is a copy of the kit that git does not hide", found["kit-copy:downloads/ai-sdlc-kit"])

    def test_a_kit_folder_newer_than_the_state_is_stale(self):
        (self.kit / "VERSION").write_text("9.9.9\n")
        self.assertEqual(self.ids(), ["stale-kit"])

    def test_check_exit_codes(self):
        self.assertEqual(helpers.cli(self.root, self.kit, "check")[0], 0)
        (self.root / CORE).unlink()
        code, out = helpers.cli(self.root, self.kit, "check")
        self.assertEqual(code, 1)
        self.assertIn(f"- [missing:{CORE}] {CORE} is missing.", out)
        code, out = helpers.cli(self.root, self.kit, "check", "--quiet")
        self.assertEqual(code, 0)
        self.assertIn("· 1 to look at:", out)

    def test_quiet_never_fails(self):
        with mock.patch.object(checks, "run", side_effect=RuntimeError("boom")):
            code, out = helpers.cli(self.root, self.kit, "check", "--quiet")
        self.assertEqual((code, out), (0, "AI-SDLC: the check could not run (boom).\n"))

    def test_not_set_up(self):
        other = helpers.make_repo(Path(self.tmp.name) / "other")
        code, out = helpers.cli(other, self.kit, "check", "--quiet")
        self.assertEqual(out, 'The kit is not set up in this repo. Say "do the onboarding".\n')


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_checks.py`
Expected: `ImportError: cannot import name 'checks' from 'personal'`.

**Step 3: Implement.** Create `scripts/personal/checks.py`:

```python
"""`check`: is the personal setup whole, hidden, current, and alone?

Each finding is (id, text). Ids are stable, so ONBOARDING.md can map them to fixes:
    missing:<path>     a file the kit placed is gone
    unknown:<path>     an ai-sdlc* file the kit did not write (Copilot may have made it)
    unexcluded:<path>  an ai-sdlc* file git does not hide
    stale-kit          the kit folder and state.json disagree on the version
    kit-copy:<dir>     another kit folder in the repo that git does not hide
"""
from __future__ import annotations

from pathlib import Path

from . import paths, place, reuse, state

SCAN = (".github/instructions", ".github/skills", ".agents/skills", ".claude/skills")


def ai_sdlc_files(root) -> list[str]:
    """Every file named ai-sdlc* (or inside an ai-sdlc* folder) where Copilot looks."""
    root = Path(root)
    out = []
    for d in SCAN:
        for p in sorted((root / d).glob("ai-sdlc*")) if (root / d).is_dir() else []:
            files = [p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file())
            out += [q.relative_to(root).as_posix() for q in files]
    return out


def version_key(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def _dirs(top: Path, depth: int):
    yield top
    if depth:
        for child in sorted(p for p in top.iterdir() if p.is_dir()):
            yield from _dirs(child, depth - 1)


def kit_copies(root) -> list[str]:
    """Kit folders (up to two levels inside an untracked folder) that git does not hide."""
    r = paths.git(root, "ls-files", "--others", "--exclude-standard", "--directory", "-z")
    if r is None or r.returncode != 0:
        return []
    found = []
    for entry in r.stdout.split("\0"):
        if entry.endswith("/"):
            found += [d.relative_to(root).as_posix() for d in _dirs(Path(root) / entry, 2)
                      if place.is_kit(d)]
    return found


def run(root) -> tuple[dict | None, list[tuple[str, str]]]:
    root = Path(root)
    st = state.load(root)
    if st is None:
        return None, [("not-set-up", 'The kit is not set up in this repo. Say "do the onboarding".')]
    found = []
    for rel in sorted(st["files"]):
        if reuse.file_state(root, st, rel) == reuse.MISSING:
            found.append((f"missing:{rel}", f"{rel} is missing."))
    present = ai_sdlc_files(root)
    for rel in present:
        if rel not in st["files"] and not rel.endswith(".tmp"):
            found.append((f"unknown:{rel}", f"{rel} looks like a kit file, but the kit did not write it."))
    if paths.repo_root(root)[1]:
        on_disk = sorted(set(present) | {r for r in st["files"] if (root / r).is_file()})
        hidden, tracked = paths.ignored(root, on_disk), paths.tracked(root, on_disk)
        for rel in on_disk:
            if rel not in hidden and rel not in tracked:
                found.append((f"unexcluded:{rel}", f"{rel} is not hidden from git."))
        for d in kit_copies(root):
            if d == paths.KIT_REL:
                found.append((f"unexcluded:{d}", f"The kit folder {d} is not hidden from git."))
                continue
            v = paths.kit_version(root / d)
            if version_key(v) > version_key(st["kit_version"]):
                text = f'A newer kit ({v}) is waiting in {d}. Say "update the kit".'
            else:
                text = f"{d} is a copy of the kit that git does not hide. Delete it."
            found.append((f"kit-copy:{d}", text))
    kv = paths.kit_version(root / paths.KIT_REL)
    if kv != st["kit_version"]:
        found.append(("stale-kit", f"The kit folder is {kv} but this setup is {st['kit_version']}. "
                                   'Say "update the kit".'))
    return st, found


def quiet_line(root, st, found) -> str:
    if st is None:
        return found[0][1]
    c = st["choices"]
    head = f"AI-SDLC {st['kit_version']} · roles: {', '.join(r.upper() for r in c['roles'])} · {c['lang']}"
    if not paths.repo_root(root)[1]:
        head += " · not a git repo"
    if not found:
        return head + " · ok"
    return head + f" · {len(found)} to look at: " + " ".join(text for _, text in found)
```

In `scripts/personal/commands.py`:

- the import line becomes `from . import checks, exclude, packs, paths, place, state`;
- the last line of `cmd_setup` becomes `    return 0, lines + _check_lines(root)[1]`;
- insert before `def not_built`:

```python
def _check_lines(root) -> tuple[int, list[str]]:
    st, found = checks.run(root)
    if not found:
        return 0, ["Check: all good."]
    return 1, [f"Check: {len(found)} to look at:"] + [f"- [{fid}] {text}" for fid, text in found]


def cmd_check(args, cwd, kit):
    root, _ = paths.repo_root(cwd)
    if args.quiet:
        try:
            st, found = checks.run(root)
            return 0, [checks.quiet_line(root, st, found)]
        except Exception as exc:  # noqa: BLE001  the session-start check must never fail
            return 0, [f"AI-SDLC: the check could not run ({exc})."]
    return _check_lines(root)
```

- and add `    "check": cmd_check,` to `HANDLERS`.

**Step 4: Run the tests**

Run: `python3 scripts/personal/tests/test_checks.py && python3 scripts/personal/tests/test_setup.py`
Expected: `test_checks` `Ran 9 tests` `OK`; `test_setup` 8 OK. Others unchanged.

**Step 5: Commit**

```bash
git add scripts/personal/checks.py \
        scripts/personal/commands.py \
        scripts/personal/tests/test_checks.py
git commit -F - <<'EOF'
feat(personal): check (missing, unknown, unhidden, stale, kit copies) and --quiet

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output; wait for approval before Task 8.

---

### Task 8: Team-file warnings and `ack`

**Built in parallel worktrees and integrated on feat/personal-setup-commands** (Tasks 8–11, 2026-10-08): each task was cut from the same `main`, then cherry-picked in order; the conflicts in `commands.py` (the import line, `HANDLERS`, functions inserted at the same place) were resolved by keeping every side, and Task 11's final `HANDLERS` and `run` applied as written.

**What counts as a warning** (the kit never edits a team file; it says where the two meet):

| Id | When |
|---|---|
| `team-agents-md` | the repo has an `AGENTS.md` |
| `team-copilot-instructions` | the repo has `.github/copilot-instructions.md` |
| `team-instructions:<path>` | a team `.github/instructions/*.instructions.md` whose `applyTo` overlaps the kit's (`**`, so any `applyTo`); one without `applyTo` is only used when attached, so it is not reported |
| `team-rules:<path>` | not reported in v1: Task 0 check 10 showed Copilot does not apply `.claude/rules/*.md`, so `TEAM_RULE_DIRS` is `()`. The code path stays (parsed with Phase 0's `_rule_paths`, no `paths:` means everywhere) so a directory can be added back if a future Copilot reads one |
| `skill-clash:<dir>` | a team skill in `.claude/skills`, `.github/skills` or `.agents/skills` named like a placed kit skill, bare (`playbook-dev`) or prefixed (`ai-sdlc-playbook-dev`) |

Frontmatter is split with Phase 0's `_split_frontmatter`; `applyTo` values are unquoted with `_unquote`. `overlaps()` compares the literal prefixes of two globs and errs on the side of "yes". Ids derive from paths only, so they are stable. Each warning carries the team file's sha256; `ack <id>` stores it, and the warning comes back only when that file changes. The judgement pass (real contradictions) is Copilot's job in `ONBOARDING.md`; a contradiction always sits in a team file that already has an id, so it is acknowledged with that id.

**Files:**
- Create: `scripts/personal/conflicts.py`
- Modify: `scripts/personal/checks.py` (import `conflicts`; docstring; `run` returns `found + conflicts.active(root, st)`)
- Modify: `scripts/personal/commands.py` (import `conflicts`, `cmd_ack`, `HANDLERS`)
- Test: `scripts/personal/tests/test_conflicts.py`

**Step 1: Write the failing test.** Create `scripts/personal/tests/test_conflicts.py`:

```python
#!/usr/bin/env python3
"""Team-file warnings: stable ids, precise text, acknowledged by fingerprint."""
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import conflicts, paths, state

ARGS = ["setup", "--name", "Ana", "--roles", "po,sm", "--lang", "en"]
TEAM = {
    "AGENTS.md": "# Team brief\n",
    ".github/copilot-instructions.md": "Use British English.\n",
    ".github/instructions/docs.instructions.md": "---\napplyTo: 'docs/**'\n---\nTwo reviewers.\n",
    ".github/instructions/manual.instructions.md": "No applyTo: only used when attached.\n",
    ".claude/skills/playbook-product/SKILL.md": "---\nname: playbook-product\n---\nTeam's.\n",
    ".github/skills/ai-sdlc-playbook-sm/SKILL.md": "---\nname: ai-sdlc-playbook-sm\n---\nX.\n",
    ".github/skills/release-notes/SKILL.md": "---\nname: release-notes\n---\nNo clash.\n",
}


class TestOverlaps(unittest.TestCase):
    def test_globs(self):
        self.assertTrue(conflicts.overlaps("docs/**", "**"))
        self.assertTrue(conflicts.overlaps("src/*.ts", "src/app/**"))
        self.assertFalse(conflicts.overlaps("docs/**", "src/**"))


class TestWarnings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = helpers.make_repo(Path(self.tmp.name).resolve() / "repo", TEAM)
        self.kit = self.root / paths.KIT_REL
        code, self.out = helpers.cli(self.root, helpers.copy_kit(self.root / "kit-copy"), *ARGS)
        self.assertEqual(code, 0, self.out)

    def tearDown(self):
        self.tmp.cleanup()

    def warnings(self):
        return {wid: text for wid, text, _ in conflicts.warnings(self.root, state.load(self.root))}

    def test_each_kind_of_overlap_has_a_stable_id(self):
        self.assertEqual(sorted(self.warnings()), [
            "skill-clash:.claude/skills/playbook-product",
            "skill-clash:.github/skills/ai-sdlc-playbook-sm",
            "team-agents-md", "team-copilot-instructions",
            "team-instructions:.github/instructions/docs.instructions.md"])

    def test_the_text_is_precise(self):
        w = self.warnings()
        self.assertEqual(w["team-instructions:.github/instructions/docs.instructions.md"],
                         "The team's .github/instructions/docs.instructions.md also applies to "
                         "docs/**, where the kit's instructions apply too.")
        self.assertIn("the kit adds ai-sdlc-playbook-product",
                      w["skill-clash:.claude/skills/playbook-product"])

    def test_setup_lists_them_and_changes_no_team_file(self):
        self.assertIn("- [team-agents-md] The team has its own AGENTS.md.", self.out)
        self.assertEqual(helpers.git(self.root, "status", "--porcelain").stdout, "")
        self.assertEqual(helpers.git(self.root, "diff", "HEAD", "--stat").stdout, "")

    def test_ack_silences_a_warning_until_the_team_file_changes(self):
        code, out = helpers.cli(self.root, self.kit, "ack", "team-agents-md")
        self.assertEqual(code, 0, out)
        self.assertNotIn("[team-agents-md]", helpers.cli(self.root, self.kit, "check")[1])
        (self.root / "AGENTS.md").write_text("# Team brief, edited\n")
        self.assertIn("[team-agents-md]", helpers.cli(self.root, self.kit, "check")[1])

    def test_ack_needs_a_current_id(self):
        code, out = helpers.cli(self.root, self.kit, "ack", "team-nope")
        self.assertEqual(code, 2)
        self.assertIn("No current warning has the id team-nope.", out)


class TestQuietRepo(unittest.TestCase):
    def test_no_team_files_no_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = helpers.make_repo(Path(tmp).resolve() / "repo", {"README.md": "x\n"})
            helpers.cli(root, helpers.copy_kit(root / "kit-copy"), *ARGS)
            self.assertEqual(conflicts.warnings(root, state.load(root)), [])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_conflicts.py`
Expected: `ImportError: cannot import name 'conflicts' from 'personal'`.

**Step 3: Implement.** Create `scripts/personal/conflicts.py`:

```python
"""Precise warnings about the team's own AI files, and acknowledging them.

The kit never edits a team file. It says where the team's instructions and the
kit's meet, so the person (and Copilot) can look for real contradictions. Each
warning has a stable id built from the team file's path and carries that file's
fingerprint; `ack` stores the fingerprint, and the warning returns only when the
file changes.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import packs, reuse

TEAM_BRIEFS = {"AGENTS.md": "team-agents-md",
               ".github/copilot-instructions.md": "team-copilot-instructions"}
TEAM_RULE_DIRS = ()                          # Copilot ignores .claude/rules (Task 0 check 10)
SKILL_DIRS = (".claude/skills", ".github/skills", ".agents/skills")
KIT_APPLY_TO = ("**",)                       # every kit instructions file applies everywhere


def _apply_to(front: str) -> list[str]:
    for line in front.splitlines():
        m = re.match(r"^applyTo:\s*(.*)$", line)
        if m:
            return [g.strip() for g in reuse.unquote(m.group(1)).split(",") if g.strip()]
    return []


def _literal_prefix(glob: str) -> str:
    cut = min([glob.find(c) for c in "*?[{" if c in glob] or [len(glob)])
    return glob[:cut]


def overlaps(a: str, b: str) -> bool:
    """Could globs `a` and `b` match the same file? Errs on the side of yes."""
    pa, pb = _literal_prefix(a), _literal_prefix(b)
    return pa.startswith(pb) or pb.startswith(pa)


def _shared(globs) -> list[str]:
    return [g for g in globs if any(overlaps(g, k) for k in KIT_APPLY_TO)]


def warnings(root, st) -> list[tuple[str, str, str]]:
    """(id, text, fingerprint of the team file) for every place team and kit meet."""
    root = Path(root)
    ours = set(st["files"])
    out = []
    for rel, wid in TEAM_BRIEFS.items():
        fp = reuse.sha256_file(root / rel)
        if fp:
            out.append((wid, f"The team has its own {rel}. Copilot reads it together with the "
                             "kit's instructions.", fp))
    inst = root / ".github/instructions"
    for p in sorted(inst.glob("*.instructions.md")) if inst.is_dir() else []:
        rel = p.relative_to(root).as_posix()
        if p.name.startswith(packs.PREFIX) or rel in ours:
            continue
        front, _ = reuse.split_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        shared = _shared(_apply_to(front))
        if shared:
            out.append((f"team-instructions:{rel}", f"The team's {rel} also applies to "
                        f"{', '.join(shared)}, where the kit's instructions apply too.",
                        reuse.sha256_file(p)))
    for d in TEAM_RULE_DIRS:
        for p in sorted((root / d).glob("*.md")) if (root / d).is_dir() else []:
            rel = p.relative_to(root).as_posix()
            front, _ = reuse.split_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
            try:
                globs = reuse.rule_paths(front, rel) or ["**"]
            except ValueError:
                globs = ["**"]
            out.append((f"team-rules:{rel}", f"The team's rule {rel} applies to "
                        f"{', '.join(_shared(globs))}, where the kit's instructions apply too.",
                        reuse.sha256_file(p)))
    placed = {Path(rel).parent.name for rel in ours if rel.startswith(".agents/skills/")}
    names = placed | {n[len(packs.PREFIX):] for n in placed}
    for d in SKILL_DIRS:
        for skill in sorted((root / d).glob("*/SKILL.md")) if (root / d).is_dir() else []:
            rel = skill.relative_to(root).as_posix()
            if rel in ours or skill.parent.name not in names:
                continue
            out.append((f"skill-clash:{skill.parent.relative_to(root).as_posix()}",
                        f"The team has a skill {skill.parent.name} ({rel}); the kit adds "
                        f"{packs.PREFIX}{skill.parent.name.removeprefix(packs.PREFIX)}. "
                        "Copilot sees both.", reuse.sha256_file(skill)))
    return out


def active(root, st) -> list[tuple[str, str]]:
    """The warnings not yet acknowledged, or whose team file changed since."""
    return [(wid, text) for wid, text, fp in warnings(root, st) if st["acks"].get(wid) != fp]
```

In `scripts/personal/checks.py`: the import line becomes `from . import conflicts, paths, place, reuse, state`; add the docstring line `and the team-file warnings from conflicts.py that are not acknowledged.` after the `kit-copy` line; and the last line of `run` becomes:

```python
    return st, found + conflicts.active(root, st)
```

In `scripts/personal/commands.py`: the import line becomes `from . import checks, conflicts, exclude, packs, paths, place, state`; insert before `def not_built`:

```python
def cmd_ack(args, cwd, kit):
    root, _ = paths.repo_root(cwd)
    st = _need_state(root)
    current = {wid: fp for wid, _, fp in conflicts.warnings(root, st)}
    unknown = [wid for wid in args.ids if wid not in current]
    if unknown:
        raise SetupError(f"No current warning has the id {', '.join(unknown)}. "
                         "Run check to see the ids.")
    for wid in args.ids:
        st["acks"][wid] = current[wid]
    state.save(root, st)
    return 0, [f"Noted {wid}. It comes back only if that team file changes." for wid in args.ids]
```

and add `    "ack": cmd_ack,` to `HANDLERS`.

**Step 4: Run the tests**

Run: `python3 scripts/personal/tests/test_conflicts.py && python3 scripts/personal/tests/test_checks.py`
Expected: `test_conflicts` `Ran 7 tests` `OK`; `test_checks` 9 OK (its repo has no team files). Others unchanged.

**Step 5: Commit**

```bash
git add scripts/personal/conflicts.py \
        scripts/personal/checks.py \
        scripts/personal/commands.py \
        scripts/personal/tests/test_conflicts.py
git commit -F - <<'EOF'
feat(personal): precise team-file warnings with stable ids, and ack

AGENTS.md, copilot-instructions.md, overlapping applyTo and skill-name
clashes. ack stores the team file's fingerprint; the warning
returns only when that file changes. No team file is ever edited.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output; wait for approval before Task 9.

---

### Task 9: `change`

`change` loads the installed kit (`.ai-sdlc/kit`), applies only the options given, re-hides (the exclude block is refreshed, which also fixes `unexcluded:` findings), reconciles through `place.apply`, saves state last, and ends with the check. Because the reconcile compares fingerprints, only affected files change: a new language rewrites the core file and `USER.md`, nothing else. `--git-comfort default` / `--rituals default` go back to the roles' defaults. `--add-skill` refuses unknown and unplaceable skills. `change` with no options repairs: it rewrites missing files and re-hides.

**Files:**
- Modify: `scripts/personal/commands.py` (`_skill`, `cmd_change`, `HANDLERS`)
- Test: `scripts/personal/tests/test_change.py`

**Step 1: Write the failing test.** Create `scripts/personal/tests/test_change.py`:

```python
#!/usr/bin/env python3
"""`change`: new choices touch only the files they affect; edits are kept."""
import json
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import paths

ARGS = ["setup", "--name", "Ana", "--roles", "po", "--lang", "en"]
CORE = ".github/instructions/ai-sdlc-core.instructions.md"
PO = ".github/instructions/ai-sdlc-po.instructions.md"
DEV = ".github/instructions/ai-sdlc-dev.instructions.md"


class TestChange(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = helpers.make_repo(Path(self.tmp.name).resolve() / "repo", {"README.md": "x\n"})
        self.kit = self.root / paths.KIT_REL
        helpers.cli(self.root, helpers.copy_kit(self.root / "kit-copy"), *ARGS)

    def tearDown(self):
        self.tmp.cleanup()

    def change(self, *argv):
        code, out = helpers.cli(self.root, self.kit, "change", *argv)
        self.assertEqual(code, 0, out)
        return out

    def test_language_rewrites_only_the_core_and_user_files(self):
        before = helpers.snapshot(self.root)
        self.change("--lang", "ro")
        after = helpers.snapshot(self.root)
        changed = sorted(k for k in after if after[k] != before.get(k))
        self.assertEqual(changed, sorted([paths.STATE_REL, paths.USER_REL, CORE]))
        self.assertIn("Always answer in Romanian (română)", (self.root / CORE).read_text())

    def test_adding_a_role_adds_its_files_and_dropping_removes_them(self):
        self.change("--roles", "po,dev")
        self.assertTrue((self.root / DEV).is_file())
        self.assertTrue((self.root / ".agents/skills/ai-sdlc-playbook-dev/SKILL.md").is_file())
        out = self.change("--roles", "po")
        self.assertFalse((self.root / DEV).exists())
        self.assertFalse((self.root / ".agents/skills/ai-sdlc-playbook-dev").exists())
        self.assertIn("Removed 2 file(s) no longer needed", out)

    def test_skills_can_be_added_and_dropped(self):
        self.change("--add-skill", "skill-creator", "--drop-skill", "playbook-product")
        skills = sorted(p.name for p in (self.root / ".agents/skills").iterdir())
        self.assertEqual(skills, ["ai-sdlc-skill-creator"])

    def test_unknown_or_unsupported_skills_are_refused(self):
        code, out = helpers.cli(self.root, self.kit, "change", "--add-skill", "nope")
        self.assertEqual(code, 2)
        self.assertIn("There is no skill nope.", out)
        code, out = helpers.cli(self.root, self.kit, "change", "--add-skill", "git-verbs")
        self.assertEqual(code, 2)
        self.assertIn("cannot be added", out)

    def test_git_comfort_override_and_back_to_the_default(self):
        self.change("--git-comfort", "git-native")
        self.assertIn("They use git themselves.", (self.root / CORE).read_text())
        self.change("--git-comfort", "default")
        self.assertIn("Do git for them in plain words", (self.root / CORE).read_text())
        st = json.loads((self.root / paths.STATE_REL).read_text())
        self.assertIsNone(st["choices"]["git_comfort"])

    def test_an_edited_file_is_kept(self):
        (self.root / CORE).write_text("my own core\n")
        out = self.change("--lang", "de")
        self.assertEqual((self.root / CORE).read_text(), "my own core\n")
        self.assertIn(f"Kept your edit in {CORE}", out)
        self.assertIn("Always answer in German", (self.root / (CORE + ".kit-new")).read_text())
        self.assertEqual(helpers.git(self.root, "status", "--porcelain").stdout, "")

    def test_change_with_no_options_repairs_missing_files(self):
        (self.root / PO).unlink()
        out = self.change()
        self.assertTrue((self.root / PO).is_file())
        self.assertIn("Check: all good.", out)

    def test_change_before_setup_is_a_plain_error(self):
        other = helpers.make_repo(Path(self.tmp.name) / "other")
        code, out = helpers.cli(other, self.kit, "change", "--lang", "de")
        self.assertEqual((code, out), (2, 'The kit is not set up in this repo yet. Say "do the onboarding".\n'))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_change.py`
Expected: `Ran 8 tests`, `FAILED (failures=8)`, e.g. `AssertionError: 3 != 0 : setup.py change: not built yet`.

**Step 3: Implement.** In `scripts/personal/commands.py`, insert before `def _need_state`:

```python
def _skill(kit, value) -> str:
    if value in packs.UNSUPPORTED_SKILLS:
        raise SetupError(f"The skill {value} cannot be added: {packs.UNSUPPORTED_SKILLS[value]}.")
    if value not in packs.available_skills(kit):
        raise SetupError(f"There is no skill {value}. Available: "
                         f"{', '.join(packs.available_skills(kit))}.")
    return value
```

Insert before `def not_built`:

```python
def cmd_change(args, cwd, kit):
    root, is_git = paths.repo_root(cwd)
    st = _need_state(root)
    kit = root / paths.KIT_REL
    all_packs = packs.load(kit)
    c = st["choices"]
    if args.name is not None:
        c["name"] = _name(args.name)
    if args.roles is not None:
        c["roles"] = _roles(all_packs, args.roles)
    if args.lang is not None:
        c["lang"] = _lang(args.lang)
    if args.git_comfort is not None:
        c["git_comfort"] = None if args.git_comfort == "default" else args.git_comfort
    if args.rituals is not None:
        c["rituals"] = None if args.rituals == "default" else args.rituals
    for s in args.add_skill:
        _skill(kit, s)
        c["add_skills"] = sorted(set(c["add_skills"]) | {s})
        c["drop_skills"] = [x for x in c["drop_skills"] if x != s]
    for s in args.drop_skill:
        c["drop_skills"] = sorted(set(c["drop_skills"]) | {s})
        c["add_skills"] = [x for x in c["add_skills"] if x != s]
    if is_git:
        exclude.protect(root)
    report = place.apply(root, st, place.wanted_files(kit, all_packs, c))
    state.save(root, st)
    return 0, _summary("Updated", root, is_git, kit, all_packs, st, report) + _check_lines(root)[1]
```

and add `    "change": cmd_change,` to `HANDLERS`.

**Step 4: Run the tests**

Run: `python3 scripts/personal/tests/test_change.py`
Expected: `Ran 8 tests`, `OK`. Others unchanged.

**Step 5: Commit**

```bash
git add scripts/personal/commands.py \
        scripts/personal/tests/test_change.py
git commit -F - <<'EOF'
feat(personal): change updates choices and only the files they affect

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output; wait for approval before Task 10.

---

### Task 10: `update`, run from the newer copy

The person copies a newer kit folder into the repo and says "update the kit"; Copilot runs **that folder's** `setup.py update`. It refuses an older copy and a copy outside the repo (nothing changed), refreshes the exclude block (a newer kit may hide more), replaces `.ai-sdlc/kit` with the newer copy (`place.replace_kit`: delete the old kit folder only if it is a kit, then `move_kit`), reconciles with the person's unchanged choices, and records the new version. Unedited files are refreshed; an edited one is kept and the kit's newer copy written as `<file>.kit-new`; a skill the newer kit dropped is removed while unedited. A role the newer kit no longer has is dropped and said so. Run from `.ai-sdlc/kit` itself, `update` refreshes in place. If interrupted after the old kit was deleted, re-running the newer copy's `update` finishes it (`check` says `stale-kit` meanwhile).

**Files:**
- Modify: `scripts/personal/place.py` (`replace_kit`)
- Modify: `scripts/personal/commands.py` (`cmd_update`, `HANDLERS`)
- Test: `scripts/personal/tests/test_update.py`

**Step 1: Write the failing test.** Create `scripts/personal/tests/test_update.py`:

```python
#!/usr/bin/env python3
"""`update`, run from a newer kit copy: replace the kit, refresh unedited files, keep edits."""
import json
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import paths

ARGS = ["setup", "--name", "Ana", "--roles", "po,dev", "--lang", "de"]
CORE = ".github/instructions/ai-sdlc-core.instructions.md"
PO = ".github/instructions/ai-sdlc-po.instructions.md"


class TestUpdate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = helpers.make_repo(Path(self.tmp.name).resolve() / "repo", {"README.md": "x\n"})
        self.kit = self.root / paths.KIT_REL
        helpers.cli(self.root, helpers.copy_kit(self.root / "kit-copy"), *ARGS)
        self.newer = helpers.copy_kit(self.root / "kit-newer")
        (self.newer / "VERSION").write_text("9.9.9\n")
        for pid in ("core", "po"):
            with open(self.newer / f"roles/{pid}/instructions.md", "a", encoding="utf-8") as fh:
                fh.write("\nNewer kit line.\n")

    def tearDown(self):
        self.tmp.cleanup()

    def update(self, kit=None):
        return helpers.cli(self.root, kit or self.newer, "update")

    def test_the_kit_folder_is_replaced_and_the_version_recorded(self):
        code, out = self.update()
        self.assertEqual(code, 0, out)
        self.assertIn("Updated to AI-SDLC 9.9.9", out)
        self.assertEqual(paths.kit_version(self.kit), "9.9.9")
        self.assertFalse(self.newer.exists())
        st = json.loads((self.root / paths.STATE_REL).read_text())
        self.assertEqual(st["kit_version"], "9.9.9")
        self.assertEqual(st["choices"]["roles"], ["po", "dev"])

    def test_unedited_files_are_refreshed_and_edited_ones_kept(self):
        (self.root / PO).write_text("my po notes\n")
        self.update()
        self.assertIn("Newer kit line.", (self.root / CORE).read_text())
        self.assertEqual((self.root / PO).read_text(), "my po notes\n")
        self.assertIn("Newer kit line.", (self.root / (PO + ".kit-new")).read_text())
        self.assertEqual(helpers.git(self.root, "status", "--porcelain").stdout, "")

    def test_a_skill_the_newer_kit_drops_is_removed(self):
        role = self.newer / "roles/dev/role.json"
        data = json.loads(role.read_text())
        data["skills"] = []
        role.write_text(json.dumps(data))
        self.update()
        self.assertFalse((self.root / ".agents/skills/ai-sdlc-playbook-dev").exists())

    def test_an_older_copy_is_refused(self):
        (self.newer / "VERSION").write_text("0.0.1\n")
        code, out = self.update()
        self.assertEqual(code, 2)
        self.assertIn("This copy is older (0.0.1)", out)
        self.assertTrue(self.newer.exists())

    def test_update_from_the_installed_kit_refreshes_in_place(self):
        (self.root / CORE).unlink()
        code, out = self.update(self.kit)
        self.assertEqual(code, 0, out)
        self.assertTrue((self.root / CORE).is_file())

    def test_after_update_check_is_clean(self):
        code, out = self.update()
        self.assertIn("Check: all good.", out)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_update.py`
Expected: `Ran 6 tests`, `FAILED (failures=6)`, e.g. `AssertionError: 3 != 0 : setup.py update: not built yet`.

**Step 3: Implement.** In `scripts/personal/place.py`, insert before `def move_kit`:

```python
def replace_kit(root, kit) -> Path:
    """Swap .ai-sdlc/kit for the newer copy at `kit` (update). Interrupted, a re-run finishes it."""
    dest = Path(root) / paths.KIT_REL
    if dest.exists():
        if not is_kit(dest):
            raise FileExistsError(dest)
        shutil.rmtree(dest)
    return move_kit(root, kit)
```

In `scripts/personal/commands.py`, insert before `def not_built`:

```python
def cmd_update(args, cwd, kit):
    root, is_git = paths.repo_root(cwd)
    st = _need_state(root)
    kit = Path(kit).resolve()
    dest = root / paths.KIT_REL
    if kit != dest:
        new, old = paths.kit_version(kit), paths.kit_version(dest)
        if checks.version_key(new) < checks.version_key(old):
            raise SetupError(f"This copy is older ({new}) than the kit set up here ({old}). "
                             "Nothing was changed.")
        if root not in kit.parents:
            raise SetupError(f"Copy the newer kit folder into the repo first; it is at {kit}.")
    if is_git:
        exclude.protect(root)                     # the newer kit may hide more paths
    if kit != dest:
        try:
            place.replace_kit(root, kit)
        except FileExistsError:
            raise SetupError(f"{paths.KIT_REL} is not a kit folder; it was left alone.") from None
    all_packs = packs.load(dest)
    c = st["choices"]
    gone = [r for r in c["roles"] if r not in packs.selectable(all_packs)]
    c["roles"] = [r for r in c["roles"] if r not in gone]
    report = place.apply(root, st, place.wanted_files(dest, all_packs, c))
    st["kit_version"] = paths.kit_version(dest)
    state.save(root, st)
    lines = _summary("Updated to", root, is_git, dest, all_packs, st, report)
    if gone:
        lines.append(f"- The newer kit has no {', '.join(gone)} role any more; it was dropped.")
    return 0, lines + _check_lines(root)[1]
```

and add `    "update": cmd_update,` to `HANDLERS`.

**Step 4: Run the tests**

Run: `python3 scripts/personal/tests/test_update.py`
Expected: `Ran 6 tests`, `OK`. `test_place` 17, others unchanged.

**Step 5: Commit**

```bash
git add scripts/personal/place.py \
        scripts/personal/commands.py \
        scripts/personal/tests/test_update.py
git commit -F - <<'EOF'
feat(personal): update from a newer kit copy, keeping edits as .kit-new

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output; wait for approval before Task 11.

---

### Task 11: `remove`, and the byte-for-byte restore

`remove` reconciles to nothing (`place.apply(root, st, {})`: unedited files deleted, edited ones kept and listed, created folders pruned), deletes the kit folder (only if it is a kit), `state.json`, and `.ai-sdlc/` if empty, then strips the exclude block. **The strictest test:** snapshot every file and folder plus `.git/info/exclude` *before the kit is copied in*; copy, `setup --protect-only`, `setup`, `change`, `ack`, `remove`; the snapshot must be identical, including an exclude file with no final newline, a repo whose `.github/` the kit created, and a non-git folder. Edited files are kept and the summary says git now shows them. This task also drops the `not_built` fallback, since every command now exists.

**Files:**
- Modify: `scripts/personal/commands.py` (`import shutil`, `cmd_remove`, final `HANDLERS` and `run`)
- Test: `scripts/personal/tests/test_remove.py`

**Step 1: Write the failing test.** Create `scripts/personal/tests/test_remove.py`:

```python
#!/usr/bin/env python3
"""`remove`: the repo ends byte for byte as it was before the kit was copied in."""
import tempfile
import unittest
from pathlib import Path

import helpers
from personal import paths

ARGS = ["setup", "--name", "Ana", "--roles", "po,sm,dev", "--lang", "ro"]
TEAM = {"README.md": "team\n", "AGENTS.md": "# Team\n",
        ".github/instructions/team.instructions.md": "---\napplyTo: 'docs/**'\n---\nTeam.\n"}
CORE = ".github/instructions/ai-sdlc-core.instructions.md"


class TestRemove(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def round_trip(self, root, edit=None):
        """Snapshot, copy the kit in, set up, use it, remove. Returns (before, after, output)."""
        before = helpers.snapshot(root)
        copy = helpers.copy_kit(root / "ai-sdlc-kit")
        kit = root / paths.KIT_REL
        helpers.cli(root, copy, "setup", "--protect-only")
        helpers.cli(root, kit, *ARGS)
        helpers.cli(root, kit, "change", "--lang", "en", "--add-skill", "skill-creator")
        if (root / "AGENTS.md").exists():
            self.assertEqual(helpers.cli(root, kit, "ack", "team-agents-md")[0], 0)
        if edit:
            edit(root)
        code, out = helpers.cli(root, kit, "remove")
        self.assertEqual(code, 0, out)
        return before, helpers.snapshot(root), out

    def test_git_repo_is_restored_byte_for_byte(self):
        root = helpers.make_repo(self.base / "repo", TEAM)
        before, after, out = self.round_trip(root)
        self.assertEqual(after, before)
        self.assertIn("The repo is back to how it was before setup.", out)

    def test_an_exclude_file_without_a_final_newline_is_restored(self):
        root = helpers.make_repo(self.base / "repo", TEAM)
        (root / ".git/info/exclude").write_text("*.log")
        before, after, _ = self.round_trip(root)
        self.assertEqual(after, before)

    def test_a_repo_whose_github_folder_the_kit_created(self):
        root = helpers.make_repo(self.base / "repo", {"README.md": "x\n"})
        before, after, _ = self.round_trip(root)
        self.assertEqual(after, before)
        self.assertFalse((root / ".github").exists())

    def test_a_non_git_folder_is_restored(self):
        root = self.base / "plain"
        root.mkdir()
        (root / "notes.md").write_text("mine\n")
        before, after, _ = self.round_trip(root)
        self.assertEqual(after, before)

    def test_edited_files_are_kept_and_listed(self):
        root = helpers.make_repo(self.base / "repo", TEAM)
        _, _, out = self.round_trip(root, edit=lambda r: (r / CORE).write_text("mine\n"))
        self.assertEqual((root / CORE).read_text(), "mine\n")
        self.assertIn(f"Kept, because you edited them (git now shows them; delete them if you "
                      f"don't need them): {CORE}", out)
        self.assertFalse((root / paths.HOME_REL).exists())

    def test_remove_before_setup_is_a_plain_error(self):
        root = helpers.make_repo(self.base / "repo")
        code, out = helpers.cli(root, helpers.KIT, "remove")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_remove.py`
Expected: `Ran 6 tests`, `FAILED (failures=6)`, e.g. `AssertionError: 3 != 0 : setup.py remove: not built yet`.

**Step 3: Implement.** In `scripts/personal/commands.py`, add `import shutil` above `from pathlib import Path`; insert before `def not_built`:

```python
def cmd_remove(args, cwd, kit):
    root, is_git = paths.repo_root(cwd)
    st = _need_state(root)
    report = place.apply(root, st, {})            # deletes unedited files, keeps edited ones
    kit_dir = root / paths.KIT_REL
    if place.is_kit(kit_dir):
        shutil.rmtree(kit_dir)
    (root / paths.STATE_REL).unlink()
    home = root / paths.HOME_REL
    if home.is_dir() and not any(home.iterdir()):
        home.rmdir()
    if is_git:
        exclude.unprotect(root)
    lines = [f"Removed the kit: {len(report['removed'])} file(s), the kit folder and your settings."]
    if report["kept"]:
        lines.append("Kept, because you edited them (git now shows them; delete them if you "
                     "don't need them): " + ", ".join(report["kept"]))
    elif is_git:
        lines.append("The repo is back to how it was before setup.")
    return 0, lines
```

Then replace everything from `def not_built` to the end of the file with:

```python
HANDLERS = {
    "setup": cmd_setup,
    "change": cmd_change,
    "update": cmd_update,
    "check": cmd_check,
    "ack": cmd_ack,
    "remove": cmd_remove,
}


def run(args, cwd, kit):
    return HANDLERS[args.command](args, cwd, kit)
```

**Step 4: Run all personal suites**

Run: `for t in scripts/personal/tests/test_*.py; do printf '%-44s ' "$t"; python3 "$t" 2>&1 | tail -1; done`
Expected: every file `OK`: `test_change` 8, `test_checks` 9, `test_cli` 10, `test_conflicts` 7, `test_exclude` 11, `test_packs` 16, `test_place` 17, `test_remove` 6, `test_roles` 7, `test_setup` 8, `test_state` 6, `test_update` 6.

**Step 5: Commit**

```bash
git add scripts/personal/commands.py \
        scripts/personal/tests/test_remove.py
git commit -F - <<'EOF'
feat(personal): remove restores the repo byte for byte

Unedited files, the kit folder, state and the exclude block go; edited
files stay and are listed. Tested against a snapshot taken before the kit
was copied in, including .git/info/exclude.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output; wait for approval before Task 13.

---

### Task 12: Removed after the spike (decision A)

This task placed a session-start hook (`.github/hooks/…`) that ran `check --quiet`. Task 0 showed that VS Code does not run hooks and that hook output never reaches the model in either the CLI or VS Code, so the owner chose option A: no hook. The status comes from the core instructions' session line (Task 4), which tells Copilot to run `python3 .ai-sdlc/kit/setup.py check --quiet` itself. Nothing to do here; the heading stays so task numbers match earlier reviews. Go from Task 11 straight to Task 13.

---

### Task 13: `ONBOARDING.md` at the kit root

The conversation script, with no file logic in it. "Do the onboarding": check `python3 --version` (3.9+, else a plain who-to-ask message and stop), `setup --protect-only`, the three questions one at a time (then speak the chosen language), `setup`, relay the summary and each warning with its id, the judgement pass over the team's files versus the kit's (real contradictions only; the team's rule wins), `ack`, close. Then sections for "change my preferences" (a table from wishes to `change` options), "update the kit", "check the kit" (each finding id → its fix) and "remove the kit" (confirm first). The test parses `setup.py`'s argparse parser and fails if the document names a subcommand or a flag that does not exist, or forgets a role or a language. It also checks that the retired `template/ONBOARDING.md` sends Copilot here (Task 0, check 8: the kit folder carries both files).

**MVP adjustment (owner decision, 2026-10-08, for the demo).** `change`, `update`, `remove`, `ack` and the team-file warnings (Task 8) were not built when Task 13 landed: `setup.py` answers them with exit 3 ("not built yet"). `ONBOARDING.md` keeps their sections and adds one deletable line at the top of "Change my preferences", "Update the kit" and "Remove the kit" ("…tell the person in their language that it arrives in the next kit version, and stop.") and at the start of step 7 ("…and go to step 8.", so the onboarding still closes). Delete those four lines when Tasks 8–11 land. Tasks 13 and 15 were built in parallel worktrees and cherry-picked onto the branch. Removed when Tasks 8–11 landed (2026-10-08).

**Step-6 wording fix (2026-10-08, with Tasks 8–11).** Step 6 of "Do the onboarding" now reads "For each `team-…` or `skill-clash:…` warning", matching the "Check the kit" section; a skill clash is a team file too. The `ONBOARDING.md` below still shows the original wording.

**Files:**
- Create: `ONBOARDING.md` (kit root)
- Modify: `template/ONBOARDING.md` (one blockquote after the title)
- Test: `scripts/personal/tests/test_onboarding.py`

**Step 1: Write the failing test.** Create `scripts/personal/tests/test_onboarding.py`:

```python
#!/usr/bin/env python3
"""ONBOARDING.md names only real setup.py commands and flags, and offers every role and language."""
import argparse
import re
import sys
import unittest

import helpers
from personal import packs

sys.path.insert(0, str(helpers.KIT))
import setup  # noqa: E402  the kit-root setup.py

DOC = (helpers.KIT / "ONBOARDING.md").read_text(encoding="utf-8")
CALL = re.compile(r"setup\.py ([a-z]+)([^`\n]*)")
FLAG = re.compile(r"--[a-z][a-z-]*")


def subcommands() -> dict:
    """{command: {its option strings}} straight from setup.py's argparse parser."""
    action = next(a for a in setup.parser()._actions
                  if isinstance(a, argparse._SubParsersAction))
    return {name: set(p._option_string_actions) for name, p in action.choices.items()}


def section(title: str) -> str:
    return DOC.split(f"\n## {title}\n", 1)[1].split("\n## ", 1)[0]


class TestOnboarding(unittest.TestCase):
    def test_every_command_named_is_real_and_its_flags_belong_to_it(self):
        real = subcommands()
        calls = CALL.findall(DOC)
        self.assertGreater(len(calls), 5)
        for command, tail in calls:
            with self.subTest(call=f"setup.py {command}{tail}"):
                self.assertIn(command, real)
                self.assertLessEqual(set(FLAG.findall(tail)), real[command])

    def test_the_change_table_uses_change_flags_only(self):
        flags = set(FLAG.findall(section("Change my preferences")))
        self.assertTrue(flags)
        self.assertLessEqual(flags, subcommands()["change"])

    def test_every_role_and_language_is_offered(self):
        for pid in packs.selectable(packs.load(helpers.KIT)):
            self.assertIn(f"`{pid}`", section("Do the onboarding"), pid)
        for code in packs.LANGUAGES:
            self.assertIn(f"`{code}`", section("Do the onboarding"), code)

    def test_every_spoken_request_has_a_section(self):
        for title in ("Do the onboarding", "Change my preferences", "Update the kit",
                      "Check the kit", "Remove the kit"):
            self.assertIn(f"\n## {title}\n", DOC)

    def test_python_floor_matches_setup_py(self):
        self.assertIn("3.9 or newer", DOC)
        self.assertIn("sys.version_info < (3, 9)", (helpers.KIT / "setup.py").read_text())

    def test_the_core_instructions_point_here(self):
        core = (helpers.KIT / "roles/core/instructions.md").read_text()
        self.assertIn("`.ai-sdlc/kit/ONBOARDING.md`", core)

    def test_the_retired_template_onboarding_points_to_the_kit_root(self):
        text = (helpers.KIT / "template/ONBOARDING.md").read_text()
        self.assertTrue("follow the `ONBOARDING.md` at the kit's top folder" in text,
                        "template/ONBOARDING.md does not point to the kit-root ONBOARDING.md")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_onboarding.py`
Expected: `FileNotFoundError: [Errno 2] No such file or directory: '…/ONBOARDING.md'` at import.

**Step 3: Write the documents.** Create `ONBOARDING.md`:

~~~~markdown
# AI-SDLC kit: onboarding

> **To Copilot.** The person said "do the onboarding", or "change my preferences", "update the kit", "check the kit" or "remove the kit". Follow the matching section below. Run every command yourself, from the repo root; the person only answers questions. Speak plainly, without git or Python words unless they use them. Never edit a team file: `AGENTS.md`, `.github/copilot-instructions.md`, or anything not named `ai-sdlc-*`.

Below, `KIT` is the folder this file is in. Before setup it is wherever the person copied it (for example `tools/ai-sdlc-kit`); after setup it is always `.ai-sdlc/kit`.

## Do the onboarding

1. **Check Python.** Run `python3 --version`. It must say 3.9 or newer. If the command is missing or older, say: "Your computer needs Python 3.9 or newer before I can set this up. Please ask your IT support to install it." Then stop. Nothing has changed.
2. **Protect the kit first.** Run `python3 KIT/setup.py setup --protect-only`. It moves the kit to `.ai-sdlc/kit` and hides it from git. From now on, run `python3 .ai-sdlc/kit/setup.py`.
3. **Ask three questions,** one at a time:
   1. "What is your name?"
   2. "What is your role here? You can pick more than one: Product Owner (`po`), Product Manager (`pm`), Scrum Master / Team Coach in SAFe (`sm`), Developer (`dev`), QA (`qa`), Architect (`architect`), Engineering Manager (`em`)."
   3. "Which language should I answer in: English (`en`), Romanian (`ro`) or German (`de`)?"

   From the answer to question 3 on, speak that language.
4. **Set up.** Run `python3 .ai-sdlc/kit/setup.py setup --name "<name>" --roles <ids, comma-separated> --lang <code>`.
5. **Relay the result** in plain words: who it is set up for, then each item under "Check", with its id in brackets.
6. **Look for contradictions.** For each `team-…` warning, read the team file it names and the kit's `.github/instructions/ai-sdlc-*.instructions.md`. Tell the person only about real contradictions (one says do X, the other says don't), one sentence each, naming both files. The team's rule wins; say so.
7. **Acknowledge.** For each warning the person has understood, run `python3 .ai-sdlc/kit/setup.py ack <warning-id>`. It comes back only if that team file changes.
8. **Close.** Say: "You're set up. Say 'change my preferences', 'update the kit' or 'remove the kit' at any time."

## Change my preferences

Ask what they want to change, then run `python3 .ai-sdlc/kit/setup.py change` with the matching option:

| They want | Option |
|---|---|
| another name | `--name "<name>"` |
| other roles | `--roles <ids>` (the full new list) |
| another language | `--lang <en, ro or de>` |
| git done for them, or not | `--git-comfort <hidden, guided, git-native or default>` |
| the one-line session summary on or off (the session-start check always runs) | `--rituals <status, none or default>` |
| an extra skill | `--add-skill <skill>` |
| a skill left out | `--drop-skill <skill>` |

Relay the summary. If it says it kept their edit, explain that the kit's newer copy is next to their file as `<file>.kit-new`, for them to compare.

## Update the kit

The person copied a newer kit folder into the repo; `check` names it (`kit-copy:<folder>`). Run `python3 <that folder>/setup.py update`. Relay the summary, including any kept edits.

## Check the kit

Run `python3 .ai-sdlc/kit/setup.py check` and relay each item:

- `missing:` or `unexcluded:`: run `python3 .ai-sdlc/kit/setup.py change` with no options. It puts files back and hides them again.
- `unknown:`: a file named like the kit's that the kit did not write. Ask before deleting it.
- `kit-copy:`: a newer copy means "update the kit"; an older one can be deleted, after asking.
- `stale-kit`: run `python3 .ai-sdlc/kit/setup.py update`.
- `team-…` and `skill-clash:…`: as in steps 6 and 7 above.

## Remove the kit

Ask first: "This removes the kit and your settings from this repo. Files you edited are kept. Continue?" On yes, run `python3 .ai-sdlc/kit/setup.py remove` and relay what it removed and kept.
~~~~

In `template/ONBOARDING.md`, directly after the line `# Onboarding — first-run setup` and its blank line, insert:

```markdown
> **Retired team-mode onboarding.** If you were asked to "do the onboarding" for the AI-SDLC kit, stop here and follow the `ONBOARDING.md` at the kit's top folder instead.

```

**Step 4: Run the tests**

Run:
```bash
python3 scripts/personal/tests/test_onboarding.py
python3 scripts/personal/tests/test_roles.py          # now also scans ONBOARDING.md for client names
python3 template/scripts/validate-frontmatter.py
python3 scripts/install/tests/test_adopt.py
```
Expected: `test_onboarding` `Ran 7 tests` `OK`; `test_roles` 7 OK; `9/9 files satisfy the frontmatter contract.`; `test_adopt` 42 OK.

**Step 5: Commit.** This is the script Copilot follows with every person: the human reads it as a non-technical PO would hear it.

```bash
git add ONBOARDING.md \
        template/ONBOARDING.md \
        scripts/personal/tests/test_onboarding.py
git commit -F - <<'EOF'
docs(onboarding): the conversation Copilot follows for personal setup

Python check, protect the kit, three questions, setup, warnings, the
judgement pass, ack; plus change, update, check and remove. A test keeps
every command and flag it names in step with setup.py's parser.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output; wait for approval before Task 14.

---

### Task 14: Kit CI — `personal-e2e` replaces `adopt-e2e`

**Decision on the existing `ai-governance` job: keep all of it, add to it.** `template/` is retired as a shipped artifact, but it is still the source of every pack skill (`template/.claude/skills/`), and `scripts/install/manifest.py` plus `template/scripts/harness/{sync,merge}.py` are imported by personal setup. Its validators and tests cost seconds and guard exactly that reused code, so the 40 commands stay; dropping them would leave reused code untested. The job already runs every personal suite (the `Personal setup unit tests` step, added early in Task 2 by owner decision: one `for t in scripts/personal/tests/test_*.py` loop line); this task adds `validate_packs.py` (42 commands: the 40, the loop line, the validator; still 42 after Task 15, whose `test_release.py` the loop picks up). **`adopt-e2e` is deleted**: it exercised `install.sh`, which is no longer offered, and its four legs were the slowest part of CI. Its replacement exercises what a person does.

**`personal-e2e`** runs on Python 3.9 (the promised floor) and 3.12, without PyYAML (proving `setup.py` is stdlib only). The 3.9 leg runs only this job: the Phase 0 suites in `ai-governance` need `tomllib` (3.11+) and stay on 3.12. Steps: the personal unit tests on that Python; a fake team repo with its own `AGENTS.md`, `.github/instructions/team.instructions.md` (`applyTo: 'docs/**'`) and a clashing `.claude/skills/playbook-product` (the PO pack's skill), whose file hashes and snapshot are recorded; the kit copied in from the checkout without `.git` (like a ZIP download); `setup --protect-only`, then `setup --roles po,sm --lang de`; asserts `git status --porcelain` is empty, `git diff --exit-code HEAD` and the recorded hashes (team files unchanged), all three warning ids, and the core skills placed as whole folders; `ack` of one warning (it goes quiet, the others stay); `change --lang en` (only `USER.md` and the core file are rewritten); an `update` from a newer copy (version 9.9.9, one new line in the PO pack) with the PO file edited by the person: the edit kept, `.kit-new` written, status still empty; then, because `remove` keeps edited files (and the person's `ai-sdlc-personal*` files, which this job does not create), the person takes the kit's copy (`mv` + `change`), runs `remove`, and the snapshot (`helpers.py snapshot`, which includes `.git/info/exclude`) must equal the one taken before the kit arrived. Both kit copies live at the repo root and are moved away by `setup` and `update` (asserted), so the snapshots must match exactly, with no allowance for a leftover folder.

Note the pipefail trap the job avoids: `check` exits 1 when it has findings, so `check | grep` fails under `set -o pipefail` even when grep matches. The job captures output first (`out="$(… check || true)"`). And `runner.temp` is not available in a job-level `env:` (only `github`, `matrix` and a few other contexts are), so each step derives its paths from `$RUNNER_TEMP` and `$GITHUB_WORKSPACE`.

**Files:**
- Modify: `.github/workflows/ci.yml`

**Step 1: The failing check.** The local CI extraction (Task 16 Step 1) uses the range `/^  ai-governance:/,/^  personal-e2e:/`. Run it now:

```bash
sed -n '/^  ai-governance:/,/^  personal-e2e:/p' .github/workflows/ci.yml \
  | grep -E '^\s+(run: )?(python3 |for t in scripts/personal/)' | wc -l
```
Expected: `43`, not the 42 this task needs: there is no `personal-e2e:` line yet, so the range runs to the end of the file and picks up two `adopt-e2e` lines (`python3 -m venv …`, `python3 - <<'EOF'`) that fail outside a generated clone, and the pack validator is not listed. (The 43 are the 40 from Phase 0, the personal-suites loop line added in Task 2, and those two `adopt-e2e` lines.)

**Step 2: Edit the workflow.** **Do not add a personal-suites step here:** the step `Personal setup unit tests` (after `Installer unit tests (brownfield adoption)`) was added early, in Task 2, by owner decision, and its `for t in scripts/personal/tests/test_*.py` loop already runs every suite, `test_onboarding.py` included. A second one would run each suite twice. In the `ai-governance` job, after the step `Installer end-to-end (greenfield, brownfield, idempotency, uninstall)`, add only the pack validator (the steps after it are shown unchanged, for position):

```yaml
      - name: Validate role packs (roles/*, and their skills against agentskills.io)
        run: python3 scripts/personal/validate_packs.py

      - name: Validate Agent Skills (agentskills.io)
        run: python3 template/scripts/validate-skills.py
      - name: Validate doc frontmatter contract (AGENTS.md §4.2)
        run: python3 template/scripts/validate-frontmatter.py
      - name: Validate session lifecycle-moments manifest
        run: python3 template/scripts/validate-moments.py
      - name: Validator unit tests
        run: python3 template/scripts/tests/test_validate_moments.py
      - name: Validate per-seat profiles manifest
        run: python3 template/scripts/validate-seat-profiles.py
      - name: Seat-profiles validator unit tests
        run: python3 template/scripts/tests/test_validate_seat_profiles.py

      - name: Knowledge-graph unit tests
        run: |
          python3 template/scripts/knowledge/tests/test_graph_store.py
          python3 template/scripts/knowledge/tests/test_manifest.py
          python3 template/scripts/knowledge/tests/test_ingest_docs.py
          python3 template/scripts/knowledge/tests/test_ingest_code.py
          python3 template/scripts/knowledge/tests/test_link_commits.py
          python3 template/scripts/knowledge/tests/test_query.py
          python3 template/scripts/knowledge/tests/test_ingest.py
          python3 template/scripts/knowledge/tests/test_mcp_server.py
          python3 template/scripts/knowledge/tests/test_end_to_end.py
          python3 template/scripts/knowledge/tests/test_ingest_issues.py
          python3 template/scripts/knowledge/tests/test_link_issues.py
          python3 template/scripts/knowledge/tests/test_issue_chain.py
          python3 template/scripts/jira/tests/test_export_jira.py

      - name: Consumption/ROI unit tests (token-roi theme)
        run: |
          python3 template/dashboard/tests/test_schema.py
          python3 template/dashboard/tests/test_roi.py
          python3 template/scripts/spend/tests/test_parse_transcript.py
          python3 template/scripts/spend/tests/test_collect_usage.py
          python3 template/scripts/spend/tests/test_import_invoice.py
          python3 template/scripts/spend/tests/test_import_api_usage.py
          python3 template/scripts/spend/tests/test_import_tickets.py
          python3 template/scripts/spend/tests/test_export_sessions.py
          python3 template/scripts/spend/tests/test_import_sessions.py
          python3 template/scripts/tests/test_check_brief_churn.py

      - name: Brief-churn gate (token-economy rule 2)
        run: python3 template/scripts/check-brief-churn.py --path template/AGENTS.md
      - name: Compile dashboard app
        run: python3 -m py_compile template/dashboard/app.py

      - name: Knowledge graph build + traceability smoke
        run: |
          python3 template/scripts/knowledge/ingest.py --build
          python3 template/scripts/knowledge/ingest.py --federated --trace ADR-0001 | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('nodes'), 'empty trace chain'; print('trace OK:', len(d.get('nodes')), 'nodes')"
          python3 template/scripts/knowledge/ingest.py --federated --trace issue:PROJ-1 | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('nodes'), 'empty issue trace'; print('issue trace OK:', len(d['nodes']), 'nodes')"
```

Then delete the whole `adopt-e2e` job, from its comment block (`# Adopt the kit end to end, as a client would: …`) to the end of the file, and append:

```yaml
  # Personal setup end to end, as a person does it: a team repo with its own AI files,
  # the kit copied in, setup as Copilot runs it from ONBOARDING.md, ack, change, an update
  # from a newer copy, then remove, ending byte-identical. Plan: Task 14 in
  # docs/roadmap/2026-10-08-personal-setup-plan.md. Replaces the team-mode adopt-e2e job.
  # No pyyaml here, which proves setup.py is stdlib only. The 3.9 leg runs only this job;
  # the Phase 0 suites (ai-governance, 3.12) need tomllib.
  personal-e2e:
    # Pinned: ubuntu-latest moves to 26.04 on 2026-10-19 and Python 3.9 has no 26.04 build.
    runs-on: ubuntu-24.04
    strategy:
      fail-fast: false
      matrix:
        # 3.9 is the floor setup.py promises (ONBOARDING.md checks it); 3.12 matches
        # ai-governance. A plain list, no `include` (the H8 trap).
        python: ['3.9', '3.12']
    env:
      PYTHONDONTWRITEBYTECODE: '1'   # no __pycache__ in the checkout the kit is copied from
    defaults:
      run:
        shell: bash
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python }}

      - name: Personal setup unit tests on this Python
        run: |
          set -euo pipefail
          python3 --version
          for t in scripts/personal/tests/test_*.py; do echo "== $t"; python3 "$t"; done

      - name: Throwaway git identity
        run: |
          set -euo pipefail
          git config --global user.name "kit-ci"
          git config --global user.email "kit-ci@users.noreply.github.com"
          git config --global init.defaultBranch main

      - name: A team repo with its own AI files
        run: |
          set -euo pipefail
          T="$RUNNER_TEMP/team"
          mkdir -p "$T" && cd "$T" && git init -q
          mkdir -p .github/instructions .claude/skills/playbook-product docs
          printf '# Team brief\nUse British English.\n' > AGENTS.md
          printf -- "---\napplyTo: 'docs/**'\n---\nDocs need two reviewers.\n" > .github/instructions/team.instructions.md
          printf -- '---\nname: playbook-product\ndescription: The team playbook.\n---\nTeam rules.\n' > .claude/skills/playbook-product/SKILL.md
          printf 'Hello.\n' > docs/readme.md
          git add -A && git commit -qm "team repo"
          for f in $(git ls-files); do echo "$(git hash-object "$f") $f"; done > "$RUNNER_TEMP/team-hashes.txt"
          python3 "$GITHUB_WORKSPACE/scripts/personal/tests/helpers.py" snapshot "$T" > "$RUNNER_TEMP/before.json"

      - name: Copy the kit in and set up, as Copilot does from ONBOARDING.md
        run: |
          set -euo pipefail
          T="$RUNNER_TEMP/team"
          mkdir "$T/ai-sdlc-kit"
          tar -C "$GITHUB_WORKSPACE" --exclude=.git -cf - . | tar -xf - -C "$T/ai-sdlc-kit"
          cd "$T"
          test ! -e ai-sdlc-kit/.git && test -f ai-sdlc-kit/setup.py
          python3 ai-sdlc-kit/setup.py setup --protect-only
          test ! -e ai-sdlc-kit && test -f .ai-sdlc/kit/setup.py
          out="$(python3 .ai-sdlc/kit/setup.py setup --name "CI Person" --roles po,sm --lang de)"
          printf '%s\n' "$out"
          test -z "$(git status --porcelain)"            # nothing for git to see
          git diff --exit-code HEAD                      # team files unchanged ...
          for f in $(git ls-files); do echo "$(git hash-object "$f") $f"; done \
            | diff "$RUNNER_TEMP/team-hashes.txt" -     # ... byte for byte
          for id in team-agents-md 'team-instructions:.github/instructions/team.instructions.md' \
                    'skill-clash:.claude/skills/playbook-product'; do
            printf '%s\n' "$out" | grep -qF "[$id]" || { echo "missing warning $id"; exit 1; }
          done
          grep -q 'Always answer in German' .github/instructions/ai-sdlc-core.instructions.md
          test -f .github/instructions/ai-sdlc-sm.instructions.md
          test -f .agents/skills/ai-sdlc-playbook-product/SKILL.md
          test -f .agents/skills/ai-sdlc-playbook-sm/SKILL.md
          # Core skills are placed as whole folders (references included).
          test -f .agents/skills/ai-sdlc-drawio/references/xml-reference.md

      - name: Acknowledge one warning; it goes quiet, the others stay
        run: |
          set -euo pipefail
          cd "$RUNNER_TEMP/team"
          python3 .ai-sdlc/kit/setup.py ack team-agents-md
          out="$(python3 .ai-sdlc/kit/setup.py check || true)"   # exit 1: there are findings
          printf '%s\n' "$out"
          if printf '%s\n' "$out" | grep -qF '[team-agents-md]'; then echo "ack ignored"; exit 1; fi
          printf '%s\n' "$out" | grep -qF '[skill-clash:.claude/skills/playbook-product]'
          python3 .ai-sdlc/kit/setup.py check --quiet | grep '^AI-SDLC '

      - name: Change a preference; only the core file and USER.md change
        run: |
          set -euo pipefail
          cd "$RUNNER_TEMP/team"
          out="$(python3 .ai-sdlc/kit/setup.py change --lang en)"
          printf '%s\n' "$out"
          printf '%s\n' "$out" | grep -qF 'Wrote 2 file(s): .ai-sdlc/USER.md, .github/instructions/ai-sdlc-core.instructions.md'
          grep -q 'Always answer in English' .github/instructions/ai-sdlc-core.instructions.md
          test -z "$(git status --porcelain)"

      - name: Update from a newer copy; an edited file is kept
        run: |
          set -euo pipefail
          T="$RUNNER_TEMP/team"
          mkdir "$T/ai-sdlc-kit-new"
          tar -C "$GITHUB_WORKSPACE" --exclude=.git -cf - . | tar -xf - -C "$T/ai-sdlc-kit-new"
          cd "$T"
          echo 9.9.9 > ai-sdlc-kit-new/VERSION
          printf '\nNewer kit line.\n' >> ai-sdlc-kit-new/roles/po/instructions.md
          printf '\nMy own note.\n' >> .github/instructions/ai-sdlc-po.instructions.md
          out="$(python3 .ai-sdlc/kit/setup.py check || true)"   # exit 1: there are findings
          printf '%s\n' "$out" | grep -qF '[kit-copy:ai-sdlc-kit-new]'
          python3 ai-sdlc-kit-new/setup.py update
          test "$(cat .ai-sdlc/kit/VERSION)" = 9.9.9 && test ! -e ai-sdlc-kit-new
          grep -q 'My own note' .github/instructions/ai-sdlc-po.instructions.md
          if grep -q 'Newer kit line' .github/instructions/ai-sdlc-po.instructions.md; then
            echo "edited file overwritten"; exit 1
          fi
          grep -q 'Newer kit line' .github/instructions/ai-sdlc-po.instructions.md.kit-new
          test -z "$(git status --porcelain)"

      # remove keeps edited files, so the person first takes the kit's copy (`change`
      # records it), then removes. Nothing is left over: both kit copies lived at the repo
      # root and were moved away by setup and update (checked above).
      - name: Take the kit's copy, then remove; the repo is byte-identical to before
        run: |
          set -euo pipefail
          T="$RUNNER_TEMP/team"
          cd "$T"
          mv .github/instructions/ai-sdlc-po.instructions.md.kit-new .github/instructions/ai-sdlc-po.instructions.md
          python3 .ai-sdlc/kit/setup.py change
          out="$(python3 .ai-sdlc/kit/setup.py remove)"
          printf '%s\n' "$out"
          printf '%s\n' "$out" | grep -qF 'The repo is back to how it was before setup.'
          python3 "$GITHUB_WORKSPACE/scripts/personal/tests/helpers.py" snapshot "$T" > "$RUNNER_TEMP/after.json"
          diff "$RUNNER_TEMP/before.json" "$RUNNER_TEMP/after.json"
          test -z "$(git status --porcelain)"
```

**Step 3: Validate the YAML and simulate the job locally** (bash, from the kit root; the simulation runs every `run:` block of the new job in order, the global git identity included: `HOME` points at a scratch folder, so `git config --global` writes there). Run it once with the Python under test first on `PATH` (`PY=/usr/bin/python3` for 3.9.6 on macOS, then `PY="$(command -v python3)"`); the YAML is read with a Python that has PyYAML:

```bash
python3 -c "import yaml; print(list(yaml.safe_load(open('.github/workflows/ci.yml'))['jobs']))"
S="$(mktemp -d)"; mkdir -p "$S/runner_temp" "$S/home" "$S/bin"; ln -s "$PY" "$S/bin/python3"
python3 - "$S" <<'EOF'
import shlex, sys, yaml
with open(sys.argv[1] + "/steps.sh", "w") as f:
    for st in yaml.safe_load(open(".github/workflows/ci.yml"))["jobs"]["personal-e2e"]["steps"]:
        if "run" in st:
            f.write("bash --noprofile --norc -eo pipefail -c " + shlex.quote(st["run"])
                    + " >/dev/null || { echo FAILED: " + shlex.quote(st["name"]) + "; exit 1; }\n")
    f.write("echo ALL-STEPS-OK\n")
EOF
env -u GIT_CONFIG_GLOBAL RUNNER_TEMP="$S/runner_temp" HOME="$S/home" GITHUB_WORKSPACE="$PWD" \
    PYTHONDONTWRITEBYTECODE=1 PATH="$S/bin:$PATH" bash "$S/steps.sh"
```
Expected: `['ai-governance', 'personal-e2e']`, then `ALL-STEPS-OK` for each Python. (The kit is copied from the working tree, not `git archive HEAD`, so uncommitted changes are tested too.)

**Step 4: Count the local CI commands**

Run the Step 1 command again.
Expected: `42` (the 40 from Phase 0, the personal-suites loop line from Task 2, the pack validator). The range stops at the `  personal-e2e:` line, so none of the new job's commands are counted.

**Step 5: Commit and push; watch the run**

```bash
git add .github/workflows/ci.yml docs/roadmap/2026-10-08-personal-setup-plan.md
git commit -F - <<'EOF'
ci(kit): personal-e2e replaces adopt-e2e (team repo, setup, update, remove; Python 3.9 and 3.12)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```
```bash
git push
```
Expected on the PR: `ai-governance` and both `personal-e2e` legs (`3.9`, `3.12`) succeed. On 2026-10-08 `actions/python-versions` ships 3.9.25 for Ubuntu 22.04 and 24.04 but not for 26.04, and `ubuntu-latest` moves to 26.04 on 2026-10-19; that is why the job is pinned to `runs-on: ubuntu-24.04` rather than dropping 3.9. Check the logs: the 3.9 leg's "Set up job" step reports Ubuntu 24.04.

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output and the green PR checks; wait for approval before Task 15.

---

### Task 15: Retire team mode; release 0.4.0

**Decision: leave the team-mode files in place, stop presenting them.** `install.sh`, `scripts/install/`, `template/ci/`, `template/.github/workflows/` and the `--ci` documentation stay in the repo, untouched except for a one-line notice in `install.sh`. Why not delete: `scripts/install/manifest.py` and `template/scripts/harness/` are imported by personal setup, `template/.claude/skills/` is the skill library, and the Phase 0 tests guard that reused code. Deleting the rest would be a large diff with no user-visible gain, and the client may still want it as reference (design: "stays in git history; promote to a team setup only on request"). The smallest change that stops presenting team mode is: the README no longer documents it (one short "Retired" section says what the files are), `install.sh` prints a notice, and the CHANGELOG says so.

**Follow-up (owner decision, 2026-10-08):** After a successful pilot, propose deleting the retired team-mode code (install.sh, scripts/install outside what personal setup imports, template/ CI files, --ci). Do NOT delete anything without the owner's explicit approval in that moment; ask first. (Task 16, Step 7 raises it; the reused modules move under `scripts/personal/` in the same proposal.)

`VERSION` becomes `0.4.0`. Retiring team mode is breaking, but the kit is 0.x, where SemVer allows it in a minor bump; the version policy now says so. The previous Unreleased lines (the last team-mode changes) move under 0.4.0 as "Team mode, last changes". Replace `<release date>` with the merge date.

**Files:**
- Modify: `README.md` (rewritten), `CHANGELOG.md`, `VERSION`, `install.sh`
- Test: `scripts/personal/tests/test_release.py` (kit CI picks it up through the `Personal setup unit tests` loop from Task 2; `ci.yml` needs no edit)

**Step 1: Write the failing test.** Create `scripts/personal/tests/test_release.py`:

```python
#!/usr/bin/env python3
"""Release 0.4.0: the version, the changelog entry, and docs that lead with personal setup."""
import unittest

import helpers

KIT = helpers.KIT


def read(rel):
    return (KIT / rel).read_text(encoding="utf-8")


class TestRelease(unittest.TestCase):
    def test_version(self):
        self.assertEqual(read("VERSION").strip(), "0.4.0")

    def test_changelog_says_team_mode_is_retired(self):
        entry = read("CHANGELOG.md").split("## [0.4.0]", 1)[1].split("\n## [", 1)[0]
        self.assertIn("**Team mode is retired.**", entry)

    def test_readme_leads_with_copy_then_onboarding(self):
        top = "\n".join(read("README.md").splitlines()[:20])
        self.assertIn("Copy this kit folder", top)
        self.assertIn('Say **"do the onboarding"**', top)

    def test_readme_no_longer_offers_the_installer(self):
        self.assertNotIn("./install.sh --into", read("README.md"))

    def test_install_sh_says_it_is_retired(self):
        self.assertIn("team mode is retired since kit 0.4.0", read("install.sh"))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run it to make sure it fails**

Run: `python3 scripts/personal/tests/test_release.py`
Expected: `Ran 5 tests`, `FAILED (failures=5)`: `AssertionError: '0.3.0' != '0.4.0'`, the changelog has no `## [0.4.0]` entry, the README top has neither line, the README still shows `./install.sh --into`, and `install.sh` has no notice.

**Step 3: Implement.** Replace `README.md` with:

~~~~markdown
# AI-SDLC Bootstrap Kit

A **personal AI setup for everyone on a software team**: developers, QA, architects, engineering managers, product owners, product managers and scrum masters. Each person gets GitHub Copilot instructions and skills that fit their role, their language and how they like to work, inside the shared repo, without committing anything to it.

## Set it up: copy, then "do the onboarding"

1. Copy this kit folder anywhere into your repo (a GitHub ZIP or a colleague's copy; any folder name).
2. Open the repo in VS Code and start Copilot Chat in Agent mode, or run `copilot` in a terminal.
3. Say **"do the onboarding"**. Copilot finds the kit's [`ONBOARDING.md`](./ONBOARDING.md) and follows it.
4. Answer three questions: your name, your role(s), and your language (English, Romanian or German).

Copilot tells you what it set up. `git status` shows nothing: every file the kit adds is hidden from git through `.git/info/exclude`, so it never reaches the shared history. Setup is once per repo.

Afterwards, say **"change my preferences"**, **"update the kit"** (after copying a newer kit folder in), **"check the kit"** or **"remove the kit"** at any time.

You need Python 3.9 or newer. Copilot checks it first and tells you who to ask if it is missing.

## What ends up in your repo

```
<repo>/
├── .ai-sdlc/
│   ├── kit/            this kit folder, moved here by setup (needed for updates)
│   ├── USER.md         your name, roles, language and preferences
│   └── state.json      kit version, your choices, the files placed and their fingerprints
├── .github/
│   └── instructions/ai-sdlc-*.instructions.md   a core brief plus one file per role
└── .agents/skills/ai-sdlc-*/SKILL.md            your roles' skills, prefixed so names cannot clash
```

The kit never creates or edits `AGENTS.md`, `.github/copilot-instructions.md` or `.vscode/settings.json`: the team may own them. Copilot reads the team's files and the kit's `ai-sdlc-*` files together. When they overlap, setup warns you (without blocking) and Copilot looks for real contradictions with you; where they disagree, the team's rule wins.

## Roles

| Role | Id | Skills | Git by default |
|---|---|---|---|
| Product Owner | `po` | `ai-sdlc-playbook-product` | done for you, in plain words |
| Product Manager | `pm` | `ai-sdlc-playbook-product` | done for you, in plain words |
| Scrum Master / Team Coach (SAFe) | `sm` | `ai-sdlc-playbook-sm` | done for you, explained |
| Developer | `dev` | `ai-sdlc-playbook-dev` | you drive git |
| QA | `qa` | `ai-sdlc-playbook-qa` | done for you, explained |
| Architect | `architect` | `ai-sdlc-playbook-architect` | you drive git |
| Engineering Manager | `em` | `ai-sdlc-playbook-em` | you drive git |

You can hold several roles: their skills are combined, each keeps its own instructions file, and where their defaults differ the more guided one wins. Every role works under one rule: **a human validates everything** the AI writes or decides.

Role packs live in [`roles/`](./roles/), one folder per role (`role.json` + `instructions.md`). To add or change one, edit the folder and run `python3 scripts/personal/validate_packs.py`.

## Under the hood

Copilot runs the conversation from `ONBOARDING.md`; a small, tested, stdlib-only script does the file work: `python3 .ai-sdlc/kit/setup.py setup | change | update | check | ack | remove`. You never need to run it yourself.

It never uses the network, never runs a git command that changes anything (only `rev-parse`, `ls-files` and `check-ignore`), never writes to a path git tracks, and never touches a file it did not create. A file you edit is yours: `update` and `change` keep it and put the kit's newer copy next to it as `<file>.kit-new`; `remove` keeps it and tells you. After `remove`, the repo is byte for byte what it was before setup.

**Known limit:** `git add -f` can still add hidden files. The kit installs no git hooks, because they could clash with the team's own.

## Repository layout

```
├── README.md  ONBOARDING.md  setup.py  VERSION  CHANGELOG.md
├── roles/                 role packs: core + one folder per role
├── scripts/personal/      the code behind setup.py, its tests and the role-pack validator
├── template/              the skill library (.claude/skills) and the retired team-mode skeleton
├── scripts/install/       retired team-mode installer (its manifest code is reused)
└── docs/                  specification, roadmap (design and plan records), visuals, deck
```

## Verify locally

```bash
pip install "pyyaml>=6"                        # only the validators need it; setup.py does not
for t in scripts/personal/tests/test_*.py; do python3 "$t"; done
python3 scripts/personal/validate_packs.py
```

Kit CI ([`.github/workflows/ci.yml`](./.github/workflows/ci.yml)) also runs every template validator and test, and a `personal-e2e` job: a team repo with its own AI files, the kit copied in, setup, update and remove, ending byte-identical.

## Retired: team mode

Up to 0.3.x the kit was installed into a repo and committed there (`install.sh`, `scripts/install/`, the CI gates in `template/ci/` and `template/.github/workflows/`). Team mode is retired as of 0.4.0: those files stay in the repo as internal history and reused code, and are no longer offered or supported. See [`CHANGELOG.md`](./CHANGELOG.md).

## Contributing

Contributions are welcome. See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the workflow and [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) for community expectations. Security issues: please follow [`SECURITY.md`](./SECURITY.md) rather than opening a public issue.

## License

Released under the [MIT License](./LICENSE).
~~~~

In `CHANGELOG.md`, replace everything above `## [0.3.0] — 2026-10-07` with (the "Team mode, last changes" lines are the former Unreleased lines, verbatim):

~~~~markdown
# Changelog

All notable changes to the AI-SDLC Bootstrap Kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions: [SemVer](https://semver.org/).

**Version policy (for maintainers):**
- **MAJOR**: an adopting repo must act by hand on upgrade (renamed or removed seat, manifest schema change, removed extension point).
- **MINOR**: new role pack, skill, harness, surface or gate. Upgrades apply cleanly through "update the kit" (`setup.py update`). While the kit is 0.x, a breaking change also rides a MINOR bump.
- **PATCH**: fixes and wording, with no change to generated surfaces.
- Every PR that changes `roles/`, `scripts/personal/`, `setup.py`, `ONBOARDING.md` or `template/` adds a line under **Unreleased**. A release moves those lines under the new version and bumps `VERSION`.

## [Unreleased]

## [0.4.0] — <release date>
### Changed
- **Team mode is retired.** Nothing from the kit is committed to a shared repo any more. Each person copies the kit folder into their working copy and tells Copilot "do the onboarding"; `setup.py` places their role, language and preference files and hides every one of them from git through `.git/info/exclude`.
- `install.sh`, `scripts/install/`, `template/ci/` and `template/.github/workflows/` stay in the repo as retired, internal code; `install.sh` prints a notice. Kit CI replaces the `adopt-e2e` job with `personal-e2e`.

### Added
- `setup.py` with `setup`, `change`, `update`, `check`, `ack` and `remove`, backed by `scripts/personal/` (stdlib only, Python 3.9+).
- Role packs in `roles/`: core, Product Owner, Product Manager, Scrum Master / Team Coach (SAFe), Developer, QA, Architect and Engineering Manager, with `scripts/personal/validate_packs.py`.
- `playbook-sm`: a SAFe Scrum Master / Team Coach playbook in the skill library, used by the Scrum Master pack.
- Placed skills' relative links that leave their folder point at the same file inside `.ai-sdlc/kit/`.
- `ONBOARDING.md` at the kit root: the conversation Copilot follows (three questions: name, role(s), language).
- Warnings with stable ids when the team's own `AGENTS.md`, `.github/copilot-instructions.md`, `.github/instructions/` or skills overlap the kit's files; `ack` silences one until that team file changes.
- A session-start line in the core instructions: Copilot runs `setup.py check --quiet` once and mentions any warning, whatever the rituals setting; `--rituals status` adds a one-line summary of where the work stands.

### Team mode, last changes: added (released in 0.4.0, now retired)
- `install.sh --ci jenkins|github|none` installs only the CI governance gate a project runs (repeatable for both). The choice is recorded in `.ai-sdlc/manifest.json` and kept on re-run; without it, both gates ship as before. Switching removes the old gate's file only while it is unedited. `doctor` shows the choice.
- The generated `.github/workflows/ai-governance.yml` runs `validate-moments.py` and `validate-seat-profiles.py` when their manifests are installed, as the Jenkinsfile already did.

### Team mode, last changes: fixed
- The generated `ci/Jenkinsfile.ai-governance` no longer runs `pip install --user`, which PEP 668 refuses on Debian 12+ and Ubuntu 23.04+ agents. It uses the agent's pyyaml when importable, otherwise installs it into a gitignored `.venv-ai-governance/`, and fails with a clear message when `python3-venv` is missing.
- `--ci jenkins` no longer ships the GitHub-only docs link check (`.github/workflows/docs.yml`, `mlc-config.json`); it now belongs to the `github` gate and still needs the `standard` profile or above. Switching to Jenkins removes it while unedited.
- The generated `.github/workflows/ai-governance.yml` now runs on `minimal` and `standard` installs: steps for scripts a profile does not ship are skipped. Kit CI's `adopt-e2e` job covers all three profiles and runs the generated GitHub workflow on a fresh clone.
~~~~

`VERSION`:

```
0.4.0
```

`install.sh`: insert between `set -euo pipefail` and the `exec python3 …` line:

```bash
echo "install.sh: team mode is retired since kit 0.4.0. See README.md: copy the kit, then say \"do the onboarding\"." >&2
```

`.github/workflows/ci.yml`: no edit. The step `Personal setup unit tests` (Task 2) runs every `scripts/personal/tests/test_*.py`, so `test_release.py` runs in kit CI as soon as it exists.

**Step 4: Run the tests**

Run:
```bash
python3 scripts/personal/tests/test_release.py
python3 scripts/personal/tests/test_roles.py     # README is docs: the guidance scan does not read it
python3 scripts/install/tests/test_adopt.py      # adopt.py itself is unchanged
```
Expected: `test_release` `Ran 5 tests` `OK`; `test_roles` 7 OK; `test_adopt` 42 OK.

**Step 5: Commit**

```bash
git add README.md \
        CHANGELOG.md \
        VERSION \
        install.sh \
        scripts/personal/tests/test_release.py
git commit -F - <<'EOF'
docs: retire team mode; README leads with copy-then-onboard; 0.4.0

install.sh, scripts/install/ and the template CI files stay as retired,
internal code (personal setup reuses the manifest and frontmatter helpers);
they are no longer documented or offered.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

**Step 6: Human review checkpoint.** Show `git show --stat HEAD` and the test output and the rendered README on the PR; wait for approval before Task 16.

---

### Task 16: Full verification, then the pilot

**Step 1: The whole kit CI, locally** (from the kit root, after Task 15):

```bash
pip install --quiet "pyyaml>=6"
sed -n '/^  ai-governance:/,/^  personal-e2e:/p' .github/workflows/ci.yml \
  | grep -E '^\s+(run: )?(python3 |for t in scripts/personal/)' | sed -E 's/^ *(run: )?//' > /tmp/ci-cmds.sh
wc -l < /tmp/ci-cmds.sh
bash -e /tmp/ci-cmds.sh > /tmp/ci.log 2>&1 && echo ALL-GREEN || tail -30 /tmp/ci.log
git status --porcelain
```
Expected: `42` (the 40 from Phase 0, one loop line that runs all 14 personal suites, the pack validator), then `ALL-GREEN`, then no output from `git status`.

Expected suite counts: `test_change` 8, `test_checks` 9, `test_cli` 10, `test_conflicts` 7, `test_exclude` 11, `test_onboarding` 7, `test_packs` 16, `test_place` 17, `test_release` 5, `test_remove` 6, `test_roles` 7, `test_setup` 8, `test_state` 6, `test_update` 6 (123 new tests: 118 before the 2026-10-08 owner decisions, plus 1 in `test_roles` for Task 5c and 4 in `test_place` for the link rewrite); Phase 0 unchanged: `test_adopt` 42, `test_harness` 13, `test_manifest` 9, `test_merge` 19, `test_plan` 18, `test_harness_copilot` 29.

**Step 2: The Python floor.** With a 3.9 interpreter (macOS ships one as `/usr/bin/python3`; on the VM use whatever `python3 --version` says):

```bash
for t in scripts/personal/tests/test_*.py; do printf '%-44s ' "$t"; /usr/bin/python3 "$t" 2>&1 | tail -1; done
```
Expected: every line `OK` (`test_packs` shows `OK (skipped=1)` when that Python has no PyYAML).

**Step 3: GitHub CI.** On the PR: `ai-governance`, `personal-e2e (3.9)` and `personal-e2e (3.12)` green. Then mark the PR ready for review and use superpowers:requesting-code-review on the branch range.

**Step 4: Pilot 1, the owner, on the VM.** In a scratch clone of a real repo the owner works in:

```bash
git clone -q <real repo url> ~/pilot && cd ~/pilot && git status --porcelain     # expect nothing
# copy the kit folder in, as a person would: unzip the GitHub ZIP, or
cp -R ~/Downloads/ai-sdlc-kit ./tools-ai-sdlc-kit
code .                                     # VS Code; Copilot Chat, Agent mode
```

In the chat say **"do the onboarding"** and answer the three questions (e.g. "Emil", "architect and dev", "English"). Expected:

| # | What to see | Pass when |
|---|---|---|
| 1 | Copilot checks `python3 --version`, then runs `setup --protect-only` before asking anything | the copied folder is gone from the repo root; `.ai-sdlc/kit/` exists |
| 2 | Three questions, one at a time; afterwards Copilot speaks the chosen language | yes |
| 3 | Copilot relays "Set up AI-SDLC 0.4.0 for …" and every warning with its id; for team files it reads both sides and names only real contradictions | yes, in plain words |
| 4 | Acknowledged warnings go quiet | `python3 .ai-sdlc/kit/setup.py check` lists none of them |
| 5 | `git status --porcelain` | empty |
| 6 | New chat (and `copilot` in a terminal) | Copilot runs `check --quiet` once at the start and reports its AI-SDLC line and any warning |
| 7 | "change my preferences" → "answer in German" | replies switch to German; only the core file and USER.md changed |
| 8 | Copy a kit folder with a bumped `VERSION` in, say "update the kit" | "Updated to AI-SDLC …", status still empty |
| 9 | "remove the kit" | Copilot asks first; afterwards `git status` and `ls -a` match the fresh clone |

**Step 5: Pilot 2, one non-technical PO or PM, on the VM.** The owner prepares the clone and the kit folder on the person's desktop, then only watches and takes notes (no help unless the person is stuck for two minutes). The person's whole job: "copy the folder into the repo, open VS Code, say *do the onboarding*, answer three questions". Expected: done in under ten minutes with no git or Python words from the person, `git status` empty afterwards, and the person can say in their own words what changed. Every point where they hesitated is a finding.

**Step 6: Record and close.** Add the pilot findings to `docs/roadmap/2026-10-08-personal-setup-design.md` as a short "Pilot (<date>)" section, and mark the status line "implemented in 0.4.0".

```bash
git add docs/roadmap/2026-10-08-personal-setup-design.md
git commit -F - <<'EOF'
docs(roadmap): personal setup piloted; findings recorded

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git push
```

**Step 7: Human review checkpoint.** The owner decides: merge, or fix pilot findings first (each as its own test-first task).

**Follow-up (owner decision, 2026-10-08):** After a successful pilot, propose deleting the retired team-mode code (install.sh, scripts/install outside what personal setup imports, template/ CI files, --ci). Do NOT delete anything without the owner's explicit approval in that moment; ask first. The proposal lists every file to delete and every reused module to move under `scripts/personal/` first; nothing is deleted as part of this plan.

---

## Open questions for the owner (all decided 2026-10-08)

1. **Scrum Master's skill.** No SM playbook existed; the SM pack borrowed `playbook-em`. **Decided 2026-10-08:** the client works in SAFe, so Task 5c writes `playbook-sm`, a generic SAFe Scrum Master / Team Coach playbook (no client names), and points the `sm` pack at it. Content for the human to review line by line.
2. **Team rules win.** **Decided 2026-10-08:** when a team rule contradicts a kit rule, the team rule wins. The core instructions carry the line "If a team rule in this repo contradicts a kit rule, follow the team rule and mention the difference once." and `test_packs` asserts it (Task 4). Recorded in design §2.
3. **Git comfort when roles differ.** **Decided 2026-10-08:** the more guided git comfort wins (`git-native` < `guided` < `hidden`), as Task 4 already does; this replaces the 2026-10-07 seat design's §4a rule.
4. **Playbook links.** **Decided 2026-10-08:** rewrite them. When setup or update place a skill, relative links that leave the skill's folder point at the same file inside `.ai-sdlc/kit/`; links inside the folder, URLs and anchors stay as they are; a link with no target in the kit is left and reported (`place.rewrite_links`, Task 6a).
5. **`.claude/rules` warnings.** ~~Kept only if Task 0 check 10 shows Copilot applies them.~~ **Decided 2026-10-08:** check 10 failed, so there are none (`TEAM_RULE_DIRS = ()`, Task 8).
6. **Cleanup of retired code.** **Decided 2026-10-08:** after a successful pilot, propose deleting the retired team-mode code (`install.sh`, `scripts/install/` outside what personal setup imports, the template CI files, `--ci`), but delete nothing without the owner's explicit approval in that moment (Global constraints; follow-ups in Tasks 15 and 16).

## Follow-up (2026-10-08, owner decision): core skills

Every person gets four skills whatever their roles: `roles/core/role.json` lists `deceneus`, `drawio`, `visual-explainers` and `visual-issue`, so a future role inherits them with no skills of its own (a person can still leave one out with `change --drop-skill`). `drawio` is the upstream Copilot variant (jgraph/drawio-mcp `plugins/copilot/skills/drawio` @1da785068fde, Apache-2.0) with its references bundled, no URL or upload mode, diagrams in `docs/diagrams/`; `visual-explainers` and `visual-issue` are the owner's own, adapted for Copilot; `deceneus` is the owner's own (danemil/deceneus @01de547, MIT), limited to personal, git-hidden destinations. Each skill folder has a `PROVENANCE.md`. To support them, `place.placed_skill_files` places a skill's whole folder, file by file in `state.json`, and the person's own notes file (`.github/instructions/ai-sdlc-personal.instructions.md`) and `ai-sdlc-personal-*` skills are never reported by `check` and are kept and listed by `remove`. This supersedes the "`drawio` = vendored skill #6, Phase 4" item of the 2026-10-07 onboarding design.

## Out of scope (by design §9)

RTE/SAFe pack (the SAFe Scrum Master playbook is in v1, Task 5c); connectors (Phase 3); role discovery (v2); languages beyond en/ro/de; rituals beyond the one-line session summary; promoting a personal setup to a team setup; a fixed install location as a second kit source; local git hooks (accepted limit: `git add -f` bypasses the exclude block).

**Follow-up, not part of this plan (owner decision, 2026-10-08):** After a successful pilot, propose deleting the retired team-mode code (install.sh, scripts/install outside what personal setup imports, template/ CI files, --ci). Do NOT delete anything without the owner's explicit approval in that moment; ask first.
