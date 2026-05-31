from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import IngestionRunStatus
from app.models.market_data_ingestion_run import MarketDataIngestionRun
from app.models.platform_traceability import RunLineageRecord


class RunLineageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def link(
        self,
        *,
        child_entity_type: str,
        child_entity_id: UUID,
        parent_entity_type: str,
        parent_entity_id: UUID,
        relationship_type: str,
    ) -> RunLineageRecord:
        existing = self.db.scalar(
            select(RunLineageRecord).where(
                RunLineageRecord.child_entity_type == child_entity_type,
                RunLineageRecord.child_entity_id == child_entity_id,
                RunLineageRecord.parent_entity_type == parent_entity_type,
                RunLineageRecord.parent_entity_id == parent_entity_id,
                RunLineageRecord.relationship_type == relationship_type,
            )
        )
        if existing is not None:
            return existing
        row = RunLineageRecord(
            child_entity_type=child_entity_type,
            child_entity_id=child_entity_id,
            parent_entity_type=parent_entity_type,
            parent_entity_id=parent_entity_id,
            relationship_type=relationship_type,
            created_at=datetime.now(UTC),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def list_for_entity(self, entity_type: str, entity_id: UUID) -> list[RunLineageRecord]:
        as_child = self.db.scalars(
            select(RunLineageRecord).where(
                RunLineageRecord.child_entity_type == entity_type,
                RunLineageRecord.child_entity_id == entity_id,
            )
        ).all()
        as_parent = self.db.scalars(
            select(RunLineageRecord).where(
                RunLineageRecord.parent_entity_type == entity_type,
                RunLineageRecord.parent_entity_id == entity_id,
            )
        ).all()
        return list(as_child) + list(as_parent)
