#!/usr/bin/env python3
"""Unit tests for the deck Jira source (deck-builder design §3.1, §3.3). No network."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sources import SourceUnavailable
from sources import jira_snapshot as js

FIX = Path(__file__).resolve().parent / "fixtures"
CLOUD = json.loads((FIX / "jira_cloud_search.json").read_text(encoding="utf-8"))["issues"]
DC = json.loads((FIX / "jira_dc_search.json").read_text(encoding="utf-8"))["issues"]

LEDGER_CLOUD = {"deployment": "cloud", "base_url_env": "JIRA_BASE_URL", "project": "ATM",
                "fields": {"sprint": "customfield_10020", "epic_link": "customfield_10014",
                           "story_points": "customfield_10016"}}
LEDGER_DC = dict(LEDGER_CLOUD, deployment="datacenter")
DECK_FIELDS = {"jira": {"fields": {"acceptance_criteria": "customfield_10500",
                                   "doc_update": "customfield_10600"},
                        "dependency_link_types": ["Blocks", "Depends"]},
               "jama": {"link_match": "^Jama|^SSR-"}}
DECK_DESC = {"jira": {"fields": {"acceptance_criteria": "description:Acceptance criteria",
                                 "doc_update": "label:docs-updated"}},
             "jama": {"link_match": "^Jama|^SSR-"}}
BASE = "https://jira.example.com"


def by_key(items):
    return {i["key"]: i for i in items}


class ConfigTest(unittest.TestCase):
    def test_deck_config_adds_extra_and_custom_fields_without_breaking_ledger_keys(self):
        cfg = js.deck_jira_config(LEDGER_CLOUD, DECK_FIELDS, {"projects": ["ATM"]})
        requested = set(cfg["fields"].values())
        for f in js.EXTRA_FIELDS + ["customfield_10500", "customfield_10600", "customfield_10016"]:
            self.assertIn(f, requested)
        self.assertEqual(cfg["fields"]["story_points"], "customfield_10016")
        self.assertNotIn("description:Acceptance criteria", requested)
        self.assertIsNot(cfg["fields"], LEDGER_CLOUD["fields"])  # ledger cfg untouched

    def test_description_and_label_modes_request_no_custom_field(self):
        cfg = js.deck_jira_config(LEDGER_CLOUD, DECK_DESC, {"projects": ["ATM"]})
        self.assertFalse(any(v.startswith(("description:", "label:")) for v in cfg["fields"].values()))

    def test_scoped_jql(self):
        self.assertEqual(js.scoped_jql({"projects": ["ATM", "NAV"], "sprint": 'ATM "Sprint" 42'}, "X"),
                         'project in ("ATM", "NAV") AND sprint = "ATM \\"Sprint\\" 42" ORDER BY key ASC')
        self.assertEqual(js.scoped_jql({"release": "R5.2"}, "ATM"),
                         'project in ("ATM") AND fixVersion = "R5.2" ORDER BY key ASC')
        self.assertEqual(js.scoped_jql({"since": "2026-10-01", "until": "2026-10-31"}, "ATM"),
                         'project in ("ATM") AND updated >= "2026-10-01" AND updated <= "2026-10-31" '
                         'ORDER BY key ASC')
        self.assertEqual(js.scoped_jql({"jql": "filter = 123"}, "ATM"), "filter = 123")


class CloudNormalizeTest(unittest.TestCase):
    def setUp(self):
        cfg = js.deck_jira_config(LEDGER_CLOUD, DECK_FIELDS, {"projects": ["ATM"]})
        self.items = by_key([js.normalize_work_item(r, cfg, DECK_FIELDS, BASE) for r in CLOUD])

    def test_core_fields(self):
        i = self.items["ATM-10"]
        self.assertEqual((i["type"], i["status"], i["status_category"]), ("Story", "In Progress", "indeterminate"))
        self.assertEqual(i["assignee"], "Ada")
        self.assertEqual(i["story_points"], 8)
        self.assertEqual(i["sprints"], ["ATM Sprint 41", "ATM Sprint 42"])
        self.assertEqual(i["components"], ["Radio", "VCS"])
        self.assertEqual(i["fix_versions"], ["R5.2"])
        self.assertEqual(i["subtask_count"], 2)
        self.assertEqual((i["parent"], i["epic"]), ("ATM-1", "ATM-1"))
        self.assertEqual(i["url"], f"{BASE}/browse/ATM-10")

    def test_links_with_direction_and_status_category(self):
        links = self.items["ATM-10"]["links"]
        self.assertIn({"type": "Blocks", "direction": "inward", "key": "NAV-77",
                       "status_category": "new"}, links)
        self.assertIn({"type": "Relates", "direction": "outward", "key": "ATM-20",
                       "status_category": "done"}, links)

    def test_requirement_links_match_jama(self):
        self.assertEqual(self.items["ATM-10"]["requirement_links"], ["SSR-301"])
        self.assertEqual(self.items["ATM-2"]["requirement_links"], [])

    def test_acceptance_criteria_and_doc_update_from_custom_fields(self):
        self.assertIs(self.items["ATM-10"]["acceptance_criteria"], True)
        self.assertIs(self.items["ATM-2"]["acceptance_criteria"], False)
        self.assertEqual(self.items["ATM-10"]["doc_update"], "Done")
        self.assertEqual(self.items["ATM-2"]["doc_update"], "missing")

    def test_empty_values(self):
        i = self.items["ATM-2"]
        self.assertIsNone(i["story_points"])
        self.assertEqual((i["assignee"], i["sprints"], i["components"], i["links"]), ("", [], [], []))

    def test_acceptance_criteria_from_adf_description_heading(self):
        cfg = js.deck_jira_config(LEDGER_CLOUD, DECK_DESC, {"projects": ["ATM"]})
        items = by_key([js.normalize_work_item(r, cfg, DECK_DESC, BASE) for r in CLOUD])
        self.assertIs(items["ATM-2"]["acceptance_criteria"], True)
        self.assertIs(items["ATM-10"]["acceptance_criteria"], False)


class DataCenterNormalizeTest(unittest.TestCase):
    def setUp(self):
        cfg = js.deck_jira_config(LEDGER_DC, DECK_DESC, {"projects": ["ATM"]})
        self.items = by_key([js.normalize_work_item(r, cfg, DECK_DESC, BASE) for r in DC])

    def test_greenhopper_sprint_strings(self):
        self.assertEqual(self.items["ATM-7"]["sprints"], ["ATM Sprint 40", "ATM Sprint 41"])

    def test_wiki_markup_heading_needs_content_after_it(self):
        self.assertIs(self.items["ATM-7"]["acceptance_criteria"], True)
        self.assertIs(self.items["ATM-8"]["acceptance_criteria"], False)

    def test_label_mode_doc_update(self):
        self.assertEqual(self.items["ATM-7"]["doc_update"], "done")
        self.assertEqual(self.items["ATM-8"]["doc_update"], "missing")

    def test_done_item_and_dependency(self):
        i = self.items["ATM-7"]
        self.assertEqual((i["status_category"], i["resolved"]), ("done", "2026-09-05T09:00:00.000+0200"))
        self.assertEqual(i["links"], [{"type": "Depends", "direction": "outward", "key": "ATM-8",
                                       "status_category": "new"}])
        self.assertEqual(i["story_points"], 3)

    def test_unconfigured_fields_are_unknown_not_missing(self):
        items = [js.normalize_work_item(r, LEDGER_DC, {"jira": {"fields": {}}}, BASE) for r in DC]
        for i in items:
            self.assertIsNone(i["acceptance_criteria"])
            self.assertEqual(i["doc_update"], "n/a")
            self.assertIsNone(i["requirement_links"])


class FetchTest(unittest.TestCase):
    def test_fetch_uses_injected_fetch_all_and_sorts_naturally(self):
        seen = {}

        def fake_fetch_all(cfg):
            seen["jql"] = cfg["jql"]
            return BASE, CLOUD

        items, meta = js.fetch(DECK_FIELDS, {"projects": ["ATM"]}, ledger_cfg=LEDGER_CLOUD,
                               fetch_all=fake_fetch_all)
        self.assertEqual([i["key"] for i in items], ["ATM-2", "ATM-10"])
        self.assertEqual(meta, {"tier": "script", "query": seen["jql"], "count": 2,
                                "deployment": "cloud"})

    def test_missing_auth_becomes_source_unavailable(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SourceUnavailable) as ctx:
                js.fetch(DECK_FIELDS, {"projects": ["ATM"]}, ledger_cfg=LEDGER_CLOUD)
        self.assertIn("JIRA_BASE_URL", str(ctx.exception))

    def test_missing_ledger_config_becomes_source_unavailable(self):
        with self.assertRaises(SourceUnavailable):
            js.fetch({"jira": {"config": "does/not/exist.json"}}, {"projects": ["ATM"]})


if __name__ == "__main__":
    unittest.main()
