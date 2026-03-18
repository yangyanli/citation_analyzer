#!/usr/bin/env python3
"""Export domain distribution data as a JSON file for static embedding.

Usage:
    python scripts/export_domains.py --target 9RxI7UAAAAAJ --output ~/Projects/yangyanli.github.io/src/data/domains.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database.connection import get_db_connection


def export_domains(target_id: str, output_path: str) -> None:
    with get_db_connection() as conn:
        # Get target name
        target = conn.execute(
            "SELECT name FROM analysis_targets WHERE target_id = ?",
            (target_id,),
        ).fetchone()
        if not target:
            print(f"Error: target '{target_id}' not found in database.")
            sys.exit(1)

        # Get total citations for this target
        total_row = conn.execute(
            "SELECT COUNT(*) as count FROM citations WHERE target_id = ?",
            (target_id,),
        ).fetchone()

        # Get domain distribution
        rows = conn.execute(
            """SELECT research_domain, COUNT(*) as count
               FROM citations
               WHERE target_id = ? AND research_domain IS NOT NULL
               GROUP BY research_domain
               ORDER BY count DESC""",
            (target_id,),
        ).fetchall()

        domains = []
        for r in rows:
            domain_name = r["research_domain"]
            # Get sentiment breakdown for this domain
            sentiment_rows = conn.execute(
                """SELECT ROUND(MAX(0, MIN(10, COALESCE(score, 0)))) as score,
                          COUNT(*) as count
                   FROM citations
                   WHERE target_id = ? AND research_domain = ?
                   GROUP BY ROUND(MAX(0, MIN(10, COALESCE(score, 0))))
                   ORDER BY score DESC""",
                (target_id, domain_name),
            ).fetchall()
            sentiment = [
                {"score": int(sr["score"]), "count": sr["count"]}
                for sr in sentiment_rows
            ]
            domains.append({
                "domain": domain_name,
                "count": r["count"],
                "sentiment": sentiment,
            })

    data = {
        "target": target["name"],
        "target_id": target_id,
        "collected": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "domains": domains,
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"Exported {len(domains)} domains ({sum(d['count'] for d in domains)} classified citations) → {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export domain data for homepage embedding.")
    parser.add_argument("--target", required=True, help="Target ID (e.g., Google Scholar user ID)")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()
    export_domains(args.target, args.output)
