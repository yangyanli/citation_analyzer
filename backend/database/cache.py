"""CRUD operations for the s2_search_cache table."""

from __future__ import annotations
import time

from backend.database.connection import get_db_connection


def get_cached_s2_paper(title: str) -> dict | None:
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM s2_search_cache WHERE title = ?", (title,)
        ).fetchone()
        if not row:
            return None
        return {
            "title": row["title"],
            "paperId": row["paper_id"],
            "citationCount": row["citation_count"],
        }


def set_cached_s2_paper(title: str, s2_data: dict) -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO s2_search_cache (title, paper_id, citation_count, timestamp)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(title) DO UPDATE SET
                paper_id=excluded.paper_id,
                citation_count=excluded.citation_count,
                timestamp=excluded.timestamp
            """,
            (title, s2_data.get("paperId"), s2_data.get("citationCount"), time.time()),
        )
