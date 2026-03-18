from backend.core.cost import estimate_pipeline_cost, MODEL_PRICING


def test_cost_estimation_empty():
    estimates = estimate_pipeline_cost([], [], {})
    assert estimates["phase_2"]["input_tokens"] == 0
    assert estimates["phase_2"]["output_tokens"] == 0
    assert estimates["phase_3"]["output_tokens"] == 0
    assert estimates["phase_4"]["output_tokens"] == 0


def test_cost_estimation_authors_only():
    authors = ["Author A", "Author B"]
    criteria = {"notable_criteria": "Must be very notable"}
    estimates = estimate_pipeline_cost(authors, [], criteria)

    assert estimates["phase_2"]["input_tokens"] > 0
    assert estimates["phase_2"]["output_tokens"] > 0
    
    # 1 batch of 100
    assert estimates["phase_2"]["batches"] == 1

    # 2 authors -> at least 2 JSON blocks in output projection
    # 2 * 40 = 80 output tokens
    assert estimates["phase_2"]["output_tokens"] == len(authors) * 40


def test_cost_estimation_citations_only():
    citations = [
        {
            "citation_id": "123",
            "citing_title": "Paper 1",
            "citing_citation_count": 10,
            "cited_title": "Target 1",
            "contexts": ["Context 1"],
        }
    ]
    criteria = {"seminal_criteria": "groundbreaking paper"}
    estimates = estimate_pipeline_cost([], citations, criteria)

    assert estimates["phase_4"]["input_tokens"] > 0
    assert estimates["phase_4"]["output_tokens"] > 0

    assert estimates["phase_3"]["batches"] == 1
    assert estimates["phase_4"]["batches"] == 1

    # 1 citation -> 1 * 130 = 130 output tokens
    assert estimates["phase_4"]["output_tokens"] == len(citations) * 130


def test_cost_estimation_both_and_batching():
    authors = [f"Author {i}" for i in range(150)]  # 150 authors (>100 chunk size)
    citations = [
        {
            "citation_id": f"id_{i}",
            "citing_title": f"Paper XYZ {i}",
            "citing_citation_count": 5,
            "cited_title": "Target ABC",
            "contexts": ["Short context"],
        }
        for i in range(60)  # 60 citations (>50 chunk size)
    ]
    criteria = {"notable_criteria": "notable", "seminal_criteria": "seminal"}

    estimates = estimate_pipeline_cost(authors, citations, criteria)

    assert estimates["phase_2"]["input_tokens"] > 0
    assert estimates["phase_3"]["input_tokens"] > 0
    assert estimates["phase_4"]["input_tokens"] > 0

    # Batches math: 150 authors / 100 = 2 batches
    assert estimates["phase_2"]["batches"] == 2
    # Batches math: 60 unique distinct titles / 30 = 2 batches
    assert estimates["phase_3"]["batches"] == 2
    # Batches math: 60 citations / 50 = 2 batches
    assert estimates["phase_4"]["batches"] == 2

    assert estimates["phase_2"]["output_tokens"] == len(authors) * 40
    assert estimates["phase_4"]["output_tokens"] == len(citations) * 130


def test_pricing_keys_exist():
    assert "gemini-2.5-flash" in MODEL_PRICING
    assert "gemini-2.0-flash" in MODEL_PRICING
    assert "gemini-2.5-pro" in MODEL_PRICING


def test_cost_estimation_massive_inputs():
    """Verify the cost estimation logic handles extremely large lists without errors."""
    authors = [f"Massive Author {i}" for i in range(15000)]
    citations = [
        {
            "citation_id": f"id_{i}",
            "citing_title": f"Citing {i}",
            "cited_title": "Target",
            "contexts": [f"Massive context {i} {j}" for j in range(5)],
        }
        for i in range(5000)
    ]
    estimates = estimate_pipeline_cost(authors, citations, {"domain": "AI"})

    assert estimates["phase_2"]["input_tokens"] > 0
    assert estimates["phase_4"]["input_tokens"] > 0
    assert estimates["phase_2"]["output_tokens"] == 15000 * 40
    assert estimates["phase_4"]["output_tokens"] == 5000 * 130


def test_cost_estimation_partial_or_missing_fields():
    """Verify cost logic is robust against missing data in citation objects."""
    citations = [
        {
            "citation_id": "1",
            "citing_title": "T1",
            "cited_title": "P1",
        },  # Missing contexts entirely
        {
            "citation_id": "2",
            "citing_title": "T2",
            "cited_title": "P2",
            "contexts": [],
        },  # Empty contexts
        {
            "citation_id": "3",
            "citing_title": "T3",
            "cited_title": "P3",
            "contexts": ["valid"],
        },  # Valid
    ]
    estimates = estimate_pipeline_cost([], citations, {"domain": "AI"})

    # 3 citations, so 3 * 130 = 390 expected output tokens
    assert estimates["phase_4"]["output_tokens"] == 390
    assert estimates["phase_4"]["input_tokens"] > 0
