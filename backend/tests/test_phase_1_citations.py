import pytest
from unittest.mock import patch

from backend.pipeline.phase_1_citations import collect_citations
from backend.database.sqlite_db import (
    init_db,
    get_unscored_citations,
    get_all_citations,
)


@pytest.fixture
def mock_s2_search():
    with patch(
        "backend.api.semantic_scholar.SemanticScholarProvider.search_paper"
    ) as mock:
        yield mock


@pytest.fixture
def mock_s2_fetch():
    with patch(
        "backend.api.semantic_scholar.SemanticScholarProvider.fetch_citations"
    ) as mock:
        yield mock


def test_collect_citations_success(mock_s2_search, mock_s2_fetch):
    # Setup mocks
    mock_s2_search.return_value = {
        "paperId": "p123",
        "title": "Groundbreaking Research",
        "citationCount": 5,
    }

    import uuid

    cid_001 = f"cid_001_{uuid.uuid4()}"
    cid_002 = f"cid_002_{uuid.uuid4()}"

    mock_s2_fetch.return_value = [
        {
            "contexts": ["Great paper referenced here."],
            "citingPaper": {
                "paperId": cid_001,
                "title": "Citing Paper A",
                "year": 2024,
                "venue": "CVPR",
                "citationCount": 10,
                "authors": [{"name": "Jane Doe"}],
                "url": "http://example.com/a",
            },
        },
        {
            "contexts": ["Self citation."],
            "citingPaper": {
                "paperId": cid_002,
                "title": "Citing Paper B (Self)",
                "year": 2024,
                "authors": [{"name": "Target Author"}],
            },
        },
    ]

    publications = [{"bib": {"title": "Groundbreaking Research"}}]

    initial_all = len(get_all_citations("test_target_id"))
    initial_unscored = len(get_unscored_citations("test_target_id"))

    citations = collect_citations(
        publications=publications,
        scholar_name="Target Author",
        total_citations_to_add=10,
        target_id="test_target_id",
    )

    assert len(citations) == 2

    # Verify the first citation (normal)
    assert citations[0]["citation_id"] == cid_001
    assert citations[0]["citing_title"] == "Citing Paper A"
    assert citations[0]["is_self_citation"] is False
    assert citations[0]["is_cached"] is False
    assert citations[0]["year"] == 2024
    assert citations[0]["venue"] == "CVPR"

    # Verify the second citation (self-citation)
    assert citations[1]["citation_id"] == cid_002
    assert citations[1]["is_self_citation"] is True

    # Verify DB insertion
    db_citations = get_all_citations("test_target_id")
    assert len(db_citations) == initial_all + 2

    # They should be inserted as 'unscored' initially
    unscored = get_unscored_citations("test_target_id")
    assert len(unscored) == initial_unscored + 2


def test_collect_citations_limit(mock_s2_search, mock_s2_fetch):
    mock_s2_search.return_value = {"paperId": "p123", "title": "Paper 1"}

    # Generate 15 citing papers
    mock_s2_fetch.return_value = [
        {"citingPaper": {"paperId": f"cid_{i}", "title": f"Paper {i}"}}
        for i in range(15)
    ]

    publications = [{"bib": {"title": "Paper 1"}}]

    # Limit to 5
    citations = collect_citations(
        publications=publications,
        scholar_name="Target Author",
        total_citations_to_add=5,
        target_id="test_target_id",
    )

    assert len(citations) == 5
    assert citations[-1]["citation_id"] == "cid_4"


def test_collect_citations_search_fails(mock_s2_search, mock_s2_fetch):
    # Simulate a timeout or None returned from Search
    mock_s2_search.return_value = None

    publications = [{"bib": {"title": "Ghost Paper"}}]

    citations = collect_citations(
        publications=publications,
        scholar_name="Target Author",
        total_citations_to_add=10,
        target_id="test_target_id",
    )

    # Should safely return empty and skip without crashing
    assert len(citations) == 0


def test_collect_citations_rate_limit(mock_s2_search, mock_s2_fetch):
    mock_s2_search.return_value = {"paperId": "p123", "title": "Paper 1"}

    # Simulate HTTPError for rate limiting causing None
    mock_s2_fetch.return_value = None

    publications = [{"bib": {"title": "Paper 1"}}]

    citations = collect_citations(
        publications=publications,
        scholar_name="Target Author",
        total_citations_to_add=10,
        target_id="test_target_id",
    )

    assert len(citations) == 0


@patch("backend.database.sqlite_db.get_target_status")
def test_collect_citations_edge_cases(
    mock_get_target_status, mock_s2_search, mock_s2_fetch
):
    # Test paused status
    mock_get_target_status.return_value = "paused"
    publications = [{"bib": {"title": "Title 1"}}]
    citations = collect_citations(publications, "Author", "all", "test_target_id")
    assert len(citations) == 0

    # Test missing title in publication, missing title but found via search, missing citing paper, missing citing paperId
    mock_get_target_status.return_value = "running"

    # Missing title in pub
    publications = [
        {"bib": {}},  # No title
        {"bib": {"title": "Valid Title"}},  # Valid title
    ]

    mock_s2_search.return_value = {
        "paperId": "p1",
        "title": "Valid Title",
        "citationCount": 3,
    }
    mock_s2_fetch.return_value = [
        {"contexts": ["Citing paper with no 'citingPaper' object"]},
        {"citingPaper": {}, "contexts": ["Empty citing paper"]},
        {"citingPaper": {"title": "No ID"}, "contexts": ["Missing paperId"]},
        {"citingPaper": {"paperId": "valid_1", "title": "Valid Citing Paper"}},
    ]

    citations = collect_citations(
        publications=publications,
        scholar_name="Author",
        total_citations_to_add="all",
        target_id="test_target_id",
    )

    # Only 1 valid citation expected
    assert len(citations) == 1
    assert citations[0]["citation_id"] == "valid_1"


def test_collect_citations_limit_break_outer_loop(mock_s2_search, mock_s2_fetch):
    mock_s2_search.side_effect = [
        {"paperId": "p1", "title": "Paper 1"},
        {"paperId": "p2", "title": "Paper 2"},
    ]
    mock_s2_fetch.side_effect = [
        [{"citingPaper": {"paperId": "cid_1", "title": "C1"}}],
        [{"citingPaper": {"paperId": "cid_2", "title": "C2"}}],
    ]

    publications = [{"bib": {"title": "P1"}}, {"bib": {"title": "P2"}}]

    # Limit to 1, should break after first publication iteration
    citations = collect_citations(publications, "Author", 1, "test_target_id")
    assert len(citations) == 1
    assert citations[0]["citation_id"] == "cid_1"
