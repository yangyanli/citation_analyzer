"""Tests for Phase 3 — seminal discovery and grouping."""

import json
from unittest.mock import patch, MagicMock


class TestPhase3SeminalGrouping:
    """Test the grouping and update logic in evaluate_seminal_works."""

    def _run_evaluation(self, llm_response_text, all_citations_mock):
        mock_response = MagicMock()
        mock_response.text = llm_response_text

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        from backend.pipeline.phase_3_seminal import evaluate_seminal_works

        with patch(
            "backend.pipeline.phase_3_seminal.get_all_citations",
            return_value=all_citations_mock,
        ):
            with patch(
                "backend.pipeline.phase_3_seminal.get_target_status",
                return_value="running",
            ):
                with patch("backend.database.sqlite_db.update_target_progress"):
                    with patch(
                        "backend.database.sqlite_db.update_citation_seminal"
                    ) as mock_update:
                        evaluate_seminal_works(
                            mock_client,
                            "gemini-2.5-flash",
                            {"seminal_criteria": "test"},
                            "target_123",
                        )
                        return mock_update

    def test_grouping_multiple_citations_same_paper(self):
        """Test that multiple citations from the same citing paper are updated together."""
        citations = [
            {
                "citation_id": "c1",
                "citing_title": "Paper A",
                "year": 2024,
                "venue": "CVPR",
                "citing_citation_count": 100,
            },
            {
                "citation_id": "c2",
                "citing_title": "Paper A",
                "year": 2024,
                "venue": "CVPR",
                "citing_citation_count": 100,
            },
            {
                "citation_id": "c3",
                "citing_title": "Paper B",
                "year": 2023,
                "venue": "ICCV",
                "citing_citation_count": 50,
            },
        ]

        response = json.dumps(
            {
                "Paper A": {"is_seminal": True, "seminal_evidence": "Highly cited"},
                "Paper B": {"is_seminal": False, "seminal_evidence": "Not enough"},
            }
        )

        mock_update = self._run_evaluation(response, citations)

        # 3 citations should result in 3 update_citation_seminal calls
        assert mock_update.call_count == 3

        # Check that c1 and c2 got is_seminal = True
        calls = mock_update.call_args_list
        c1_call = [c for c in calls if c[0][0] == "c1"][0]
        c2_call = [c for c in calls if c[0][0] == "c2"][0]
        c3_call = [c for c in calls if c[0][0] == "c3"][0]

        assert c1_call[0][1] is True
        assert c2_call[0][1] is True
        assert c3_call[0][1] is False

    def test_json_list_parsing(self):
        """Test that the LLM returning a JSON list is handled correctly."""
        citations = [
            {
                "citation_id": "c1",
                "citing_title": "Paper A",
                "year": 2024,
                "venue": "CVPR",
                "citing_citation_count": 100,
            },
        ]

        response = json.dumps(
            [{"title": "Paper A", "is_seminal": True, "seminal_evidence": "Yes"}]
        )

        mock_update = self._run_evaluation(response, citations)
        assert mock_update.call_count == 1
        assert mock_update.call_args[0][1] is True

    @patch('backend.pipeline.phase_3_seminal.logger')
    def test_empty_json_response(self, mock_logger):
        """Test that an empty JSON object is considered a valid 0-match success and breaks the loop."""
        citations = [
            {
                "citation_id": "c1",
                "citing_title": "Paper A",
                "year": 2024,
                "venue": "CVPR",
                "citing_citation_count": 100,
            },
        ]

        response = json.dumps({})

        mock_update = self._run_evaluation(response, citations)
        # Should not throw and should break the loop cleanly
        mock_logger.info.assert_any_call("  Batch processed correctly but 0 seminal papers identified natively.")
        assert mock_update.call_count == 0
