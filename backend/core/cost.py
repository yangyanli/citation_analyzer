"""Cost estimation and token counting utilities."""

# Model pricing per million tokens: (input_cost, output_cost)
MODEL_PRICING = {
    "gemini-2.0-flash-lite": (0.075, 0.30),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.5-pro": (1.25, 10.00),
}

# Trackers for fallback mode token savings
FALLBACK_SAVED_USD = 0.0


def compute_phase_costs(estimates: dict, model: str) -> dict[int, dict]:
    """Compute per-phase batch counts and costs from token estimates.

    Returns ``{2: {"batches": N, "cost": $}, 3: {...}, 4: {...}}``.
    """
    in_cost, out_cost = MODEL_PRICING.get(model, MODEL_PRICING["gemini-2.5-flash"])
    result = {}
    for phase_num in (2, 3, 4, 5):
        phase_key = f"phase_{phase_num}"
        est_in = estimates[phase_key]["input_tokens"]
        est_out = estimates[phase_key]["output_tokens"]
        result[phase_num] = {
            "batches": estimates[phase_key]["batches"],
            "cost": (est_in / 1_000_000) * in_cost + (est_out / 1_000_000) * out_cost,
        }
    return result


def estimate_pipeline_cost(
    unknown_authors: list[str],
    uncached_citations: list[dict],
    eval_criteria: dict,
) -> dict[str, dict[str, int]]:
    """Return estimated specs per phase (batches, input_tokens, output_tokens)."""
    from backend.api.llm import get_llm_client

    client = get_llm_client()

    estimates = {
        "phase_2": {"batches": 0, "input_tokens": 0, "output_tokens": 0},
        "phase_3": {"batches": 0, "input_tokens": 0, "output_tokens": 0},
        "phase_4": {"batches": 0, "input_tokens": 0, "output_tokens": 0},
        "phase_5": {"batches": 0, "input_tokens": 0, "output_tokens": 0},
    }

    # Author phase (Phase 2) estimate
    estimates["phase_2"]["batches"] = (len(unknown_authors) + 99) // 100
    for i in range(0, len(unknown_authors), 100):
        chunk = unknown_authors[i : i + 100]
        prompt = (
            f"Criteria: {eval_criteria.get('notable_criteria')}\n"
            'For each author below, respond with JSON: {"name": {"is_notable": bool, "evidence": str, "homepage": str, "verification_keywords": [], "verification_url": str}}.\n'
            "Authors:\n" + "\n".join(f"- {a}" for a in chunk)
        )
        if client:
            try:
                estimates["phase_2"]["input_tokens"] += client.models.count_tokens(
                    model="gemini-2.5-flash", contents=prompt
                ).total_tokens
            except Exception:
                estimates["phase_2"]["input_tokens"] += len(prompt) // 4
        else:
            estimates["phase_2"]["input_tokens"] += len(prompt) // 4

        # JSON output per author is approx 40 tokens on average
        estimates["phase_2"]["output_tokens"] += len(chunk) * 40

    # Seminal phase (Phase 3) estimate
    # We need distinct citing papers first
    distinct_papers = list({c["citing_title"] for c in uncached_citations})
    estimates["phase_3"]["batches"] = (len(distinct_papers) + 29) // 30
    for i in range(0, len(distinct_papers), 30):
        chunk = distinct_papers[i : i + 30]
        prompt = (
            "CRITICAL INSTRUCTION: Analyze the publication records below carefully.\n\n"
            f"Seminal Criteria: {eval_criteria.get('seminal_criteria')}\n\n"
        )
        for p in chunk:
            prompt += f"Title: '{p}'\nTotal Citations: 99\n\n" # Mock for token counting

        if client:
            try:
                estimates["phase_3"]["input_tokens"] += client.models.count_tokens(
                    model="gemini-2.5-flash", contents=prompt
                ).total_tokens
            except Exception:
                estimates["phase_3"]["input_tokens"] += len(prompt) // 4
        else:
            estimates["phase_3"]["input_tokens"] += len(prompt) // 4
        
        # Output is only for seminal ones, but let's assume 10% match + 40 tokens each
        estimates["phase_3"]["output_tokens"] += max(1, len(chunk) // 10) * 40

    # Sentiment phase (Phase 4) estimate
    estimates["phase_4"]["batches"] = (len(uncached_citations) + 49) // 50
    for i in range(0, len(uncached_citations), 50):
        chunk = uncached_citations[i : i + 50]
        prompt = (
            "CRITICAL INSTRUCTION: Analyze the citations below carefully.\n\n"
            "For each citation below, provide JSON mapping ID to:\n"
            '{"score": 1-10, "positive_comment": "...", "sentiment_evidence": "...", '
            f'"is_seminal": bool ({eval_criteria.get("seminal_criteria")}), '
            '"seminal_evidence": str, "paper_homepage": str, '
            '"usage_classification": "Discussing"|"Experimental Comparison"|"Extending / Using"}.\n\n'
        )
        for c in chunk:
            contexts_str = " ".join(c.get("contexts", []))
            prompt += (
                f"ID: {c['citation_id']}\n"
                f"Citing Paper: '{c['citing_title']}' (Citations: {c.get('citing_citation_count', 0)})\n"
                f"Cited Paper: '{c['cited_title']}'\n"
                f"Ctx: {contexts_str}\n\n"
            )

        if client:
            try:
                estimates["phase_4"]["input_tokens"] += client.models.count_tokens(
                    model="gemini-2.5-flash", contents=prompt
                ).total_tokens
            except Exception:
                estimates["phase_4"]["input_tokens"] += len(prompt) // 4
        else:
            estimates["phase_4"]["input_tokens"] += len(prompt) // 4

        # JSON output per citation is approx 130 tokens
        estimates["phase_4"]["output_tokens"] += len(chunk) * 130

    # Domains phase (Phase 5) estimate
    estimates["phase_5"]["batches"] = (len(uncached_citations) + 59) // 60
    for i in range(0, len(uncached_citations), 60):
        chunk = uncached_citations[i : i + 60]
        prompt = (
            "CRITICAL INSTRUCTION: Analyze the citations below carefully.\n\n"
            "For each citation below, classify its research domain.\n\n"
        )
        for c in chunk:
            contexts_str = " ".join(c.get("contexts", []))
            prompt += (
                f"ID: {c['citation_id']}\n"
                f"Citing Paper: '{c['citing_title']}'\n"
                f"Ctx: {contexts_str}\n\n"
            )

        if client:
            try:
                estimates["phase_5"]["input_tokens"] += client.models.count_tokens(
                    model="gemini-2.5-flash", contents=prompt
                ).total_tokens
            except Exception:
                estimates["phase_5"]["input_tokens"] += len(prompt) // 4
        else:
            estimates["phase_5"]["input_tokens"] += len(prompt) // 4

        # JSON output per citation is approx 20 tokens
        estimates["phase_5"]["output_tokens"] += len(chunk) * 20

    return estimates


def print_cost_table(
    unknown_authors: list[str],
    uncached_citations: list[dict],
    estimates: dict[str, dict[str, int]],
) -> None:
    """Print the cost estimation table."""
    total_input = sum(e["input_tokens"] for e in estimates.values())
    total_output = sum(e["output_tokens"] for e in estimates.values())
    
    print("\n--- ESTIMATED USAGE ---")
    print(
        f"Phase 2: Extracting {len(unknown_authors)} missing author profiles in {estimates['phase_2']['batches']} batches"
    )
    print(
        f"Phase 3: Discovering seminal works among {len({c['citing_title'] for c in uncached_citations})} citing papers in {estimates['phase_3']['batches']} batches"
    )
    print(
        f"Phase 4: Classifying {len(uncached_citations)} un-cached citations in {estimates['phase_4']['batches']} batches"
    )
    print(
        f"Phase 5: Domain classification for {len(uncached_citations)} citations in {estimates['phase_5']['batches']} batches"
    )
    print(f"Estimated Tokens: ~{total_input:,} Input / ~{total_output:,} Output")
    print(
        f"\n{'Model':<25} {'Input $/1M':>10} {'Output $/1M':>12} {'Est. Cost':>10} {'Extrapolated 10k Cost':>22}"
    )
    print(f"{'-' * 25} {'-' * 10} {'-' * 12} {'-' * 10} {'-' * 22}")

    # Calculate multiplier for 10k extrapolation based on the citations in this batch
    multiplier = 0
    if len(uncached_citations) > 0:
        multiplier = 10000 / len(uncached_citations)

    for model_id, (in_cost, out_cost) in MODEL_PRICING.items():
        est = (total_input / 1_000_000) * in_cost + (
            total_output / 1_000_000
        ) * out_cost

        extrapolated_str = "N/A"
        if multiplier > 0:
            extrapolated_str = f"${est * multiplier:>7.2f}"

        marker = " ← default" if model_id == "gemini-2.5-flash" else ""
        print(
            f"{model_id:<25} ${in_cost:>8.3f}  ${out_cost:>10.2f}  ${est:>8.5f} {extrapolated_str:>21}{marker}"
        )


def increment_fallback_savings(
    model: str, input_tokens: int, output_tokens: int
) -> None:
    """Add cost to the global fallback savings tracker based on exact model pricing."""
    global FALLBACK_SAVED_USD

    in_cost, out_cost = MODEL_PRICING.get(model, (0.0, 0.0))
    cost = (input_tokens / 1_000_000) * in_cost + (output_tokens / 1_000_000) * out_cost
    FALLBACK_SAVED_USD += cost


def print_fallback_savings_summary() -> None:
    """Print the total estimated cost savings from using fallback mode."""
    if FALLBACK_SAVED_USD <= 0:
        return

    print("\n--- FALLBACK LLM MODE SAVINGS SUMMARY ---")
    print(f"Total Estimated Savings: ${FALLBACK_SAVED_USD:,.4f} USD")
    print("-----------------------------------------\n")
