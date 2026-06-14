"""Deterministic trade levels for recommendations (ADR-034).

Pure functions — no DB, no LLM. The recommendation engine stays price-blind;
this module decorates BUY rows with an entry range and a stop-loss range using
freshly-ingested OHLCV. Stop levels reuse the same advisory/critical percentages
the exit monitor applies, so pre-trade and in-trade stops are consistent.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class _Bar(Protocol):
    high: object
    low: object
    close: object
    date: object


@dataclass(frozen=True)
class TradeLevels:
    reference_close: float
    atr_pct: float | None
    entry_low: float
    entry_high: float
    stop_advisory: float
    stop_critical: float
    basis: str  # "actionable" (BUY) | "indicative" (WATCH)


def atr_pct_from_bars(bars: Sequence[_Bar], *, period: int = 14) -> float | None:
    """Average True Range as a percent of the latest close.

    Robust to input ordering (sorts ascending by date internally). Returns None
    when there is insufficient or malformed OHLC data.
    """
    rows = sorted(
        (b for b in bars if b.high is not None and b.low is not None and b.close is not None),
        key=lambda b: b.date,
    )
    if len(rows) < 2:
        return None

    true_ranges: list[float] = []
    for prev, cur in zip(rows, rows[1:], strict=False):
        high, low, prev_close = float(cur.high), float(cur.low), float(prev.close)
        true_ranges.append(
            max(high - low, abs(high - prev_close), abs(low - prev_close))
        )
    if not true_ranges:
        return None

    window = true_ranges[-period:] if period > 0 else true_ranges
    atr = sum(window) / len(window)
    last_close = float(rows[-1].close)
    if last_close <= 0:
        return None
    return round(atr / last_close * 100.0, 4)


def compute_trade_levels(
    *,
    reference_close: float,
    atr_pct: float | None,
    advisory_stop_pct: float,
    critical_stop_pct: float,
    entry_band_atr_mult: float,
    entry_band_pct_fallback: float,
    basis: str = "actionable",
) -> TradeLevels | None:
    """Entry range + stop-loss range off a reference close.

    - Entry band half-width = ``entry_band_atr_mult × ATR%`` of close when ATR is
      available, else ``entry_band_pct_fallback%`` of close.
    - Stops = close × (1 + advisory/critical_stop_pct/100). The stop percentages
      are negative (e.g. -8, -10), so stops land below the close.

    Returns None when ``reference_close`` is non-positive (cannot price levels).
    """
    if reference_close is None or reference_close <= 0:
        return None

    if atr_pct is not None and atr_pct > 0:
        half_width = entry_band_atr_mult * (atr_pct / 100.0) * reference_close
    else:
        half_width = (entry_band_pct_fallback / 100.0) * reference_close

    return TradeLevels(
        reference_close=round(reference_close, 2),
        atr_pct=atr_pct,
        entry_low=round(reference_close - half_width, 2),
        entry_high=round(reference_close + half_width, 2),
        stop_advisory=round(reference_close * (1.0 + advisory_stop_pct / 100.0), 2),
        stop_critical=round(reference_close * (1.0 + critical_stop_pct / 100.0), 2),
        basis=basis,
    )
