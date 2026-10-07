"""Deck data sources (Gather unit). Each source returns (rows, source_meta) or
raises SourceUnavailable, which the CLI records as tier `unavailable` so the
run continues and the affected slides say "Not measured". Design §3."""


class SourceUnavailable(Exception):
    """A scripted source cannot run (no config, no auth, unreachable)."""
