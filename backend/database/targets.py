"""CRUD operations for the analysis_targets table."""

from __future__ import annotations
import json
import logging

from backend.database.connection import get_db_connection

logger = logging.getLogger("citation_analyzer")


def get_analysis_target(target_id: str) -> dict | None:
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM analysis_targets WHERE target_id = ?", (target_id,)
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["interests"] = json.loads(data["interests"]) if data["interests"] else []
        data["evaluation_criteria"] = (
            json.loads(data["evaluation_criteria"])
            if data["evaluation_criteria"]
            else {}
        )
        return dict(data)


def upsert_analysis_target(target_id: str, data: dict) -> None:
    """Insert or update an analysis target using its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO analysis_targets (
                target_id, mode, name, url, interests, evaluation_criteria, status, progress, error, group_id, is_paused_for_fallback
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(target_id) DO UPDATE SET
                mode = COALESCE(excluded.mode, mode),
                name = COALESCE(excluded.name, name),
                url = COALESCE(excluded.url, url),
                interests = COALESCE(excluded.interests, interests),
                evaluation_criteria = COALESCE(excluded.evaluation_criteria, evaluation_criteria),
                status = COALESCE(excluded.status, status),
                progress = COALESCE(excluded.progress, progress),
                error = COALESCE(excluded.error, error),
                group_id = COALESCE(excluded.group_id, group_id),
                is_paused_for_fallback = COALESCE(excluded.is_paused_for_fallback, is_paused_for_fallback)
            """,
            (
                target_id,
                data.get("mode"),
                data.get("name") or data.get("title"),
                data.get("url") or data.get("s2_url"),
                json.dumps(data.get("interests", [])),
                json.dumps(data.get("evaluation_criteria")) if data.get("evaluation_criteria") else None,
                data.get("status", "pending"),
                data.get("progress", 0),
                data.get("error"),
                data.get("group_id"),
                data.get("is_paused_for_fallback", False),
            ),
        )


def delete_analysis_target(target_id: str) -> bool:
    """Delete an analysis target and all its associated citations. Returns True if found and deleted."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM analysis_targets WHERE target_id = ?", (target_id,)
        ).fetchone()
        if not row:
            return False
        conn.execute("DELETE FROM citations WHERE target_id = ?", (target_id,))
        conn.execute("DELETE FROM analysis_targets WHERE target_id = ?", (target_id,))
        return True


def get_target_status(target_id: str) -> str:
    """Get the current progress status string for an analysis target."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT status FROM analysis_targets WHERE target_id = ?", (target_id,)
        ).fetchone()
        return row["status"] if row else "unknown"


def update_target_progress(
    target_id: str, status: str, progress: int, error: str | None = None
) -> bool:
    """Update progress tracking for an analysis target.
    Returns False if the target was paused or cancelled by the user, skipping the update.
    """
    with get_db_connection() as conn:
        if status not in ("paused", "cancelled", "failed"):
            current = conn.execute(
                "SELECT status FROM analysis_targets WHERE target_id = ?", (target_id,)
            ).fetchone()
            if current and current["status"] in ("paused", "cancelled"):
                return False

        conn.execute(
            "UPDATE analysis_targets SET status = ?, progress = ?, error = ?, is_paused_for_fallback = 0 WHERE target_id = ?",
            (status, progress, error, target_id),
        )
        return True


def set_target_fallback_status(target_id: str, is_paused: bool) -> None:
    """Explicitly toggle the fallback wait state for a target."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE analysis_targets SET is_paused_for_fallback = ? WHERE target_id = ?",
            (1 if is_paused else 0, target_id),
        )


def update_target_total_citations(target_id: str, total_citations: int) -> None:
    """Update the requested/task citation limit for the analysis target."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE analysis_targets SET total_citations = ? WHERE target_id = ?",
            (total_citations, target_id),
        )


def update_target_s2_total(target_id: str, s2_total: int) -> None:
    """Update the total S2 citation count across all papers for the target."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE analysis_targets SET s2_total_citations = ? WHERE target_id = ?",
            (s2_total, target_id),
        )


def update_target_phase_estimates(target_id: str, phase: int, batches: int, cost: float) -> None:
    """Update the estimated batches and cost for a specific phase."""
    with get_db_connection() as conn:
        if phase == 2:
            conn.execute("UPDATE analysis_targets SET p2_est_batches = ?, p2_est_cost = ? WHERE target_id = ?", (batches, cost, target_id))
        elif phase == 3:
            conn.execute("UPDATE analysis_targets SET p3_est_batches = ?, p3_est_cost = ? WHERE target_id = ?", (batches, cost, target_id))
        elif phase == 4:
            conn.execute("UPDATE analysis_targets SET p4_est_batches = ?, p4_est_cost = ? WHERE target_id = ?", (batches, cost, target_id))
        elif phase == 5:
            conn.execute("UPDATE analysis_targets SET p5_est_batches = ?, p5_est_cost = ? WHERE target_id = ?", (batches, cost, target_id))
