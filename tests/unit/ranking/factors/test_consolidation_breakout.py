from datetime import date
from decimal import Decimal

from app.ranking.factors.consolidation_breakout import ConsolidationBreakoutFactor
from tests.unit.ranking.factors.conftest import make_bars


def test_consolidation_scores_tight_base_near_highs():
    start = date(2023, 1, 1)
    bars = make_bars(start, 100, start_price=Decimal("100"), step=Decimal("0.05"))
    for index in range(-20, 0):
        wiggle = Decimal("0.02") if index % 2 == 0 else Decimal("-0.01")
        bars[index] = bars[index].__class__(
            date=bars[index].date,
            close=Decimal("100.05") + wiggle,
            volume=bars[index].volume,
        )
    score = ConsolidationBreakoutFactor.compute(bars)
    assert score is not None
    assert score > Decimal("0")


def test_consolidation_insufficient_history():
    bars = make_bars(date(2024, 1, 1), 30)
    assert ConsolidationBreakoutFactor.compute(bars) is None
