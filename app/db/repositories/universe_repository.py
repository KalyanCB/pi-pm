from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.stock import Stock
from app.models.stock_universe import StockUniverse
from app.models.universe_membership import UniverseMembership


class UniverseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_code(self, code: str) -> StockUniverse | None:
        return self.db.scalar(select(StockUniverse).where(StockUniverse.code == code))

    def list_active(self) -> list[StockUniverse]:
        return list(
            self.db.scalars(
                select(StockUniverse).where(StockUniverse.is_active.is_(True)).order_by(StockUniverse.code)
            ).all()
        )

    def list_stocks_in_universe(self, universe_code: str) -> list[Stock]:
        universe = self.get_by_code(universe_code)
        if universe is None:
            return []
        stmt = (
            select(Stock)
            .join(UniverseMembership, UniverseMembership.stock_id == Stock.id)
            .where(
                UniverseMembership.universe_id == universe.id,
                UniverseMembership.removed_at.is_(None),
            )
            .order_by(Stock.symbol)
        )
        return list(self.db.scalars(stmt).all())

    def list_candidate_stocks(self, universe_code: str) -> list[Stock]:
        universe = self.get_by_code(universe_code)
        if universe is None:
            return []
        stmt = (
            select(Stock)
            .join(UniverseMembership, UniverseMembership.stock_id == Stock.id)
            .where(UniverseMembership.universe_id == universe.id)
            .order_by(Stock.symbol)
        )
        return list(self.db.scalars(stmt).all())

    def count_active_memberships(self, universe_code: str) -> int:
        universe = self.get_by_code(universe_code)
        if universe is None:
            return 0
        count = self.db.scalar(
            select(func.count())
            .select_from(UniverseMembership)
            .where(
                UniverseMembership.universe_id == universe.id,
                UniverseMembership.removed_at.is_(None),
            )
        )
        return int(count or 0)

    def add_membership(self, universe_id: UUID, stock_id: UUID) -> tuple[UniverseMembership, bool]:
        existing = self.db.scalar(
            select(UniverseMembership).where(
                UniverseMembership.universe_id == universe_id,
                UniverseMembership.stock_id == stock_id,
            )
        )
        if existing:
            if existing.removed_at is not None:
                existing.removed_at = None
                self.db.flush()
                return existing, True
            return existing, False

        membership = UniverseMembership(universe_id=universe_id, stock_id=stock_id)
        self.db.add(membership)
        self.db.flush()
        return membership, True
