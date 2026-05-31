from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from statistics import median
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import RankingRunStatus
from app.factor_analytics.models import FactorObservation
from app.models.platform_traceability import RankingFactorContribution
from app.models.ranking_performance_snapshot import RankingPerformanceSnapshot
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport
from app.validation.campaign_aggregator import _RETURN_COLUMNS
from app.validation.constants import VALIDATION_STATUS_COMPLETED

logger = logging.getLogger(__name__)


def compute_factor_percentile_ranks(
    values: list[tuple[UUID, Decimal]],
) -> dict[UUID, float]:
    """Cross-sectional percentile rank (0-100) for stocks within one run."""
    if not values:
        return {}
    sorted_items = sorted(values, key=lambda item: (item[1], str(item[0])))
    n = len(sorted_items)
    if n == 1:
        return {sorted_items[0][0]: 100.0}
    ranks: dict[UUID, float] = {}
    for index, (stock_id, _value) in enumerate(sorted_items):
        percentile = (index / (n - 1)) * 100.0
        ranks[stock_id] = percentile
    return ranks


class FactorObservationLoader:
    def __init__(self, db: Session) -> None:
        self.db = db

    def load_observations(
        self,
        *,
        strategy_name: str,
        strategy_version: str,
        universe_code: str,
        start_date: date,
        end_date: date,
        horizon: int,
    ) -> list[FactorObservation]:
        return_column = _RETURN_COLUMNS[horizon]
        rows = self.db.execute(
            select(
                RankingFactorContribution.ranking_run_id,
                RankingFactorContribution.stock_id,
                RankingFactorContribution.factor_name,
                RankingFactorContribution.normalized_factor_value,
                return_column,
                RankingValidationReport.regime_label,
                RankingRun.as_of_date,
            )
            .join(
                RankingRun,
                RankingRun.id == RankingFactorContribution.ranking_run_id,
            )
            .join(
                RankingValidationReport,
                RankingValidationReport.ranking_run_id == RankingFactorContribution.ranking_run_id,
            )
            .join(
                RankingPerformanceSnapshot,
                (RankingPerformanceSnapshot.ranking_run_id == RankingFactorContribution.ranking_run_id)
                & (RankingPerformanceSnapshot.stock_id == RankingFactorContribution.stock_id),
            )
            .where(RankingRun.status == RankingRunStatus.COMPLETED.value)
            .where(RankingValidationReport.status == VALIDATION_STATUS_COMPLETED)
            .where(RankingRun.strategy_name == strategy_name)
            .where(RankingRun.strategy_version == strategy_version)
            .where(RankingRun.universe_code == universe_code)
            .where(RankingRun.as_of_date >= start_date)
            .where(RankingRun.as_of_date <= end_date)
            .where(RankingFactorContribution.normalized_factor_value.is_not(None))
            .where(return_column.is_not(None))
            .where(RankingValidationReport.regime_label.is_not(None))
        ).all()

        by_run_factor: dict[tuple[UUID, str], list[tuple[UUID, Decimal]]] = defaultdict(list)
        raw_rows: list[tuple] = []
        for row in rows:
            if row.normalized_factor_value is None or row[4] is None or row.regime_label is None:
                continue
            key = (row.ranking_run_id, row.factor_name)
            by_run_factor[key].append((row.stock_id, Decimal(str(row.normalized_factor_value))))
            raw_rows.append(row)

        percentile_maps: dict[tuple[UUID, str], dict[UUID, float]] = {}
        for key, pairs in by_run_factor.items():
            percentile_maps[key] = compute_factor_percentile_ranks(pairs)

        observations: list[FactorObservation] = []
        for row in raw_rows:
            key = (row.ranking_run_id, row.factor_name)
            percentile = percentile_maps.get(key, {}).get(row.stock_id, 50.0)
            observations.append(
                FactorObservation(
                    ranking_run_id=row.ranking_run_id,
                    stock_id=row.stock_id,
                    factor_name=row.factor_name,
                    normalized_factor_value=Decimal(str(row.normalized_factor_value)),
                    factor_percentile=percentile,
                    forward_return=Decimal(str(row[4])),
                    regime_label=row.regime_label,
                    as_of_date=row.as_of_date,
                )
            )
        return observations

    def list_distinct_dates(
        self,
        observations: list[FactorObservation],
        *,
        dataset_split: str,
        holdout_start_date: date,
    ) -> set[date]:
        from app.factor_analytics.window import include_in_split

        return {
            obs.as_of_date
            for obs in observations
            if include_in_split(obs.as_of_date, dataset_split, holdout_start_date)
        }
