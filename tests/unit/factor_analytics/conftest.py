from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.constants import RankingRunStatus
from app.models.platform_traceability import RankingFactorContribution
from app.models.ranking_performance_snapshot import RankingPerformanceSnapshot
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport
from app.models.stock import Stock
from app.validation.constants import VALIDATION_STATUS_COMPLETED


@pytest.fixture
def factor_analytics_service(db_session):
    from app.db.repositories.factor_performance_metric_repository import (
        FactorPerformanceMetricRepository,
    )
    from app.db.repositories.factor_performance_run_repository import (
        FactorPerformanceRunRepository,
    )
    from app.db.repositories.ranking_run_repository import RankingRunRepository
    from app.db.repositories.ranking_validation_repository import RankingValidationRepository
    from app.services.factor_predictive_power_service import FactorPredictivePowerService

    return FactorPredictivePowerService(
        db_session,
        FactorPerformanceMetricRepository(db_session),
        FactorPerformanceRunRepository(db_session),
        RankingValidationRepository(db_session),
        RankingRunRepository(db_session),
    )


def seed_factor_run(
    db_session,
    *,
    as_of: date,
    regime_label: str = "BULL_LOW_VOL",
    universe_code: str = "PI_PM_CORE",
    factor_name: str = "volume_surge",
    stock_count: int = 35,
    metadata: dict | None = None,
) -> RankingRun:
    run = RankingRun(
        strategy_name="breakout_v1",
        strategy_version="1.0.0",
        universe_code=universe_code,
        as_of_date=as_of,
        benchmark_symbol="^NSEI",
        filter_config_hash="test-filter",
        normalization_method="percentile",
        status=RankingRunStatus.COMPLETED.value,
        regime_label=regime_label,
        inputs_hash=f"hash-{as_of.isoformat()}-{uuid4()}",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        metadata_=metadata,
    )
    db_session.add(run)
    db_session.flush()

    db_session.add(
        RankingValidationReport(
            ranking_run_id=run.id,
            status=VALIDATION_STATUS_COMPLETED,
            regime_label=regime_label,
            computed_at=datetime.now(UTC),
        )
    )

    for index in range(stock_count):
        stock = Stock(
            symbol=f"FA{as_of.strftime('%Y%m%d')}{index:03d}.NS",
            name=f"FA Stock {index}",
            exchange="NSE",
            is_active=True,
            data_status="ACTIVE",
        )
        db_session.add(stock)
        db_session.flush()

        factor_value = Decimal(str(0.1 + index * 0.02))
        forward_return = Decimal(str(-0.05 + index * 0.003))

        db_session.add(
            RankingFactorContribution(
                ranking_run_id=run.id,
                stock_id=stock.id,
                factor_name=factor_name,
                normalized_factor_value=float(factor_value),
                raw_factor_value=float(factor_value),
                weighted_factor_value=float(factor_value * Decimal("0.15")),
            )
        )
        db_session.add(
            RankingPerformanceSnapshot(
                ranking_run_id=run.id,
                stock_id=stock.id,
                return_20d=float(forward_return),
                captured_at=datetime.now(UTC),
            )
        )

    db_session.commit()
    return run
