#!/usr/bin/env python3
"""Unit tests for the merging session-ledger importer."""
import io
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import import_sessions as im  # noqa: E402

HDR = ",".join(im.HEADER)


def _csv(*lines):
    return io.StringIO("\n".join((HDR,) + lines) + "\n")


def _row(session_id="s1", user="ana", tin=10, tout=2, **kw):
    d = {"session_id": session_id, "ts": "2026-07-01T10:00:00", "user": user,
         "seat": "Developer", "tool": "claude", "task": "", "ticket": "PROJ-1",
         "model": "claude-opus-4-8", "tokens_in": str(tin), "tokens_out": str(tout),
         "cache_read_tokens": "0", "cost_usd": "0.5", "outcome": "unknown",
         "grounded": "0", "notes": ""}
    d.update(kw)
    return ",".join(d[k] for k in im.HEADER)


class TestRowsFromCsv(unittest.TestCase):
    def test_header_mismatch_raises_loudly(self):
        bad = io.StringIO("session_id,nope\nx,y\n")
        with self.assertRaisesRegex(ValueError, "ana.csv"):
            im.rows_from_csv(bad, "ana", "ana.csv")

    def test_malformed_rows_name_file_and_line(self):
        with self.assertRaisesRegex(ValueError, r"ana\.csv line 2"):
            im.rows_from_csv(_csv("only,two"), "ana", "ana.csv")
        with self.assertRaisesRegex(ValueError, r"ana\.csv line 2"):
            im.rows_from_csv(_csv(_row(tokens_in="NaN")), "ana", "ana.csv")
        with self.assertRaisesRegex(ValueError, r"ana\.csv line 2"):
            im.rows_from_csv(_csv(_row(session_id="")), "ana", "ana.csv")

    def test_stem_mismatch_takes_filename_and_notes_it(self):
        rows = im.rows_from_csv(_csv(_row(user="impostor")), "ana", "ana.csv")
        self.assertEqual(rows[0]["user"], "ana")
        self.assertIn("impostor", rows[0]["notes"])

    def test_clean_rows_parse(self):
        rows = im.rows_from_csv(_csv(_row(), _row(session_id="s2")), "ana", "ana.csv")
        self.assertEqual([r["session_id"] for r in rows], ["s1", "s2"])
        self.assertEqual(rows[0]["tokens_in"], 10)
        self.assertEqual(rows[0]["cost_usd"], 0.5)
        self.assertIsNone(rows[0]["task"])


class TestImportMerge(unittest.TestCase):
    def _import(self, tmp, files, db=None):
        db = db or Path(tmp) / "u.db"
        d = Path(tmp) / "sessions"
        d.mkdir(exist_ok=True)
        for name, lines in files.items():
            (d / name).write_text("\n".join([HDR] + lines) + "\n", encoding="utf-8")
        rc = im.main(["--dir", str(d), "--db", str(db)])
        self.assertEqual(rc, 0)
        return db

    def _q(self, db, sql):
        conn = sqlite3.connect(db)
        try:
            return conn.execute(sql).fetchall()
        finally:
            conn.close()

    def test_merges_two_users(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self._import(tmp, {
                "ana.csv": [_row("s1", "ana")],
                "ben.csv": [_row("s2", "ben")],
            })
            got = dict(self._q(db, "SELECT session_id, user FROM sessions "
                                   "WHERE session_id IN ('s1','s2')"))
            self.assertEqual(got, {"s1": "ana", "s2": "ben"})

    def test_greater_total_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self._import(tmp, {"ana.csv": [_row("s1", "ana", tin=100, tout=10)]})
            # smaller incoming total must NOT overwrite
            self._import(tmp, {"ana.csv": [_row("s1", "ana", tin=5, tout=1)]}, db=db)
            self.assertEqual(self._q(db, "SELECT tokens_in FROM sessions "
                                         "WHERE session_id='s1'"), [(100,)])
            # larger incoming total replaces
            self._import(tmp, {"ana.csv": [_row("s1", "ana", tin=200, tout=10)]}, db=db)
            self.assertEqual(self._q(db, "SELECT tokens_in FROM sessions "
                                         "WHERE session_id='s1'"), [(200,)])

    def test_rerun_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = {"ana.csv": [_row("s1"), _row("s9", tin=1)]}
            db = self._import(tmp, files)
            self._import(tmp, files, db=db)
            self.assertEqual(self._q(db, "SELECT COUNT(*) FROM sessions "
                                         "WHERE session_id IN ('s1','s9')"), [(2,)])

    def test_empty_dir_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "sessions"
            d.mkdir()
            self.assertEqual(im.main(["--dir", str(d),
                                      "--db", str(Path(tmp) / "u.db")]), 0)


if __name__ == "__main__":
    unittest.main()
