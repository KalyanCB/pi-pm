"""Portfolio benchmarking — compare portfolio NAV against NIFTY 500 / NIFTY 50.

Pure functions. Deterministic. No LLM.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SeriesPoint:
    date: date
    value: float


@dataclass
class BenchmarkComparison:
    benchmark_symbol: str
    portfolio_return_pct: float | None
    benchmark_return_pct: float | None
    alpha_pct: float | None
    tracking_error_pct: float | None  # annualised std of return diffs
    information_ratio: float | None  # alpha / tracking_error
    outperformance_pct: float | None  # portfolio - benchmark
    periods: int


def _returns(series: list[SeriesPoint]) -> list[float]:
    out = []
    for i in range(1, len(series)):
        prev = series[i - 1].value
        if prev > 0:
            out.append((series[i].value - prev) / prev)
    return out


def compute_benchmark_comparison(
    portfolio_series: list[SeriesPoint],
    benchmark_series: list[SeriesPoint],
    benchmark_symbol: str = "^CRSLDX",
) -> BenchmarkComparison:
    """Compare aligned portfolio and benchmark NAV/price series.

    Both series must be sorted ascending by date. Only overlapping dates are used.
    """
    # Align on common dates
    p_map = {p.date: p.value for p in portfolio_series}
    b_map = {b.date: b.value for b in benchmark_series}
    common = sorted(set(p_map) & set(b_map))

    if len(common) < 2:
        return BenchmarkComparison(
            benchmark_symbol=benchmark_symbol,
            portfolio_return_pct=None,
            benchmark_return_pct=None,
            alpha_pct=None,
            tracking_error_pct=None,
            information_ratio=None,
            outperformance_pct=None,
            periods=len(common),
        )

    p_aligned = [SeriesPoint(d, p_map[d]) for d in common]
    b_aligned = [SeriesPoint(d, b_map[d]) for d in common]

    p_total = (p_aligned[-1].value - p_aligned[0].value) / p_aligned[0].value * 100
    b_total = (b_aligned[-1].value - b_aligned[0].value) / b_aligned[0].value * 100

    p_returns = _returns(p_aligned)
    b_returns = _returns(b_aligned)

    # Active returns (period-by-period diff)
    active = [p - b for p, b in zip(p_returns, b_returns)]

    tracking_error = None
    information_ratio = None
    if len(active) >= 2:
        te_daily = statistics.stdev(active)
        tracking_error = te_daily * math.sqrt(252) * 100
        mean_active = statistics.mean(active)
        if te_daily > 0:
            information_ratio = mean_active / te_daily * math.sqrt(252)

    alpha = p_total - b_total
    outperformance = p_total - b_total

    return BenchmarkComparison(
        benchmark_symbol=benchmark_symbol,
        portfolio_return_pct=round(p_total, 4),
        benchmark_return_pct=round(b_total, 4),
        alpha_pct=round(alpha, 4),
        tracking_error_pct=round(tracking_error, 4) if tracking_error is not None else None,
        information_ratio=round(information_ratio, 4) if information_ratio is not None else None,
        outperformance_pct=round(outperformance, 4),
        periods=len(common),
    )
