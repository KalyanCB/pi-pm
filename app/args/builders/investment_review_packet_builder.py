from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.args.builders.packet_evidence_coverage import (
    derive_evidence_confidence,
    score_packet_evidence,
)
from app.args.validation_status import normalize_validation_status_for_packet
from app.db.repositories.exit_research_metric_repository import ExitResearchMetricRepository
from app.db.repositories.factor_performance_metric_repository import (
    FactorPerformanceMetricRepository,
)
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_performance_repository import RankingPerformanceRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.db.repositories.research_intelligence_repository import (
    ResearchIntelligenceReportRepository,
)
from app.factor_analytics.constants import REGIME_LABEL_ALL
from app.models.platform_traceability import ValidationDecileMetric, ValidationHorizonMetric
from app.models.ranking_performance_snapshot import RankingPerformanceSnapshot
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.stock import Stock
from app.workspace_args.constants import PACKET_VERSION
from app.workspace_args.models import InvestmentReviewPacket
from app.args.plugins.stock_quality_evidence import (
    SCHEMA_VERSION as SQE_SCHEMA_VERSION,
    build_stock_quality_evidence,
)
from app.stock_setup_evidence.packet_enricher import attach_stock_setup_evidence
from app.services.stock_setup_research_service import StockSetupResearchService
from app.workspace_args.packet_schema import compute_packet_hash

_HISTORICAL_VALIDATION_LOOKBACK_DAYS = 120
_MAX_HISTORICAL_VALIDATION_REPORTS = 12


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
        research_intel_repo: ResearchIntelligenceReportRepository | None = None,
        stock_setup_service: StockSetupResearchService | None = None,
    ) -> None:
        self.db = db
        self.validation_repo = validation_repo
        self.stock_setup_service = stock_setup_service
        self.factor_metric_repo = factor_metric_repo or FactorPerformanceMetricRepository(db)
        self.exit_metric_repo = exit_metric_repo or ExitResearchMetricRepository(db)
        self.market_data_repo = market_data_repo or MarketDataRepository(db)
        self.ranking_performance_repo = ranking_performance_repo or RankingPerformanceRepository(db)
        self.regime_repo = regime_repo or RegimeAnalyticsRepository(db)
        self.research_intel_repo = research_intel_repo or ResearchIntelligenceReportRepository(db)

    def build(
        self,
        *,
        ranking_run: RankingRun,
        result: RankingResult,
        stock: Stock,
    ) -> InvestmentReviewPacket:
        validation_report = self.validation_repo.get_by_ranking_run_id(ranking_run.id)
        raw_validation_status = validation_report.status if validation_report else None
        packet_validation_status, database_validation_status, pending_reason = (
            normalize_validation_status_for_packet(raw_validation_status)
        )
        regime_label = _validation_regime(validation_report, ranking_run)
        horizon_rows, decile_rows = _load_validation_metrics(self.db, validation_report)
        regime_labels = _regime_label_scope(regime_label)

        factor_ic, factor_metric_ids, factor_window = _load_factor_ic(
            self.factor_metric_repo,
            strategy_name=ranking_run.strategy_name,
            strategy_version=ranking_run.strategy_version,
            universe_code=ranking_run.universe_code,
            as_of_date=ranking_run.as_of_date,
            regime_labels=regime_labels,
        )
        factor_daily = _load_factor_daily(
            self.factor_metric_repo,
            ranking_run=ranking_run,
            regime_labels=regime_labels,
        )
        exit_research, exit_run_ids, exit_window = _load_exit_research(
            self.exit_metric_repo,
            strategy_name=ranking_run.strategy_name,
            strategy_version=ranking_run.strategy_version,
            universe_code=ranking_run.universe_code,
            as_of_date=ranking_run.as_of_date,
            regime_labels=regime_labels,
        )
        historical_validation = _load_historical_validation_context(
            self.db,
            self.validation_repo,
            strategy_name=ranking_run.strategy_name,
            strategy_version=ranking_run.strategy_version,
            universe_code=ranking_run.universe_code,
            as_of_date=ranking_run.as_of_date,
        )
        historical = _load_historical_performance(self.db, ranking_run.id, result.stock_id)
        market_snapshot = _load_market_snapshot(self.market_data_repo, stock)
        strategy_regime = _load_strategy_regime_performance(
            self.regime_repo,
            strategy_name=ranking_run.strategy_name,
            strategy_version=ranking_run.strategy_version,
            current_regime_label=regime_label,
        )
        research_context = _load_research_context(
            self.research_intel_repo,
            universe_code=ranking_run.universe_code,
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
                "status": packet_validation_status,
                "database_status": database_validation_status,
                "pending_reason": pending_reason,
                "horizon_metrics": horizon_rows,
                "decile_metrics": decile_rows,
                "regime_label": regime_label,
            },
            "historical_validation_context": historical_validation,
            "regime": {
                "regime_label": regime_label,
                "strategy_regime_performance": strategy_regime,
            },
            "quant_evidence": {
                "factor_ic": factor_ic,
                "factor_ic_window": factor_window,
                "factor_daily": factor_daily,
                "exit_research": exit_research,
                "exit_research_window": exit_window,
            },
            "historical_performance": historical,
            "market_snapshot": market_snapshot,
            "fundamental_snapshot": {},
            "news_snapshot": {"status": "unavailable", "items": []},
            "portfolio_context": {"existing_position": False},
            "research_context": research_context,
            "source_lineage": {
                "ranking_run_id": str(ranking_run.id),
                "ranking_result_id": str(result.id),
                "validation_report_id": (
                    str(validation_report.id) if validation_report else None
                ),
                "factor_metric_ids": factor_metric_ids,
                "exit_research_run_ids": exit_run_ids,
                "research_intelligence_run_id": research_context.get("run_id"),
                "market_data_through": market_snapshot.get("last_date"),
            },
        }
        attach_stock_setup_evidence(
            payload,
            see_service=self.stock_setup_service,
            ranking_run_id=ranking_run.id,
            stock_id=result.stock_id,
        )
        see_id = (payload.get("stock_setup_evidence") or {}).get("research_id")
        if see_id:
            payload["source_lineage"]["stock_setup_research_id"] = see_id

        coverage = score_packet_evidence(payload)
        payload["evidence_coverage"] = coverage
        payload["evidence_confidence"] = derive_evidence_confidence(payload, coverage)

        sqe = build_stock_quality_evidence(payload, stock.symbol)
        payload["stock_quality_evidence"] = sqe
        lineage = payload.setdefault("source_lineage", {})
        lineage["stock_quality_evidence_schema_version"] = SQE_SCHEMA_VERSION
        lineage["stock_quality_evidence_ranking_run_id"] = sqe.get("ranking_run_id")

        payload["packet_built_at"] = datetime.now(UTC).isoformat()
        packet_hash = compute_packet_hash(payload)
        return InvestmentReviewPacket(
            symbol=stock.symbol,
            stock_id=result.stock_id,
            ranking_run_id=ranking_run.id,
            ranking_result_id=result.id,
            payload=payload,
            packet_hash=packet_hash,
            packet_version=PACKET_VERSION,
        )


