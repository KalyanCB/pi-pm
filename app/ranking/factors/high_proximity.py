from __future__ import annotations

from decimal import Decimal

from app.ranking.math_utils import PriceBar, rolling_max_close
from app.ranking.models import quantize_component

LOOKBACK_52W = 252


class FiftyTwoWeekHighFactor:
    """Distance to 52-week high; closer to zero (at high) scores higher after normalization."""

    lookback: int = LOOKBACK_52W

    @classmethod
    def compute(cls, bars: list[PriceBar]) -> Decimal | None:
        if len(bars) < cls.lookback:
            return None
        rolling_high = rolling_max_close(bars, cls.lookback)
        if rolling_high is None or rolling_high <= 0:
            return None
        close = Decimal(str(bars[-1].close))
        distance = (close / rolling_high) - Decimal("1")
        return quantize_component(distance)
