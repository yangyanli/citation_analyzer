"""Database operations for admin: groups and group membership."""

from __future__ import annotations

from backend.database.connection import get_db_connection


def list_groups() -> list[dict]:
    """Return all groups with their members."""
    with get_db_connection() as conn:
        groups = [
            dict(r)
            for r in conn.execute(
                "SELECT id, name, is_public, created_at FROM groups ORDER BY created_at DESC"
            ).fetchall()
        ]
        for g in groups:
            members = [
                dict(r)
                for r in conn.execute(
                    """
                    SELECT u.id, u.username, u.role
                    FROM users u
                    JOIN user_groups ug ON u.id = ug.user_id
                    WHERE ug.group_id = ?
                    """,
                    (g["id"],),
                ).fetchall()
            ]
            g["members"] = members
        return groups


def create_group(name: str, is_public: bool = False) -> int:
    """Create a new group.  Returns the new group ID.
    Raises sqlite3.IntegrityError if name already exists.
    """
    with get_db_connection() as conn:
        cur = conn.execute(
            "INSERT INTO groups (name, is_public) VALUES (?, ?)",
            (name.strip(), 1 if is_public else 0),
        )
        return cur.lastrowid


def update_group_visibility(group_id: int, is_public: bool) -> None:
    """Update a group's public visibility."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE groups SET is_public = ? WHERE id = ?",
            (1 if is_public else 0, group_id),
        )


def delete_group(group_id: int) -> None:
    """Delete a group if it has no members. Raises Exception if group has members."""
    with get_db_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM user_groups WHERE group_id = ?", (group_id,)).fetchone()[0]
        if count > 0:
            raise ValueError("Cannot delete a group that currently has members.")
        conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))


def add_user_to_group(group_id: int, user_id: int) -> None:
    """Add a user to a group.
    Raises sqlite3.IntegrityError on duplicate or invalid FK.
    """
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO user_groups (user_id, group_id) VALUES (?, ?)",
            (user_id, group_id),
        )


def remove_user_from_group(group_id: int, user_id: int) -> None:
    """Remove a user from a group."""
    with get_db_connection() as conn:
        conn.execute(
            "DELETE FROM user_groups WHERE group_id = ? AND user_id = ?",
            (group_id, user_id),
        )
