from datetime import date, timedelta
from decimal import Decimal

from app.ranking.math_utils import PriceBar
from app.validation.forward_returns import compute_forward_return


def _bars(start_price: int, days: int, start: date) -> list[PriceBar]:
    bars: list[PriceBar] = []
    price = start_price
    for i in range(days):
        bars.append(
            PriceBar(date=start + timedelta(days=i), close=Decimal(str(price)), volume=1_000_000)
        )
        price += 1
    return bars


def test_forward_return_5_trading_days():
    start = date(2025, 1, 1)
    bars = _bars(100, 20, start)
    as_of = start + timedelta(days=4)
    ret = compute_forward_return(bars, as_of, 5)
    assert ret is not None
    assert ret > 0


def test_forward_return_insufficient_future_data():
    start = date(2025, 1, 1)
    bars = _bars(100, 6, start)
    as_of = start + timedelta(days=4)
    assert compute_forward_return(bars, as_of, 5) is None
