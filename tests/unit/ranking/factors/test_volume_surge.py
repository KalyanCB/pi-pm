from datetime import date
from decimal import Decimal

from app.ranking.factors.volume_surge import VolumeSurgeFactor
from tests.unit.ranking.factors.conftest import make_bars


def test_volume_surge_detects_recent_participation():
    start = date(2023, 1, 1)
    bars = make_bars(start, 100, volume=500_000)
    recent = bars[-20:]
    for index, bar in enumerate(recent):
        bars[-20 + index] = bar.__class__(
            date=bar.date,
            close=bar.close,
            volume=2_000_000 + index,
        )
    score = VolumeSurgeFactor.compute(bars)
    assert score is not None
    assert score > Decimal("1")


def test_volume_surge_insufficient_history():
    bars = make_bars(date(2024, 1, 1), 50)
    assert VolumeSurgeFactor.compute(bars) is None
