"""Database schema initialization and migrations for Citation Analyzer."""

from __future__ import annotations
import logging

from backend.database.connection import get_db_connection, DB_PATH

logger = logging.getLogger("citation_analyzer")


def init_db() -> None:
    """Initialize database schemas if they do not exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Analysis Targets (Tracks Scholar vs Paper jobs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_targets (
                target_id TEXT PRIMARY KEY,
                mode TEXT NOT NULL,
                name TEXT,
                url TEXT,
                interests TEXT, -- JSON array
                evaluation_criteria TEXT, -- JSON object
                status TEXT DEFAULT 'pending',
                is_paused_for_fallback BOOLEAN DEFAULT 0,
                progress INTEGER DEFAULT 0,
                error TEXT,
                total_citations INTEGER DEFAULT 0,
                s2_total_citations INTEGER DEFAULT 0,
                p2_est_batches INTEGER DEFAULT 0,
                p2_est_cost REAL DEFAULT 0.0,
                p3_est_batches INTEGER DEFAULT 0,
                p3_est_cost REAL DEFAULT 0.0,
                p4_est_batches INTEGER DEFAULT 0,
                p4_est_cost REAL DEFAULT 0.0,
                p5_est_batches INTEGER DEFAULT 0,
                p5_est_cost REAL DEFAULT 0.0
            )
            """)

        # 2. Authors (Validates and caches hallucination checks)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authors (
                name TEXT PRIMARY KEY,
                is_notable BOOLEAN NOT NULL,
                evidence TEXT,
                homepage TEXT,
                is_human_verified BOOLEAN DEFAULT 0,
                ai_is_notable BOOLEAN,
                ai_evidence TEXT,
                ai_homepage TEXT
            )
            """)

        # 3. Groups (RBAC)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                is_public BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

        # 4. User Groups junction table (RBAC)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_groups (
                user_id INTEGER,
                group_id INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, group_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
            """)

        # 5. S2 Search Cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s2_search_cache (
                title TEXT PRIMARY KEY,
                paper_id TEXT,
                citation_count INTEGER,
                timestamp REAL
            )
            """)

        # 6. Citations (Main records table)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS citations (
                citation_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                cited_title TEXT NOT NULL,
                cited_paper_id TEXT,
                citing_title TEXT NOT NULL,
                url TEXT,
                paper_homepage TEXT,
                year INTEGER,
                venue TEXT,
                citing_citation_count INTEGER,
                is_self_citation BOOLEAN DEFAULT 0,
                is_seminal BOOLEAN DEFAULT 0,
                seminal_evidence TEXT,
                usage_classification TEXT DEFAULT 'Pending',
                score INTEGER,
                positive_comment TEXT,
                sentiment_evidence TEXT,
                raw_contexts TEXT,
                notable_authors TEXT,
                pdf_url TEXT,
                full_text_path TEXT,
                full_text_analysis TEXT,
                version TEXT,
                is_human_verified BOOLEAN DEFAULT 0,
                ai_score INTEGER,
                ai_usage_classification TEXT,
                ai_positive_comment TEXT,
                ai_sentiment_evidence TEXT,
                ai_is_seminal BOOLEAN DEFAULT 0,
                ai_seminal_evidence TEXT,
                authors TEXT,
                research_domain TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(citation_id, target_id),
                FOREIGN KEY(target_id) REFERENCES analysis_targets(target_id)
            )
            """)

        # --- RBAC tables (must be before migrations since group_id migration references users) ---
        _create_auth_tables(cursor)

        # --- Migrations ---
        _run_migrations(cursor)

        # --- LLM Logs ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                target_id TEXT,
                system_user_id INTEGER,
                stage TEXT,
                model TEXT,
                prompt_text TEXT,
                response_text TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                is_fallback BOOLEAN DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

        logger.info(f"SQLite database initialized at {DB_PATH}")


