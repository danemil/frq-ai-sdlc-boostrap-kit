#!/usr/bin/env python3
"""Installer-side view of the harness adapters.

The implementation lives in the *template* (`template/scripts/harness/sync.py`),
because the generated project has to regenerate and drift-check its own derived
surfaces without the kit checked out next to it. The installer is a consumer of
that module, not a second copy of it.
"""
from __future__ import annotations

import sys
from pathlib import Path

_TEMPLATE_HARNESS = Path(__file__).resolve().parents[2] / "template/scripts/harness"
sys.path.insert(0, str(_TEMPLATE_HARNESS))

from sync import (  # noqa: E402,F401
    COPILOT_FORMATS, POINTER_MD, POINTER_MDC, TABLE_REL,
    check, detect, load_table, materialize, mcp_servers, orphan_instructions,
    pointer_text, probe, to_codex_hooks, to_codex_toml, to_copilot_mcp, unconfigured,
)
