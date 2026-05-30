from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.ranking_performance_snapshot import RankingPerformanceSnapshot


class RankingPerformanceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_placeholder_snapshots(
        self,
        ranking_run_id: UUID,
        stock_ids: list[UUID],
    ) -> list[RankingPerformanceSnapshot]:
        now = datetime.now(UTC)
        rows: list[RankingPerformanceSnapshot] = []
        for stock_id in stock_ids:
            row = RankingPerformanceSnapshot(
                ranking_run_id=ranking_run_id,
                stock_id=stock_id,
                return_5d=None,
                return_10d=None,
                return_20d=None,
                return_60d=None,
                captured_at=now,
            )
            self.db.add(row)
            rows.append(row)
        self.db.flush()
        return rows
