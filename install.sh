#!/usr/bin/env bash
# install.sh — adopt the AI-SDLC Bootstrap Kit into a repo (new or existing).
#
#   ./install.sh --into ../my-repo                 # interactive adopt
#   ./install.sh --into ../my-repo --dry-run       # show the plan, write nothing
#   ./install.sh --into ../my-repo --profile full
#   ./install.sh --into ../my-repo doctor          # verify wiring + drift
#   ./install.sh --into ../my-repo uninstall
#
# Greenfield is the zero-conflict case of the same code path; see
# docs/roadmap/2026-08-28-brownfield-adoption-design.md.
set -euo pipefail
exec python3 "$(cd "$(dirname "$0")" && pwd)/scripts/install/adopt.py" "$@"
