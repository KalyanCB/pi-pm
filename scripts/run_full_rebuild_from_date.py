#!/usr/bin/env python3
"""Re-ingest market data from a start date and run the full daily-batch recompute pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from app.core.config import get_settings
from app.db.repositories.daily_batch_artifact_repository import DailyBatchArtifactRepository
from app.db.repositories.daily_batch_run_repository import DailyBatchRunRepository
from app.db.repositories.factor_performance_run_repository import FactorPerformanceRunRepository
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.db.repositories.research_intelligence_repository import (
    ResearchIntelligenceReportRepository,
    ResearchIntelligenceRunRepository,
)
from app.db.repositories.stock_repository import StockRepository
from app.db.session import get_session_factory
from app.schemas.daily_batch import DailyBatchPhaseFlags, DailyBatchRunCreateRequest
from app.services.daily_batch_service import DailyBatchService
from app.services.factor_predictive_power_service import FactorPredictivePowerService
from app.services.regime_analytics_service import RegimeAnalyticsService
from app.services.research_intelligence_service import ResearchIntelligenceService
from scripts.pipm_service_factory import build_pipm_services


def _build_daily_batch(db) -> DailyBatchService:
    services = build_pipm_services(db)
    settings = get_settings()
    regime_service = RegimeAnalyticsService(
        db,
        settings,
        RegimeAnalyticsRepository(db),
        StockRepository(db),
        MarketDataRepository(db),
    )
    factor_service = FactorPredictivePowerService(
        db,
        services["factor_service"].metric_repo,
        FactorPerformanceRunRepository(db),
        RankingValidationRepository(db),
        RankingRunRepository(db),
    )
    research_service = ResearchIntelligenceService(
        db,
        ResearchIntelligenceRunRepository(db),
        ResearchIntelligenceReportRepository(db),
        services["validation_service"],
        factor_service.metric_repo,
    )
    return DailyBatchService(
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-date",
        type=date.fromisoformat,
        default=date(2024, 6, 1),
        help="First calendar date for ingest + recompute window (default: 2024-06-01)",
    )
    parser.add_argument(
        "--target-date",
        type=date.fromisoformat,
        default=None,
        help="Last trading day to process (default: latest benchmark session)",
    )
    parser.add_argument(
        "--holdout-start",
        type=date.fromisoformat,
        default=None,
        help="Holdout split for factor/exit analytics (default: same as --from-date)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Plan only, no execution")
    parser.add_argument("--output", type=Path, default=Path("docs/full-rebuild-from-date.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    holdout = args.holdout_start or args.from_date

    request = DailyBatchRunCreateRequest(
        from_date=args.from_date,
        target_date=args.target_date,
        force_from_date=True,
        force_recompute=True,
        force_regenerate_rankings=True,
        force_ingest=True,
        holdout_start_date=holdout,
        assume_session_done=True,
        allow_partial_ingest=True,
        phases=DailyBatchPhaseFlags(
            ingest=True,
            rankings=True,
            validation=True,
            regime_history=True,
            regime_performance=True,
            factor_ic=True,
            research_intelligence=True,
            exit_research=True,
        ),
        dry_run=args.dry_run,
    )

    Session = get_session_factory()
    with Session() as db:
        batch = _build_daily_batch(db)
        print(
            f"Full rebuild: ingest since {args.from_date}, recompute through "
            f"{args.target_date or 'latest'}, holdout_start={holdout}, dry_run={args.dry_run}"
        )
        response = batch.create_and_execute(request)
        payload = response.model_dump(mode="json")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        print(json.dumps(payload, indent=2, default=str))
        print(f"\nWrote {args.output}")
        if response.status != "completed":
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
