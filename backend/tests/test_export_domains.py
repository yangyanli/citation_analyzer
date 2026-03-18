"""Tests for scripts/export_domains.py — domain export functionality."""

import json
import sqlite3
import os
from pathlib import Path


def _init_test_db(db_path: str):
    """Initialize a test DB using the real schema via DB_PATH env var."""
    os.environ["DB_PATH"] = db_path
    # Force reimport so connection module picks up the env var
    import importlib
    import backend.database.connection as conn_mod
    importlib.reload(conn_mod)
    conn_mod.DB_PATH = Path(db_path)

    from backend.database.schema import init_db
    init_db()

    return sqlite3.connect(db_path)


def _insert(conn, target_id, target_name, citations):
    """Insert a target and its citations."""
    conn.execute(
        "INSERT OR IGNORE INTO analysis_targets (target_id, mode, name) VALUES (?, ?, ?)",
        (target_id, "scholar", target_name),
    )
    for c in citations:
        conn.execute(
            "INSERT INTO citations (citation_id, target_id, citing_title, cited_title, research_domain, score) VALUES (?, ?, ?, ?, ?, ?)",
            (c["id"], target_id, c.get("title", "Paper"), c.get("cited", "Target"), c.get("domain"), c.get("score", 5)),
        )
    conn.commit()


def _run_export(db_path, target_id, output_path):
    """Run export_domains with DB_PATH pointed at our test DB."""
    os.environ["DB_PATH"] = db_path
    import importlib
    import backend.database.connection as conn_mod
    importlib.reload(conn_mod)
    conn_mod.DB_PATH = Path(db_path)

    import scripts.export_domains as mod
    importlib.reload(mod)
    mod.export_domains(target_id, output_path)


class TestExportDomains:
    """Tests for the export_domains function."""

    def test_basic_export(self, tmp_path):
        """Exports domain distribution with correct structure."""
        db_path = str(tmp_path / "test.db")
        conn = _init_test_db(db_path)
        _insert(conn, "t1", "Dr. Test", [
            {"id": "c1", "domain": "Computer Vision", "score": 8},
            {"id": "c2", "domain": "Computer Vision", "score": 6},
            {"id": "c3", "domain": "NLP", "score": 4},
        ])
        conn.close()

        output = str(tmp_path / "out.json")
        _run_export(db_path, "t1", output)
        data = json.loads(Path(output).read_text())

        assert data["target"] == "Dr. Test"
        assert data["target_id"] == "t1"
        assert len(data["domains"]) == 2
        assert data["domains"][0]["domain"] == "Computer Vision"
        assert data["domains"][0]["count"] == 2
        assert data["domains"][1]["domain"] == "NLP"
        assert data["domains"][1]["count"] == 1

    def test_sentiment_breakdown(self, tmp_path):
        """Each domain includes sentiment score breakdown."""
        db_path = str(tmp_path / "test.db")
        conn = _init_test_db(db_path)
        _insert(conn, "t1", "Dr. Test", [
            {"id": "c1", "domain": "CV", "score": 9},
            {"id": "c2", "domain": "CV", "score": 9},
            {"id": "c3", "domain": "CV", "score": 5},
        ])
        conn.close()

        output = str(tmp_path / "out.json")
        _run_export(db_path, "t1", output)
        data = json.loads(Path(output).read_text())

        cv = data["domains"][0]
        scores = {s["score"]: s["count"] for s in cv["sentiment"]}
        assert scores[9] == 2
        assert scores[5] == 1

    def test_no_domains_exports_empty(self, tmp_path):
        """Citations without domains produce empty domains list."""
        db_path = str(tmp_path / "test.db")
        conn = _init_test_db(db_path)
        _insert(conn, "t1", "Dr. Test", [
            {"id": "c1", "domain": None, "score": 5},
        ])
        conn.close()

        output = str(tmp_path / "out.json")
        _run_export(db_path, "t1", output)
        data = json.loads(Path(output).read_text())
        assert data["domains"] == []

    def test_nonexistent_target_exits(self, tmp_path):
        """Missing target_id causes sys.exit(1)."""
        db_path = str(tmp_path / "test.db")
        conn = _init_test_db(db_path)
        conn.close()

        output = str(tmp_path / "out.json")
        import pytest
        with pytest.raises(SystemExit) as exc_info:
            _run_export(db_path, "NONEXISTENT", output)
        assert exc_info.value.code == 1

    def test_output_creates_parent_dirs(self, tmp_path):
        """Export creates parent directories if they don't exist."""
        db_path = str(tmp_path / "test.db")
        conn = _init_test_db(db_path)
        _insert(conn, "t1", "Dr. Test", [
            {"id": "c1", "domain": "ML", "score": 7},
        ])
        conn.close()

        output = str(tmp_path / "deep" / "nested" / "out.json")
        _run_export(db_path, "t1", output)
        assert Path(output).exists()

    def test_collected_date_format(self, tmp_path):
        """Collected date is in YYYY-MM-DD format."""
        db_path = str(tmp_path / "test.db")
        conn = _init_test_db(db_path)
        _insert(conn, "t1", "Dr. Test", [
            {"id": "c1", "domain": "AI", "score": 5},
        ])
        conn.close()

        output = str(tmp_path / "out.json")
        _run_export(db_path, "t1", output)
        data = json.loads(Path(output).read_text())

        import re
        assert re.match(r"\d{4}-\d{2}-\d{2}", data["collected"])

    def test_score_clamping(self, tmp_path):
        """Scores outside 0-10 range are clamped in sentiment breakdown."""
        db_path = str(tmp_path / "test.db")
        conn = _init_test_db(db_path)
        _insert(conn, "t1", "Dr. Test", [
            {"id": "c1", "domain": "Test", "score": -5},
            {"id": "c2", "domain": "Test", "score": 15},
        ])
        conn.close()

        output = str(tmp_path / "out.json")
        _run_export(db_path, "t1", output)
        data = json.loads(Path(output).read_text())

        scores = [s["score"] for s in data["domains"][0]["sentiment"]]
        assert all(0 <= s <= 10 for s in scores)

    def test_domain_ordering_by_count(self, tmp_path):
        """Domains are ordered by citation count descending."""
        db_path = str(tmp_path / "test.db")
        conn = _init_test_db(db_path)
        _insert(conn, "t1", "Dr. Test", [
            {"id": "c1", "domain": "Small", "score": 5},
            {"id": "c2", "domain": "Big", "score": 5},
            {"id": "c3", "domain": "Big", "score": 7},
            {"id": "c4", "domain": "Big", "score": 3},
            {"id": "c5", "domain": "Medium", "score": 6},
            {"id": "c6", "domain": "Medium", "score": 8},
        ])
        conn.close()

        output = str(tmp_path / "out.json")
        _run_export(db_path, "t1", output)
        data = json.loads(Path(output).read_text())

        counts = [d["count"] for d in data["domains"]]
        assert counts == sorted(counts, reverse=True)
        assert data["domains"][0]["domain"] == "Big"

    def test_json_trailing_newline(self, tmp_path):
        """Output JSON file ends with a trailing newline."""
        db_path = str(tmp_path / "test.db")
        conn = _init_test_db(db_path)
        _insert(conn, "t1", "Dr. Test", [
            {"id": "c1", "domain": "AI", "score": 5},
        ])
        conn.close()

        output = str(tmp_path / "out.json")
        _run_export(db_path, "t1", output)
        raw = Path(output).read_text()
        assert raw.endswith("\n")
