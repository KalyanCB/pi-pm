from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import mean


@dataclass(frozen=True)
class PriceBar:
    date: date
    close: Decimal
    volume: int | None


def price_value(bar: PriceBar) -> Decimal:
    return bar.close


def bars_on_or_before(bars: list[PriceBar], as_of_date: date) -> list[PriceBar]:
    eligible = [b for b in bars if b.date <= as_of_date]
    eligible.sort(key=lambda b: b.date)
    return eligible


def latest_bar(bars: list[PriceBar], as_of_date: date) -> PriceBar | None:
    eligible = bars_on_or_before(bars, as_of_date)
    return eligible[-1] if eligible else None


def simple_moving_average(bars: list[PriceBar], window: int) -> Decimal | None:
    if len(bars) < window:
        return None
    window_bars = bars[-window:]
    return Decimal(str(mean(float(b.close) for b in window_bars)))


def total_return(bars: list[PriceBar], lookback: int) -> Decimal | None:
    if len(bars) < lookback + 1:
        return None
    start = bars[-(lookback + 1)].close
    end = bars[-1].close
    if start <= 0:
        return None
    return (end / start) - Decimal("1")


def daily_log_returns(bars: list[PriceBar]) -> list[Decimal]:
    returns: list[Decimal] = []
    for prev, curr in zip(bars, bars[1:], strict=False):
        if prev.close <= 0 or curr.close <= 0:
            continue
        ratio = curr.close / prev.close
        if ratio <= 0:
            continue
        returns.append(Decimal(str(math.log(float(ratio)))))
    return returns


def annualized_volatility(bars: list[PriceBar], lookback: int) -> Decimal | None:
    window = bars[-(lookback + 1) :]
    if len(window) < lookback + 1:
        return None
    returns = daily_log_returns(window)
    if len(returns) < 2:
        return None
    avg = Decimal(str(mean(float(r) for r in returns)))
    variance = Decimal(str(mean(float((r - avg) ** 2) for r in returns)))
    if variance <= 0:
        return None
    return variance.sqrt() * Decimal(str(252)).sqrt()


def average_volume(bars: list[PriceBar], window: int) -> Decimal | None:
    if len(bars) < window:
        return None
    volumes = [b.volume for b in bars[-window:] if b.volume is not None]
    if not volumes:
        return None
    return Decimal(str(mean(volumes)))
