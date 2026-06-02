#!/usr/bin/env python3
"""Run recovery phases (regime, factor IC, research intelligence) and print verification counts."""

from __future__ import annotations

import json
import sys
from datetime import date

from sqlalchemy import text

from app.db.session import get_session_factory
from app.schemas.daily_batch import DailyBatchPhaseFlags, DailyBatchRunCreateRequest
from app.services.daily_batch_service import DailyBatchService
from app.services.factor_predictive_power_service import FactorPredictivePowerService
from scripts.pipm_service_factory import build_pipm_services
from app.db.repositories.daily_batch_artifact_repository import DailyBatchArtifactRepository
from app.db.repositories.daily_batch_run_repository import DailyBatchRunRepository
from app.db.repositories.factor_performance_run_repository import FactorPerformanceRunRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.services.regime_analytics_service import RegimeAnalyticsService
from app.services.research_intelligence_service import ResearchIntelligenceService
from app.db.repositories.research_intelligence_repository import (
    ResearchIntelligenceReportRepository,
    ResearchIntelligenceRunRepository,
)
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.market_data_repository import MarketDataRepository
from app.core.config import get_settings


def _counts(db) -> dict[str, int]:
    rows = {}
    for table in (
        "factor_performance_metrics",
        "strategy_regime_performance",
        "research_intelligence_runs",
        "research_intelligence_reports",
    ):
        rows[table] = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
    return rows


def main() -> int:
    before = None
    Session = get_session_factory()
    with Session() as db:
        before = _counts(db)
        print("BEFORE", json.dumps(before))

        services = build_pipm_services(db)
        factor_metric_repo = services["factor_service"].metric_repo
        factor_service = FactorPredictivePowerService(
            db,
            factor_metric_repo,
            FactorPerformanceRunRepository(db),
            RankingValidationRepository(db),
            RankingRunRepository(db),
        )
        settings = get_settings()
        regime_service = RegimeAnalyticsService(
            db,
            settings,
            RegimeAnalyticsRepository(db),
            StockRepository(db),
            MarketDataRepository(db),
        )
        research_service = ResearchIntelligenceService(
            db,
            ResearchIntelligenceRunRepository(db),
            ResearchIntelligenceReportRepository(db),
            services["validation_service"],
            factor_metric_repo,
        )
        batch = DailyBatchService(
            db,
            market_data_service=services["market_data_service"],
            backtest_service=services["backtest_service"],
            validation_service=services["validation_service"],
            factor_service=factor_service,
            exit_service=services["exit_service"],
            regime_service=regime_service,
            research_intelligence_service=research_service,
            ranking_run_repo=RankingRunRepository(db),
            run_repo=DailyBatchRunRepository(db),
            artifact_repo=DailyBatchArtifactRepository(db),
        )
        request = DailyBatchRunCreateRequest(
            from_date=date(2026, 6, 1),
            force_from_date=True,
            phases=DailyBatchPhaseFlags(
                ingest=False,
                rankings=False,
                validation=False,
                regime_history=True,
                regime_performance=True,
                factor_ic=True,
                research_intelligence=True,
                exit_research=False,
            ),
        )
        response = batch.create_and_execute(request)
        print("RUN", json.dumps(response.model_dump(mode="json"), indent=2, default=str))

        after = _counts(db)
        print("AFTER", json.dumps(after))
        print("DELTA", json.dumps({k: after[k] - before[k] for k in after}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
