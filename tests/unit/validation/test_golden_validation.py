from datetime import date
from decimal import Decimal
from uuid import UUID

from app.validation.hashing import build_validation_hash
from app.validation.models import RegimeClassification, StockForwardReturns
from app.validation.statistics import _ScoredReturn, compute_horizon_metrics

GOLDEN_HASH = "placeholder"


def test_validation_hash_stable():
    run_id = UUID("11111111-1111-1111-1111-111111111111")
    as_of = date(2025, 1, 31)
    regime = RegimeClassification("BULL", "LOW_VOL", "BULL_LOW_VOL")
    stock_returns = (
        StockForwardReturns(
            UUID("22222222-2222-2222-2222-222222222222"),
            "AAA.NS",
            Decimal("0.9"),
            1,
            {5: Decimal("0.01"), 10: Decimal("0.02"), 20: Decimal("0.03"), 60: Decimal("0.04")},
        ),
        StockForwardReturns(
            UUID("33333333-3333-3333-3333-333333333333"),
            "BBB.NS",
            Decimal("0.8"),
            2,
            {5: Decimal("0.02"), 10: Decimal("0.03"), 20: Decimal("0.04"), 60: Decimal("0.05")},
        ),
        StockForwardReturns(
            UUID("44444444-4444-4444-4444-444444444444"),
            "CCC.NS",
            Decimal("0.7"),
            3,
            {5: Decimal("0.03"), 10: Decimal("0.04"), 20: Decimal("0.05"), 60: Decimal("0.06")},
        ),
        StockForwardReturns(
            UUID("55555555-5555-5555-5555-555555555555"),
            "DDD.NS",
            Decimal("0.6"),
            4,
            {5: Decimal("0.04"), 10: Decimal("0.05"), 20: Decimal("0.06"), 60: Decimal("0.07")},
        ),
        StockForwardReturns(
            UUID("66666666-6666-6666-6666-666666666666"),
            "EEE.NS",
            Decimal("0.5"),
            5,
            {5: Decimal("0.05"), 10: Decimal("0.06"), 20: Decimal("0.07"), 60: Decimal("0.08")},
        ),
    )
    horizon_metrics = {
        20: compute_horizon_metrics(
            20,
            [
                _ScoredReturn("AAA.NS", Decimal("0.9"), 1, Decimal("0.03")),
                _ScoredReturn("BBB.NS", Decimal("0.8"), 2, Decimal("0.04")),
                _ScoredReturn("CCC.NS", Decimal("0.7"), 3, Decimal("0.05")),
                _ScoredReturn("DDD.NS", Decimal("0.6"), 4, Decimal("0.06")),
                _ScoredReturn("EEE.NS", Decimal("0.5"), 5, Decimal("0.07")),
            ],
        )
    }
    first = build_validation_hash(
        run_id, "inputs123", as_of, regime, stock_returns, horizon_metrics
    )
    second = build_validation_hash(
        run_id, "inputs123", as_of, regime, stock_returns, horizon_metrics
    )
    assert first == second
    assert len(first) == 64
