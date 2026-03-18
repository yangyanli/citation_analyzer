"""Tests for Phase 5 — research domain classification and JSON parsing."""

import json
from unittest.mock import patch, MagicMock


class TestPhase5DomainClassification:
    """Test the JSON extraction and key matching logic in classify_domains."""

    def _run_classification(self, llm_response_text, citations):
        """Helper to run classify_domains with a mocked LLM response."""
        eval_criteria = {"inferred_domain": "Computer Vision"}

        mock_response = MagicMock()
        mock_response.text = llm_response_text

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        from backend.pipeline.phase_5_domains import classify_domains

        with patch(
            "backend.pipeline.phase_5_domains.get_all_citations",
            return_value=citations,
        ):
            with patch(
                "backend.pipeline.phase_5_domains.update_citation_domain"
            ) as mock_update:
                with patch(
                    "backend.database.sqlite_db.get_target_status",
                    return_value="running",
                ):
                    classify_domains(
                        mock_client, "gemini-2.5-flash", eval_criteria, "target_123"
                    )
                    return mock_update

    def _make_citation(self, citation_id, citing_title, research_domain=None):
        """Create a citation dict for testing."""
        return {
            "citation_id": citation_id,
            "cited_title": "Target Paper",
            "citing_title": citing_title,
            "url": "",
            "year": 2024,
            "venue": "CVPR",
            "citing_citation_count": 100,
            "notable_authors": [],
            "raw_contexts": ["The paper is good."],
            "research_domain": research_domain,
        }

    def test_exact_title_match(self):
        """LLM returns exact title keys → domains stored."""
        title = "Deep Learning for Object Detection"
        citation = self._make_citation("cid_1", title)
        response = json.dumps({title: {"domain": "Computer Vision"}})
        mock_update = self._run_classification(response, [citation])
        mock_update.assert_called_once_with("cid_1", "Computer Vision", "target_123")

    def test_fuzzy_title_match(self):
        """LLM truncates title → fuzzy prefix match recovers it."""
        full_title = "A Very Long Paper Title About Something Important in AI Research"
        truncated = "A Very Long Paper Ti"
        citation = self._make_citation("cid_1", full_title)
        response = json.dumps({truncated: {"domain": "Artificial Intelligence"}})
        mock_update = self._run_classification(response, [citation])
        mock_update.assert_called_once_with("cid_1", "Artificial Intelligence", "target_123")

    def test_list_format_response(self):
        """LLM returns [{title: ..., domain: ...}] → coerced to dict."""
        title = "NLP Paper"
        citation = self._make_citation("cid_1", title)
        response = json.dumps([{"title": title, "domain": "Natural Language Processing"}])
        mock_update = self._run_classification(response, [citation])
        mock_update.assert_called_once_with("cid_1", "Natural Language Processing", "target_123")

    def test_markdown_wrapped_json(self):
        """LLM wraps response in ```json ... ``` → extracted correctly."""
        title = "Robotics Paper"
        citation = self._make_citation("cid_1", title)
        inner = json.dumps({title: {"domain": "Robotics"}})
        response = f"```json\n{inner}\n```"
        mock_update = self._run_classification(response, [citation])
        mock_update.assert_called_once_with("cid_1", "Robotics", "target_123")

    def test_skips_already_classified(self):
        """Citations with existing domain are skipped entirely."""
        citation = self._make_citation("cid_1", "Already Classified", research_domain="Computer Vision")
        mock_client = MagicMock()

        from backend.pipeline.phase_5_domains import classify_domains

        with patch(
            "backend.pipeline.phase_5_domains.get_all_citations",
            return_value=[citation],
        ):
            with patch(
                "backend.pipeline.phase_5_domains.update_citation_domain"
            ) as mock_update:
                with patch(
                    "backend.database.sqlite_db.get_target_status",
                    return_value="running",
                ):
                    classify_domains(
                        mock_client, "gemini-test", {}, "target_123"
                    )

        mock_client.models.generate_content.assert_not_called()
        mock_update.assert_not_called()

    def test_paused_target_skips(self):
        """Paused target aborts immediately."""
        title = "Some Paper"
        citation = self._make_citation("cid_1", title)

        mock_response = MagicMock()
        mock_response.text = json.dumps({title: {"domain": "ML"}})
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        from backend.pipeline.phase_5_domains import classify_domains

        with patch(
            "backend.pipeline.phase_5_domains.get_all_citations",
            return_value=[citation],
        ):
            with patch(
                "backend.pipeline.phase_5_domains.update_citation_domain"
            ) as mock_update:
                with patch(
                    "backend.pipeline.phase_5_domains.get_target_status",
                    return_value="paused",
                ):
                    classify_domains(
                        mock_client, "gemini-test", {}, "target_123"
                    )

        mock_client.models.generate_content.assert_not_called()
        mock_update.assert_not_called()

    def test_zero_matches_retries(self):
        """LLM returns JSON but 0 titles match → retries up to 4 times."""
        title = "Real Paper"
        citation = self._make_citation("cid_1", title)

        mock_response = MagicMock()
        mock_response.text = json.dumps({"Wrong Title": {"domain": "ML"}})
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        from backend.pipeline.phase_5_domains import classify_domains

        with patch(
            "backend.pipeline.phase_5_domains.get_all_citations",
            return_value=[citation],
        ):
            with patch("time.sleep") as mock_sleep:
                with patch(
                    "backend.database.sqlite_db.get_target_status",
                    return_value="running",
                ):
                    classify_domains(
                        mock_client, "gemini-test", {}, "target_123"
                    )

        assert mock_client.models.generate_content.call_count == 4

    def test_multiple_citations_same_title(self):
        """Multiple citations with same citing_title get the same domain."""
        title = "Shared Paper"
        citations = [
            self._make_citation("cid_1", title),
            self._make_citation("cid_2", title),
        ]
        response = json.dumps({title: {"domain": "Machine Learning"}})
        mock_update = self._run_classification(response, citations)
        assert mock_update.call_count == 2
        mock_update.assert_any_call("cid_1", "Machine Learning", "target_123")
        mock_update.assert_any_call("cid_2", "Machine Learning", "target_123")

    def test_empty_domain_skipped(self):
        """LLM returns empty domain string → citation not updated."""
        title = "Some Paper"
        citation = self._make_citation("cid_1", title)
        response = json.dumps({title: {"domain": ""}})
        mock_update = self._run_classification(response, [citation])
        mock_update.assert_not_called()

    def test_no_citations_returns_early(self):
        """No citations → returns immediately without calling LLM."""
        mock_client = MagicMock()

        from backend.pipeline.phase_5_domains import classify_domains

        with patch(
            "backend.pipeline.phase_5_domains.get_all_citations",
            return_value=[],
        ):
            classify_domains(mock_client, "gemini-test", {}, "target_123")

        mock_client.models.generate_content.assert_not_called()

    def test_rate_limit_retries(self):
        """Rate limit (429) triggers sleep and retry."""
        title = "Rate Limited Paper"
        citation = self._make_citation("cid_1", title)

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception(
            "HTTP 429 Resource Exhausted"
        )

        from backend.pipeline.phase_5_domains import classify_domains

        with patch(
            "backend.pipeline.phase_5_domains.get_all_citations",
            return_value=[citation],
        ):
            with patch("time.sleep") as mock_sleep:
                with patch(
                    "backend.database.sqlite_db.get_target_status",
                    return_value="running",
                ):
                    classify_domains(
                        mock_client, "gemini-test", {}, "target_123"
                    )

        # 4 attempts with 20s retries + preemptive sleeps
        assert mock_sleep.call_count == 8

    def test_daily_quota_aborts(self):
        """Daily quota exhaustion aborts instantly."""
        title = "Quota Paper"
        citation = self._make_citation("cid_1", title)

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception(
            "GenerateRequestsPerDay quota exceeded"
        )

        from backend.pipeline.phase_5_domains import classify_domains

        with patch(
            "backend.pipeline.phase_5_domains.get_all_citations",
            return_value=[citation],
        ):
            with patch("time.sleep") as mock_sleep:
                with patch(
                    "backend.database.sqlite_db.get_target_status",
                    return_value="running",
                ):
                    classify_domains(
                        mock_client, "gemini-test", {}, "target_123"
                    )

        # Only 1 preemptive sleep before the abort
        assert mock_sleep.call_count == 1
