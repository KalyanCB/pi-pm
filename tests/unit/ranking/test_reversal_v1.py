"""Unit tests for ReversalV1Strategy (reversal_v1)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.ranking.math_utils import PriceBar
from app.ranking.strategies.reversal_v1 import DEFAULT_WEIGHTS, HISTORY_DAYS, ReversalV1Strategy
from app.universe.models import StockSnapshot


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stock() -> StockSnapshot:
    return StockSnapshot(
        stock_id=uuid.uuid4(), symbol="TEST.NS", name="Test",
        exchange="NSE", sector="Test", data_status="ACTIVE", is_active=True,
    )


def _trending_up_bars(n: int, *, base: float = 100.0, daily_gain: float = 0.5) -> list[PriceBar]:
    """Bars trending steadily upward — low anti_momentum score (good momentum = bad reversal candidate)."""
    bars, price = [], Decimal(str(base))
    start = date(2023, 1, 1)
    for i in range(n):
        price += Decimal(str(daily_gain))
        bars.append(PriceBar(date=start + timedelta(days=i), close=price, volume=1_000_000))
    return bars


def _falling_bars(n: int, *, base: float = 200.0, daily_loss: float = 0.3) -> list[PriceBar]:
    """Bars trending steadily downward — high anti_momentum score (oversold)."""
    bars, price = [], Decimal(str(base))
    start = date(2023, 1, 1)
    for i in range(n):
        price = max(price - Decimal(str(daily_loss)), Decimal("1"))
        bars.append(PriceBar(date=start + timedelta(days=i), close=price, volume=1_000_000))
    return bars


def _flat_volume_bars(n: int, volume: int = 1_000_000) -> list[PriceBar]:
    bars, price = [], Decimal("100")
    start = date(2023, 1, 1)
    for i in range(n):
        price += Decimal("0.1") * (1 if i % 2 == 0 else -1)
        bars.append(PriceBar(date=start + timedelta(days=i), close=price, volume=volume))
    return bars


def _high_recent_volume_bars(n: int) -> list[PriceBar]:
    """Low initial volume, high recent volume = volume surge = low_volume_surge score."""
    bars, price = [], Decimal("100")
    start = date(2023, 1, 1)
    for i in range(n):
        price += Decimal("0.1") * (1 if i % 2 == 0 else -1)
        vol = 5_000_000 if i >= n - 20 else 500_000  # spike in last 20 days
        bars.append(PriceBar(date=start + timedelta(days=i), close=price, volume=vol))
    return bars


# ── Identity ──────────────────────────────────────────────────────────────────

def test_strategy_name():
    assert ReversalV1Strategy().name == "reversal_v1"


def test_strategy_version():
    assert ReversalV1Strategy().version == "1.0.0"


# ── Requirements ──────────────────────────────────────────────────────────────

def test_required_history_days():
    assert ReversalV1Strategy().requirements().required_history_days == 253
    assert HISTORY_DAYS == 253


# ── Factor structure ──────────────────────────────────────────────────────────

def test_four_factors():
    assert len(ReversalV1Strategy().factor_names()) == 4


def test_factor_names():
    s = ReversalV1Strategy()
    assert "anti_momentum" in s.factor_names()
    assert "anti_rs" in s.factor_names()
    assert "low_proximity" in s.factor_names()
    assert "low_volume_surge" in s.factor_names()


def test_weights_sum_to_one():
    total = sum(ReversalV1Strategy().base_weights().values())
    assert abs(float(total) - 1.0) < 1e-9


def test_default_weights():
    assert DEFAULT_WEIGHTS["anti_momentum"]    == Decimal("0.35")
    assert DEFAULT_WEIGHTS["anti_rs"]          == Decimal("0.30")
    assert DEFAULT_WEIGHTS["low_proximity"]    == Decimal("0.25")
    assert DEFAULT_WEIGHTS["low_volume_surge"] == Decimal("0.10")


# ── Core property: falling stock ranks higher than rising stock ───────────────

def test_falling_stock_higher_anti_momentum_than_rising():
    s = ReversalV1Strategy()
    falling = _falling_bars(270)
    rising  = _trending_up_bars(270)
    as_of   = falling[-1].date

    fall_f = s.compute_raw_factors(_stock(), falling, None, as_of)
    rise_f = s.compute_raw_factors(_stock(), rising,  None, as_of)

    assert fall_f["anti_momentum"] is not None
    assert rise_f["anti_momentum"] is not None
    assert fall_f["anti_momentum"] > rise_f["anti_momentum"]


def test_falling_stock_higher_low_proximity():
    """A stock near its 52w low scores higher than one near its 52w high."""
    s = ReversalV1Strategy()
    falling = _falling_bars(270)
    rising  = _trending_up_bars(270)
    as_of   = falling[-1].date

    fall_f = s.compute_raw_factors(_stock(), falling, None, as_of)
    rise_f = s.compute_raw_factors(_stock(), rising,  None, as_of)

    assert fall_f["low_proximity"] is not None
    assert rise_f["low_proximity"] is not None
    assert fall_f["low_proximity"] > rise_f["low_proximity"]


def test_low_volume_stock_higher_than_high_volume():
    """Quiet stock (suppressed volume) ranks higher than volume-spiking stock."""
    s     = ReversalV1Strategy()
    quiet = _flat_volume_bars(270, volume=500_000)
    crowd = _high_recent_volume_bars(270)
    as_of = quiet[-1].date

    quiet_f = s.compute_raw_factors(_stock(), quiet, None, as_of)
    crowd_f = s.compute_raw_factors(_stock(), crowd, None, as_of)

    assert quiet_f["low_volume_surge"] is not None
    assert crowd_f["low_volume_surge"] is not None
    assert quiet_f["low_volume_surge"] > crowd_f["low_volume_surge"]


# ── anti_rs requires benchmark ────────────────────────────────────────────────

def test_anti_rs_none_without_benchmark():
    s    = ReversalV1Strategy()
    bars = _falling_bars(270)
    f    = s.compute_raw_factors(_stock(), bars, None, bars[-1].date)
    assert f["anti_rs"] is None


def test_anti_rs_populated_with_benchmark():
    s     = ReversalV1Strategy()
    stock = _falling_bars(270)
    bench = _trending_up_bars(270, base=18000.0, daily_gain=20.0)
    f     = s.compute_raw_factors(_stock(), stock, bench, stock[-1].date)
    assert f["anti_rs"] is not None


def test_underperformer_vs_benchmark_higher_anti_rs():
    """Stock falling faster than benchmark gets higher anti_rs."""
    s         = ReversalV1Strategy()
    laggard   = _falling_bars(270, daily_loss=0.5)   # big underperformer
    outperform = _trending_up_bars(270)
    bench     = _flat_volume_bars(270)
    as_of     = laggard[-1].date

    lag_f  = s.compute_raw_factors(_stock(), laggard,    bench, as_of)
    out_f  = s.compute_raw_factors(_stock(), outperform, bench, as_of)

    assert lag_f["anti_rs"] is not None
    assert out_f["anti_rs"] is not None
    assert lag_f["anti_rs"] > out_f["anti_rs"]


# ── Insufficient history ──────────────────────────────────────────────────────

def test_all_none_with_short_history():
    s     = ReversalV1Strategy()
    short = _falling_bars(50)  # < 253 needed
    f     = s.compute_raw_factors(_stock(), short, None, short[-1].date)
    # anti_momentum needs 64 bars, low_proximity needs 253
    assert f["low_proximity"] is None


# ── Determinism ───────────────────────────────────────────────────────────────

def test_deterministic():
    s     = ReversalV1Strategy()
    bars  = _falling_bars(270)
    bench = _flat_volume_bars(270)
    stock = _stock()
    as_of = bars[-1].date
    r1    = s.compute_raw_factors(stock, bars, bench, as_of)
    r2    = s.compute_raw_factors(stock, bars, bench, as_of)
    assert r1 == r2


# ── Registry ──────────────────────────────────────────────────────────────────

def test_strategy_in_registry():
    from app.ranking.registry import RankingStrategyRegistry
    strategy = RankingStrategyRegistry().get("reversal_v1", "1.0.0")
    assert strategy.name == "reversal_v1"
