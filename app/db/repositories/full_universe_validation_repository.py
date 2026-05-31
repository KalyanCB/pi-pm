from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.full_universe_validation import (
    FullUniverseValidationCampaign,
    FullUniverseValidationDecile,
    FullUniverseValidationMetric,
    FullUniverseValidationRun,
)
from app.validation.constants import (
    FULL_UNIVERSE_CAMPAIGN_STATUS_COMPLETED,
    FULL_UNIVERSE_CAMPAIGN_STATUS_FAILED,
    FULL_UNIVERSE_CAMPAIGN_STATUS_PENDING,
    FULL_UNIVERSE_CAMPAIGN_STATUS_RUNNING,
    FULL_UNIVERSE_RUN_STATUS_COMPLETED,
    FULL_UNIVERSE_RUN_STATUS_FAILED,
)
from app.validation.models import FullHorizonMetrics


class FullUniverseValidationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_campaign(
        self,
        *,
        universe_code: str,
        strategy_name: str,
        strategy_version: str,
        start_date: date,
        end_date: date,
    ) -> FullUniverseValidationCampaign:
        campaign = FullUniverseValidationCampaign(
            universe_code=universe_code,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            start_date=start_date,
            end_date=end_date,
            status=FULL_UNIVERSE_CAMPAIGN_STATUS_PENDING,
        )
        self.db.add(campaign)
        self.db.flush()
        return campaign

    def mark_running(self, campaign: FullUniverseValidationCampaign) -> FullUniverseValidationCampaign:
        campaign.status = FULL_UNIVERSE_CAMPAIGN_STATUS_RUNNING
        campaign.started_at = datetime.now(UTC)
        self.db.flush()
        return campaign

    def update_generation_stats(
        self,
        campaign: FullUniverseValidationCampaign,
        *,
        runs_created: int,
        runs_reused: int,
    ) -> FullUniverseValidationCampaign:
        campaign.ranking_runs_created = runs_created
        campaign.ranking_runs_reused = runs_reused
        self.db.flush()
        return campaign

    def complete_campaign(
        self,
        campaign: FullUniverseValidationCampaign,
        *,
        validation_days_completed: int,
        validation_days_failed: int,
    ) -> FullUniverseValidationCampaign:
        campaign.status = FULL_UNIVERSE_CAMPAIGN_STATUS_COMPLETED
        campaign.validation_days_completed = validation_days_completed
        campaign.validation_days_failed = validation_days_failed
        campaign.completed_at = datetime.now(UTC)
        self.db.flush()
        return campaign

    def fail_campaign(
        self,
        campaign: FullUniverseValidationCampaign,
        error_message: str,
    ) -> FullUniverseValidationCampaign:
        campaign.status = FULL_UNIVERSE_CAMPAIGN_STATUS_FAILED
        campaign.error_message = error_message
        campaign.completed_at = datetime.now(UTC)
        self.db.flush()
        return campaign

    def create_validation_run(
        self,
        campaign_id: UUID,
        ranking_run_id: UUID,
        validation_date: date,
    ) -> FullUniverseValidationRun:
        row = FullUniverseValidationRun(
            campaign_id=campaign_id,
            ranking_run_id=ranking_run_id,
            validation_date=validation_date,
            status=FULL_UNIVERSE_RUN_STATUS_COMPLETED,
            created_at=datetime.now(UTC),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def fail_validation_run(
        self,
        row: FullUniverseValidationRun,
        error_message: str,
    ) -> FullUniverseValidationRun:
        row.status = FULL_UNIVERSE_RUN_STATUS_FAILED
        row.error_message = error_message
        self.db.flush()
        return row

    def save_metrics(
        self,
        campaign_id: UUID,
        metrics_by_horizon: dict[int, FullHorizonMetrics],
    ) -> list[FullUniverseValidationMetric]:
        saved: list[FullUniverseValidationMetric] = []
        for horizon, metrics in metrics_by_horizon.items():
            row = FullUniverseValidationMetric(
                campaign_id=campaign_id,
                horizon=horizon,
                ic_pearson=_to_float(metrics.ic_pearson),
                rank_ic_spearman=_to_float(metrics.rank_ic_spearman),
                hit_rate=_to_float(metrics.hit_rate),
                directional_hit_rate=_to_float(metrics.directional_hit_rate),
                top_decile_return=_to_float(metrics.top_decile_return),
                bottom_decile_return=_to_float(metrics.bottom_decile_return),
                spread=_to_float(metrics.spread),
                top_20_return=_to_float(metrics.top_20_return),
                top_50_return=_to_float(metrics.top_50_return),
                sample_size=metrics.sample_size,
                ranked_days=metrics.ranked_days,
                is_monotonic=metrics.is_monotonic,
            )
            self.db.add(row)
            saved.append(row)
        self.db.flush()
        return saved

    def save_deciles(
        self,
        campaign_id: UUID,
        metrics_by_horizon: dict[int, FullHorizonMetrics],
    ) -> list[FullUniverseValidationDecile]:
        saved: list[FullUniverseValidationDecile] = []
        for horizon, metrics in metrics_by_horizon.items():
            for bucket in metrics.deciles:
                row = FullUniverseValidationDecile(
                    campaign_id=campaign_id,
                    horizon=horizon,
                    decile=bucket.decile,
                    count=bucket.count,
                    avg_return=_to_float(bucket.mean_return),
                    median_return=_to_float(bucket.median_return),
                    win_rate=_to_float(bucket.win_rate),
                )
                self.db.add(row)
                saved.append(row)
        self.db.flush()
        return saved

    def get_campaign_by_id(self, campaign_id: UUID) -> FullUniverseValidationCampaign | None:
        return self.db.scalar(
            select(FullUniverseValidationCampaign).where(
                FullUniverseValidationCampaign.id == campaign_id
            )
        )

    def get_latest_completed_campaign(
        self,
        *,
        universe_code: str | None = None,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
    ) -> FullUniverseValidationCampaign | None:
        stmt = (
            select(FullUniverseValidationCampaign)
            .where(FullUniverseValidationCampaign.status == FULL_UNIVERSE_CAMPAIGN_STATUS_COMPLETED)
            .order_by(FullUniverseValidationCampaign.completed_at.desc())
        )
        if universe_code:
            stmt = stmt.where(FullUniverseValidationCampaign.universe_code == universe_code)
        if strategy_name:
            stmt = stmt.where(FullUniverseValidationCampaign.strategy_name == strategy_name)
        if strategy_version:
            stmt = stmt.where(FullUniverseValidationCampaign.strategy_version == strategy_version)
        return self.db.scalar(stmt.limit(1))

    def list_metrics(self, campaign_id: UUID) -> list[FullUniverseValidationMetric]:
        return list(
            self.db.scalars(
                select(FullUniverseValidationMetric)
                .where(FullUniverseValidationMetric.campaign_id == campaign_id)
                .order_by(FullUniverseValidationMetric.horizon)
            ).all()
        )

    def list_deciles(
        self,
        campaign_id: UUID,
        horizon: int,
    ) -> list[FullUniverseValidationDecile]:
        return list(
            self.db.scalars(
                select(FullUniverseValidationDecile)
                .where(
                    FullUniverseValidationDecile.campaign_id == campaign_id,
                    FullUniverseValidationDecile.horizon == horizon,
                )
                .order_by(FullUniverseValidationDecile.decile)
            ).all()
        )

    def list_completed_run_ids(self, campaign_id: UUID) -> list[UUID]:
        rows = self.db.scalars(
            select(FullUniverseValidationRun.ranking_run_id).where(
                FullUniverseValidationRun.campaign_id == campaign_id,
                FullUniverseValidationRun.status == FULL_UNIVERSE_RUN_STATUS_COMPLETED,
            )
        ).all()
        return list(rows)


def _to_float(value) -> float | None:
    if value is None:
        return None
    return float(value)
