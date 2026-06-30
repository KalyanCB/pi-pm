"""Unit tests for BreakoutV3Strategy (breakout_v3_broad / breakout_v3_def)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.ranking.math_utils import PriceBar
from app.ranking.strategies.breakout_v3 import (
    BROAD_WEIGHTS,
    DEFENSIVE_WEIGHTS,
    FACTOR_HIGH_PROXIMITY,
    FACTOR_LOW_VOL,
    FACTOR_MOMENTUM_12M,
    FACTOR_TREND_EFFICIENCY,
    HISTORY_DAYS,
    build_breakout_v3_broad_strategy,
    build_breakout_v3_def_strategy,
)
from app.universe.models import StockSnapshot


def _stock() -> StockSnapshot:
    return StockSnapshot(
        stock_id=uuid.uuid4(), symbol="TEST.NS", name="Test", exchange="NSE",
        sector="Test", data_status="ACTIVE", is_active=True,
    )


def _uptrend(n: int, *, base: float = 100.0, step: float = 0.5) -> list[PriceBar]:
    """Smooth rising series (efficient trend, near its own high)."""
    bars, price, start = [], Decimal(str(base)), date(2023, 1, 1)
    for i in range(n):
        price = price + Decimal(str(step))
        bars.append(PriceBar(date=start + timedelta(days=i), close=price, volume=1_000_000))
    return bars


def _choppy(n: int, *, base: float = 100.0, swing: float = 8.0) -> list[PriceBar]:
    """Volatile sideways series (inefficient, high vol)."""
    bars, price, start = [], Decimal(str(base)), date(2023, 1, 1)
    for i in range(n):
        price = max(price + Decimal(str(swing * (1 if i % 2 == 0 else -1))), Decimal("1"))
        bars.append(PriceBar(date=start + timedelta(days=i), close=price, volume=1_000_000))
    return bars


# ── Identity / registration ───────────────────────────────────────────────────

def test_broad_identity():
    s = build_breakout_v3_broad_strategy()
    assert s.name == "breakout_v3_broad" and s.version == "1.0.0"


def test_def_identity():
    s = build_breakout_v3_def_strategy()
    assert s.name == "breakout_v3_def" and s.version == "1.0.0"


def test_both_in_registry():
    from app.ranking.registry import RankingStrategyRegistry
    reg = RankingStrategyRegistry()
    assert reg.get("breakout_v3_broad", "1.0.0").name == "breakout_v3_broad"
    assert reg.get("breakout_v3_def", "1.0.0").name == "breakout_v3_def"


# ── Weights / factor sets ─────────────────────────────────────────────────────

def test_broad_weights():
    assert BROAD_WEIGHTS[FACTOR_HIGH_PROXIMITY] == Decimal("0.45")
    assert BROAD_WEIGHTS[FACTOR_MOMENTUM_12M] == Decimal("0.35")
    assert BROAD_WEIGHTS[FACTOR_TREND_EFFICIENCY] == Decimal("0.20")
    assert abs(float(sum(BROAD_WEIGHTS.values())) - 1.0) < 1e-9


def test_def_weights():
    assert DEFENSIVE_WEIGHTS[FACTOR_HIGH_PROXIMITY] == Decimal("0.55")
    assert DEFENSIVE_WEIGHTS[FACTOR_LOW_VOL] == Decimal("0.45")
    assert abs(float(sum(DEFENSIVE_WEIGHTS.values())) - 1.0) < 1e-9


def test_vol_contraction_dropped():
    """v3's whole thesis: vol_contraction is dead weight and must NOT appear."""
    assert "vol_contraction" not in BROAD_WEIGHTS
    assert "vol_contraction" not in DEFENSIVE_WEIGHTS


def test_proximity_in_both_sleeves():
    assert FACTOR_HIGH_PROXIMITY in BROAD_WEIGHTS
    assert FACTOR_HIGH_PROXIMITY in DEFENSIVE_WEIGHTS


def test_history_days():
    # max(252 proximity, 252 momentum, 60 efficiency) + 5
    assert HISTORY_DAYS == 257
    assert build_breakout_v3_broad_strategy().requirements().required_history_days == 257


# ── Broad sleeve only computes its factors (no low_vol) ───────────────────────

def test_broad_computes_only_its_factors():
    s = build_breakout_v3_broad_strategy()
    bars = _uptrend(260)
    f = s.compute_raw_factors(_stock(), bars, None, bars[-1].date)
    assert set(f.keys()) == {FACTOR_HIGH_PROXIMITY, FACTOR_MOMENTUM_12M, FACTOR_TREND_EFFICIENCY}
    assert FACTOR_LOW_VOL not in f


