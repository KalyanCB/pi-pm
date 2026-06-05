#!/usr/bin/env python3
"""One-shot deterministic research platform recovery (regime, factor IC, research intelligence)."""

from __future__ import annotations

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
from app.factor_analytics.constants import DEFAULT_HOLDOUT_START_DATE
from app.ops.daily_batch.evidence_windows import (
    list_completed_validation_dates,
    resolve_quant_evidence_window,
)
from app.ops.research_platform_metrics import snapshot_table_counts
from app.schemas.daily_batch import DailyBatchPhaseFlags, DailyBatchRunCreateRequest
from app.services.daily_batch_service import DailyBatchService
from app.services.factor_predictive_power_service import FactorPredictivePowerService
from app.services.regime_analytics_service import RegimeAnalyticsService
from app.services.research_intelligence_service import ResearchIntelligenceService
from scripts.pipm_service_factory import build_pipm_services


def main() -> int:
    holdout = DEFAULT_HOLDOUT_START_DATE
    target = date(2026, 6, 2)
    universe = "NIFTY_500"
    benchmark = "^NSEI"

    Session = get_session_factory()
    with Session() as db:
        before = snapshot_table_counts(db)
        print("BEFORE", json.dumps(before, indent=2))

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
            universe_code=universe,
            benchmark_symbol=benchmark,
            target_date=target,
            from_date=holdout,
            force_from_date=True,
            holdout_start_date=holdout,
            phases=DailyBatchPhaseFlags(
                ingest=False,
                rankings=False,
                validation=False,
                regime_history=True,
                regime_performance=True,
                factor_ic=False,
                research_intelligence=False,
                exit_research=False,
            ),
        )
        response = batch.create_and_execute(request)
        print("BATCH", json.dumps(response.model_dump(mode="json"), indent=2, default=str))

        completed_dates = []
        for strategy_name, strategy_version in (("breakout_v1", "1.0.0"), ("momentum_v1", "1.0.0")):
            completed_dates.extend(
                list_completed_validation_dates(
                    db,
                    universe_code=universe,
                    strategy_name=strategy_name,
                    strategy_version=strategy_version,
                    start_date=holdout,
                    end_date=target,
                )
            )
        window = resolve_quant_evidence_window(
            plan_from_date=holdout,
            target_trading_day=target,
            holdout_start_date=holdout,
            completed_validation_dates=sorted(set(completed_dates)),
        )
        print("EVIDENCE_WINDOW", window)

        phase_extra: dict = {}
        if window:
            start, end = window
            for strategy_name, strategy_version in (
                ("breakout_v1", "1.0.0"),
                ("momentum_v1", "1.0.0"),
            ):
                fic = factor_service.backfill(
                    strategy_name=strategy_name,
                    strategy_version=strategy_version,
                    universe_code=universe,
                    start_date=start,
                    end_date=end,
                    holdout_start_date=holdout,
                    force_recompute=False,
                )
                phase_extra.setdefault("factor_ic", {})[strategy_name] = {
                    "run_id": str(fic.id),
                    "metrics_written": fic.metrics_written,
                    "reports_processed": fic.reports_processed,
                }
            intel = research_service.generate_executive_pack(
                universe_code=universe,
                start_date=start,
                end_date=end,
                holdout_start_date=holdout,
                persist=True,
            )
            phase_extra["research_intelligence"] = intel

        after = snapshot_table_counts(db)
        print("AFTER", json.dumps(after, indent=2))
        print("DELTA", json.dumps({k: after[k] - before[k] for k in after}))
        print("EXTRA", json.dumps(phase_extra, indent=2, default=str))

        out = Path("docs/research-platform-recovery-metrics.json")
        out.write_text(
            json.dumps(
                {"before": before, "after": after, "batch": response.model_dump(mode="json")},
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
