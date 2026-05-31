from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.platform_traceability import RankingFactorContribution
from app.models.ranking_result import RankingResult


class RankingFactorContributionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def sync_from_results(self, ranking_run_id: UUID) -> int:
        results = self.db.scalars(
            select(RankingResult).where(RankingResult.ranking_run_id == ranking_run_id)
        ).all()
        self.db.execute(
            delete(RankingFactorContribution).where(
                RankingFactorContribution.ranking_run_id == ranking_run_id
            )
        )
        rows_written = 0
        for result in results:
            components = result.score_components or {}
            for factor_name, payload in components.items():
                if factor_name == "composite_score" or not isinstance(payload, dict):
                    continue
                row = RankingFactorContribution(
                    ranking_run_id=ranking_run_id,
                    stock_id=result.stock_id,
                    factor_name=factor_name,
                    raw_factor_value=_to_float(payload.get("raw")),
                    normalized_factor_value=_to_float(payload.get("normalized")),
                    weighted_factor_value=_to_float(payload.get("weighted")),
                )
                self.db.add(row)
                rows_written += 1
        self.db.flush()
        return rows_written

    def has_for_run(self, ranking_run_id: UUID) -> bool:
        count = self.db.scalar(
            select(func.count())
            .select_from(RankingFactorContribution)
            .where(RankingFactorContribution.ranking_run_id == ranking_run_id)
        )
        return int(count or 0) > 0

    def list_by_run(self, ranking_run_id: UUID) -> list[RankingFactorContribution]:
        return list(
            self.db.scalars(
                select(RankingFactorContribution)
                .where(RankingFactorContribution.ranking_run_id == ranking_run_id)
                .order_by(
                    RankingFactorContribution.stock_id,
                    RankingFactorContribution.factor_name,
                )
            ).all()
        )


def _to_float(value) -> float | None:
    if value is None:
        return None
    return float(value)
