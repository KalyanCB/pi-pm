from decimal import Decimal

from app.regime_policy.metrics import compute_pooled_period_metrics
from app.validation.statistics import _ScoredReturn


def test_pooled_period_metrics_large_sample_is_fast():
    """Regression: pooled metrics must not use O(n²) directional hit rate."""
    n = 2000
    scored = [
        _ScoredReturn(
            symbol=f"S{i}",
            score=Decimal(str(n - i)),
            rank=i + 1,
            forward_return=Decimal("0.001") * Decimal(i % 10 - 5),
        )
        for i in range(n)
    ]
    result = compute_pooled_period_metrics(
        scored,
        horizon=20,
        ranked_days=10,
        daily_returns=[0.01] * 10,
    )
    assert result["sample_count"] == n
    assert result["status"] == "ok"
    assert result["ic_spearman"] is not None
