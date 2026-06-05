"""Portfolio Engine REST API (M2)."""
from __future__ import annotations

import dataclasses
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_db
from app.services.paper_trade_service import PaperTradeService
from app.services.portfolio_service import PortfolioService
from app.services.portfolio_analytics_service import (
    PortfolioAnalyticsService,
    ReconciliationGateError,
)
from app.services.portfolio_nav_service import PortfolioNavService
from app.portfolio.reconciliation.service import ReconciliationService
from app.portfolio.exit_monitor.service import ExitMonitorService

router = APIRouter()


def _svc(db=Depends(get_db)) -> PortfolioService:
    return PortfolioService(db)


def _pt_svc(db=Depends(get_db)) -> PaperTradeService:
    return PaperTradeService(db)


def _an_svc(db=Depends(get_db)) -> PortfolioAnalyticsService:
    return PortfolioAnalyticsService(db)


def _recon_svc(db=Depends(get_db)) -> ReconciliationService:
    return ReconciliationService(db)


def _exit_svc(db=Depends(get_db)) -> ExitMonitorService:
    return ExitMonitorService(db)


def _nav_svc(db=Depends(get_db)) -> PortfolioNavService:
    return PortfolioNavService(db)


def _dc(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _dc(v) for k, v in dataclasses.asdict(obj).items()}
    return obj


# ── Schemas ───────────────────────────────────────────────────────────────────

class PortfolioConfigRequest(BaseModel):
    total_equity: float = Field(..., gt=0, description="Total portfolio equity in INR")
    deploy_pct: float = Field(default=0.85, ge=0.1, le=1.0)
    cash_floor_pct: float = Field(default=0.15, ge=0.05, le=0.5)
    reserve_pct: float = Field(default=0.02, ge=0.0, le=0.1)
    notes: str | None = None


class EntryRequest(BaseModel):
    recommendation_result_id: UUID
    as_of_date: date | None = None
    idempotency_key: str | None = None


class ExitRequest(BaseModel):
    recommendation_result_id: UUID
    as_of_date: date | None = None
    idempotency_key: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/summary")
def get_summary(
    as_of_date: date | None = None,
    svc: PortfolioService = Depends(_svc),
) -> Any:
    """NAV, cash, deployable capital, regime slots."""
    try:
        return _dc(svc.get_summary(as_of_date))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/positions")
def get_positions(svc: PortfolioService = Depends(_svc)) -> list[dict]:
    """Current open positions with P&L."""
    positions = svc.get_positions()
    out = []
    for p in positions:
        stock = p.stock
        out.append({
            "id": str(p.id),
            "symbol": stock.symbol if stock else None,
            "quantity": float(p.quantity),
            "avg_cost": float(p.avg_cost),
            "entry_price": float(p.entry_price) if p.entry_price else None,
            "entry_date": p.entry_date.isoformat() if p.entry_date else None,
            "market_value": float(p.market_value) if p.market_value else None,
            "unrealized_pnl": float(p.unrealized_pnl) if p.unrealized_pnl else None,
            "weight_pct": float(p.weight_pct) if p.weight_pct else None,
            "conviction_band": p.conviction_band,
            "strategy_name": p.strategy_name,
            "sector": p.sector,
            "position_status": p.position_status,
        })
    return out


@router.get("/limits")
def get_limits(
    as_of_date: date | None = None,
    svc: PortfolioService = Depends(_svc),
) -> Any:
    """Regime-based slot limits and headroom."""
    try:
        return _dc(svc.get_limits(as_of_date))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/allocation")
def compute_allocation(
    conviction_band: str,
    last_price: float,
    sector: str | None = None,
    svc: PortfolioService = Depends(_svc),
) -> Any:
    """Calculate position size for a given conviction band and price."""
    try:
        return _dc(svc.compute_allocation(conviction_band, last_price, sector=sector))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/config", status_code=201)
def upsert_config(
    payload: PortfolioConfigRequest,
    svc: PortfolioService = Depends(_svc),
) -> dict:
    """Set portfolio equity and allocation parameters."""
    cfg = svc.upsert_config(
        total_equity=payload.total_equity,
        deploy_pct=payload.deploy_pct,
        cash_floor_pct=payload.cash_floor_pct,
        reserve_pct=payload.reserve_pct,
        notes=payload.notes,
    )
    svc.db.commit()
    return {
        "id": str(cfg.id),
        "total_equity": float(cfg.total_equity),
        "deploy_pct": float(cfg.deploy_pct),
        "cash_floor_pct": float(cfg.cash_floor_pct),
        "is_active": cfg.is_active,
    }


@router.post("/recompute")
def recompute(svc: PortfolioService = Depends(_svc)) -> dict:
    """Mark-to-market all positions and recompute weights."""
    result = svc.recompute()
    svc.db.commit()
    return result


