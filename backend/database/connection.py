"""Shared SQLite connection management for Citation Analyzer."""

from __future__ import annotations
import sqlite3
import os
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger("citation_analyzer")

# We manage the connection locally to the DB file
_env_path = os.environ.get("DB_PATH")
if _env_path:
    DB_PATH = Path(_env_path)
else:
    DB_PATH = Path(__file__).parent.parent.parent / "data" / "citation_analyzer.db"


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional scope around a series of operations."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
