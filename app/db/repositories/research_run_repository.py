from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.constants import ResearchRunStatus
from app.models.args import ResearchRun


class ResearchRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        trigger_mode: str,
        universe_code: str,
        strategy_name: str,
        strategy_version: str,
        as_of_date,
        top_n: int,
        committee_codes: list[str],
        config_snapshot: dict,
        ranking_run_ids: list[str],
    ) -> ResearchRun:
        now = datetime.now(UTC)
        run = ResearchRun(
            status=ResearchRunStatus.PENDING.value,
            trigger_mode=trigger_mode,
            universe_code=universe_code,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            as_of_date=as_of_date,
            top_n=top_n,
            committee_codes=committee_codes,
            config_snapshot=config_snapshot,
            ranking_run_ids=ranking_run_ids,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def get_by_id(self, run_id: UUID) -> ResearchRun | None:
        return self.db.scalar(
            select(ResearchRun)
            .options(
                selectinload(ResearchRun.packets),
                selectinload(ResearchRun.committee_reviews),
                selectinload(ResearchRun.cro_reviews),
                selectinload(ResearchRun.governance_reports),
            )
            .where(ResearchRun.id == run_id)
        )

    def get_latest(
        self,
        *,
        universe_code: str | None = None,
        strategy_name: str | None = None,
        as_of_date=None,
    ) -> ResearchRun | None:
        stmt = (
            select(ResearchRun)
            .where(ResearchRun.status == ResearchRunStatus.COMPLETED.value)
            .order_by(ResearchRun.completed_at.desc())
        )
        if universe_code:
            stmt = stmt.where(ResearchRun.universe_code == universe_code)
        if strategy_name:
            stmt = stmt.where(ResearchRun.strategy_name == strategy_name)
        if as_of_date is not None:
            stmt = stmt.where(ResearchRun.as_of_date == as_of_date)
        return self.db.scalar(stmt.limit(1))

    def mark_running(self, run: ResearchRun, *, phase: str) -> ResearchRun:
        run.status = ResearchRunStatus.RUNNING.value
        run.phase = phase
        run.updated_at = datetime.now(UTC)
        self.db.flush()
        return run

    def complete(
        self,
        run: ResearchRun,
        *,
        status: str = ResearchRunStatus.COMPLETED.value,
        phase: str = "completed",
        error_message: str | None = None,
    ) -> ResearchRun:
        now = datetime.now(UTC)
        run.status = status
        run.phase = phase
        run.completed_at = now
        run.updated_at = now
        run.error_message = error_message
        if run.started_at:
            run.duration_seconds = (now - run.started_at).total_seconds()
        self.db.flush()
        return run
