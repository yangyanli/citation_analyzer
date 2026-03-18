"""CRUD operations for the citations table."""

from __future__ import annotations
import json
import sqlite3
import logging

from backend.database.connection import get_db_connection

logger = logging.getLogger("citation_analyzer")


def insert_citation_if_missing(citation_id: str, data: dict) -> bool:
    """Inserts a pending citation. Returns True if inserted, False if it already exists."""
    with get_db_connection() as conn:
        try:
            conn.execute(
                """
                INSERT INTO citations (
                    citation_id, target_id, cited_title, cited_paper_id,
                    citing_title, url,
                    year, venue, citing_citation_count, is_self_citation,
                    raw_contexts, authors
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    citation_id,
                    data.get("target_id", ""),
                    data["cited_title"],
                    data.get("cited_paper_id"),
                    data["citing_title"],
                    data.get("url"),
                    data.get("year"),
                    data.get("venue"),
                    data.get("citing_citation_count", 0),
                    data.get("is_self_citation", False),
                    json.dumps(data.get("contexts", [])),
                    json.dumps(data.get("authors", [])),
                ),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def get_unscored_citations(target_id: str) -> list[dict]:
    """Fetch citations that need Gemini sentiment analysis."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM citations WHERE target_id = ? AND score IS NULL",
            (target_id,),
        ).fetchall()

        results: list[dict] = []
        for row in rows:
            d = dict(row)
            d["raw_contexts"] = (
                json.loads(d["raw_contexts"]) if d["raw_contexts"] else []
            )
            d["notable_authors"] = (
                json.loads(d["notable_authors"]) if d["notable_authors"] else []
            )
            d["research_domain"] = d.get("research_domain")
            results.append(d)
        return results


