"""CRUD operations for the llm_logs table."""

from __future__ import annotations

from backend.database.connection import get_db_connection


def insert_llm_log(data: dict) -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO llm_logs (
                run_id, target_id, system_user_id, stage, model,
                prompt_text, response_text, input_tokens, output_tokens, is_fallback
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("run_id"),
                data.get("target_id"),
                data.get("system_user_id"),
                data.get("stage"),
                data.get("model"),
                data.get("prompt_text"),
                data.get("response_text"),
                data.get("input_tokens"),
                data.get("output_tokens"),
                data.get("is_fallback", False),
            ),
        )


def get_llm_logs(
    limit: int = 100,
    offset: int = 0,
    target_id: str | None = None,
    stage: str | None = None,
) -> list[dict]:
    with get_db_connection() as conn:
        query = "SELECT * FROM llm_logs WHERE 1=1"
        params: list[str | int] = []
        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)
        if stage:
            query += " AND stage = ?"
            params.append(stage)
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]
