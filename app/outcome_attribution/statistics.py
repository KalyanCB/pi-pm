from __future__ import annotations

import math
from statistics import stdev

from app.outcome_attribution.constants import (
    MIN_OBSERVATIONS_FOR_METRICS,
    MIN_RUNS_FOR_SHARPE,
    TRADING_DAYS_PER_YEAR,
)
from app.outcome_attribution.models import BucketMetrics

_STATUS_OK = "ok"
_STATUS_INSUFFICIENT = "insufficient_data"


def hit_rate_positive(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(1 for value in values if value > 0) / len(values)


def mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def annualized_sharpe(period_returns: list[float], horizon_days: int) -> float | None:
    if len(period_returns) < MIN_RUNS_FOR_SHARPE or horizon_days <= 0:
        return None
    avg = sum(period_returns) / len(period_returns)
    try:
        std = stdev(period_returns)
    except Exception:
        return None
    if std == 0:
        return None
    periods_per_year = TRADING_DAYS_PER_YEAR / horizon_days
    return (avg / std) * math.sqrt(periods_per_year)


def max_drawdown_compound(period_returns: list[float]) -> float | None:
    if not period_returns:
        return None
    cumulative = 1.0
    peak = 1.0
    max_dd = 0.0
    for period_return in period_returns:
        cumulative *= 1.0 + period_return
        if cumulative > peak:
            peak = cumulative
        drawdown = (peak - cumulative) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, drawdown)
    return max_dd


def rank_in_bucket(rank: int, bucket: str) -> bool:
    if bucket == "top_5":
        return 1 <= rank <= 5
    if bucket == "top_10":
        return 1 <= rank <= 10
    if bucket == "top_20":
        return 1 <= rank <= 20
    return False


def rank_in_band(rank: int, band: str) -> bool:
    if band == "rank_1_5":
        return 1 <= rank <= 5
    if band == "rank_6_10":
        return 6 <= rank <= 10
    if band == "rank_11_20":
        return 11 <= rank <= 20
    return False


def compute_bucket_metrics(
    *,
    bucket: str,
    horizon: int,
    per_run_returns: list[float],
    stock_returns: list[float],
    benchmark_returns: list[float],
) -> BucketMetrics:
    if bucket == "benchmark":
        per_run = benchmark_returns
        stock_level = benchmark_returns
    else:
        per_run = per_run_returns
        stock_level = stock_returns

    if len(per_run) < MIN_OBSERVATIONS_FOR_METRICS:
        return BucketMetrics(
            bucket=bucket,
            horizon=horizon,
            hit_rate=None,
            average_return=None,
            alpha=None,
            sharpe=None,
            max_drawdown=None,
            run_count=len(per_run),
            observation_count=len(stock_level),
            status=_STATUS_INSUFFICIENT,
        )

    avg_return = mean_or_none(per_run)
    bench_avg = mean_or_none(benchmark_returns) if bucket != "benchmark" else None
    alpha = None
    if avg_return is not None and bench_avg is not None:
        alpha = avg_return - bench_avg

    return BucketMetrics(
        bucket=bucket,
        horizon=horizon,
        hit_rate=hit_rate_positive(stock_level),
        average_return=avg_return,
        alpha=alpha if bucket != "benchmark" else 0.0,
        sharpe=annualized_sharpe(per_run, horizon),
        max_drawdown=max_drawdown_compound(per_run),
        run_count=len(per_run),
        observation_count=len(stock_level),
        status=_STATUS_OK,
    )
