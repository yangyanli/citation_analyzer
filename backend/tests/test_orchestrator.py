from unittest.mock import patch, MagicMock
import pytest
import argparse
from backend.pipeline.orchestrator import run_pipeline
from backend.database.sqlite_db import init_db

@pytest.fixture
def mock_args():
    return argparse.Namespace(
        user_id="test_user",
        paper=None,
        group_id=1,
        start_phase=0,
        generate_criteria_only=False,
        non_interactive=True,
        total_citations_to_add="10",
        estimate_only=False,
        model="test-model",
    )


@pytest.fixture
def mock_client():
    return MagicMock()


@patch("backend.pipeline.orchestrator.generate_domain_criteria")
@patch("backend.pipeline.orchestrator.collect_citations")
@patch("backend.pipeline.orchestrator.evaluate_authors")
@patch("backend.pipeline.orchestrator.score_citations")
@patch("backend.pipeline.orchestrator.upsert_analysis_target")
@patch("backend.pipeline.orchestrator.update_target_progress")
@patch("backend.pipeline.orchestrator.print_task_summary", return_value=10)
@patch("backend.pipeline.orchestrator.update_target_s2_total")
@patch("backend.pipeline.orchestrator.get_all_citations", return_value=[])
@patch("backend.pipeline.orchestrator.get_unscored_citations", return_value=[])
@patch("backend.pipeline.orchestrator.update_target_phase_estimates")
def test_run_pipeline_scholar_happy_path(
    mock_update_phase_est,
    mock_get_unscored,
    mock_get_all,
    mock_update_s2,
    mock_print_summary,
    mock_update_progress,
    mock_upsert,
    mock_score,
    mock_eval,
    mock_collect,
    mock_gen,
    mock_args,
    mock_client,
):
    with pytest.raises(ValueError, match="No publications found."):
        run_pipeline(mock_args, mock_client, overrides=None)


@patch("backend.pipeline.orchestrator.search_semantic_scholar_paper")
@patch("backend.pipeline.orchestrator.generate_domain_criteria")
@patch("backend.pipeline.orchestrator.collect_citations")
@patch("backend.pipeline.orchestrator.evaluate_authors")
@patch("backend.pipeline.orchestrator.score_citations")
@patch("backend.pipeline.orchestrator.upsert_analysis_target")
@patch("backend.pipeline.orchestrator.update_target_progress")
@patch("backend.pipeline.orchestrator.print_task_summary", return_value=1)
@patch("backend.pipeline.orchestrator.update_target_s2_total")
@patch("backend.pipeline.orchestrator.get_all_citations", return_value=[])
@patch("backend.pipeline.orchestrator.get_unscored_citations", return_value=[])
@patch("backend.pipeline.orchestrator.update_target_phase_estimates")
def test_run_pipeline_paper_happy_path(
    mock_update_phase_est,
    mock_get_unscored,
    mock_get_all,
    mock_update_s2,
    mock_print_summary,
    mock_update_progress,
    mock_upsert,
    mock_score,
    mock_eval,
    mock_collect,
    mock_gen,
    mock_search,
    mock_client,
):
    mock_get_all.return_value = [
        {"citation_id": "cid_1", "authors": [{"name": "Auth A"}], "citing_title": "Cite 1", "cited_title": "T"}
    ]
    mock_get_unscored.return_value = [
        {"citation_id": "cid_1", "authors": [{"name": "Auth A"}], "citing_title": "Cite 1", "cited_title": "T"}
    ]
    args = argparse.Namespace(
        user_id=None,
        paper="Test Paper Title",
        group_id=2,
        start_phase=0,
        generate_criteria_only=False,
        non_interactive=True,
        total_citations_to_add="10",
        estimate_only=False,
        model="test-model",
    )

    mock_search.return_value = {"title": "Test Paper Title", "paperId": "123"}
    mock_gen.return_value = {
        "domain": "AI",
        "notable_criteria": "x",
        "seminal_criteria": "y",
    }
    mock_collect.return_value = [
        {"citation_id": "cid_1", "authors": [{"name": "Auth A"}], "citing_title": "Cite 1", "cited_title": "T"}
    ]

    run_pipeline(args, mock_client, overrides=None)

    mock_search.assert_called_once_with("Test Paper Title")
    mock_gen.assert_called_once()
    mock_collect.assert_called_once()
    mock_eval.assert_called_once()
    mock_score.assert_called_once()


