from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.stock_setup_research import StockSetupResearch, StockSetupResearchMetric


class StockSetupResearchRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_run_stock(self, *, ranking_run_id: UUID, stock_id: UUID) -> StockSetupResearch | None:
        return self.db.scalar(
            select(StockSetupResearch)
            .where(
                StockSetupResearch.ranking_run_id == ranking_run_id,
                StockSetupResearch.stock_id == stock_id,
            )
            .options(selectinload(StockSetupResearch.metrics))
        )

    def list_for_ranking_run(self, ranking_run_id: UUID) -> list[StockSetupResearch]:
        return list(
            self.db.scalars(
                select(StockSetupResearch)
                .where(StockSetupResearch.ranking_run_id == ranking_run_id)
                .options(selectinload(StockSetupResearch.metrics))
                .order_by(StockSetupResearch.symbol)
            ).all()
        )

    def get_by_id(self, research_id: UUID) -> StockSetupResearch | None:
        return self.db.scalar(
            select(StockSetupResearch)
            .where(StockSetupResearch.id == research_id)
            .options(selectinload(StockSetupResearch.metrics))
        )

    def replace_for_run_stock(
        self,
        *,
        ranking_run_id: UUID,
        ranking_result_id: UUID | None,
        stock_id: UUID,
        symbol: str,
        as_of_date,
        status: str,
        reference_profile: dict,
        similar_setups: list[dict],
        nearest_n: int,
        min_similarity: float,
        match_count: int,
        parameter_set: dict,
        research_hash: str | None,
        metrics: list[dict],
        error_message: str | None = None,
    ) -> StockSetupResearch:
        existing = self.get_for_run_stock(ranking_run_id=ranking_run_id, stock_id=stock_id)
        now = datetime.now(UTC)
        if existing is not None:
            self.db.execute(
                delete(StockSetupResearchMetric).where(
                    StockSetupResearchMetric.stock_setup_research_id == existing.id
                )
            )
            row = existing
            row.status = status
            row.reference_profile = reference_profile
            row.similar_setups = similar_setups
            row.nearest_n = nearest_n
            row.min_similarity = min_similarity
            row.match_count = match_count
            row.parameter_set = parameter_set
            row.research_hash = research_hash
            row.error_message = error_message
            row.ranking_result_id = ranking_result_id
            row.completed_at = now
        else:
            row = StockSetupResearch(
                ranking_run_id=ranking_run_id,
                ranking_result_id=ranking_result_id,
                stock_id=stock_id,
                symbol=symbol,
                as_of_date=as_of_date,
                status=status,
                reference_profile=reference_profile,
                similar_setups=similar_setups,
                nearest_n=nearest_n,
                min_similarity=min_similarity,
                match_count=match_count,
                parameter_set=parameter_set,
                research_hash=research_hash,
                error_message=error_message,
                started_at=now,
                completed_at=now,
            )
            self.db.add(row)
            self.db.flush()

        for metric in metrics:
            self.db.add(
                StockSetupResearchMetric(
                    stock_setup_research_id=row.id,
                    regime_label=metric["regime_label"],
                    occurrence_count=metric["occurrence_count"],
                    win_rate_5d=metric.get("win_rate_5d"),
                    win_rate_20d=metric.get("win_rate_20d"),
                    avg_return_5d=metric.get("avg_return_5d"),
                    avg_return_20d=metric.get("avg_return_20d"),
                    median_return_20d=metric.get("median_return_20d"),
                    avg_max_drawdown=metric.get("avg_max_drawdown"),
                    avg_max_runup=metric.get("avg_max_runup"),
                    avg_similarity_score=metric.get("avg_similarity_score"),
                )
            )
        self.db.flush()
        return row
