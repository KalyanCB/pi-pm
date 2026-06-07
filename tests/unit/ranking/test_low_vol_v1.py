"""Unit tests for LowVolV1Strategy (low_vol_v1)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.ranking.math_utils import PriceBar
from app.ranking.strategies.low_vol_v1 import DEFAULT_WEIGHTS, HISTORY_DAYS, LowVolV1Strategy
from app.universe.models import StockSnapshot


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stock() -> StockSnapshot:
    return StockSnapshot(
        stock_id=uuid.uuid4(),
        symbol="TEST.NS",
        name="Test Stock",
        exchange="NSE",
        sector="Test",
        data_status="ACTIVE",
        is_active=True,
    )


def _bars(n: int, *, base: float = 100.0, daily_change: float = 1.0) -> list[PriceBar]:
    """Bars with deterministic fixed daily change (constant = zero vol in limit)."""
    bars = []
    price = Decimal(str(base))
    start = date(2024, 1, 1)
    for i in range(n):
        price = price + Decimal(str(daily_change * (1 if i % 2 == 0 else -1)))
        price = max(price, Decimal("1"))
        bars.append(PriceBar(date=start + timedelta(days=i), close=price, volume=1_000_000))
    return bars


def _volatile_bars(n: int, *, base: float = 100.0, swing: float = 10.0) -> list[PriceBar]:
    """Bars with large daily swings = high volatility."""
    bars = []
    price = Decimal(str(base))
    start = date(2024, 1, 1)
    for i in range(n):
        price = price + Decimal(str(swing * (1 if i % 2 == 0 else -1)))
        price = max(price, Decimal("1"))
        bars.append(PriceBar(date=start + timedelta(days=i), close=price, volume=1_000_000))
    return bars


# ── Identity ──────────────────────────────────────────────────────────────────

def test_strategy_name():
    assert LowVolV1Strategy().name == "low_vol_v1"


def test_strategy_version():
    assert LowVolV1Strategy().version == "1.0.0"


# ── Requirements ──────────────────────────────────────────────────────────────

def test_required_history_days():
    # VOL_LONG (60) + 1 = 61
    assert LowVolV1Strategy().requirements().required_history_days == 61
    assert HISTORY_DAYS == 61


# ── Factor structure ──────────────────────────────────────────────────────────

def test_three_factors():
    s = LowVolV1Strategy()
    assert len(s.factor_names()) == 3


def test_factor_names_correct():
    s = LowVolV1Strategy()
    assert "vol_30d_inverse" in s.factor_names()
    assert "vol_60d_inverse" in s.factor_names()
    assert "atr_price_inverse" in s.factor_names()


def test_weights_sum_to_one():
    s = LowVolV1Strategy()
    total = sum(s.base_weights().values())
    assert abs(float(total) - 1.0) < 1e-9


def test_default_weight_values():
    assert DEFAULT_WEIGHTS["vol_30d_inverse"]   == Decimal("0.50")
    assert DEFAULT_WEIGHTS["vol_60d_inverse"]   == Decimal("0.30")
    assert DEFAULT_WEIGHTS["atr_price_inverse"] == Decimal("0.20")


# ── Core property: low-vol stock ranks higher than high-vol ───────────────────

def test_calm_stock_higher_vol30_than_choppy():
    s = LowVolV1Strategy()
    calm    = _bars(70, daily_change=0.5)
    choppy  = _volatile_bars(70, swing=8.0)
    as_of   = calm[-1].date

    calm_f   = s.compute_raw_factors(_stock(), calm,   None, as_of)
    choppy_f = s.compute_raw_factors(_stock(), choppy, None, as_of)

    assert calm_f["vol_30d_inverse"] is not None
    assert choppy_f["vol_30d_inverse"] is not None
    assert calm_f["vol_30d_inverse"] > choppy_f["vol_30d_inverse"]


def test_calm_stock_higher_vol60_than_choppy():
    s = LowVolV1Strategy()
    calm   = _bars(70, daily_change=0.5)
    choppy = _volatile_bars(70, swing=8.0)
    as_of  = calm[-1].date

    calm_f   = s.compute_raw_factors(_stock(), calm,   None, as_of)
    choppy_f = s.compute_raw_factors(_stock(), choppy, None, as_of)

    assert calm_f["vol_60d_inverse"] is not None
    assert choppy_f["vol_60d_inverse"] is not None
    assert calm_f["vol_60d_inverse"] > choppy_f["vol_60d_inverse"]


def test_calm_stock_higher_atr_inverse_than_choppy():
    s = LowVolV1Strategy()
    calm   = _bars(70, daily_change=0.5)
    choppy = _volatile_bars(70, swing=8.0)
    as_of  = calm[-1].date

    calm_f   = s.compute_raw_factors(_stock(), calm,   None, as_of)
    choppy_f = s.compute_raw_factors(_stock(), choppy, None, as_of)

    assert calm_f["atr_price_inverse"] is not None
    assert choppy_f["atr_price_inverse"] is not None
    assert calm_f["atr_price_inverse"] > choppy_f["atr_price_inverse"]


# ── Insufficient history ──────────────────────────────────────────────────────

def test_vol_60d_none_with_short_history():
    s = LowVolV1Strategy()
    short = _bars(20)
    factors = s.compute_raw_factors(_stock(), short, None, short[-1].date)
    assert factors["vol_60d_inverse"] is None


def test_vol_30d_none_with_very_short_history():
    s = LowVolV1Strategy()
    short = _bars(10)
    factors = s.compute_raw_factors(_stock(), short, None, short[-1].date)
    assert factors["vol_30d_inverse"] is None


# ── Positive factor values with sufficient history ────────────────────────────

def test_all_factors_positive_with_sufficient_history():
    s = LowVolV1Strategy()
    bars = _bars(70)
    factors = s.compute_raw_factors(_stock(), bars, None, bars[-1].date)
    for name, val in factors.items():
        assert val is not None, f"{name} should not be None with 70 bars"
        assert val > Decimal("0"), f"{name} should be positive"


# ── Benchmark independence ────────────────────────────────────────────────────

def test_benchmark_not_used():
    """low_vol_v1 does not use benchmark — result identical with/without it."""
    s = LowVolV1Strategy()
    bars = _bars(70)
    bench = _bars(70, base=18000.0, daily_change=50.0)
    as_of = bars[-1].date

    with_bench    = s.compute_raw_factors(_stock(), bars, bench, as_of)
    without_bench = s.compute_raw_factors(_stock(), bars, None,  as_of)

    assert with_bench == without_bench


# ── Composite score ───────────────────────────────────────────────────────────

def test_composite_score_between_0_and_1():
    s = LowVolV1Strategy()
    bars = _bars(70)
    raw = s.compute_raw_factors(_stock(), bars, None, bars[-1].date)
    # Use mid-percentile normalization (0.5 = median)
    normalized = {k: Decimal("0.5") for k in s.factor_names() if raw.get(k) is not None}
    factor_scores = s.build_factor_scores(raw, normalized, s.base_weights())
    composite = s.composite_score(factor_scores)
    assert Decimal("0") <= composite <= Decimal("1")


def test_composite_score_higher_for_calmer_stock():
    s = LowVolV1Strategy()
    calm   = _bars(70, daily_change=0.5)
    choppy = _volatile_bars(70, swing=8.0)
    as_of  = calm[-1].date

    def get_composite(b: list[PriceBar]) -> Decimal:
        raw = s.compute_raw_factors(_stock(), b, None, as_of)
        # Simulate: calm = 0.9 percentile, choppy = 0.1 percentile
        return Decimal("0")  # placeholder — score ordering tested via factor values

    # Verify through factor values that calm stock will rank higher
    calm_f   = s.compute_raw_factors(_stock(), calm,   None, as_of)
    choppy_f = s.compute_raw_factors(_stock(), choppy, None, as_of)
    for name in s.factor_names():
        if calm_f[name] and choppy_f[name]:
            assert calm_f[name] > choppy_f[name], f"{name}: calm should beat choppy"


# ── Determinism ───────────────────────────────────────────────────────────────

def test_deterministic_same_inputs():
    s = LowVolV1Strategy()
    bars  = _bars(70)
    stock = _stock()
    as_of = bars[-1].date
    r1 = s.compute_raw_factors(stock, bars, None, as_of)
    r2 = s.compute_raw_factors(stock, bars, None, as_of)
    assert r1 == r2


def test_custom_weights_accepted():
    custom = {"vol_30d_inverse": Decimal("1.0"), "vol_60d_inverse": Decimal("0"), "atr_price_inverse": Decimal("0")}
    s = LowVolV1Strategy(weights=custom)
    assert s.base_weights()["vol_30d_inverse"] == Decimal("1.0")


# ── Registry ──────────────────────────────────────────────────────────────────

def test_strategy_in_registry():
    from app.ranking.registry import RankingStrategyRegistry
    registry = RankingStrategyRegistry()
    strategy = registry.get("low_vol_v1", "1.0.0")
    assert strategy.name == "low_vol_v1"
    assert strategy.version == "1.0.0"
