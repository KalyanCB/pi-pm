from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.factor_analytics.constants import FACTOR_ANALYTICS_HORIZONS

# Calendar lookback when the batch window has no completed validations (e.g. latest as-of only).
DEFAULT_FACTOR_IC_LOOKBACK_DAYS = 400
DEFAULT_REGIME_PERFORMANCE_HORIZON = 20


def list_completed_validation_dates(
    db: Session,
    *,
    universe_code: str,
    strategy_name: str,
    strategy_version: str,
    start_date: date,
    end_date: date,
) -> list[date]:
    repo = RankingValidationRepository(db)
    reports = repo.list_completed_with_runs(
        universe_code=universe_code,
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        start_date=start_date,
        end_date=end_date,
    )
    dates: list[date] = []
    for report in reports:
        run = report.ranking_run
        if run is not None:
            dates.append(run.as_of_date)
    return sorted(set(dates))


def resolve_quant_evidence_window(
    *,
    plan_from_date: date,
    target_trading_day: date,
    holdout_start_date: date,
    completed_validation_dates: list[date],
    lookback_days: int = DEFAULT_FACTOR_IC_LOOKBACK_DAYS,
) -> tuple[date, date] | None:
    """Pick a [start, end] window with at least one completed validation for factor/exit backfills."""
    if not completed_validation_dates:
        return None

    eligible = [d for d in completed_validation_dates if d <= target_trading_day]
    if not eligible:
        return None

    evidence_end = max(eligible)
    lookback_floor = evidence_end - timedelta(days=lookback_days)
    window_start = max(holdout_start_date, lookback_floor)
    # Recent plan_from_date may be after the last completed validation (insufficient_data tail).
    if plan_from_date <= evidence_end:
        window_start = max(window_start, plan_from_date)
    in_window = [d for d in eligible if window_start <= d <= evidence_end]
    if not in_window:
        return None

    return min(in_window), evidence_end


def max_forward_horizon_trading_days() -> int:
    return max(FACTOR_ANALYTICS_HORIZONS)
