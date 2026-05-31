from datetime import date
from decimal import Decimal

from app.ranking.factors.high_proximity import FiftyTwoWeekHighFactor
from tests.unit.ranking.factors.conftest import make_bars


def test_at_52_week_high():
    start = date(2023, 1, 1)
    bars = make_bars(start, 260, step=Decimal("0.5"))
    score = FiftyTwoWeekHighFactor.compute(bars)
    assert score is not None
    assert score == Decimal("0.000000")


def test_below_52_week_high():
    start = date(2023, 1, 1)
    bars = make_bars(start, 260, step=Decimal("0.5"))
    bars[-1] = bars[-1].__class__(
        date=bars[-1].date,
        close=Decimal("80"),
        volume=bars[-1].volume,
    )
    score = FiftyTwoWeekHighFactor.compute(bars)
    assert score is not None
    assert score < Decimal("0")


def test_insufficient_history():
    bars = make_bars(date(2024, 1, 1), 100)
    assert FiftyTwoWeekHighFactor.compute(bars) is None
