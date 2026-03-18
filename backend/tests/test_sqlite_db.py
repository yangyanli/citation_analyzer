import pytest
import sqlite3
import uuid

from backend.database.sqlite_db import (
    init_db,
    get_db_connection,
    upsert_analysis_target,
    get_analysis_target,
    get_author,
    upsert_author,
    get_cached_s2_paper,
    set_cached_s2_paper,
    insert_citation_if_missing,
    get_all_citations,
    get_unscored_citations,
    update_citation_sentiment_only,
)


def test_init_db_creates_tables():
    """Verify all 4 core tables are created."""
    with get_db_connection() as conn:
        tables = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "analysis_targets" in tables
        assert "authors" in tables
        assert "s2_search_cache" in tables
        assert "citations" in tables


def test_upsert_and_get_analysis_target():
    target_id = "test_target_1"
    target_data = {"mode": "scholar", "name": "Jane Doe"}
    eval_criteria = {"domain": "AI"}

    target_data["evaluation_criteria"] = eval_criteria
    upsert_analysis_target(target_id, target_data)

    result = get_analysis_target(target_id)
    assert result is not None
    assert result["mode"] == "scholar"
    assert result["name"] == "Jane Doe"
    assert result["evaluation_criteria"]["domain"] == "AI"

    # Test update
    eval_criteria_new = {"domain": "Machine Learning"}
    target_data["evaluation_criteria"] = eval_criteria_new
    upsert_analysis_target(target_id, target_data)

    result = get_analysis_target(target_id)
    assert result["evaluation_criteria"]["domain"] == "Machine Learning"


def test_author_cache():
    author_name = f"Test Author {uuid.uuid4()}"
    author_data = {"is_notable": True, "evidence": "Awards"}

    # Should be None initially
    assert get_author(author_name) is None

    # Insert and get
    upsert_author(author_name, author_data["is_notable"], author_data["evidence"])
    result = get_author(author_name)
    assert result is not None
    assert result["is_notable"] == 1
    assert result["evidence"] == "Awards"


def test_s2_search_cache():
    title = f"Test Paper Title {uuid.uuid4()}"
    s2_data = {"paperId": "abcdef", "citationCount": 42}

    # Should be None initially
    assert get_cached_s2_paper(title) is None

    # Insert and get
    set_cached_s2_paper(title, s2_data)
    result = get_cached_s2_paper(title)

    assert result is not None
    assert result["title"] == title
    assert result["paperId"] == "abcdef"
    assert result["citationCount"] == 42


def test_citation_operations():
    target_id = f"test_target_{uuid.uuid4()}"

    # 1. Insert a citation
    citation_id = f"cid_{uuid.uuid4()}"
    citation_data = {
        "citation_id": citation_id,
        "citing_title": "Citing Paper A",
        "year": 2024,
        "authors": [{"name": "Author X"}],
        "contexts": ["Context string A"],
        "cited_title": "Cited Paper Title",
        "target_id": target_id,
    }

    # Needs a parent target_id to satisfy FK constraint
    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Target"})

    # 2. Retrieve all citations
    initial_all_citations = get_all_citations(target_id)
    initial_len = len(initial_all_citations)

    insert_citation_if_missing(citation_id, citation_data)

    all_citations = get_all_citations(target_id)
    assert len(all_citations) == initial_len + 1

    # 3. Retrieve unscored citations
    unscored = get_unscored_citations(target_id)

    # Verify our specific cid exists in the unscored list
    assert any(c["citation_id"] == citation_id for c in unscored)

    # 4. Update the score
    update_data = {
        "score": 9,
        "positive_comment": "Great paper",
        "sentiment_evidence": "Quote A",
        "is_seminal": True,
        "usage_classification": "Extending / Using",
    }
    update_citation_sentiment_only(citation_id, update_data, version="test")

    # 5. Verify the score was updated and it's no longer 'unscored'
    unscored_after = get_unscored_citations(target_id)
    assert not any(c["citation_id"] == citation_id for c in unscored_after)

    all_citations_after = get_all_citations(target_id)
    updated_citation = next(
        c for c in all_citations_after if c["citation_id"] == citation_id
    )
    assert updated_citation["score"] == 9
    assert updated_citation["usage_classification"] == "Extending / Using"


