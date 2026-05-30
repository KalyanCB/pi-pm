from decimal import Decimal

from app.validation.statistics import (
    _ScoredReturn,
    compute_horizon_metrics,
    spearman_ic,
)


def test_spearman_ic_perfect_monotonic():
    scores = [Decimal("4"), Decimal("3"), Decimal("2"), Decimal("1"), Decimal("0")]
    returns = [Decimal("0.4"), Decimal("0.3"), Decimal("0.2"), Decimal("0.1"), Decimal("0.0")]
    ic = spearman_ic(scores, returns)
    assert ic is not None
    assert ic == Decimal("1.00000000")


def test_spearman_ic_insufficient_sample():
    assert spearman_ic([Decimal("1")], [Decimal("1")]) is None


def test_decile_spread_and_hit_rates():
    items = [
        _ScoredReturn("A", Decimal("5"), 1, Decimal("0.10")),
        _ScoredReturn("B", Decimal("4"), 2, Decimal("0.08")),
        _ScoredReturn("C", Decimal("3"), 3, Decimal("0.06")),
        _ScoredReturn("D", Decimal("2"), 4, Decimal("0.04")),
        _ScoredReturn("E", Decimal("1"), 5, Decimal("0.02")),
    ]
    metrics = compute_horizon_metrics(20, items)
    assert metrics.status == "ok"
    assert metrics.ic_spearman is not None
    assert metrics.top_minus_bottom_spread is not None
    assert metrics.top_minus_bottom_spread > 0
    assert metrics.hit_rates.top_vs_bottom_hit_rate == Decimal("1.00000000")
