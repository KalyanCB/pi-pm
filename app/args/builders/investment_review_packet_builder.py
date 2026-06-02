from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.repositories.exit_research_metric_repository import ExitResearchMetricRepository
from app.db.repositories.factor_performance_metric_repository import FactorPerformanceMetricRepository
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_performance_repository import RankingPerformanceRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.models.platform_traceability import ValidationDecileMetric, ValidationHorizonMetric
from app.models.ranking_performance_snapshot import RankingPerformanceSnapshot
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.stock import Stock
from app.workspace_args.constants import PACKET_VERSION
from app.workspace_args.models import InvestmentReviewPacket
from app.workspace_args.packet_schema import compute_packet_hash


class InvestmentReviewPacketBuilder:
    def __init__(
        self,
        db: Session,
        validation_repo: RankingValidationRepository,
        *,
        factor_metric_repo: FactorPerformanceMetricRepository | None = None,
        exit_metric_repo: ExitResearchMetricRepository | None = None,
        market_data_repo: MarketDataRepository | None = None,
        ranking_performance_repo: RankingPerformanceRepository | None = None,
        regime_repo: RegimeAnalyticsRepository | None = None,
    ) -> None:
        self.db = db
        self.validation_repo = validation_repo
        self.factor_metric_repo = factor_metric_repo or FactorPerformanceMetricRepository(db)
        self.exit_metric_repo = exit_metric_repo or ExitResearchMetricRepository(db)
        self.market_data_repo = market_data_repo or MarketDataRepository(db)
        self.ranking_performance_repo = ranking_performance_repo or RankingPerformanceRepository(db)
        self.regime_repo = regime_repo or RegimeAnalyticsRepository(db)

    def build(
        self,
        *,
        ranking_run: RankingRun,
        result: RankingResult,
        stock: Stock,
    ) -> InvestmentReviewPacket:
        validation_report = self.validation_repo.get_by_ranking_run_id(ranking_run.id)
        regime_label = _validation_regime(validation_report, ranking_run)
        horizon_rows, decile_rows = _load_validation_metrics(self.db, validation_report)
        factor_ic, factor_metric_ids = _load_factor_ic(
            self.factor_metric_repo,
            strategy_name=ranking_run.strategy_name,
            strategy_version=ranking_run.strategy_version,
            universe_code=ranking_run.universe_code,
            regime_label=regime_label,
            as_of_date_end=ranking_run.as_of_date,
        )
        exit_research, exit_run_ids = _load_exit_research(
            self.exit_metric_repo,
            strategy_name=ranking_run.strategy_name,
            strategy_version=ranking_run.strategy_version,
            universe_code=ranking_run.universe_code,
            regime_label=regime_label,
        )
        historical = _load_historical_performance(
            self.db, ranking_run.id, result.stock_id
        )
        market_snapshot = _load_market_snapshot(self.market_data_repo, stock)
        strategy_regime = _load_strategy_regime_performance(
            self.regime_repo,
            strategy_name=ranking_run.strategy_name,
            strategy_version=ranking_run.strategy_version,
            regime_label=regime_label,
        )
        technical_factors = _technical_from_components(result.score_components or {})
        payload: dict[str, Any] = {
            "packet_version": PACKET_VERSION,
            "symbol": stock.symbol,
            "stock_id": str(result.stock_id),
            "ranking": {
                "ranking_run_id": str(ranking_run.id),
                "ranking_result_id": str(result.id),
                "strategy_name": ranking_run.strategy_name,
                "strategy_version": ranking_run.strategy_version,
                "universe_code": ranking_run.universe_code,
                "as_of_date": ranking_run.as_of_date.isoformat(),
                "rank": result.rank,
                "composite_score": float(result.score),
                "score_components": result.score_components or {},
                "inputs_hash": ranking_run.inputs_hash,
            },
            "technical_factors": technical_factors,
            "validation": {
                "report_id": str(validation_report.id) if validation_report else None,
                "status": validation_report.status if validation_report else None,
                "horizon_metrics": horizon_rows,
                "decile_metrics": decile_rows,
                "regime_label": regime_label,
            },
            "regime": {
                "regime_label": regime_label,
                "strategy_regime_performance": strategy_regime,
            },
            "quant_evidence": {
                "factor_ic": factor_ic,
                "exit_research": exit_research,
            },
            "historical_performance": historical,
            "market_snapshot": market_snapshot,
            "fundamental_snapshot": {},
            "news_snapshot": {"status": "unavailable", "items": []},
            "portfolio_context": {"existing_position": False},
            "research_context": {"notes": []},
            "source_lineage": {
                "ranking_run_id": str(ranking_run.id),
                "ranking_result_id": str(result.id),
                "validation_report_id": (
                    str(validation_report.id) if validation_report else None
                ),
                "factor_metric_ids": factor_metric_ids,
                "exit_research_run_ids": exit_run_ids,
                "market_data_through": market_snapshot.get("last_date"),
            },
        }
        packet_hash = compute_packet_hash(payload)
        payload["packet_built_at"] = datetime.now(UTC).isoformat()
        return InvestmentReviewPacket(
            symbol=stock.symbol,
            stock_id=result.stock_id,
            ranking_run_id=ranking_run.id,
            ranking_result_id=result.id,
            payload=payload,
            packet_hash=packet_hash,
            packet_version=PACKET_VERSION,
        )


