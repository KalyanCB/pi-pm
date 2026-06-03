from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from app.ranking.math_utils import PriceBar
from app.stock_setup_evidence.profile import (
    build_stock_internal_normalized_profiles,
    extract_reference_profile,
)
from app.stock_setup_evidence.strategy_profiles import resolve_see_strategy
from app.universe.models import StockSnapshot


def _bars(n: int) -> list[PriceBar]:
    base = date(2025, 1, 1)
    return [
        PriceBar(date=base + timedelta(days=i), close=Decimal(100 + i), volume=1000 + i)
        for i in range(n)
    ]


def test_momentum_reference_and_historical_share_factor_space():
    momentum = resolve_see_strategy("momentum_v1")
    score_components = {
        name: {"normalized": 0.75, "raw": 1.0}
        for name in momentum.factor_names
    }
    reference = extract_reference_profile(
        score_components, factor_names=momentum.factor_names
    )
    assert set(reference.keys()) == set(momentum.factor_names)

    stock = StockSnapshot(
        stock_id=uuid4(),
        symbol="TEST.NS",
        name="Test",
        exchange="NSE",
        sector=None,
        is_active=True,
        data_status="ok",
    )
    bars = _bars(260)
    dates = [b.date for b in bars[60:-1:5]]
    profiles = build_stock_internal_normalized_profiles(
        stock,
        bars,
        None,
        dates,
        strategy_config=momentum,
    )
    assert profiles
    for profile in profiles.values():
        assert set(profile.keys()).issubset(set(momentum.factor_names))
