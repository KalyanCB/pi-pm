"""Daily batch portfolio phase flags — schema contract."""
from app.schemas.daily_batch import DailyBatchPhaseFlags, DailyBatchPortfolioPhaseFlags, DailyBatchRunCreateRequest


def test_portfolio_phases_default_off():
    req = DailyBatchRunCreateRequest()
    assert req.phases.portfolio is False
    assert req.pilot_auto_execute is False
    assert req.pilot_auto_approve is False


def test_portfolio_phases_enabled():
    req = DailyBatchRunCreateRequest(
        phases=DailyBatchPhaseFlags(portfolio=True),
        portfolio_phases=DailyBatchPortfolioPhaseFlags(
            recompute=True,
            exit_monitor=True,
            paper_trading=True,
            nav_snapshot=True,
            reconcile=True,
        ),
        pilot_auto_execute=True,
        pilot_auto_approve=True,
    )
    assert req.phases.portfolio is True
    assert req.pilot_auto_execute is True
    assert req.portfolio_phases.reconcile is True
