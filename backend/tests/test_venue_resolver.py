import pytest
from unittest.mock import patch
from backend.api.semantic_scholar import resolve_arxiv_venue
from backend.api.venue_resolver import batch_resolve_arxiv_venues
from backend.database.sqlite_db import get_db_connection, init_db
import json

def test_resolve_arxiv_venue_journal():
    paper = {
        "venue": "ArXiv",
        "journal": {"name": "CVPR 2024"}
    }
    assert resolve_arxiv_venue(paper) == "CVPR 2024"

def test_resolve_arxiv_venue_publication_venue():
    paper = {
        "venue": "arxiv.org",
        "publicationVenue": {"name": "ICCV 2023"}
    }
    assert resolve_arxiv_venue(paper) == "ICCV 2023"

def test_resolve_arxiv_venue_still_arxiv():
    paper = {
        "venue": "ArXiv",
        "journal": {"name": "arXiv preprint"}
    }
    assert resolve_arxiv_venue(paper) == "ArXiv"

def test_resolve_arxiv_venue_no_enrichment():
    paper = {
        "venue": "ArXiv"
    }
    assert resolve_arxiv_venue(paper) == "ArXiv"

@patch("backend.api.venue_resolver.batch_fetch_paper_details")
@patch("backend.api.venue_resolver.update_target_progress")
def test_batch_resolve_arxiv_venues(mock_update_progress, mock_fetch):
    # Setup database with a dummy target
    target_id = "test_target"
    with get_db_connection() as conn:
        conn.execute("INSERT INTO analysis_targets (target_id, name, mode) VALUES (?, ?, ?)", (target_id, "Test", "scholar"))
        
        # Insert citations: 1 needs venue update, 1 needs author update
        conn.execute(
            """INSERT INTO citations 
               (citation_id, target_id, citing_title, cited_title, venue, authors) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("cit1", target_id, "Paper 1", "Target", "ArXiv", "[]") # Needs both
        )
        conn.execute(
            """INSERT INTO citations 
               (citation_id, target_id, citing_title, cited_title, venue, authors) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("cit2", target_id, "Paper 2", "Target", "Valid Venue", "") # Needs authors
        )
        conn.execute(
            """INSERT INTO citations 
               (citation_id, target_id, citing_title, cited_title, venue, authors) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("cit3", target_id, "Paper 3", "Target", "CVPR", '[{"name": "Valid Author"}]') # Does not need update
        )
        conn.commit()
    
    # Mock the S2 response
    mock_fetch.return_value = [
        {
            "paperId": "p1",
            "title": "Paper 1",
            "journal": {"name": "SIGGRAPH"},
            "authors": [{"name": "Author One"}, {"name": "Author Two"}]
        },
        {
            "paperId": "p2",
            "title": "Paper 2",
            "journal": {"name": "Valid Venue"},
            "authors": [{"name": "Author Three"}]
        }
    ]

    # Execute
    batch_resolve_arxiv_venues(target_id)
    
    # Verify the database was updated
    with get_db_connection() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        rows = conn.execute("SELECT citation_id, venue, authors FROM citations").fetchall()
        
        cit1 = next(r for r in rows if r["citation_id"] == "cit1")
        assert cit1["venue"] == "SIGGRAPH"
        authors1 = json.loads(cit1["authors"])
        assert len(authors1) == 2
        assert authors1[0]["name"] == "Author One"
        
        cit2 = next(r for r in rows if r["citation_id"] == "cit2")
        assert cit2["venue"] == "Valid Venue"
        authors2 = json.loads(cit2["authors"])
        assert len(authors2) == 1
        assert authors2[0]["name"] == "Author Three"
        
    # Verify progress was updated
    assert mock_update_progress.call_count >= 2 # 5% and 100%
