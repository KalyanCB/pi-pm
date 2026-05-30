from datetime import date, timedelta
from decimal import Decimal

from app.ranking.math_utils import PriceBar
from app.validation.constants import TREND_REGIME_BULL, VOL_REGIME_LOW
from app.validation.regimes import classify_regime


def test_classify_bull_low_vol_regime():
    start = date(2024, 1, 1)
    bars: list[PriceBar] = []
    price = 100
    for i in range(220):
        bars.append(
            PriceBar(date=start + timedelta(days=i), close=Decimal(str(price)), volume=1_000_000)
        )
        price += 1

    regime = classify_regime(bars, bars[-1].date, Decimal("0.50"))
    assert regime is not None
    assert regime.trend_regime == TREND_REGIME_BULL
    assert regime.vol_regime == VOL_REGIME_LOW
    assert regime.regime_label == f"{TREND_REGIME_BULL}_{VOL_REGIME_LOW}"
