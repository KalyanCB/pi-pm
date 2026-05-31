from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ranking_performance_snapshot import RankingPerformanceSnapshot
from app.models.ranking_result import RankingResult
from app.models.stock import Stock
from app.validation.constants import VALIDATION_HORIZONS
from app.validation.models import FullHorizonMetrics
from app.validation.statistics import _ScoredReturn, compute_full_horizon_metrics

_RETURN_COLUMNS = {
    5: RankingPerformanceSnapshot.return_5d,
    10: RankingPerformanceSnapshot.return_10d,
    20: RankingPerformanceSnapshot.return_20d,
    60: RankingPerformanceSnapshot.return_60d,
}


def load_pooled_scored_returns(
    db: Session,
    ranking_run_ids: list[UUID],
    horizon: int,
) -> list[_ScoredReturn]:
    if not ranking_run_ids:
        return []

    return_column = _RETURN_COLUMNS[horizon]
    rows = db.execute(
        select(
            Stock.symbol,
            RankingResult.score,
            RankingResult.rank,
            return_column,
        )
        .join(
            RankingPerformanceSnapshot,
            (RankingPerformanceSnapshot.ranking_run_id == RankingResult.ranking_run_id)
            & (RankingPerformanceSnapshot.stock_id == RankingResult.stock_id),
        )
        .join(Stock, Stock.id == RankingResult.stock_id)
        .where(RankingResult.ranking_run_id.in_(ranking_run_ids))
        .where(return_column.is_not(None))
    ).all()

    return [
        _ScoredReturn(
            symbol=row.symbol,
            score=Decimal(str(row.score)),
            rank=row.rank,
            forward_return=Decimal(str(row[-1])),
        )
        for row in rows
    ]


def compute_campaign_horizon_metrics(
    db: Session,
    ranking_run_ids: list[UUID],
    horizon: int,
) -> FullHorizonMetrics:
    scored = load_pooled_scored_returns(db, ranking_run_ids, horizon)
    return compute_full_horizon_metrics(
        horizon,
        scored,
        ranked_days=len(ranking_run_ids),
    )


def compute_campaign_metrics(
    db: Session,
    ranking_run_ids: list[UUID],
) -> dict[int, FullHorizonMetrics]:
    return {
        horizon: compute_campaign_horizon_metrics(db, ranking_run_ids, horizon)
        for horizon in VALIDATION_HORIZONS
    }


def pick_best_worst_horizons(
    metrics_by_horizon: dict[int, FullHorizonMetrics],
) -> tuple[int | None, int | None]:
    candidates = [
        (horizon, metric.spread)
        for horizon, metric in metrics_by_horizon.items()
        if metric.spread is not None
    ]
    if not candidates:
        return None, None
    best = max(candidates, key=lambda item: item[1])
    worst = min(candidates, key=lambda item: item[1])
    return best[0], worst[0]
