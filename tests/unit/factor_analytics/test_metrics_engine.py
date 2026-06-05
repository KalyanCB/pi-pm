from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.factor_analytics.constants import (
    BOOTSTRAP_SAMPLE_COUNT,
    DATASET_SPLIT_TRAIN,
    MIN_FACTOR_SAMPLE_SIZE,
)
from app.factor_analytics.metrics_engine import (
    FactorMetricsEngine,
    bootstrap_ic_significance,
    compute_daily_ic,
    compute_regime_coverage_pct,
    compute_stability_score,
    coverage_label,
    stability_label,
)
from app.factor_analytics.models import FactorObservation


def _obs(
    *,
    factor_value: float,
    forward_return: float,
    as_of: date = date(2024, 6, 3),
    regime: str = "BULL_LOW_VOL",
    factor_name: str = "volume_surge",
) -> FactorObservation:
    return FactorObservation(
        ranking_run_id=uuid4(),
        stock_id=uuid4(),
        factor_name=factor_name,
        normalized_factor_value=Decimal(str(factor_value)),
        factor_percentile=50.0,
        forward_return=Decimal(str(forward_return)),
        regime_label=regime,
        as_of_date=as_of,
    )


def _positive_correlation_observations(
    count: int = MIN_FACTOR_SAMPLE_SIZE,
) -> list[FactorObservation]:
    return [_obs(factor_value=i, forward_return=i * 0.01) for i in range(count)]


def test_compute_daily_ic_positive_correlation():
    observations = _positive_correlation_observations(MIN_FACTOR_SAMPLE_SIZE)
    ic = compute_daily_ic(observations)
    assert ic is not None
    assert ic > 0.9


def test_compute_daily_ic_insufficient_sample():
    observations = _positive_correlation_observations(10)
    assert compute_daily_ic(observations) is None


def test_stability_score_labels():
    assert compute_stability_score([0.1, 0.2, -0.1, 0.3]) == 0.75
    assert stability_label(0.75) == "stable"
    assert stability_label(0.60) == "moderate"
    assert stability_label(0.40) == "unstable"


def test_coverage_labels():
    assert coverage_label(0.03) == "sparse_regime"
    assert coverage_label(0.10) == "low_coverage"
    assert coverage_label(0.20) == "adequate_coverage"
    assert compute_regime_coverage_pct(2, 10) == 0.2


def test_bootstrap_significance_positive_series():
    daily_ics = [0.05, 0.04, 0.06, 0.03, 0.05, 0.07, 0.04, 0.05]
    point, lower, upper, p_value, significant = bootstrap_ic_significance(
        daily_ics, n_bootstrap=200, seed=42
    )
    assert point is not None and point > 0
    assert lower is not None and upper is not None
    assert p_value is not None
    assert significant is True


def test_bootstrap_significance_empty():
    assert bootstrap_ic_significance([]) == (None, None, None, None, False)


def test_aggregate_metric_includes_bootstrap_audit_fields():
    engine = FactorMetricsEngine()
    observations = _positive_correlation_observations()
    result = engine.aggregate_metric(
        factor_name="volume_surge",
        strategy_name="breakout_v1",
        strategy_version="1.0.0",
        universe_code="PI_PM_CORE",
        horizon=20,
        regime_label="BULL_LOW_VOL",
        dataset_split=DATASET_SPLIT_TRAIN,
        observations=observations,
        daily_ics=[0.05, 0.04, 0.06, 0.03],
        ranked_days_in_regime=4,
        total_ranked_days_in_split=10,
        holdout_start_date=date(2025, 1, 1),
        as_of_date_start=date(2024, 1, 1),
        as_of_date_end=date(2024, 12, 31),
    )
    assert result is not None
    assert result.ic_spearman is not None and result.ic_spearman > 0.9
    assert result.bootstrap_sample_count == BOOTSTRAP_SAMPLE_COUNT
    assert result.bootstrap_method == "daily_ic_resample_with_replacement"
    assert result.stability_score == 1.0
    assert result.coverage_label == "adequate_coverage"


def test_build_daily_metrics_groups_by_run_and_regime():
    engine = FactorMetricsEngine()
    run_id = uuid4()
    observations = [
        FactorObservation(
            ranking_run_id=run_id,
            stock_id=uuid4(),
            factor_name="volume_surge",
            normalized_factor_value=Decimal(str(i)),
            factor_percentile=float(i),
            forward_return=Decimal(str(i * 0.01)),
            regime_label="BULL_LOW_VOL",
            as_of_date=date(2024, 6, 3),
        )
        for i in range(MIN_FACTOR_SAMPLE_SIZE)
    ]
    rows = engine.build_daily_metrics(observations, horizon=20, holdout_start_date=date(2025, 1, 1))
    assert len(rows) == 1
    assert rows[0].dataset_split == DATASET_SPLIT_TRAIN
    assert rows[0].ic_spearman is not None
