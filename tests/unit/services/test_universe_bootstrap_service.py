from pathlib import Path

import pytest

from app.core.constants import UNIVERSE_NIFTY_500
from app.models.stock_universe import StockUniverse
from app.services.universe_bootstrap_service import UniverseBootstrapService
from app.universe.nifty500_loader import load_nifty500_constituents


@pytest.fixture
def nifty500_universe(db_session, universe_repo):
    universe = StockUniverse(
        code=UNIVERSE_NIFTY_500,
        name="NIFTY 500",
        is_active=True,
    )
    db_session.add(universe)
    db_session.flush()
    return universe


def test_bootstrap_nifty500_from_fixture(
    db_session, stock_repo, universe_repo, nifty500_universe
) -> None:
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "nifty500_sample.csv"
    service = UniverseBootstrapService(db_session, stock_repo, universe_repo)

    result = service.bootstrap_from_constituents(
        UNIVERSE_NIFTY_500,
        load_nifty500_constituents(fixture),
    )

    assert result.constituents_loaded == 3
    assert result.stocks_created == 3
    assert result.membership_total == 3
    assert universe_repo.count_active_memberships(UNIVERSE_NIFTY_500) == 3


def test_bootstrap_is_idempotent(
    db_session, stock_repo, universe_repo, nifty500_universe
) -> None:
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "nifty500_sample.csv"
    service = UniverseBootstrapService(db_session, stock_repo, universe_repo)
    constituents = load_nifty500_constituents(fixture)

    first = service.bootstrap_from_constituents(UNIVERSE_NIFTY_500, constituents)
    second = service.bootstrap_from_constituents(UNIVERSE_NIFTY_500, constituents)

    assert first.membership_total == 3
    assert second.membership_total == 3
    assert second.stocks_created == 0
    assert second.memberships_added == 0
