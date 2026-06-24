#!/usr/bin/env python3
"""Seed ADR-039 sector_classifications from the existing stocks.sector column.

The FIL sector layer needs a stock → sector mapping. Rather than invent one, this
backfills sector_classifications from the sector already recorded on each stock row
(populated at universe ingest). Re-runnable: it upserts on (stock_id, sector).

Usage:
    uv run python scripts/seed_sector_classifications.py [--dry-run]

Stocks with no sector recorded are reported and skipped — fill those in upstream
(stocks.sector) or via a curated override file in a later pass.
"""

from __future__ import annotations

import argparse
import sys

from app.db.repositories.sector_classification_repository import SectorClassificationRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.session import get_session_factory


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed sector_classifications from stocks.sector.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be written without committing.",
    )
    args = parser.parse_args()

    session_factory = get_session_factory()
    db = session_factory()
    try:
        stock_repo = StockRepository(db)
        sector_repo = SectorClassificationRepository(db)

        stocks = stock_repo.list_stocks()
        with_sector = [s for s in stocks if s.sector]
        without_sector = [s for s in stocks if not s.sector]

        written = 0
        for stock in with_sector:
            if not args.dry_run:
                sector_repo.upsert(
                    stock_id=stock.id,
                    sector=stock.sector,
                    sub_sector=stock.industry,
                )
            written += 1

        if args.dry_run:
            db.rollback()
        else:
            db.commit()

        print(f"Stocks total:            {len(stocks)}")
        print(f"Classifications {'(would write)' if args.dry_run else 'written'}: {written}")
        print(f"Missing sector (skipped): {len(without_sector)}")
        if without_sector:
            preview = ", ".join(s.symbol for s in without_sector[:20])
            more = "" if len(without_sector) <= 20 else f" … (+{len(without_sector) - 20} more)"
            print(f"  e.g. {preview}{more}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
