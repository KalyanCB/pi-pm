from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import mean


@dataclass(frozen=True)
class PriceBar:
    date: date
    close: float  # native float — ranking only needs relative ordering, not accounting precision
    volume: int | None


def price_value(bar: PriceBar) -> Decimal:
    return Decimal(str(bar.close))


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
    return Decimal(str(mean(b.close for b in bars[-window:])))


def total_return(bars: list[PriceBar], lookback: int) -> Decimal | None:
    if len(bars) < lookback + 1:
        return None
    start = bars[-(lookback + 1)].close
    end = bars[-1].close
    if start <= 0:
        return None
    return Decimal(str(float(end) / float(start) - 1.0))


def daily_log_returns(bars: list[PriceBar]) -> list[Decimal]:
    returns: list[Decimal] = []
    for prev, curr in zip(bars, bars[1:], strict=False):
        if prev.close <= 0 or curr.close <= 0:
            continue
        ratio = curr.close / prev.close
        if ratio <= 0:
            continue
        returns.append(Decimal(str(math.log(ratio))))
    return returns


def annualized_volatility(bars: list[PriceBar], lookback: int) -> Decimal | None:
    window = bars[-(lookback + 1):]
    if len(window) < lookback + 1:
        return None
    # Compute in float for speed, wrap result in Decimal for pipeline compatibility
    closes = [b.close for b in window]
    log_returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0 and closes[i] > 0:
            log_returns.append(math.log(closes[i] / closes[i - 1]))
    if len(log_returns) < 2:
        return None
    avg = mean(log_returns)
    variance = mean((r - avg) ** 2 for r in log_returns)
    if variance <= 0:
        return None
    return Decimal(str(math.sqrt(variance) * math.sqrt(252)))


def average_volume(bars: list[PriceBar], window: int) -> Decimal | None:
    if len(bars) < window:
        return None
    volumes = [b.volume for b in bars[-window:] if b.volume is not None]
    if not volumes:
        return None
    return Decimal(str(mean(volumes)))


def rolling_max_close(bars: list[PriceBar], window: int) -> Decimal | None:
    if len(bars) < window:
        return None
    return Decimal(str(max(b.close for b in bars[-window:])))


def rolling_min_close(bars: list[PriceBar], window: int) -> Decimal | None:
    if len(bars) < window:
        return None
    return Decimal(str(min(b.close for b in bars[-window:])))


def average_true_range(bars: list[PriceBar], window: int) -> Decimal | None:
    if len(bars) < window + 1:
        return None
    window_bars = bars[-(window + 1):]
    ranges: list[float] = []
    for prev, curr in zip(window_bars, window_bars[1:], strict=False):
        ranges.append(abs(curr.close - prev.close))
    if not ranges:
        return None
    return Decimal(str(mean(ranges[-window:])))


def relative_strength_spread(
    stock_bars: list[PriceBar],
    bench_bars: list[PriceBar],
    lookback: int,
) -> Decimal | None:
    stock_ret = total_return(stock_bars, lookback)
    bench_ret = total_return(bench_bars, lookback)
    if stock_ret is None or bench_ret is None:
        return None
    return stock_ret - bench_ret
