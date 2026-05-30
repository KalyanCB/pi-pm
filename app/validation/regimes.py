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


def classify_regime(
    benchmark_bars: list[PriceBar],
    as_of_date: date,
    high_vol_threshold: Decimal,
) -> RegimeClassification | None:
    bars = bars_on_or_before(benchmark_bars, as_of_date)
    if len(bars) < REGIME_MA_WINDOW:
        return None

    close = bars[-1].close
    ma200 = simple_moving_average(bars, REGIME_MA_WINDOW)
    if ma200 is None:
        return None

    trend = TREND_REGIME_BULL if close > ma200 else TREND_REGIME_BEAR

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
