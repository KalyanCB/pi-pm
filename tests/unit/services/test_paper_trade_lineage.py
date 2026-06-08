"""Paper trade lineage — ranking_run_id and outcome fields populated."""
from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.models.recommendation import RecommendationResult, RecommendationRun
from app.models.stock import Stock
from app.services.paper_trade_service import PaperTradeService


def _seed_buy_rec(db_session):
    stock = Stock(symbol="RELIANCE.NS", name="Reliance", exchange="NSE", is_active=True)
    db_session.add(stock)
    db_session.flush()

    ranking_run_id = uuid4()
    rec_run = RecommendationRun(
        ranking_run_id=ranking_run_id,
        strategy_name="momentum_v1",
        universe_code="NIFTY_500",
        as_of_date=date(2026, 6, 5),
        status="completed",
        config_version="v1",
        config_snapshot={},
        regime_snapshot={"regime_label": "BULL_LOW_VOL"},
        input_hash="abc",
    )
    db_session.add(rec_run)
    db_session.flush()

    result = RecommendationResult(
        recommendation_run_id=rec_run.id,
        stock_id=stock.id,
        rank=3,
        composite_score=0.82,
        action="BUY",
        lifecycle_state="APPROVED",
        conviction_score=78,
        conviction_band="HIGH",
        conviction_components={},
        reason_codes=["RANK_POOL_TOP20"],
    )
    db_session.add(result)
    db_session.flush()
    return result, ranking_run_id, stock


def test_entry_sets_ranking_run_id(db_session):
    result, ranking_run_id, stock = _seed_buy_rec(db_session)

    cfg_mock = MagicMock()
    cfg_mock.fee_per_leg = 20.0
    cfg_mock.total_equity = 1_000_000.0
    cfg_mock.deploy_pct = 0.85
    cfg_mock.regime_slots = {"neutral": {"max_positions": 6, "max_buy_per_day": 2}}

    svc = PaperTradeService(db_session)
    svc.portfolio_service.get_config = MagicMock(return_value=cfg_mock)
    svc.portfolio_service.compute_allocation = MagicMock(
        return_value=MagicMock(quantity_estimate=10.0)
    )
    svc.portfolio_service.open_position = MagicMock(
        return_value=MagicMock(id=uuid4())
    )
    svc.nav_service.ensure_initial_capital = MagicMock()
    svc.nav_service.record_cash_entry = MagicMock()

    latest_bar = MagicMock()
    latest_bar.close = 2500.0
    # _fill_price now calls get_by_stock_and_date_range (returns a list of bars)
    svc.market_data_repo.get_by_stock_and_date_range = MagicMock(return_value=[latest_bar])

    trade = svc.execute_entry(
        recommendation_result_id=result.id,
        as_of_date=date(2026, 6, 5),
    )
    assert trade.ranking_run_id == ranking_run_id
    assert trade.metadata_["recommendation_run_id"] == str(result.recommendation_run_id)
    svc.portfolio_service.open_position.assert_called_once()
    call_kw = svc.portfolio_service.open_position.call_args.kwargs
    assert call_kw["strategy_name"] == "momentum_v1"
