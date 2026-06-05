"""Portfolio performance analytics — pure functions, no DB access.

All metrics are deterministic. Same inputs → same outputs (AC-PE-13).
No LLM. No feedback into recommendation or conviction.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class NavPoint:
    date: date
    nav: float
    benchmark_nav: float | None = None


@dataclass
class PerformanceMetrics:
    # Returns
    total_return_pct: float | None
    cagr_pct: float | None
    alpha_pct: float | None

    # Risk
    volatility_pct: float | None  # annualised daily return std
    sharpe_ratio: float | None
    sortino_ratio: float | None
    max_drawdown_pct: float | None
    max_drawdown_start: date | None
    max_drawdown_end: date | None

    # Activity
    turnover_pct: float | None  # (buys + sells) / avg_nav
    win_rate: float | None
    profit_factor: float | None
    avg_holding_days: float | None

    # Exposure
    avg_exposure_pct: float | None  # avg market_value / nav
    avg_cash_pct: float | None

    # Counts
    total_closed_positions: int
    total_open_positions: int

    # Period
    from_date: date | None
    to_date: date | None
    trading_days: int


def compute_performance(
    nav_series: list[NavPoint],
    closed_outcomes: list[dict],  # [{pnl_pct, days_held, alpha_pct}, ...]
    risk_free_rate_annual: float = 0.065,  # 6.5% RBI repo rate approx
) -> PerformanceMetrics:
    """Compute full performance metrics from NAV series and closed outcomes."""

    if not nav_series:
        return _empty_metrics()

    nav_series = sorted(nav_series, key=lambda x: x.date)
    from_date = nav_series[0].date
    to_date = nav_series[-1].date
    trading_days = len(nav_series)

    first_nav = nav_series[0].nav
    last_nav = nav_series[-1].nav

    # Total return
    total_return = ((last_nav - first_nav) / first_nav * 100) if first_nav > 0 else None

    # CAGR
    years = (to_date - from_date).days / 365.25
    cagr = None
    if years > 0 and first_nav > 0 and total_return is not None:
        cagr = ((last_nav / first_nav) ** (1 / years) - 1) * 100

    # Alpha vs benchmark
    alpha = None
    bench_navs = [p.benchmark_nav for p in nav_series if p.benchmark_nav is not None]
    if bench_navs and len(bench_navs) >= 2:
        bench_return = (bench_navs[-1] - bench_navs[0]) / bench_navs[0] * 100
        if total_return is not None:
            alpha = total_return - bench_return

    # Daily returns for risk metrics
    daily_returns = []
    for i in range(1, len(nav_series)):
        prev = nav_series[i - 1].nav
        curr = nav_series[i].nav
        if prev > 0:
            daily_returns.append((curr - prev) / prev)

    volatility = None
    sharpe = None
    sortino = None
    if len(daily_returns) >= 2:
        vol_daily = statistics.stdev(daily_returns)
        volatility = vol_daily * math.sqrt(252) * 100  # annualised %
        rf_daily = risk_free_rate_annual / 252
        avg_daily = statistics.mean(daily_returns)
        if vol_daily > 0:
            sharpe = (avg_daily - rf_daily) / vol_daily * math.sqrt(252)
        # Sortino — downside deviation
        downside = [r for r in daily_returns if r < rf_daily]
        if downside:
            down_std = math.sqrt(sum((r - rf_daily) ** 2 for r in downside) / len(downside))
            if down_std > 0:
                sortino = (avg_daily - rf_daily) / down_std * math.sqrt(252)

    # Max drawdown
    max_dd, dd_start, dd_end = _compute_max_drawdown(nav_series)

    # Outcome-based metrics
    win_rate = profit_factor = avg_holding = None
    if closed_outcomes:
        wins = [o for o in closed_outcomes if o.get("pnl_pct", 0) > 0]
        losses = [o for o in closed_outcomes if o.get("pnl_pct", 0) < 0]
        win_rate = len(wins) / len(closed_outcomes) * 100

        gain_sum = sum(o.get("pnl_pct", 0) for o in wins)
        loss_sum = abs(sum(o.get("pnl_pct", 0) for o in losses))
        profit_factor = gain_sum / loss_sum if loss_sum > 0 else None

        days_vals = [o.get("days_held") for o in closed_outcomes if o.get("days_held") is not None]
        avg_holding = statistics.mean(days_vals) if days_vals else None

    return PerformanceMetrics(
        total_return_pct=round(total_return, 4) if total_return is not None else None,
        cagr_pct=round(cagr, 4) if cagr is not None else None,
        alpha_pct=round(alpha, 4) if alpha is not None else None,
        volatility_pct=round(volatility, 4) if volatility is not None else None,
        sharpe_ratio=round(sharpe, 4) if sharpe is not None else None,
        sortino_ratio=round(sortino, 4) if sortino is not None else None,
        max_drawdown_pct=round(max_dd, 4) if max_dd is not None else None,
        max_drawdown_start=dd_start,
        max_drawdown_end=dd_end,
        turnover_pct=None,  # populated by service
        win_rate=round(win_rate, 2) if win_rate is not None else None,
        profit_factor=round(profit_factor, 4) if profit_factor is not None else None,
        avg_holding_days=round(avg_holding, 1) if avg_holding is not None else None,
        avg_exposure_pct=None,
        avg_cash_pct=None,
        total_closed_positions=len(closed_outcomes),
        total_open_positions=0,
        from_date=from_date,
        to_date=to_date,
        trading_days=trading_days,
    )


def _compute_max_drawdown(
    nav_series: list[NavPoint],
) -> tuple[float | None, date | None, date | None]:
    if len(nav_series) < 2:
        return None, None, None
    peak = nav_series[0].nav
    peak_date = nav_series[0].date
    max_dd = 0.0
    dd_start = dd_end = nav_series[0].date

    for point in nav_series[1:]:
        if point.nav > peak:
            peak = point.nav
            peak_date = point.date
        dd = (peak - point.nav) / peak * 100
        if dd > max_dd:
            max_dd = dd
            dd_start = peak_date
            dd_end = point.date

    return max_dd if max_dd > 0 else None, dd_start, dd_end


def _empty_metrics() -> PerformanceMetrics:
    return PerformanceMetrics(
        total_return_pct=None,
        cagr_pct=None,
        alpha_pct=None,
        volatility_pct=None,
        sharpe_ratio=None,
        sortino_ratio=None,
        max_drawdown_pct=None,
        max_drawdown_start=None,
        max_drawdown_end=None,
        turnover_pct=None,
        win_rate=None,
        profit_factor=None,
        avg_holding_days=None,
        avg_exposure_pct=None,
        avg_cash_pct=None,
        total_closed_positions=0,
        total_open_positions=0,
        from_date=None,
        to_date=None,
        trading_days=0,
    )
