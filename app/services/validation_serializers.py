from __future__ import annotations

from uuid import UUID

from app.db.repositories.stock_repository import StockRepository
from app.models.ranking_performance_snapshot import RankingPerformanceSnapshot
from app.models.ranking_validation_report import RankingValidationReport
from app.schemas.validation import (
    RegimeIcRead,
    ValidationReportRead,
    ValidationSnapshotRead,
    ValidationSummaryRead,
)


def report_to_read(report: RankingValidationReport) -> ValidationReportRead:
    return ValidationReportRead(
        ranking_run_id=str(report.ranking_run_id),
        status=report.status,
        validation_hash=report.validation_hash,
        regime_label=report.regime_label,
        trend_regime=report.trend_regime,
        vol_regime=report.vol_regime,
        horizon_metrics=report.horizon_metrics,
        sample_summary=report.sample_summary,
        computed_at=report.computed_at.isoformat() if report.computed_at else None,
        error_message=report.error_message,
    )


def snapshot_to_read(
    snapshot: RankingPerformanceSnapshot,
    symbol: str | None = None,
) -> ValidationSnapshotRead:
    return ValidationSnapshotRead(
        id=str(snapshot.id),
        stock_id=str(snapshot.stock_id),
        symbol=symbol,
        return_5d=float(snapshot.return_5d) if snapshot.return_5d is not None else None,
        return_10d=float(snapshot.return_10d) if snapshot.return_10d is not None else None,
        return_20d=float(snapshot.return_20d) if snapshot.return_20d is not None else None,
        return_60d=float(snapshot.return_60d) if snapshot.return_60d is not None else None,
        captured_at=snapshot.captured_at.isoformat(),
    )


def symbol_map(stock_repo: StockRepository, stock_ids: list[UUID]) -> dict[UUID, str]:
    mapping: dict[UUID, str] = {}
    for stock_id in stock_ids:
        stock = stock_repo.get_by_id(stock_id)
        if stock:
            mapping[stock_id] = stock.symbol
    return mapping


def summary_to_read(data: dict) -> ValidationSummaryRead:
    horizon = data["horizon"]
    regime_raw = data.get("regime_ic") or {}
    return ValidationSummaryRead(
        reports_count=data["reports_count"],
        horizon=horizon,
        validated_runs=data.get("validated_runs", 0),
        failed_runs=data.get("failed_runs", 0),
        insufficient_data_runs=data.get("insufficient_data_runs", 0),
        average_ic_20d=data.get(f"average_ic_{horizon}d"),
        median_ic_20d=data.get(f"median_ic_{horizon}d"),
        top_decile_return_20d=data.get(f"top_decile_return_{horizon}d"),
        bottom_decile_return_20d=data.get(f"bottom_decile_return_{horizon}d"),
        spread_20d=data.get(f"spread_{horizon}d"),
        hit_rate_20d=data.get(f"hit_rate_{horizon}d"),
        directional_hit_rate_20d=data.get(f"directional_hit_rate_{horizon}d"),
        bull_market_ic=data.get("bull_market_ic"),
        bear_market_ic=data.get("bear_market_ic"),
        high_vol_ic=data.get("high_vol_ic"),
        low_vol_ic=data.get("low_vol_ic"),
        regime_ic=RegimeIcRead(**regime_raw) if regime_raw else None,
        best_regime=data.get("best_regime"),
        worst_regime=data.get("worst_regime"),
    )
