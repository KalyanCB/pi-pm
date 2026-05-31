from decimal import Decimal

from app.validation.campaign_aggregator import pick_best_worst_horizons
from app.validation.models import FullHorizonMetrics


def _metric(horizon: int, spread: str) -> FullHorizonMetrics:
    value = Decimal(spread)
    return FullHorizonMetrics(
        horizon=horizon,
        status="ok",
        ic_pearson=value,
        rank_ic_spearman=value,
        hit_rate=value,
        directional_hit_rate=value,
        top_decile_return=value,
        bottom_decile_return=Decimal("0"),
        spread=value,
        top_20_return=value,
        top_50_return=value,
        deciles=(),
        is_monotonic=True,
        sample_size=100,
        ranked_days=10,
    )


def test_pick_best_worst_horizons_by_spread():
    metrics = {
        5: _metric(5, "0.01"),
        10: _metric(10, "0.05"),
        20: _metric(20, "0.03"),
        60: _metric(60, "-0.02"),
    }
    best, worst = pick_best_worst_horizons(metrics)
    assert best == 10
    assert worst == 60
