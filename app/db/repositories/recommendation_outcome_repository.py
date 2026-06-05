"""Repository for RecommendationOutcome — filtered queries for analytics."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.recommendation import RecommendationOutcome, RecommendationResult, RecommendationRun


class RecommendationOutcomeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_result_id(self, result_id: UUID) -> RecommendationOutcome | None:
        return self.db.scalar(
            select(RecommendationOutcome).where(
                RecommendationOutcome.recommendation_result_id == result_id
            )
        )

    def list_for_analytics(
        self,
        *,
        strategy_name: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        outcome_statuses: list[str] | None = None,
        conviction_bands: list[str] | None = None,
        regime_labels: list[str] | None = None,
        limit: int = 2000,
    ) -> list[RecommendationOutcome]:
        q = select(RecommendationOutcome)
        if strategy_name:
            q = q.where(RecommendationOutcome.strategy_name == strategy_name)
        if from_date:
            q = q.where(RecommendationOutcome.entry_date >= from_date)
        if to_date:
            q = q.where(RecommendationOutcome.entry_date <= to_date)
        if outcome_statuses:
            q = q.where(RecommendationOutcome.outcome_status.in_(outcome_statuses))
        if conviction_bands:
            q = q.where(RecommendationOutcome.conviction_band.in_(conviction_bands))
        if regime_labels:
            q = q.where(RecommendationOutcome.regime_label.in_(regime_labels))
        q = q.order_by(RecommendationOutcome.entry_date.desc()).limit(limit)
        return list(self.db.scalars(q).all())

    def list_by_symbol(self, symbol: str, limit: int = 100) -> list[RecommendationOutcome]:
        return list(
            self.db.scalars(
                select(RecommendationOutcome)
                .where(RecommendationOutcome.symbol == symbol.upper())
                .order_by(RecommendationOutcome.entry_date.desc())
                .limit(limit)
            ).all()
        )

    def count_by_validation_status(
        self,
        *,
        strategy_name: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, int]:
        """Return {completed: N, insufficient_data: N} for reliability metric."""
        # Join to recommendation_results to get conviction_components which holds validation status
        q = (
            select(
                RecommendationResult.conviction_components,
            )
            .join(
                RecommendationOutcome,
                RecommendationOutcome.recommendation_result_id == RecommendationResult.id,
            )
        )
        if strategy_name:
            q = q.join(
                RecommendationRun,
                RecommendationRun.id == RecommendationResult.recommendation_run_id,
            ).where(RecommendationRun.strategy_name == strategy_name)
        if from_date:
            q = q.where(RecommendationOutcome.entry_date >= from_date)
        if to_date:
            q = q.where(RecommendationOutcome.entry_date <= to_date)

        rows = self.db.execute(q).all()
        completed = 0
        insufficient = 0
        for (components,) in rows:
            if not components:
                insufficient += 1
                continue
            val_status = components.get("validation_status", "")
            if val_status == "insufficient_data":
                insufficient += 1
            else:
                completed += 1
        return {"completed": completed, "insufficient_data": insufficient}

    def list_action_history(
        self,
        *,
        strategy_name: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[dict]:
        """Return rows of (symbol, as_of_date, action) for stability computation."""
        q = (
            select(
                RecommendationOutcome.symbol,
                RecommendationOutcome.entry_date,
                RecommendationResult.action,
            )
            .join(
                RecommendationResult,
                RecommendationResult.id == RecommendationOutcome.recommendation_result_id,
            )
        )
        if strategy_name:
            q = q.join(
                RecommendationRun,
                RecommendationRun.id == RecommendationResult.recommendation_run_id,
            ).where(RecommendationRun.strategy_name == strategy_name)
        if from_date:
            q = q.where(RecommendationOutcome.entry_date >= from_date)
        if to_date:
            q = q.where(RecommendationOutcome.entry_date <= to_date)
        q = q.order_by(RecommendationOutcome.symbol, RecommendationOutcome.entry_date)
        rows = self.db.execute(q).all()
        return [{"symbol": r[0], "date": r[1], "action": r[2]} for r in rows]

    def list_results_for_symbol(
        self, symbol: str, strategy_name: str | None = None
    ) -> list[RecommendationResult]:
        """All recommendation results for a symbol (for why-not analysis)."""
        from sqlalchemy import select
        from app.models.stock import Stock

        stock = self.db.scalar(select(Stock).where(Stock.symbol == symbol.upper()))
        if stock is None:
            return []
        q = select(RecommendationResult).where(
            RecommendationResult.stock_id == stock.id
        ).order_by(RecommendationResult.created_at.desc()).limit(50)
        if strategy_name:
            q = q.join(
                RecommendationRun,
                RecommendationRun.id == RecommendationResult.recommendation_run_id,
            ).where(RecommendationRun.strategy_name == strategy_name)
        return list(self.db.scalars(q).all())
