"""Global test fixtures for all backend tests.

This conftest.py patches the database path at the correct location
(backend.database.connection.DB_PATH) to prevent test data from ever
leaking into the production database.
"""

import pytest
from backend.database.schema import init_db


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch, tmp_path):
    """Override DB_PATH to use a fresh temp SQLite database for every test."""
    temp_db = tmp_path / "test.db"
    monkeypatch.setattr("backend.database.connection.DB_PATH", temp_db)
    init_db()
    yield
