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
