from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_BREAKOUT_V1_VERSION,
    UNIVERSE_NIFTY_500,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.db.repositories.full_universe_validation_repository import (
    FullUniverseValidationRepository,
)
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.models.full_universe_validation import (
    FullUniverseValidationCampaign,
    FullUniverseValidationMetric,
)
from app.schemas.backtest import GenerateRankingsRequest
from app.services.backtest_service import BacktestService
from app.services.signal_validation_service import SignalValidationService
from app.validation.campaign_aggregator import (
    compute_campaign_metrics,
    pick_best_worst_horizons,
)
from app.validation.constants import VALIDATION_HORIZONS, VALIDATION_STATUS_COMPLETED


@dataclass(frozen=True)
class FullUniverseValidationRunResult:
    campaign_id: UUID
    status: str
    ranking_runs_created: int
    ranking_runs_reused: int
    validation_days_completed: int
    validation_days_failed: int
    ranked_days_total: int


class FullUniverseValidationService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        campaign_repo: FullUniverseValidationRepository,
        ranking_run_repo: RankingRunRepository,
        backtest_service: BacktestService,
        signal_validation_service: SignalValidationService,
    ) -> None:
        self.db = db
        self.settings = settings
        self.campaign_repo = campaign_repo
        self.ranking_run_repo = ranking_run_repo
        self.backtest_service = backtest_service
        self.signal_validation_service = signal_validation_service

    def run_campaign(
        self,
        start_date: date,
        end_date: date,
        *,
        universe_code: str = UNIVERSE_NIFTY_500,
        strategy_name: str = RANKING_STRATEGY_BREAKOUT_V1,
        strategy_version: str = RANKING_STRATEGY_BREAKOUT_V1_VERSION,
        force_recompute: bool = False,
    ) -> FullUniverseValidationRunResult:
        if end_date < start_date:
            raise ValidationError("end_date must be on or after start_date")

        campaign = self.campaign_repo.create_campaign(
            universe_code=universe_code,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            start_date=start_date,
            end_date=end_date,
        )
        self.db.commit()

        try:
            self.campaign_repo.mark_running(campaign)
            self.db.commit()

            generation = self.backtest_service.generate_rankings(
                GenerateRankingsRequest(
                    universe_code=universe_code,
                    start_date=start_date,
                    end_date=end_date,
                    strategy_name=strategy_name,
                    strategy_version=strategy_version,
                )
            )
            self.campaign_repo.update_generation_stats(
                campaign,
                runs_created=generation.runs_created,
                runs_reused=generation.runs_reused,
            )
            self.db.commit()

            runs = self.ranking_run_repo.list_completed_in_range(
                start_date,
                end_date,
                universe_code=universe_code,
                strategy_name=strategy_name,
                strategy_version=strategy_version,
            )

            validated_run_ids: list[UUID] = []
            validation_days_completed = 0
            validation_days_failed = 0

            for run in runs:
                try:
                    report = self.signal_validation_service.validate_run(
                        run.id,
                        force_recompute=force_recompute,
                    )
                    if report.status == VALIDATION_STATUS_COMPLETED:
                        self.campaign_repo.create_validation_run(
                            campaign.id,
                            run.id,
                            run.as_of_date,
                        )
                        validated_run_ids.append(run.id)
                        validation_days_completed += 1
                    else:
                        failed_row = self.campaign_repo.create_validation_run(
                            campaign.id,
                            run.id,
                            run.as_of_date,
                        )
                        self.campaign_repo.fail_validation_run(
                            failed_row,
                            f"Validation status: {report.status}",
                        )
                        validation_days_failed += 1
                except ValidationError as exc:
                    failed_row = self.campaign_repo.create_validation_run(
                        campaign.id,
                        run.id,
                        run.as_of_date,
                    )
                    self.campaign_repo.fail_validation_run(failed_row, str(exc))
                    validation_days_failed += 1

            metrics_by_horizon = compute_campaign_metrics(self.db, validated_run_ids)
            self.campaign_repo.save_metrics(campaign.id, metrics_by_horizon)
            self.campaign_repo.save_deciles(campaign.id, metrics_by_horizon)
            self.campaign_repo.complete_campaign(
                campaign,
                validation_days_completed=validation_days_completed,
                validation_days_failed=validation_days_failed,
            )
            self.db.commit()

            return FullUniverseValidationRunResult(
                campaign_id=campaign.id,
                status=campaign.status,
                ranking_runs_created=generation.runs_created,
                ranking_runs_reused=generation.runs_reused,
                validation_days_completed=validation_days_completed,
                validation_days_failed=validation_days_failed,
                ranked_days_total=len(runs),
            )
        except Exception as exc:
            self.db.rollback()
            campaign = self.campaign_repo.get_campaign_by_id(campaign.id)
            if campaign is not None:
                self.campaign_repo.fail_campaign(campaign, str(exc))
                self.db.commit()
            raise ValidationError(str(exc)) from exc

    def get_summary(
        self,
        *,
        campaign_id: UUID | None = None,
        horizon: int = 20,
        universe_code: str | None = None,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
    ) -> dict:
        campaign = self._resolve_campaign(
            campaign_id=campaign_id,
            universe_code=universe_code,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
        )
        metrics = self.campaign_repo.list_metrics(campaign.id)
        if not metrics:
            raise NotFoundError(f"No metrics found for campaign: {campaign.id}")

        metrics_by_horizon = {row.horizon: row for row in metrics}
        if horizon not in metrics_by_horizon:
            raise NotFoundError(f"No metrics for horizon {horizon} in campaign {campaign.id}")

        selected = metrics_by_horizon[horizon]
        best_horizon, worst_horizon = pick_best_worst_horizons(
            {row.horizon: _metric_row_to_full(row) for row in metrics}
        )

        return {
            "campaign_id": str(campaign.id),
            "universe_code": campaign.universe_code,
            "strategy_name": campaign.strategy_name,
            "strategy_version": campaign.strategy_version,
            "start_date": campaign.start_date.isoformat(),
            "end_date": campaign.end_date.isoformat(),
            "status": campaign.status,
            "horizon": horizon,
            "ic": _fmt(selected.ic_pearson),
            "rank_ic": _fmt(selected.rank_ic_spearman),
            "hit_rate": _fmt(selected.hit_rate),
            "directional_hit_rate": _fmt(selected.directional_hit_rate),
            "top_decile_return": _fmt(selected.top_decile_return),
            "bottom_decile_return": _fmt(selected.bottom_decile_return),
            "spread": _fmt(selected.spread),
            "top_20_return": _fmt(selected.top_20_return),
            "top_50_return": _fmt(selected.top_50_return),
            "sample_size": selected.sample_size,
            "ranked_days": selected.ranked_days,
            "is_monotonic": selected.is_monotonic,
            "best_horizon": best_horizon,
            "worst_horizon": worst_horizon,
            "horizons": {
                str(row.horizon): {
                    "ic": _fmt(row.ic_pearson),
                    "rank_ic": _fmt(row.rank_ic_spearman),
                    "hit_rate": _fmt(row.hit_rate),
                    "spread": _fmt(row.spread),
                    "top_decile_return": _fmt(row.top_decile_return),
                    "bottom_decile_return": _fmt(row.bottom_decile_return),
                    "is_monotonic": row.is_monotonic,
                }
                for row in metrics
            },
        }

    def get_deciles(
        self,
        horizon: int,
        *,
        campaign_id: UUID | None = None,
        universe_code: str | None = None,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
    ) -> dict:
        if horizon not in VALIDATION_HORIZONS:
            raise ValidationError(f"Unsupported horizon: {horizon}")

        campaign = self._resolve_campaign(
            campaign_id=campaign_id,
            universe_code=universe_code,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
        )
        deciles = self.campaign_repo.list_deciles(campaign.id, horizon)
        if not deciles:
            raise NotFoundError(
                f"No decile statistics for horizon {horizon} in campaign {campaign.id}"
            )

        return {
            "campaign_id": str(campaign.id),
            "horizon": horizon,
            "deciles": [
                {
                    "decile": row.decile,
                    "count": row.count,
                    "avg_return": _fmt(row.avg_return),
                    "median_return": _fmt(row.median_return),
                    "win_rate": _fmt(row.win_rate),
                }
                for row in deciles
            ],
        }

    def _resolve_campaign(
        self,
        *,
        campaign_id: UUID | None,
        universe_code: str | None,
        strategy_name: str | None,
        strategy_version: str | None,
    ) -> FullUniverseValidationCampaign:
        if campaign_id is not None:
            campaign = self.campaign_repo.get_campaign_by_id(campaign_id)
            if campaign is None:
                raise NotFoundError(f"Validation campaign not found: {campaign_id}")
            return campaign

        campaign = self.campaign_repo.get_latest_completed_campaign(
            universe_code=universe_code or UNIVERSE_NIFTY_500,
            strategy_name=strategy_name or RANKING_STRATEGY_BREAKOUT_V1,
            strategy_version=strategy_version or RANKING_STRATEGY_BREAKOUT_V1_VERSION,
        )
        if campaign is None:
            raise NotFoundError("No completed full-universe validation campaign found")
        return campaign


def _fmt(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{value:.8f}"


def _metric_row_to_full(row: FullUniverseValidationMetric):
    from app.validation.models import FullHorizonMetrics

    def _dec(value: float | None):
        return None if value is None else Decimal(str(value))

    return FullHorizonMetrics(
        horizon=row.horizon,
        status="ok",
        ic_pearson=_dec(row.ic_pearson),
        rank_ic_spearman=_dec(row.rank_ic_spearman),
        hit_rate=_dec(row.hit_rate),
        directional_hit_rate=_dec(row.directional_hit_rate),
        top_decile_return=_dec(row.top_decile_return),
        bottom_decile_return=_dec(row.bottom_decile_return),
        spread=_dec(row.spread),
        top_20_return=_dec(row.top_20_return),
        top_50_return=_dec(row.top_50_return),
        deciles=(),
        is_monotonic=row.is_monotonic,
        sample_size=row.sample_size,
        ranked_days=row.ranked_days,
    )
