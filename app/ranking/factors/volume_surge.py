from __future__ import annotations

from decimal import Decimal

from app.ranking.math_utils import PriceBar, average_volume
from app.ranking.models import quantize_component

SHORT_WINDOW = 20
LONG_WINDOW = 90


class VolumeSurgeFactor:
    """Recent participation versus longer baseline (20d / 90d average volume)."""

    short_window: int = SHORT_WINDOW
    long_window: int = LONG_WINDOW

    @classmethod
    def compute(cls, bars: list[PriceBar]) -> Decimal | None:
        short = average_volume(bars, cls.short_window)
        long = average_volume(bars, cls.long_window)
        if short is None or long is None or long <= 0:
            return None
        return quantize_component(short / long)
