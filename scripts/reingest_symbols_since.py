#!/usr/bin/env python3
"""Re-ingest Yahoo bars from since_date for symbols listed in a file (one per line)."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from app.core.constants import IngestPeriod, IngestionMode
from app.db.session import get_session_factory
from scripts.pipm_service_factory import build_pipm_services


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", type=date.fromisoformat, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    symbols = [
        line.strip()
        for line in args.symbols_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not symbols:
        print("No symbols in file", file=sys.stderr)
        return 1

    db = get_session_factory()()
    try:
        services = build_pipm_services(db)
        market_data = services["market_data_service"]
        totals = {"ok": 0, "failed": 0, "inserted": 0, "updated": 0}
        for offset in range(0, len(symbols), args.batch_size):
            batch = symbols[offset : offset + args.batch_size]
            print(f"Batch {offset // args.batch_size + 1}: {len(batch)} symbols")
            response = market_data.ingest(
                batch,
                IngestPeriod.FIVE_YEARS,
                ingestion_mode=IngestionMode.INCREMENTAL,
                since_date=args.since,
            )
            totals["ok"] += response.symbols_processed
            totals["failed"] += response.symbols_failed
            totals["inserted"] += response.rows_inserted
            totals["updated"] += response.rows_updated
            print(
                f"  status={response.status.value} ok={response.symbols_processed} "
                f"failed={response.symbols_failed} inserted={response.rows_inserted} "
                f"updated={response.rows_updated}"
            )
        print("Done:", totals)
    finally:
        db.close()
    return 0 if totals["failed"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
