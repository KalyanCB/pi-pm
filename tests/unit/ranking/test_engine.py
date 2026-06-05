from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from app.ranking.engine import RankingEngine
from app.ranking.strategies.momentum_v1 import MomentumV1Strategy
from app.universe.models import StockSnapshot, TradableUniverse, UniverseFilterConfig


class InMemoryLoader:
    def __init__(self, data: dict):
        self.data = data

    def load_series(self, stock_id, as_of_date, source="yahoo"):
        return [bar for bar in self.data.get(stock_id, []) if bar.date <= as_of_date]


def _bar(day: int, close: str, volume: int = 1_000_000):
    from app.ranking.math_utils import PriceBar

    return PriceBar(
        date=date(2024, 1, 1) + timedelta(days=day),
        close=Decimal(close),
        volume=volume,
    )


def test_ranking_reproducibility():
    stock_a = uuid4()
    stock_b = uuid4()
    bench_id = uuid4()
    bars_a = [_bar(i, str(100 + i), 1_000_000 + i * 1000) for i in range(210)]
    bars_b = [_bar(i, str(90 + i), 900_000 + i * 1000) for i in range(210)]
    bench = [_bar(i, str(80 + i), 500_000) for i in range(210)]

    loader = InMemoryLoader({stock_a: bars_a, stock_b: bars_b, bench_id: bench})
    engine = RankingEngine(loader)
    strategy = MomentumV1Strategy()
    as_of = bars_a[-1].date

    included = (
        StockSnapshot(stock_a, "AAA.NS", "A", "NSE", None, "ACTIVE", True),
        StockSnapshot(stock_b, "BBB.NS", "B", "NSE", None, "ACTIVE", True),
    )
    config = UniverseFilterConfig(universe_code="PI_PM_CORE")
    universe = TradableUniverse(
        universe_code="PI_PM_CORE",
        as_of_date=as_of,
        filter_config=config,
        filter_config_hash=config.config_hash(),
        included=included,
        excluded=(),
        exclusion_summary={},
    )

    first = engine.run(universe, strategy, "^NSEI", bench_id, as_of)
    second = engine.run(universe, strategy, "^NSEI", bench_id, as_of)

    assert first.inputs_hash == second.inputs_hash
    assert [s.rank for s in first.ranked_stocks] == [s.rank for s in second.ranked_stocks]
    assert [s.composite_score for s in first.ranked_stocks] == [
        s.composite_score for s in second.ranked_stocks
    ]


def test_benchmark_missing_redistributes_weights():
    stock_a = uuid4()
    bars_a = [_bar(i, str(100 + i), 1_000_000 + i * 1000) for i in range(210)]
    loader = InMemoryLoader({stock_a: bars_a})
    engine = RankingEngine(loader)
    strategy = MomentumV1Strategy()
    as_of = bars_a[-1].date
    included = (StockSnapshot(stock_a, "AAA.NS", "A", "NSE", None, "ACTIVE", True),)
    config = UniverseFilterConfig(universe_code="PI_PM_CORE")
    universe = TradableUniverse(
        universe_code="PI_PM_CORE",
        as_of_date=as_of,
        filter_config=config,
        filter_config_hash=config.config_hash(),
        included=included,
        excluded=(),
        exclusion_summary={},
    )

    output = engine.run(universe, strategy, "^NSEI", None, as_of)
    assert output.metadata["benchmark_available"] is False
    assert "weight_adjustment_reason" in output.metadata
    assert "relative_strength" not in output.metadata["effective_weights"]


