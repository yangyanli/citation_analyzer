"""Phase 1 — Citation collection from Semantic Scholar.

Iterates over the researcher's publications, resolves each to a Semantic
Scholar paper ID, and collects all citing papers with their contexts.
Self-citations are flagged, and previously cached citations are tagged to
avoid redundant LLM calls.
"""

from backend.core.config import logger, is_same_person
from backend.api.semantic_scholar import SemanticScholarProvider


def collect_citations(
    publications: list,
    scholar_name: str | None,
    total_citations_to_add: int | str,
    target_id: str,
    provider: SemanticScholarProvider | None = None,
) -> list[dict]:
    """Collect citing papers using the provided citation source. Limit can be an integer or 'all'."""
    from backend.database.sqlite_db import (
        get_cached_s2_paper,
        set_cached_s2_paper,
        get_citation,
        insert_citation_if_missing,
        get_target_status,
    )
    from backend.api.semantic_scholar import resolve_arxiv_venue

    if provider is None:
        provider = SemanticScholarProvider()

    collected_citations: list[dict] = []
    new_inserts = 0

    for pub in publications:
        # Check if user paused or cancelled
        if get_target_status(target_id) in ("paused", "cancelled"):
            logger.info(
                f"Target {target_id} paused or cancelled. Stopping citation collection."
            )
            break

        if total_citations_to_add != "all" and len(collected_citations) >= int(
            total_citations_to_add
        ):
            break

        title = pub["bib"].get("title")
        if not title:
            continue

        s2_paper = get_cached_s2_paper(title)
        if not s2_paper:
            s2_paper = provider.search_paper(title)
            if s2_paper:
                set_cached_s2_paper(title, s2_paper)

        if not s2_paper:
            continue

        paper_id = s2_paper["paperId"]
        canonical_title = s2_paper.get("title") or title

        citations_data = provider.fetch_citations(paper_id)

        for citation in citations_data or []:
            if total_citations_to_add != "all" and len(collected_citations) >= int(
                total_citations_to_add
            ):
                break

            citing_paper = citation.get("citingPaper", {})
            if not citing_paper:
                continue

            citation_id = citing_paper.get("paperId")
            if not citation_id:
                continue

            # Identify self-citations
            is_self = any(
                is_same_person(scholar_name, auth.get("name"))
                for auth in citing_paper.get("authors", [])
            )

            # Check if we already have it in the DB for this target
            cached_db_record = get_citation(citation_id, target_id)
            is_cached = bool(
                cached_db_record and cached_db_record.get("score") is not None
            )

            record_dict = {
                "cited_title": canonical_title,
                "cited_paper_id": paper_id,
                "citation_id": citation_id,
                "target_id": target_id,
                "authors": citing_paper.get("authors", []),
                "citing_title": citing_paper.get("title", ""),
                "url": citing_paper.get("url", ""),
                "is_self_citation": is_self,
                "is_cached": is_cached,
                "citing_citation_count": citing_paper.get("citationCount", 0),
                "year": citing_paper.get("year"),
                "venue": resolve_arxiv_venue(citing_paper),
                "contexts": citation.get("contexts", []),
            }

            collected_citations.append(record_dict)

            # Instantly insert pending records to SQLite for the frontend
            if insert_citation_if_missing(citation_id, record_dict):
                new_inserts += 1

    deduped = len(collected_citations) - new_inserts
    if deduped > 0:
        logger.info(
            f"Collected {len(collected_citations)} citation references "
            f"({new_inserts} unique citing papers added to DB, "
            f"{deduped} deduplicated across cited papers)."
        )
    else:
        logger.info(
            f"Collected {len(collected_citations)} citations "
            f"({new_inserts} new records added to DB)."
        )
    return collected_citations
