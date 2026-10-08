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
