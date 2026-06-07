"""Pilot Command Center — read-only operational visibility for 90-day paper pilot.

Aggregates existing analytics services. Does not modify investment logic.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.daily_batch import DailyBatchRun
from app.models.paper_trade import PaperTrade
from app.models.portfolio_analytics import PortfolioNavHistory
from app.models.recommendation import RecommendationApproval, RecommendationOutcome, RecommendationResult, RecommendationRun
from app.ops.daily_batch.paper_pilot_ops import PaperPilotOps
from app.ops.pilot.alerting import evaluate_alerts
from app.ops.pilot.reporting import (
    build_daily_report,
    build_final_report,
    build_monthly_report,
    build_weekly_report,
    compute_success_metrics,
)
from app.ops.pilot.serializers import to_jsonable
from app.portfolio.reconciliation.service import ReconciliationService
from app.services.portfolio_analytics_service import PortfolioAnalyticsService, ReconciliationGateError
from app.services.recommendation_analytics_service import RecommendationAnalyticsService


class PilotCommandCenterService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._pilot_ops = PaperPilotOps(db)
        self._rec_analytics = RecommendationAnalyticsService(db)
        self._port_analytics = PortfolioAnalyticsService(db)
        self._recon = ReconciliationService(db)

    # ── Command center overview ─────────────────────────────────────────────────

    def get_command_center(self, as_of_date: date | None = None) -> dict:
        as_of = as_of_date or date.today()
        alerts = evaluate_alerts(self.db, as_of_date=as_of)
        critical = sum(1 for a in alerts if a.severity == "critical")
        warning = sum(1 for a in alerts if a.severity == "warning")

        pilot_start = as_of - timedelta(days=89)
        success = compute_success_metrics(self.db, pilot_start, as_of)

        return {
            "as_of_date": as_of.isoformat(),
            "pilot_day": (as_of - pilot_start).days + 1,
            "pilot_days_remaining": max(0, 90 - ((as_of - pilot_start).days + 1)),
            "status": "healthy" if critical == 0 else "degraded",
            "alert_summary": {
                "critical": critical,
                "warning": warning,
                "total": len(alerts),
            },
            "success_metrics": success,
            "dashboards": {
                "pilot": "/api/v1/pilot/dashboard/pilot",
                "health": "/api/v1/pilot/dashboard/health",
                "recommendations": "/api/v1/pilot/dashboard/recommendations",
                "committee": "/api/v1/pilot/dashboard/committee",
                "trust": "/api/v1/pilot/dashboard/trust",
                "operational": "/api/v1/pilot/dashboard/operational",
            },
        }

    # ── Dashboards ────────────────────────────────────────────────────────────

    def get_pilot_dashboard(self, as_of_date: date | None = None) -> dict:
        as_of = as_of_date or date.today()
        health = self._pilot_ops.health_snapshot(as_of)
        nav_history = self._nav_trend(as_of, days=30)
        daily_activity = self._daily_activity(as_of)

        return to_jsonable({
            "as_of_date": as_of.isoformat(),
            "portfolio": health,
            "nav_trend_30d": nav_history,
            "today_activity": daily_activity,
            "alerts": evaluate_alerts(self.db, as_of_date=as_of),
        })

    def get_health_dashboard(self, as_of_date: date | None = None) -> dict:
        as_of = as_of_date or date.today()
        health = self._pilot_ops.health_snapshot(as_of)
        recon = self._recon.get_latest()
        healthy, gate_reason = self._recon.is_healthy()

        risk_level = "UNKNOWN"
        try:
            risk = self._port_analytics.get_risk()
            risk_level = risk.risk_level if hasattr(risk, "risk_level") else "MODERATE"
        except (ReconciliationGateError, ValueError):
            pass

        return to_jsonable({
            "as_of_date": as_of.isoformat(),
            "health": health,
            "reconciliation": _recon_detail(recon),
            "analytics_gate_open": healthy,
            "analytics_gate_reason": gate_reason,
            "risk_level": risk_level,
            "alerts": evaluate_alerts(self.db, as_of_date=as_of),
        })

    def get_recommendation_dashboard(
        self,
        *,
        as_of_date: date | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict:
        as_of = as_of_date or date.today()
        window_start = from_date or (as_of - timedelta(days=29))
        window_end = to_date or as_of

        summary = self._rec_analytics.get_summary(
            from_date=window_start, to_date=window_end
        )
        conviction = self._rec_analytics.get_conviction_performance(
            from_date=window_start, to_date=window_end
        )
        regime = self._rec_analytics.get_regime_performance(
            from_date=window_start, to_date=window_end
        )

        as_of, daily_rec = self._resolve_daily_recommendation_counts(as_of, as_of_date)

        return to_jsonable({
            "as_of_date": as_of.isoformat(),
            "window": {"from": window_start.isoformat(), "to": window_end.isoformat()},
            "summary": summary,
            "conviction": conviction,
            "regime": regime,
            "today": daily_rec,
            "exit_performance": self._exit_performance(window_start, window_end),
        })

    def get_committee_dashboard(
        self,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict:
        end = to_date or date.today()
        start = from_date or (end - timedelta(days=29))
        committee = self._rec_analytics.get_committee_performance(
            from_date=start, to_date=end
        )
        return to_jsonable({
            "window": {"from": start.isoformat(), "to": end.isoformat()},
            "committee_effectiveness": committee,
            "note": "Committee output is advisory only — observation, not decision input.",
        })

    def get_trust_dashboard(
        self,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict:
        end = to_date or date.today()
        start = from_date or (end - timedelta(days=29))
        trust = self._rec_analytics.get_trust_metrics(from_date=start, to_date=end)
        trend = self._trust_trend(end, weeks=4)

        return to_jsonable({
            "window": {"from": start.isoformat(), "to": end.isoformat()},
            "trust": trust,
            "trend_weekly": trend,
            "note": "Trust metrics are observation-only — no feedback into conviction or engine.",
        })

    def get_operational_dashboard(self, as_of_date: date | None = None) -> dict:
        as_of = as_of_date or date.today()
        batches = self.db.scalars(
            select(DailyBatchRun)
            .order_by(DailyBatchRun.started_at.desc())
            .limit(10)
        ).all()

        return to_jsonable({
            "as_of_date": as_of.isoformat(),
            "recent_batches": [
                {
                    "run_id": str(b.id),
                    "status": b.status,
                    "target_trading_day": b.target_trading_day.isoformat()
                    if b.target_trading_day
                    else None,
                    "duration_seconds": float(b.duration_seconds) if b.duration_seconds else None,
                    "portfolio_phases": bool(
                        (b.parameter_set or {}).get("phases", {}).get("portfolio")
                    ),
                    "phase_keys": list((b.phase_results or {}).keys()),
                }
                for b in batches
            ],
            "alerts": evaluate_alerts(self.db, as_of_date=as_of),
            "success_metrics_30d": compute_success_metrics(
                self.db, as_of - timedelta(days=29), as_of
            ),
        })

    # ── Alerts & reports ──────────────────────────────────────────────────────

    def get_alerts(self, as_of_date: date | None = None) -> list[dict]:
        return to_jsonable(evaluate_alerts(self.db, as_of_date=as_of_date))

    def get_success_metrics(
        self,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict:
        end = to_date or date.today()
        start = from_date or (end - timedelta(days=89))
        return compute_success_metrics(self.db, start, end)

    def get_report(
        self,
        report_type: str,
        *,
        as_of_date: date | None = None,
        pilot_start: date | None = None,
        pilot_end: date | None = None,
    ) -> dict:
        if report_type == "daily":
            report = build_daily_report(self.db, as_of_date)
        elif report_type == "weekly":
            report = build_weekly_report(self.db, as_of_date)
        elif report_type == "monthly":
            report = build_monthly_report(self.db, as_of_date)
        elif report_type == "final":
            end = pilot_end or date.today()
            start = pilot_start or (end - timedelta(days=89))
            report = build_final_report(self.db, pilot_start=start, pilot_end=end)
        else:
            raise ValueError(f"Unknown report type: {report_type}")
        return to_jsonable(report)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _nav_trend(self, as_of: date, *, days: int) -> list[dict]:
        start = as_of - timedelta(days=days)
        rows = self.db.scalars(
            select(PortfolioNavHistory)
            .where(
                PortfolioNavHistory.as_of_date >= start,
                PortfolioNavHistory.as_of_date <= as_of,
            )
            .order_by(PortfolioNavHistory.as_of_date)
        ).all()
        return [
            {
                "as_of_date": r.as_of_date.isoformat(),
                "total_equity": float(r.total_equity),
                "day_return_pct": float(r.day_return_pct) if r.day_return_pct else None,
                "alpha_pct": float(r.alpha_pct) if r.alpha_pct else None,
            }
            for r in rows
        ]

    def _daily_activity(self, as_of: date) -> dict:
        approvals = (
            self.db.scalar(
                select(func.count(RecommendationApproval.id)).where(
                    func.date(RecommendationApproval.decided_at) == as_of
                )
            )
            or 0
        )
        trades = (
            self.db.scalar(
                select(func.count(PaperTrade.id)).where(
                    func.date(PaperTrade.filled_at) == as_of
                )
            )
            or 0
        )
        rec_runs = (
            self.db.scalar(
                select(func.count(RecommendationRun.id)).where(
                    RecommendationRun.as_of_date == as_of
                )
            )
            or 0
        )
        return {
            "recommendation_runs": int(rec_runs),
            "approvals": int(approvals),
            "paper_trades": int(trades),
        }

    def _resolve_daily_recommendation_counts(
        self, as_of: date, as_of_date: date | None
    ) -> tuple[date, dict]:
        """Return counts for as_of; fall back to latest run day when today has no runs."""
        daily_rec = self._daily_recommendation_counts(as_of)
        if daily_rec["runs"] == 0 and as_of_date is None:
            latest = self.db.scalar(select(func.max(RecommendationRun.as_of_date)))
            if latest is not None and latest != as_of:
                as_of = latest
                daily_rec = self._daily_recommendation_counts(as_of)
        return as_of, daily_rec

    def _daily_recommendation_counts(self, as_of: date) -> dict:
        runs = self.db.scalars(
            select(RecommendationRun).where(RecommendationRun.as_of_date == as_of)
        ).all()
        actions: dict[str, int] = {}
        for run in runs:
            results = self.db.scalars(
                select(RecommendationResult).where(
                    RecommendationResult.recommendation_run_id == run.id
                )
            ).all()
            for r in results:
                actions[r.action] = actions.get(r.action, 0) + 1
        buy_count = actions.get("BUY", 0)
        watch_count = actions.get("WATCH", 0)
        exit_count = actions.get("EXIT_APPROVED", 0)
        hold_count = actions.get("HOLD", 0)
        reject_count = actions.get("REJECT", 0)
        total = sum(actions.values())
        return {
            "runs": len(runs),
            "actions": actions,
            "buy_count": buy_count,
            "watch_count": watch_count,
            "exit_count": exit_count,
            "hold_count": hold_count,
            "reject_count": reject_count,
            "total": total,
        }

    def _exit_performance(self, start: date, end: date) -> dict:
        closed = self.db.scalars(
            select(RecommendationOutcome).where(
                RecommendationOutcome.exit_date.isnot(None),
                RecommendationOutcome.exit_date >= start,
                RecommendationOutcome.exit_date <= end,
            )
        ).all()
        if not closed:
            return {"closed_exits": 0}
        pnls = [float(o.pnl_pct) for o in closed if o.pnl_pct is not None]
        return {
            "closed_exits": len(closed),
            "avg_pnl_pct": round(sum(pnls) / len(pnls), 4) if pnls else None,
            "wins": sum(1 for o in closed if o.outcome_status == "WIN"),
            "losses": sum(1 for o in closed if o.outcome_status == "LOSS"),
        }

    def _trust_trend(self, end: date, *, weeks: int) -> list[dict]:
        trend = []
        for w in range(weeks):
            w_end = end - timedelta(days=w * 7)
            w_start = w_end - timedelta(days=6)
            try:
                trust = self._rec_analytics.get_trust_metrics(
                    from_date=w_start, to_date=w_end
                )
                trend.append({
                    "week_ending": w_end.isoformat(),
                    "overall_trust_score": trust.overall_trust_score,
                    "calibration_ok": trust.calibration.is_calibrated
                    if hasattr(trust, "calibration")
                    else None,
                    "stability_score": trust.stability.stability_score
                    if hasattr(trust, "stability")
                    else None,
                    "reliability_rate": trust.reliability.reliability_rate
                    if hasattr(trust, "reliability")
                    else None,
                })
            except Exception:
                trend.append({"week_ending": w_end.isoformat(), "error": "insufficient_data"})
        return list(reversed(trend))


def _recon_detail(recon) -> dict | None:
    if recon is None:
        return None
    return {
        "as_of_date": recon.as_of_date.isoformat(),
        "status": recon.status,
        "computed_nav": float(recon.computed_nav),
        "reported_nav": float(recon.reported_nav),
        "discrepancy_pct": float(recon.discrepancy_pct),
        "checks": recon.checks or {},
    }
