#!/usr/bin/env python3
"""Remove duplicate ranking runs, keeping the newest per (universe, strategy, as_of_date).

Does NOT delete market_data OHLCV bars — those are shared source data, not per-run artifacts.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import text

from app.db.session import get_session_factory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-date",
        default="2024-06-01",
        help="Only prune runs with as_of_date on or after this date",
    )
    parser.add_argument(
        "--universe",
        default="NIFTY_500",
        help="Universe code to prune",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report counts only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    Session = get_session_factory()

    stale_sql = text("""
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY universe_code, strategy_name, strategy_version, as_of_date
                       ORDER BY started_at DESC
                   ) AS rn
            FROM ranking_runs
            WHERE as_of_date >= :from_date
              AND universe_code = :universe
              AND status = 'completed'
        )
        SELECT id FROM ranked WHERE rn > 1
    """)

    count_results_sql = text("""
        WITH stale AS (
            SELECT id FROM ranking_runs WHERE id = ANY(:ids)
        )
        SELECT
            (SELECT COUNT(*) FROM stale) AS stale_runs,
            (SELECT COUNT(*) FROM ranking_results rr WHERE rr.ranking_run_id = ANY(:ids)) AS stale_results,
            (SELECT COUNT(*) FROM ranking_validation_reports rv WHERE rv.ranking_run_id = ANY(:ids)) AS stale_validation_reports
    """)

    with Session() as db:
        stale_ids = [row[0] for row in db.execute(
            stale_sql, {"from_date": args.from_date, "universe": args.universe}
        ).all()]
        if not stale_ids:
            print("No stale duplicate ranking runs found.")
            return 0

        counts = db.execute(count_results_sql, {"ids": stale_ids}).mappings().one()
        print(
            f"Stale runs to delete: {counts['stale_runs']}\n"
            f"  ranking_results rows: {counts['stale_results']}\n"
            f"  validation reports: {counts['stale_validation_reports']}"
        )

        if args.dry_run:
            print("Dry run — no changes made.")
            return 0

        deleted = db.execute(
            text("DELETE FROM ranking_runs WHERE id = ANY(:ids)"),
            {"ids": stale_ids},
        ).rowcount
        db.commit()
        print(f"Deleted {deleted} stale ranking runs (children cascade).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
