"""Low Volatility Ranking Strategy v1 (low_vol_v1).

Designed for BEAR_LOW_VOL regime where breakout/momentum signals invert.

Research basis (docs/research/BEAR_LOW_VOL_STRATEGIES.md):
  - Bottom quintile of breakout ranking returns +2.85% per 20d in BEAR_LOW_VOL
    vs top quintile +0.73% — ranking is inverted in bear regime.
  - Low-volatility stocks (low ATR, low realized vol) are the Q5 equivalents.
  - OOS evidence: 157 BEAR_LOW_VOL days (2022-2026), Sharpe 0.251.

Factor composition:
  vol_30d_inverse   (0.50) — 1 / annualized_volatility(30d) — primary signal
  vol_60d_inverse   (0.30) — 1 / annualized_volatility(60d) — confirms persistence
  atr_price_inverse (0.20) — 1 / (ATR_20 / close) — range stability

Higher score = lower volatility = higher rank = BUY candidate in BEAR_LOW_VOL.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.constants import (
    RANKING_STRATEGY_LOW_VOL_V1,
    RANKING_STRATEGY_LOW_VOL_V1_VERSION,
)
from app.ranking.math_utils import (
    PriceBar,
    annualized_volatility,
    average_true_range,
    bars_on_or_before,
)
from app.ranking.models import FactorScore, quantize_component, quantize_score
from app.ranking.strategy import RankingStrategy, StrategyRequirements
from app.universe.models import StockSnapshot

# Minimum floors to avoid division-by-zero
MIN_VOL = Decimal("0.001")
MIN_ATR_RATIO = Decimal("0.0001")

VOL_SHORT = 30
VOL_LONG = 60
ATR_WINDOW = 20
HISTORY_DAYS = VOL_LONG + 1  # 61 days

DEFAULT_WEIGHTS: dict[str, Decimal] = {
    "vol_30d_inverse":   Decimal("0.50"),
    "vol_60d_inverse":   Decimal("0.30"),
    "atr_price_inverse": Decimal("0.20"),
}


class LowVolV1Strategy:
    name = RANKING_STRATEGY_LOW_VOL_V1
    version = RANKING_STRATEGY_LOW_VOL_V1_VERSION

    FACTOR_VOL_30D   = "vol_30d_inverse"
    FACTOR_VOL_60D   = "vol_60d_inverse"
    FACTOR_ATR_PRICE = "atr_price_inverse"

    def __init__(self, weights: dict[str, Decimal] | None = None) -> None:
        self._weights = dict(DEFAULT_WEIGHTS)
        if weights:
            self._weights.update(weights)

    def requirements(self) -> StrategyRequirements:
        return StrategyRequirements(required_history_days=HISTORY_DAYS)

    def base_weights(self) -> dict[str, Decimal]:
        return dict(self._weights)

    def factor_names(self) -> tuple[str, ...]:
        return tuple(self._weights.keys())

    def compute_raw_factors(
        self,
        stock: StockSnapshot,
        price_series: list[PriceBar],
        benchmark_series: list[PriceBar] | None,
        as_of_date: date,
    ) -> dict[str, Decimal | None]:
        bars = bars_on_or_before(price_series, as_of_date)
        return {
            self.FACTOR_VOL_30D:   self._vol_inverse(bars, VOL_SHORT),
            self.FACTOR_VOL_60D:   self._vol_inverse(bars, VOL_LONG),
            self.FACTOR_ATR_PRICE: self._atr_price_inverse(bars),
        }

    def build_factor_scores(
        self,
        raw_factors: dict[str, Decimal | None],
        normalized_factors: dict[str, Decimal],
        effective_weights: dict[str, Decimal],
    ) -> list[FactorScore]:
        scores: list[FactorScore] = []
        for name in self.factor_names():
            if name not in effective_weights:
                continue
            weight = effective_weights[name]
            normalized = normalized_factors.get(name, Decimal("0"))
            weighted = quantize_score(normalized * weight)
            scores.append(
                FactorScore(
                    factor_name=name,
                    raw_value=raw_factors.get(name),
                    normalized_value=normalized,
                    weight=weight,
                    weighted_contribution=weighted,
                )
            )
        return scores

    def composite_score(self, factor_scores: list[FactorScore]) -> Decimal:
        return quantize_score(
            sum((fs.weighted_contribution for fs in factor_scores), Decimal("0"))
        )

    # ── Private factor computations ──────────────────────────────────────────

    def _vol_inverse(self, bars: list[PriceBar], window: int) -> Decimal | None:
        """1 / annualized_volatility — higher value = calmer stock = higher rank."""
        vol = annualized_volatility(bars, window)
        if vol is None or vol < MIN_VOL:
            return None
        return quantize_component(Decimal("1") / vol)

    def _atr_price_inverse(self, bars: list[PriceBar]) -> Decimal | None:
        """1 / (ATR_20 / close) — higher value = tighter range relative to price."""
        if not bars:
            return None
        atr = average_true_range(bars, ATR_WINDOW)
        close = Decimal(str(bars[-1].close))
        if atr is None or close <= 0:
            return None
        atr_ratio = atr / close
        if atr_ratio < MIN_ATR_RATIO:
            return None
        return quantize_component(Decimal("1") / atr_ratio)


def build_low_vol_v1_strategy() -> RankingStrategy:
    return LowVolV1Strategy()
