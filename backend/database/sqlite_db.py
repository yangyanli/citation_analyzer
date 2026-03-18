"""Backward-compatible re-export facade for Citation Analyzer database.

All functions that were originally defined here have been split into focused
modules under ``backend.database.*``.  This file re-exports every public name
so that *existing* import paths continue to work without modification::

    from backend.database.sqlite_db import init_db, get_all_citations  # still works

New code should import from the specific module directly::

    from backend.database.schema import init_db
    from backend.database.citations import get_all_citations
"""

# Connection
from backend.database.connection import get_db_connection, DB_PATH  # noqa: F401

# Schema & migrations
from backend.database.schema import init_db  # noqa: F401

# Analysis targets CRUD
from backend.database.targets import (  # noqa: F401
    get_analysis_target,
    upsert_analysis_target,
    delete_analysis_target,
    get_target_status,
    update_target_progress,
    set_target_fallback_status,
    update_target_total_citations,
    update_target_s2_total,
    update_target_phase_estimates,
)

# Citations CRUD
from backend.database.citations import (  # noqa: F401
    insert_citation_if_missing,
    get_unscored_citations,
    get_citation,
    update_citation_sentiment_only,
    get_all_citations,
    wipe_phase_data,
    update_citation_authors,
    update_citation_seminal,
    update_citation_domain,
    get_unclassified_citations,
    find_shared_domain,
    find_shared_sentiment,
    find_shared_venue_authors,
)

# Authors CRUD
from backend.database.authors import (  # noqa: F401
    get_author,
    upsert_author,
)

# S2 search cache
from backend.database.cache import (  # noqa: F401
    get_cached_s2_paper,
    set_cached_s2_paper,
)

# LLM logs
from backend.database.logs import (  # noqa: F401
    insert_llm_log,
    get_llm_logs,
)
