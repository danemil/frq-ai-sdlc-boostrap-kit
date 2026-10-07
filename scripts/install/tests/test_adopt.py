#!/usr/bin/env python3
"""End-to-end tests: adopt into a populated repo, then prove a re-run is a no-op.

These run the real installer against real temp repos — the greenfield case, the
brownfield case with pre-existing config, and the upgrade case.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
KIT = HERE.parents[3]

import manifest  # noqa: E402


def run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(KIT / "scripts/install/adopt.py"), *args],
        capture_output=True, text=True, cwd=cwd, env={"PATH": "/usr/bin:/bin", "NO_COLOR": "1"})


def snapshot(root):
    """Hash every file so we can prove a second run changes nothing."""
    out = {}
    for p in sorted(Path(root).rglob("*")):
        if p.is_symlink():
            out[str(p.relative_to(root))] = "link:" + str(Path(p).readlink())
        elif p.is_file() and "manifest.json" not in p.name:
            out[str(p.relative_to(root))] = manifest.sha256_file(p)
    return out


class TestGreenfield(unittest.TestCase):
    def test_empty_dir_gets_the_kit(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run("--into", tmp, "--profile", "minimal", "--yes",
                    "--harness", "claude-code", "--name", "Acme", "--ticket", "ACME")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((Path(tmp) / "AGENTS.md").is_file())
            self.assertTrue((Path(tmp) / ".claude/skills/playbook-dev/SKILL.md").is_file())
            self.assertIn("Acme", (Path(tmp) / "AGENTS.md").read_text())
            self.assertNotIn("<PROJECT_NAME>", (Path(tmp) / "AGENTS.md").read_text())

    def test_second_run_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            run("--into", tmp, "--profile", "minimal", "--yes", "--harness", "claude-code")
            before = snapshot(tmp)
            r = run("--into", tmp, "--yes")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(before, snapshot(tmp), "installer is not idempotent")

    def test_dry_run_into_an_empty_dir_wires_copilot(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run("--into", tmp, "--dry-run", "--harness", "copilot-cli")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("would generate after AGENTS.md is installed", r.stdout)


class TestBrownfield(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        root = Path(self.tmp)
        (root / "src").mkdir()
        (root / "src/main.py").write_text("print('mine')\n", encoding="utf-8")
        (root / "AGENTS.md").write_text("# My own brief\nDo not clobber me.\n", encoding="utf-8")
        (root / ".mcp.json").write_text(json.dumps(
            {"mcpServers": {"code-review-graph": {"command": "uvx",
                                                  "args": ["code-review-graph", "serve"]}}}),
            encoding="utf-8")
        (root / ".claude").mkdir()
        (root / ".claude/settings.json").write_text(json.dumps(
            {"hooks": {"PostToolUse": [{"matcher": "Edit", "hooks": [
                {"type": "command", "command": "graph update"}]}]}}), encoding="utf-8")
        (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_existing_files_survive(self):
        r = run("--into", self.tmp, "--profile", "standard", "--yes",
                "--harness", "claude-code", "--harness", "codex-cli")
        self.assertEqual(r.returncode, 0, r.stderr)
        root = Path(self.tmp)

        # the operator's own code and brief are untouched
        self.assertEqual((root / "src/main.py").read_text(), "print('mine')\n")
        self.assertIn("Do not clobber me", (root / "AGENTS.md").read_text())

        # .mcp.json gained the kit's servers and kept theirs
        servers = json.loads((root / ".mcp.json").read_text())["mcpServers"]
        self.assertIn("code-review-graph", servers)
        self.assertIn("knowledge", servers)

        # their hook survived; the kit's was added and tagged
        hooks = json.loads((root / ".claude/settings.json").read_text())["hooks"]
        self.assertEqual(hooks["PostToolUse"][0]["hooks"][0]["command"], "graph update")
        self.assertIn("SessionStart", hooks)

        # .gitignore kept its line and gained a sentinel block
        gitignore = (root / ".gitignore").read_text()
        self.assertIn("node_modules/", gitignore)
        self.assertIn(">>> ai-sdlc >>>", gitignore)

    def test_dry_run_writes_nothing(self):
        before = snapshot(self.tmp)
        r = run("--into", self.tmp, "--profile", "full", "--dry-run", "--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(before, snapshot(self.tmp))
        self.assertFalse((Path(self.tmp) / ".ai-sdlc/manifest.json").exists())

    def test_seed_conflict_is_deferred_not_clobbered(self):
        run("--into", self.tmp, "--yes", "--harness", "claude-code")
        man = manifest.load(self.tmp)
        self.assertNotIn("AGENTS.md", man["files"])   # seed file left as theirs
        self.assertIn("Do not clobber me", (Path(self.tmp) / "AGENTS.md").read_text())

    def test_take_kit_overwrites_owned_conflicts(self):
        root = Path(self.tmp)
        (root / "scripts").mkdir(exist_ok=True)
        (root / "scripts/validate-skills.py").write_text("# stale\n", encoding="utf-8")
        run("--into", self.tmp, "--take-kit", "--harness", "claude-code")
        self.assertIn("agentskills.io", (root / "scripts/validate-skills.py").read_text())

    def test_brownfield_rerun_is_idempotent(self):
        run("--into", self.tmp, "--profile", "full", "--yes",
            "--harness", "claude-code", "--harness", "codex-cli", "--harness", "copilot-cli")
        before = snapshot(self.tmp)
        run("--into", self.tmp, "--yes")
        self.assertEqual(before, snapshot(self.tmp), "brownfield re-run is not idempotent")


class TestHarnessWiring(unittest.TestCase):
    def test_codex_and_copilot_surfaces(self):
        import tomllib
        with tempfile.TemporaryDirectory() as tmp:
            run("--into", tmp, "--profile", "standard", "--yes",
                "--harness", "claude-code", "--harness", "codex-cli",
                "--harness", "copilot-cli")
            root = Path(tmp)

            # Codex: project config carries MCP + a hooks pointer; skills symlinked
            cfg = tomllib.loads((root / ".codex/config.toml").read_text())
            self.assertIn("knowledge", cfg["mcp_servers"])
            self.assertEqual(cfg["hooks"], "./hooks.json")
            self.assertTrue((root / ".codex/skills").is_symlink())
            self.assertTrue((root / ".codex/skills/playbook-qa/SKILL.md").is_file())

            # Codex hooks mirror Claude's, minus Claude-only events
            hooks = json.loads((root / ".codex/hooks.json").read_text())["hooks"]
            self.assertIn("SessionStart", hooks)
            self.assertNotIn("SessionEnd", hooks)

            # Copilot: generated MCP file, and no duplicated skills tree
            copilot = json.loads((root / ".copilot/mcp-config.json").read_text())
            self.assertEqual(copilot["mcpServers"]["knowledge"]["type"], "local")
            self.assertFalse((root / ".github/skills").exists())
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

    def test_wiring_does_not_overwrite_the_shipped_claude_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            run("--into", tmp, "--profile", "minimal", "--yes", "--harness", "claude-code")
            shipped = (Path(tmp) / "CLAUDE.md").read_text()
            template = (KIT / "template/CLAUDE.md").read_text()
            self.assertEqual(shipped, template)
            self.assertIn(".claude/skills", shipped)   # Claude-specific detail survives

    def test_pointer_harnesses_carry_no_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            run("--into", tmp, "--profile", "minimal", "--yes",
                "--harness", "claude-code", "--harness", "gemini-cli", "--harness", "cursor")
            gemini = (Path(tmp) / "GEMINI.md").read_text()
            self.assertIn("AGENTS.md", gemini)
            self.assertLess(len(gemini.splitlines()), 20)     # a pointer, not a copy
            self.assertTrue((Path(tmp) / ".cursor/rules/ai-sdlc.mdc").is_file())
            # the legacy path must not be left holding a stale copy of the brief
            legacy = (Path(tmp) / ".cursorrules").read_text()
            self.assertIn("AGENTS.md", legacy)
            self.assertNotIn("---", legacy.splitlines()[0])   # plain md, not .mdc

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

    def test_removed_orphan_is_forgotten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude/rules").mkdir(parents=True)
            (root / ".claude/rules/local.md").write_text("# Local rule\n", encoding="utf-8")
            run("--into", tmp, "--profile", "minimal", "--yes", "--harness", "copilot-cli")
            rel = ".github/instructions/local.instructions.md"
            self.assertIn(rel, manifest.load(tmp)["files"])
            (root / ".claude/rules/local.md").unlink()
            out = run("--into", tmp, "--yes").stdout
            self.assertIn("local.instructions.md (removed)", out)
            self.assertNotIn("(removed) (generated)", out)
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


class TestStandaloneSync(unittest.TestCase):
    """The generated project must drift-check itself with no kit checked out."""

    def sync(self, root, *args):
        return subprocess.run(
            [sys.executable, "scripts/harness/sync.py", *args],
            capture_output=True, text=True, cwd=root,
            env={"PATH": "/usr/bin:/bin", "NO_COLOR": "1"})

    def test_check_write_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            run("--into", tmp, "--profile", "standard", "--yes",
                "--harness", "claude-code", "--harness", "codex-cli",
                "--harness", "copilot-cli")
            self.assertEqual(self.sync(tmp, "--check").returncode, 0)

            mcp = Path(tmp) / ".mcp.json"
            data = json.loads(mcp.read_text())
            data["mcpServers"]["newthing"] = {"command": "foo", "args": ["bar"]}
            mcp.write_text(json.dumps(data, indent=2), encoding="utf-8")

            drifted = self.sync(tmp, "--check")
            self.assertEqual(drifted.returncode, 1)
            self.assertIn(".copilot/mcp-config.json", drifted.stderr)

            self.assertEqual(self.sync(tmp, "--write").returncode, 0)
            self.assertEqual(self.sync(tmp, "--check").returncode, 0)
            self.assertIn("[mcp_servers.newthing]",
                          (Path(tmp) / ".codex/config.toml").read_text())
            agents = Path(tmp) / "AGENTS.md"
            agents.write_text(agents.read_text() + "\n", encoding="utf-8")
            self.assertEqual(self.sync(tmp, "--check").returncode, 0,
                             "trailing newline outside §0/§3 must not drift")
            text = agents.read_text().replace("No fabrication", "No fabrication, ever")
            agents.write_text(text, encoding="utf-8")
            drifted = self.sync(tmp, "--check")
            self.assertEqual(drifted.returncode, 1)
            self.assertIn(".github/copilot-instructions.md", drifted.stderr)

    def test_sync_ships_with_the_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            run("--into", tmp, "--profile", "minimal", "--yes", "--harness", "claude-code")
            for rel in ("scripts/harness/sync.py", "scripts/harness/merge.py",
                        "scripts/harness/harnesses.json"):
                self.assertTrue((Path(tmp) / rel).is_file(), rel)


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


class TestDoctorAndUninstall(unittest.TestCase):
    def test_doctor_flags_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            run("--into", tmp, "--profile", "minimal", "--yes",
                "--harness", "claude-code", "--harness", "copilot-cli")
            self.assertIn("none", run("--into", tmp, "doctor").stdout)
            (Path(tmp) / ".copilot/mcp-config.json").write_text('{"mcpServers":{}}',
                                                                encoding="utf-8")
            out = run("--into", tmp, "doctor")
            self.assertIn("drift", out.stdout)
            self.assertEqual(out.returncode, 1)

    def test_doctor_reports_real_placeholders_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            run("--into", tmp, "--profile", "minimal", "--yes", "--harness", "claude-code")
            out = run("--into", tmp, "doctor").stdout
            self.assertIn("<TICKET>", out)          # operator must fill this
            self.assertNotIn("<NNNN>", out)         # an example inside prose
            self.assertNotIn("<KEY>", out)

    def test_doctor_scans_the_brief_even_when_it_is_unmanaged(self):
        """A seed AGENTS.md the installer skipped must still be checked."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "AGENTS.md").write_text(
                "# Mine\nOwner: <SEAT_HOLDERS>\n", encoding="utf-8")
            run("--into", tmp, "--profile", "minimal", "--yes", "--harness", "claude-code")
            man = json.loads((Path(tmp) / ".ai-sdlc/manifest.json").read_text())
            self.assertNotIn("AGENTS.md", man["files"])      # unmanaged, as designed
            out = run("--into", tmp, "doctor").stdout
            self.assertIn("AGENTS.md", out)
            self.assertIn("<SEAT_HOLDERS>", out)

    def test_doctor_skips_unconfigured_mcp_servers(self):
        with tempfile.TemporaryDirectory() as tmp:
            run("--into", tmp, "--profile", "minimal", "--yes",
                "--harness", "claude-code", "--harness", "copilot-cli")
            out = run("--into", tmp, "doctor").stdout
            self.assertIn("docs-wiki (unfilled placeholder)", out)
            copilot = json.loads((Path(tmp) / ".copilot/mcp-config.json").read_text())
            self.assertNotIn("docs-wiki", copilot["mcpServers"])

    def test_uninstall_keeps_your_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
            run("--into", tmp, "--profile", "minimal", "--yes", "--harness", "claude-code")
            self.assertTrue((root / "scripts/validate-skills.py").is_file())
            run("--into", tmp, "uninstall")
            self.assertFalse((root / "scripts/validate-skills.py").exists())
            self.assertTrue((root / "AGENTS.md").is_file())       # seed: yours now
            self.assertIn("node_modules/", (root / ".gitignore").read_text())
            self.assertNotIn("ai-sdlc", (root / ".gitignore").read_text())

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



