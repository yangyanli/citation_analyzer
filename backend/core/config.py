"""Core configuration, utilities, and shared helpers for the Citation Analyzer pipeline."""

import re
import json
import logging
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("citation_analyzer")

# ---------------------------------------------------------------------------
# Versioning & Paths
# ---------------------------------------------------------------------------
VERSION = "1.2.0"
# All data is now persisted in the SQLite database (data/citation_analyzer.db).
CACHE_EXPIRY_DAYS = 7

load_dotenv()

# ---------------------------------------------------------------------------
# URL Validation
# ---------------------------------------------------------------------------


def url_looks_valid(url: str) -> bool:
    """Fast format-only check (no network request).

    Returns True if *url* starts with ``http://`` or ``https://`` and
    contains a domain-like segment.  This replaces the old ``is_valid_url``
    which performed an expensive 5-second HEAD request per call.
    """
    if not url or not isinstance(url, str):
        return False
    return bool(re.match(r"^https?://[^\s/$.?#].[^\s]*$", url, re.IGNORECASE))



# ---------------------------------------------------------------------------
# Name Matching (self-citation detection)
# ---------------------------------------------------------------------------


def is_same_person(scholar_name: str, s2_name: str) -> bool:
    """Fuzzy name equality for self-citation detection.

    Handles exact matches and initial-based abbreviations
    (e.g. ``"Yangyan Li"`` vs ``"Y. Li"``).
    """
    if not scholar_name or not s2_name:
        return False
    if scholar_name.lower() == s2_name.lower():
        return True
    s_parts = scholar_name.lower().split()
    s2_parts = s2_name.lower().split()
    if not s_parts or not s2_parts:
        return False
    if s_parts[-1] == s2_parts[-1]:
        if s_parts[0][0] == s2_parts[0][0]:
            return True
    return False


# ---------------------------------------------------------------------------
# Shared JSON Extraction
# ---------------------------------------------------------------------------


def extract_json(text: str) -> dict:
    """Extract the first JSON object from an LLM response.

    Handles three common formats returned by Gemini:
    1. Bare JSON: ``{...}``
    2. Markdown-fenced: ````json ... ````
    3. JSON list: ``[{...}]`` (coerced to dict via ``list[0]``)

    Raises ``ValueError`` if no valid JSON can be extracted.
    """
    text = text.strip()

    # Try markdown-fenced JSON first
    md_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if md_match:
        text = md_match.group(1).strip()

    # If not fenced, look for the outermost { ... } or [ ... ]
    if not text.startswith(("{", "[")):
        # Find first { or [
        start_idx = -1
        for i, ch in enumerate(text):
            if ch in ("{", "["):
                start_idx = i
                break
        if start_idx == -1:
            raise ValueError(f"No JSON object found in response: {text[:100]}...")

        # Find matching end
        bracket = text[start_idx]
        end_bracket = "}" if bracket == "{" else "]"
        end_idx = text.rfind(end_bracket)
        if end_idx <= start_idx:
            raise ValueError(f"No closing bracket found in response: {text[:100]}...")
        text = text[start_idx : end_idx + 1]

    parsed = json.loads(text)

    # Coerce list → dict if needed
    if isinstance(parsed, list) and parsed:
        if isinstance(parsed[0], dict):
            return parsed[0] if len(parsed) == 1 else parsed
    return parsed


def coerce_llm_list_to_dict(parsed, key_field: str = "name", value_fields: tuple = ("is_notable", "evidence", "is_seminal")) -> dict:
    """Coerce an LLM response that came back as a list into a dict keyed by *key_field*.

    Handles two common LLM output shapes:
    1. ``[{"name": "X", "is_notable": true, ...}]`` → ``{"X": {...}}``
    2. ``[{"X": {...}}, {"Y": {...}}]``             → ``{"X": {...}, "Y": {...}}``
    """
    if not isinstance(parsed, list):
        return parsed

    new_parsed: dict = {}
    for item in parsed:
        if isinstance(item, dict):
            if key_field in item and any(k in item for k in value_fields):
                new_parsed[item[key_field]] = item
            else:
                new_parsed.update(item)
    return new_parsed


def handle_llm_error(e: Exception, attempt: int, max_attempts: int = 4) -> str:
    """Shared error handler for LLM API calls across pipeline phases.

    Returns one of: ``"abort"``, ``"retry"``, ``"skip"``.
    Side-effects: logs the error and sleeps on rate limits.
    """
    import time

    if "GenerateRequestsPerDay" in str(e):
        logger.critical("\nCRITICAL: Gemini Daily Quota Exhausted!")
        return "abort"

    err_lower = str(e).lower()
    if any(s in err_lower for s in ("429", "resource_exhausted", "disconnected", "connection")):
        logger.warning("  Rate limited or Disconnected. Waiting 20s...")
        time.sleep(20)
        return "retry"

    logger.error(f"  Attempt {attempt + 1}/{max_attempts} failed: {e}")
    if attempt < max_attempts - 1:
        time.sleep(5)
        return "retry"
    return "skip"
