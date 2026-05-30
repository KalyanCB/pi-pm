from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.constants import RANKING_STRATEGY_MOMENTUM_V1, RANKING_STRATEGY_MOMENTUM_V1_VERSION
from app.ranking.math_utils import (
    PriceBar,
    annualized_volatility,
    average_volume,
    bars_on_or_before,
    simple_moving_average,
    total_return,
)
from app.ranking.models import FactorScore, quantize_component, quantize_score
from app.ranking.strategy import RankingStrategy, StrategyRequirements
from app.universe.models import StockSnapshot

MIN_VOL = Decimal("0.001")
MOMENTUM_LOOKBACK = 63
VOLUME_SHORT = 20
VOLUME_LONG = 50
MA_SHORT = 50
MA_LONG = 200


class MomentumV1Strategy:
    name = RANKING_STRATEGY_MOMENTUM_V1
    version = RANKING_STRATEGY_MOMENTUM_V1_VERSION

    FACTOR_VOL_ADJ_MOMENTUM = "volatility_adjusted_momentum"
    FACTOR_VOLUME_EXPANSION = "volume_expansion"
    FACTOR_TREND_QUALITY = "trend_quality"
    FACTOR_RELATIVE_STRENGTH = "relative_strength"

    def requirements(self) -> StrategyRequirements:
        return StrategyRequirements(required_history_days=MA_LONG + 1)

    def base_weights(self) -> dict[str, Decimal]:
        return {
            self.FACTOR_VOL_ADJ_MOMENTUM: Decimal("0.40"),
            self.FACTOR_VOLUME_EXPANSION: Decimal("0.25"),
            self.FACTOR_TREND_QUALITY: Decimal("0.20"),
            self.FACTOR_RELATIVE_STRENGTH: Decimal("0.15"),
        }

    def factor_names(self) -> tuple[str, ...]:
        return (
            self.FACTOR_VOL_ADJ_MOMENTUM,
            self.FACTOR_VOLUME_EXPANSION,
            self.FACTOR_TREND_QUALITY,
            self.FACTOR_RELATIVE_STRENGTH,
        )

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
            self.FACTOR_VOLUME_EXPANSION: self._volume_expansion(bars),
            self.FACTOR_TREND_QUALITY: self._trend_quality(bars),
            self.FACTOR_RELATIVE_STRENGTH: None,
        }

        if benchmark_series is not None:
            bench_bars = bars_on_or_before(benchmark_series, as_of_date)
            factors[self.FACTOR_RELATIVE_STRENGTH] = self._relative_strength(bars, bench_bars)

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

    def _volume_expansion(self, bars: list[PriceBar]) -> Decimal | None:
        short = average_volume(bars, VOLUME_SHORT)
        long = average_volume(bars, VOLUME_LONG)
        if short is None or long is None or long <= 0:
            return None
        return quantize_component(short / long)

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

    def _relative_strength(
        self, stock_bars: list[PriceBar], bench_bars: list[PriceBar]
    ) -> Decimal | None:
        stock_ret = total_return(stock_bars, MOMENTUM_LOOKBACK)
        bench_ret = total_return(bench_bars, MOMENTUM_LOOKBACK)
        if stock_ret is None or bench_ret is None:
            return None
        return quantize_component(stock_ret - bench_ret)


def build_momentum_v1_strategy() -> RankingStrategy:
    return MomentumV1Strategy()