def get_citation(citation_id: str, target_id: str | None = None) -> dict | None:
    with get_db_connection() as conn:
        if target_id:
            row = conn.execute(
                "SELECT * FROM citations WHERE citation_id = ? AND target_id = ?",
                (citation_id, target_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM citations WHERE citation_id = ?", (citation_id,)
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["raw_contexts"] = json.loads(d["raw_contexts"]) if d["raw_contexts"] else []
        d["notable_authors"] = (
            json.loads(d["notable_authors"]) if d["notable_authors"] else []
        )
        d["research_domain"] = d.get("research_domain")
        return d


def update_citation_sentiment_only(
    citation_id: str, score_data: dict, version: str, target_id: str | None = None
) -> None:
    """Update a citation with Gemini sentiment outputs (Phase 4)."""
    with get_db_connection() as conn:
        if target_id:
            where = "WHERE citation_id = ? AND target_id = ?"
            params_suffix = (citation_id, target_id)
        else:
            where = "WHERE citation_id = ?"
            params_suffix = (citation_id,)
        conn.execute(
            f"""
            UPDATE citations SET
                score = ?,
                usage_classification = ?,
                positive_comment = ?,
                sentiment_evidence = ?,
                paper_homepage = ?,
                version = ?,
                ai_score = ?,
                ai_usage_classification = ?,
                ai_positive_comment = ?,
                ai_sentiment_evidence = ?
            {where}
            """,
            (
                score_data.get("score"),
                score_data.get("usage_classification", "Discussing"),
                score_data.get("positive_comment"),
                score_data.get("sentiment_evidence"),
                score_data.get("paper_homepage"),
                version,
                score_data.get("score"),
                score_data.get("usage_classification", "Discussing"),
                score_data.get("positive_comment"),
                score_data.get("sentiment_evidence"),
                *params_suffix,
            ),
        )


def get_all_citations(target_id: str | None = None) -> list[dict]:
    """Fetch structured citations for the frontend API."""
    with get_db_connection() as conn:
        query = "SELECT * FROM citations"
        params = ()
        if target_id:
            query += " WHERE target_id = ?"
            params = (target_id,)

        rows = conn.execute(query, params).fetchall()
        results: list[dict] = []
        for row in rows:
            d = dict(row)
            d["raw_contexts"] = (
                json.loads(d["raw_contexts"]) if d["raw_contexts"] else []
            )
            d["notable_authors"] = (
                json.loads(d["notable_authors"]) if d["notable_authors"] else []
            )
            d["research_domain"] = d.get("research_domain")
            results.append(d)
        return results


def wipe_phase_data(target_id: str, phase: int) -> None:
    """Wipes analysis and AI column data for a specific phase (2, 3, 4 only).
    Phase 1 cannot be wiped to preserve S2 foreign key citations.
    """
    if phase not in (2, 3, 4, 5):
        raise ValueError("Only phases 2, 3, 4, and 5 can be wiped safely.")

    with get_db_connection() as conn:
        if phase == 2:
            conn.execute(
                "UPDATE citations SET notable_authors = NULL WHERE target_id = ?",
                (target_id,),
            )
            logger.info(f"Target {target_id}: Wiped Phase 2 citation notable_authors data.")

        elif phase == 3:
            conn.execute(
                """
                UPDATE citations SET
                    is_seminal = 0,
                    seminal_evidence = NULL,
                    ai_is_seminal = 0,
                    ai_seminal_evidence = NULL
                WHERE target_id = ?
                """,
                (target_id,),
            )
            logger.info(f"Target {target_id}: Wiped Phase 3 seminal discovery data.")

        elif phase == 4:
            conn.execute(
                """
                UPDATE citations SET
                    score = NULL,
                    usage_classification = 'Pending',
                    positive_comment = NULL,
                    sentiment_evidence = NULL,
                    ai_score = NULL,
                    ai_usage_classification = NULL,
                    ai_positive_comment = NULL,
                    ai_sentiment_evidence = NULL
                WHERE target_id = ?
                """,
                (target_id,),
            )
            logger.info(f"Target {target_id}: Wiped Phase 4 sentiment analysis data.")

        elif phase == 5:
            conn.execute(
                "UPDATE citations SET research_domain = NULL WHERE target_id = ?",
                (target_id,),
            )
            logger.info(f"Target {target_id}: Wiped Phase 5 research domain data.")


def update_citation_authors(citation_id: str, notable_authors_json: str, target_id: str | None = None) -> None:
    """Attach the JSON array of notable authors to a citation."""
    with get_db_connection() as conn:
        if target_id:
            conn.execute(
                "UPDATE citations SET notable_authors = ? WHERE citation_id = ? AND target_id = ?",
                (notable_authors_json, citation_id, target_id),
            )
        else:
            conn.execute(
                "UPDATE citations SET notable_authors = ? WHERE citation_id = ?",
                (notable_authors_json, citation_id),
            )


def update_citation_seminal(citation_id: str, is_seminal: bool, evidence: str, target_id: str | None = None) -> None:
    """Update a citation's seminal discovery status (Phase 3)."""
    with get_db_connection() as conn:
        if target_id:
            where = "WHERE citation_id = ? AND target_id = ?"
            params_suffix = (citation_id, target_id)
        else:
            where = "WHERE citation_id = ?"
            params_suffix = (citation_id,)
        conn.execute(
            f"""
            UPDATE citations SET
                is_seminal = ?,
                seminal_evidence = ?,
                ai_is_seminal = ?,
                ai_seminal_evidence = ?
            {where}
            """,
            (is_seminal, evidence, is_seminal, evidence, *params_suffix),
        )


def update_citation_domain(citation_id: str, domain: str, target_id: str | None = None) -> None:
    """Update a citation's research domain (Phase 5)."""
    with get_db_connection() as conn:
        if target_id:
            conn.execute(
                "UPDATE citations SET research_domain = ? WHERE citation_id = ? AND target_id = ?",
                (domain, citation_id, target_id),
            )
        else:
            conn.execute(
                "UPDATE citations SET research_domain = ? WHERE citation_id = ?",
                (domain, citation_id),
            )


def get_unclassified_citations(target_id: str) -> list[dict]:
    """Fetch citations that have no research domain assigned yet."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM citations WHERE target_id = ? AND research_domain IS NULL",
            (target_id,),
        ).fetchall()

        results: list[dict] = []
        for row in rows:
            d = dict(row)
            d["raw_contexts"] = (
                json.loads(d["raw_contexts"]) if d["raw_contexts"] else []
            )
            d["notable_authors"] = (
                json.loads(d["notable_authors"]) if d["notable_authors"] else []
            )
            d["research_domain"] = d.get("research_domain")
            results.append(d)
        return results


# ── Cross-target sharing helpers ──────────────────────────────────────


def find_shared_domain(
    citation_id: str, target_id: str, max_age_days: int = 30
) -> str | None:
    """Find a research domain for this citation_id from another target (within max_age_days)."""
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT research_domain FROM citations
            WHERE citation_id = ? AND target_id != ?
              AND research_domain IS NOT NULL
              AND created_at > datetime('now', ? || ' days')
            LIMIT 1
            """,
            (citation_id, target_id, str(-max_age_days)),
        ).fetchone()
        return row["research_domain"] if row else None


def find_shared_sentiment(
    citation_id: str,
    cited_paper_id: str,
    target_id: str,
    max_age_days: int = 30,
) -> dict | None:
    """Find sentiment data for the same (citation_id, cited_paper_id) from another target."""
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT score, positive_comment, sentiment_evidence,
                   usage_classification, paper_homepage, version
            FROM citations
            WHERE citation_id = ? AND cited_paper_id = ? AND target_id != ?
              AND score IS NOT NULL
              AND created_at > datetime('now', ? || ' days')
            LIMIT 1
            """,
            (citation_id, cited_paper_id, target_id, str(-max_age_days)),
        ).fetchone()
        return dict(row) if row else None


def find_shared_venue_authors(
    citation_id: str, target_id: str, max_age_days: int = 30
) -> dict | None:
    """Find resolved venue/authors for this citation_id from another target."""
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT venue, authors FROM citations
            WHERE citation_id = ? AND target_id != ?
              AND venue NOT LIKE '%arxiv%'
              AND authors IS NOT NULL AND authors != '[]' AND authors != ''
              AND created_at > datetime('now', ? || ' days')
            LIMIT 1
            """,
            (citation_id, target_id, str(-max_age_days)),
        ).fetchone()
        return dict(row) if row else None
