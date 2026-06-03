#!/usr/bin/env python3
"""Run calibrated vs production top-20 backtest (research only)."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from app.core.constants import UNIVERSE_NIFTY_500
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.session import get_session_factory
from app.ranking_research.backtest import run_calibrated_backtest
from app.ranking_research.calibration import build_calibration_tables
from app.ranking_research.data_loader import RankingResearchDataLoader
from app.ranking_research.models import RankingResearchConfig
from app.ranking_research.reports import (
    build_backtest_markdown,
    build_master_research_markdown,
    build_rank_reliability_markdown,
    build_regime_rank_reliability_markdown,
)
from app.ranking_research.service import RankReliabilityService

DEFAULT_REGIME_OUTPUT = Path("docs/regime-rank-reliability-report.md")

DEFAULT_BACKTEST_OUTPUT = Path("docs/calibrated-ranking-backtest.md")
DEFAULT_MASTER_OUTPUT = Path("docs/calibrated-ranking-research.md")
DEFAULT_RELIABILITY_OUTPUT = Path("docs/rank-reliability-report.md")
DEFAULT_START = date(2024, 6, 1)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrated ranking backtest (research)")
    parser.add_argument("--universe-code", default=UNIVERSE_NIFTY_500)
    parser.add_argument("--start-date", type=_parse_date, default=DEFAULT_START)
    parser.add_argument("--end-date", type=_parse_date, default=date.today())
    parser.add_argument("--strategies", default="breakout_v1,momentum_v1")
    parser.add_argument("--backtest-output", type=Path, default=DEFAULT_BACKTEST_OUTPUT)
    parser.add_argument("--master-output", type=Path, default=DEFAULT_MASTER_OUTPUT)
    parser.add_argument("--reliability-output", type=Path, default=DEFAULT_RELIABILITY_OUTPUT)
    parser.add_argument("--skip-reliability", action="store_true")
    args = parser.parse_args()

    config = RankingResearchConfig(
        universe_code=args.universe_code,
        start_date=args.start_date,
        end_date=args.end_date,
        strategy_names=tuple(s.strip() for s in args.strategies.split(",") if s.strip()),
    )

    session_factory = get_session_factory()
    db = session_factory()
    try:
        loader = RankingResearchDataLoader(
            db,
            StockRepository(db),
            MarketDataRepository(db),
        )
        observations, benchmarks = loader.load_enriched(config)
        tables = build_calibration_tables(observations, benchmarks)
        backtest = run_calibrated_backtest(config, observations, benchmarks, tables=tables)

        args.backtest_output.parent.mkdir(parents=True, exist_ok=True)
        args.backtest_output.write_text(
            build_backtest_markdown(backtest, tables),
            encoding="utf-8",
        )

        reliability_report = RankReliabilityService().compute(
            config, observations, benchmarks
        )
        if not args.skip_reliability:
            args.reliability_output.write_text(
                build_rank_reliability_markdown(reliability_report),
                encoding="utf-8",
            )
        DEFAULT_REGIME_OUTPUT.write_text(
            build_regime_rank_reliability_markdown(reliability_report),
            encoding="utf-8",
        )
        args.master_output.write_text(
            build_master_research_markdown(
                reliability_path=str(args.reliability_output),
                regime_path=str(DEFAULT_REGIME_OUTPUT),
                backtest_path=str(args.backtest_output),
                reliability=reliability_report,
                report=backtest,
                tables=tables,
            ),
            encoding="utf-8",
        )
        print(
            f"Backtest verdict={backtest.verdict} "
            f"(mono={backtest.meets_monotonicity}, sharpe={backtest.meets_sharpe})"
        )
        print(f"Wrote {args.backtest_output}, {args.master_output}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
