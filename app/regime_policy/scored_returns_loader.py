from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ranking_performance_snapshot import RankingPerformanceSnapshot
from app.models.ranking_result import RankingResult
from app.models.stock import Stock
from app.validation.campaign_aggregator import _RETURN_COLUMNS
from app.validation.statistics import _ScoredReturn


def batch_load_scored_returns_by_run(
    db: Session,
    ranking_run_ids: list[UUID],
    horizon: int,
) -> dict[UUID, list[_ScoredReturn]]:
    """Load all scored returns for many runs in one query (avoids N+1)."""
    if not ranking_run_ids:
        return {}

    return_column = _RETURN_COLUMNS[horizon]
    rows = db.execute(
        select(
            RankingResult.ranking_run_id,
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

    by_run: dict[UUID, list[_ScoredReturn]] = defaultdict(list)
    for row in rows:
        by_run[row.ranking_run_id].append(
            _ScoredReturn(
                symbol=row.symbol,
                score=Decimal(str(row.score)),
                rank=row.rank,
                forward_return=Decimal(str(row[-1])),
            )
        )
    return dict(by_run)


def count_scored_returns_by_run(
    scored_by_run: dict[UUID, list[_ScoredReturn]],
) -> tuple[int, int]:
    """Return (runs_with_data, total_rows) for replay diagnostics."""
    runs_with_data = sum(1 for rows in scored_by_run.values() if rows)
    total_rows = sum(len(rows) for rows in scored_by_run.values())
    return runs_with_data, total_rows
