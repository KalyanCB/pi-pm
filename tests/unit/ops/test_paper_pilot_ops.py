"""Paper pilot orchestration tests."""
from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.ops.daily_batch.paper_pilot_ops import PaperPilotOps
from app.services.portfolio_service import RegimeLimits


def test_health_snapshot_structure(db_session):
    ops = PaperPilotOps(db_session)
    with patch.object(ops.portfolio_service, "get_limits") as mock_limits:
        with patch.object(ops.portfolio_service, "get_summary") as mock_summary:
            mock_limits.return_value = RegimeLimits(
                regime_posture="neutral",
                max_positions=6,
                max_buy_per_day=1,
                active_positions=2,
                slots_available=4,
                buys_today=0,
                can_add_position=True,
                block_reason=None,
            )
            mock_summary.return_value = {"total_equity": 1_000_000, "open_positions": 2}
            health = ops.health_snapshot(date(2026, 6, 5))
    assert health["as_of_date"] == "2026-06-05"
    assert health["limits"]["can_add_position"] is True
    assert health["summary"]["open_positions"] == 2


def test_run_invokes_portfolio_phases(db_session):
    ops = PaperPilotOps(db_session)
    ops.portfolio_service.recompute = MagicMock(return_value={"positions_updated": 1})
    ops.exit_monitor.run = MagicMock(return_value=[])
    ops.nav_service.snapshot = MagicMock()
    nav_mock = MagicMock()
    nav_mock.id = uuid4()
    nav_mock.total_equity = 1_000_000
    nav_mock.cash_pct = 0.15
    nav_mock.open_positions = 2
    ops.nav_service.snapshot.return_value = nav_mock
    recon_mock = MagicMock()
    recon_mock.id = uuid4()
    recon_mock.status = "PASS"
    recon_mock.discrepancy_pct = 0.0
    ops.reconciliation_service.run = MagicMock(return_value=recon_mock)

    result = ops.run(
        date(2026, 6, 5),
        paper_trading=False,
        pilot_auto_execute=False,
    )
    ops.portfolio_service.recompute.assert_called_once()
    ops.exit_monitor.run.assert_called_once_with(date(2026, 6, 5))
    ops.nav_service.snapshot.assert_called_once_with(date(2026, 6, 5))
    ops.reconciliation_service.run.assert_called_once_with(date(2026, 6, 5))
    assert result["reconcile"]["status"] == "PASS"
