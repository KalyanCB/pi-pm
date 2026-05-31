from __future__ import annotations

from decimal import Decimal

from app.ranking.math_utils import PriceBar, relative_strength_spread
from app.ranking.models import quantize_component

RS_LOOKBACK = 63
ACCELERATION_LAG = 20


class RelativeStrengthAccelerationFactor:
    """Change in relative strength versus benchmark over the prior 20 sessions."""

    rs_lookback: int = RS_LOOKBACK
    lag: int = ACCELERATION_LAG

    @classmethod
    def compute(
        cls,
        stock_bars: list[PriceBar],
        benchmark_bars: list[PriceBar],
    ) -> Decimal | None:
        min_bars = cls.rs_lookback + cls.lag + 1
        if len(stock_bars) < min_bars or len(benchmark_bars) < min_bars:
            return None

        rs_today = relative_strength_spread(stock_bars, benchmark_bars, cls.rs_lookback)
        stock_lagged = stock_bars[: -cls.lag]
        bench_lagged = benchmark_bars[: -cls.lag]
        rs_lagged = relative_strength_spread(stock_lagged, bench_lagged, cls.rs_lookback)
        if rs_today is None or rs_lagged is None:
            return None
        return quantize_component(rs_today - rs_lagged)
