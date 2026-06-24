from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.ranking.math_utils import (
    PriceBar,
    annualized_volatility,
    bars_on_or_before,
    simple_moving_average,
)
from app.validation.constants import (
    REGIME_MA_WINDOW,
    REGIME_VOL_WINDOW,
    TREND_REGIME_BEAR,
    TREND_REGIME_BULL,
    VOL_REGIME_HIGH,
    VOL_REGIME_LOW,
)
from app.validation.models import RegimeClassification

_SMA50_WINDOW = 50
_DRAWDOWN_BEAR_THRESHOLD = 0.10  # 10% from 52-week high → BEAR
_52W_WINDOW = 252
_BREADTH_BEAR_THRESHOLD = 0.45  # P-14: <45% of universe above 50-SMA → BEAR


def classify_regime(
    benchmark_bars: list[PriceBar],
    as_of_date: date,
    high_vol_threshold: Decimal,
    breadth_pct: float | None = None,
) -> RegimeClassification | None:
    bars = bars_on_or_before(benchmark_bars, as_of_date)
    if len(bars) < REGIME_MA_WINDOW:
        return None

    close = bars[-1].close
    ma200 = simple_moving_average(bars, REGIME_MA_WINDOW)
    if ma200 is None:
        return None

    # Primary signal: close vs 200-day SMA
    bear_200 = close < ma200

    # Secondary signal: 50-day SMA death cross (SMA50 < SMA200)
    ma50 = simple_moving_average(bars, _SMA50_WINDOW)
    bear_death_cross = (ma50 is not None) and (ma50 < ma200)

    # Tertiary signal: >10% drawdown from 52-week high
    lookback = bars[-_52W_WINDOW:] if len(bars) >= _52W_WINDOW else bars
    peak = max(b.close for b in lookback)
    bear_drawdown = float(close) < float(peak) * (1 - _DRAWDOWN_BEAR_THRESHOLD)

    # P-14: market-breadth signal — fires 1-3 weeks earlier than the index-level
    # signals because mid/small caps break their 50-SMA well before the NIFTY-50
    # index crosses its 200-SMA. Directly addresses the 2024-H1 failure where the
    # large-cap regime stayed BULL while the traded small/mid-cap universe corrected.
    bear_breadth = breadth_pct is not None and breadth_pct < _BREADTH_BEAR_THRESHOLD

    # BEAR if any signal fires — gives earlier warning than 200 SMA alone
    trend = (
        TREND_REGIME_BEAR
        if (bear_200 or bear_death_cross or bear_drawdown or bear_breadth)
        else TREND_REGIME_BULL
    )

    vol = annualized_volatility(bars, REGIME_VOL_WINDOW)
    if vol is None:
        vol_regime = VOL_REGIME_LOW
    else:
        vol_regime = VOL_REGIME_HIGH if vol >= high_vol_threshold else VOL_REGIME_LOW

    return RegimeClassification(
        trend_regime=trend,
        vol_regime=vol_regime,
        regime_label=f"{trend}_{vol_regime}",
    )
