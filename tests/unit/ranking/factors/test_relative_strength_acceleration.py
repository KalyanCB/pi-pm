from datetime import date
from decimal import Decimal

from app.ranking.factors.relative_strength_acceleration import RelativeStrengthAccelerationFactor
from tests.unit.ranking.factors.conftest import make_bars


def test_positive_acceleration_when_stock_outperforms():
    start = date(2023, 1, 1)
    stock = make_bars(start, 100, start_price=Decimal("100"), step=Decimal("0.2"))
    benchmark = make_bars(start, 100, start_price=Decimal("100"), step=Decimal("0.2"))
    for offset in range(20):
        index = -(20 - offset)
        stock[index] = stock[index].__class__(
            date=stock[index].date,
            close=stock[index - 1].close + Decimal("2"),
            volume=stock[index].volume,
        )
    score = RelativeStrengthAccelerationFactor.compute(stock, benchmark)
    assert score is not None
    assert score > Decimal("0")


def test_insufficient_history():
    start = date(2024, 1, 1)
    stock = make_bars(start, 70)
    benchmark = make_bars(start, 70)
    assert RelativeStrengthAccelerationFactor.compute(stock, benchmark) is None
