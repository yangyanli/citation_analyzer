"""Phase 3 \u2014 Seminal-discovery classification based on cited papers.

Evaluates the CITED papers intrinsically (by grouping their citations)
against the target's seminal_criteria.
"""

import time
from backend.core.config import logger, extract_json, coerce_llm_list_to_dict, handle_llm_error
from backend.database.sqlite_db import get_all_citations, get_target_status


def evaluate_seminal_works(
    client,
    model_name: str,
    eval_criteria: dict,
    target_id: str,
    system_user_id: int | None = None,
) -> None:
    """Group citations by citing paper and query the LLM for seminal status."""

    # 1. Fetch all citations for this target to group by citing paper
    all_citations = get_all_citations(target_id)
    if not all_citations:
        return

    # Group papers: keyed by citing_title.
    citing_papers = {}
    for citation in all_citations:
        title = citation["citing_title"]
        if title not in citing_papers:
            citing_papers[title] = {
                "title": title,
                "year": citation.get("year", "Unknown"),
                "venue": citation.get("venue", "Unknown"),
                "total_citations": citation.get("citing_citation_count", 0),
                "citation_ids": [],
            }
        citing_papers[title]["citation_ids"].append(citation["citation_id"])

        # Keep the max known citation count if there were discrepancies
        if (
            citation.get("citing_citation_count", 0)
            > citing_papers[title]["total_citations"]
        ):
            citing_papers[title]["total_citations"] = citation.get(
                "citing_citation_count", 0
            )

    # Filter out papers that have already been evaluated if we implement caching later,
    # but for now we evaluate all distinct citing papers. Let's filter to just the distinct titles.
    papers_to_evaluate = list(citing_papers.values())

    if not (papers_to_evaluate and client):
        return

    logger.info(
        f"\nPhase 3: Querying Gemini for seminal status of {len(papers_to_evaluate)} distinct citing papers..."
    )
    chunk_size = 30

    from backend.database.sqlite_db import update_citation_seminal, update_target_progress

    for i in range(0, len(papers_to_evaluate), chunk_size):
        if get_target_status(target_id) in ("paused", "cancelled"):
            logger.info(f"Target {target_id} paused or cancelled. Stopping Phase 3.")
            break

        chunk = papers_to_evaluate[i : i + chunk_size]
        logger.info(
            f"  Batch {i // chunk_size + 1}/"
            f"{(len(papers_to_evaluate) - 1) // chunk_size + 1} ({len(chunk)} citing papers)..."
        )

        prompt = (
            "CRITICAL INSTRUCTION: Analyze the publication records below carefully. "
            "DO NOT hallucinate. Provide EXACT, FACTUAL assessments.\n\n"
            f"Seminal Criteria: {eval_criteria.get('seminal_criteria')}\n\n"
            "For each citing paper below, evaluate if it intrinsically qualifies as a seminal discovery "
            "based purely on its title, venue, and total citation count according to the criteria above. "
            "A seminal paper must be a highly impactful or foundational work, not just any cited paper.\n\n"
            "To save tokens, ONLY include papers in your JSON response if they ARE seminal. Omit all other papers.\n\n"
            "Provide JSON mapping the Paper Title to:\n"
            "{\n"
            '  "is_seminal": true,\n'
            '  "seminal_evidence": str (1-sentence explanation of WHY the paper meets the criteria based on its venue/citations)\n'
            "}.\n\n"
        )
        for p in chunk:
            prompt += (
                f"Title: '{p['title']}'\n"
                f"Year: {p['year']}\n"
                f"Venue: {p['venue']}\n"
                f"Total Citations: {p['total_citations']}\n\n"
            )

        for attempt in range(4):
            try:
                time.sleep(0.01)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    # NOTE: Since google.genai validates config via Pydantic, we cannot pass custom kwargs here.
                    config={"phase": "phase_3_seminal", "temperature": 0.1, "top_p": 0.8, "target_id": target_id, "system_user_id": system_user_id},
                )

                parsed = extract_json(response.text)
                parsed = coerce_llm_list_to_dict(parsed, key_field="title", value_fields=("is_seminal", "seminal_evidence"))

                if (
                    isinstance(parsed, dict)
                    and "is_seminal" in parsed
                    and "title" in parsed
                ):
                    parsed = {parsed["title"]: parsed}

                scored_count = 0

                for p in chunk:
                    res_data = parsed.get(p["title"])
                    # Fuzzy match
                    if not res_data:
                        for key in parsed:
                            if p["title"].lower().startswith(key.lower()[:20]):
                                res_data = parsed[key]
                                break

                    if res_data:
                        try:
                            is_seminal = bool(res_data.get("is_seminal", False))
                            seminal_evidence = str(
                                res_data.get("seminal_evidence", "")
                            )

                            # Apply this status to ALL citations that reference this paper
                            for cid in p["citation_ids"]:
                                update_citation_seminal(cid, is_seminal, seminal_evidence, target_id)

                            if is_seminal:
                                logger.info(
                                    f"    [SEMINAL DISCOVERY] '{p['title'][:40]}...' ({p['total_citations']} citations)"
                                )
                            scored_count += 1
                        except Exception:
                            pass

                if scored_count == 0 and len(parsed) > 0:
                    # The LLM returned keys but they didn't match our chunk titles.
                    logger.warning(
                        f"  WARNING: LLM returned JSON but 0/{len(chunk)} papers matched. "
                        f"LLM keys: {list(parsed.keys())[:3]}..."
                    )
                    if attempt < 3:
                        logger.info("  Retrying batch...")
                        time.sleep(5)
                        continue
                elif len(parsed) == 0:
                     logger.info(f"  Batch processed correctly but 0 seminal papers identified natively.")
                
                current_batch = i // chunk_size
                total_batches = (len(papers_to_evaluate) - 1) // chunk_size + 1
                progress = 50 + int(((current_batch + 1) / total_batches) * 20)
                update_target_progress(target_id, "scoring", progress)

                break
            except Exception as e:
                action = handle_llm_error(e, attempt)
                if action == "abort":
                    return
                elif action == "skip":
                    break
