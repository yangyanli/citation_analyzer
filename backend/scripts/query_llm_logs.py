#!/usr/bin/env python3
"""Query script to inspect LLM logs stored in the SQLite database."""

import argparse
from backend.database.sqlite_db import get_llm_logs, init_db


def main():
    parser = argparse.ArgumentParser(description="Query LLM usage logs.")
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max number of logs to retrieve (default: 100)",
    )
    parser.add_argument("--offset", type=int, default=0, help="Pagination offset")
    parser.add_argument("--target_id", type=str, help="Filter by target ID")
    parser.add_argument("--stage", type=str, help="Filter by pipeline stage")
    parser.add_argument(
        "--fallback_only", action="store_true", help="Show ONLY fallback logs"
    )

    args = parser.parse_args()

    # Ensure tables exist just in case
    init_db()

    logs = get_llm_logs(
        limit=args.limit, offset=args.offset, target_id=args.target_id, stage=args.stage
    )

    if args.fallback_only:
        logs = [log for log in logs if log["is_fallback"] == 1]

    print(f"\nFound {len(logs)} logs (showing up to {args.limit}):")
    print("-" * 120)
    for log in logs:
        is_fb = "[FALLBACK]" if log["is_fallback"] else "[API]"
        user_str = f"U:{log['system_user_id']}" if log["system_user_id"] else "U:System"
        print(
            f"[{log['timestamp']}] {is_fb} {user_str} | Target: {log['target_id']} | Stage: {log['stage']} | Model: {log['model']}"
        )
        prompt_snippet = (
            (log["prompt_text"][:60].replace("\n", " ") + "...")
            if log["prompt_text"]
            else "None"
        )
        resp_snippet = (
            (log["response_text"][:60].replace("\n", " ") + "...")
            if log["response_text"]
            else "None"
        )
        print(f"  Prompt: {prompt_snippet}")
        print(f"  Response: {resp_snippet}")
        print(f"  Tokens: {log['input_tokens']} in / {log['output_tokens']} out")
        print("-" * 120)


if __name__ == "__main__":
    main()
