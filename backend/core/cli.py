"""Command-line interface and terminal display utilities."""

import argparse
import sys
import select
from backend.core.cost import MODEL_PRICING
from backend.core.config import logger


def setup_parser() -> argparse.ArgumentParser:
    """Configure and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Citation Analyzer — AI-powered citation sentiment analysis",
    )

    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--user_id", type=str, help="Author ID: numeric for Semantic Scholar, alphanumeric for Google Scholar")
    target_group.add_argument(
        "--paper",
        type=str,
        help="Analyze a single paper by title (via Semantic Scholar)",
    )

    # New flags for deletion and reset
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the specified researcher or paper from the database",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Drop all tables and purge the database before running",
    )
    parser.add_argument(
        "--resolve_arxiv",
        action="store_true",
        help="Trigger the retrospective arXiv venue resolution scan",
    )
    parser.add_argument(
        "--group_id",
        type=int,
        help="ID of the group this new analysis should belong to",
    )

    parser.add_argument(
        "--system_user_id",
        type=int,
        help="The internal user ID triggering this analysis (for LLM logging)",
    )

    parser.add_argument(
        "--total_citations_to_add",
        type=str,
        default="all",
        help="Target citations to analyze ('all' or integer limit)",
    )
    parser.add_argument(
        "--estimate_only",
        action="store_true",
        help="Estimate LLM cost without running queries",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.5-flash",
        help="LLM model (e.g. gemini-2.5-flash)",
    )
    parser.add_argument(
        "--domain", type=str, default=None, help="Override the inferred domain"
    )
    parser.add_argument(
        "--notable_criteria",
        type=str,
        default=None,
        help="Override notable author criteria",
    )
    parser.add_argument(
        "--seminal_criteria", type=str, default=None, help="Override seminal criteria"
    )
    parser.add_argument(
        "--start_phase",
        type=int,
        default=0,
        help="Start pipeline at specific phase (0: Criteria, 1: Citations, 2: Authors, 3: Seminal, 4: Sentiment, 5: Domains)",
    )
    parser.add_argument(
        "--wipe_phase",
        type=int,
        choices=[2, 3, 4, 5],
        help="Wipe AI and analysis data for a specific phase (2, 3, 4, or 5). Phase 1 cannot be wiped to preserve citation relations.",
    )
    parser.add_argument(
        "--run_only_phase",
        type=int,
        choices=[0, 1, 2, 3, 4, 5],
        help="Only run this specific phase, instead of progressing through all subsequent phases.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run without user confirmation (useful for API triggers)",
    )
    parser.add_argument(
        "--generate_criteria_only",
        action="store_true",
        help="Generate AI criteria and print to stdout as JSON, then exit",
    )
    parser.add_argument(
        "--config", type=str, default=None, help="Path to JSON config file"
    )
    return parser


def timed_input(prompt_text: str, timeout: int = 300, default: str = "") -> str:
    """Prompt the user with a timeout (only works on Unix/Mac)."""
    sys.stdout.write(prompt_text)
    sys.stdout.flush()
    try:
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            return sys.stdin.readline().strip()
    except Exception:
        pass
    sys.stdout.write(
        f"\n[Timeout reached ({timeout}s) or non-interactive environment. Proceeding automatically.]\n"
    )
    return default


def prompt_model_selection(
    default_model: str, non_interactive: bool = False
) -> str | None:
    """Prompt the user to select a model. Returns model name or None to abort."""
    print(f"\nSelect a model to proceed (or press Enter for default: {default_model}):")
    if non_interactive:
        print(
            "[Non-interactive mode] Will automatically accept the default if no input is provided within 5 minutes."
        )

    for i, model_id in enumerate(MODEL_PRICING.keys(), 1):
        print(f"  {i}. {model_id}")
    print("  0. Abort")

    if non_interactive:
        confirm = timed_input("\nSelection: ", 300, "")
    else:
        confirm = input("\nSelection: ").strip()

    if confirm == "0":
        return None
    if confirm == "":
        return default_model
    if confirm.isdigit() and 1 <= int(confirm) <= len(MODEL_PRICING):
        return list(MODEL_PRICING.keys())[int(confirm) - 1]
    if confirm in MODEL_PRICING:
        return confirm
    return None


def wrap_text(text: str, width: int = 60) -> list[str]:
    """Simple word-wrap for display in the terminal."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines or [""]


