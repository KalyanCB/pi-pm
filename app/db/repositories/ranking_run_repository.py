from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.constants import RankingRunStatus
from app.models.ranking_run import RankingRun


class RankingRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_pending(
        self,
        strategy_name: str,
        strategy_version: str,
        as_of_date,
        universe_code: str,
        benchmark_symbol: str,
        filter_config_hash: str,
        normalization_method: str,
    ) -> RankingRun:
        run = RankingRun(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            as_of_date=as_of_date,
            inputs_hash=None,
            universe_code=universe_code,
            benchmark_symbol=benchmark_symbol,
            filter_config_hash=filter_config_hash,
            normalization_method=normalization_method,
            status=RankingRunStatus.PENDING.value,
            started_at=datetime.now(UTC),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def complete(self, run: RankingRun, inputs_hash: str, metadata: dict | None) -> RankingRun:
        run.inputs_hash = inputs_hash
        run.metadata_ = metadata or {}
        run.status = RankingRunStatus.COMPLETED.value
        run.completed_at = datetime.now(UTC)
        self.db.flush()
        return run

    def fail(self, run: RankingRun, error_message: str) -> RankingRun:
        run.status = RankingRunStatus.FAILED.value
        run.error_message = error_message
        run.inputs_hash = None
        run.completed_at = datetime.now(UTC)
        self.db.flush()
        return run

    def get_by_id(self, run_id: UUID) -> RankingRun | None:
        return self.db.scalar(
            select(RankingRun)
            .options(selectinload(RankingRun.results))
            .where(RankingRun.id == run_id)
        )

    def get_latest(
        self,
        universe_code: str | None = None,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
    ) -> RankingRun | None:
        stmt = (
            select(RankingRun)
            .options(selectinload(RankingRun.results))
            .where(RankingRun.status == RankingRunStatus.COMPLETED.value)
            .order_by(RankingRun.completed_at.desc())
        )
        if universe_code:
            stmt = stmt.where(RankingRun.universe_code == universe_code)
        if strategy_name:
            stmt = stmt.where(RankingRun.strategy_name == strategy_name)
        if strategy_version:
            stmt = stmt.where(RankingRun.strategy_version == strategy_version)
        return self.db.scalar(stmt.limit(1))

    def find_completed_by_inputs_hash(self, inputs_hash: str) -> RankingRun | None:
        return self.db.scalar(
            select(RankingRun)
            .options(selectinload(RankingRun.results))
            .where(
                RankingRun.inputs_hash == inputs_hash,
                RankingRun.status == RankingRunStatus.COMPLETED.value,
            )
            .order_by(RankingRun.completed_at.desc())
            .limit(1)
        )
