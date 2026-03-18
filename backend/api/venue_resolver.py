"""Retrospective arXiv Venue Resolver.

Scans the SQLite database for existing citations with 'arXiv.org'
as the venue OR missing author lists, batches them up, fetches enriched
metadata from Semantic Scholar, and updates the SQLite database.
"""

from backend.core.config import logger
from backend.database.sqlite_db import get_db_connection, update_target_progress, find_shared_venue_authors
from backend.api.semantic_scholar import batch_fetch_paper_details, resolve_arxiv_venue


def batch_resolve_arxiv_venues(target_id: str | None = None) -> None:
    """Find arXiv papers in the DB and resolve them via Semantic Scholar."""

    # 1. Query for citations needing updates (arXiv or missing authors)
    target_citations = []

    with get_db_connection() as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        query = "SELECT citation_id, target_id, venue, authors FROM citations WHERE venue LIKE '%arxiv%' OR authors IS NULL OR authors = '[]' OR authors = ''"
        params = ()
        if target_id:
            query += " AND target_id = ?"
            params = (target_id,)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        target_citations = rows

    if not target_citations:
        logger.info("No citations found requiring venue or author resolution.")
        if target_id:
            update_target_progress(target_id, "completed", 100)
        return

    # ── Cross-target sharing: reuse venue/authors from other targets ──
    shared_updates = []
    remaining_citations = []
    for row in target_citations:
        shared = find_shared_venue_authors(row["citation_id"], row["target_id"])
        if shared:
            shared_updates.append((shared["venue"], shared["authors"], row["citation_id"], row["target_id"]))
            logger.info(f"  [VENUE-SHARED] {row['citation_id'][:16]}... → {shared['venue']}")
        else:
            remaining_citations.append(row)

    if shared_updates:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "UPDATE citations SET venue = ?, authors = ? WHERE citation_id = ? AND target_id = ?",
                shared_updates,
            )
            conn.commit()
        logger.info(f"  Phase 1: Reused venue/authors for {len(shared_updates)} citations from other targets.")

    target_citations = remaining_citations

    if not target_citations:
        logger.info("All citations resolved via cross-target sharing.")
        if target_id:
            update_target_progress(target_id, "completed", 100)
        return

    logger.info(
        f"Found {len(target_citations)} citations requiring updates. Starting resolution..."
    )

    if target_id:
        update_target_progress(target_id, "resolving_venues", 5)

    # 2. Batch fetch from S2
    # batch_fetch_paper_details automatically chunks to 500
    fields = "paperId,title,venue,publicationVenue,journal,authors"
    citation_ids = [row["citation_id"] for row in target_citations]
    enriched_papers = batch_fetch_paper_details(citation_ids, fields)

    # 3. Resolve and Update
    resolved_count = 0
    updates = []

    total = len(enriched_papers)

    for i, paper in enumerate(enriched_papers):
        # Progress tracking
        if target_id and i % 50 == 0:
            prog = 5 + int(90 * (i / total))
            update_target_progress(target_id, "resolving_venues", prog)

        if not paper:
            continue

        paper_id = paper.get("paperId")
        if not paper_id:
            continue

        original_db_row = target_citations[i]
        needs_update = False

        # Determine Venue Update
        resolved_venue = resolve_arxiv_venue(paper)
        final_venue = original_db_row.get("venue")
        if (
            resolved_venue
            and "arxiv" not in resolved_venue.lower()
            and original_db_row.get("venue", "").lower().find("arxiv") != -1
        ):
            final_venue = resolved_venue
            needs_update = True

        # Determine Author Update
        final_authors = original_db_row.get("authors")
        original_authors = final_authors

        if not original_authors or original_authors == "[]":
            api_authors = paper.get("authors", [])
            if api_authors:
                import json

                # Format to schema [ { "name": "Author 1" } ]
                clean_authors = [
                    {"name": a.get("name")} for a in api_authors if a.get("name")
                ]
                if clean_authors:
                    final_authors = json.dumps(clean_authors)
                    needs_update = True

        if needs_update:
            updates.append((final_venue, final_authors, original_db_row["citation_id"], original_db_row["target_id"]))
            resolved_count += 1
            logger.info(f"  [UPDATED] {paper.get('title', '')[:40]}...")

    if updates:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "UPDATE citations SET venue = ?, authors = ? WHERE citation_id = ? AND target_id = ?",
                updates,
            )
            conn.commit()

    logger.info(
        f"Retrospective resolution complete. Successfully updated {resolved_count}/{len(target_citations)} citations."
    )
    if target_id:
        update_target_progress(target_id, "completed", 100)


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
