from datetime import date, timedelta
from decimal import Decimal

from app.ranking.math_utils import PriceBar, total_return
from app.ranking.strategies.momentum_v1 import MomentumV1Strategy
from app.universe.models import StockSnapshot


def _bars(start: Decimal, days: int, start_date: date) -> list[PriceBar]:
    bars: list[PriceBar] = []
    price = start
    for i in range(days):
        bars.append(
            PriceBar(
                date=start_date + timedelta(days=i),
                close=price,
                volume=1_000_000 + (i * 1000),
            )
        )
        price += Decimal("1")
    return bars


def test_trend_quality_continuous():
    strategy = MomentumV1Strategy()
    start = date(2024, 1, 1)
    bars = _bars(Decimal("100"), 210, start)
    stock = StockSnapshot(
        stock_id=__import__("uuid").uuid4(),
        symbol="TEST.NS",
        name="Test",
        exchange="NSE",
        sector=None,
        data_status="ACTIVE",
        is_active=True,
    )
    factors = strategy.compute_raw_factors(stock, bars, None, bars[-1].date)
    assert factors["trend_quality"] is not None
    assert factors["relative_strength"] is None


def test_total_return_calculation():
    start = date(2024, 1, 1)
    bars = _bars(Decimal("100"), 70, start)
    ret = total_return(bars, 63)
    assert ret is not None
    assert ret > 0
