"""Where a person's connector credentials live, and how they are read and written.

One JSON file per connector, outside every repo, per user and shared by all repos:

    $AI_SDLC_CONFIG_DIR/connectors/<name>.json        (tests, power users)
    $XDG_CONFIG_HOME/ai-sdlc/connectors/<name>.json
    ~/.config/ai-sdlc/connectors/<name>.json          (default)

The folder is 0700 and each file 0600, written atomically (temp file, then rename).
Any value can also come from the environment, AI_SDLC_<NAME>_<KEY> (for example
AI_SDLC_JIRA_URL, AI_SDLC_JIRA_TOKEN); the environment wins over the file. Nothing
here prints or logs a value.
"""
from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ENV_DIR = "AI_SDLC_CONFIG_DIR"
SCHEMA = 1
_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def config_root() -> Path:
    """The ai-sdlc config folder (not created here)."""
    override = os.environ.get(ENV_DIR)
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return (Path(xdg).expanduser() if xdg else Path.home() / ".config") / "ai-sdlc"


def connectors_dir() -> Path:
    return config_root() / "connectors"


def file_for(name) -> Path:
    if not _NAME.match(name or ""):
        raise ValueError(f"not a connector name: {name!r}")
    return connectors_dir() / f"{name}.json"


def env_name(name, key) -> str:
    return f"AI_SDLC_{name}_{key}".upper().replace("-", "_")


def env_values(name, keys) -> dict:
    """{key: value} for every key set (non-empty) in the environment."""
    out = {}
    for key in keys:
        value = os.environ.get(env_name(name, key))
        if value:
            out[key] = value.strip()
    return out


def read_file(name) -> dict | None:
    """The saved document {"schema", "values", "saved_at", "last_test"}, or None."""
    path = file_for(name)
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("values"), dict):
        return None
    return doc


def load(name, keys) -> dict | None:
    """The values for `name`: the file's, overlaid by the environment's. None if neither."""
    doc = read_file(name)
    values = {k: v for k, v in (doc or {}).get("values", {}).items() if isinstance(v, str)}
    values.update(env_values(name, keys))
    return values or None


def source(name, keys) -> str | None:
    """'file', 'env', 'file+env' or None: where the values come from."""
    has_file = read_file(name) is not None
    has_env = bool(env_values(name, keys))
    if has_file and has_env:
        return "file+env"
    return "file" if has_file else "env" if has_env else None


def _ensure_dirs() -> Path:
    root, folder = config_root(), connectors_dir()
    if not root.exists():
        root.mkdir(mode=0o700, parents=True)
    if not folder.exists():
        folder.mkdir(mode=0o700)
    os.chmod(folder, 0o700)  # our folder: always private, whatever the umask said
    return folder


def _write(name, doc) -> Path:
    path = file_for(name)
    folder = _ensure_dirs()
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=path.name + ".", suffix=".tmp")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return path


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def save(name, values) -> Path:
    """Save `values` (strings) for `name`, keeping the last test result. Returns the path."""
    doc = read_file(name) or {}
    clean = {k: str(v).strip() for k, v in values.items() if v is not None and str(v).strip()}
    return _write(name, {"schema": SCHEMA, "values": clean, "saved_at": now(),
                         "last_test": doc.get("last_test")})


def record_test(name, ok, message, user=None) -> bool:
    """Note a --test result in the saved file. False when there is no file (env only)."""
    doc = read_file(name)
    if doc is None:
        return False
    doc["last_test"] = {"at": now(), "ok": bool(ok), "message": message, "user": user}
    _write(name, doc)
    return True


def delete(name) -> bool:
    path = file_for(name)
    if not path.is_file():
        return False
    path.unlink()
    return True


def saved() -> list[str]:
    folder = connectors_dir()
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob("*.json") if _NAME.match(p.stem))


def loose_permissions(name) -> bool:
    """True when the saved file can be read by other users (someone changed its mode)."""
    path = file_for(name)
    return path.is_file() and bool(stat.S_IMODE(path.stat().st_mode) & 0o077)
