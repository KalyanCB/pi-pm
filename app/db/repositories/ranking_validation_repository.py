from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.ranking_validation_report import RankingValidationReport
from app.validation.constants import (
    VALIDATION_STATUS_COMPLETED,
    VALIDATION_STATUS_FAILED,
    VALIDATION_STATUS_PENDING,
)


class RankingValidationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_ranking_run_id(self, ranking_run_id: UUID) -> RankingValidationReport | None:
        return self.db.scalar(
            select(RankingValidationReport).where(
                RankingValidationReport.ranking_run_id == ranking_run_id
            )
        )

    def find_completed_by_validation_hash(
        self, validation_hash: str
    ) -> RankingValidationReport | None:
        return self.db.scalar(
            select(RankingValidationReport).where(
                RankingValidationReport.validation_hash == validation_hash,
                RankingValidationReport.status == VALIDATION_STATUS_COMPLETED,
            )
        )

    def create_pending(self, ranking_run_id: UUID) -> RankingValidationReport:
        report = RankingValidationReport(
            ranking_run_id=ranking_run_id,
            status=VALIDATION_STATUS_PENDING,
        )
        self.db.add(report)
        self.db.flush()
        return report

    def complete(
        self,
        report: RankingValidationReport,
        *,
        validation_hash: str | None,
        regime_label: str | None,
        trend_regime: str | None,
        vol_regime: str | None,
        status: str,
        horizon_metrics: dict,
        sample_summary: dict,
    ) -> RankingValidationReport:
        report.validation_hash = validation_hash
        report.regime_label = regime_label
        report.trend_regime = trend_regime
        report.vol_regime = vol_regime
        report.status = status
        report.horizon_metrics = horizon_metrics
        report.sample_summary = sample_summary
        report.computed_at = datetime.now(UTC)
        report.error_message = None
        self.db.flush()
        return report

    def fail(self, report: RankingValidationReport, error_message: str) -> RankingValidationReport:
        report.status = VALIDATION_STATUS_FAILED
        report.error_message = error_message
        report.validation_hash = None
        report.computed_at = datetime.now(UTC)
        self.db.flush()
        return report

    def list_completed_with_runs(
        self,
        universe_code: str | None = None,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
        start_date=None,
        end_date=None,
    ) -> list[RankingValidationReport]:
        return self.list_reports_with_runs(
            universe_code=universe_code,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            start_date=start_date,
            end_date=end_date,
            status=VALIDATION_STATUS_COMPLETED,
        )

    def list_reports_with_runs(
        self,
        universe_code: str | None = None,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
        start_date=None,
        end_date=None,
        status: str | None = None,
    ) -> list[RankingValidationReport]:
        from app.core.constants import RankingRunStatus
        from app.models.ranking_run import RankingRun

        stmt = (
            select(RankingValidationReport)
            .join(RankingRun, RankingRun.id == RankingValidationReport.ranking_run_id)
            .options(selectinload(RankingValidationReport.ranking_run))
            .where(RankingRun.status == RankingRunStatus.COMPLETED.value)
        )
        if status is not None:
            stmt = stmt.where(RankingValidationReport.status == status)
        if universe_code:
            stmt = stmt.where(RankingRun.universe_code == universe_code)
        if strategy_name:
            stmt = stmt.where(RankingRun.strategy_name == strategy_name)
        if strategy_version:
            stmt = stmt.where(RankingRun.strategy_version == strategy_version)
        if start_date:
            stmt = stmt.where(RankingRun.as_of_date >= start_date)
        if end_date:
            stmt = stmt.where(RankingRun.as_of_date <= end_date)
        stmt = stmt.order_by(RankingRun.as_of_date)
        return list(self.db.scalars(stmt).all())