def test_benchmark_present_uses_configured_weights():
    stock_a = uuid4()
    bench_id = uuid4()
    bars_a = [_bar(i, str(100 + i), 1_000_000 + i * 1000) for i in range(220)]
    bench = [_bar(i, str(80 + i), 500_000 + i * 1000) for i in range(220)]

    loader = InMemoryLoader({stock_a: bars_a, bench_id: bench})
    engine = RankingEngine(loader)
    strategy = MomentumV1Strategy()
    as_of = bars_a[-1].date
    included = (StockSnapshot(stock_a, "AAA.NS", "A", "NSE", None, "ACTIVE", True),)
    config = UniverseFilterConfig(universe_code="PI_PM_CORE")
    universe = TradableUniverse(
        universe_code="PI_PM_CORE",
        as_of_date=as_of,
        filter_config=config,
        filter_config_hash=config.config_hash(),
        included=included,
        excluded=(),
        exclusion_summary={},
    )

    output = engine.run(universe, strategy, "^NSEI", bench_id, as_of)
    assert output.metadata["benchmark_available"] is True
    assert "weight_adjustment_reason" not in output.metadata
    weights = output.metadata["effective_weights"]
    assert weights["volatility_adjusted_momentum"] == "0.40000000"
    assert weights["volume_expansion"] == "0.25000000"
    assert weights["trend_quality"] == "0.20000000"
    assert weights["relative_strength"] == "0.15000000"
    assert len(output.ranked_stocks) == 1
    components = {fs.factor_name for fs in output.ranked_stocks[0].factor_scores}
    assert "relative_strength" in components


def test_breakout_benchmark_missing_excludes_rs_factors():
    from app.ranking.strategies.breakout_v1 import BreakoutV1Strategy

    stock_a = uuid4()
    bars_a = [_bar(i, str(100 + i * 0.4), 1_000_000 + i * 1000) for i in range(280)]
    loader = InMemoryLoader({stock_a: bars_a})
    engine = RankingEngine(loader)
    strategy = BreakoutV1Strategy()
    as_of = bars_a[-1].date
    included = (StockSnapshot(stock_a, "AAA.NS", "A", "NSE", None, "ACTIVE", True),)
    config = UniverseFilterConfig(universe_code="PI_PM_CORE")
    universe = TradableUniverse(
        universe_code="PI_PM_CORE",
        as_of_date=as_of,
        filter_config=config,
        filter_config_hash=config.config_hash(),
        included=included,
        excluded=(),
        exclusion_summary={},
    )

    output = engine.run(universe, strategy, "^NSEI", None, as_of)
    effective = output.metadata["effective_weights"]
    assert "relative_strength" not in effective
    assert "relative_strength_acceleration" not in effective
    assert output.metadata["benchmark_available"] is False


def test_insufficient_strategy_history_exclusion():
    stock_short = uuid4()
    stock_long = uuid4()
    bars_short = [_bar(i, str(100 + i), 1_000_000) for i in range(150)]
    bars_long = [_bar(i, str(90 + i), 900_000) for i in range(220)]

    loader = InMemoryLoader({stock_short: bars_short, stock_long: bars_long})
    engine = RankingEngine(loader)
    strategy = MomentumV1Strategy()
    as_of = bars_long[-1].date
    included = (
        StockSnapshot(stock_short, "SHORT.NS", "Short", "NSE", None, "ACTIVE", True),
        StockSnapshot(stock_long, "LONG.NS", "Long", "NSE", None, "ACTIVE", True),
    )
    config = UniverseFilterConfig(universe_code="PI_PM_CORE")
    universe = TradableUniverse(
        universe_code="PI_PM_CORE",
        as_of_date=as_of,
        filter_config=config,
        filter_config_hash=config.config_hash(),
        included=included,
        excluded=(),
        exclusion_summary={},
    )

    output = engine.run(universe, strategy, "^NSEI", None, as_of)

    assert len(output.ranked_stocks) == 1
    assert output.ranked_stocks[0].symbol == "LONG.NS"
    assert output.metadata["ranking_exclusion_summary"]["INSUFFICIENT_STRATEGY_HISTORY"] == 1
    assert output.exclusion_summary["INSUFFICIENT_STRATEGY_HISTORY"] == 1
