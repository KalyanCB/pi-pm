from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_BREAKOUT_V1_VERSION,
)
from app.ranking.factors.atr_expansion import AtrExpansionFactor
from app.ranking.factors.consolidation_breakout import ConsolidationBreakoutFactor
from app.ranking.factors.high_proximity import FiftyTwoWeekHighFactor
from app.ranking.factors.relative_strength_acceleration import RelativeStrengthAccelerationFactor
from app.ranking.factors.volume_surge import VolumeSurgeFactor
from app.ranking.math_utils import (
    PriceBar,
    annualized_volatility,
    bars_on_or_before,
    relative_strength_spread,
    simple_moving_average,
    total_return,
)
from app.ranking.models import FactorScore, quantize_component, quantize_score
from app.ranking.strategy import RankingStrategy, StrategyRequirements
from app.universe.models import StockSnapshot

MIN_VOL = Decimal("0.001")
MOMENTUM_LOOKBACK = 63
MA_SHORT = 50
MA_LONG = 200
HISTORY_DAYS = max(
    MA_LONG + 1,
    FiftyTwoWeekHighFactor.lookback,
    VolumeSurgeFactor.long_window + 1,
    AtrExpansionFactor.long_window + 1,
    RelativeStrengthAccelerationFactor.rs_lookback
    + RelativeStrengthAccelerationFactor.lag
    + 1,
)

DEFAULT_WEIGHTS: dict[str, Decimal] = {
    "volatility_adjusted_momentum": Decimal("0.20"),
    "relative_strength": Decimal("0.15"),
    "trend_quality": Decimal("0.10"),
    "volume_surge": Decimal("0.15"),
    "high_proximity": Decimal("0.15"),
    "atr_expansion": Decimal("0.10"),
    "relative_strength_acceleration": Decimal("0.05"),
    "consolidation_breakout": Decimal("0.10"),
}


class BreakoutV1Strategy:
    name = RANKING_STRATEGY_BREAKOUT_V1
    version = RANKING_STRATEGY_BREAKOUT_V1_VERSION

    FACTOR_VOL_ADJ_MOMENTUM = "volatility_adjusted_momentum"
    FACTOR_RELATIVE_STRENGTH = "relative_strength"
    FACTOR_TREND_QUALITY = "trend_quality"
    FACTOR_VOLUME_SURGE = "volume_surge"
    FACTOR_HIGH_PROXIMITY = "high_proximity"
    FACTOR_ATR_EXPANSION = "atr_expansion"
    FACTOR_RS_ACCELERATION = "relative_strength_acceleration"
    FACTOR_CONSOLIDATION = "consolidation_breakout"

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
        factors: dict[str, Decimal | None] = {
            self.FACTOR_VOL_ADJ_MOMENTUM: self._volatility_adjusted_momentum(bars),
            self.FACTOR_TREND_QUALITY: self._trend_quality(bars),
            self.FACTOR_VOLUME_SURGE: VolumeSurgeFactor.compute(bars),
            self.FACTOR_HIGH_PROXIMITY: FiftyTwoWeekHighFactor.compute(bars),
            self.FACTOR_ATR_EXPANSION: AtrExpansionFactor.compute(bars),
            self.FACTOR_CONSOLIDATION: ConsolidationBreakoutFactor.compute(bars),
            self.FACTOR_RELATIVE_STRENGTH: None,
            self.FACTOR_RS_ACCELERATION: None,
        }

        if benchmark_series is not None:
            bench_bars = bars_on_or_before(benchmark_series, as_of_date)
            rs = relative_strength_spread(bars, bench_bars, MOMENTUM_LOOKBACK)
            factors[self.FACTOR_RELATIVE_STRENGTH] = (
                quantize_component(rs) if rs is not None else None
            )
            factors[self.FACTOR_RS_ACCELERATION] = RelativeStrengthAccelerationFactor.compute(
                bars, bench_bars
            )

        return factors

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

    def _volatility_adjusted_momentum(self, bars: list[PriceBar]) -> Decimal | None:
        total_ret = total_return(bars, MOMENTUM_LOOKBACK)
        vol = annualized_volatility(bars, MOMENTUM_LOOKBACK)
        if total_ret is None or vol is None or vol < MIN_VOL:
            return None
        return quantize_component(total_ret / vol)

    def _trend_quality(self, bars: list[PriceBar]) -> Decimal | None:
        if len(bars) < MA_LONG:
            return None
        close = bars[-1].close
        ma50 = simple_moving_average(bars, MA_SHORT)
        ma200 = simple_moving_average(bars, MA_LONG)
        if ma50 is None or ma200 is None or ma50 <= 0 or ma200 <= 0:
            return None
        score = (Decimal("0.5") * (close / ma50)) + (Decimal("0.5") * (close / ma200))
        return quantize_component(score)


def build_breakout_v1_strategy(weights: dict[str, Decimal] | None = None) -> RankingStrategy:
    return BreakoutV1Strategy(weights=weights)
