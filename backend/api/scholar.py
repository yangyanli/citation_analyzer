"""Google Scholar profile fetcher via the ``scholarly`` library."""

from scholarly import scholarly

from backend.core.config import logger


def fetch_scholar_publications(user_id: str) -> dict | None:
    """Fetch the Google Scholar profile and publications for *user_id*."""
    logger.info(f"Fetching Google Scholar profile for user: {user_id}...")
    try:
        author = scholarly.search_author_id(user_id)
        scholarly.fill(author, sections=["publications"])
        return author
    except Exception as e:
        logger.error(f"Error fetching Google Scholar profile: {e}")
        return None
