from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.daily_batch import DailyBatchRunArtifact


class DailyBatchArtifactRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(
        self,
        *,
        daily_batch_run_id: UUID,
        artifact_type: str,
        artifact_id: UUID,
        status: str,
        strategy_name: str | None = None,
        as_of_date=None,
    ) -> DailyBatchRunArtifact:
        existing = self.db.scalar(
            select(DailyBatchRunArtifact).where(
                DailyBatchRunArtifact.daily_batch_run_id == daily_batch_run_id,
                DailyBatchRunArtifact.artifact_type == artifact_type,
                DailyBatchRunArtifact.artifact_id == artifact_id,
            )
        )
        if existing is not None:
            existing.status = status
            return existing
        row = DailyBatchRunArtifact(
            daily_batch_run_id=daily_batch_run_id,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            strategy_name=strategy_name,
            as_of_date=as_of_date,
            status=status,
            created_at=datetime.now(UTC),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def list_by_run(self, daily_batch_run_id: UUID) -> list[DailyBatchRunArtifact]:
        stmt = (
            select(DailyBatchRunArtifact)
            .where(DailyBatchRunArtifact.daily_batch_run_id == daily_batch_run_id)
            .order_by(DailyBatchRunArtifact.created_at)
        )
        return list(self.db.scalars(stmt).all())

    def group_ids_by_type(self, daily_batch_run_id: UUID) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for row in self.list_by_run(daily_batch_run_id):
            grouped[row.artifact_type].append(str(row.artifact_id))
        return dict(grouped)
