"""Tests for cross-strategy deduplication (Improvement 3)."""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock, call


def _make_buy_row(stock_id, conviction_score, strategy_name, result_id=None):
    row = MagicMock()
    row.id = result_id or uuid.uuid4()
    row.stock_id = stock_id
    row.conviction_score = conviction_score
    row.strategy_name = strategy_name
    return row


def test_cross_strategy_dedup_keeps_highest_conviction():
    """Two BUY results for the same stock from different strategies.
    The lower-conviction one should be downgraded to WATCH with
    CROSS_STRATEGY_DUPLICATE appended to reason_codes (ORM mutation path)."""
    from app.services.daily_batch_service import DailyBatchService

    stock_id = uuid.uuid4()
    high_id = uuid.uuid4()
    low_id = uuid.uuid4()

    high_row = _make_buy_row(stock_id, conviction_score=75, strategy_name="momentum_v1", result_id=high_id)
    low_row  = _make_buy_row(stock_id, conviction_score=55, strategy_name="breakout_v1", result_id=low_id)

    # ORM rec objects returned by second execute().scalars().all()
    low_rec = MagicMock()
    low_rec.id = low_id
    low_rec.action = "BUY"
    low_rec.reason_codes = []

    db = MagicMock()
    # First execute: SELECT BUY rows → returns high_row + low_row
    # Second execute: SELECT RecommendationResult for ids_to_downgrade → returns low_rec
    db.execute.return_value.all.return_value = [high_row, low_row]
    db.execute.return_value.scalars.return_value.all.return_value = [low_rec]

    svc = DailyBatchService.__new__(DailyBatchService)
    svc.db = db

    strategies = [
        MagicMock(strategy_name="momentum_v1"),
        MagicMock(strategy_name="breakout_v1"),
    ]
    svc._dedup_cross_strategy_buys(strategies=strategies, as_of_date=date(2026, 1, 31))

    # Two db.execute calls: first SELECT buys, second SELECT rows to fix
    assert db.execute.call_count == 2
    # The low-conviction record should be downgraded to WATCH
    assert low_rec.action == "WATCH"
    assert "CROSS_STRATEGY_DUPLICATE" in low_rec.reason_codes
    # flush should be called to persist mutations
    db.flush.assert_called_once()


def test_cross_strategy_dedup_single_strategy_no_change():
    """If only one strategy produced a BUY for a stock, no UPDATE should run."""
    from app.services.daily_batch_service import DailyBatchService

    stock_id = uuid.uuid4()
    only_row = _make_buy_row(stock_id, conviction_score=70, strategy_name="momentum_v1")

    db = MagicMock()
    db.execute.return_value.all.return_value = [only_row]

    svc = DailyBatchService.__new__(DailyBatchService)
    svc.db = db

    strategies = [MagicMock(strategy_name="momentum_v1")]
    svc._dedup_cross_strategy_buys(strategies=strategies, as_of_date=date(2026, 1, 31))

    # Only one db.execute call (the SELECT) — no UPDATE needed
    assert db.execute.call_count == 1
