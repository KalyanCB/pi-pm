"""Repository for ADR-039 sector_classifications (stock → sector mapping)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fil import SectorClassification


class SectorClassificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(
        self,
        *,
        stock_id: UUID,
        sector: str,
        sub_sector: str | None = None,
        index_membership: dict | None = None,
    ) -> SectorClassification:
        existing = self.db.scalar(
            select(SectorClassification).where(
                SectorClassification.stock_id == stock_id,
                SectorClassification.sector == sector,
            )
        )
        if existing is not None:
            existing.sub_sector = sub_sector
            existing.index_membership = index_membership
            self.db.flush()
            return existing
        row = SectorClassification(
            stock_id=stock_id,
            sector=sector,
            sub_sector=sub_sector,
            index_membership=index_membership,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def stock_ids_for_sector(self, sector: str) -> list[UUID]:
        return list(
            self.db.scalars(
                select(SectorClassification.stock_id).where(SectorClassification.sector == sector)
            )
        )

    def sector_for_stock(self, stock_id: UUID) -> str | None:
        return self.db.scalar(
            select(SectorClassification.sector).where(SectorClassification.stock_id == stock_id)
        )
