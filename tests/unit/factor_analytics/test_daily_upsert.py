from datetime import date
from uuid import uuid4

from app.db.repositories.factor_performance_metric_repository import (
    FactorPerformanceMetricRepository,
)
from app.factor_analytics.models import DailyFactorIC


def test_upsert_daily_is_idempotent_within_session(db_session):
    repo = FactorPerformanceMetricRepository(db_session)
    run_id = uuid4()
    row = DailyFactorIC(
        factor_name="volume_surge",
        ranking_run_id=run_id,
        as_of_date=date(2024, 6, 3),
        regime_label="BULL_LOW_VOL",
        dataset_split="TRAIN",
        horizon=20,
        ic_spearman=0.05,
        sample_size=40,
    )
    repo.upsert_daily(
        row, strategy_name="breakout_v1", strategy_version="1.0.0", universe_code="PI_PM_CORE"
    )
    row2 = DailyFactorIC(
        factor_name="volume_surge",
        ranking_run_id=run_id,
        as_of_date=date(2024, 6, 3),
        regime_label="BULL_LOW_VOL",
        dataset_split="TRAIN",
        horizon=20,
        ic_spearman=0.06,
        sample_size=41,
    )
    repo.upsert_daily(
        row2, strategy_name="breakout_v1", strategy_version="1.0.0", universe_code="PI_PM_CORE"
    )
    db_session.commit()

    from sqlalchemy import func, select

    from app.models.factor_analytics import FactorDailyMetric

    count = db_session.scalar(
        select(func.count())
        .select_from(FactorDailyMetric)
        .where(
            FactorDailyMetric.ranking_run_id == run_id,
            FactorDailyMetric.factor_name == "volume_surge",
        )
    )
    assert count == 1
