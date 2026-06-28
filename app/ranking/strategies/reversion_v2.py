"""Mean-Reversion Strategy v2 (reversion_v2) — for BEAR regimes.

Spec intent: in a bear, buy stocks that have been *beaten to death recently* and are
starting to stabilise — the panic overshoot that snaps back — NOT chronic long-term
losers that keep bleeding.

Why v2 exists: reversal_v1 keyed off a 63-day inverse return (anti_momentum 0.35,
anti_rs 0.30) — that picks CHRONIC losers (down for months), which keep falling
(weak/zero IC). Forward-return research (monthly panel) shows the edge is the
SHORT-term crush:
  - In BEAR, the worst 20d-return quintile (avg -18.9%) -> +2.57% fwd 10d, 59% recover
  - vs the strongest quintile in bear                   -> +0.88%
So it's the recent ~20-day washout that reverts, not the 63-day downtrend.

v2 factors:
  short_oversold (0.55) — inverse 20d return: the recent washout (the snap-back fuel)
  near_52w_low   (0.25) — depth of drawdown vs 52w low (capitulation zone)
  stabilizing    (0.20) — last-3d return turning up: the knife has slowed (avoid catching falls)

Higher score = recently crushed + stabilising = higher rank = BUY (bear regimes only).
Pair with tight stops; calibrate against scripts/signal_ic.sql.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.constants import (
    RANKING_STRATEGY_REVERSION_V2,
    RANKING_STRATEGY_REVERSION_V2_VERSION,
)
from app.ranking.math_utils import (
    PriceBar,
    bars_on_or_before,
    rolling_min_close,
    total_return,
)
from app.ranking.models import FactorScore, quantize_component, quantize_score
from app.ranking.strategy import RankingStrategy, StrategyRequirements
from app.universe.models import StockSnapshot

OVERSOLD_LOOKBACK = 20   # the recent washout window (the validated reversion signal)
STABILIZE_LOOKBACK = 3   # very-recent turn (avoid falling knives)
LOW_WINDOW = 252         # 52-week low for capitulation depth
HISTORY_DAYS = LOW_WINDOW + 1

DEFAULT_WEIGHTS: dict[str, Decimal] = {
    "short_oversold": Decimal("0.55"),
    "near_52w_low": Decimal("0.25"),
    "stabilizing": Decimal("0.20"),
}


class ReversionV2Strategy:
    name = RANKING_STRATEGY_REVERSION_V2
    version = RANKING_STRATEGY_REVERSION_V2_VERSION

    FACTOR_OVERSOLD = "short_oversold"
    FACTOR_NEAR_LOW = "near_52w_low"
    FACTOR_STABILIZING = "stabilizing"

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
            self.FACTOR_OVERSOLD: self._short_oversold(bars),
            self.FACTOR_NEAR_LOW: self._near_52w_low(bars),
            self.FACTOR_STABILIZING: self._stabilizing(bars),
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

    def _short_oversold(self, bars: list[PriceBar]) -> Decimal | None:
        """Inverse 20d return — the deeper the recent washout, the higher the score
        (the validated +2.57% snap-back fuel in bear)."""
        r = total_return(bars, OVERSOLD_LOOKBACK)
        return quantize_component(-r) if r is not None else None

    def _near_52w_low(self, bars: list[PriceBar]) -> Decimal | None:
        """Capitulation depth: how close to the 52w low. Returned so that names nearer
        the low score HIGHER (smaller distance above the low -> larger score)."""
        if not bars:
            return None
        low = rolling_min_close(bars, LOW_WINDOW)
        if low is None or low <= 0:
            return None
        close = Decimal(str(bars[-1].close))
        return quantize_component(-((close / low) - Decimal("1")))

    def _stabilizing(self, bars: list[PriceBar]) -> Decimal | None:
        """Very-recent (3d) return turning up = the knife has slowed. Higher = more
        stabilised, which filters out names still in free-fall."""
        r = total_return(bars, STABILIZE_LOOKBACK)
        return quantize_component(r) if r is not None else None


def build_reversion_v2_strategy(weights: dict[str, Decimal] | None = None) -> RankingStrategy:
    return ReversionV2Strategy(weights=weights)
