from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import ResearchIntelligenceRunStatus
from app.models.research_intelligence import ResearchIntelligenceReport, ResearchIntelligenceRun


class ResearchIntelligenceRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_running(
        self,
        *,
        report_type: str,
        universe_code: str,
        as_of_date_start,
        as_of_date_end,
        holdout_start_date,
        parameter_set: dict,
    ) -> ResearchIntelligenceRun:
        run = ResearchIntelligenceRun(
            status=ResearchIntelligenceRunStatus.RUNNING.value,
            report_type=report_type,
            universe_code=universe_code,
            as_of_date_start=as_of_date_start,
            as_of_date_end=as_of_date_end,
            holdout_start_date=holdout_start_date,
            parameter_set=parameter_set,
            started_at=datetime.now(UTC),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def complete(self, run: ResearchIntelligenceRun) -> ResearchIntelligenceRun:
        run.status = ResearchIntelligenceRunStatus.COMPLETED.value
        run.completed_at = datetime.now(UTC)
        self.db.flush()
        return run

    def fail(self, run: ResearchIntelligenceRun, error_message: str) -> ResearchIntelligenceRun:
        run.status = ResearchIntelligenceRunStatus.FAILED.value
        run.error_message = error_message
        run.completed_at = datetime.now(UTC)
        self.db.flush()
        return run


class ResearchIntelligenceReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_report(
        self,
        *,
        run_id: UUID,
        report_type: str,
        universe_code: str,
        payload: dict,
    ) -> ResearchIntelligenceReport:
        existing = self.db.scalar(
            select(ResearchIntelligenceReport).where(
                ResearchIntelligenceReport.run_id == run_id,
                ResearchIntelligenceReport.report_type == report_type,
            )
        )
        now = datetime.now(UTC)
        if existing is None:
            row = ResearchIntelligenceReport(
                run_id=run_id,
                report_type=report_type,
                universe_code=universe_code,
                payload=payload,
                generated_at=now,
            )
            self.db.add(row)
            self.db.flush()
            return row
        existing.payload = payload
        existing.generated_at = now
        self.db.flush()
        return existing

    def get_latest_run(self, *, universe_code: str) -> ResearchIntelligenceRun | None:
        return self.db.scalar(
            select(ResearchIntelligenceRun)
            .where(ResearchIntelligenceRun.universe_code == universe_code)
            .order_by(ResearchIntelligenceRun.completed_at.desc().nullslast())
            .limit(1)
        )

    def list_for_run(self, run_id: UUID) -> list[ResearchIntelligenceReport]:
        stmt = (
            select(ResearchIntelligenceReport)
            .where(ResearchIntelligenceReport.run_id == run_id)
            .order_by(ResearchIntelligenceReport.report_type)
        )
        return list(self.db.scalars(stmt).all())

    def get_latest(self, *, report_type: str, universe_code: str) -> ResearchIntelligenceReport | None:
        stmt = (
            select(ResearchIntelligenceReport)
            .where(
                ResearchIntelligenceReport.report_type == report_type,
                ResearchIntelligenceReport.universe_code == universe_code,
            )
            .order_by(ResearchIntelligenceReport.generated_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)
