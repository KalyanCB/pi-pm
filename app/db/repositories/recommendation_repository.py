from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import RecommendationAction, RecommendationRunStatus
from app.models.recommendation import (
    RecommendationApproval,
    RecommendationConfig,
    RecommendationOutcome,
    RecommendationResult,
    RecommendationRun,
)


class RecommendationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Config ──────────────────────────────────────────────────────────────

    def get_active_config(self) -> RecommendationConfig | None:
        return self.db.scalar(
            select(RecommendationConfig)
            .where(RecommendationConfig.is_active.is_(True))
            .order_by(RecommendationConfig.created_at.desc())
            .limit(1)
        )

    def upsert_config(
        self, config_version: str, config_blob: dict[str, Any]
    ) -> RecommendationConfig:
        existing = self.db.scalar(
            select(RecommendationConfig).where(
                RecommendationConfig.config_version == config_version
            )
        )
        if existing:
            existing.config_blob = config_blob
            self.db.flush()
            return existing
        cfg = RecommendationConfig(config_version=config_version, config_blob=config_blob)
        self.db.add(cfg)
        self.db.flush()
        return cfg

    # ── Runs ─────────────────────────────────────────────────────────────────

    def create_run(
        self,
        *,
        ranking_run_id: UUID,
        strategy_name: str,
        universe_code: str,
        as_of_date: date,
        config_version: str,
        config_snapshot: dict[str, Any],
        regime_snapshot: dict[str, Any] | None,
        input_hash: str,
    ) -> RecommendationRun:
        run = RecommendationRun(
            ranking_run_id=ranking_run_id,
            strategy_name=strategy_name,
            universe_code=universe_code,
            as_of_date=as_of_date,
            status=RecommendationRunStatus.PENDING.value,
            config_version=config_version,
            config_snapshot=config_snapshot,
            regime_snapshot=regime_snapshot,
            input_hash=input_hash,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def complete_run(self, run: RecommendationRun) -> RecommendationRun:
        run.status = RecommendationRunStatus.COMPLETED.value
        run.completed_at = datetime.now(UTC)
        self.db.flush()
        return run

    def fail_run(self, run: RecommendationRun, error: str) -> RecommendationRun:
        run.status = RecommendationRunStatus.FAILED.value
        run.error_message = error
        run.completed_at = datetime.now(UTC)
        self.db.flush()
        return run

    def get_runs_by_date(self, as_of_date: date) -> list[RecommendationRun]:
        """All completed runs for a given date, one per strategy."""
        return list(
            self.db.scalars(
                select(RecommendationRun).where(
                    RecommendationRun.as_of_date == as_of_date,
                    RecommendationRun.status == RecommendationRunStatus.COMPLETED.value,
                )
            ).all()
        )

    def get_latest_run_date(self) -> date | None:
        """Most recent completed recommendation run date."""
        return self.db.scalar(
            select(func.max(RecommendationRun.as_of_date)).where(
                RecommendationRun.status == RecommendationRunStatus.COMPLETED.value,
            )
        )

    def list_available_dates(self, strategy_name: str | None = None) -> list[date]:
        """Distinct completed recommendation run dates, newest first."""
        q = (
            select(RecommendationRun.as_of_date)
            .where(RecommendationRun.status == RecommendationRunStatus.COMPLETED.value)
            .distinct()
            .order_by(RecommendationRun.as_of_date.desc())
        )
        if strategy_name:
            q = q.where(RecommendationRun.strategy_name == strategy_name)
        return list(self.db.scalars(q).all())

    def get_run_by_ranking_run_id(self, ranking_run_id: UUID) -> RecommendationRun | None:
        return self.db.scalar(
            select(RecommendationRun).where(RecommendationRun.ranking_run_id == ranking_run_id)
        )

    def get_latest_run_by_strategy(
        self, strategy_name: str, as_of_date: date | None = None
    ) -> RecommendationRun | None:
        q = (
            select(RecommendationRun)
            .where(
                RecommendationRun.strategy_name == strategy_name,
                RecommendationRun.status == RecommendationRunStatus.COMPLETED.value,
            )
            .order_by(RecommendationRun.as_of_date.desc(), RecommendationRun.created_at.desc())
            .limit(1)
        )
        if as_of_date is not None:
            q = q.where(RecommendationRun.as_of_date == as_of_date)
        return self.db.scalar(q)

    # ── Results ──────────────────────────────────────────────────────────────

    def bulk_insert_results(self, results: list[RecommendationResult]) -> None:
        for r in results:
            self.db.add(r)
        self.db.flush()

    def get_results(
        self,
        run_id: UUID,
        action_filter: list[str] | None = None,
    ) -> list[RecommendationResult]:
        q = select(RecommendationResult).where(RecommendationResult.recommendation_run_id == run_id)
        if action_filter:
            q = q.where(RecommendationResult.action.in_(action_filter))
        return list(self.db.scalars(q).all())

    def get_result_by_symbol(self, run_id: UUID, stock_id: UUID) -> RecommendationResult | None:
        return self.db.scalar(
            select(RecommendationResult).where(
                RecommendationResult.recommendation_run_id == run_id,
                RecommendationResult.stock_id == stock_id,
            )
        )

    def get_approval_queue(self) -> list[RecommendationResult]:
        """BUY + EXIT_APPROVED results in CANDIDATE lifecycle state."""
        return list(
            self.db.scalars(
                select(RecommendationResult).where(
                    RecommendationResult.action.in_(
                        [RecommendationAction.BUY, RecommendationAction.EXIT_APPROVED]
                    ),
                    RecommendationResult.lifecycle_state == "CANDIDATE",
                )
            ).all()
        )

    # ── Approvals ────────────────────────────────────────────────────────────

    def create_approval(
        self,
        *,
        recommendation_result_id: UUID,
        approval_type: str,
        decision: str,
        actor_id: str,
        note: str | None = None,
        idempotency_key: str | None = None,
    ) -> RecommendationApproval:
        approval = RecommendationApproval(
            recommendation_result_id=recommendation_result_id,
            approval_type=approval_type,
            decision=decision,
            actor_id=actor_id,
            note=note,
            decided_at=datetime.now(UTC),
            idempotency_key=idempotency_key,
        )
        self.db.add(approval)
        self.db.flush()
        return approval

    # ── Outcomes ─────────────────────────────────────────────────────────────

    def create_outcome(
        self,
        *,
        recommendation_result_id: UUID,
        entry_date: date,
        entry_price: float,
    ) -> RecommendationOutcome:
        outcome = RecommendationOutcome(
            recommendation_result_id=recommendation_result_id,
            outcome_status="OPEN",
            entry_date=entry_date,
            entry_price=entry_price,
        )
        self.db.add(outcome)
        self.db.flush()
        return outcome
