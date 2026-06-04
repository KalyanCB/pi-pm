#!/usr/bin/env python3
"""Generate outcome attribution report from ranking runs and forward return snapshots."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from app.core.constants import UNIVERSE_NIFTY_500
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.session import get_session_factory
from app.outcome_attribution.data_loader import OutcomeAttributionDataLoader
from app.outcome_attribution.models import OutcomeAttributionConfig
from app.outcome_attribution.reports import build_markdown_report
from app.outcome_attribution.service import OutcomeAttributionService

DEFAULT_OUTPUT = Path("docs/outcome-attribution-report.md")
DEFAULT_START = date(2024, 6, 1)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate outcome attribution analytics report")
    parser.add_argument("--universe-code", default=UNIVERSE_NIFTY_500)
    parser.add_argument("--start-date", type=_parse_date, default=DEFAULT_START)
    parser.add_argument("--end-date", type=_parse_date, default=date.today())
    parser.add_argument(
        "--strategies",
        default="breakout_v1,momentum_v1",
        help="Comma-separated strategy names",
    )
    parser.add_argument("--strategy-version", default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    config = OutcomeAttributionConfig(
        universe_code=args.universe_code,
        start_date=args.start_date,
        end_date=args.end_date,
        strategy_names=tuple(s.strip() for s in args.strategies.split(",") if s.strip()),
        strategy_version=args.strategy_version,
    )

    session_factory = get_session_factory()
    db = session_factory()
    try:
        loader = OutcomeAttributionDataLoader(
            db,
            StockRepository(db),
            MarketDataRepository(db),
        )
        observations, benchmarks = loader.load(config)
        report = OutcomeAttributionService().compute(config, observations, benchmarks)
        markdown = build_markdown_report(report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
        print(f"Wrote {args.output} ({report.ranked_run_count} runs, verdict={report.verdict})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
