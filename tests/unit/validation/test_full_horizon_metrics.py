from decimal import Decimal

from app.validation.statistics import (
    _ScoredReturn,
    compute_full_horizon_metrics,
    compute_top_n_return,
    is_decile_monotonic,
    pearson_ic,
)


def test_pearson_ic_perfect_positive():
    scores = [Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4"), Decimal("5")]
    returns = [Decimal("0.1"), Decimal("0.2"), Decimal("0.3"), Decimal("0.4"), Decimal("0.5")]
    ic = pearson_ic(scores, returns)
    assert ic is not None
    assert ic == Decimal("1.00000000")


def test_compute_full_horizon_metrics_includes_portfolio_fields():
    items = [
        _ScoredReturn("A", Decimal("10"), 1, Decimal("0.20")),
        _ScoredReturn("B", Decimal("9"), 2, Decimal("0.18")),
        _ScoredReturn("C", Decimal("8"), 3, Decimal("0.16")),
        _ScoredReturn("D", Decimal("7"), 4, Decimal("0.14")),
        _ScoredReturn("E", Decimal("6"), 5, Decimal("0.12")),
        _ScoredReturn("F", Decimal("1"), 6, Decimal("0.02")),
    ]
    metrics = compute_full_horizon_metrics(20, items, ranked_days=3)
    assert metrics.status == "ok"
    assert metrics.ic_pearson is not None
    assert metrics.rank_ic_spearman is not None
    assert metrics.top_20_return == compute_top_n_return(items, 20)
    assert metrics.spread is not None
    assert metrics.spread > 0
    assert metrics.is_monotonic is True
    assert metrics.ranked_days == 3
    assert all(bucket.win_rate is not None for bucket in metrics.deciles)


def test_is_decile_monotonic_detects_non_monotonic():
    from app.validation.models import DecileBucket

    monotonic = (
        DecileBucket(1, 10, Decimal("0.10"), Decimal("0.09"), Decimal("0.60")),
        DecileBucket(2, 10, Decimal("0.05"), Decimal("0.04"), Decimal("0.55")),
    )
    non_monotonic = (
        DecileBucket(1, 10, Decimal("0.05"), Decimal("0.04"), Decimal("0.50")),
        DecileBucket(2, 10, Decimal("0.10"), Decimal("0.09"), Decimal("0.60")),
    )
    assert is_decile_monotonic(monotonic) is True
    assert is_decile_monotonic(non_monotonic) is False
