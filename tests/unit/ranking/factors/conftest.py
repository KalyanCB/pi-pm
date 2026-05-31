from datetime import date, timedelta
from decimal import Decimal

from app.ranking.math_utils import PriceBar


def make_bars(
    start: date,
    days: int,
    *,
    start_price: Decimal = Decimal("100"),
    step: Decimal = Decimal("0.1"),
    volume: int = 1_000_000,
) -> list[PriceBar]:
    bars: list[PriceBar] = []
    price = start_price
    for i in range(days):
        bars.append(
            PriceBar(
                date=start + timedelta(days=i),
                close=price,
                volume=volume + i,
            )
        )
        price += step
    return bars
