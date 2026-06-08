"""Pilot alerting — read-only anomaly detection. No side effects."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import DailyBatchRunStatus
from app.models.daily_batch import DailyBatchRun
from app.models.portfolio_analytics import PortfolioNavHistory, PortfolioReconciliationReport
from app.models.recommendation import RecommendationResult, RecommendationRun
from app.portfolio.reconciliation.service import ReconciliationService


class AlertSeverity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertCode(StrEnum):
    BATCH_FAILED = "batch_failed"
    BATCH_STALE = "batch_stale"
    BATCH_MISSING_PORTFOLIO = "batch_missing_portfolio"
    RECON_FAIL = "reconciliation_fail"
    RECON_MISSING = "reconciliation_missing"
    NAV_MISSING = "nav_missing"
    RECOMMENDATION_ZERO = "recommendation_zero"
    RECOMMENDATION_RUN_FAILED = "recommendation_run_failed"
    APPROVAL_BACKLOG = "approval_backlog"
    EXIT_BACKLOG = "exit_backlog"
    PORTFOLIO_CASH_NEGATIVE = "portfolio_cash_negative"
    PORTFOLIO_SLOTS_EXCEEDED = "portfolio_slots_exceeded"
    TRUST_CALIBRATION_WEAK = "trust_calibration_weak"


@dataclass
class PilotAlert:
    code: str
    severity: str
    message: str
    as_of_date: str | None = None
    details: dict = field(default_factory=dict)


def evaluate_alerts(
    db: Session,
    *,
    as_of_date: date | None = None,
    pilot_start_date: date | None = None,
) -> list[PilotAlert]:
    """Evaluate all pilot alerts for the command center."""
    as_of = as_of_date or date.today()
    alerts: list[PilotAlert] = []

    _check_batch(db, as_of, alerts)
    _check_reconciliation(db, as_of, alerts)
    _check_nav(db, as_of, alerts)
    _check_recommendations(db, as_of, alerts)
    _check_portfolio(db, as_of, alerts)
    _check_backlogs(db, alerts)

    return sorted(alerts, key=lambda a: (a.severity != AlertSeverity.CRITICAL.value, a.code))


def _check_batch(db: Session, as_of: date, alerts: list[PilotAlert]) -> None:
    latest = db.scalar(
        select(DailyBatchRun).order_by(DailyBatchRun.started_at.desc()).limit(1)
    )
    if latest is None:
        alerts.append(
            PilotAlert(
                code=AlertCode.BATCH_STALE.value,
                severity=AlertSeverity.CRITICAL.value,
                message="No daily batch runs found.",
            )
        )
        return

    if latest.status == DailyBatchRunStatus.FAILED.value:
        alerts.append(
            PilotAlert(
                code=AlertCode.BATCH_FAILED.value,
                severity=AlertSeverity.CRITICAL.value,
                message=f"Latest batch run failed: {latest.error_message or 'unknown'}",
                as_of_date=latest.target_trading_day.isoformat()
                if latest.target_trading_day
                else None,
                details={"run_id": str(latest.id)},
            )
        )

    if latest.target_trading_day and (as_of - latest.target_trading_day).days > 3:
        alerts.append(
            PilotAlert(
                code=AlertCode.BATCH_STALE.value,
                severity=AlertSeverity.WARNING.value,
                message=f"Last batch target day {latest.target_trading_day} is stale.",
                details={"run_id": str(latest.id), "status": latest.status},
            )
        )

    phase_results = latest.phase_results or {}
    if latest.status == DailyBatchRunStatus.COMPLETED.value:
        if "portfolio_reconcile" not in phase_results and "portfolio_nav" not in phase_results:
            params = latest.parameter_set or {}
            if params.get("phases", {}).get("portfolio"):
                alerts.append(
                    PilotAlert(
                        code=AlertCode.BATCH_MISSING_PORTFOLIO.value,
                        severity=AlertSeverity.WARNING.value,
                        message="Batch completed but portfolio phases missing from results.",
                        details={"run_id": str(latest.id)},
                    )
                )


def _check_reconciliation(db: Session, as_of: date, alerts: list[PilotAlert]) -> None:
    report = db.scalar(
        select(PortfolioReconciliationReport)
        .where(PortfolioReconciliationReport.as_of_date <= as_of)
        .order_by(PortfolioReconciliationReport.as_of_date.desc())
        .limit(1)
    )
    if report is None:
        alerts.append(
            PilotAlert(
                code=AlertCode.RECON_MISSING.value,
                severity=AlertSeverity.WARNING.value,
                message="No reconciliation report on file.",
            )
        )
        return

    if report.status == "FAIL":
        alerts.append(
            PilotAlert(
                code=AlertCode.RECON_FAIL.value,
                severity=AlertSeverity.CRITICAL.value,
                message=f"Reconciliation FAIL on {report.as_of_date}.",
                as_of_date=report.as_of_date.isoformat(),
                details={
                    "discrepancy_pct": float(report.discrepancy_pct),
                    "failures": report.failures or [],
                },
            )
        )
    elif report.as_of_date < as_of - timedelta(days=2):
        alerts.append(
            PilotAlert(
                code=AlertCode.RECON_MISSING.value,
                severity=AlertSeverity.WARNING.value,
                message=f"Latest reconciliation is {report.as_of_date}, expected ~{as_of}.",
            )
        )


def _check_nav(db: Session, as_of: date, alerts: list[PilotAlert]) -> None:
    nav = db.scalar(
        select(PortfolioNavHistory).where(PortfolioNavHistory.as_of_date == as_of)
    )
    if nav is None:
        latest = db.scalar(
            select(PortfolioNavHistory)
            .order_by(PortfolioNavHistory.as_of_date.desc())
            .limit(1)
        )
        if latest is None or latest.as_of_date < as_of - timedelta(days=2):
            alerts.append(
                PilotAlert(
                    code=AlertCode.NAV_MISSING.value,
                    severity=AlertSeverity.WARNING.value,
                    message=f"No NAV snapshot for {as_of.isoformat()}.",
                    details={
                        "latest_nav_date": latest.as_of_date.isoformat() if latest else None
                    },
                )
            )


def _check_recommendations(db: Session, as_of: date, alerts: list[PilotAlert]) -> None:
    runs = db.scalars(
        select(RecommendationRun).where(RecommendationRun.as_of_date == as_of)
    ).all()
    if not runs:
        return

    failed = [r for r in runs if r.status != "completed"]
    if failed:
        alerts.append(
            PilotAlert(
                code=AlertCode.RECOMMENDATION_RUN_FAILED.value,
                severity=AlertSeverity.WARNING.value,
                message=f"{len(failed)} recommendation run(s) not completed for {as_of}.",
                details={"run_ids": [str(r.id) for r in failed]},
            )
        )

    total_results = 0
    for run in runs:
        total_results += (
            db.scalar(
                select(func.count(RecommendationResult.id)).where(
                    RecommendationResult.recommendation_run_id == run.id
                )
            )
            or 0
        )
    if total_results == 0:
        alerts.append(
            PilotAlert(
                code=AlertCode.RECOMMENDATION_ZERO.value,
                severity=AlertSeverity.WARNING.value,
                message=f"Zero recommendation results for {as_of}.",
            )
        )


def _check_portfolio(db: Session, as_of: date, alerts: list[PilotAlert]) -> None:
    recon = ReconciliationService(db)
    latest = recon.get_latest()
    if latest and float(latest.cash_from_ledger) < 0:
        alerts.append(
            PilotAlert(
                code=AlertCode.PORTFOLIO_CASH_NEGATIVE.value,
                severity=AlertSeverity.CRITICAL.value,
                message="Cash ledger balance is negative.",
                details={"cash": float(latest.cash_from_ledger)},
            )
        )


def _check_backlogs(db: Session, alerts: list[PilotAlert]) -> None:
    pending_approvals = (
        db.scalar(
            select(func.count(RecommendationResult.id)).where(
                RecommendationResult.action == "BUY",
                RecommendationResult.lifecycle_state == "CANDIDATE",
            )
        )
        or 0
    )
    if pending_approvals > 10:
        alerts.append(
            PilotAlert(
                code=AlertCode.APPROVAL_BACKLOG.value,
                severity=AlertSeverity.INFO.value,
                message=f"{pending_approvals} BUY recommendations awaiting approval.",
                details={"count": int(pending_approvals)},
            )
        )

    from app.models.portfolio_analytics import ExitRecommendation

    pending_exits = (
        db.scalar(
            select(func.count(ExitRecommendation.id)).where(
                ExitRecommendation.status == "PENDING"
            )
        )
        or 0
    )
    if pending_exits > 5:
        alerts.append(
            PilotAlert(
                code=AlertCode.EXIT_BACKLOG.value,
                severity=AlertSeverity.INFO.value,
                message=f"{pending_exits} exit recommendations pending human review.",
                details={"count": int(pending_exits)},
            )
        )
