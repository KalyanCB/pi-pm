from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import RankingRunStatus
from app.factor_analytics.window import split_dataset
from app.models.ranking_performance_snapshot import RankingPerformanceSnapshot
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport
from app.models.stock import Stock
from app.validation.constants import VALIDATION_STATUS_COMPLETED
from app.workspace_exit_research.models import SignalEntry


class SignalCohortLoader:
    def __init__(self, db: Session) -> None:
        self.db = db

    def load_entries(
        self,
        *,
        strategy_name: str,
        strategy_version: str,
        universe_code: str,
        start_date: date,
        end_date: date,
        holdout_start_date: date,
    ) -> list[SignalEntry]:
        rows = self.db.execute(
            select(
                RankingResult.ranking_run_id,
                RankingResult.stock_id,
                RankingResult.rank,
                RankingResult.score,
                RankingRun.as_of_date,
                RankingValidationReport.regime_label,
                Stock.symbol,
                Stock.sector,
                RankingPerformanceSnapshot.return_5d,
                RankingPerformanceSnapshot.return_10d,
                RankingPerformanceSnapshot.return_20d,
                RankingPerformanceSnapshot.return_60d,
            )
            .join(RankingRun, RankingRun.id == RankingResult.ranking_run_id)
            .join(
                RankingValidationReport,
                RankingValidationReport.ranking_run_id == RankingResult.ranking_run_id,
            )
            .join(Stock, Stock.id == RankingResult.stock_id)
            .join(
                RankingPerformanceSnapshot,
                (RankingPerformanceSnapshot.ranking_run_id == RankingResult.ranking_run_id)
                & (RankingPerformanceSnapshot.stock_id == RankingResult.stock_id),
            )
            .where(RankingRun.status == RankingRunStatus.COMPLETED.value)
            .where(RankingValidationReport.status == VALIDATION_STATUS_COMPLETED)
            .where(RankingRun.strategy_name == strategy_name)
            .where(RankingRun.strategy_version == strategy_version)
            .where(RankingRun.universe_code == universe_code)
            .where(RankingRun.as_of_date >= start_date)
            .where(RankingRun.as_of_date <= end_date)
            .where(RankingValidationReport.regime_label.is_not(None))
        ).all()

        run_counts: dict = {}
        for row in rows:
            run_counts[row.ranking_run_id] = run_counts.get(row.ranking_run_id, 0) + 1

        entries: list[SignalEntry] = []
        for row in rows:
            total = run_counts.get(row.ranking_run_id, 0)
            top_decile_cutoff = max(1, (total + 9) // 10)
            if row.rank > top_decile_cutoff:
                continue
            entries.append(
                SignalEntry(
                    ranking_run_id=row.ranking_run_id,
                    stock_id=row.stock_id,
                    symbol=row.symbol,
                    entry_date=row.as_of_date,
                    entry_rank=row.rank,
                    entry_score=Decimal(str(row.score)),
                    entry_close=Decimal("0"),  # filled from bars when simulating
                    regime_label=row.regime_label,
                    sector=row.sector,
                    dataset_split=split_dataset(row.as_of_date, holdout_start_date),
                    return_5d=_dec(row.return_5d),
                    return_10d=_dec(row.return_10d),
                    return_20d=_dec(row.return_20d),
                    return_60d=_dec(row.return_60d),
                )
            )
        return entries


def _dec(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
