#!/usr/bin/env python3
"""Sprint 8.3 — backfill exit research metrics from validated ranking signals."""

from __future__ import annotations

import argparse
import sys
from datetime import date

from app.core.config import get_settings
from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_BREAKOUT_V1_VERSION,
)
from app.db.repositories.exit_research_metric_repository import ExitResearchMetricRepository
from app.db.repositories.exit_research_run_repository import ExitResearchRunRepository
from app.db.session import get_session_factory
from app.factor_analytics.constants import DEFAULT_HOLDOUT_START_DATE
from app.services.exit_research_service import ExitResearchService


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe-code", default="NIFTY_500")
    parser.add_argument("--strategy-name", default=RANKING_STRATEGY_BREAKOUT_V1)
    parser.add_argument("--strategy-version", default=RANKING_STRATEGY_BREAKOUT_V1_VERSION)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--holdout-start-date", type=date.fromisoformat, default=DEFAULT_HOLDOUT_START_DATE)
    parser.add_argument("--force-recompute", action="store_true")
    args = parser.parse_args()
    get_settings()
    with get_session_factory()() as db:
        service = ExitResearchService(
            db,
            ExitResearchRunRepository(db),
            ExitResearchMetricRepository(db),
        )
        run = service.backfill(
            strategy_name=args.strategy_name,
            strategy_version=args.strategy_version,
            universe_code=args.universe_code,
            start_date=args.start_date,
            end_date=args.end_date,
            holdout_start_date=args.holdout_start_date,
            force_recompute=args.force_recompute,
        )
        print(
            f"run_id={run.id} status={run.status} "
            f"signals={run.signals_processed} metrics={run.metrics_written}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
