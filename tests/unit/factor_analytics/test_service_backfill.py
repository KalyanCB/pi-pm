from datetime import date

from sqlalchemy import func, select

from app.factor_analytics.constants import DATASET_SPLIT_HOLDOUT, DATASET_SPLIT_TRAIN
from app.models.factor_analytics import FactorDailyMetric, FactorPerformanceMetric
from tests.unit.factor_analytics.conftest import seed_factor_run


def test_backfill_writes_aggregate_and_daily_metrics(factor_analytics_service, db_session):
    seed_factor_run(db_session, as_of=date(2024, 6, 3), regime_label="BULL_LOW_VOL")
    seed_factor_run(db_session, as_of=date(2024, 6, 10), regime_label="BEAR_LOW_VOL")

    run = factor_analytics_service.backfill(
        universe_code="PI_PM_CORE",
        start_date=date(2024, 6, 1),
        end_date=date(2024, 6, 30),
        holdout_start_date=date(2025, 1, 1),
        horizons=[20],
        dataset_splits=[DATASET_SPLIT_TRAIN, DATASET_SPLIT_HOLDOUT, "ALL"],
        write_daily_metrics=True,
    )
    assert run.status == "completed"
    assert run.metrics_written > 0

    metric_count = db_session.scalar(select(func.count()).select_from(FactorPerformanceMetric))
    daily_count = db_session.scalar(select(func.count()).select_from(FactorDailyMetric))
    assert metric_count > 0
    assert daily_count > 0

    all_regime = db_session.scalars(
        select(FactorPerformanceMetric).where(
            FactorPerformanceMetric.regime_label == "ALL",
            FactorPerformanceMetric.dataset_split == DATASET_SPLIT_TRAIN,
        )
    ).all()
    assert len(all_regime) >= 1


def test_backfill_is_idempotent(factor_analytics_service, db_session):
    seed_factor_run(db_session, as_of=date(2024, 7, 1))
    kwargs = dict(
        universe_code="PI_PM_CORE",
        start_date=date(2024, 7, 1),
        end_date=date(2024, 7, 31),
        holdout_start_date=date(2025, 1, 1),
        horizons=[20],
        dataset_splits=[DATASET_SPLIT_TRAIN],
    )
    factor_analytics_service.backfill(**kwargs)
    first_count = db_session.scalar(select(func.count()).select_from(FactorPerformanceMetric))

    factor_analytics_service.backfill(**kwargs)
    second_count = db_session.scalar(select(func.count()).select_from(FactorPerformanceMetric))
    assert first_count == second_count


def test_backfill_resolves_weights_from_metadata(factor_analytics_service, db_session):
    seed_factor_run(
        db_session,
        as_of=date(2024, 8, 1),
        metadata={"effective_weights": {"volume_surge": "0.25", "high_proximity": "0.10"}},
    )
    factor_analytics_service.backfill(
        universe_code="PI_PM_CORE",
        start_date=date(2024, 8, 1),
        end_date=date(2024, 8, 31),
        holdout_start_date=date(2025, 1, 1),
        horizons=[20],
        dataset_splits=[DATASET_SPLIT_TRAIN],
    )
    leaderboard = factor_analytics_service.get_leaderboard(
        regime_label="BULL_LOW_VOL",
        horizon=20,
        universe_code="PI_PM_CORE",
        dataset_split=DATASET_SPLIT_TRAIN,
        start_date=date(2024, 8, 1),
        end_date=date(2024, 8, 31),
    )
    entry = next(item for item in leaderboard["entries"] if item["factor_name"] == "volume_surge")
    assert entry["current_weight"] == 0.25
