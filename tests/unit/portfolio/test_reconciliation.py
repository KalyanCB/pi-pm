"""Reconciliation engine tests — AC-PE-05, AC-PE-12."""
from datetime import date

import pytest

from app.models.portfolio_position import PortfolioConfig, PortfolioPosition
from app.models.portfolio_analytics import CashLedger
from app.portfolio.reconciliation.service import ReconciliationService


def _seed_config(db, equity=1_000_000.0):
    cfg = PortfolioConfig(
        is_active=True, total_equity=equity, deploy_pct=0.85,
        cash_floor_pct=0.15, reserve_pct=0.02, regime_slots={},
        single_name_cap_pct=0.18, sector_cap_pct=0.30,
        slippage_bps=5.0, fee_per_leg=20.0,
    )
    db.add(cfg)
    db.flush()
    return cfg


def _cash(db, amount, balance_after, as_of, entry_type="INITIAL_CAPITAL"):
    db.add(CashLedger(
        entry_type=entry_type, amount=amount, balance_after=balance_after,
        as_of_date=as_of,
    ))
    db.flush()


def test_reconciliation_pass_clean(db_session):
    """AC-PE-05: NAV reconciles when cash + positions = equity."""
    _seed_config(db_session, equity=1_000_000.0)
    # All cash, no positions → cash 1M = NAV 1M = equity 1M
    _cash(db_session, 1_000_000.0, 1_000_000.0, date(2026, 6, 5))

    svc = ReconciliationService(db_session)
    report = svc.run(date(2026, 6, 5))
    assert report.status == "PASS"
    assert float(report.computed_nav) == pytest.approx(1_000_000.0)
    assert float(report.discrepancy_pct) < 0.01


def test_reconciliation_with_position(db_session):
    _seed_config(db_session, equity=1_000_000.0)
    # 800K cash + 200K position = 1M
    _cash(db_session, 1_000_000.0, 1_000_000.0, date(2026, 6, 1))
    _cash(db_session, -200_000.0, 800_000.0, date(2026, 6, 2), entry_type="TRADE_BUY")

    from app.models.stock import Stock
    stock = Stock(symbol="TESTCO", name="Test Co")
    db_session.add(stock)
    db_session.flush()

    from datetime import datetime, UTC
    pos = PortfolioPosition(
        stock_id=stock.id, quantity=100, avg_cost=2000, market_value=200_000,
        as_of=datetime.now(UTC), is_current=True, position_status="OPEN",
    )
    db_session.add(pos)
    db_session.flush()

    svc = ReconciliationService(db_session)
    report = svc.run(date(2026, 6, 5))
    # cash 800K + mv 200K = 1M = equity
    assert report.status in ("PASS", "WARNING")
    assert float(report.computed_nav) == pytest.approx(1_000_000.0, abs=1.0)


def test_reconciliation_fail_on_large_discrepancy(db_session):
    _seed_config(db_session, equity=1_000_000.0)
    # Only 500K in ledger but equity says 1M → 50% discrepancy → FAIL
    _cash(db_session, 500_000.0, 500_000.0, date(2026, 6, 5))

    svc = ReconciliationService(db_session)
    report = svc.run(date(2026, 6, 5))
    assert report.status == "FAIL"
    assert report.failures
    assert float(report.discrepancy_pct) > 0.1


def test_is_healthy_blocks_on_fail(db_session):
    _seed_config(db_session, equity=1_000_000.0)
    _cash(db_session, 500_000.0, 500_000.0, date(2026, 6, 5))
    svc = ReconciliationService(db_session)
    svc.run(date(2026, 6, 5))
    ok, reason = svc.is_healthy()
    assert ok is False
    assert reason is not None


def test_is_healthy_passes_when_clean(db_session):
    _seed_config(db_session, equity=1_000_000.0)
    _cash(db_session, 1_000_000.0, 1_000_000.0, date(2026, 6, 5))
    svc = ReconciliationService(db_session)
    svc.run(date(2026, 6, 5))
    ok, reason = svc.is_healthy()
    assert ok is True


def test_is_healthy_allows_when_no_recon(db_session):
    """Fresh system with no reconciliation yet → allowed."""
    svc = ReconciliationService(db_session)
    ok, reason = svc.is_healthy()
    assert ok is True
