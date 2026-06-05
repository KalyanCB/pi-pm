from datetime import UTC, date, datetime
from decimal import Decimal

from app.factor_analytics.weight_resolver import resolve_factor_weights
from app.models.ranking_run import RankingRun
from app.ranking.registry import RankingStrategyRegistry


def _run(metadata: dict | None = None) -> RankingRun:
    return RankingRun(
        strategy_name="breakout_v1",
        strategy_version="1.0.0",
        universe_code="PI_PM_CORE",
        as_of_date=date(2024, 6, 3),
        benchmark_symbol="^NSEI",
        filter_config_hash="x",
        normalization_method="percentile",
        status="COMPLETED",
        inputs_hash="abc",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        metadata_=metadata,
    )


def test_resolve_weights_from_metadata_first():
    runs = [
        _run({"effective_weights": {"volume_surge": "0.20", "high_proximity": "0.10"}}),
        _run({"effective_weights": {"volume_surge": "0.18", "high_proximity": "0.12"}}),
    ]
    weights = resolve_factor_weights("breakout_v1", "1.0.0", runs, RankingStrategyRegistry())
    assert weights["volume_surge"] == 0.19
    assert weights["high_proximity"] == 0.11


def test_resolve_weights_fallback_to_registry():
    weights = resolve_factor_weights("breakout_v1", "1.0.0", [], RankingStrategyRegistry())
    assert weights["volume_surge"] == float(Decimal("0.15"))
    assert len(weights) == 8


def test_resolve_weights_unknown_strategy_returns_empty():
    weights = resolve_factor_weights("unknown", "9.9.9", [], RankingStrategyRegistry())
    assert weights == {}