def _regime_label_scope(regime_label: str | None) -> list[str] | None:
    if not regime_label:
        return None
    labels = [regime_label, REGIME_LABEL_ALL]
    return list(dict.fromkeys(labels))


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
    as_of_date: date,
    regime_labels: list[str] | None,
) -> tuple[list[dict[str, Any]], list[str], dict[str, str] | None]:
    metrics = repo.list_metrics_covering_as_of(
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        universe_code=universe_code,
        as_of_date=as_of_date,
        regime_labels=regime_labels,
        limit=500,
    )
    if not metrics:
        return [], [], None

    window = {
        "as_of_date_start": metrics[0].as_of_date_start.isoformat(),
        "as_of_date_end": metrics[0].as_of_date_end.isoformat(),
    }
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
                "stability_score": (
                    float(m.stability_score) if m.stability_score is not None else None
                ),
                "confidence": m.confidence,
            }
        )
    return rows, metric_ids, window


def _load_factor_daily(
    repo: FactorPerformanceMetricRepository,
    *,
    ranking_run: RankingRun,
    regime_labels: list[str] | None,
) -> list[dict[str, Any]]:
    daily = repo.list_daily_for_ranking_run(ranking_run_id=ranking_run.id, limit=200)
    if not daily:
        daily = repo.list_daily_covering_as_of(
            strategy_name=ranking_run.strategy_name,
            strategy_version=ranking_run.strategy_version,
            universe_code=ranking_run.universe_code,
            as_of_date=ranking_run.as_of_date,
            regime_labels=regime_labels,
            limit=200,
        )
    return [
        {
            "factor_name": row.factor_name,
            "horizon": row.horizon,
            "regime_label": row.regime_label,
            "dataset_split": row.dataset_split,
            "ic_spearman": float(row.ic_spearman) if row.ic_spearman is not None else None,
            "sample_size": row.sample_size,
            "as_of_date": row.as_of_date.isoformat(),
        }
        for row in daily
        if row.ic_spearman is not None
    ]


