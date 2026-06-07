"""Execution service unit tests — lifecycle, audit, authorization guards."""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.execution.constants import ExecutionMode, ExecutionStatus
from app.execution.domain import TradeResult
from app.execution.services.execution_service import ExecutionService, ExecutionValidationError
from app.models.auth import Portfolio, User
from app.models.execution import ExecutionAudit, ExecutionEvent, ExecutionOrder
from app.models.portfolio_position import PortfolioConfig
from app.models.recommendation import RecommendationApproval, RecommendationResult, RecommendationRun
from app.models.stock import Stock


DEFAULT_PORTFOLIO_ID = UUID("00000000-0000-4000-8000-000000000010")
DEFAULT_USER_ID = UUID("00000000-0000-4000-8000-000000000001")


@pytest.fixture
def seed_execution_prereqs(db_session: Session):
    portfolio = Portfolio(id=DEFAULT_PORTFOLIO_ID, name="Default", slug="default", is_default=True)
    user = User(
        id=DEFAULT_USER_ID,
        email="owner@test.local",
        password_hash="x",
        display_name="Owner",
    )
    stock = Stock(id=uuid4(), symbol="TESTCO", name="Test Co", exchange="NSE")
    db_session.add_all([portfolio, user, stock])
    db_session.flush()

    rec_run = RecommendationRun(
        ranking_run_id=uuid4(),
        strategy_name="momentum_v1",
        universe_code="NIFTY_500",
        as_of_date=date.today(),
        status="completed",
        config_version="v1",
        config_snapshot={},
        input_hash="test-hash",
    )
    db_session.add(rec_run)
    db_session.flush()

    result = RecommendationResult(
        recommendation_run_id=rec_run.id,
        stock_id=stock.id,
        rank=1,
        composite_score=0.8,
        action="BUY",
        conviction_band="MEDIUM",
        conviction_score=75,
        conviction_components={},
        lifecycle_state="APPROVED",
        reason_codes=["TEST"],
    )
    db_session.add(result)
    db_session.flush()

    approval = RecommendationApproval(
        id=uuid4(),
        recommendation_result_id=result.id,
        approval_type="ENTRY",
        decision="APPROVED",
        actor_id=str(DEFAULT_USER_ID),
        decided_at=datetime.now(UTC),
    )
    db_session.add(approval)

    cfg = PortfolioConfig(
        portfolio_id=DEFAULT_PORTFOLIO_ID,
        is_active=True,
        total_equity=1_000_000,
        execution_mode="PAPER",
    )
    db_session.add(cfg)
    db_session.commit()
    return {"result": result, "approval": approval, "stock": stock}


def test_rejects_without_approval(db_session: Session, seed_execution_prereqs):
    svc = ExecutionService(db_session, portfolio_id=DEFAULT_PORTFOLIO_ID)
    result = seed_execution_prereqs["result"]
    db_session.query(RecommendationApproval).filter_by(recommendation_result_id=result.id).delete()
    db_session.commit()
    with pytest.raises(ExecutionValidationError, match="No APPROVED approval"):
        svc.submit_from_recommendation(
            recommendation_id=result.id,
            approval_id=None,
            requested_by=DEFAULT_USER_ID,
        )


def test_rejects_live_without_flag(db_session: Session, seed_execution_prereqs):
    svc = ExecutionService(
        db_session,
        portfolio_id=DEFAULT_PORTFOLIO_ID,
        settings=Settings(enable_live_trading=False),
    )
    result = seed_execution_prereqs["result"]
    approval = seed_execution_prereqs["approval"]
    with pytest.raises(Exception, match="ENABLE_LIVE_TRADING"):
        svc.submit_order(
            recommendation_id=result.id,
            approval_id=approval.id,
            requested_by=DEFAULT_USER_ID,
            execution_mode=ExecutionMode.LIVE,
        )


def test_submit_order_persists_audit_and_events(
    db_session: Session, seed_execution_prereqs, monkeypatch
):
    result = seed_execution_prereqs["result"]
    approval = seed_execution_prereqs["approval"]
    svc = ExecutionService(db_session, portfolio_id=DEFAULT_PORTFOLIO_ID)

    fake_result = TradeResult(
        broker_name="paper",
        broker_order_id="paper-abc",
        execution_status=ExecutionStatus.FILLED,
        filled_quantity=Decimal("10"),
        avg_fill_price=Decimal("100"),
        fees=Decimal("20"),
        slippage=Decimal("5"),
        raw_response={"paper_trade_id": str(uuid4())},
    )

    class FakeAdapter:
        broker_name = "paper"

        def place_order(self, request):
            return fake_result

        def cancel_order(self, broker_order_id):
            return fake_result

        def get_order_status(self, broker_order_id):
            return fake_result

        def health_check(self):
            return fake_result

        def sync_holdings(self, portfolio_id):
            return []

        def sync_positions(self, portfolio_id):
            return []

    monkeypatch.setattr(
        "app.execution.services.execution_service.ExecutionAdapterFactory.get_adapter",
        lambda self, mode: FakeAdapter(),
    )

    order = svc.submit_order(
        recommendation_id=result.id,
        approval_id=approval.id,
        requested_by=DEFAULT_USER_ID,
    )

    assert order.status == ExecutionStatus.FILLED.value
    events = db_session.query(ExecutionEvent).filter_by(execution_order_id=order.id).all()
    audits = db_session.query(ExecutionAudit).filter_by(execution_order_id=order.id).all()
    assert len(events) >= 2
    assert len(audits) >= 2
    assert order.requested_by == DEFAULT_USER_ID


def test_viewer_lacks_execution_write_permission():
    from app.auth.constants import Permission, UserRole, role_has_permission

    assert not role_has_permission(UserRole.VIEWER, Permission.EXECUTION_WRITE)
    assert role_has_permission(UserRole.OWNER, Permission.EXECUTION_WRITE)
