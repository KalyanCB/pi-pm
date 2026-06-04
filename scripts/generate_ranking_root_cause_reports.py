#!/usr/bin/env python3
"""Generate all five ranking calibration research docs (read-only DB)."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from app.core.constants import UNIVERSE_NIFTY_500
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.session import get_session_factory
from app.outcome_attribution.constants import REGIME_LABEL_ALL
from app.ranking_research.constants import REGIME_LABELS
from app.ranking_research.data_loader import RankingResearchDataLoader
from app.ranking_research.models import RankingResearchConfig
from app.ranking_research.reports import (
    build_factor_reliability_markdown,
    build_rank_reliability_markdown,
    build_ranking_calibration_root_cause_markdown,
    build_regime_rank_reliability_markdown,
    build_score_compression_markdown,
)
from app.ranking_research.score_compression import build_score_compression_report
from app.ranking_research.service import RankReliabilityService

DEFAULT_START = date(2024, 6, 1)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate rank/factor/regime/score/root-cause research docs"
    )
    parser.add_argument("--universe-code", default=UNIVERSE_NIFTY_500)
    parser.add_argument("--start-date", type=_parse_date, default=DEFAULT_START)
    parser.add_argument("--end-date", type=_parse_date, default=date.today())
    parser.add_argument("--strategies", default="breakout_v1,momentum_v1")
    parser.add_argument(
        "--rank-reliability-output",
        type=Path,
        default=Path("docs/rank-reliability-report.md"),
    )
    parser.add_argument(
        "--factor-output",
        type=Path,
        default=Path("docs/factor-reliability-report.md"),
    )
    parser.add_argument(
        "--regime-output",
        type=Path,
        default=Path("docs/regime-rank-reliability-report.md"),
    )
    parser.add_argument(
        "--compression-output",
        type=Path,
        default=Path("docs/score-compression-analysis.md"),
    )
    parser.add_argument(
        "--root-cause-output",
        type=Path,
        default=Path("docs/ranking-calibration-root-cause.md"),
    )
    args = parser.parse_args()

    config = RankingResearchConfig(
        universe_code=args.universe_code,
        start_date=args.start_date,
        end_date=args.end_date,
        strategy_names=tuple(s.strip() for s in args.strategies.split(",") if s.strip()),
    )

    outputs = (
        args.rank_reliability_output,
        args.factor_output,
        args.regime_output,
        args.compression_output,
        args.root_cause_output,
    )
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)

    session_factory = get_session_factory()
    db = session_factory()
    try:
        loader = RankingResearchDataLoader(
            db,
            StockRepository(db),
            MarketDataRepository(db),
        )
        observations, benchmarks = loader.load_enriched(config)
        benchmark_by_run = {b.run_id: b for b in benchmarks}
        reliability = RankReliabilityService().compute(config, observations, benchmarks)
        compression = build_score_compression_report(
            observations=observations,
            benchmark_by_run=benchmark_by_run,
            strategy_names=config.strategy_names,
            regime_labels=(REGIME_LABEL_ALL, *REGIME_LABELS),
        )

        args.rank_reliability_output.write_text(
            build_rank_reliability_markdown(reliability),
            encoding="utf-8",
        )
        args.factor_output.write_text(
            build_factor_reliability_markdown(reliability),
            encoding="utf-8",
        )
        args.regime_output.write_text(
            build_regime_rank_reliability_markdown(reliability),
            encoding="utf-8",
        )
        args.compression_output.write_text(
            build_score_compression_markdown(reliability, compression),
            encoding="utf-8",
        )
        args.root_cause_output.write_text(
            build_ranking_calibration_root_cause_markdown(
                reliability,
                compression,
                reliability_path=str(args.rank_reliability_output),
                factor_path=str(args.factor_output),
                regime_path=str(args.regime_output),
                compression_path=str(args.compression_output),
            ),
            encoding="utf-8",
        )

        print(f"Runs analyzed: {reliability.ranked_run_count}")
        for path in outputs:
            print(f"Wrote {path}")
        print("")
        print("Run: python scripts/generate_ranking_root_cause_reports.py")
        print("Headlines: see docs/ranking-calibration-root-cause.md")
    finally:
        db.close()


if __name__ == "__main__":
    main()
