from datetime import UTC, date, datetime
from uuid import uuid4

from app.factor_analytics.constants import DATASET_SPLIT_HOLDOUT, DATASET_SPLIT_TRAIN
from app.factor_analytics.reports import build_leaderboard, build_train_holdout_drift
from app.models.factor_analytics import FactorPerformanceMetric


def _metric(
    *,
    factor_name: str,
    ic: float,
    dataset_split: str,
    stability: float = 0.8,
    coverage: float = 0.2,
) -> FactorPerformanceMetric:
    return FactorPerformanceMetric(
        id=uuid4(),
        factor_name=factor_name,
        strategy_name="breakout_v1",
        strategy_version="1.0.0",
        universe_code="PI_PM_CORE",
        horizon=20,
        regime_label="BULL_LOW_VOL",
        dataset_split=dataset_split,
        ic_spearman=ic,
        ic_pearson=ic,
        hit_rate=0.55,
        spread_contribution=0.02,
        sample_size=100,
        ranked_days=20,
        regime_coverage_pct=coverage,
        stability_score=stability,
        stability_label="stable",
        coverage_label="adequate_coverage",
        bootstrap_ci_lower=0.01,
        bootstrap_ci_upper=0.05,
        p_value=0.01,
        is_statistically_significant=True,
        confidence="high",
        bootstrap_sample_count=1000,
        bootstrap_method="daily_ic_resample_with_replacement",
        holdout_start_date=date(2025, 1, 1),
        as_of_date_start=date(2024, 1, 1),
        as_of_date_end=date(2024, 12, 31),
        computed_at=datetime.now(UTC),
    )


def test_leaderboard_sorts_by_ic_and_exposes_drift():
    holdout = [
        _metric(factor_name="alpha", ic=0.08, dataset_split=DATASET_SPLIT_HOLDOUT),
        _metric(factor_name="beta", ic=0.04, dataset_split=DATASET_SPLIT_HOLDOUT),
    ]
    train = {
        "alpha": _metric(factor_name="alpha", ic=0.10, dataset_split=DATASET_SPLIT_TRAIN),
        "beta": _metric(factor_name="beta", ic=0.05, dataset_split=DATASET_SPLIT_TRAIN),
    }
    payload = build_leaderboard(
        holdout,
        weights={"alpha": 0.2, "beta": 0.1},
        train_by_factor=train,
        sort_by="ic_spearman",
    )
    entries = payload["entries"]
    assert entries[0]["factor_name"] == "alpha"
    assert entries[0]["train_ic"] == 0.10
    assert entries[0]["holdout_ic"] == 0.08
    assert entries[0]["ic_drift"] == 0.02
    assert entries[0]["current_weight"] == 0.2


def test_train_holdout_drift_verdicts():
    train = [
        _metric(factor_name="good", ic=0.06, dataset_split=DATASET_SPLIT_TRAIN),
        _metric(factor_name="weak", ic=0.01, dataset_split=DATASET_SPLIT_TRAIN),
    ]
    holdout = [
        _metric(factor_name="good", ic=0.04, dataset_split=DATASET_SPLIT_HOLDOUT),
        _metric(factor_name="weak", ic=0.02, dataset_split=DATASET_SPLIT_HOLDOUT),
    ]
    entries = build_train_holdout_drift(train, holdout, min_train_ic=0.03)
    by_name = {entry.factor_name: entry for entry in entries}
    assert "weak" not in by_name
    assert by_name["good"].verdict == "holdout_confirmed"
