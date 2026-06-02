from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.platform_traceability import ValidationDecileMetric, ValidationHorizonMetric
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport


class ValidationMetricsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def replace_for_report(
        self,
        report: RankingValidationReport,
        ranking_run: RankingRun,
        horizon_metrics: dict,
    ) -> None:
        self.db.execute(
            delete(ValidationHorizonMetric).where(
                ValidationHorizonMetric.validation_report_id == report.id
            )
        )
        self.db.execute(
            delete(ValidationDecileMetric).where(
                ValidationDecileMetric.validation_report_id == report.id
            )
        )
        now = datetime.now(UTC)
        for horizon_key, payload in horizon_metrics.items():
            horizon = int(horizon_key)
            deciles = payload.get("deciles") or []
            hit_rates = payload.get("hit_rates") or {}
            top_decile = deciles[0]["mean_return"] if deciles else None
            bottom_decile = deciles[-1]["mean_return"] if deciles else None
            spread = payload.get("top_minus_bottom_spread")
            self.db.add(
                ValidationHorizonMetric(
                    validation_report_id=report.id,
                    ranking_run_id=ranking_run.id,
                    strategy_name=ranking_run.strategy_name,
                    strategy_version=ranking_run.strategy_version,
                    regime_label=report.regime_label,
                    horizon=horizon,
                    ic_pearson=_to_float(payload.get("ic_pearson")),
                    rank_ic_spearman=_to_float(payload.get("ic_spearman")),
                    hit_rate=_to_float(hit_rates.get("top_vs_median_hit_rate")),
                    directional_hit_rate=_to_float(hit_rates.get("rank_directional_hit_rate")),
                    spread=_to_float(spread),
                    top_decile_return=_to_float(top_decile),
                    bottom_decile_return=_to_float(bottom_decile),
                    sample_size=int(payload.get("sample_size") or 0),
                    computed_at=now,
                )
            )
            for bucket in deciles:
                self.db.add(
                    ValidationDecileMetric(
                        validation_report_id=report.id,
                        horizon=horizon,
                        decile=int(bucket["decile"]),
                        count=int(bucket.get("count") or 0),
                        avg_return=_to_float(bucket.get("mean_return")),
                        median_return=_to_float(bucket.get("median_return")),
                        win_rate=_to_float(bucket.get("win_rate")),
                    )
                )
        self.db.flush()

    def count_for_strategy(
        self,
        strategy_name: str,
        strategy_version: str,
        *,
        horizon: int | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(ValidationHorizonMetric)
            .where(
                ValidationHorizonMetric.strategy_name == strategy_name,
                ValidationHorizonMetric.strategy_version == strategy_version,
            )
        )
        if horizon is not None:
            stmt = stmt.where(ValidationHorizonMetric.horizon == horizon)
        count = self.db.scalar(stmt)
        return int(count or 0)

    def has_for_report(self, report_id: UUID) -> bool:
        count = self.db.scalar(
            select(func.count())
            .select_from(ValidationHorizonMetric)
            .where(ValidationHorizonMetric.validation_report_id == report_id)
        )
        return bool(count and count > 0)

    def spreads_by_report_for_horizon(
        self,
        report_ids: list[UUID],
        horizon: int,
    ) -> dict[UUID, float]:
        if not report_ids:
            return {}
        rows = self.db.execute(
            select(
                ValidationHorizonMetric.validation_report_id,
                ValidationHorizonMetric.spread,
            ).where(
                ValidationHorizonMetric.validation_report_id.in_(report_ids),
                ValidationHorizonMetric.horizon == horizon,
                ValidationHorizonMetric.spread.is_not(None),
            )
        ).all()
        return {row.validation_report_id: float(row.spread) for row in rows}

    def sample_sizes_by_report_for_horizon(
        self,
        report_ids: list[UUID],
        horizon: int,
    ) -> dict[UUID, int]:
        if not report_ids:
            return {}
        rows = self.db.execute(
            select(
                ValidationHorizonMetric.validation_report_id,
                ValidationHorizonMetric.sample_size,
            ).where(
                ValidationHorizonMetric.validation_report_id.in_(report_ids),
                ValidationHorizonMetric.horizon == horizon,
            )
        ).all()
        return {row.validation_report_id: int(row.sample_size or 0) for row in rows}


def _to_float(value) -> float | None:
    if value is None:
        return None
    return float(value)
