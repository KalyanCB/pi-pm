from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.ranking.math_utils import PriceBar, bars_on_or_before
from app.validation.forward_returns import compute_forward_return, quantize_return


class BarForwardReturnIndex:
    """Pre-indexed bars for O(1) forward-return lookups at multiple horizons."""

    __slots__ = ("_entry", "_entry_close", "_future")

    def __init__(self, bars: list[PriceBar], as_of_date: date) -> None:
        eligible = bars_on_or_before(bars, as_of_date)
        if not eligible:
            self._entry = None
            self._entry_close = None
            self._future = ()
            return
        entry = eligible[-1]
        if entry.close <= 0:
            self._entry = None
            self._entry_close = None
            self._future = ()
            return
        self._entry = entry
        self._entry_close = Decimal(str(entry.close))
        self._future = tuple(bar for bar in bars if bar.date > entry.date)

    def forward_return(self, forward_trading_days: int) -> Decimal | None:
        if forward_trading_days <= 0 or self._entry is None:
            return None
        if len(self._future) < forward_trading_days:
            return None
        exit_bar = self._future[forward_trading_days - 1]
        if exit_bar.close <= 0:
            return None
        return quantize_return(Decimal(str(exit_bar.close)) / self._entry_close - Decimal("1"))

    def forward_returns_through(self, max_days: int) -> dict[int, Decimal | None]:
        if self._entry is None or max_days <= 0:
            return {day: None for day in range(1, max_days + 1)}
        results: dict[int, Decimal | None] = {}
        future = self._future
        entry_close = self._entry_close
        for day in range(1, max_days + 1):
            if len(future) < day:
                results[day] = None
                continue
            exit_close = Decimal(str(future[day - 1].close))
            if exit_close <= 0:
                results[day] = None
            else:
                results[day] = quantize_return((exit_close / entry_close) - Decimal("1"))
        return results


def build_forward_return_index(bars: list[PriceBar], as_of_date: date) -> BarForwardReturnIndex:
    return BarForwardReturnIndex(bars, as_of_date)


def alpha_decay_returns_indexed(
    index: BarForwardReturnIndex,
    *,
    max_days: int,
) -> dict[int, Decimal | None]:
    return index.forward_returns_through(max_days)


def alpha_decay_returns_matches_reference(
    bars: list[PriceBar],
    as_of_date: date,
    *,
    max_days: int,
) -> bool:
    """Compare optimized path to validation.compute_forward_return for every horizon."""
    index = BarForwardReturnIndex(bars, as_of_date)
    for day in range(1, max_days + 1):
        if index.forward_return(day) != compute_forward_return(bars, as_of_date, day):
            return False
    return True