def test_concurrent_connection_handling():
    """Simulate concurrent-like multiple writes to verify WAL mode durability."""
    target_id = f"concurrent_target_{uuid.uuid4()}"
    # Threading isn't strictly necessary for sqlite3 with WAL if we just rapidly open connections
    initial_all_c = get_all_citations(target_id)
    initial_c_len = len(initial_all_c)

    # Needs a parent target_id to satisfy FK constraint
    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Target"})

    for i in range(100):
        val = {
            "citation_id": f"cid_{target_id}_{i}",
            "target_id": target_id,
            "citing_title": f"T_{i}",
            "cited_title": "Target",
            "year": 2024,
        }
        insert_citation_if_missing(f"cid_{target_id}_{i}", val)

    all_c = get_all_citations(target_id)
    assert len(all_c) == initial_c_len + 100


def test_deep_nested_transactions_rollback():
    """Verify that a manual failed operation doesn't corrupt the DB state."""
    target_id = "rollback_test"
    with get_db_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO analysis_targets (target_id, mode) VALUES (?, ?)",
            (target_id, "scholar"),
        )
        conn.commit()

    citations_before = get_all_citations(target_id)

    try:
        with get_db_connection() as conn:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "INSERT INTO citations (citation_id, target_id, citing_title) VALUES (?, ?, ?)",
                ("bad_cid", target_id, "Before Rollback"),
            )
            # Force integrity error
            conn.execute(
                "INSERT INTO citations (citation_id, target_id) VALUES (NULL, NULL)"
            )
    except sqlite3.InterfaceError:
        pass
    except sqlite3.IntegrityError:
        pass

    # The transaction should have rolled back
    citations_after = get_all_citations(target_id)
    assert len(citations_after) == len(citations_before)


def test_data_integrity_large_scale():
    """Test inserting 5000 citations to verify batch speed and integrity."""
    target_id = f"massive_target_{uuid.uuid4()}"
    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Big Data Guy"})

    citations_to_insert = []
    for i in range(5000):
        citations_to_insert.append(
            {
                "citation_id": f"mass_cid_{target_id}_{i}",
                "target_id": target_id,
                "citing_title": f"Massive Title {i}",
                "year": 2020 + (i % 5),
                "authors": [{"name": f"Author_{i}"}],
                "contexts": [f"This is context {i}"],
                "cited_title": "Target",
            }
        )

    initial_all_c2 = get_all_citations(target_id)
    initial_c2_len = len(initial_all_c2)

    for c in citations_to_insert:
        insert_citation_if_missing(c["citation_id"], c)

    all_c = get_all_citations(target_id)
    assert len(all_c) == initial_c2_len + 5000

