"""Phase 5 — Research domain classification of citing papers.

Groups citations by citing paper title, sends batches to the LLM
for domain classification, and stores the result per-citation.
"""

import time
from backend.core.config import logger, extract_json, coerce_llm_list_to_dict, handle_llm_error
from backend.database.sqlite_db import (
    get_all_citations,
    get_target_status,
    update_citation_domain,
    update_target_progress,
    find_shared_domain,
)


def classify_domains(
    client,
    model_name: str,
    eval_criteria: dict,
    target_id: str,
    system_user_id: int | None = None,
) -> None:
    """Classify each citing paper into a research domain via LLM batches."""

    all_citations = get_all_citations(target_id)
    if not all_citations:
        return

    # Group citations by citing paper title (same strategy as Phase 3)
    citing_papers: dict[str, dict] = {}
    for citation in all_citations:
        title = citation["citing_title"]
        if title not in citing_papers:
            citing_papers[title] = {
                "title": title,
                "year": citation.get("year", "Unknown"),
                "venue": citation.get("venue", "Unknown"),
                "citation_ids": [],
                "has_domain": citation.get("research_domain") is not None,
            }
        citing_papers[title]["citation_ids"].append(citation["citation_id"])

        # If any citation for this title already has a domain, mark it
        if citation.get("research_domain") is not None:
            citing_papers[title]["has_domain"] = True

    # ── Cross-target sharing: reuse domains from other targets ──
    shared_count = 0
    for paper in citing_papers.values():
        if paper["has_domain"]:
            continue
        # Check any citation_id for a shared domain
        for cid in paper["citation_ids"]:
            shared_domain = find_shared_domain(cid, target_id)
            if shared_domain:
                for apply_cid in paper["citation_ids"]:
                    update_citation_domain(apply_cid, shared_domain, target_id)
                paper["has_domain"] = True
                shared_count += 1
                logger.info(
                    f"    [DOMAIN-SHARED] '{paper['title'][:40]}...' → {shared_domain}"
                )
                break

    if shared_count:
        logger.info(f"  Phase 5: Reused domains for {shared_count} papers from other targets.")

    # Filter to only papers without a domain assigned
    papers_to_classify = [
        p for p in citing_papers.values() if not p["has_domain"]
    ]

    if not (papers_to_classify and client):
        return

    logger.info(
        f"\nPhase 5: Classifying research domains for {len(papers_to_classify)} distinct citing papers..."
    )
    chunk_size = 30

    inferred_domain = eval_criteria.get("inferred_domain", "")

    for i in range(0, len(papers_to_classify), chunk_size):
        if get_target_status(target_id) in ("paused", "cancelled"):
            logger.info(f"Target {target_id} paused or cancelled. Stopping Phase 5.")
            break

        chunk = papers_to_classify[i : i + chunk_size]
        logger.info(
            f"  Batch {i // chunk_size + 1}/"
            f"{(len(papers_to_classify) - 1) // chunk_size + 1} ({len(chunk)} citing papers)..."
        )

        prompt = (
            "CRITICAL INSTRUCTION: Classify each paper below into its primary research domain/field. "
            "DO NOT hallucinate. Use concise, standardized domain names.\n\n"
        )
        if inferred_domain:
            prompt += f"The target author/paper is in the domain: {inferred_domain}\n\n"
        prompt += (
            "For each paper, provide a concise research domain label such as:\n"
            "  'Computer Vision', 'Natural Language Processing', 'Robotics', 'Machine Learning',\n"
            "  'Computer Graphics', 'Speech Processing', 'Information Retrieval', 'Medical Imaging',\n"
            "  'Reinforcement Learning', 'Software Engineering', etc.\n\n"
            "Provide JSON mapping each Paper Title to:\n"
            "{\n"
            '  "domain": str (concise research domain label)\n'
            "}.\n\n"
        )
        for p in chunk:
            prompt += (
                f"Title: '{p['title']}'\n"
                f"Year: {p['year']}\n"
                f"Venue: {p['venue']}\n\n"
            )

        for attempt in range(4):
            try:
                time.sleep(0.01)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "phase": "phase_5_domain",
                        "temperature": 0.1,
                        "top_p": 0.8,
                        "target_id": target_id,
                        "system_user_id": system_user_id,
                    },
                )

                parsed = extract_json(response.text)
                parsed = coerce_llm_list_to_dict(
                    parsed, key_field="title", value_fields=("domain",)
                )

                # Handle single-element dict that got flattened
                if (
                    isinstance(parsed, dict)
                    and "domain" in parsed
                    and "title" in parsed
                ):
                    parsed = {parsed["title"]: parsed}

                classified_count = 0

                for p in chunk:
                    res_data = parsed.get(p["title"])
                    # Fuzzy match by prefix
                    if not res_data:
                        for key in parsed:
                            if p["title"].lower().startswith(key.lower()[:20]):
                                res_data = parsed[key]
                                break

                    if res_data:
                        try:
                            domain = str(res_data.get("domain", "")).strip()
                            if not domain:
                                continue

                            # Apply domain to ALL citations with this citing title
                            for cid in p["citation_ids"]:
                                update_citation_domain(cid, domain, target_id)

                            logger.info(
                                f"    [DOMAIN] '{p['title'][:40]}...' → {domain}"
                            )
                            classified_count += 1
                        except Exception:
                            pass

                if classified_count == 0 and len(parsed) > 0:
                    logger.warning(
                        f"  WARNING: LLM returned JSON but 0/{len(chunk)} papers matched. "
                        f"LLM keys: {list(parsed.keys())[:3]}..."
                    )
                    if attempt < 3:
                        logger.info("  Retrying batch...")
                        time.sleep(5)
                        continue
                elif len(parsed) == 0:
                    logger.info(
                        f"  Batch returned empty JSON — retrying..."
                    )
                    if attempt < 3:
                        time.sleep(5)
                        continue

                current_batch = i // chunk_size
                total_batches = (len(papers_to_classify) - 1) // chunk_size + 1
                progress = 80 + int(((current_batch + 1) / total_batches) * 20)
                update_target_progress(target_id, "scoring", progress)

                break
            except Exception as e:
                action = handle_llm_error(e, attempt)
                if action == "abort":
                    return
                elif action == "skip":
                    break
