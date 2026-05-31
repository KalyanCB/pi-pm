from datetime import date
from decimal import Decimal

from app.ranking.factors.atr_expansion import AtrExpansionFactor
from tests.unit.ranking.factors.conftest import make_bars


def test_atr_expansion_rises_with_larger_recent_moves():
    start = date(2023, 1, 1)
    calm = make_bars(start, 60, step=Decimal("0.01"))
    volatile = make_bars(start, 60, step=Decimal("0.01"))
    for offset in range(14):
        index = -(14 - offset)
        volatile[index] = volatile[index].__class__(
            date=volatile[index].date,
            close=volatile[index - 1].close + Decimal("3"),
            volume=volatile[index].volume,
        )
    calm_score = AtrExpansionFactor.compute(calm)
    volatile_score = AtrExpansionFactor.compute(volatile)
    assert calm_score is not None
    assert volatile_score is not None
    assert volatile_score >= calm_score
    assert volatile_score > Decimal("1")


def test_atr_expansion_insufficient_history():
    bars = make_bars(date(2024, 1, 1), 40)
    assert AtrExpansionFactor.compute(bars) is None