def test_wipe_phase_data():
    from backend.database.sqlite_db import wipe_phase_data
    target_id = f"wipe_target_{uuid.uuid4()}"
    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Wipe Guy"})

    citation_id = f"cid_{uuid.uuid4()}"
    citation_data = {
        "citation_id": citation_id,
        "citing_title": "Citing Paper A",
        "year": 2024,
        "authors": [{"name": "Author X"}],
        "contexts": ["Context string A"],
        "cited_title": "Cited Paper Title",
        "target_id": target_id,
    }
    insert_citation_if_missing(citation_id, citation_data)

    # Phase 2
    from backend.database.sqlite_db import update_citation_authors
    update_citation_authors(citation_id, '["Author X"]')

    # Phase 3 & 4
    update_data = {
        "score": 9,
        "positive_comment": "Great paper",
        "sentiment_evidence": "Quote A",
        "is_seminal": True,
        "usage_classification": "Extending / Using",
    }
    update_citation_sentiment_only(citation_id, update_data, version="test")

    # Wipe Phase 4
    wipe_phase_data(target_id, 4)
    c_after_p4 = get_all_citations(target_id)[0]
    assert c_after_p4["score"] is None
    assert c_after_p4["usage_classification"] == "Pending"
    assert c_after_p4["positive_comment"] is None

    # Wipe Phase 3
    wipe_phase_data(target_id, 3)
    c_after_p3 = get_all_citations(target_id)[0]
    assert c_after_p3["is_seminal"] == 0
    assert c_after_p3["seminal_evidence"] is None

    # Wipe Phase 2
    wipe_phase_data(target_id, 2)
    c_after_p2 = get_all_citations(target_id)[0]
    assert not c_after_p2["notable_authors"]

    # Trying to wipe Phase 1 should fail
    with pytest.raises(ValueError, match="Only phases 2, 3, 4, and 5 can be wiped safely."):
        wipe_phase_data(target_id, 1)


def test_wipe_phase_5_data():
    """Test wiping Phase 5 research domain data."""
    from backend.database.sqlite_db import wipe_phase_data, update_citation_domain
    target_id = f"wipe5_target_{uuid.uuid4()}"
    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Wipe5 Guy"})

    citation_id = f"cid_{uuid.uuid4()}"
    citation_data = {
        "citation_id": citation_id,
        "citing_title": "Citing Paper B",
        "year": 2024,
        "authors": [],
        "contexts": [],
        "cited_title": "Cited Paper Title",
        "target_id": target_id,
    }
    insert_citation_if_missing(citation_id, citation_data)

    # Assign a domain
    update_citation_domain(citation_id, "Computer Vision")
    c = get_all_citations(target_id)[0]
    assert c["research_domain"] == "Computer Vision"

    # Wipe Phase 5
    wipe_phase_data(target_id, 5)
    c_after = get_all_citations(target_id)[0]
    assert c_after["research_domain"] is None


def test_update_citation_domain():
    """Test update_citation_domain assigns domain correctly."""
    from backend.database.sqlite_db import update_citation_domain
    target_id = f"domain_target_{uuid.uuid4()}"
    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Domain Guy"})

    citation_id = f"cid_{uuid.uuid4()}"
    insert_citation_if_missing(citation_id, {
        "citation_id": citation_id,
        "citing_title": "Test Paper",
        "year": 2024,
        "authors": [],
        "contexts": [],
        "cited_title": "Target",
        "target_id": target_id,
    })

    update_citation_domain(citation_id, "Natural Language Processing")
    c = get_all_citations(target_id)[0]
    assert c["research_domain"] == "Natural Language Processing"


def test_get_unclassified_citations():
    """Test get_unclassified_citations returns only citations without a domain."""
    from backend.database.sqlite_db import get_unclassified_citations, update_citation_domain
    target_id = f"unclass_target_{uuid.uuid4()}"
    upsert_analysis_target(target_id, {"mode": "scholar", "name": "Unclass Guy"})

    cid_1 = f"cid_{uuid.uuid4()}"
    cid_2 = f"cid_{uuid.uuid4()}"
    for cid in (cid_1, cid_2):
        insert_citation_if_missing(cid, {
            "citation_id": cid,
            "citing_title": f"Paper {cid}",
            "year": 2024,
            "authors": [],
            "contexts": [],
            "cited_title": "Target",
            "target_id": target_id,
        })

    # Both should be unclassified
    unclassified = get_unclassified_citations(target_id)
    assert len(unclassified) == 2

    # Classify one
    update_citation_domain(cid_1, "Robotics")

    unclassified = get_unclassified_citations(target_id)
    assert len(unclassified) == 1
    assert unclassified[0]["citation_id"] == cid_2