def _load_exit_research(
    repo: ExitResearchMetricRepository,
    *,
    strategy_name: str,
    strategy_version: str,
    universe_code: str,
    as_of_date: date,
    regime_labels: list[str] | None,
) -> tuple[list[dict[str, Any]], list[str], dict[str, str] | None]:
    metrics = repo.list_policy_metrics_covering_as_of(
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        universe_code=universe_code,
        as_of_date=as_of_date,
        regime_labels=regime_labels,
        limit=100,
    )
    if not metrics:
        return [], [], None

    window = {
        "as_of_date_start": metrics[0].as_of_date_start.isoformat(),
        "as_of_date_end": metrics[0].as_of_date_end.isoformat(),
    }
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
        for m in metrics
    ]
    return rows, sorted(run_ids), window


def _load_historical_validation_context(
    db: Session,
    validation_repo: RankingValidationRepository,
    *,
    strategy_name: str,
    strategy_version: str,
    universe_code: str,
    as_of_date: date,
) -> dict[str, Any]:
    start = as_of_date - timedelta(days=_HISTORICAL_VALIDATION_LOOKBACK_DAYS)
    reports = validation_repo.list_completed_with_runs(
        universe_code=universe_code,
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        start_date=start,
        end_date=as_of_date,
    )
    recent: list[dict[str, Any]] = []
    for report in reports[-_MAX_HISTORICAL_VALIDATION_REPORTS:]:
        run = report.ranking_run
        if run is None:
            continue
        horizons, deciles = _load_validation_metrics(db, report)
        recent.append(
            {
                "as_of_date": run.as_of_date.isoformat(),
                "report_id": str(report.id),
                "regime_label": report.regime_label,
                "horizon_metrics": horizons,
                "decile_metrics": deciles,
            }
        )

    return {
        "lookback_days": _HISTORICAL_VALIDATION_LOOKBACK_DAYS,
        "completed_reports_in_window": len(reports),
        "recent_completed_validations": recent,
        "note": (
            "Historical completed validations supply QRC context when the current run "
            "is pending (forward horizons not yet available)."
        ),
    }


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
    current_regime_label: str | None,
) -> list[dict[str, Any]]:
    rows = repo.list_strategy_regime_performance(
        strategy_name=strategy_name,
        strategy_version=strategy_version,
    )
    return [
        {
            "regime_label": r.regime_label,
            "horizon": r.horizon,
            "avg_ic": float(r.avg_ic) if r.avg_ic is not None else None,
            "avg_spread": float(r.avg_spread) if r.avg_spread is not None else None,
            "sample_count": r.sample_count,
            "is_current_regime": r.regime_label == current_regime_label,
        }
        for r in rows
    ]


def _load_research_context(
    repo: ResearchIntelligenceReportRepository,
    *,
    universe_code: str,
) -> dict[str, Any]:
    run = repo.get_latest_run(universe_code=universe_code)
    if run is None:
        return {"notes": [], "reports": {}, "run_id": None}

    reports = repo.list_for_run(run.id)
    report_map = {row.report_type: row.payload for row in reports}
    notes: list[str] = []

    executive = report_map.get("executive_committee_summary") or {}
    for conclusion in executive.get("key_conclusions") or []:
        notes.append(str(conclusion))

    top20 = report_map.get("current_top_20_candidates") or {}
    if top20.get("as_of_date"):
        notes.append(
            f"Research intelligence top-20 as_of={top20['as_of_date']} "
            f"(run_id={top20.get('run_id')})."
        )

    ic_strategy = report_map.get("ic_by_strategy") or {}
    if ic_strategy:
        notes.append(f"IC by strategy snapshot available ({len(ic_strategy)} entries).")

    return {
        "run_id": str(run.id),
        "window": {
            "start": run.as_of_date_start.isoformat(),
            "end": run.as_of_date_end.isoformat(),
        },
        "notes": notes,
        "reports": {
            key: _compact_report_payload(value) for key, value in report_map.items()
        },
    }


def _compact_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"value": payload}
    if "entries" in payload:
        return {"report": payload.get("report"), "entry_count": len(payload.get("entries") or [])}
    if "key_conclusions" in payload:
        return {"key_conclusions": payload.get("key_conclusions")}
    return {k: payload[k] for k in list(payload.keys())[:8]}


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