def test_run_pipeline_scholar_not_found(mock_args, mock_client):
    with pytest.raises(ValueError, match="No publications found."):
        run_pipeline(mock_args, mock_client, overrides=None)


@patch("backend.pipeline.orchestrator.search_semantic_scholar_paper", return_value=None)
def test_run_pipeline_paper_not_found(mock_search, mock_client):
    args = argparse.Namespace(
        user_id=None,
        paper="Unknown",
        group_id=1,
        start_phase=0,
        estimate_only=False,
        generate_criteria_only=False,
        total_citations_to_add="all",
        non_interactive=True,
        model="gemini",
    )
    with pytest.raises(ValueError, match="Could not find paper 'Unknown'"):
        run_pipeline(args, mock_client, overrides=None)


@patch("backend.pipeline.orchestrator.generate_domain_criteria")
@patch("backend.pipeline.orchestrator.upsert_analysis_target")
@patch("backend.pipeline.orchestrator.update_target_progress")
def test_run_pipeline_generate_criteria_only(
    mock_update_progress,
    mock_upsert,
    mock_gen,
    mock_args,
    mock_client,
    capsys,
):
    mock_args.generate_criteria_only = True
    mock_args.user_id = None
    mock_args.paper = "Test"
    with patch("backend.pipeline.orchestrator.search_semantic_scholar_paper") as mock_search:
        mock_search.return_value = {"paperId": "123", "title": "Test"}
        mock_gen.return_value = {"domain": "AI"}

        with pytest.raises(SystemExit):
            run_pipeline(mock_args, mock_client, overrides=None)

        captured = capsys.readouterr()
        assert "---CRITERIA_JSON_START---" in captured.out
        assert "---CRITERIA_JSON_END---" in captured.out
        assert '{"domain": "AI"}' in captured.out


@patch("backend.pipeline.orchestrator.get_analysis_target")
@patch("backend.pipeline.orchestrator.upsert_analysis_target")
@patch("backend.pipeline.orchestrator.update_target_progress")
@patch("backend.pipeline.orchestrator.print_task_summary", return_value=1)
@patch("backend.pipeline.orchestrator.update_target_s2_total")
@patch("backend.pipeline.orchestrator.get_all_citations", return_value=[])
def test_run_pipeline_skip_phase_0_no_data_in_db(
    mock_get_all,
    mock_update_s2,
    mock_print,
    mock_update_prog,
    mock_upsert,
    mock_get_target,
    mock_args,
    mock_client,
):
    mock_args.start_phase = 1
    mock_args.user_id = None
    mock_args.paper = "Test"
    
    with patch("backend.pipeline.orchestrator.search_semantic_scholar_paper") as mock_search:
        mock_search.return_value = {"paperId": "123", "title": "Test"}
        mock_get_target.return_value = None  # DB has no criteria

        with pytest.raises(
            ValueError, match="Cannot skip phase 0: No criteria found in DB"
        ):
            run_pipeline(mock_args, mock_client, overrides=None)


# ---------------------------------------------------------------------------
# Tests for --run_only_phase mechanism
# ---------------------------------------------------------------------------


