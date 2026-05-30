from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.ranking_result import RankingResult
from app.ranking.models import RankedStock


class RankingResultRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save_results(
        self, ranking_run_id: UUID, ranked_stocks: tuple[RankedStock, ...]
    ) -> list[RankingResult]:
        now = datetime.now(UTC)
        rows: list[RankingResult] = []
        for ranked in ranked_stocks:
            components = {
                fs.factor_name: {
                    "raw": str(fs.raw_value) if fs.raw_value is not None else None,
                    "normalized": (
                        str(fs.normalized_value) if fs.normalized_value is not None else None
                    ),
                    "weight": str(fs.weight),
                    "weighted": str(fs.weighted_contribution),
                }
                for fs in ranked.factor_scores
            }
            components["composite_score"] = str(ranked.composite_score)
            row = RankingResult(
                ranking_run_id=ranking_run_id,
                stock_id=ranked.stock_id,
                rank=ranked.rank,
                score=float(ranked.composite_score),
                score_components=components,
                created_at=now,
            )
            self.db.add(row)
            rows.append(row)
        self.db.flush()
        return rows

    def list_by_run_id(self, ranking_run_id: UUID) -> list[RankingResult]:
        from sqlalchemy import select

        return list(
            self.db.scalars(
                select(RankingResult)
                .where(RankingResult.ranking_run_id == ranking_run_id)
                .order_by(RankingResult.rank)
            ).all()
        )

    def list_top(self, ranking_run_id: UUID, limit: int) -> list[RankingResult]:
        from sqlalchemy import select

        return list(
            self.db.scalars(
                select(RankingResult)
                .where(RankingResult.ranking_run_id == ranking_run_id)
                .order_by(RankingResult.rank)
                .limit(limit)
            ).all()
        )
