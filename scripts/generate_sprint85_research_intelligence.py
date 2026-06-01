#!/usr/bin/env python3
"""Sprint 8.5 — generate executive research intelligence report pack."""

from __future__ import annotations

import argparse
import sys
from datetime import date

from app.core.config import get_settings
from app.db.repositories.factor_performance_metric_repository import FactorPerformanceMetricRepository
from app.db.repositories.research_intelligence_repository import (
    ResearchIntelligenceReportRepository,
    ResearchIntelligenceRunRepository,
)
from app.db.session import get_session_factory
from app.factor_analytics.constants import DEFAULT_HOLDOUT_START_DATE
from app.services.research_intelligence_service import ResearchIntelligenceService
from app.services.signal_validation_service import SignalValidationService


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe-code", default="NIFTY_500")
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--holdout-start-date", type=date.fromisoformat, default=DEFAULT_HOLDOUT_START_DATE)
    args = parser.parse_args()
    get_settings()
    with get_session_factory()() as db:
        from app.db.repositories.ranking_performance_repository import RankingPerformanceRepository
        from app.db.repositories.ranking_result_repository import RankingResultRepository
        from app.db.repositories.ranking_run_repository import RankingRunRepository
        from app.db.repositories.ranking_validation_repository import RankingValidationRepository
        from app.db.repositories.stock_repository import StockRepository
        from app.db.repositories.market_data_repository import MarketDataRepository

        validation_service = SignalValidationService(
            db,
            get_settings(),
            RankingRunRepository(db),
            RankingResultRepository(db),
            RankingPerformanceRepository(db),
            RankingValidationRepository(db),
            StockRepository(db),
            MarketDataRepository(db),
            None,
        )
        service = ResearchIntelligenceService(
            db,
            ResearchIntelligenceRunRepository(db),
            ResearchIntelligenceReportRepository(db),
            validation_service,
            FactorPerformanceMetricRepository(db),
        )
        result = service.generate_executive_pack(
            universe_code=args.universe_code,
            start_date=args.start_date,
            end_date=args.end_date,
            holdout_start_date=args.holdout_start_date,
        )
        print(f"run_id={result['run_id']} status={result['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
