"""Semantic Scholar API client with rate-limit handling."""

import os
import time
import requests
import re
import urllib.parse
from backend.core.config import logger
from backend.api.base import CitationProvider

S2_API_BASE = "https://api.semanticscholar.org/graph/v1"
S2_API_KEY = os.environ.get("S2_API_KEY")


def _s2_headers() -> dict:
    """Build request headers, including API key if available."""
    headers = {}
    if S2_API_KEY:
        headers["x-api-key"] = S2_API_KEY
    return headers


class SemanticScholarProvider(CitationProvider):
    """Concrete implementation of CitationProvider using Semantic Scholar."""

    def search_paper(self, title: str) -> dict | None:
        """Search for a paper by title and return the first match."""
        return search_semantic_scholar_paper(title)

    def fetch_citations(self, paper_id: str) -> list[dict]:
        """Fetch all citations for a given Semantic Scholar paper ID."""
        return fetch_citations_from_s2(paper_id)


def _s2_request(url: str) -> dict | None:
    """Execute a GET request against the Semantic Scholar API with retries."""
    for attempt in range(5):
        try:
            time.sleep(1.1)
            response = requests.get(url, headers=_s2_headers(), timeout=10)
            if response.status_code == 429:
                wait_time = 5 * (attempt + 1)
                logger.warning(f"S2 Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            wait_time = 5 * (attempt + 1)
            if "429" in str(e):
                logger.warning(f"S2 Rate limited. Waiting {wait_time}s...")
            else:
                logger.warning(
                    f"S2 Network error (attempt {attempt+1}/5): {e}. Retrying in {wait_time}s..."
                )

            if attempt < 4:
                time.sleep(wait_time)
                continue

            logger.error(f"Failed to request S2 after 5 attempts: {e}")
            break
    return None


def search_semantic_scholar_paper(title: str) -> dict | None:
    """Search for a paper by title and return the first match."""
    logger.info(f"Searching Semantic Scholar for: '{title}'")
    # Sanitize query to avoid 500 errors from S2's search backend
    clean_title = re.sub(r'[:\-]', ' ', title)
    clean_title = urllib.parse.quote(clean_title)
    url = f"{S2_API_BASE}/paper/search?query={clean_title}&limit=1&fields=paperId,title,citationCount"
    data = _s2_request(url)
    if data and data.get("data"):
        return data["data"][0]
    return None


def fetch_citations_from_s2(paper_id: str) -> list[dict]:
    """Fetch all citations for a given Semantic Scholar paper ID."""
    limit = 1000
    logger.info(f"Fetching citations for S2 Paper ID: {paper_id}")
    url = (
        f"{S2_API_BASE}/paper/{paper_id}/citations"
        f"?fields=title,authors,contexts,citationCount,year,venue,publicationVenue,journal,url&limit={limit}"
    )
    data = _s2_request(url)
    return data.get("data", []) if data else []


def fetch_s2_author(author_id: str) -> dict | None:
    """Fetch an author and their publications from Semantic Scholar by Author ID."""
    logger.info(f"Fetching Semantic Scholar profile for Author ID: {author_id}")
    url = f"{S2_API_BASE}/author/{author_id}?fields=name,affiliations,homepage,paperCount,citationCount,hIndex,papers.title,papers.year,papers.citationCount"
    data = _s2_request(url)
    if data and not data.get("error"):
        return data
    return None


def _s2_post_request(url: str, json_body: dict) -> dict | None:
    """Execute a POST request against the Semantic Scholar API with retries."""
    for attempt in range(5):
        try:
            time.sleep(1.1)
            response = requests.post(
                url, json=json_body, headers=_s2_headers(), timeout=30
            )
            if response.status_code == 429:
                wait_time = 5 * (attempt + 1)
                logger.warning(f"S2 Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            wait_time = 5 * (attempt + 1)
            if "429" in str(e):
                logger.warning(f"S2 Rate limited. Waiting {wait_time}s...")
            else:
                logger.warning(
                    f"S2 POST error (attempt {attempt+1}/5): {e}. Retrying in {wait_time}s..."
                )
            if attempt < 4:
                time.sleep(wait_time)
                continue
            logger.error(f"Failed S2 POST after 5 attempts: {e}")
            break
    return None


def batch_fetch_paper_details(
    paper_ids: list[str], fields: str = "paperId,title,citationCount"
) -> list[dict]:
    """Fetch details for multiple papers in one request using S2 batch endpoint.

    Accepts up to 500 paper IDs per call. IDs can be S2 paper IDs, DOIs, etc.
    Returns a list of paper detail dicts (may contain None for unfound papers).
    """
    if not paper_ids:
        return []

    results = []
    # S2 batch endpoint allows up to 500 IDs per request
    for i in range(0, len(paper_ids), 500):
        chunk = paper_ids[i : i + 500]
        logger.info(
            f"Batch fetching {len(chunk)} papers from S2 ({i+1}-{i+len(chunk)} of {len(paper_ids)})..."
        )
        url = f"{S2_API_BASE}/paper/batch?fields={fields}"
        data = _s2_post_request(url, {"ids": chunk})
        if data and isinstance(data, list):
            results.extend(data)
        else:
            # If batch fails, extend with None placeholders
            results.extend([None] * len(chunk))

    return results


def resolve_arxiv_venue(paper_data: dict) -> str:
    """Extract a peer-reviewed venue string if one exists, overriding 'arXiv'.

    Semantic Scholar often retains 'arXiv.org' in the base 'venue' field even
    after publication. This function checks enriched fields like 'journal' or
    'publicationVenue' for actual conference or journal names.
    """
    base_venue = paper_data.get("venue") or ""

    # Check journal
    journal = paper_data.get("journal")
    if journal and isinstance(journal, dict):
        journal_name = journal.get("name")
        if journal_name and "arxiv" not in journal_name.lower():
            return journal_name

    # Check publicationVenue
    pub_venue = paper_data.get("publicationVenue")
    if pub_venue and isinstance(pub_venue, dict):
        pub_name = pub_venue.get("name")
        if pub_name and "arxiv" not in pub_name.lower():
            return pub_name

    return base_venue
