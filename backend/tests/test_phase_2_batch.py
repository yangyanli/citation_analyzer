import pytest
import uuid
from unittest.mock import patch, MagicMock
from backend.pipeline.phase_2_authors import evaluate_authors
from backend.database.sqlite_db import init_db, upsert_author, get_author


@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    # Mocking the LLM JSON response for a batch of authors
    mock_response = MagicMock()
    mock_response.text = """
    ```json
    {
        "Jane Doe": {
            "is_notable": true,
            "evidence": "Turing Award winner (2020)",
            "homepage": "http://janedoe.com",
            "verification_keywords": ["turing award"],
            "verification_url": "http://acm.org/turing"
        },
        "John Smith": {
            "is_notable": false,
            "evidence": "",
            "homepage": "",
            "verification_keywords": [],
            "verification_url": ""
        }
    }
    ```
    """
    client.models.generate_content.return_value = mock_response
    return client


@patch("backend.pipeline.phase_2_authors.time.sleep", return_value=None)
@patch("backend.pipeline.phase_2_authors.verify_notable_claim")
def test_evaluate_authors_batching_and_db_flow(
    mock_verify, mock_sleep, mock_llm_client
):
    """Test that evaluate_authors correctly calls the LLM, verifies claims, and updates DB."""

    jane_name = f"Jane Doe {uuid.uuid4()}"
    john_name = f"John Smith {uuid.uuid4()}"
    alice_name = f"Alice {uuid.uuid4()}"

    # Re-mock the LLM response dynamically generated to match our UUID names
    mock_response = MagicMock()
    mock_response.text = f"""
    ```json
    {{
        "{jane_name}": {{
            "is_notable": true,
            "evidence": "Turing Award winner (2020)",
            "homepage": "http://janedoe.com",
            "verification_keywords": ["turing award"],
            "verification_url": "http://acm.org/turing"
        }},
        "{john_name}": {{
            "is_notable": false,
            "evidence": "",
            "homepage": "",
            "verification_keywords": [],
            "verification_url": ""
        }}
    }}
    ```
    """
    mock_llm_client.models.generate_content.return_value = mock_response

    # 1. Provide an unknown author (Jane Doe) and a known author (Alice)
    # Alice should be skipped. John Smith is also unknown to test negative LLM output.
    upsert_author(alice_name, True, "Nobel Laureate")

    cid_1 = f"cid_{uuid.uuid4()}"
    cid_2 = f"cid_{uuid.uuid4()}"

    collected_citations = [
        {
            "citation_id": cid_1,
            "authors": [{"name": jane_name}, {"name": alice_name}],
        },
        {
            "citation_id": cid_2,
            "authors": [{"name": john_name}],
        },
    ]

    eval_criteria = {"notable_criteria": "Turing Award"}
    target_id = "test_target_20"

    from backend.database.sqlite_db import (
        insert_citation_if_missing,
        upsert_analysis_target,
    )

    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Target"})

    insert_citation_if_missing(
        cid_1,
        {"citing_title": "Paper 1", "cited_title": "Target", "target_id": target_id},
    )
    insert_citation_if_missing(
        cid_2,
        {"citing_title": "Paper 2", "cited_title": "Target", "target_id": target_id},
    )

    # 2. Mock the verification step always passing for simplicity
    # Signature: (is_notable, evidence + " [Verified]", [scraped_urls])
    mock_verify.return_value = (
        True,
        "Turing Award winner (2020) [AI Verified]",
        ["http://acm.org/turing"],
    )

    # 3. Call the entrypoint
    evaluate_authors(mock_llm_client, "gemini-test", eval_criteria, collected_citations)

    # 4. Verify LLM was called ONCE for the unknown authors (Jane and John)
    mock_llm_client.models.generate_content.assert_called_once()

    # 5. Verify the DB was correctly updated
    jane = get_author(jane_name)
    assert jane is not None
    assert jane["is_notable"] == 1
    assert "[AI Verified]" in jane["evidence"]

    john = get_author(john_name)
    assert john is not None
    assert john["is_notable"] == 0
    assert john["evidence"] == ""

    # Verify the citations were correctly updated with notable authors JSON
    from backend.database.sqlite_db import get_citation

    c1 = get_citation(cid_1)
    assert len(c1["notable_authors"]) == 2  # Jane Doe and Alice

    c2 = get_citation(cid_2)
    assert len(c2["notable_authors"]) == 0  # John Smith is not notable


@patch("backend.pipeline.phase_2_authors.time.sleep", return_value=None)
@patch("backend.pipeline.phase_2_authors.verify_notable_claim")
def test_evaluate_authors_massive_authors_batching(
    mock_verify, mock_sleep, mock_llm_client
):
    """Test that submitting 200 unknown authors properly chunks and loops the API."""

    collected_citations = []

    target_id = f"test_target_mass_{uuid.uuid4()}"
    from backend.database.sqlite_db import (
        insert_citation_if_missing,
        upsert_analysis_target,
    )

    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Target"})

    # 200 unique authors
    run_uuid = uuid.uuid4()
    for i in range(200):
        collected_citations.append(
            {
                "citation_id": f"cid_mass_{run_uuid}_{i}",
                "authors": [{"name": f"Unknown {run_uuid}_{i}"}],
            }
        )

        insert_citation_if_missing(
            f"cid_mass_{run_uuid}_{i}",
            {
                "citing_title": f"M Paper {i}",
                "cited_title": "Target",
                "target_id": target_id,
            },
        )

    mock_response = MagicMock()
    mock_response.text = '```json\n{"dummy": true}\n```'
    mock_llm_client.models.generate_content.return_value = mock_response

    # Each chunk defaults to 100 authors, so 200 authors requires 2 calls
    evaluate_authors(
        mock_llm_client, "gemini-test", {"notable_criteria": "x"}, collected_citations
    )

    assert mock_llm_client.models.generate_content.call_count == 2


@patch("backend.pipeline.phase_2_authors.time.sleep", return_value=None)
def test_evaluate_authors_malformed_json_fallback(mock_sleep, mock_llm_client):
    """Test resilience against broken dictionaries from LLM output."""
    broken_author_name = f"Broken Author {uuid.uuid4()}"
    cid_mal = f"cid_mal_{uuid.uuid4()}"
    target_id = f"test_target_mal_{uuid.uuid4()}"

    collected_citations = [
        {"citation_id": cid_mal, "authors": [{"name": broken_author_name}]}
    ]
    from backend.database.sqlite_db import (
        insert_citation_if_missing,
        upsert_analysis_target,
    )

    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Target"})

    insert_citation_if_missing(
        cid_mal,
        {"citing_title": "Paper", "cited_title": "Target", "target_id": target_id},
    )

    mock_response = MagicMock()
    # Missing brackets
    mock_response.text = f'```json\n"{broken_author_name}": {{"is_notable": true\n```'
    mock_llm_client.models.generate_content.return_value = mock_response

    # Should not crash, just log and fallback gracefully
    evaluate_authors(
        mock_llm_client, "gemini-test", {"notable_criteria": "x"}, collected_citations
    )

    # The author will be skipped if it repeatedly fails to return proper JSON structure
    from backend.database.sqlite_db import get_author

    author = get_author(broken_author_name)
    assert author is None