class TestInheritedDebt(unittest.TestCase):
    """Adopting a repo with pre-kit docs must not hand the team a red gate."""

    def test_first_adopt_baselines_existing_violations(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            docs.mkdir()
            (docs / "legacy.md").write_text("# No frontmatter here\n", encoding="utf-8")

            r = run("--into", tmp, "--profile", "minimal", "--yes", "--harness", "claude-code")
            self.assertEqual(r.returncode, 0, r.stderr)

            baseline = Path(tmp) / ".ai-sdlc/frontmatter-baseline.txt"
            self.assertTrue(baseline.is_file())
            self.assertIn("docs/legacy.md", baseline.read_text())

            gate = subprocess.run(
                [sys.executable, "scripts/validate-frontmatter.py"],
                cwd=tmp, capture_output=True, text=True,
                env={"PATH": "/usr/bin:/bin", "NO_COLOR": "1"})
            self.assertEqual(gate.returncode, 0, gate.stdout)
            self.assertIn("debt", gate.stdout)

    def test_a_new_violation_still_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            docs.mkdir()
            (docs / "legacy.md").write_text("# Old\n", encoding="utf-8")
            run("--into", tmp, "--profile", "minimal", "--yes", "--harness", "claude-code")
            (docs / "brand-new.md").write_text("# Added after adoption\n", encoding="utf-8")

            gate = subprocess.run(
                [sys.executable, "scripts/validate-frontmatter.py"],
                cwd=tmp, capture_output=True, text=True,
                env={"PATH": "/usr/bin:/bin", "NO_COLOR": "1"})
            self.assertEqual(gate.returncode, 1)
            self.assertIn("FAIL  docs/brand-new.md", gate.stdout)
            self.assertIn("debt  docs/legacy.md", gate.stdout)

    def test_doctor_keeps_the_debt_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            docs.mkdir()
            (docs / "legacy.md").write_text("# Old\n", encoding="utf-8")
            run("--into", tmp, "--profile", "minimal", "--yes", "--harness", "claude-code")
            self.assertIn("Inherited doc debt", run("--into", tmp, "doctor").stdout)


JENKINSFILE = "ci/Jenkinsfile.ai-governance"
WORKFLOW = ".github/workflows/ai-governance.yml"


class TestCiChoice(unittest.TestCase):
    """--ci picks the governance gate: the Jenkinsfile, the GitHub workflow, both, or none."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def install(self, *extra):
        return run("--into", self.tmp, "--profile", "minimal", "--yes",
                   "--harness", "claude-code", *extra)

    def gates(self):
        return {rel for rel in (JENKINSFILE, WORKFLOW) if (self.root / rel).is_file()}

    def recorded(self):
        return json.loads((self.root / ".ai-sdlc/manifest.json").read_text())

    def test_ci_jenkins_installs_only_the_jenkinsfile(self):
        r = self.install("--ci", "jenkins")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.gates(), {JENKINSFILE})

    def test_ci_github_installs_only_the_workflow(self):
        r = self.install("--ci", "github")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.gates(), {WORKFLOW})

    def test_ci_none_installs_neither(self):
        r = self.install("--ci", "none")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.gates(), set())
        self.assertEqual(self.recorded()["ci"], [])

    def test_no_flag_installs_both(self):
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.gates(), {JENKINSFILE, WORKFLOW})

    def test_choice_persists_across_a_rerun(self):
        self.install("--ci", "jenkins")
        self.assertEqual(self.recorded()["ci"], ["jenkins"])
        r = run("--into", self.tmp, "--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.gates(), {JENKINSFILE})
        self.assertEqual(self.recorded()["ci"], ["jenkins"])

    def test_switch_removes_the_clean_gate(self):
        self.install("--ci", "jenkins")
        r = self.install("--ci", "github")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.gates(), {WORKFLOW})
        self.assertFalse((self.root / "ci").exists(), "empty ci/ left behind")
        self.assertNotIn(JENKINSFILE, self.recorded()["files"])

    def test_switch_keeps_an_edited_gate(self):
        self.install("--ci", "jenkins")
        jf = self.root / JENKINSFILE
        jf.write_text(jf.read_text() + "// our extra stage\n", encoding="utf-8")
        r = self.install("--ci", "github")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.gates(), {JENKINSFILE, WORKFLOW})
        self.assertIn("our extra stage", jf.read_text())
        notes = [l for l in r.stdout.splitlines() if JENKINSFILE in l and "kept your edits" in l]
        self.assertTrue(notes, r.stdout)
        self.assertNotIn(JENKINSFILE, self.recorded()["files"])  # yours now; uninstall keeps it

    def test_doctor_shows_the_choice(self):
        self.install("--ci", "jenkins")
        out = run("--into", self.tmp, "doctor").stdout
        self.assertIn("ci jenkins", out)
        self.assertIn("Script Path", out)

    def test_unknown_ci_value_is_rejected(self):
        r = self.install("--ci", "gitlab")
        self.assertEqual(r.returncode, 2)
        self.assertIn("argument --ci: invalid choice: 'gitlab'", r.stderr)
        r = self.install("--ci", "none", "--ci", "jenkins")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--ci none cannot be combined", r.stderr)
        self.assertEqual(self.gates(), set())


if __name__ == "__main__":
    unittest.main(verbosity=1)
