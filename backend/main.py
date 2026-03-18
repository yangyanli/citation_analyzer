#!/usr/bin/env python3
"""Citation Analyzer — AI-powered citation sentiment analysis.

Orchestrates the full pipeline:
  Phase 0: Domain-adaptive criteria generation
  Phase 1: Citation collection from Semantic Scholar
  Phase 2: Notable-author detection with web verification
  Phase 3: Seminal-discovery classification
  Phase 4: Sentiment scoring via multi-LLM analysis
"""

import json
import sys


from backend.api.llm import get_llm_client, initialize_llm_client
from backend.core.cli import setup_parser
from backend.pipeline.orchestrator import run_pipeline
from backend.database.sqlite_db import init_db


def main() -> None:
    """Entry point for the Citation Analyzer CLI."""
    parser = setup_parser()
    args = parser.parse_args()

    # Automatically set start_phase to match run_only_phase if it wasn't explicitly set
    if getattr(args, "run_only_phase", None) is not None and not any(arg == "--start_phase" for arg in sys.argv):
        args.start_phase = args.run_only_phase

    # Handle database reset if requested
    if getattr(args, "reset_db", False):
        print("\n⚠️  WARNING: You requested to reset the database.")
        confirm = (
            input("Are you sure you want to delete ALL data? (y/N): ").strip().lower()
        )
        if confirm == "y":
            import os

            db_path = "data/citation_analyzer.db"
            if os.path.exists(db_path):
                os.remove(db_path)
                print(f"✅ Database {db_path} deleted successfully.")
            else:
                print(f"ℹ️ Database {db_path} does not exist. Nothing to delete.")
        else:
            print("Aborted database reset. Exiting.")
            sys.exit(0)

    # --- Initialise ---
    init_db()

    # Handle deletion if requested
    if getattr(args, "delete", False):
        from backend.database.sqlite_db import delete_analysis_target

        target_id = args.user_id if args.user_id else args.paper
        if delete_analysis_target(target_id):
            print(
                f"✅ Successfully deleted target '{target_id}' and all associated citations."
            )
        else:
            print(
                f"❌ Target '{target_id}' not found in the database. Nothing to delete."
            )
        sys.exit(0)

    # Handle explicit arXiv resolution trigger
    if getattr(args, "resolve_arxiv", False):
        from backend.api.venue_resolver import batch_resolve_arxiv_venues

        target_id = args.user_id if args.user_id else args.paper
        batch_resolve_arxiv_venues(target_id)
        sys.exit(0)

    initialize_llm_client()
    client = get_llm_client()

    if not client:
        print(
            "\n❌ GEMINI_API_KEY is missing or invalid. Please check your .env file or environment variables."
        )
        sys.exit(1)

    # Build overrides: config file as base, CLI args override
    overrides: dict = {}
    if args.config:
        with open(args.config, "r") as f:
            config_data = json.load(f)
        for key in ("domain", "notable_criteria", "seminal_criteria"):
            if config_data.get(key):
                overrides[key] = config_data[key]
    if args.domain:
        overrides["domain"] = args.domain
    if args.notable_criteria:
        overrides["notable_criteria"] = args.notable_criteria
    if args.seminal_criteria:
        overrides["seminal_criteria"] = args.seminal_criteria
    overrides = overrides or None

    try:
        run_pipeline(args, client, overrides)
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user.")
        sys.exit(1)
    finally:
        from backend.core.cost import print_fallback_savings_summary

        print_fallback_savings_summary()


if __name__ == "__main__":
    main()
