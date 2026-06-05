from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.db.repositories.factor_performance_metric_repository import (
    FactorPerformanceMetricRepository,
)
from app.db.repositories.research_intelligence_repository import (
    ResearchIntelligenceReportRepository,
    ResearchIntelligenceRunRepository,
)
from app.factor_analytics.constants import DEFAULT_HOLDOUT_START_DATE
from app.services.signal_validation_service import SignalValidationService
from app.workspace_research_reporting.builder import ResearchIntelligenceBuilder


class ResearchIntelligenceService:
    REPORT_TYPES = (
        "coverage_statistics",
        "ranking_statistics",
        "ic_by_strategy",
        "spread_by_strategy",
        "ic_by_regime",
        "spread_by_regime",
        "factor_contribution_analysis",
        "current_top_20_candidates",
        "executive_committee_summary",
    )

    def __init__(
        self,
        db: Session,
        run_repo: ResearchIntelligenceRunRepository,
        report_repo: ResearchIntelligenceReportRepository,
        validation_service: SignalValidationService,
        factor_metric_repo: FactorPerformanceMetricRepository,
    ) -> None:
        self.db = db
        self.run_repo = run_repo
        self.report_repo = report_repo
        self.builder = ResearchIntelligenceBuilder(db, validation_service, factor_metric_repo)

    def generate_executive_pack(
        self,
        *,
        universe_code: str,
        start_date: date,
        end_date: date,
        holdout_start_date: date = DEFAULT_HOLDOUT_START_DATE,
        persist: bool = True,
    ) -> dict:
        run = self.run_repo.create_running(
            report_type="executive_pack",
            universe_code=universe_code,
            as_of_date_start=start_date,
            as_of_date_end=end_date,
            holdout_start_date=holdout_start_date,
            parameter_set={},
        )
        try:
            reports = {
                "coverage_statistics": self.builder.build_coverage_statistics(
                    universe_code=universe_code, start_date=start_date, end_date=end_date
                ),
                "ranking_statistics": self.builder.build_ranking_statistics(
                    universe_code=universe_code, start_date=start_date, end_date=end_date
                ),
            }
            strategy_block = self.builder.build_ic_spread_by_strategy(
                universe_code=universe_code, start_date=start_date, end_date=end_date
            )
            reports["ic_by_strategy"] = strategy_block["ic_by_strategy"]
            reports["spread_by_strategy"] = strategy_block["spread_by_strategy"]
            regime_block = self.builder.build_ic_spread_by_regime(
                universe_code=universe_code,
                strategy_name="breakout_v1",
                start_date=start_date,
                end_date=end_date,
            )
            reports["ic_by_regime"] = regime_block["ic_by_regime"]
            reports["spread_by_regime"] = regime_block["spread_by_regime"]
            reports["factor_contribution_analysis"] = (
                self.builder.build_factor_contribution_analysis(universe_code=universe_code)
            )
            reports["current_top_20_candidates"] = self.builder.build_top_20_candidates(
                universe_code=universe_code
            )
            executive = self.builder.build_executive_summary(
                universe_code=universe_code,
                start_date=start_date,
                end_date=end_date,
                holdout_start_date=holdout_start_date,
            )
            reports["executive_committee_summary"] = executive

            if persist:
                for report_type, payload in reports.items():
                    self.report_repo.upsert_report(
                        run_id=run.id,
                        report_type=report_type,
                        universe_code=universe_code,
                        payload=payload,
                    )
            self.run_repo.complete(run)
            self.db.commit()
            return {"run_id": str(run.id), "status": "completed", "reports": reports}
        except Exception as exc:
            self.run_repo.fail(run, str(exc))
            self.db.commit()
            raise

    def get_report(self, report_type: str, *, universe_code: str) -> dict | None:
        row = self.report_repo.get_latest(report_type=report_type, universe_code=universe_code)
        return row.payload if row else None
