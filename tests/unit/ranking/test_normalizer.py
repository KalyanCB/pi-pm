from decimal import Decimal

from app.ranking.normalizer import percentile_normalize, redistribute_weights


def test_percentile_normalize_ties():
    values = {"A": Decimal("1"), "B": Decimal("1"), "C": Decimal("3")}
    result = percentile_normalize(values)
    assert result["A"] == result["B"]
    assert result["C"] > result["A"]


def test_redistribute_weights_without_benchmark():
    weights = {
        "volatility_adjusted_momentum": Decimal("0.40"),
        "volume_expansion": Decimal("0.25"),
        "trend_quality": Decimal("0.20"),
        "relative_strength": Decimal("0.15"),
    }
    adjusted = redistribute_weights(weights, {"relative_strength"})
    assert adjusted["volatility_adjusted_momentum"] == Decimal("0.47058824")
    assert adjusted["volume_expansion"] == Decimal("0.29411765")
    assert adjusted["trend_quality"] == Decimal("0.23529412")
