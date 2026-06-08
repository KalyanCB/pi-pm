"""Pilot reporting — daily / weekly / monthly / final report builders (read-only)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import DailyBatchRunStatus
from app.models.daily_batch import DailyBatchRun
from app.models.paper_trade import PaperTrade
from app.models.portfolio_analytics import PortfolioNavHistory, PortfolioReconciliationReport
from app.models.recommendation import RecommendationApproval, RecommendationOutcome, RecommendationRun
from app.ops.pilot.alerting import evaluate_alerts
from app.ops.pilot.serializers import to_jsonable


@dataclass
class PilotReport:
    report_type: str
    period_start: date
    period_end: date
    generated_for: date
    sections: dict = field(default_factory=dict)
    alerts: list = field(default_factory=list)


def build_daily_report(db: Session, as_of_date: date | None = None) -> PilotReport:
    as_of = as_of_date or date.today()
    alerts = evaluate_alerts(db, as_of_date=as_of)

    rec_runs = db.scalars(
        select(RecommendationRun).where(RecommendationRun.as_of_date == as_of)
    ).all()
    approvals = db.scalars(
        select(RecommendationApproval).where(
            func.date(RecommendationApproval.decided_at) == as_of
        )
    ).all()
    trades = db.scalars(
        select(PaperTrade).where(func.date(PaperTrade.filled_at) == as_of)
    ).all()
    nav = db.scalar(select(PortfolioNavHistory).where(PortfolioNavHistory.as_of_date == as_of))
    recon = db.scalar(
        select(PortfolioReconciliationReport).where(
            PortfolioReconciliationReport.as_of_date == as_of
        )
    )
    batch = db.scalar(
        select(DailyBatchRun)
        .where(DailyBatchRun.target_trading_day == as_of)
        .order_by(DailyBatchRun.started_at.desc())
        .limit(1)
    )

    return PilotReport(
        report_type="daily",
        period_start=as_of,
        period_end=as_of,
        generated_for=as_of,
        sections={
            "batch": _batch_summary(batch),
            "recommendations": {
                "runs": len(rec_runs),
                "strategies": [r.strategy_name for r in rec_runs],
                "statuses": [r.status for r in rec_runs],
            },
            "approvals": {
                "count": len(approvals),
                "approved": sum(1 for a in approvals if a.decision == "APPROVED"),
                "rejected": sum(1 for a in approvals if a.decision == "REJECTED"),
            },
            "paper_trades": {
                "count": len(trades),
                "buys": sum(1 for t in trades if t.side == "BUY"),
                "sells": sum(1 for t in trades if t.side == "SELL"),
            },
            "nav": _nav_summary(nav),
            "reconciliation": _recon_summary(recon),
        },
        alerts=to_jsonable(alerts),
    )


def build_weekly_report(db: Session, as_of_date: date | None = None) -> PilotReport:
    as_of = as_of_date or date.today()
    start = as_of - timedelta(days=6)
    return _period_report(db, "weekly", start, as_of)


def build_monthly_report(db: Session, as_of_date: date | None = None) -> PilotReport:
    as_of = as_of_date or date.today()
    start = as_of - timedelta(days=29)
    return _period_report(db, "monthly", start, as_of)


def build_final_report(
    db: Session,
    *,
    pilot_start: date,
    pilot_end: date,
) -> PilotReport:
    return _period_report(db, "final", pilot_start, pilot_end, include_success=True)


def _period_report(
    db: Session,
    report_type: str,
    start: date,
    end: date,
    *,
    include_success: bool = False,
) -> PilotReport:
    alerts = evaluate_alerts(db, as_of_date=end)

    batches = db.scalars(
        select(DailyBatchRun).where(
            DailyBatchRun.target_trading_day >= start,
            DailyBatchRun.target_trading_day <= end,
        )
    ).all()
    nav_rows = db.scalars(
        select(PortfolioNavHistory).where(
            PortfolioNavHistory.as_of_date >= start,
            PortfolioNavHistory.as_of_date <= end,
        ).order_by(PortfolioNavHistory.as_of_date)
    ).all()
    outcomes = db.scalars(
        select(RecommendationOutcome).where(
            RecommendationOutcome.entry_date >= start,
            RecommendationOutcome.entry_date <= end,
        )
    ).all()
    trades = db.scalars(
        select(PaperTrade).where(
            func.date(PaperTrade.filled_at) >= start,
            func.date(PaperTrade.filled_at) <= end,
        )
    ).all()

    sections: dict = {
        "batch": {
            "total_runs": len(batches),
            "completed": sum(1 for b in batches if b.status == DailyBatchRunStatus.COMPLETED.value),
            "failed": sum(1 for b in batches if b.status == DailyBatchRunStatus.FAILED.value),
        },
        "nav": {
            "snapshots": len(nav_rows),
            "start_equity": float(nav_rows[0].total_equity) if nav_rows else None,
            "end_equity": float(nav_rows[-1].total_equity) if nav_rows else None,
            "cumulative_return_pct": _cumulative_return(nav_rows),
            "cumulative_alpha_pct": _cumulative_alpha(nav_rows),
        },
        "outcomes": {
            "total": len(outcomes),
            "closed": sum(1 for o in outcomes if o.outcome_status != "OPEN"),
            "wins": sum(1 for o in outcomes if o.outcome_status == "WIN"),
            "losses": sum(1 for o in outcomes if o.outcome_status == "LOSS"),
        },
        "paper_trades": {
            "total": len(trades),
            "entries": sum(1 for t in trades if t.side == "BUY"),
            "exits": sum(1 for t in trades if t.side == "SELL"),
        },
    }

    if include_success:
        sections["success_metrics"] = compute_success_metrics(db, start, end)

    return PilotReport(
        report_type=report_type,
        period_start=start,
        period_end=end,
        generated_for=end,
        sections=sections,
        alerts=to_jsonable(alerts),
    )


def compute_success_metrics(db: Session, start: date, end: date) -> dict:
    batches = db.scalars(
        select(DailyBatchRun).where(
            DailyBatchRun.target_trading_day >= start,
            DailyBatchRun.target_trading_day <= end,
        )
    ).all()
    recons = db.scalars(
        select(PortfolioReconciliationReport).where(
            PortfolioReconciliationReport.as_of_date >= start,
            PortfolioReconciliationReport.as_of_date <= end,
        )
    ).all()
    nav_rows = db.scalars(
        select(PortfolioNavHistory).where(
            PortfolioNavHistory.as_of_date >= start,
            PortfolioNavHistory.as_of_date <= end,
        )
    ).all()
    outcomes = db.scalars(
        select(RecommendationOutcome).where(
            RecommendationOutcome.outcome_status != "OPEN",
        )
    ).all()

    batch_total = len(batches) or 1
    recon_total = len(recons) or 1
    closed = [o for o in outcomes if o.outcome_status in ("WIN", "LOSS", "BREAKEVEN")]
    wins = sum(1 for o in closed if o.outcome_status == "WIN")

    return {
        "batch_completion_rate": round(
            sum(1 for b in batches if b.status == "completed") / batch_total, 4
        ),
        "reconciliation_pass_rate": round(
            sum(1 for r in recons if r.status == "PASS") / recon_total, 4
        ),
        "nav_coverage_days": len(nav_rows),
        "win_rate": round(wins / len(closed), 4) if closed else None,
        "trading_days_in_period": (end - start).days + 1,
    }


def _batch_summary(batch) -> dict | None:
    if batch is None:
        return None
    return {
        "run_id": str(batch.id),
        "status": batch.status,
        "target_trading_day": batch.target_trading_day.isoformat()
        if batch.target_trading_day
        else None,
        "duration_seconds": float(batch.duration_seconds) if batch.duration_seconds else None,
        "phases": list((batch.phase_results or {}).keys()),
    }


def _nav_summary(nav) -> dict | None:
    if nav is None:
        return None
    return {
        "total_equity": float(nav.total_equity),
        "day_return_pct": float(nav.day_return_pct) if nav.day_return_pct else None,
        "alpha_pct": float(nav.alpha_pct) if nav.alpha_pct else None,
        "open_positions": nav.open_positions,
    }


def _recon_summary(recon) -> dict | None:
    if recon is None:
        return None
    return {
        "status": recon.status,
        "discrepancy_pct": float(recon.discrepancy_pct),
    }


def _cumulative_return(nav_rows: list) -> float | None:
    if len(nav_rows) < 2:
        return None
    start = float(nav_rows[0].total_equity)
    end = float(nav_rows[-1].total_equity)
    if start <= 0:
        return None
    return round((end - start) / start * 100, 4)


def _cumulative_alpha(nav_rows: list) -> float | None:
    alphas = [float(r.alpha_pct) for r in nav_rows if r.alpha_pct is not None]
    if not alphas:
        return None
    return round(sum(alphas), 4)
