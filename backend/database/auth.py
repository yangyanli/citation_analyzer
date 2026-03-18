"""Database operations for authentication: users, sessions, password hashing."""

from __future__ import annotations
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from backend.database.connection import get_db_connection


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash a password with SHA-256.  Returns (salt, hash_hex)."""
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((password + salt).encode()).hexdigest()
    return salt, h


def verify_credentials(username: str, password: str) -> dict | None:
    """Verify username/password.  Returns user dict or None."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT id, password_hash, role FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if not row:
            return None
        stored = dict(row)
        salt, stored_hash = stored["password_hash"].split("$", 1)
        _, computed = _hash_password(password, salt)
        if computed != stored_hash:
            return None
        return {"id": stored["id"], "username": username, "role": stored["role"]}


def create_session(user_id: int) -> tuple[str, str]:
    """Create a new session.  Returns (token, expires_at_iso)."""
    token = secrets.token_hex(32)
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    expires_iso = expires.isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (session_token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_iso),
        )
    return token, expires_iso


def delete_session(token: str) -> None:
    """Delete a session by token."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE session_token = ?", (token,))


def get_user_by_session(token: str) -> dict | None:
    """Look up user + groups from a session token.  Returns None if invalid/expired."""
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.username, u.role
            FROM users u
            JOIN sessions s ON u.id = s.user_id
            WHERE s.session_token = ? AND s.expires_at > datetime('now')
            """,
            (token,),
        ).fetchone()
        if not row:
            return None
        user = dict(row)
        groups = [
            dict(r)
            for r in conn.execute(
                """
                SELECT g.id, g.name
                FROM groups g
                JOIN user_groups ug ON g.id = ug.group_id
                WHERE ug.user_id = ?
                """,
                (user["id"],),
            ).fetchall()
        ]
        user["groups"] = groups
        return user


def create_user(username: str, password: str, role: str = "editor") -> dict:
    """Register a new user.  Returns {'id': ..., 'username': ..., 'role': ...}.
    Raises sqlite3.IntegrityError if username already exists.
    """
    salt, h = _hash_password(password)
    password_hash = f"{salt}${h}"
    with get_db_connection() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, role),
        )
        return {"id": cur.lastrowid, "username": username, "role": role}


def list_users() -> list[dict]:
    """Return all users (without password hashes)."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id, username, role, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_user_role(user_id: int, role: str) -> None:
    """Update a user's role."""
    with get_db_connection() as conn:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))


def update_user_password(user_id: int, new_password: str) -> None:
    """Update a user's password."""
    salt, h = _hash_password(new_password)
    password_hash = f"{salt}${h}"
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash, user_id),
        )


def delete_user(user_id: int) -> None:
    """Delete a user and their sessions."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
