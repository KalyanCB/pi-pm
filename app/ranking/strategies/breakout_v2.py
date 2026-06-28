"""Breakout Strategy v2 (breakout_v2) — ANTICIPATION, not confirmation.

Spec intent: rank stocks that are *about to* break out — a coiled, quiet base near
resistance — NOT stocks that have *already* broken out.

Why v2 exists: breakout_v1 put ~75% of its weight on after-the-fact confirmation
factors (volume_surge, atr_expansion, relative_strength, rs_acceleration,
vol_adj_momentum) which carry NEGATIVE forward IC — by the time they fire the move
is done, so you buy the top and it reverts. The one factor that actually predicts,
consolidation_breakout (+0.027 IC overall, +0.055 in bull), was weighted just 0.10.

v2 leads with the setup factors and DROPS every confirmation factor. Weights are
CALIBRATED on forward IC (not guessed) — bull composite IC +0.048, validated on the
2018-2024 local panel (vs the original guess's +0.033):
  high_proximity          (0.45) — near 52w high = breaking into clean air   [IC +0.038]
  vol_contraction         (0.35) — low recent volatility = quiet before move [IC +0.029]
  consolidation_breakout  (0.20) — tight base resolving; supporting only     [IC ~0 as lead,
                                    but additive at minority weight]

Higher score = better pre-breakout setup = higher rank = BUY candidate (bull regimes).
The real edge is "quiet stocks near their highs" — re-calibrate via scripts/signal_ic.sql.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V2,
    RANKING_STRATEGY_BREAKOUT_V2_VERSION,
)
from app.ranking.factors.consolidation_breakout import ConsolidationBreakoutFactor
from app.ranking.factors.high_proximity import FiftyTwoWeekHighFactor
from app.ranking.math_utils import (
    PriceBar,
    annualized_volatility,
    bars_on_or_before,
)
from app.ranking.models import FactorScore, quantize_component, quantize_score
from app.ranking.strategy import RankingStrategy, StrategyRequirements
from app.universe.models import StockSnapshot

MIN_VOL = Decimal("0.001")
VOL_LOOKBACK = 20  # recent realised volatility window (coil detector)
HISTORY_DAYS = max(FiftyTwoWeekHighFactor.lookback, 200) + 1

DEFAULT_WEIGHTS: dict[str, Decimal] = {
    "high_proximity": Decimal("0.45"),
    "vol_contraction": Decimal("0.35"),
    "consolidation_breakout": Decimal("0.20"),
}


class BreakoutV2Strategy:
    name = RANKING_STRATEGY_BREAKOUT_V2
    version = RANKING_STRATEGY_BREAKOUT_V2_VERSION

    FACTOR_CONSOLIDATION = "consolidation_breakout"
    FACTOR_VOL_CONTRACTION = "vol_contraction"
    FACTOR_HIGH_PROXIMITY = "high_proximity"

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
            self.FACTOR_CONSOLIDATION: ConsolidationBreakoutFactor.compute(bars),
            self.FACTOR_VOL_CONTRACTION: self._vol_contraction(bars),
            self.FACTOR_HIGH_PROXIMITY: FiftyTwoWeekHighFactor.compute(bars),
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
        total = sum((fs.weighted_contribution for fs in factor_scores), Decimal("0"))
        return quantize_score(total)

    def _vol_contraction(self, bars: list[PriceBar]) -> Decimal | None:
        """Low recent realised volatility = coiled spring. Returned inverted so that
        QUIETER names score HIGHER (the pre-breakout 'tightness')."""
        vol = annualized_volatility(bars, VOL_LOOKBACK)
        if vol is None or vol < MIN_VOL:
            return None
        return quantize_component(-vol)


def build_breakout_v2_strategy(weights: dict[str, Decimal] | None = None) -> RankingStrategy:
    return BreakoutV2Strategy(weights=weights)
