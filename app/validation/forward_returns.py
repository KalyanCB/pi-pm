from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.ranking.math_utils import PriceBar, bars_on_or_before

_QUANTIZE = Decimal("0.00000001")


def quantize_return(value: Decimal) -> Decimal:
    return value.quantize(_QUANTIZE, rounding=ROUND_HALF_UP)


def compute_forward_return(
    bars: list[PriceBar],
    as_of_date: date,
    forward_trading_days: int,
) -> Decimal | None:
    """Return over N trading days forward from as_of_date."""
    if forward_trading_days <= 0:
        return None

    eligible = bars_on_or_before(bars, as_of_date)
    if not eligible:
        return None

    entry = eligible[-1]
    if entry.close <= 0:
        return None

    future_bars = [bar for bar in bars if bar.date > entry.date]
    if len(future_bars) < forward_trading_days:
        return None

    exit_bar = future_bars[forward_trading_days - 1]
    if exit_bar.close <= 0:
        return None

    return quantize_return((exit_bar.close / entry.close) - Decimal("1"))


def compute_forward_returns(
    bars: list[PriceBar],
    as_of_date: date,
    horizons: tuple[int, ...],
) -> dict[int, Decimal | None]:
    return {horizon: compute_forward_return(bars, as_of_date, horizon) for horizon in horizons}
