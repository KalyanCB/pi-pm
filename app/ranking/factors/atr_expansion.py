from __future__ import annotations

from decimal import Decimal

from app.ranking.math_utils import PriceBar, average_true_range
from app.ranking.models import quantize_component

ATR_SHORT = 14
ATR_LONG = 50


class AtrExpansionFactor:
    """Short-term versus long-term average true range (close-based proxy)."""

    short_window: int = ATR_SHORT
    long_window: int = ATR_LONG

    @classmethod
    def compute(cls, bars: list[PriceBar]) -> Decimal | None:
        short_atr = average_true_range(bars, cls.short_window)
        long_atr = average_true_range(bars, cls.long_window)
        if short_atr is None or long_atr is None or long_atr <= 0:
            return None
        return quantize_component(short_atr / long_atr)
