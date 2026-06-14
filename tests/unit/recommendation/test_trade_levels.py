"""ADR-034: deterministic trade-levels unit tests."""

from dataclasses import dataclass
from datetime import date

import pytest

from app.recommendation.trade_levels import (
    atr_pct_from_bars,
    compute_trade_levels,
)


@dataclass
class _Bar:
    date: date
    high: float | None
    low: float | None
    close: float | None


# ── ATR ───────────────────────────────────────────────────────────────────────


def test_atr_pct_constant_range():
    # Each session spans exactly 10 around a 100 close → TR=10, ATR%=10.
    bars = [
        _Bar(date(2026, 6, d), high=105.0, low=95.0, close=100.0) for d in range(1, 8)
    ]
    assert atr_pct_from_bars(bars, period=14) == pytest.approx(10.0)


def test_atr_pct_order_independent():
    bars = [
        _Bar(date(2026, 6, 1), 102, 98, 100),
        _Bar(date(2026, 6, 2), 104, 100, 103),
        _Bar(date(2026, 6, 3), 101, 97, 99),
    ]
    forward = atr_pct_from_bars(bars)
    assert atr_pct_from_bars(list(reversed(bars))) == pytest.approx(forward)


def test_atr_pct_insufficient_or_malformed():
    assert atr_pct_from_bars([]) is None
    assert atr_pct_from_bars([_Bar(date(2026, 6, 1), 10, 9, 9.5)]) is None  # 1 bar
    bad = [_Bar(date(2026, 6, 1), None, None, 100), _Bar(date(2026, 6, 2), None, None, 100)]
    assert atr_pct_from_bars(bad) is None


# ── Trade levels ──────────────────────────────────────────────────────────────


def test_levels_atr_band_and_stop_range():
    levels = compute_trade_levels(
        reference_close=100.0,
        atr_pct=10.0,
        advisory_stop_pct=-8.0,
        critical_stop_pct=-10.0,
        entry_band_atr_mult=0.5,
        entry_band_pct_fallback=1.0,
    )
    assert levels is not None
    # half-width = 0.5 × 10% × 100 = 5
    assert levels.entry_low == pytest.approx(95.0)
    assert levels.entry_high == pytest.approx(105.0)
    # stops reuse advisory/critical pct off the close
    assert levels.stop_advisory == pytest.approx(92.0)
    assert levels.stop_critical == pytest.approx(90.0)
    # stop range is below entry; critical below advisory
    assert levels.stop_critical < levels.stop_advisory < levels.entry_low
    assert levels.basis == "actionable"


def test_levels_fallback_band_when_atr_missing():
    levels = compute_trade_levels(
        reference_close=200.0,
        atr_pct=None,
        advisory_stop_pct=-8.0,
        critical_stop_pct=-10.0,
        entry_band_atr_mult=0.5,
        entry_band_pct_fallback=1.0,
    )
    assert levels is not None
    # fallback half-width = 1% × 200 = 2
    assert levels.entry_low == pytest.approx(198.0)
    assert levels.entry_high == pytest.approx(202.0)
    assert levels.atr_pct is None


def test_levels_none_for_nonpositive_close():
    assert (
        compute_trade_levels(
            reference_close=0.0,
            atr_pct=5.0,
            advisory_stop_pct=-8.0,
            critical_stop_pct=-10.0,
            entry_band_atr_mult=0.5,
            entry_band_pct_fallback=1.0,
        )
        is None
    )


def test_levels_rounded_to_2dp():
    levels = compute_trade_levels(
        reference_close=1234.567,
        atr_pct=3.3,
        advisory_stop_pct=-8.0,
        critical_stop_pct=-10.0,
        entry_band_atr_mult=0.5,
        entry_band_pct_fallback=1.0,
    )
    assert levels is not None
    for v in (levels.reference_close, levels.entry_low, levels.entry_high,
              levels.stop_advisory, levels.stop_critical):
        assert round(v, 2) == v