def confirm_criteria(
    target_id: str, eval_criteria: dict, non_interactive: bool = False
) -> dict:
    """Display inferred criteria and let the user confirm or edit each field.

    Returns the (possibly modified) criteria dict.
    """
    from backend.database.sqlite_db import upsert_analysis_target, get_analysis_target

    fields = [
        ("inferred_domain", "Domain"),
        ("notable_criteria", "Notable Author Criteria"),
        ("seminal_criteria", "Seminal Discovery Criteria"),
    ]

    print("\n--- Domain-Adaptive Criteria ---")
    for key, label in fields:
        value = eval_criteria.get(key, "")
        print(f"\n{label}:\n{value}")
    print("\n---------------------------")

    if non_interactive:
        print(
            "\n[Non-interactive mode] Will automatically accept if no input is provided within 5 minutes."
        )

    print("\nReview the criteria above. For each field:")
    print("  • Press Enter to accept the current value")
    print("  • Type a new value to replace it")
    print("  • Type 'q' to abort\n")

    changed = False
    import time

    timeout = 300
    for key, label in fields:
        current = eval_criteria.get(key, "")
        prompt_str = f"  {label} [{current[:60]}{'...' if len(current) > 60 else ''}]: "

        if non_interactive:
            start_time = time.time()
            user_input = timed_input(prompt_str, timeout, "")
            elapsed = time.time() - start_time
            timeout = max(0, timeout - int(elapsed))
        else:
            user_input = input(prompt_str).strip()

        if user_input.lower() == "q":
            print("Aborted by user.")
            sys.exit(0)
        if user_input:
            eval_criteria[key] = user_input
            changed = True

    if changed:
        target_data = get_analysis_target(target_id) or {}
        target_data["evaluation_criteria"] = eval_criteria
        upsert_analysis_target(target_id, target_data)
        print("\n✅ Criteria updated and saved.")
    else:
        print("\n✅ Criteria confirmed.")

    return eval_criteria


def print_task_summary(target_id: str, publications: list) -> int:
    """Print a summary of total tasks, finished tasks, and todo tasks before running.
    Returns the total citations fetched from Semantic Scholar.
    Uses batch API for efficiency when possible.
    """
    from backend.api.semantic_scholar import (
        search_semantic_scholar_paper,
    )
    from backend.database.sqlite_db import (
        get_cached_s2_paper,
        set_cached_s2_paper,
    )

    print("\nFetching total citation counts from Semantic Scholar...")

    # Phase 1: Check cache for all papers and collect IDs for batch fetch
    cached_total = 0
    uncached_titles = []  # Titles that need S2 lookup
    cached_paper_ids = []  # S2 IDs from cache (for batch refresh if needed)

    for pub in publications:
        title = pub.get("bib", {}).get("title")
        if not title:
            continue

        cached = get_cached_s2_paper(title)
        if cached and cached.get("citationCount") is not None:
            cached_total += cached.get("citationCount", 0)
            if cached.get("paperId"):
                cached_paper_ids.append(cached["paperId"])
        else:
            uncached_titles.append(title)

    # Phase 2: For uncached papers, try batch search by doing individual lookups
    # but with a cap to avoid getting stuck on rate limits
    uncached_total = 0
    MAX_INDIVIDUAL_LOOKUPS = 10  # Cap individual lookups to avoid rate-limit hell

    if uncached_titles:
        if len(uncached_titles) <= MAX_INDIVIDUAL_LOOKUPS:
            # Small number — do individual lookups
            import time

            for title in uncached_titles:
                s2_paper = search_semantic_scholar_paper(title)
                if s2_paper:
                    uncached_total += s2_paper.get("citationCount", 0)
                    cache_key = title or s2_paper.get("title", "")
                    if cache_key:
                        set_cached_s2_paper(cache_key, s2_paper)
                time.sleep(0.5)
        else:
            # Too many uncached papers — skip individual lookups, report partial count
            logger.info(
                f"Skipping individual S2 lookups for {len(uncached_titles)} uncached papers (would cause rate limiting). Using cached data only."
            )

    total_citations = cached_total + uncached_total

    return total_citations
