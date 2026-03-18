"""Phase 4 — Sentiment scoring and usage classification.

Sends citation contexts to the LLM in batches, parses the structured
JSON response, and caches per-citation scores, evidence quotes, and
usage classifications.
"""

import json
import re
import time


from backend.core.config import logger, VERSION, url_looks_valid, extract_json, handle_llm_error
from backend.api.base import CitationScorer
from backend.database.sqlite_db import (
    get_unscored_citations,
    update_citation_sentiment_only,
    find_shared_sentiment,
)


class GeminiScorer(CitationScorer):
    """Implementation of CitationScorer using Google Gemini."""

    def __init__(self, client, model_name: str):
        self.client = client
        self.model_name = model_name

    def score_citation(self, citation_data: dict, criteria: dict) -> dict:
        """Note: This implementation is batch-oriented for efficiency,
        so we still use the legacy score_citations for now but this class
        provides the interface for future single-citation or alternative scoring.
        """
        # Placeholder for future single-scoring logic
        return {}


def score_citations(
    client,
    model_name: str,
    eval_criteria: dict,
    target_id: str,
    scorer: GeminiScorer | None = None,
    system_user_id: int | None = None,
) -> None:
    """Score citation sentiment and usage classification via the LLM."""

    if scorer is None:
        scorer = GeminiScorer(client, model_name)

    citations_to_score = get_unscored_citations(target_id)

    # Pre-filter any citations that don't need LLM processing
    filtered_citations_to_score = []
    shared_count = 0
    for citation in citations_to_score:
        if not citation.get("raw_contexts"):
            update_citation_sentiment_only(
                citation["citation_id"],
                {
                    "score": 5,
                    "positive_comment": "No specific context available from the source text.",
                    "usage_classification": "Discussing",
                },
                VERSION,
                target_id,
            )
            continue

        # ── Cross-target sharing: reuse sentiment from other targets ──
        cited_paper_id = citation.get("cited_paper_id")
        if cited_paper_id:
            shared = find_shared_sentiment(
                citation["citation_id"], cited_paper_id, target_id
            )
            if shared:
                update_citation_sentiment_only(
                    citation["citation_id"],
                    shared,
                    shared.get("version", VERSION),
                    target_id,
                )
                shared_count += 1
                logger.info(
                    f"    [SENTIMENT-SHARED] '{citation['citing_title'][:40]}...' → "
                    f"{shared.get('usage_classification', 'Discussing')}, {shared.get('score')}/10"
                )
                continue

        filtered_citations_to_score.append(
            {
                "id": citation["citation_id"],
                "cited_title": citation["cited_title"],
                "title": citation["citing_title"],
                "url": citation["url"],
                "citing_citation_count": citation["citing_citation_count"],
                "authors": [a["name"] for a in citation.get("notable_authors", [])] if citation.get("notable_authors") else [],
                "contexts": citation["raw_contexts"],
            }
        )

    if shared_count:
        logger.info(f"  Phase 4: Reused sentiment for {shared_count} citations from other targets.")

    citations_to_score = filtered_citations_to_score

    if not (citations_to_score and client):
        return

    logger.info(
        f"\nPhase 4: Querying Gemini for sentiment of {len(citations_to_score)} citations..."
    )
    chunk_size = 20

    from backend.database.sqlite_db import get_target_status, update_target_progress

    for i in range(0, len(citations_to_score), chunk_size):
        if get_target_status(target_id) in ("paused", "cancelled"):
            logger.info(
                f"Target {target_id} paused or cancelled. Stopping sentiment scoring."
            )
            break

        chunk = citations_to_score[i : i + chunk_size]
        logger.info(
            f"  Batch {i // chunk_size + 1}/"
            f"{(len(citations_to_score) - 1) // chunk_size + 1} ({len(chunk)} contexts)..."
        )

        prompt = (
            "CRITICAL INSTRUCTION: Analyze the citations below carefully. "
            "DO NOT hallucinate. Provide EXACT, FACTUAL assessments based ONLY on the provided citation contexts.\n\n"
            "For each citation below, provide JSON mapping ID to:\n"
            "{\n"
            '  "score": 1-10 (sentiment),\n'
            '  "positive_comment": "A very brief, user-friendly 1-sentence explanation of HOW the citing paper '
            'views the specific CITED PAPER. Avoid academic jargon and lengthy summaries.",\n'
            '  "sentiment_evidence": "Exact 1-2 sentence evidence quote extracted directly from the provided '
            'context that justifies the score and the positive_comment.",\n'
            '  "paper_homepage": str (official URL),\n'
            '  "usage_classification": "Discussing"|"Comparison"|"Extending / Using"\n'
            "}.\n\n"
        )
        for c in chunk:
            prompt += (
                f"ID: {c['id']}\n"
                f"Citing Paper: '{c['title']}' (Citations: {c['citing_citation_count']})\n"
                f"Cited Paper: '{c['cited_title']}'\n"
                f"Ctx: {' '.join(c['contexts'])}\n\n"
            )

        for attempt in range(4):
            try:
                time.sleep(0.01)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "phase": "phase_4_sentiment",
                        "temperature": 0.1,
                        "top_p": 0.8,
                        "target_id": target_id,
                        "system_user_id": system_user_id,
                    },
                )
                text = response.text.strip()
                parsed = extract_json(text)

                if isinstance(parsed, list):
                    new_parsed: dict = {}
                    for item in parsed:
                        if isinstance(item, dict):
                            # Support both [{"ID1": {...}}] and [{"id": "ID1", "score": ...}]
                            if "score" in item and "id" in item:
                                new_parsed[item["id"]] = item
                            else:
                                new_parsed.update(item)
                    parsed = new_parsed
                elif isinstance(parsed, dict) and "score" in parsed and "id" in parsed:
                    # extract_json coerces single-element lists to a flat dict;
                    # re-key by the "id" field so downstream lookup works.
                    parsed = {parsed["id"]: parsed}

                scored_count = 0
                for c in chunk:
                    res_data = parsed.get(c["id"])
                    # Fuzzy match: try prefix matching if exact key fails
                    if not res_data:
                        for key in parsed:
                            if c["id"].startswith(key) or key.startswith(c["id"][:12]):
                                res_data = parsed[key]
                                break
                    if res_data:
                        try:
                            score = int(res_data.get("score", 5))
                            paper_url = str(res_data.get("paper_homepage", ""))
                            if paper_url and not url_looks_valid(paper_url):
                                paper_url = ""

                            update_citation_sentiment_only(
                                c["id"],
                                {
                                    "score": score,
                                    "positive_comment": str(
                                        res_data.get("positive_comment", "")
                                    ),
                                    "sentiment_evidence": str(
                                        res_data.get("sentiment_evidence", "")
                                    ),
                                    "paper_homepage": paper_url,
                                    "usage_classification": str(
                                        res_data.get(
                                            "usage_classification", "Discussing"
                                        )
                                    ),
                                },
                                VERSION,
                                target_id,
                            )
                            logger.info(
                                f"    [SCORED] '{c['title'][:40]}...' -> "
                                f"{str(res_data.get('usage_classification', 'Discussing'))}, {score}/10"
                            )
                            scored_count += 1
                        except Exception:
                            pass

                if scored_count == 0:
                    logger.warning(
                        f"  WARNING: LLM returned JSON but 0/{len(chunk)} citations matched. "
                        f"LLM keys: {list(parsed.keys())[:3]}..."
                    )
                    logger.warning(
                        f"  Expected IDs: {[c['id'][:16] + '...' for c in chunk[:3]]}"
                    )
                    if attempt < 3:
                        logger.info("  Retrying batch...")
                        time.sleep(5)
                        continue
                
                current_batch = i // chunk_size
                total_batches = (len(citations_to_score) - 1) // chunk_size + 1
                progress = 70 + int(((current_batch + 1) / total_batches) * 30)
                update_target_progress(target_id, "scoring", progress)

                break
            except Exception as e:
                action = handle_llm_error(e, attempt)
                if action == "abort":
                    return
                elif action == "skip":
                    break
