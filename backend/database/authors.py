"""CRUD operations for the authors table."""

from __future__ import annotations

from backend.database.connection import get_db_connection


def get_author(name: str) -> dict | None:
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM authors WHERE name = ?", (name,)).fetchone()
        if not row:
            return None
        return dict(row)


def upsert_author(
    name: str, is_notable: bool, evidence: str = "", homepage: str = ""
) -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO authors (name, is_notable, evidence, homepage, ai_is_notable, ai_evidence, ai_homepage)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                is_notable=excluded.is_notable,
                evidence=excluded.evidence,
                homepage=excluded.homepage,
                ai_is_notable=excluded.ai_is_notable,
                ai_evidence=excluded.ai_evidence,
                ai_homepage=excluded.ai_homepage
            """,
            (name, is_notable, evidence, homepage, is_notable, evidence, homepage),
        )
