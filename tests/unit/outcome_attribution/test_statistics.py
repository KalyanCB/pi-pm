from __future__ import annotations

import pytest

from app.outcome_attribution.statistics import (
    annualized_sharpe,
    compute_bucket_metrics,
    hit_rate_positive,
    max_drawdown_compound,
    mean_or_none,
    rank_in_band,
    rank_in_bucket,
)


def test_rank_in_bucket_and_band():
    assert rank_in_bucket(3, "top_5")
    assert rank_in_bucket(8, "top_10")
    assert not rank_in_bucket(21, "top_20")
    assert rank_in_band(4, "rank_1_5")
    assert rank_in_band(9, "rank_6_10")
    assert rank_in_band(15, "rank_11_20")


def test_hit_rate_positive():
    assert hit_rate_positive([0.01, -0.02, 0.03]) == pytest.approx(2 / 3)
    assert hit_rate_positive([]) is None


def test_mean_or_none():
    assert mean_or_none([0.1, 0.2]) == pytest.approx(0.15)
    assert mean_or_none([]) is None


def test_annualized_sharpe_positive():
    returns = [0.02, 0.01, 0.03, 0.015, 0.025]
    sharpe = annualized_sharpe(returns, horizon_days=20)
    assert sharpe is not None
    assert sharpe > 0


def test_annualized_sharpe_insufficient():
    assert annualized_sharpe([0.01], horizon_days=20) is None


def test_max_drawdown_compound():
    # Peak then drawdown
    dd = max_drawdown_compound([0.10, -0.05, -0.05])
    assert dd is not None
    assert dd > 0
    assert max_drawdown_compound([]) is None


def test_compute_bucket_metrics_alpha():
    metrics = compute_bucket_metrics(
        bucket="top_5",
        horizon=20,
        per_run_returns=[0.04, 0.02, 0.06],
        stock_returns=[0.05, 0.03, 0.04, 0.02, 0.06, 0.01],
        benchmark_returns=[0.01, 0.01, 0.02],
    )
    assert metrics.status == "ok"
    assert metrics.average_return == pytest.approx(0.04)
    assert metrics.alpha == pytest.approx(0.04 - (0.01 + 0.01 + 0.02) / 3)
    assert metrics.hit_rate == pytest.approx(1.0)
    assert metrics.sharpe is not None


def test_compute_bucket_metrics_benchmark():
    metrics = compute_bucket_metrics(
        bucket="benchmark",
        horizon=20,
        per_run_returns=[0.01, 0.02],
        stock_returns=[0.01, 0.02],
        benchmark_returns=[0.01, 0.02],
    )
    assert metrics.alpha == pytest.approx(0.0)


def test_compute_bucket_metrics_insufficient():
    metrics = compute_bucket_metrics(
        bucket="top_5",
        horizon=20,
        per_run_returns=[],
        stock_returns=[],
        benchmark_returns=[],
    )
    assert metrics.status == "insufficient_data"
    assert metrics.average_return is None
