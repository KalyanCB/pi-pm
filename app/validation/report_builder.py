from __future__ import annotations

from uuid import UUID

from app.validation.constants import (
    VALIDATION_HORIZONS,
    VALIDATION_STATUS_COMPLETED,
    VALIDATION_STATUS_INSUFFICIENT_DATA,
)
from app.validation.hashing import build_validation_hash
from app.validation.models import (
    RegimeClassification,
    StockForwardReturns,
    ValidationReportData,
)
from app.validation.statistics import _ScoredReturn, compute_horizon_metrics


def build_validation_report(
    ranking_run_id: UUID,
    inputs_hash: str | None,
    as_of_date,
    regime: RegimeClassification | None,
    stock_returns: list[StockForwardReturns],
) -> ValidationReportData:
    horizon_metrics: dict[int, object] = {}
    any_valid = False

    for horizon in VALIDATION_HORIZONS:
        scored = [
            _ScoredReturn(
                symbol=item.symbol,
                score=item.score,
                rank=item.rank,
                forward_return=item.returns[horizon],
            )
            for item in stock_returns
            if item.returns.get(horizon) is not None
        ]
        metrics = compute_horizon_metrics(horizon, scored)
        horizon_metrics[horizon] = metrics
        if metrics.status == "ok":
            any_valid = True

    status = VALIDATION_STATUS_COMPLETED if any_valid else VALIDATION_STATUS_INSUFFICIENT_DATA
    validation_hash = None
    if status == VALIDATION_STATUS_COMPLETED:
        validation_hash = build_validation_hash(
            ranking_run_id,
            inputs_hash,
            as_of_date,
            regime,
            tuple(stock_returns),
            horizon_metrics,
        )

    sample_summary = {
        "ranked_stock_count": len(stock_returns),
        "horizon_valid_counts": {
            str(h): horizon_metrics[h].sample_size for h in VALIDATION_HORIZONS
        },
    }

    return ValidationReportData(
        ranking_run_id=ranking_run_id,
        as_of_date=as_of_date,
        status=status,
        validation_hash=validation_hash,
        regime=regime,
        horizon_metrics=horizon_metrics,
        sample_summary=sample_summary,
    )


def serialize_horizon_metrics(metrics: dict[int, object]) -> dict[str, dict]:
    serialized: dict[str, dict] = {}
    for horizon, data in metrics.items():
        serialized[str(horizon)] = {
            "status": data.status,
            "ic_spearman": str(data.ic_spearman) if data.ic_spearman is not None else None,
            "top_minus_bottom_spread": (
                str(data.top_minus_bottom_spread)
                if data.top_minus_bottom_spread is not None
                else None
            ),
            "sample_size": data.sample_size,
            "deciles": [
                {
                    "decile": bucket.decile,
                    "count": bucket.count,
                    "mean_return": str(bucket.mean_return)
                    if bucket.mean_return is not None
                    else None,
                    "median_return": (
                        str(bucket.median_return) if bucket.median_return is not None else None
                    ),
                }
                for bucket in data.deciles
            ],
            "hit_rates": {
                "top_vs_median_hit_rate": (
                    str(data.hit_rates.top_vs_median_hit_rate)
                    if data.hit_rates.top_vs_median_hit_rate is not None
                    else None
                ),
                "top_vs_bottom_hit_rate": (
                    str(data.hit_rates.top_vs_bottom_hit_rate)
                    if data.hit_rates.top_vs_bottom_hit_rate is not None
                    else None
                ),
                "rank_directional_hit_rate": (
                    str(data.hit_rates.rank_directional_hit_rate)
                    if data.hit_rates.rank_directional_hit_rate is not None
                    else None
                ),
            },
        }
    return serialized