def _load_validation_metrics(db, validation_report) -> tuple[list[dict], list[dict]]:
    if validation_report is None:
        return [], []
    horizon_rows = [
        {
            "horizon": row.horizon,
            "ic_pearson": float(row.ic_pearson) if row.ic_pearson is not None else None,
            "rank_ic_spearman": (
                float(row.rank_ic_spearman) if row.rank_ic_spearman is not None else None
            ),
            "spread": float(row.spread) if row.spread is not None else None,
            "sample_size": row.sample_size,
        }
        for row in db.scalars(
            select(ValidationHorizonMetric).where(
                ValidationHorizonMetric.validation_report_id == validation_report.id
            )
        ).all()
    ]
    decile_rows = [
        {
            "horizon": row.horizon,
            "decile": row.decile,
            "avg_return": float(row.avg_return) if row.avg_return is not None else None,
            "count": row.count,
        }
        for row in db.scalars(
            select(ValidationDecileMetric).where(
                ValidationDecileMetric.validation_report_id == validation_report.id
            )
        ).all()
    ]
    return horizon_rows, decile_rows


def _load_factor_ic(
    repo: FactorPerformanceMetricRepository,
    *,
    strategy_name: str,
    strategy_version: str,
    universe_code: str,
    regime_label: str | None,
    as_of_date_end,
) -> tuple[list[dict[str, Any]], list[str]]:
    metrics = repo.list_metrics(
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        universe_code=universe_code,
        regime_label=regime_label,
        as_of_date_end=as_of_date_end,
        limit=100,
    )
    metric_ids: list[str] = []
    rows: list[dict[str, Any]] = []
    for m in metrics:
        metric_ids.append(str(m.id))
        rows.append(
            {
                "id": str(m.id),
                "factor_name": m.factor_name,
                "horizon": m.horizon,
                "regime_label": m.regime_label,
                "dataset_split": m.dataset_split,
                "ic_spearman": float(m.ic_spearman) if m.ic_spearman is not None else None,
                "ic_pearson": float(m.ic_pearson) if m.ic_pearson is not None else None,
                "sample_size": m.sample_size,
            }
        )
    return rows, metric_ids


def _load_exit_research(
    repo: ExitResearchMetricRepository,
    *,
    strategy_name: str,
    strategy_version: str,
    universe_code: str,
    regime_label: str | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    metrics = repo.list_policy_metrics(
        strategy_name=strategy_name,
        universe_code=universe_code,
        regime_label=regime_label,
        limit=100,
    )
    metrics = [m for m in metrics if m.strategy_version == strategy_version]
    run_ids = {str(m.research_run_id) for m in metrics}
    rows = [
        {
            "id": str(m.id),
            "metric_id": str(m.id),
            "research_run_id": str(m.research_run_id),
            "policy_family": m.policy_family,
            "policy_variant": m.policy_variant,
            "horizon": m.horizon,
            "regime_label": m.regime_label,
            "hit_rate": float(m.hit_rate) if m.hit_rate is not None else None,
            "mean_return": float(m.mean_return) if m.mean_return is not None else None,
            "sample_size": m.sample_size,
        }
        for m in metrics[:50]
    ]
    return rows, sorted(run_ids)


def _load_historical_performance(
    db: Session, ranking_run_id: UUID, stock_id: UUID
) -> dict[str, Any]:
    snap = db.scalar(
        select(RankingPerformanceSnapshot).where(
            RankingPerformanceSnapshot.ranking_run_id == ranking_run_id,
            RankingPerformanceSnapshot.stock_id == stock_id,
        )
    )
    if snap is None:
        return {}
    return {
        "return_5d": snap.return_5d,
        "return_10d": snap.return_10d,
        "return_20d": snap.return_20d,
        "return_60d": snap.return_60d,
        "captured_at": snap.captured_at.isoformat() if snap.captured_at else None,
    }


def _load_market_snapshot(repo: MarketDataRepository, stock: Stock) -> dict[str, Any]:
    snapshot: dict[str, Any] = {"sector": stock.sector}
    bar = repo.get_latest_market_data(stock.id)
    if bar is None:
        return snapshot
    close = float(bar.close)
    snapshot["last_close"] = close
    snapshot["last_date"] = bar.date.isoformat()
    if bar.volume is not None:
        snapshot["adv_inr"] = close * int(bar.volume)
    return snapshot


def _load_strategy_regime_performance(
    repo: RegimeAnalyticsRepository,
    *,
    strategy_name: str,
    strategy_version: str,
    regime_label: str | None,
) -> list[dict[str, Any]]:
    rows = repo.list_strategy_regime_performance(
        strategy_name=strategy_name,
        strategy_version=strategy_version,
    )
    if regime_label:
        rows = [r for r in rows if r.regime_label == regime_label]
    return [
        {
            "regime_label": r.regime_label,
            "horizon": r.horizon,
            "avg_ic": float(r.avg_ic) if r.avg_ic is not None else None,
            "avg_spread": float(r.avg_spread) if r.avg_spread is not None else None,
            "sample_count": r.sample_count,
        }
        for r in rows[:20]
    ]


def _validation_regime(validation_report, ranking_run: RankingRun) -> str | None:
    if validation_report is not None:
        return validation_report.regime_label
    return ranking_run.regime_label


def _technical_from_components(components: dict) -> dict:
    skip = {"composite_score"}
    return {
        key: value
        for key, value in components.items()
        if key not in skip and isinstance(value, dict)
    }