def test_def_computes_only_its_factors():
    s = build_breakout_v3_def_strategy()
    bars = _uptrend(260)
    f = s.compute_raw_factors(_stock(), bars, None, bars[-1].date)
    assert set(f.keys()) == {FACTOR_HIGH_PROXIMITY, FACTOR_LOW_VOL}


# ── Factor economics ──────────────────────────────────────────────────────────

def test_efficient_trend_scores_higher_efficiency():
    s = build_breakout_v3_broad_strategy()
    smooth = _uptrend(260)
    rough = _choppy(260)
    a = s.compute_raw_factors(_stock(), smooth, None, smooth[-1].date)
    b = s.compute_raw_factors(_stock(), rough, None, rough[-1].date)
    assert a[FACTOR_TREND_EFFICIENCY] > b[FACTOR_TREND_EFFICIENCY]


def test_uptrend_momentum_positive():
    s = build_breakout_v3_broad_strategy()
    bars = _uptrend(260)
    f = s.compute_raw_factors(_stock(), bars, None, bars[-1].date)
    assert f[FACTOR_MOMENTUM_12M] is not None and f[FACTOR_MOMENTUM_12M] > Decimal("0")


def test_calm_stock_higher_low_vol_than_choppy():
    s = build_breakout_v3_def_strategy()
    calm = _choppy(260, swing=0.5)    # mild real volatility (not zero)
    choppy = _choppy(260, swing=8.0)  # large swings
    a = s.compute_raw_factors(_stock(), calm, None, calm[-1].date)
    b = s.compute_raw_factors(_stock(), choppy, None, choppy[-1].date)
    assert a[FACTOR_LOW_VOL] is not None and b[FACTOR_LOW_VOL] is not None
    assert a[FACTOR_LOW_VOL] > b[FACTOR_LOW_VOL]


def test_near_high_scores_high_proximity():
    """high_proximity = close/252d-high - 1: 0 at the high, negative below.
    A stock at its high (uptrend) must out-score one trading below it (choppy)."""
    s = build_breakout_v3_broad_strategy()
    at_high = _uptrend(260)           # ends at its own 252d high -> proximity ~ 0
    below = _choppy(260, swing=8.0)   # oscillating, last close below its max -> negative
    fa = s.compute_raw_factors(_stock(), at_high, None, at_high[-1].date)
    fb = s.compute_raw_factors(_stock(), below, None, below[-1].date)
    assert fa[FACTOR_HIGH_PROXIMITY] is not None and fb[FACTOR_HIGH_PROXIMITY] is not None
    assert fa[FACTOR_HIGH_PROXIMITY] >= Decimal("-0.01")   # essentially at the high
    assert fa[FACTOR_HIGH_PROXIMITY] > fb[FACTOR_HIGH_PROXIMITY]


# ── Insufficient history ──────────────────────────────────────────────────────

def test_short_history_yields_none_momentum():
    s = build_breakout_v3_broad_strategy()
    bars = _uptrend(50)
    f = s.compute_raw_factors(_stock(), bars, None, bars[-1].date)
    assert f[FACTOR_MOMENTUM_12M] is None


# ── Composite + determinism ───────────────────────────────────────────────────

def test_composite_in_unit_range():
    s = build_breakout_v3_broad_strategy()
    bars = _uptrend(260)
    raw = s.compute_raw_factors(_stock(), bars, None, bars[-1].date)
    norm = {k: Decimal("0.5") for k in s.factor_names() if raw.get(k) is not None}
    comp = s.composite_score(s.build_factor_scores(raw, norm, s.base_weights()))
    assert Decimal("0") <= comp <= Decimal("1")


def test_deterministic():
    s = build_breakout_v3_def_strategy()
    bars, stock = _uptrend(260), _stock()
    assert s.compute_raw_factors(stock, bars, None, bars[-1].date) == \
        s.compute_raw_factors(stock, bars, None, bars[-1].date)


def test_benchmark_not_used():
    s = build_breakout_v3_broad_strategy()
    bars = _uptrend(260)
    bench = _uptrend(260, base=18000.0, step=20.0)
    assert s.compute_raw_factors(_stock(), bars, bench, bars[-1].date) == \
        s.compute_raw_factors(_stock(), bars, None, bars[-1].date)
