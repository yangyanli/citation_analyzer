"""Tests for Phase 4 — sentiment scoring and JSON parsing."""

import json
from unittest.mock import patch, MagicMock


class TestPhase4JSONParsing:
    """Test the JSON extraction and key matching logic in score_citations."""

    def _run_scoring(self, llm_response_text, citations_to_score):
        """Helper to run score_citations with a mocked LLM response."""
        eval_criteria = {"seminal_criteria": "Papers with >5000 citations"}

        # Build collected_citations from citations_to_score
        collected_citations = []
        for c in citations_to_score:
            collected_citations.append(
                {
                    "citation_id": c["id"],
                    "cited_title": "Target Paper",
                    "citing_title": c.get("title", "Citing Paper"),
                    "url": "",
                    "citing_citation_count": c.get("citing_citation_count", 100),
                    "notable_authors": [{"name": "Notable Person", "evidence": "IEEE"}],
                    "raw_contexts": ["The paper is good."],
                    "is_self_citation": False,
                    "is_cached": False,
                    "year": 2024,
                    "venue": "CVPR",
                }
            )

        mock_response = MagicMock()
        mock_response.text = llm_response_text

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        from backend.pipeline.phase_4_sentiment import score_citations

        with patch(
            "backend.pipeline.phase_4_sentiment.get_unscored_citations",
            return_value=collected_citations,
        ):
            with patch(
                "backend.pipeline.phase_4_sentiment.update_citation_sentiment_only"
            ) as mock_update:
                with patch(
                    "backend.database.sqlite_db.get_target_status",
                    return_value="running",
                ):
                    score_citations(
                        mock_client, "gemini-2.5-flash", eval_criteria, "target_123"
                    )
                    return mock_update

    def test_exact_id_match(self):
        """LLM returns exact S2 paper IDs as JSON keys → all scored."""
        cid = "d15fc3fbef114453a1019143ce8dda0815d710d6"
        response = json.dumps({cid: {"score": 8, "positive_comment": "Great work"}})
        mock_update = self._run_scoring(response, [{"id": cid}])
        mock_update.assert_called_once()
        args = mock_update.call_args[0]
        assert args[0] == cid
        assert args[1]["score"] == 8
        assert args[1]["positive_comment"] == "Great work"

    def test_truncated_id_fuzzy_match(self):
        """LLM truncates ID → fuzzy prefix match recovers it."""
        full_id = "d15fc3fbef114453a1019143ce8dda0815d710d6"
        truncated = "d15fc3fbef11"
        response = json.dumps({truncated: {"score": 7, "positive_comment": "Nice"}})
        mock_update = self._run_scoring(response, [{"id": full_id}])
        mock_update.assert_called_once()
        assert mock_update.call_args[0][1]["score"] == 7

    def test_list_format_coercion(self):
        """LLM returns a JSON list [{id: ..., score: ...}] → coerced to dict."""
        cid = "d15fc3fbef114453a1019143ce8dda0815d710d6"
        response = json.dumps([{cid: {"score": 6, "positive_comment": "OK"}}])
        mock_update = self._run_scoring(response, [{"id": cid}])
        mock_update.assert_called_once()
        assert mock_update.call_args[0][1]["score"] == 6

    def test_markdown_wrapped_json(self):
        """LLM wraps response in ```json ... ``` → extracted correctly."""
        cid = "abc123def456"
        inner = json.dumps({cid: {"score": 9, "positive_comment": "Excellent"}})
        response = f"```json\n{inner}\n```"
        mock_update = self._run_scoring(response, [{"id": cid}])
        mock_update.assert_called_once()
        assert mock_update.call_args[0][1]["score"] == 9

    def test_no_json_skips_batch(self):
        """LLM returns no JSON → error is caught, batch is skipped."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "I don't know how to respond in JSON."
        mock_client.models.generate_content.return_value = mock_response

        collected = [
            {
                "citation_id": "test_id",
                "cited_title": "Paper",
                "citing_title": "Citer",
                "url": "",
                "citing_citation_count": 100,
                "notable_authors": [{"name": "Notable Person", "evidence": "IEEE"}],
                "raw_contexts": ["Context"],
                "is_self_citation": False,
                "is_cached": False,
                "year": 2024,
                "venue": "",
            }
        ]

        from backend.pipeline.phase_4_sentiment import score_citations

        with patch(
            "backend.pipeline.phase_4_sentiment.get_unscored_citations",
            return_value=collected,
        ):
            with patch(
                "backend.pipeline.phase_4_sentiment.update_citation_sentiment_only"
            ) as mock_update:
                with patch("time.sleep"):
                    with patch(
                        "backend.database.sqlite_db.get_target_status",
                        return_value="running",
                    ):
                        score_citations(
                            mock_client,
                            "gemini-2.5-flash",
                            {"seminal_criteria": "test"},
                            "target_123",
                        )

        mock_update.assert_not_called()


class TestNotableAuthorFiltering:
    """Test that only citations with notable authors are sent to the LLM."""



    def test_no_raw_contexts_skipped(self):
        """Citations missing raw_contexts should be marked with a default base score."""
        collected = [
            {
                "citation_id": "skip_me_no_ctx",
                "cited_title": "Paper",
                "citing_title": "Citer",
                "url": "",
                "citing_citation_count": 100,
                "notable_authors": [{"name": "Notable"}],
                "raw_contexts": [],  # Empty contexts
                "is_self_citation": False,
                "is_cached": False,
                "year": 2024,
                "venue": "",
            }
        ]

        mock_client = MagicMock()
        from backend.pipeline.phase_4_sentiment import score_citations

        with patch(
            "backend.pipeline.phase_4_sentiment.get_unscored_citations",
            return_value=collected,
        ):
            with patch(
                "backend.pipeline.phase_4_sentiment.update_citation_sentiment_only"
            ) as mock_update:
                with patch(
                    "backend.database.sqlite_db.get_target_status",
                    return_value="running",
                ):
                    score_citations(
                        mock_client,
                        "gemini-2.5-flash",
                        {"seminal_criteria": "test"},
                        "target_123",
                    )

        mock_update.assert_called_once()
        assert mock_update.call_args[0][1]["score"] == 5
        assert "No specific context" in mock_update.call_args[0][1]["positive_comment"]
        mock_client.models.generate_content.assert_not_called()


def test_gemini_scorer():
    from backend.pipeline.phase_4_sentiment import GeminiScorer

    scorer = GeminiScorer(MagicMock(), "test")
    assert scorer.score_citation({}, {}) == {}


def test_score_citations_paused():
    collected = [
        {
            "citation_id": "cid_1",
            "cited_title": "Paper",
            "citing_title": "Citer",
            "url": "",
            "citing_citation_count": 100,
            "notable_authors": [{"name": "Notable"}],
            "raw_contexts": ["Context"],
            "is_self_citation": False,
            "is_cached": False,
            "year": 2024,
            "venue": "",
        }
    ]
    mock_client = MagicMock()

    from backend.pipeline.phase_4_sentiment import score_citations

    with patch(
        "backend.pipeline.phase_4_sentiment.get_unscored_citations",
        return_value=collected,
    ):
        with patch("backend.pipeline.phase_4_sentiment.update_citation_sentiment_only"):
            with patch(
                "backend.database.sqlite_db.get_target_status", return_value="paused"
            ):
                score_citations(mock_client, "gemini-test", {}, "test_target")

    mock_client.models.generate_content.assert_not_called()


def test_score_citations_list_format_missing_id():
    """Test LLM list-of-objects parsed correctly when it lacks 'id' and 'score' directly."""
    collected = [
        {
            "citation_id": "cid_1",
            "cited_title": "Paper",
            "citing_title": "Citer",
            "url": "",
            "citing_citation_count": 100,
            "notable_authors": [{"name": "Notable"}],
            "raw_contexts": ["Context"],
            "is_self_citation": False,
            "is_cached": False,
            "year": 2024,
            "venue": "",
        }
    ]
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = """
    ```json
    [
        {"cid_1": {"score": 10, "positive_comment": "List inner dict"}}
    ]
    ```
    """

    from backend.pipeline.phase_4_sentiment import score_citations

    with patch(
        "backend.pipeline.phase_4_sentiment.get_unscored_citations",
        return_value=collected,
    ):
        with patch(
            "backend.pipeline.phase_4_sentiment.update_citation_sentiment_only"
        ) as mock_update:
            with patch(
                "backend.database.sqlite_db.get_target_status", return_value="running"
            ):
                score_citations(mock_client, "gemini-test", {}, "test_target")

    assert mock_update.call_count == 1
    assert mock_update.call_args[0][1]["positive_comment"] == "List inner dict"


def test_score_citations_invalid_url_and_exception():
    collected = [
        {
            "citation_id": "cid_1",
            "cited_title": "Paper",
            "citing_title": "Citer",
            "url": "",
            "citing_citation_count": 100,
            "notable_authors": [{"name": "Notable"}],
            "raw_contexts": ["Context"],
            "is_self_citation": False,
            "is_cached": False,
            "year": 2024,
            "venue": "",
        }
    ]
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = """
    ```json
    {"cid_1": {"score": 10, "paper_homepage": "invalid_url_no_scheme"}}
    ```
    """

    from backend.pipeline.phase_4_sentiment import score_citations

    with patch(
        "backend.pipeline.phase_4_sentiment.get_unscored_citations",
        return_value=collected,
    ):
        with patch(
            "backend.pipeline.phase_4_sentiment.update_citation_sentiment_only",
            side_effect=Exception("DB failure"),
        ):
            with patch(
                "backend.database.sqlite_db.get_target_status", return_value="running"
            ):
                score_citations(mock_client, "gemini-test", {}, "test_target")
    # Coverage ensures that the exception is passed and url reset happens


def test_score_citations_list_format():
    """Test that LLM list-of-objects response format is parsed correctly."""
    collected = [
        {
            "citation_id": "cid_1",
            "cited_title": "Paper",
            "citing_title": "Citer",
            "url": "",
            "citing_citation_count": 100,
            "notable_authors": [{"name": "Notable"}],
            "raw_contexts": ["Context"],
            "is_self_citation": False,
            "is_cached": False,
            "year": 2024,
            "venue": "",
        }
    ]
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = """
    ```json
    [
        {
            "id": "cid_1",
            "score": 10,
            "usage_classification": "Extending / Using",
            "positive_comment": "List format comment",
            "sentiment_evidence": "List evidence"
        }
    ]
    ```
    """

    from backend.pipeline.phase_4_sentiment import score_citations

    with patch(
        "backend.pipeline.phase_4_sentiment.get_unscored_citations",
        return_value=collected,
    ):
        with patch(
            "backend.pipeline.phase_4_sentiment.update_citation_sentiment_only"
        ) as mock_update:
            with patch(
                "backend.database.sqlite_db.get_target_status", return_value="running"
            ):
                score_citations(mock_client, "gemini-test", {}, "test_target")

    assert mock_update.call_count == 1
    assert mock_update.call_args[0][1]["score"] == 10
    assert mock_update.call_args[0][1]["positive_comment"] == "List format comment"


def test_score_citations_zero_matches_retries():
    """Test that LLM is retried if it returns JSON but 0 IDs match."""
    collected = [
        {
            "citation_id": "cid_1",
            "cited_title": "Paper",
            "citing_title": "Citer",
            "url": "",
            "citing_citation_count": 100,
            "notable_authors": [{"name": "Notable"}],
            "raw_contexts": ["Context"],
            "is_self_citation": False,
            "is_cached": False,
            "year": 2024,
            "venue": "",
        }
    ]
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = (
        '{"wrong_id": {"score": 5, "positive_comment": "..."}}'
    )

    from backend.pipeline.phase_4_sentiment import score_citations

    with patch(
        "backend.pipeline.phase_4_sentiment.get_unscored_citations",
        return_value=collected,
    ):
        with patch("time.sleep") as mock_sleep:
            with patch(
                "backend.database.sqlite_db.get_target_status", return_value="running"
            ):
                score_citations(mock_client, "gemini-test", {}, "test_target")

    # Retries 4 times (1 initial + 3 retries)
    # Each attempt does a 2s preemptive sleep + 3x 5s retries = 7 sleeps
    assert mock_client.models.generate_content.call_count == 4
    assert mock_sleep.call_count == 7


def test_score_citations_rate_limit():
    """Test that LLM rate limits trigger a sleep and retry, but hard quotas abort."""
    collected = [
        {
            "citation_id": "cid_1",
            "cited_title": "Paper",
            "citing_title": "Citer",
            "url": "",
            "citing_citation_count": 100,
            "notable_authors": [{"name": "Notable"}],
            "raw_contexts": ["Context"],
            "is_self_citation": False,
            "is_cached": False,
            "year": 2024,
            "venue": "",
        }
    ]
    mock_client = MagicMock()
    # Simulate a rate limit exception (429)
    mock_client.models.generate_content.side_effect = Exception(
        "HTTP 429 Resource Exhausted"
    )

    from backend.pipeline.phase_4_sentiment import score_citations

    with patch(
        "backend.pipeline.phase_4_sentiment.get_unscored_citations",
        return_value=collected,
    ):
        with patch("time.sleep") as mock_sleep:
            with patch(
                "backend.database.sqlite_db.get_target_status", return_value="running"
            ):
                score_citations(mock_client, "gemini-test", {}, "test_target")

    # Retries 4 times (1 initial + 3 retries) with 20s sleeps + 2s preemptive sleep each = 8 sleeps
    assert mock_sleep.call_count == 8

    # Hard quota aborts instantly without sleeping (except the 1st preemptive 2s sleep)
    mock_client.models.generate_content.side_effect = Exception(
        "GenerateRequestsPerDay quota exceeded"
    )
    mock_client.models.generate_content.reset_mock()
    with patch(
        "backend.pipeline.phase_4_sentiment.get_unscored_citations",
        return_value=collected,
    ):
        with patch("time.sleep") as mock_sleep:
            with patch(
                "backend.database.sqlite_db.get_target_status", return_value="running"
            ):
                score_citations(mock_client, "gemini-test", {}, "test_target")

    assert mock_sleep.call_count == 1
