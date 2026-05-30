from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
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

    def get_by_run_id(self, ranking_run_id: UUID) -> list[RankingPerformanceSnapshot]:
        return list(
            self.db.scalars(
                select(RankingPerformanceSnapshot)
                .where(RankingPerformanceSnapshot.ranking_run_id == ranking_run_id)
                .order_by(RankingPerformanceSnapshot.stock_id)
            ).all()
        )

    def ensure_snapshots(
        self, ranking_run_id: UUID, stock_ids: list[UUID]
    ) -> list[RankingPerformanceSnapshot]:
        existing = self.get_by_run_id(ranking_run_id)
        existing_ids = {row.stock_id for row in existing}
        missing = [sid for sid in stock_ids if sid not in existing_ids]
        if missing:
            existing.extend(self.create_placeholder_snapshots(ranking_run_id, missing))
        return existing

    def update_returns(
        self,
        snapshot: RankingPerformanceSnapshot,
        returns: dict[int, Decimal | None],
    ) -> RankingPerformanceSnapshot:
        snapshot.return_5d = float(returns[5]) if returns.get(5) is not None else None
        snapshot.return_10d = float(returns[10]) if returns.get(10) is not None else None
        snapshot.return_20d = float(returns[20]) if returns.get(20) is not None else None
        snapshot.return_60d = float(returns[60]) if returns.get(60) is not None else None
        snapshot.captured_at = datetime.now(UTC)
        self.db.flush()
        return snapshot
