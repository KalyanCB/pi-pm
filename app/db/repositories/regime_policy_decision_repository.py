from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.regime_policy import RegimePolicyDecision


class RegimePolicyDecisionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        policy_config_id: UUID,
        ranking_run_id: UUID | None,
        validation_report_id: UUID | None,
        as_of_date,
        regime_label: str | None,
        action: str,
        size_multiplier: float,
        decile_filter: int | None,
        reason: str,
        experiment_run_id: UUID | None = None,
    ) -> RegimePolicyDecision:
        decision = RegimePolicyDecision(
            policy_config_id=policy_config_id,
            ranking_run_id=ranking_run_id,
            validation_report_id=validation_report_id,
            as_of_date=as_of_date,
            regime_label=regime_label,
            action=action,
            size_multiplier=size_multiplier,
            decile_filter=decile_filter,
            reason=reason,
            experiment_run_id=experiment_run_id,
            created_at=datetime.now(UTC),
        )
        self.db.add(decision)
        self.db.flush()
        return decision

    def list_decisions(
        self,
        *,
        ranking_run_id: UUID | None = None,
        as_of_date=None,
        regime_label: str | None = None,
        action: str | None = None,
        experiment_run_id: UUID | None = None,
        limit: int = 100,
    ) -> list[RegimePolicyDecision]:
        stmt = select(RegimePolicyDecision).order_by(RegimePolicyDecision.created_at.desc())
        if ranking_run_id:
            stmt = stmt.where(RegimePolicyDecision.ranking_run_id == ranking_run_id)
        if as_of_date:
            stmt = stmt.where(RegimePolicyDecision.as_of_date == as_of_date)
        if regime_label:
            stmt = stmt.where(RegimePolicyDecision.regime_label == regime_label)
        if action:
            stmt = stmt.where(RegimePolicyDecision.action == action)
        if experiment_run_id:
            stmt = stmt.where(RegimePolicyDecision.experiment_run_id == experiment_run_id)
        return list(self.db.scalars(stmt.limit(limit)).all())
