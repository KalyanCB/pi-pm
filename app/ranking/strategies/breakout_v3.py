"""Breakout Strategy v3 (breakout_v3) — a deterministic 2-STATE regime tilt.

v3 supersedes breakout_v2's mono-style design. Evidence (per-year cross-sectional IC
and top-of-book forward returns, 2021-2025, local panel):
  * breakout_v2's ``high_proximity`` factor has POSITIVE forward IC in EVERY year and is
    STRONGEST in the "failed" narrow years (+0.087 in 2024, +0.113 in 2025) — the core
    idea was never broken.
  * breakout_v2's ``vol_contraction`` factor (35% of its weight) has forward IC ~0 or
    NEGATIVE in every year 2021-2025 — it is dead weight that DILUTES proximity. v3 DROPS it.
  * ``low_volatility`` is the regime rotator: forward IC -0.08/-0.16 in broad-bull years
    (2021/2023) but +0.08/+0.12/+0.11 in the hard years (2022/2024/2025) — the anti-
    breakout style that paid exactly when breakout did not.
  * ``momentum_12m`` + ``trend_efficiency`` carry the broad-bull upside.

So v3 is a single configurable strategy run as TWO regime-selected sleeves (the breadth
regime — % of the universe above its own 200d SMA vs its trailing median — picks which):
  breakout_v3_broad  (BROAD market):  high_proximity 0.45 + momentum_12m 0.35 + trend_efficiency 0.20
  breakout_v3_def    (NARROW market): high_proximity 0.55 + low_vol_30d 0.45

``high_proximity`` is in BOTH — it is the one factor that works every regime. The switch
itself earns its keep: no static style wins all regimes (pro-trend collapses in 2024,
defensive is crushed in 2023); the regime-tracked composite captures ~95% of the broad
upside and ~90% of the defensive protection. Re-calibrate via scripts/signal_ic.sql.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V3_BROAD,
    RANKING_STRATEGY_BREAKOUT_V3_BROAD_VERSION,
    RANKING_STRATEGY_BREAKOUT_V3_DEF,
    RANKING_STRATEGY_BREAKOUT_V3_DEF_VERSION,
)
from app.ranking.factors.high_proximity import FiftyTwoWeekHighFactor
from app.ranking.math_utils import (
    PriceBar,
    annualized_volatility,
    bars_on_or_before,
    total_return,
)
from app.ranking.models import FactorScore, quantize_component, quantize_score
from app.ranking.strategy import RankingStrategy, StrategyRequirements
from app.universe.models import StockSnapshot

MIN_VOL = Decimal("0.001")
MOM_LONG = 252        # 12-month trend
EFF_WINDOW = 60       # trend-efficiency lookback
VOL_WINDOW = 30       # low-vol lookback

FACTOR_HIGH_PROXIMITY = "high_proximity"
FACTOR_MOMENTUM_12M = "momentum_12m"
FACTOR_TREND_EFFICIENCY = "trend_efficiency"
FACTOR_LOW_VOL = "low_vol_30d"

BROAD_WEIGHTS: dict[str, Decimal] = {
    FACTOR_HIGH_PROXIMITY: Decimal("0.45"),
    FACTOR_MOMENTUM_12M: Decimal("0.35"),
    FACTOR_TREND_EFFICIENCY: Decimal("0.20"),
}
DEFENSIVE_WEIGHTS: dict[str, Decimal] = {
    FACTOR_HIGH_PROXIMITY: Decimal("0.55"),
    FACTOR_LOW_VOL: Decimal("0.45"),
}

# History: proximity + momentum both need 252 bars; trend_efficiency needs EFF_WINDOW.
HISTORY_DAYS = max(FiftyTwoWeekHighFactor.lookback, MOM_LONG, EFF_WINDOW) + 5


class BreakoutV3Strategy:
    """Configurable: same factor library, regime-specific weights. Registered twice
    (broad / defensive); the breadth regime selects which sleeve trades each day."""

    def __init__(self, name: str, version: str, weights: dict[str, Decimal]) -> None:
        self.name = name
        self.version = version
        self._weights = dict(weights)

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
        # only compute the factors this sleeve actually weights
        out: dict[str, Decimal | None] = {}
        for name in self.factor_names():
            out[name] = self._compute_factor(name, bars)
        return out

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

    # ── factor library (all return HIGHER = better, like the rest of the codebase) ──

    def _compute_factor(self, name: str, bars: list[PriceBar]) -> Decimal | None:
        if name == FACTOR_HIGH_PROXIMITY:
            return FiftyTwoWeekHighFactor.compute(bars)
        if name == FACTOR_MOMENTUM_12M:
            r = total_return(bars, MOM_LONG)
            return quantize_component(r) if r is not None else None
        if name == FACTOR_TREND_EFFICIENCY:
            return self._trend_efficiency(bars, EFF_WINDOW)
        if name == FACTOR_LOW_VOL:
            return self._low_vol(bars, VOL_WINDOW)
        return None

    def _trend_efficiency(self, bars: list[PriceBar], window: int) -> Decimal | None:
        """Kaufman efficiency ratio: |net move| / sum(|daily moves|) over ``window``.
        Higher = a cleaner, more efficient (institutional) trend; lower = choppy noise."""
        if len(bars) < window + 1:
            return None
        closes = [Decimal(str(b.close)) for b in bars[-(window + 1):]]
        net = abs(closes[-1] - closes[0])
        gross = sum((abs(closes[i] - closes[i - 1]) for i in range(1, len(closes))), Decimal("0"))
        if gross <= 0:
            return None
        return quantize_component(net / gross)

    def _low_vol(self, bars: list[PriceBar], window: int) -> Decimal | None:
        """1 / annualised volatility — higher = calmer stock = higher rank (defensive)."""
        vol = annualized_volatility(bars, window)
        if vol is None or vol < MIN_VOL:
            return None
        return quantize_component(Decimal("1") / vol)


def build_breakout_v3_broad_strategy() -> RankingStrategy:
    return BreakoutV3Strategy(
        RANKING_STRATEGY_BREAKOUT_V3_BROAD,
        RANKING_STRATEGY_BREAKOUT_V3_BROAD_VERSION,
        BROAD_WEIGHTS,
    )


def build_breakout_v3_def_strategy() -> RankingStrategy:
    return BreakoutV3Strategy(
        RANKING_STRATEGY_BREAKOUT_V3_DEF,
        RANKING_STRATEGY_BREAKOUT_V3_DEF_VERSION,
        DEFENSIVE_WEIGHTS,
    )