def test_same_citation_different_targets():
    """Verify the same citing paper (citation_id) can exist independently under multiple targets."""
    from backend.database.sqlite_db import update_citation_domain, get_citation

    target_a = f"target_A_{uuid.uuid4()}"
    target_b = f"target_B_{uuid.uuid4()}"
    shared_cid = f"shared_cid_{uuid.uuid4()}"

    upsert_analysis_target(target_a, {"mode": "scholar", "name": "Researcher A"})
    upsert_analysis_target(target_b, {"mode": "scholar", "name": "Researcher B"})

    # Insert the same citation_id for both targets — this should NOT raise IntegrityError
    data_a = {
        "citation_id": shared_cid,
        "citing_title": "Shared Citing Paper",
        "cited_title": "Paper by A",
        "target_id": target_a,
        "year": 2024,
        "authors": [],
        "contexts": ["Context for A"],
    }
    data_b = {
        "citation_id": shared_cid,
        "citing_title": "Shared Citing Paper",
        "cited_title": "Paper by B",
        "target_id": target_b,
        "year": 2024,
        "authors": [],
        "contexts": ["Context for B"],
    }

    assert insert_citation_if_missing(shared_cid, data_a) is True
    assert insert_citation_if_missing(shared_cid, data_b) is True

    # Each target sees exactly 1 citation
    assert len(get_all_citations(target_a)) == 1
    assert len(get_all_citations(target_b)) == 1

    # Cited papers are independent
    assert get_all_citations(target_a)[0]["cited_title"] == "Paper by A"
    assert get_all_citations(target_b)[0]["cited_title"] == "Paper by B"

    # Updates are scoped to the correct target
    update_citation_domain(shared_cid, "Computer Vision", target_a)
    assert get_citation(shared_cid, target_a)["research_domain"] == "Computer Vision"
    assert get_citation(shared_cid, target_b)["research_domain"] is None

    # Scoring one doesn't affect the other
    update_citation_sentiment_only(
        shared_cid,
        {"score": 9, "positive_comment": "Great!", "usage_classification": "Extending / Using"},
        "test",
        target_a,
    )
    assert get_citation(shared_cid, target_a)["score"] == 9
    assert get_citation(shared_cid, target_b)["score"] is None

# ── Cross-target sharing tests ───────────────────────────────────────


def test_cross_target_domain_sharing():
    """find_shared_domain returns domain from another target, None for self."""
    from backend.database.sqlite_db import (
        update_citation_domain,
        find_shared_domain,
    )

    target_a = f"target_A_{uuid.uuid4()}"
    target_b = f"target_B_{uuid.uuid4()}"
    shared_cid = f"shared_cid_{uuid.uuid4()}"

    upsert_analysis_target(target_a, {"mode": "scholar", "name": "A"})
    upsert_analysis_target(target_b, {"mode": "scholar", "name": "B"})

    for tid in (target_a, target_b):
        insert_citation_if_missing(shared_cid, {
            "citation_id": shared_cid,
            "citing_title": "Shared Paper",
            "cited_title": "Target",
            "target_id": tid,
            "year": 2024,
            "authors": [],
            "contexts": [],
        })

    # No domain yet → None
    assert find_shared_domain(shared_cid, target_b) is None

    # Set domain on target_a
    update_citation_domain(shared_cid, "Computer Vision", target_a)

    # target_b can now see the shared domain
    assert find_shared_domain(shared_cid, target_b) == "Computer Vision"
    # target_a should NOT see its own data as "shared"
    assert find_shared_domain(shared_cid, target_a) is None


