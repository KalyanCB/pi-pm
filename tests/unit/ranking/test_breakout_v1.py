from datetime import date
from decimal import Decimal

from app.ranking.registry import RankingStrategyRegistry
from app.ranking.strategies.breakout_v1 import DEFAULT_WEIGHTS, BreakoutV1Strategy
from app.universe.models import StockSnapshot
from tests.unit.ranking.factors.conftest import make_bars


def test_registry_includes_breakout_v1():
    registry = RankingStrategyRegistry()
    strategy = registry.get("breakout_v1", "1.0.0")
    assert strategy.name == "breakout_v1"


def test_default_weights_sum_to_one():
    total = sum(DEFAULT_WEIGHTS.values(), Decimal("0"))
    assert total == Decimal("1")


def test_breakout_v1_computes_all_factors_with_benchmark():
    strategy = BreakoutV1Strategy()
    start = date(2023, 1, 1)
    stock_bars = make_bars(start, 280, start_price=Decimal("100"), step=Decimal("0.4"))
    bench_bars = make_bars(start, 280, start_price=Decimal("100"), step=Decimal("0.2"))
    stock = StockSnapshot(
        stock_id=__import__("uuid").uuid4(),
        symbol="BRK.NS",
        name="Breakout",
        exchange="NSE",
        sector=None,
        data_status="ACTIVE",
        is_active=True,
    )
    factors = strategy.compute_raw_factors(
        stock,
        stock_bars,
        bench_bars,
        stock_bars[-1].date,
    )
    assert factors["high_proximity"] is not None
    assert factors["volume_surge"] is not None
    assert factors["consolidation_breakout"] is not None
    assert factors["relative_strength"] is not None
    assert factors["relative_strength_acceleration"] is not None


def test_custom_weights_override():
    custom = {"high_proximity": Decimal("1.0")}
    strategy = BreakoutV1Strategy(weights=custom)
    weights = strategy.base_weights()
    assert weights["high_proximity"] == Decimal("1.0")
