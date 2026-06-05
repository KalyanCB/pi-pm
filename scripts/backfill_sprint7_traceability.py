#!/usr/bin/env python3
"""Sprint 7.1 — backfill traceability tables from persisted ranking/validation artifacts."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from sqlalchemy import exists, func, select

from app.core.config import get_settings
from app.core.constants import RankingRunStatus
from app.db.repositories.ingestion_run_repository import IngestionRunRepository
from app.db.repositories.ranking_factor_contribution_repository import (
    RankingFactorContributionRepository,
)
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.validation_metrics_repository import ValidationMetricsRepository
from app.db.session import get_session_factory
from app.models.platform_traceability import RankingFactorContribution, ValidationHorizonMetric
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport
from app.services.traceability_service import TraceabilityService
from app.validation.constants import VALIDATION_STATUS_COMPLETED


@dataclass
class BackfillStats:
    ranking_runs_processed: int = 0
    ranking_runs_updated: int = 0
    validation_reports_processed: int = 0
    validation_reports_updated: int = 0
    regime_rows_upserted: int = 0
    lineage_links_created: int = 0


def _build_traceability_service(db) -> TraceabilityService:
    return TraceabilityService(
        db,
        RankingFactorContributionRepository(db),
        ValidationMetricsRepository(db),
        RunLineageRepository(db),
        IngestionRunRepository(db),
    )


def _ranking_runs_needing_backfill(db, limit: int | None) -> list[RankingRun]:
    has_components = exists(
        select(RankingResult.id).where(
            RankingResult.ranking_run_id == RankingRun.id,
            RankingResult.score_components.is_not(None),
        )
    )
    missing_factors = ~exists(
        select(RankingFactorContribution.id).where(
            RankingFactorContribution.ranking_run_id == RankingRun.id
        )
    )
    missing_metadata = (
        (RankingRun.weight_config_hash.is_(None))
        | (RankingRun.ranked_stock_count.is_(None))
        | (RankingRun.excluded_stock_count.is_(None))
        | (RankingRun.regime_label.is_(None))
    )
    stmt = (
        select(RankingRun)
        .where(
            RankingRun.status == RankingRunStatus.COMPLETED.value,
            has_components,
            missing_factors | missing_metadata,
        )
        .order_by(RankingRun.as_of_date)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())


def _validation_reports_needing_backfill(db, limit: int | None) -> list[RankingValidationReport]:
    missing_metrics = ~exists(
        select(ValidationHorizonMetric.id).where(
            ValidationHorizonMetric.validation_report_id == RankingValidationReport.id
        )
    )
    stmt = (
        select(RankingValidationReport)
        .where(
            RankingValidationReport.status == VALIDATION_STATUS_COMPLETED,
            RankingValidationReport.horizon_metrics.is_not(None),
            RankingValidationReport.horizon_metrics != {},
            missing_metrics,
        )
        .order_by(RankingValidationReport.computed_at)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())


def _validation_reports_for_regime(db, limit: int | None) -> list[tuple]:
    stmt = (
        select(
            RankingRun.as_of_date,
            RankingRun.benchmark_symbol,
            RankingValidationReport.trend_regime,
            RankingValidationReport.vol_regime,
            RankingValidationReport.regime_label,
        )
        .join(RankingRun, RankingRun.id == RankingValidationReport.ranking_run_id)
        .where(
            RankingValidationReport.status == VALIDATION_STATUS_COMPLETED,
            RankingValidationReport.regime_label.is_not(None),
            RankingValidationReport.trend_regime.is_not(None),
            RankingValidationReport.vol_regime.is_not(None),
        )
        .distinct()
        .order_by(RankingRun.as_of_date)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.execute(stmt).all())


def _validation_reports_for_lineage(db, limit: int | None) -> list[RankingValidationReport]:
    stmt = (
        select(RankingValidationReport)
        .where(RankingValidationReport.status == VALIDATION_STATUS_COMPLETED)
        .order_by(RankingValidationReport.computed_at)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())


def backfill_ranking(
    db, service: TraceabilityService, *, limit: int | None, dry_run: bool
) -> BackfillStats:
    stats = BackfillStats()
    runs = _ranking_runs_needing_backfill(db, limit)
    stats.ranking_runs_processed = len(runs)
    if dry_run:
        print(f"[dry-run] ranking runs to backfill: {len(runs)}")
        return stats

    for run in runs:
        if service.ensure_ranking_traceability(run):
            stats.ranking_runs_updated += 1
    return stats


def backfill_validation(
    db, service: TraceabilityService, *, limit: int | None, dry_run: bool
) -> BackfillStats:
    stats = BackfillStats()
    reports = _validation_reports_needing_backfill(db, limit)
    stats.validation_reports_processed = len(reports)
    if dry_run:
        print(f"[dry-run] validation reports to backfill: {len(reports)}")
        return stats

    for report in reports:
        run = db.scalar(select(RankingRun).where(RankingRun.id == report.ranking_run_id))
        if run is None:
            continue
        if service.ensure_validation_traceability(report, run):
            stats.validation_reports_updated += 1
    return stats


def backfill_regime(db, *, limit: int | None, dry_run: bool) -> BackfillStats:
    stats = BackfillStats()
    rows = _validation_reports_for_regime(db, limit)
    stats.regime_rows_upserted = len(rows)
    if dry_run:
        print(f"[dry-run] regime history rows to upsert: {len(rows)}")
        return stats

    repo = RegimeAnalyticsRepository(db)
    for as_of_date, benchmark_symbol, trend_regime, vol_regime, regime_label in rows:
        repo.upsert_regime(
            as_of_date=as_of_date,
            benchmark_symbol=benchmark_symbol,
            trend_regime=trend_regime,
            vol_regime=vol_regime,
            regime_label=regime_label,
        )
    db.commit()
    return stats


def backfill_lineage(
    db, service: TraceabilityService, *, limit: int | None, dry_run: bool
) -> BackfillStats:
    stats = BackfillStats()
    reports = _validation_reports_for_lineage(db, limit)
    stats.validation_reports_processed = len(reports)
    if dry_run:
        print(f"[dry-run] validation reports for lineage: {len(reports)}")
        return stats

    for report in reports:
        run = db.scalar(select(RankingRun).where(RankingRun.id == report.ranking_run_id))
        if run is None:
            continue
        if service.ensure_validation_lineage(report, run):
            stats.lineage_links_created += 1
    return stats


def print_summary(db) -> None:
    print("\n--- Traceability table counts ---")
    queries = {
        "ranking_factor_contributions": select(func.count()).select_from(RankingFactorContribution),
        "validation_horizon_metrics": select(func.count()).select_from(ValidationHorizonMetric),
        "ranking_runs_with_weight_hash": select(func.count())
        .select_from(RankingRun)
        .where(RankingRun.weight_config_hash.is_not(None)),
        "ranking_runs_with_ranked_count": select(func.count())
        .select_from(RankingRun)
        .where(RankingRun.ranked_stock_count.is_not(None)),
    }
    for label, stmt in queries.items():
        print(f"{label}: {int(db.scalar(stmt) or 0)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill Sprint 7 traceability tables")
    parser.add_argument("--ranking", action="store_true", help="Backfill ranking traceability")
    parser.add_argument("--validation", action="store_true", help="Backfill validation metrics")
    parser.add_argument("--regime", action="store_true", help="Backfill regime_history")
    parser.add_argument("--lineage", action="store_true", help="Backfill run_lineage_records")
    parser.add_argument("--all", action="store_true", help="Run all backfill phases")
    parser.add_argument("--limit", type=int, default=None, help="Limit rows per phase")
    parser.add_argument("--dry-run", action="store_true", help="Count candidates only")
    args = parser.parse_args()

    if not any([args.ranking, args.validation, args.regime, args.lineage, args.all]):
        parser.error(
            "Specify at least one of --ranking, --validation, --regime, --lineage, or --all"
        )

    get_settings()
    session_factory = get_session_factory()
    db = session_factory()

    try:
        print_summary(db)
        service = _build_traceability_service(db)

        if args.all or args.ranking:
            stats = backfill_ranking(db, service, limit=args.limit, dry_run=args.dry_run)
            print(
                f"ranking: processed={stats.ranking_runs_processed} "
                f"updated={stats.ranking_runs_updated}"
            )

        if args.all or args.validation:
            stats = backfill_validation(db, service, limit=args.limit, dry_run=args.dry_run)
            print(
                f"validation: processed={stats.validation_reports_processed} "
                f"updated={stats.validation_reports_updated}"
            )

        if args.all or args.regime:
            stats = backfill_regime(db, limit=args.limit, dry_run=args.dry_run)
            print(f"regime: upserted={stats.regime_rows_upserted}")

        if args.all or args.lineage:
            stats = backfill_lineage(db, service, limit=args.limit, dry_run=args.dry_run)
            print(
                f"lineage: processed={stats.validation_reports_processed} "
                f"reports_with_new_links={stats.lineage_links_created}"
            )

        if not args.dry_run:
            print_summary(db)
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
