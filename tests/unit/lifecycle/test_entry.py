from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.lifecycle.entry import (
    entry_strategy_for_regime,
    is_top_pick,
    should_enter,
)
from app.ranking.math_utils import PriceBar
from app.validation.regimes import classify_stock_trend

BV2 = "breakout_v2"
RV3 = "reversion_v3"


def _series(fn, n=260):
    return [PriceBar(date=date(2022, 1, 1) + timedelta(days=i), close=fn(i), volume=None) for i in range(n)]


# ── regime -> entry sleeve ────────────────────────────────────────────────────
@pytest.mark.parametrize("regime,expected", [
    ("BULL", BV2),
    ("BEAR", RV3),
    ("SIDEWAYS", RV3),   # Tier 1: chop trades mean-reversion bounces, not cash
    (None, None),
    ("GARBAGE", None),
])
def test_entry_strategy_for_regime(regime, expected):
    assert entry_strategy_for_regime(regime) == expected


# ── top-pick percentile gate ──────────────────────────────────────────────────
def test_is_top_pick():
    assert is_top_pick(5, 100, 0.20) is True      # top 5%
    assert is_top_pick(20, 100, 0.20) is True      # exactly at the 20% edge
    assert is_top_pick(21, 100, 0.20) is False     # just past it
    assert is_top_pick(None, 100, 0.20) is False
    assert is_top_pick(1, 0, 0.20) is False


# ── per-stock entry gate ──────────────────────────────────────────────────────
_TOP = dict(rank=5, pool_size=100, entry_top_pct=0.20)


def test_breakout_entry_requires_stock_uptrend():
    assert should_enter(strategy=BV2, market_regime_3way="BULL", stock_trend_3way="BULL", **_TOP) is True
    assert should_enter(strategy=BV2, market_regime_3way="BULL", stock_trend_3way="BEAR", **_TOP) is False
    assert should_enter(strategy=BV2, market_regime_3way="BULL", stock_trend_3way="SIDEWAYS", **_TOP) is False


def test_reversion_entry_skips_uptrending_names():
    assert should_enter(strategy=RV3, market_regime_3way="BEAR", stock_trend_3way="BEAR", **_TOP) is True
    assert should_enter(strategy=RV3, market_regime_3way="BEAR", stock_trend_3way="SIDEWAYS", **_TOP) is True
    assert should_enter(strategy=RV3, market_regime_3way="BEAR", stock_trend_3way="BULL", **_TOP) is False


def test_sideways_trades_bounces_and_leaders():
    # Tier 1: a washed-out name in a SIDEWAYS chop is a mean-reversion BOUNCE -> enter.
    assert should_enter(strategy=RV3, market_regime_3way="SIDEWAYS", stock_trend_3way="BEAR", **_TOP) is True
    # Tier 3: a stock in its OWN uptrend during chop is a relative-strength LEADER -> enter.
    assert should_enter(strategy=BV2, market_regime_3way="SIDEWAYS", stock_trend_3way="BULL", **_TOP) is True


def test_leader_enters_in_bear_but_bounce_not_in_bull():
    # Tier 3: breakout LEADER bucking a bear tape -> enter (own trend is BULL).
    assert should_enter(strategy=BV2, market_regime_3way="BEAR", stock_trend_3way="BULL", **_TOP) is True
    # No mean-reversion bounces in a BULL market (chase leaders instead).
    assert should_enter(strategy=RV3, market_regime_3way="BULL", stock_trend_3way="BEAR", **_TOP) is False


def test_not_a_top_pick_is_rejected():
    assert should_enter(strategy=BV2, market_regime_3way="BULL", stock_trend_3way="BULL",
                        rank=50, pool_size=100, entry_top_pct=0.20) is False


# ── classify_stock_trend ──────────────────────────────────────────────────────
def test_classify_stock_trend():
    last = date(2022, 1, 1) + timedelta(days=259)
    assert classify_stock_trend(_series(lambda i: 100 + i * 0.4), last) == "BULL"
    assert classify_stock_trend(_series(lambda i: 220 - i * 0.4), last) == "BEAR"
    # too little history
    assert classify_stock_trend(_series(lambda i: 100 + i, n=50), last) is None
