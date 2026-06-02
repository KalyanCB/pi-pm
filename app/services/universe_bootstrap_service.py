from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.constants import UNIVERSE_NIFTY_500, UNIVERSE_NIFTY_1000
from app.core.exceptions import NotFoundError
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.universe.nifty500_loader import (
    Nifty500Constituent,
    fetch_nifty500_constituents,
    load_nifty500_constituents,
)
from app.universe.nse_index_loader import load_nifty1000_constituents


@dataclass(frozen=True)
class UniverseBootstrapResult:
    universe_code: str
    constituents_loaded: int
    stocks_created: int
    stocks_existing: int
    memberships_added: int
    memberships_reactivated: int
    membership_total: int


class UniverseBootstrapService:
    def __init__(
        self,
        db: Session,
        stock_repo: StockRepository,
        universe_repo: UniverseRepository,
    ) -> None:
        self.db = db
        self.stock_repo = stock_repo
        self.universe_repo = universe_repo

    def bootstrap_nifty500(
        self,
        *,
        csv_path: Path | None = None,
        fetch_live: bool = False,
    ) -> UniverseBootstrapResult:
        universe = self.universe_repo.get_by_code(UNIVERSE_NIFTY_500)
        if universe is None:
            raise NotFoundError(f"Universe not found: {UNIVERSE_NIFTY_500}")

        if fetch_live:
            constituents = fetch_nifty500_constituents()
        else:
            constituents = load_nifty500_constituents(csv_path)

        return self._bootstrap_memberships(universe.id, UNIVERSE_NIFTY_500, constituents)

    def bootstrap_nifty1000(
        self,
        *,
        csv_path: Path | None = None,
    ) -> UniverseBootstrapResult:
        universe = self.universe_repo.get_by_code(UNIVERSE_NIFTY_1000)
        if universe is None:
            raise NotFoundError(f"Universe not found: {UNIVERSE_NIFTY_1000}")

        constituents = load_nifty1000_constituents(csv_path)
        return self._bootstrap_memberships(universe.id, UNIVERSE_NIFTY_1000, constituents)

    def bootstrap_from_constituents(
        self,
        universe_code: str,
        constituents: list[Nifty500Constituent],
    ) -> UniverseBootstrapResult:
        universe = self.universe_repo.get_by_code(universe_code)
        if universe is None:
            raise NotFoundError(f"Universe not found: {universe_code}")
        return self._bootstrap_memberships(universe.id, universe_code, constituents)

    def _bootstrap_memberships(
        self,
        universe_id,
        universe_code: str,
        constituents: list[Nifty500Constituent],
    ) -> UniverseBootstrapResult:
        stocks_created = 0
        stocks_existing = 0
        memberships_changed = 0

        for constituent in constituents:
            stock, created = self.stock_repo.get_or_create_placeholder(
                constituent.yahoo_symbol,
                name=constituent.company_name,
                industry=constituent.industry or None,
            )
            if created:
                stocks_created += 1
            else:
                stocks_existing += 1

            _membership, changed = self.universe_repo.add_membership(universe_id, stock.id)
            if changed:
                memberships_changed += 1

        self.db.commit()
        return UniverseBootstrapResult(
            universe_code=universe_code,
            constituents_loaded=len(constituents),
            stocks_created=stocks_created,
            stocks_existing=stocks_existing,
            memberships_added=memberships_changed,
            memberships_reactivated=0,
            membership_total=self.universe_repo.count_active_memberships(universe_code),
        )
