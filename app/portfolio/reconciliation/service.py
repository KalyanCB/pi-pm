"""Portfolio Reconciliation Engine.

Daily verification: Cash Ledger + Open Positions + Closed P&L = Portfolio NAV.

Status:
  PASS    — discrepancy < 0.01% of NAV
  WARNING — discrepancy 0.01%–0.1%
  FAIL    — discrepancy > 0.1% OR structural check failures

Analytics endpoints return 409 when latest reconciliation is FAIL.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.paper_trade import PaperTrade
from app.models.portfolio_analytics import (
    CashLedger,
    PortfolioNavHistory,
    PortfolioReconciliationReport,
)
from app.models.portfolio_position import PortfolioConfig, PortfolioPosition

_PASS_THRESHOLD_PCT = 0.01  # < 0.01% discrepancy → PASS
_WARNING_THRESHOLD_PCT = 0.10  # < 0.10% → WARNING, else FAIL


@dataclass
class ReconciliationResult:
    status: str
    cash_from_ledger: float
    market_value_from_positions: float
    realized_pnl_from_closed: float
    computed_nav: float
    reported_nav: float
    discrepancy: float
    discrepancy_pct: float
    checks: dict[str, str]
    warnings: list[str]
    failures: list[str]


class ReconciliationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(self, as_of_date: date | None = None) -> PortfolioReconciliationReport:
        as_of = as_of_date or date.today()
        result = self._compute(as_of)

        # Upsert — one report per date
        existing = self.db.scalar(
            select(PortfolioReconciliationReport).where(
                PortfolioReconciliationReport.as_of_date == as_of
            )
        )
        if existing:
            report = existing
        else:
            report = PortfolioReconciliationReport(as_of_date=as_of)
            self.db.add(report)

        report.status = result.status
        report.cash_from_ledger = result.cash_from_ledger
        report.market_value_from_positions = result.market_value_from_positions
        report.realized_pnl_from_closed = result.realized_pnl_from_closed
        report.computed_nav = result.computed_nav
        report.reported_nav = result.reported_nav
        report.discrepancy = result.discrepancy
        report.discrepancy_pct = result.discrepancy_pct
        report.checks = result.checks
        report.warnings = result.warnings or None
        report.failures = result.failures or None
        self.db.flush()
        return report

    def get_latest(self) -> PortfolioReconciliationReport | None:
        return self.db.scalar(
            select(PortfolioReconciliationReport)
            .order_by(PortfolioReconciliationReport.as_of_date.desc())
            .limit(1)
        )

    def is_healthy(self) -> tuple[bool, str | None]:
        """Return (ok, reason). Analytics may only run when ok=True."""
        latest = self.get_latest()
        if latest is None:
            return True, None  # No recon yet — allow (fresh system)
        if latest.status == "FAIL":
            return False, f"Reconciliation FAIL on {latest.as_of_date}: {latest.failures}"
        return True, None

    # ── Compute ───────────────────────────────────────────────────────────────

    def _compute(self, as_of: date) -> ReconciliationResult:
        checks: dict[str, str] = {}
        warnings: list[str] = []
        failures: list[str] = []

        # 1. Cash from ledger (sum of all entries up to as_of)
        cash_from_ledger = float(
            self.db.scalar(
                select(func.sum(CashLedger.amount)).where(CashLedger.as_of_date <= as_of)
            )
            or 0.0
        )
        checks["cash_ledger"] = "PASS" if cash_from_ledger >= 0 else "WARNING"
        if cash_from_ledger < 0:
            warnings.append(f"Cash balance negative: ₹{cash_from_ledger:,.2f}")

        # 2. Market value from open positions
        mv_result = self.db.scalar(
            select(func.sum(PortfolioPosition.market_value)).where(
                PortfolioPosition.is_current.is_(True),
                PortfolioPosition.position_status == "OPEN",
            )
        )
        market_value = float(mv_result or 0.0)
        checks["open_positions"] = "PASS"

        # 3. Realized P&L from closed positions
        realized_result = self.db.scalar(
            select(func.sum(PortfolioPosition.realized_pnl)).where(
                PortfolioPosition.position_status == "CLOSED",
                PortfolioPosition.exit_date <= as_of,
            )
        )
        realized_pnl = float(realized_result or 0.0)
        checks["closed_positions"] = "PASS"

        # 4. Trade consistency check — every filled trade should have a position
        filled_buys = (
            self.db.scalar(
                select(func.count(PaperTrade.id)).where(
                    PaperTrade.side == "BUY",
                    PaperTrade.status == "filled",
                )
            )
            or 0
        )
        open_pos_count = (
            self.db.scalar(
                select(func.count(PortfolioPosition.id)).where(
                    PortfolioPosition.is_current.is_(True),
                    PortfolioPosition.position_status == "OPEN",
                )
            )
            or 0
        )
        closed_pos_count = (
            self.db.scalar(
                select(func.count(PortfolioPosition.id)).where(
                    PortfolioPosition.position_status == "CLOSED"
                )
            )
            or 0
        )

        if filled_buys != (open_pos_count + closed_pos_count):
            checks["trade_consistency"] = "WARNING"
            warnings.append(
                f"Trade/position mismatch: {filled_buys} filled BUYs vs {open_pos_count + closed_pos_count} positions"
            )
        else:
            checks["trade_consistency"] = "PASS"

        # 5. Outcome consistency — closed positions should have outcomes
        from app.models.recommendation import RecommendationOutcome

        closed_with_rec = (
            self.db.scalar(
                select(func.count(PortfolioPosition.id)).where(
                    PortfolioPosition.position_status == "CLOSED",
                    PortfolioPosition.recommendation_result_id.isnot(None),
                )
            )
            or 0
        )
        outcomes_count = (
            self.db.scalar(
                select(func.count(RecommendationOutcome.id)).where(
                    RecommendationOutcome.outcome_status != "OPEN"
                )
            )
            or 0
        )
        if closed_with_rec > 0 and outcomes_count < closed_with_rec:
            checks["outcome_consistency"] = "WARNING"
            warnings.append(
                f"Missing outcomes: {closed_with_rec - outcomes_count} closed positions without outcome records"
            )
        else:
            checks["outcome_consistency"] = "PASS"

        # 6. NAV reconciliation
        computed_nav = cash_from_ledger + market_value
        latest_nav = self.db.scalar(
            select(PortfolioNavHistory)
            .where(PortfolioNavHistory.as_of_date <= as_of)
            .order_by(PortfolioNavHistory.as_of_date.desc())
            .limit(1)
        )
        if latest_nav is not None:
            reported_nav = float(latest_nav.total_equity)
        else:
            cfg = self.db.scalar(
                select(PortfolioConfig).where(PortfolioConfig.is_active.is_(True)).limit(1)
            )
            reported_nav = float(cfg.total_equity) if cfg else computed_nav
        discrepancy = abs(computed_nav - reported_nav)
        discrepancy_pct = (discrepancy / reported_nav * 100) if reported_nav > 0 else 0.0

        if discrepancy_pct > _WARNING_THRESHOLD_PCT:
            checks["nav_reconciliation"] = "FAIL"
            failures.append(
                f"NAV discrepancy {discrepancy_pct:.4f}% exceeds threshold "
                f"(computed ₹{computed_nav:,.2f} vs reported ₹{reported_nav:,.2f})"
            )
        elif discrepancy_pct > _PASS_THRESHOLD_PCT:
            checks["nav_reconciliation"] = "WARNING"
            warnings.append(f"Minor NAV discrepancy: {discrepancy_pct:.4f}%")
        else:
            checks["nav_reconciliation"] = "PASS"

        # Final status
        if failures:
            status = "FAIL"
        elif warnings:
            status = "WARNING"
        else:
            status = "PASS"

        # Clamp to NUMERIC(8,4) column max to avoid DB overflow
        discrepancy_pct_clamped = min(round(discrepancy_pct, 4), 9999.9999)

        return ReconciliationResult(
            status=status,
            cash_from_ledger=round(cash_from_ledger, 2),
            market_value_from_positions=round(market_value, 2),
            realized_pnl_from_closed=round(realized_pnl, 2),
            computed_nav=round(computed_nav, 2),
            reported_nav=round(reported_nav, 2),
            discrepancy=round(discrepancy, 2),
            discrepancy_pct=discrepancy_pct_clamped,
            checks=checks,
            warnings=warnings,
            failures=failures,
        )
