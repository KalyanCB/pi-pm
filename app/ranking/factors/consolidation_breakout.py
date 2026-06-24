from __future__ import annotations

from decimal import Decimal

from app.ranking.math_utils import (
    PriceBar,
    average_true_range,
    rolling_max_close,
    simple_moving_average,
)
from app.ranking.models import quantize_component

RANGE_WINDOW = 20
HIGH_LOOKBACK = 63
ATR_SHORT = 14
ATR_LONG = 50


class ConsolidationBreakoutFactor:
    """Tight range, volatility contraction, and proximity to recent highs."""

    range_window: int = RANGE_WINDOW
    high_lookback: int = HIGH_LOOKBACK

    @classmethod
    def compute(cls, bars: list[PriceBar]) -> Decimal | None:
        if len(bars) < max(cls.high_lookback, ATR_LONG + 1, cls.range_window):
            return None

        compression = cls._range_compression(bars)
        contraction = cls._volatility_contraction(bars)
        proximity = cls._high_proximity(bars)
        if compression is None or contraction is None or proximity is None:
            return None

        score = compression * contraction * proximity
        return quantize_component(score)

    @classmethod
    def _range_compression(cls, bars: list[PriceBar]) -> Decimal | None:
        window = bars[-cls.range_window :]
        high = Decimal(str(max(b.close for b in window)))
        low = Decimal(str(min(b.close for b in window)))
        avg = simple_moving_average(bars, cls.range_window)
        if avg is None or avg <= 0:
            return None
        range_ratio = (high - low) / avg
        if range_ratio <= 0:
            return Decimal("1")
        return max(Decimal("0"), Decimal("1") - min(range_ratio, Decimal("1")))

    @classmethod
    def _volatility_contraction(cls, bars: list[PriceBar]) -> Decimal | None:
        short_atr = average_true_range(bars, ATR_SHORT)
        long_atr = average_true_range(bars, ATR_LONG)
        if short_atr is None or long_atr is None or short_atr <= 0:
            return None
        ratio = long_atr / short_atr
        return min(ratio, Decimal("3")) / Decimal("3")

    @classmethod
    def _high_proximity(cls, bars: list[PriceBar]) -> Decimal | None:
        rolling_high = rolling_max_close(bars, cls.high_lookback)
        if rolling_high is None or rolling_high <= 0:
            return None
        return Decimal(str(bars[-1].close)) / rolling_high