@router.post("/trades/entry", status_code=201)
def execute_entry(
    payload: EntryRequest,
    svc: PaperTradeService = Depends(_pt_svc),
) -> dict:
    """Simulate BUY fill for an approved recommendation."""
    try:
        trade = svc.execute_entry(
            recommendation_result_id=payload.recommendation_result_id,
            as_of_date=payload.as_of_date,
            idempotency_key=payload.idempotency_key,
        )
        svc.db.commit()
        return {
            "trade_id": str(trade.id),
            "status": trade.status,
            "fill_price": float(trade.fill_price),
            "quantity": float(trade.fill_quantity),
            "side": trade.side,
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/trades/exit", status_code=201)
def execute_exit(
    payload: ExitRequest,
    svc: PaperTradeService = Depends(_pt_svc),
) -> dict:
    """Simulate SELL fill for a confirmed EXIT_APPROVED."""
    try:
        trade = svc.execute_exit(
            recommendation_result_id=payload.recommendation_result_id,
            as_of_date=payload.as_of_date,
            idempotency_key=payload.idempotency_key,
        )
        svc.db.commit()
        return {
            "trade_id": str(trade.id),
            "status": trade.status,
            "fill_price": float(trade.fill_price),
            "quantity": float(trade.fill_quantity),
            "side": trade.side,
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ── M2.2 Analytics endpoints ──────────────────────────────────────────────────

@router.get("/performance")
def get_performance(
    from_date: date | None = None,
    to_date: date | None = None,
    svc: PortfolioAnalyticsService = Depends(_an_svc),
) -> Any:
    """Return, alpha, CAGR, volatility, Sharpe, Sortino, max drawdown, turnover."""
    try:
        return _dc(svc.get_performance(from_date, to_date))
    except ReconciliationGateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/risk")
def get_risk(svc: PortfolioAnalyticsService = Depends(_an_svc)) -> Any:
    """Exposure, concentration, sector, drawdown risk + alerts."""
    try:
        return _dc(svc.get_risk())
    except ReconciliationGateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/attribution")
def get_attribution(
    from_date: date | None = None,
    to_date: date | None = None,
    svc: PortfolioAnalyticsService = Depends(_an_svc),
) -> Any:
    """Where returns came from — by strategy/conviction/regime/sector/duration/committee."""
    try:
        return _dc(svc.get_attribution(from_date, to_date))
    except ReconciliationGateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/benchmark")
def get_benchmark(
    benchmark: str = "nifty500",
    from_date: date | None = None,
    to_date: date | None = None,
    svc: PortfolioAnalyticsService = Depends(_an_svc),
) -> Any:
    """Compare portfolio vs NIFTY 500 / NIFTY 50 — alpha, tracking error, IR."""
    try:
        return _dc(svc.get_benchmark(benchmark, from_date, to_date))
    except ReconciliationGateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/nav-history")
def get_nav_history(
    from_date: date | None = None,
    to_date: date | None = None,
    svc: PortfolioAnalyticsService = Depends(_an_svc),
) -> list[dict]:
    """Daily NAV time series."""
    rows = svc.get_nav_history(from_date, to_date)
    return [
        {
            "as_of_date": r.as_of_date.isoformat(),
            "total_equity": float(r.total_equity),
            "cash_balance": float(r.cash_balance),
            "market_value": float(r.market_value),
            "unrealized_pnl": float(r.unrealized_pnl),
            "open_positions": r.open_positions,
            "cash_pct": float(r.cash_pct),
            "day_return_pct": float(r.day_return_pct) if r.day_return_pct is not None else None,
            "alpha_pct": float(r.alpha_pct) if r.alpha_pct is not None else None,
            "regime_label": r.regime_label,
        }
        for r in rows
    ]


@router.get("/cash-ledger")
def get_cash_ledger(
    from_date: date | None = None,
    to_date: date | None = None,
    db=Depends(get_db),
) -> list[dict]:
    """Append-only cash movement log."""
    from sqlalchemy import select
    from app.models.portfolio_analytics import CashLedger
    q = select(CashLedger)
    if from_date:
        q = q.where(CashLedger.as_of_date >= from_date)
    if to_date:
        q = q.where(CashLedger.as_of_date <= to_date)
    q = q.order_by(CashLedger.as_of_date, CashLedger.created_at)
    rows = list(db.scalars(q).all())
    return [
        {
            "as_of_date": r.as_of_date.isoformat(),
            "entry_type": r.entry_type,
            "amount": float(r.amount),
            "balance_after": float(r.balance_after),
            "reference_type": r.reference_type,
            "description": r.description,
        }
        for r in rows
    ]


@router.get("/reconciliation")
def get_reconciliation(svc: ReconciliationService = Depends(_recon_svc)) -> dict:
    """Latest reconciliation report."""
    report = svc.get_latest()
    if report is None:
        raise HTTPException(status_code=404, detail="No reconciliation report yet. Run POST /portfolio/reconcile.")
    return {
        "as_of_date": report.as_of_date.isoformat(),
        "status": report.status,
        "computed_nav": float(report.computed_nav),
        "reported_nav": float(report.reported_nav),
        "discrepancy": float(report.discrepancy),
        "discrepancy_pct": float(report.discrepancy_pct),
        "cash_from_ledger": float(report.cash_from_ledger),
        "market_value_from_positions": float(report.market_value_from_positions),
        "checks": report.checks,
        "warnings": report.warnings,
        "failures": report.failures,
    }


@router.post("/reconcile", status_code=201)
def run_reconciliation(
    as_of_date: date | None = None,
    svc: ReconciliationService = Depends(_recon_svc),
) -> dict:
    """Run reconciliation for as_of_date (default today)."""
    report = svc.run(as_of_date)
    svc.db.commit()
    return {"as_of_date": report.as_of_date.isoformat(), "status": report.status,
            "discrepancy_pct": float(report.discrepancy_pct)}


@router.get("/exits")
def get_exits(
    as_of_date: date | None = None,
    svc: ExitMonitorService = Depends(_exit_svc),
) -> list[dict]:
    """Pending exit recommendations awaiting human confirmation."""
    recs = svc.get_pending(as_of_date)
    out = []
    for r in recs:
        stock = r.position.stock if r.position else None
        out.append({
            "id": str(r.id),
            "symbol": stock.symbol if stock else None,
            "status": r.status,
            "urgency": r.urgency,
            "triggers": r.triggers,
            "trigger_details": r.trigger_details,
            "current_rank": r.current_rank,
            "days_held": r.days_held,
            "unrealized_pnl_pct": float(r.unrealized_pnl_pct) if r.unrealized_pnl_pct is not None else None,
            "as_of_date": r.as_of_date.isoformat(),
        })
    return out


@router.post("/exits/run", status_code=201)
def run_exit_monitor(
    as_of_date: date | None = None,
    svc: ExitMonitorService = Depends(_exit_svc),
) -> dict:
    """Evaluate ACTIVE positions and generate exit recommendations."""
    recs = svc.run(as_of_date)
    svc.db.commit()
    return {"generated": len(recs), "exit_recommendation_ids": [str(r.id) for r in recs]}


@router.post("/exits/{exit_id}/confirm")
def confirm_exit(exit_id: UUID, svc: ExitMonitorService = Depends(_exit_svc)) -> dict:
    """Human confirms an exit recommendation (does not execute trade)."""
    try:
        rec = svc.confirm(exit_id)
        svc.db.commit()
        return {"id": str(rec.id), "status": rec.status}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/exits/{exit_id}/reject")
def reject_exit(
    exit_id: UUID,
    reason: str | None = None,
    svc: ExitMonitorService = Depends(_exit_svc),
) -> dict:
    """Human rejects an exit recommendation."""
    try:
        rec = svc.reject(exit_id, reason)
        svc.db.commit()
        return {"id": str(rec.id), "status": rec.status}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/nav-snapshot", status_code=201)
def take_nav_snapshot(
    as_of_date: date | None = None,
    svc: PortfolioNavService = Depends(_nav_svc),
) -> dict:
    """Write the daily NAV history snapshot."""
    row = svc.snapshot(as_of_date)
    svc.db.commit()
    return {
        "as_of_date": row.as_of_date.isoformat(),
        "total_equity": float(row.total_equity),
        "cash_balance": float(row.cash_balance),
        "market_value": float(row.market_value),
        "open_positions": row.open_positions,
    }


@router.get("/dashboard")
def get_dashboard(db=Depends(get_db)) -> Any:
    """Aggregated dashboard model (WS11) — NAV, alpha, cash, exits, risk, contributors."""
    an = PortfolioAnalyticsService(db)
    recon = ReconciliationService(db)
    exits = ExitMonitorService(db)
    port = PortfolioService(db)

    recon_report = recon.get_latest()
    recon_status = recon_report.status if recon_report else None

    nav_rows = an.get_nav_history(None, None)
    nav = float(nav_rows[-1].total_equity) if nav_rows else None
    today_change = float(nav_rows[-1].day_return_pct) if nav_rows and nav_rows[-1].day_return_pct is not None else None
    alpha = float(nav_rows[-1].alpha_pct) if nav_rows and nav_rows[-1].alpha_pct is not None else None

    try:
        summary = port.get_summary()
        cash_pct = summary.cash_pct * 100
        active = summary.active_positions
    except Exception:
        cash_pct = None
        active = 0

    pending_exits = len(exits.get_pending())

    # Risk + contributors (gated)
    risk_level = "UNKNOWN"
    alerts: list = []
    top_contributors: list = []
    worst_contributors: list = []
    try:
        risk = an.get_risk()
        risk_level = risk.risk_level
        alerts = [{"code": a.code, "level": a.level, "message": a.message} for a in risk.alerts]
        attribution = an.get_attribution()
        # contributors by symbol via outcomes
        symbol_rows = sorted(
            [b for b in attribution.by_sector],  # placeholder; real symbol-level below
            key=lambda b: (b.contribution_pct or 0), reverse=True,
        )
    except ReconciliationGateError:
        pass

    return {
        "nav": nav,
        "today_change_pct": today_change,
        "alpha_pct": alpha,
        "cash_pct": round(cash_pct, 2) if cash_pct is not None else None,
        "active_positions": active,
        "pending_exits": pending_exits,
        "risk_level": risk_level,
        "risk_alerts": alerts,
        "reconciliation_status": recon_status,
    }