def test_cross_target_sentiment_sharing():
    """find_shared_sentiment matches on (citation_id, cited_paper_id)."""
    from backend.database.sqlite_db import find_shared_sentiment

    target_a = f"target_A_{uuid.uuid4()}"
    target_b = f"target_B_{uuid.uuid4()}"
    shared_cid = f"shared_cid_{uuid.uuid4()}"
    same_paper_id = "s2_paper_XYZ"

    upsert_analysis_target(target_a, {"mode": "scholar", "name": "A"})
    upsert_analysis_target(target_b, {"mode": "scholar", "name": "B"})

    # Both targets cite the SAME paper
    for tid in (target_a, target_b):
        insert_citation_if_missing(shared_cid, {
            "citation_id": shared_cid,
            "citing_title": "Shared Paper",
            "cited_title": "Co-authored Paper",
            "cited_paper_id": same_paper_id,
            "target_id": tid,
            "year": 2024,
            "authors": [],
            "contexts": ["Great work"],
        })

    # Score target_a
    update_citation_sentiment_only(
        shared_cid,
        {"score": 8, "positive_comment": "Nice!", "usage_classification": "Extending / Using"},
        "v1",
        target_a,
    )

    # target_b can reuse the sentiment
    shared = find_shared_sentiment(shared_cid, same_paper_id, target_b)
    assert shared is not None
    assert shared["score"] == 8
    assert shared["usage_classification"] == "Extending / Using"

    # Different cited_paper_id should NOT match
    assert find_shared_sentiment(shared_cid, "different_paper", target_b) is None


def test_cross_target_venue_sharing():
    """find_shared_venue_authors returns resolved venue/authors from another target."""
    from backend.database.sqlite_db import find_shared_venue_authors, get_db_connection
    import json

    target_a = f"target_A_{uuid.uuid4()}"
    target_b = f"target_B_{uuid.uuid4()}"
    shared_cid = f"shared_cid_{uuid.uuid4()}"

    upsert_analysis_target(target_a, {"mode": "scholar", "name": "A"})
    upsert_analysis_target(target_b, {"mode": "scholar", "name": "B"})

    authors_json = json.dumps([{"name": "Author X"}])
    for tid in (target_a, target_b):
        insert_citation_if_missing(shared_cid, {
            "citation_id": shared_cid,
            "citing_title": "ArXiv Paper",
            "cited_title": "Target",
            "target_id": tid,
            "year": 2024,
            "authors": [],
            "contexts": [],
        })

    # Both start with no resolved venue → None
    assert find_shared_venue_authors(shared_cid, target_b) is None

    # Resolve target_a's venue
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE citations SET venue = ?, authors = ? WHERE citation_id = ? AND target_id = ?",
            ("CVPR", authors_json, shared_cid, target_a),
        )

    # target_b can now reuse the venue/authors
    shared = find_shared_venue_authors(shared_cid, target_b)
    assert shared is not None
    assert shared["venue"] == "CVPR"
    assert "Author X" in shared["authors"]


def test_sharing_respects_age_limit():
    """Sharing returns None when data is older than max_age_days."""
    from backend.database.sqlite_db import (
        update_citation_domain,
        find_shared_domain,
        get_db_connection,
    )

    target_a = f"target_A_{uuid.uuid4()}"
    target_b = f"target_B_{uuid.uuid4()}"
    shared_cid = f"shared_cid_{uuid.uuid4()}"

    upsert_analysis_target(target_a, {"mode": "scholar", "name": "A"})
    upsert_analysis_target(target_b, {"mode": "scholar", "name": "B"})

    for tid in (target_a, target_b):
        insert_citation_if_missing(shared_cid, {
            "citation_id": shared_cid,
            "citing_title": "Old Paper",
            "cited_title": "Target",
            "target_id": tid,
            "year": 2024,
            "authors": [],
            "contexts": [],
        })

    update_citation_domain(shared_cid, "Robotics", target_a)

    # Artificially age target_a's data to 60 days ago
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE citations SET created_at = datetime('now', '-60 days') WHERE citation_id = ? AND target_id = ?",
            (shared_cid, target_a),
        )

    # Default 30-day limit → should NOT find it
    assert find_shared_domain(shared_cid, target_b) is None

    # Explicitly allow 90 days → should find it
    assert find_shared_domain(shared_cid, target_b, max_age_days=90) == "Robotics"
