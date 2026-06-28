"""Mean-Reversion Strategy v3 (reversion_v3) — for BEAR regimes. PURE deep-oversold.

Spec intent: in a bear, buy the stocks that have been beaten down the hardest — the
capitulation overshoot snaps back. Hold ~20 days for the reversion to play out.

Why v3 exists: reversion_v2 had the right thesis but the wrong recipe — its
`stabilizing` factor (buy names already bouncing) had IC -0.024 (you bought the ones
about to re-revert) and it was judged at a 10-day horizon. Full-sample validation
(82 bear weeks, ^NSEI<200dMA) on the PURE crushed signal:
    trailing return  ->10d    ->20d    ->60d
    20d               -0.067   -0.082   -0.065
    60d               -0.063   -0.085   -0.075
(negative IC = buying the crushed works). |IC| ~0.08 — stronger than breakout_v2.
Most-crushed quintile beat the rest by +1.8pp over 20 days.

v3 is deliberately MINIMAL — two oversold factors, nothing else (no stabilizing, no
near-low, no quality filter; the NIFTY_1000 universe already handles liquidity):
    oversold_20d (0.50) — inverse 20d return: the recent washout
    oversold_60d (0.50) — inverse 60d return: the deeper quarter-long drawdown

Higher score = more deeply crushed = higher rank = BUY (bear regimes only).
IMPORTANT: the edge needs a ~20-DAY HOLD — pair with an exit that lets it breathe;
a 2-day churn sells before the reversion pays. Re-calibrate via scripts/signal_ic.sql.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.constants import (
    RANKING_STRATEGY_REVERSION_V3,
    RANKING_STRATEGY_REVERSION_V3_VERSION,
)
from app.ranking.math_utils import PriceBar, bars_on_or_before, total_return
from app.ranking.models import FactorScore, quantize_component, quantize_score
from app.ranking.strategy import RankingStrategy, StrategyRequirements
from app.universe.models import StockSnapshot

OVERSOLD_SHORT = 20   # recent washout window
OVERSOLD_LONG = 60    # quarter-long drawdown window
HISTORY_DAYS = OVERSOLD_LONG + 5

DEFAULT_WEIGHTS: dict[str, Decimal] = {
    "oversold_20d": Decimal("0.50"),
    "oversold_60d": Decimal("0.50"),
}


class ReversionV3Strategy:
    name = RANKING_STRATEGY_REVERSION_V3
    version = RANKING_STRATEGY_REVERSION_V3_VERSION

    FACTOR_OVERSOLD_20 = "oversold_20d"
    FACTOR_OVERSOLD_60 = "oversold_60d"

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
            self.FACTOR_OVERSOLD_20: self._oversold(bars, OVERSOLD_SHORT),
            self.FACTOR_OVERSOLD_60: self._oversold(bars, OVERSOLD_LONG),
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

    def _oversold(self, bars: list[PriceBar], lookback: int) -> Decimal | None:
        """Inverse trailing return over ``lookback`` — the deeper the drop, the higher
        the score (the validated bear snap-back signal)."""
        r = total_return(bars, lookback)
        return quantize_component(-r) if r is not None else None


def build_reversion_v3_strategy(weights: dict[str, Decimal] | None = None) -> RankingStrategy:
    return ReversionV3Strategy(weights=weights)
