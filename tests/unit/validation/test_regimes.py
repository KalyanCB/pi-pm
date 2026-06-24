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


def test_breadth_forces_bear_even_when_index_bullish():
    """P-14: a rising benchmark (BULL on index signals) is overridden to BEAR when
    universe breadth is below 45% — the 2024-H1 large-cap-vs-small-cap divergence."""
    start = date(2024, 1, 1)
    bars: list[PriceBar] = []
    price = 100
    for i in range(220):
        bars.append(
            PriceBar(date=start + timedelta(days=i), close=Decimal(str(price)), volume=1_000_000)
        )
        price += 1  # steadily rising index → would be BULL

    bullish = classify_regime(bars, bars[-1].date, Decimal("0.50"), breadth_pct=0.70)
    assert bullish.trend_regime == TREND_REGIME_BULL  # high breadth → stays BULL

    weak_breadth = classify_regime(bars, bars[-1].date, Decimal("0.50"), breadth_pct=0.30)
    assert weak_breadth.trend_regime == "BEAR"  # breadth < 0.45 → BEAR despite rising index


def test_breadth_none_is_ignored():
    """No breadth data (cold start) → classifier ignores it, no spurious BEAR."""
    start = date(2024, 1, 1)
    bars = [PriceBar(date=start + timedelta(days=i), close=Decimal(str(100 + i)), volume=1_000_000)
            for i in range(220)]
    regime = classify_regime(bars, bars[-1].date, Decimal("0.50"), breadth_pct=None)
    assert regime.trend_regime == TREND_REGIME_BULL
