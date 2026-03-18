import pytest
from unittest.mock import MagicMock, patch

from backend.pipeline.phase_0_criteria import generate_domain_criteria
from backend.database.sqlite_db import init_db, upsert_analysis_target


@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    mock_response = MagicMock()

    # Return a controlled JSON string from the mocked LLM
    mock_response.text = """
    ```json
    {
        "inferred_domain": "Test Domain",
        "notable_criteria": "Test Notable Criteria",
        "seminal_criteria": "Test Seminal Criteria"
    }
    ```
    """
    mock_response2 = MagicMock()
    mock_response2.text = """
    ```json
    {
        "notable_criteria": "Test Notable Criteria",
        "seminal_criteria": "Test Seminal Criteria"
    }
    ```
    """
    client.models.generate_content.side_effect = [mock_response, mock_response2]
    return client


def test_generate_criteria_override_mode(mock_llm_client):
    target_id = "test_target"
    overrides = {
        "domain": "Override Domain",
        "notable_criteria": "Override Notable",
        "seminal_criteria": "Override Seminal",
    }

    # Must upsert the target first to satisfy foreign key constraints if needed, but phase0 handles it via upsert.
    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Test"})

    criteria = generate_domain_criteria(
        client=mock_llm_client,
        model_name="test-model",
        target_id=target_id,
        overrides=overrides,
    )

    assert criteria["inferred_domain"] == "Override Domain"
    assert criteria["notable_criteria"] == "Override Notable"
    assert criteria["seminal_criteria"] == "Override Seminal"

    # Ensure LLM was NOT called
    mock_llm_client.models.generate_content.assert_not_called()


@patch(
    "backend.api.semantic_scholar.search_semantic_scholar_paper",
    return_value={"paperId": "p1"},
)
def test_generate_criteria_llm_mode(mock_search, mock_llm_client):
    target_id = "test_target"
    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Test"})

    criteria = generate_domain_criteria(
        client=mock_llm_client,
        model_name="test-model",
        target_id=target_id,
        scholar_name="John Doe",
        interests=["AI", "ML"],
        publications=[{"bib": {"title": "Paper 1"}}],
    )

    assert criteria["inferred_domain"] == "Test Domain"
    assert criteria["notable_criteria"] == "Test Notable Criteria"
    assert criteria["seminal_criteria"] == "Test Seminal Criteria"

    # Ensure LLM WAS called twice (Two-phase)
    assert mock_llm_client.models.generate_content.call_count == 2

    # Validate caching: calling it again should hit the DB cache, not the LLM
    mock_llm_client.models.generate_content.reset_mock()

    cached_criteria = generate_domain_criteria(
        client=mock_llm_client,
        model_name="test-model",
        target_id=target_id,
    )

    assert cached_criteria == criteria
    mock_llm_client.models.generate_content.assert_not_called()


@patch(
    "backend.api.semantic_scholar.search_semantic_scholar_paper",
    return_value={"paperId": "p1"},
)
def test_generate_criteria_partial_override(mock_search, mock_llm_client):
    target_id = "test_target"
    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Test"})

    overrides = {"domain": "Partial Override Domain"}

    criteria = generate_domain_criteria(
        client=mock_llm_client,
        model_name="test-model",
        target_id=target_id,
        scholar_name="John Doe",
        publications=[{"bib": {"title": "Paper 1"}}],
        overrides=overrides,
    )

    # Domain should be overriden, others fall back to LLM mock
    assert criteria["inferred_domain"] == "Partial Override Domain"
    assert criteria["notable_criteria"] == "Test Notable Criteria"
    assert criteria["seminal_criteria"] == "Test Seminal Criteria"

    # Ensure LLM WAS called twice since only partial overrides were provided
    assert mock_llm_client.models.generate_content.call_count == 2


@patch(
    "backend.api.semantic_scholar.search_semantic_scholar_paper",
    return_value={"paperId": "p1"},
)
def test_generate_criteria_malformed_json_response(
    mock_search, mock_llm_client
):
    target_id = "malformed_target"
    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Test"})

    mock_response = MagicMock()
    # Missing closing brace to simulate severe malformation
    mock_response.text = (
        '```json\n{"inferred_domain": "Broken", "notable_criteria": "Broken"'
    )
    mock_llm_client.models.generate_content.side_effect = [mock_response]

    with pytest.raises(SystemExit):
        generate_domain_criteria(
            client=mock_llm_client,
            model_name="test-model",
            target_id=target_id,
            scholar_name="John Doe",
            publications=[{"bib": {"title": "Paper 1"}}],
        )


@patch(
    "backend.api.semantic_scholar.search_semantic_scholar_paper",
    return_value={"paperId": "p1"},
)
def test_generate_criteria_missing_keys_fallback(
    mock_search, mock_llm_client
):
    target_id = "missing_keys_target"
    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Test"})

    mock_response = MagicMock()
    # Provide valid JSON but missing the required keys
    mock_response.text = '```json\n{"wrong_key": "data"}\n```'
    mock_llm_client.models.generate_content.side_effect = [mock_response]

    with pytest.raises(SystemExit):
        generate_domain_criteria(
            client=mock_llm_client,
            model_name="test-model",
            target_id=target_id,
            scholar_name="John Doe",
            publications=[{"bib": {"title": "Paper 1"}}],
        )


def test_generate_criteria_paper_mode_and_fallback(mock_llm_client):
    target_id = "paper_target"
    upsert_analysis_target(target_id, {"mode": "paper", "name": "Paper Mode"})

    with patch(
        "backend.api.semantic_scholar.search_semantic_scholar_paper",
        return_value={"paperId": "p1"},
    ):
        criteria = generate_domain_criteria(
            client=mock_llm_client,
            model_name="test-model",
            target_id=target_id,
            paper_title="Test Paper",
        )
        assert criteria["inferred_domain"] == "Test Domain"


def test_generate_criteria_no_context(mock_llm_client):
    target_id = "no_context"
    upsert_analysis_target(target_id, {"mode": "paper", "name": "No Context"})
    criteria = generate_domain_criteria(
        client=mock_llm_client,
        model_name="test-model",
        target_id=target_id,
    )
    assert criteria["inferred_domain"] == "Test Domain"


def test_generate_criteria_dict_and_list_conversion(mock_llm_client):
    target_id = "conversion_target"
    upsert_analysis_target(target_id, {"mode": "paper", "name": "Conversion"})

    # Return dict and list inside criteria
    mock_response2 = MagicMock()
    mock_response2.text = """```json
    {
        "notable_criteria": {"part1": "value1", "part2": "value2"},
        "seminal_criteria": ["item1", "item2"]
    }
    ```"""
    mock_llm_client.models.generate_content.side_effect = [MagicMock(), mock_response2]

    criteria = generate_domain_criteria(
        client=mock_llm_client,
        model_name="test-model",
        target_id=target_id,
    )
    assert criteria["notable_criteria"] == "value1 value2"
    assert criteria["seminal_criteria"] == "item1, item2"
