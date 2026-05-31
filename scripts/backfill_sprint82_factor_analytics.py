#!/usr/bin/env python3
"""Sprint 8.2 — backfill factor predictive power analytics from ranking traceability."""

from __future__ import annotations

import argparse
import sys
from datetime import date

from app.core.config import get_settings
from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_BREAKOUT_V1_VERSION,
)
from app.db.repositories.factor_performance_metric_repository import (
    FactorPerformanceMetricRepository,
)
from app.db.repositories.factor_performance_run_repository import FactorPerformanceRunRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.session import get_session_factory
from app.factor_analytics.constants import DEFAULT_HOLDOUT_START_DATE
from app.services.factor_predictive_power_service import FactorPredictivePowerService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe-code", default="NIFTY_500")
    parser.add_argument("--strategy-name", default=RANKING_STRATEGY_BREAKOUT_V1)
    parser.add_argument("--strategy-version", default=RANKING_STRATEGY_BREAKOUT_V1_VERSION)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--holdout-start-date",
        type=date.fromisoformat,
        default=DEFAULT_HOLDOUT_START_DATE,
    )
    parser.add_argument("--force-recompute", action="store_true")
    parser.add_argument("--skip-daily-metrics", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    get_settings()

    if args.dry_run:
        print(
            f"Would backfill {args.strategy_name}@{args.strategy_version} "
            f"universe={args.universe_code} "
            f"{args.start_date}..{args.end_date} holdout={args.holdout_start_date}"
        )
        return 0

    session_factory = get_session_factory()
    with session_factory() as db:
        service = FactorPredictivePowerService(
            db,
            FactorPerformanceMetricRepository(db),
            FactorPerformanceRunRepository(db),
            RankingValidationRepository(db),
            RankingRunRepository(db),
        )
        run = service.backfill(
            strategy_name=args.strategy_name,
            strategy_version=args.strategy_version,
            universe_code=args.universe_code,
            start_date=args.start_date,
            end_date=args.end_date,
            holdout_start_date=args.holdout_start_date,
            write_daily_metrics=not args.skip_daily_metrics,
            force_recompute=args.force_recompute,
        )
        print(
            f"run_id={run.id} status={run.status} "
            f"reports_processed={run.reports_processed} metrics_written={run.metrics_written}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
