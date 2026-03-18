import sqlite3
import hashlib
import os

DB_PATH = os.environ.get("DB_PATH", "data/citation_analyzer.db")


def hash_pw(pw):
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256((pw + salt).encode()).hexdigest()
    return f"{salt}${hashed}"


def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")

    # Insert groups explicitly to avoid AUTOINCREMENT gaps
    cursor.execute(
        "INSERT OR IGNORE INTO groups (id, name, is_public) VALUES (1, 'Public Group', 1)"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO groups (id, name, is_public) VALUES (2, 'PKU VCL', 0)"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO groups (id, name, is_public) VALUES (3, 'Grab-NUS', 0)"
    )

    # Get group IDs
    cursor.execute("SELECT id, name FROM groups")
    group_map = {name: id for id, name in cursor.fetchall()}

    # Insert users
    users = [
        ("admin", "admin", "super_admin", "Public Group"),
        ("wenzheng_chen", "password", "admin", "PKU VCL"),
        ("jinming_cao", "password", "admin", "Grab-NUS"),
        ("user", "user123", "viewer", "Public Group"),
    ]

    # Insert test session token for cross-validation scripts
    cursor.execute(
        "INSERT OR IGNORE INTO sessions (session_token, user_id, expires_at) "
        "SELECT 'super_admin_test_token', id, datetime('now', '+1 day') FROM users WHERE username='admin'"
    )

    for username, pw, role, group_name in users:
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        if not user_row:
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, hash_pw(pw), role),
            )
            user_id = cursor.lastrowid
        else:
            user_id = user_row[0]

        # Assign to group
        group_id = group_map.get(group_name)
        if group_id:
            cursor.execute(
                "INSERT OR IGNORE INTO user_groups (user_id, group_id) VALUES (?, ?)",
                (user_id, group_id),
            )

    conn.commit()
    conn.close()
    print("Database seeded with correct users, groups, and roles.")


if __name__ == "__main__":
    seed()