def _make_args(**overrides):
    """Helper to create a Namespace with sensible defaults for orchestrator tests."""
    defaults = dict(
        user_id=None,
        paper="Test Paper",
        group_id=1,
        start_phase=0,
        run_only_phase=None,
        wipe_phase=None,
        generate_criteria_only=False,
        non_interactive=True,
        total_citations_to_add="all",
        estimate_only=False,
        model="test-model",
        system_user_id=None,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class TestRunOnlyPhase:
    """Validate --run_only_phase gating, S2/cost skip, and error handling."""

    # -- Helper: common patches that let the pipeline reach the phase-gating block --
    COMMON_PATCHES = {
        "search": "backend.pipeline.orchestrator.search_semantic_scholar_paper",
        "gen": "backend.pipeline.orchestrator.generate_domain_criteria",
        "collect": "backend.pipeline.orchestrator.collect_citations",
        "eval_authors": "backend.pipeline.orchestrator.evaluate_authors",
        "eval_seminal": "backend.pipeline.orchestrator.evaluate_seminal_works",
        "score": "backend.pipeline.orchestrator.score_citations",
        "upsert": "backend.pipeline.orchestrator.upsert_analysis_target",
        "progress": "backend.pipeline.orchestrator.update_target_progress",
        "summary": "backend.pipeline.orchestrator.print_task_summary",
        "s2_total": "backend.pipeline.orchestrator.update_target_s2_total",
        "get_all": "backend.pipeline.orchestrator.get_all_citations",
        "get_unscored": "backend.pipeline.orchestrator.get_unscored_citations",
        "phase_est": "backend.pipeline.orchestrator.update_target_phase_estimates",
        "get_target": "backend.pipeline.orchestrator.get_analysis_target",
        "get_author": "backend.pipeline.orchestrator.get_author",
    }

    def _run_with_patches(self, args, patches_config=None):
        """Run the pipeline with all common patches applied.
        Returns a dict of MagicMock objects keyed by short name.
        """
        mocks = {}
        stack = []
        import contextlib

        with contextlib.ExitStack() as exit_stack:
            for name, target in self.COMMON_PATCHES.items():
                m = exit_stack.enter_context(patch(target))
                mocks[name] = m

            # Set up sensible return values
            mocks["search"].return_value = {"paperId": "abc", "title": "Test Paper"}
            mocks["gen"].return_value = {
                "inferred_domain": "AI",
                "notable_criteria": "criteria",
                "seminal_criteria": "criteria",
            }
            sample_citation = {
                "citation_id": "c1",
                "authors": [{"name": "A"}],
                "citing_title": "C",
                "cited_title": "T",
            }
            mocks["collect"].return_value = [sample_citation]
            mocks["get_all"].return_value = [sample_citation]
            mocks["get_unscored"].return_value = [sample_citation]
            mocks["summary"].return_value = 100  # total_citations_s2
            mocks["get_author"].return_value = None  # unknown author
            mocks["get_target"].return_value = {
                "evaluation_criteria": {
                    "inferred_domain": "AI",
                    "notable_criteria": "criteria",
                    "seminal_criteria": "criteria",
                }
            }

            # Apply any custom overrides
            if patches_config:
                for key, cfg in patches_config.items():
                    if key in mocks:
                        if "return_value" in cfg:
                            mocks[key].return_value = cfg["return_value"]
                        if "side_effect" in cfg:
                            mocks[key].side_effect = cfg["side_effect"]

            client = MagicMock()
            run_pipeline(args, client, overrides=None)
            return mocks

    # Test 1: --run_only_phase 4 calls ONLY score_citations (not evaluate_authors / evaluate_seminal)
    def test_run_only_phase_4_calls_only_score(self):
        args = _make_args(run_only_phase=4)
        mocks = self._run_with_patches(args)

        mocks["score"].assert_called_once()
        mocks["eval_authors"].assert_not_called()
        mocks["eval_seminal"].assert_not_called()
        # Phase 0 criteria generation should be skipped (start_phase is auto-set to 4)
        mocks["gen"].assert_not_called()

    # Test 2: --run_only_phase 2 calls ONLY evaluate_authors
    def test_run_only_phase_2_calls_only_authors(self):
        args = _make_args(run_only_phase=2)
        mocks = self._run_with_patches(args)

        mocks["eval_authors"].assert_called_once()
        mocks["eval_seminal"].assert_not_called()
        mocks["score"].assert_not_called()
        mocks["gen"].assert_not_called()

    # Test 3: --run_only_phase 3 calls ONLY evaluate_seminal
    def test_run_only_phase_3_calls_only_seminal(self):
        args = _make_args(run_only_phase=3)
        mocks = self._run_with_patches(args)

        mocks["eval_seminal"].assert_called_once()
        mocks["eval_authors"].assert_not_called()
        mocks["score"].assert_not_called()
        mocks["gen"].assert_not_called()

    # Test 4: --run_only_phase skips S2 summary fetch, cost table, and model selection
    def test_run_only_phase_skips_s2_and_cost(self):
        args = _make_args(run_only_phase=4)
        mocks = self._run_with_patches(args)

        # print_task_summary (which fetches S2 counts) should NOT be called
        mocks["summary"].assert_not_called()
        # update_target_s2_total should NOT be called
        mocks["s2_total"].assert_not_called()

    # Test 5: --run_only_phase sets start_phase automatically
    def test_run_only_phase_overrides_start_phase(self):
        args = _make_args(run_only_phase=4, start_phase=0)
        # After run_pipeline processes the args, start_phase should be 4
        mocks = self._run_with_patches(args)
        # This is verified indirectly: Phase 0 gen should NOT be called
        mocks["gen"].assert_not_called()
        # And explicitly: args.start_phase should be 4
        assert args.start_phase == 4

    # Test 6: --run_only_phase with missing criteria raises ValueError
    def test_run_only_phase_no_criteria_raises_error(self):
        args = _make_args(run_only_phase=4)
        with pytest.raises(ValueError, match="Cannot skip phase 0"):
            self._run_with_patches(
                args,
                patches_config={
                    "get_target": {"return_value": None},
                },
            )

    # Test 7: --run_only_phase with existing criteria loads them properly
    def test_run_only_phase_loads_existing_criteria(self):
        args = _make_args(run_only_phase=4)
        saved_criteria = {
            "inferred_domain": "Computer Vision",
            "notable_criteria": "Turing Award",
            "seminal_criteria": "PointNet",
        }
        mocks = self._run_with_patches(
            args,
            patches_config={
                "get_target": {
                    "return_value": {"evaluation_criteria": saved_criteria}
                },
            },
        )
        # score_citations should be called with the saved criteria
        call_args = mocks["score"].call_args
        assert call_args[0][2] == saved_criteria  # Third positional arg is eval_criteria


class TestUpsertPreservesCriteria:
    """Verify that upsert_analysis_target does not overwrite criteria with empty dict."""

    def test_upsert_without_criteria_preserves_existing(self):
        from backend.database.targets import upsert_analysis_target, get_analysis_target

        # Step 1: Insert a target WITH criteria
        upsert_analysis_target("test_preserve", {
            "mode": "scholar",
            "name": "Test",
            "evaluation_criteria": {"domain": "AI", "notable": "x", "seminal": "y"},
        })

        # Step 2: Upsert again WITHOUT criteria (simulating pipeline re-entry)
        upsert_analysis_target("test_preserve", {
            "mode": "scholar",
            "name": "Test Updated",
        })

        # Step 3: Criteria should still be there
        target = get_analysis_target("test_preserve")
        assert target is not None
        assert target["evaluation_criteria"] == {"domain": "AI", "notable": "x", "seminal": "y"}
        # Name should be updated
        assert target["name"] == "Test Updated"

    def test_upsert_with_new_criteria_does_update(self):
        from backend.database.targets import upsert_analysis_target, get_analysis_target

        upsert_analysis_target("test_update_criteria", {
            "mode": "scholar",
            "name": "Test",
            "evaluation_criteria": {"domain": "Old"},
        })

        upsert_analysis_target("test_update_criteria", {
            "mode": "scholar",
            "name": "Test",
            "evaluation_criteria": {"domain": "New"},
        })

        target = get_analysis_target("test_update_criteria")
        assert target["evaluation_criteria"] == {"domain": "New"}


# ---------------------------------------------------------------------------
# Tests for S2 (Semantic Scholar) author ID code path
# ---------------------------------------------------------------------------


class TestS2AuthorPath:
    """Validate the Semantic Scholar author ID code path in the orchestrator.

    When --user_id is a numeric string (e.g. '145540632'), the orchestrator
    should use fetch_s2_author instead of Google Scholar's fetch_scholar_publications.
    """

    COMMON_PATCHES = {
        "fetch_s2_author": "backend.pipeline.orchestrator.fetch_s2_author",
        "fetch_gs": "backend.pipeline.orchestrator.fetch_scholar_publications",
        "gen": "backend.pipeline.orchestrator.generate_domain_criteria",
        "collect": "backend.pipeline.orchestrator.collect_citations",
        "eval_authors": "backend.pipeline.orchestrator.evaluate_authors",
        "eval_seminal": "backend.pipeline.orchestrator.evaluate_seminal_works",
        "score": "backend.pipeline.orchestrator.score_citations",
        "classify": "backend.pipeline.orchestrator.classify_domains",
        "upsert": "backend.pipeline.orchestrator.upsert_analysis_target",
        "progress": "backend.pipeline.orchestrator.update_target_progress",
        "summary": "backend.pipeline.orchestrator.print_task_summary",
        "s2_total": "backend.pipeline.orchestrator.update_target_s2_total",
        "get_all": "backend.pipeline.orchestrator.get_all_citations",
        "get_unscored": "backend.pipeline.orchestrator.get_unscored_citations",
        "phase_est": "backend.pipeline.orchestrator.update_target_phase_estimates",
        "get_target": "backend.pipeline.orchestrator.get_analysis_target",
        "get_author": "backend.pipeline.orchestrator.get_author",
        "total_cit": "backend.pipeline.orchestrator.update_target_total_citations",
    }

    S2_AUTHOR_RESPONSE = {
        "authorId": "145540632",
        "name": "Yann LeCun",
        "affiliations": ["New York University"],
        "homepage": "http://yann.lecun.com",
        "paperCount": 500,
        "citationCount": 200000,
        "hIndex": 150,
        "papers": [
            {"title": "Gradient-Based Learning Applied to Document Recognition", "year": 1998, "citationCount": 40000},
            {"title": "Deep Learning", "year": 2015, "citationCount": 30000},
            {"title": "Convolutional Networks for Images", "year": 2010, "citationCount": 5000},
        ],
    }

    def _run_with_patches(self, args, patches_config=None):
        """Run the pipeline with all common patches applied."""
        import contextlib

        mocks = {}
        with contextlib.ExitStack() as exit_stack:
            for name, target in self.COMMON_PATCHES.items():
                m = exit_stack.enter_context(patch(target))
                mocks[name] = m

            # Default return values
            mocks["fetch_s2_author"].return_value = self.S2_AUTHOR_RESPONSE
            mocks["gen"].return_value = {
                "inferred_domain": "Deep Learning",
                "notable_criteria": "Turing Award",
                "seminal_criteria": "50+ citations",
            }
            sample_citation = {
                "citation_id": "c1",
                "authors": [{"name": "A"}],
                "citing_title": "C",
                "cited_title": "T",
            }
            mocks["collect"].return_value = [sample_citation]
            mocks["get_all"].return_value = [sample_citation]
            mocks["get_unscored"].return_value = [sample_citation]
            mocks["summary"].return_value = 100
            mocks["get_author"].return_value = None
            mocks["get_target"].return_value = {
                "evaluation_criteria": {
                    "inferred_domain": "Deep Learning",
                    "notable_criteria": "Turing Award",
                    "seminal_criteria": "50+ citations",
                }
            }

            if patches_config:
                for key, cfg in patches_config.items():
                    if key in mocks:
                        if "return_value" in cfg:
                            mocks[key].return_value = cfg["return_value"]
                        if "side_effect" in cfg:
                            mocks[key].side_effect = cfg["side_effect"]

            client = MagicMock()
            run_pipeline(args, client, overrides=None)
            return mocks

    # -- Test 1: Numeric user_id calls fetch_s2_author, NOT fetch_scholar_publications --
    def test_numeric_id_uses_s2_author(self):
        args = _make_args(user_id="145540632", paper=None)
        mocks = self._run_with_patches(args)

        mocks["fetch_s2_author"].assert_called_once_with("145540632")
        mocks["fetch_gs"].assert_not_called()

    # -- Test 2: Non-numeric user_id calls fetch_scholar_publications, NOT fetch_s2_author --
    def test_alphanumeric_id_uses_google_scholar(self):
        args = _make_args(user_id="JicYPdAAAAAJ", paper=None)
        mocks = self._run_with_patches(
            args,
            patches_config={
                "fetch_gs": {
                    "return_value": {
                        "name": "Geoffrey Hinton",
                        "interests": ["deep learning"],
                        "publications": [{"bib": {"title": "Backpropagation"}}],
                    }
                }
            },
        )

        mocks["fetch_gs"].assert_called_once_with("JicYPdAAAAAJ")
        mocks["fetch_s2_author"].assert_not_called()

    # -- Test 3: S2 author not found raises ValueError --
    def test_s2_author_not_found_raises_error(self):
        args = _make_args(user_id="999999999", paper=None)
        with pytest.raises(ValueError, match="Could not find Semantic Scholar author"):
            self._run_with_patches(
                args,
                patches_config={"fetch_s2_author": {"return_value": None}},
            )

    # -- Test 4: S2 author papers are correctly mapped to publications format --
    def test_s2_papers_mapped_to_publications(self):
        args = _make_args(user_id="145540632", paper=None)
        mocks = self._run_with_patches(args)

        # collect_citations should receive publications in {"bib": {"title": ...}} format
        collect_call = mocks["collect"].call_args
        publications = collect_call[0][0]  # first positional arg
        assert len(publications) == 3
        assert all("bib" in p for p in publications)
        assert publications[0]["bib"]["title"] == "Gradient-Based Learning Applied to Document Recognition"
        assert publications[1]["bib"]["title"] == "Deep Learning"

    # -- Test 5: S2 analysis target has correct metadata (S2 URL, not GS URL) --
    def test_s2_target_has_correct_url_and_mode(self):
        args = _make_args(user_id="145540632", paper=None)
        mocks = self._run_with_patches(args)

        # Check the upsert call to see what analysis_target was stored
        upsert_call = mocks["upsert"].call_args
        target_data = upsert_call[0][1]  # second positional arg
        assert target_data["mode"] == "scholar"
        assert target_data["name"] == "Yann LeCun"
        assert "semanticscholar.org" in target_data["url"]
        assert "145540632" in target_data["url"]

    # -- Test 6: scholar_name from S2 is passed correctly to collect_citations --
    def test_scholar_name_passed_from_s2(self):
        args = _make_args(user_id="145540632", paper=None)
        mocks = self._run_with_patches(args)

        collect_call = mocks["collect"].call_args
        scholar_name = collect_call[0][1]  # second positional arg
        assert scholar_name == "Yann LeCun"

    # -- Test 7: S2 author path with --start_phase > 0 loads criteria from DB --
    def test_s2_author_skip_phase_0(self):
        args = _make_args(user_id="145540632", paper=None, start_phase=2)
        mocks = self._run_with_patches(args)

        # Phase 0 criteria generation should be skipped
        mocks["gen"].assert_not_called()
        # Criteria should be loaded from DB
        mocks["get_target"].assert_called()
        # Phase 2 should still run
        mocks["eval_authors"].assert_called_once()

    # -- Test 8: S2 author with no papers raises ValueError --
    def test_s2_author_no_papers(self):
        args = _make_args(user_id="145540632", paper=None)
        empty_author = dict(self.S2_AUTHOR_RESPONSE, papers=[])
        # The pipeline should still proceed (publications will be empty, collect_citations may find none)
        # but it shouldn't crash — it should reach the "No new citations" path
        mocks = self._run_with_patches(
            args,
            patches_config={
                "fetch_s2_author": {"return_value": empty_author},
                "collect": {"return_value": []},
                "get_all": {"return_value": []},
                "get_unscored": {"return_value": []},
            },
        )
        # Pipeline should complete (progress set to 100%)
        progress_calls = [c[0] for c in mocks["progress"].call_args_list]
        assert any(call[1] == "completed" for call in progress_calls)


