"""Paper-trading pilot orchestration for daily batch.

Orchestrates portfolio ops only — does not modify ranking, validation,
recommendation generation, conviction, or committee logic.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import RecommendationAction
from app.models.portfolio_analytics import ExitRecommendation, PortfolioNavHistory
from app.models.portfolio_position import PortfolioPosition
from app.models.recommendation import RecommendationResult, RecommendationRun
from app.portfolio.exit_monitor.service import ExitMonitorService
from app.portfolio.reconciliation.service import ReconciliationService
from app.services.paper_trade_service import PaperTradeService
from app.services.portfolio_nav_service import PortfolioNavService
from app.services.portfolio_service import PortfolioService
from app.services.recommendation_service import RecommendationService


class PaperPilotOps:
    def __init__(
        self,
        db: Session,
        *,
        portfolio_service: PortfolioService | None = None,
        nav_service: PortfolioNavService | None = None,
        reconciliation_service: ReconciliationService | None = None,
        exit_monitor: ExitMonitorService | None = None,
        paper_trade_service: PaperTradeService | None = None,
        recommendation_service: RecommendationService | None = None,
    ) -> None:
        self.db = db
        self.portfolio_service = portfolio_service or PortfolioService(db)
        self.nav_service = nav_service or PortfolioNavService(db)
        self.reconciliation_service = reconciliation_service or ReconciliationService(db)
        self.exit_monitor = exit_monitor or ExitMonitorService(db)
        self.paper_trade_service = paper_trade_service or PaperTradeService(db)
        self.recommendation_service = recommendation_service or RecommendationService(db)

    def run(
        self,
        as_of_date: date,
        *,
        recompute: bool = True,
        exit_monitor: bool = True,
        paper_trading: bool = True,
        nav_snapshot: bool = True,
        reconcile: bool = True,
        pilot_auto_approve: bool = False,
        pilot_auto_execute: bool = False,
    ) -> dict:
        results: dict = {}

        if recompute:
            results["recompute"] = self.portfolio_service.recompute()

        if exit_monitor:
            exit_recs = self.exit_monitor.run(as_of_date)
            results["exit_monitor"] = {
                "candidates": len(exit_recs),
                "ids": [str(r.id) for r in exit_recs],
            }

        if paper_trading and pilot_auto_execute:
            results["paper_trading"] = self._execute_pilot_trades(
                as_of_date,
                pilot_auto_approve=pilot_auto_approve,
            )

        if nav_snapshot:
            nav = self.nav_service.snapshot(as_of_date)
            results["nav_snapshot"] = {
                "nav_id": str(nav.id),
                "total_equity": float(nav.total_equity),
                "cash_pct": float(nav.cash_pct),
                "open_positions": nav.open_positions,
            }

        if reconcile:
            report = self.reconciliation_service.run(as_of_date)
            results["reconcile"] = {
                "report_id": str(report.id),
                "status": report.status,
                "discrepancy_pct": float(report.discrepancy_pct),
            }

        return results

    def _execute_pilot_trades(
        self,
        as_of_date: date,
        *,
        pilot_auto_approve: bool,
    ) -> dict:
        entries: list[str] = []
        exits: list[str] = []
        skipped: list[dict] = []

        limits = self.portfolio_service.get_limits(as_of_date)

        # Exits first — EXIT_APPROVED with open position
        exit_candidates = self.db.scalars(
            select(RecommendationResult).where(
                RecommendationResult.action == RecommendationAction.EXIT_APPROVED.value,
            )
        ).all()
        for rec in exit_candidates:
            pos = self.db.scalar(
                select(PortfolioPosition).where(
                    PortfolioPosition.stock_id == rec.stock_id,
                    PortfolioPosition.is_current.is_(True),
                    PortfolioPosition.position_status == "OPEN",
                )
            )
            if pos is None:
                continue
            try:
                trade = self.paper_trade_service.execute_exit(
                    recommendation_result_id=rec.id,
                    as_of_date=as_of_date,
                )
                exits.append(str(trade.id))
            except Exception as exc:
                skipped.append({"recommendation_id": str(rec.id), "action": "exit", "error": str(exc)})

        # Entries — BUY recommendations
        rec_runs = self.db.scalars(
            select(RecommendationRun).where(
                RecommendationRun.as_of_date == as_of_date,
                RecommendationRun.status == "completed",
            )
        ).all()
        buys_today = 0
        for run in rec_runs:
            buy_results = self.db.scalars(
                select(RecommendationResult).where(
                    RecommendationResult.recommendation_run_id == run.id,
                    RecommendationResult.action == RecommendationAction.BUY.value,
                )
            ).all()
            for rec in sorted(buy_results, key=lambda r: r.conviction_score, reverse=True):
                if rec.portfolio_position_id:
                    continue
                open_pos = self.db.scalar(
                    select(PortfolioPosition).where(
                        PortfolioPosition.stock_id == rec.stock_id,
                        PortfolioPosition.is_current.is_(True),
                        PortfolioPosition.position_status == "OPEN",
                    )
                )
                if open_pos:
                    continue

                if pilot_auto_approve and rec.lifecycle_state != "APPROVED":
                    try:
                        self.recommendation_service.approve(
                            rec.id,
                            approval_type="PILOT_AUTO",
                            decision="APPROVED",
                            actor_id="paper_pilot",
                            note="Auto-approved for 90-day paper pilot",
                            idempotency_key=f"pilot-approve:{rec.id}",
                        )
                    except Exception as exc:
                        skipped.append({
                            "recommendation_id": str(rec.id),
                            "action": "approve",
                            "error": str(exc),
                        })
                        continue

                if rec.lifecycle_state not in ("APPROVED", "ACTIVE"):
                    skipped.append({
                        "recommendation_id": str(rec.id),
                        "action": "entry",
                        "reason": f"lifecycle={rec.lifecycle_state}",
                    })
                    continue

                if not limits.can_add_position or buys_today >= limits.max_buy_per_day:
                    skipped.append({
                        "recommendation_id": str(rec.id),
                        "action": "entry",
                        "reason": limits.block_reason or "slot_limit",
                    })
                    continue

                try:
                    trade = self.paper_trade_service.execute_entry(
                        recommendation_result_id=rec.id,
                        as_of_date=as_of_date,
                    )
                    entries.append(str(trade.id))
                    buys_today += 1
                except Exception as exc:
                    skipped.append({
                        "recommendation_id": str(rec.id),
                        "action": "entry",
                        "error": str(exc),
                    })

        return {
            "entries": entries,
            "exits": exits,
            "skipped": skipped,
            "entries_count": len(entries),
            "exits_count": len(exits),
        }

    def health_snapshot(self, as_of_date: date | None = None) -> dict:
        """Portfolio health for pilot dashboard — read-only."""
        as_of = as_of_date or date.today()
        limits = self.portfolio_service.get_limits(as_of)
        summary = self.portfolio_service.get_summary()
        nav = self.db.scalar(
            select(PortfolioNavHistory)
            .where(PortfolioNavHistory.as_of_date <= as_of)
            .order_by(PortfolioNavHistory.as_of_date.desc())
            .limit(1)
        )
        recon = self.reconciliation_service.get_latest()
        pending_exits = int(
            self.db.scalar(
                select(func.count(ExitRecommendation.id)).where(
                    ExitRecommendation.status == "PENDING"
                )
            )
            or 0
        )
        return {
            "as_of_date": as_of.isoformat(),
            "summary": summary,
            "limits": {
                "can_add_position": limits.can_add_position,
                "slots_available": limits.slots_available,
                "block_reason": limits.block_reason,
            },
            "nav": {
                "total_equity": float(nav.total_equity) if nav else None,
                "day_return_pct": float(nav.day_return_pct) if nav and nav.day_return_pct else None,
                "alpha_pct": float(nav.alpha_pct) if nav and nav.alpha_pct else None,
            },
            "reconciliation_status": recon.status if recon else None,
            "pending_exit_recommendations": pending_exits,
        }