def _run_migrations(cursor) -> None:
    """Run all schema migrations."""
    # -- analysis_targets migrations --
    cursor.execute("PRAGMA table_info(analysis_targets)")
    target_columns = [row[1] for row in cursor.fetchall()]

    if "status" not in target_columns:
        cursor.execute("ALTER TABLE analysis_targets ADD COLUMN status TEXT DEFAULT 'pending'")
        cursor.execute("ALTER TABLE analysis_targets ADD COLUMN progress INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE analysis_targets ADD COLUMN error TEXT")
        logger.info("Migrated database: Added progress tracking columns to 'analysis_targets' table.")

    if "total_citations" not in target_columns:
        cursor.execute("ALTER TABLE analysis_targets ADD COLUMN total_citations INTEGER DEFAULT 0")
        logger.info("Migrated database: Added 'total_citations' column to 'analysis_targets' table.")

    if "is_paused_for_fallback" not in target_columns:
        cursor.execute("ALTER TABLE analysis_targets ADD COLUMN is_paused_for_fallback BOOLEAN DEFAULT 0")
        logger.info("Migrated database: Added 'is_paused_for_fallback' column to 'analysis_targets' table.")

    if "s2_total_citations" not in target_columns:
        cursor.execute("ALTER TABLE analysis_targets ADD COLUMN s2_total_citations INTEGER DEFAULT 0")
        logger.info("Migrated database: Added 's2_total_citations' column to 'analysis_targets' table.")

    if "p2_est_batches" not in target_columns:
        for col in ["p2_est_batches", "p3_est_batches", "p4_est_batches"]:
            cursor.execute(f"ALTER TABLE analysis_targets ADD COLUMN {col} INTEGER DEFAULT 0")
        for col in ["p2_est_cost", "p3_est_cost", "p4_est_cost"]:
            cursor.execute(f"ALTER TABLE analysis_targets ADD COLUMN {col} REAL DEFAULT 0.0")
        logger.info("Migrated database: Added phase estimates columns to 'analysis_targets' table.")

    if "p5_est_batches" not in target_columns:
        cursor.execute("ALTER TABLE analysis_targets ADD COLUMN p5_est_batches INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE analysis_targets ADD COLUMN p5_est_cost REAL DEFAULT 0.0")
        logger.info("Migrated database: Added p5 estimates columns to 'analysis_targets' table.")

    # -- citations migrations --
    cursor.execute("PRAGMA table_info(citations)")
    columns = [row[1] for row in cursor.fetchall()]

    if "cited_paper_id" not in columns:
        cursor.execute("ALTER TABLE citations ADD COLUMN cited_paper_id TEXT")
        logger.info("Migrated database: Added 'cited_paper_id' column to 'citations' table.")

    if "authors" not in columns:
        cursor.execute("ALTER TABLE citations ADD COLUMN authors TEXT")
        logger.info("Migrated database: Added 'authors' column to 'citations' table.")

    if "is_human_verified" not in columns:
        cursor.execute("ALTER TABLE citations ADD COLUMN is_human_verified BOOLEAN DEFAULT 0")
        cursor.execute("ALTER TABLE citations ADD COLUMN ai_score INTEGER")
        cursor.execute("ALTER TABLE citations ADD COLUMN ai_usage_classification TEXT")
        cursor.execute("ALTER TABLE citations ADD COLUMN ai_positive_comment TEXT")
        cursor.execute("ALTER TABLE citations ADD COLUMN ai_sentiment_evidence TEXT")
        cursor.execute("ALTER TABLE citations ADD COLUMN ai_is_seminal BOOLEAN DEFAULT 0")
        cursor.execute("ALTER TABLE citations ADD COLUMN ai_seminal_evidence TEXT")
        logger.info("Migrated database: Added human vs AI tracking columns to 'citations' table.")

    # -- authors migrations --
    cursor.execute("PRAGMA table_info(authors)")
    author_columns = [row[1] for row in cursor.fetchall()]
    if "is_human_verified" not in author_columns:
        cursor.execute("ALTER TABLE authors ADD COLUMN is_human_verified BOOLEAN DEFAULT 0")
        cursor.execute("ALTER TABLE authors ADD COLUMN ai_is_notable BOOLEAN")
        cursor.execute("ALTER TABLE authors ADD COLUMN ai_evidence TEXT")
        cursor.execute("ALTER TABLE authors ADD COLUMN ai_homepage TEXT")
        logger.info("Migrated database: Added human vs AI tracking columns to 'authors' table.")

    for col in ["pdf_url", "full_text_path", "full_text_analysis"]:
        if col not in columns:
            cursor.execute(f"ALTER TABLE citations ADD COLUMN {col} TEXT")
            logger.info(f"Migrated database: Added '{col}' placeholder column.")

    if "research_domain" not in columns:
        cursor.execute("ALTER TABLE citations ADD COLUMN research_domain TEXT")
        logger.info("Migrated database: Added 'research_domain' column to 'citations' table.")

    if "created_at" not in columns:
        cursor.execute("ALTER TABLE citations ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        # Backfill existing rows so they are treated as "fresh"
        cursor.execute("UPDATE citations SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        logger.info("Migrated database: Added 'created_at' column to 'citations' table.")

    # -- group_id migration --
    cursor.execute("PRAGMA table_info(analysis_targets)")
    at_columns = [col[1] for col in cursor.fetchall()]
    if "group_id" not in at_columns:
        logger.info("Migrating analysis_targets: adding group_id column")
        cursor.execute("ALTER TABLE analysis_targets ADD COLUMN group_id INTEGER REFERENCES groups(id)")
        cursor.execute("INSERT OR IGNORE INTO groups (name, is_public) VALUES ('Public Group', 1)")
        cursor.execute("SELECT id FROM groups WHERE name = 'Public Group'")
        legacy_group_row = cursor.fetchone()
        if legacy_group_row:
            legacy_group_id = legacy_group_row[0]
            cursor.execute("UPDATE analysis_targets SET group_id = ?", (legacy_group_id,))
            cursor.execute(
                "INSERT OR IGNORE INTO user_groups (user_id, group_id) SELECT id, ? FROM users",
                (legacy_group_id,),
            )
        logger.info("Migrated database: Added 'group_id' column, assigned targets and users to 'Public Group'.")


def _create_auth_tables(cursor) -> None:
    """Create RBAC tables (user seeding is handled by seed_db.py)."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)

