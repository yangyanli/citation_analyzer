import os
import pytest
from unittest.mock import patch

from backend.api.llm import FallbackClient
from backend.database.sqlite_db import (
    upsert_analysis_target,
    get_analysis_target,
    init_db,
)


class DummyTokenizer:
    def encode(self, text):
        return text.split()


class DummyTiktoken:
    @staticmethod
    def get_encoding(name):
        return DummyTokenizer()


@pytest.fixture
def llm_calls_base(tmp_path, monkeypatch):
    """Point LLM_CALLS_DIR at a temp dir so no run_ folders leak into the project."""
    base = str(tmp_path / "llm_calls")
    os.makedirs(base, exist_ok=True)
    monkeypatch.setenv("LLM_CALLS_DIR", base)
    return base


@pytest.fixture(autouse=True)
def seed_test_target():
    """Seed the test database with a target for fallback tests."""
    upsert_analysis_target(
        "test_target_123",
        {
            "status": "pending",
            "progress": 0,
            "is_paused_for_fallback": 0,
            "mode": "scholar",
            "name": "Test Author",
        },
    )
    yield



@patch("backend.api.llm.tiktoken", DummyTiktoken())
def test_fallback_writes_native_txt_prompt(llm_calls_base):
    client = FallbackClient()
    actual_run_dir = client.models.run_dir

    # Verify run_dir is inside our temp base, not the project
    assert actual_run_dir.startswith(llm_calls_base)

    run_id = os.path.basename(actual_run_dir)

    original_exists = os.path.exists

    def auto_unblock_exists(path):
        if "phase_2_000001_author_response" in path and path.endswith(".md"):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write("I am the markdown response.")
            return True
        return original_exists(path)

    with patch("backend.api.llm.os.path.exists", side_effect=auto_unblock_exists):
        client.models.generate_content("gemini-test", "Hello world, give me markdown.",
                                       config={"phase": "phase_2_author"})

    prompt_file = os.path.join(actual_run_dir, "phase_2_000001_author_prompt.txt")
    assert os.path.exists(prompt_file)
    with open(prompt_file, "r") as f:
        assert f.read() == "Hello world, give me markdown."

    # Validate DB Logging by filtering for our specific run_id
    from backend.database.sqlite_db import get_db_connection

    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM llm_logs WHERE run_id = ?", (run_id,)
        ).fetchall()
        logs = [dict(row) for row in rows]

    assert len(logs) == 1
    assert logs[0]["prompt_text"] == "Hello world, give me markdown."
    assert logs[0]["is_fallback"] == 1


@patch("backend.api.llm.tiktoken", DummyTiktoken())
def test_fallback_detects_json_requirement(llm_calls_base):
    client = FallbackClient()
    actual_run_dir = client.models.run_dir

    original_exists = os.path.exists

    def auto_unblock_exists(path):
        if "response" in path and path.endswith(".json"):
            with open(path, "w") as f:
                f.write('{"inferred_domain": "AI"}')
            return True
        return original_exists(path)

    with patch("backend.api.llm.os.path.exists", side_effect=auto_unblock_exists):
        response = client.models.generate_content(
            "gemini-test",
            "infer the researcher's core research domains. respond with strictly json.",
            config={"phase": "phase_0_domain", "target_id": "test_target_123"},
        )

    assert '{"inferred_domain": "AI"}' in response.text


@patch("backend.api.llm.tiktoken", DummyTiktoken())
def test_fallback_toggles_database_state(llm_calls_base):
    client = FallbackClient()
    actual_run_dir = client.models.run_dir

    state_was_paused = [False]
    original_exists = os.path.exists

    def auto_unblock_exists(path):
        if "unknown_000001_response" in path and path.endswith(".md"):
            target = get_analysis_target("test_target_123")
            if target and target.get("is_paused_for_fallback") == 1:
                state_was_paused[0] = True
            with open(path, "w") as f:
                f.write("I am unblocked!")
            return True
        return original_exists(path)

    with patch("backend.api.llm.os.path.exists", side_effect=auto_unblock_exists):
        client.models.generate_content(
            "gemini-test", "Provide some md.", config={"target_id": "test_target_123"}
        )

    target_final = get_analysis_target("test_target_123")
    assert target_final.get("is_paused_for_fallback") == 0
    assert state_was_paused[0] is True
