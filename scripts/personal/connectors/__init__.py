"""Personal connectors: read-only access to Jira, Confluence, Bitbucket, Jama and Jenkins.

Foundation modules (store, http, registry, manage, text) are shared. Every other
module here is one connector, found by `registry.discover()`; see registry.py for
the contract. Design: docs/roadmap/2026-10-08-connectors-design.md.
"""
