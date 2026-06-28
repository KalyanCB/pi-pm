"""Momentum Strategy v2 (momentum_v2) — GAINING, not already gained.

Spec intent: rank stocks that are *starting* to move from a quiet base — early
momentum with room to run — NOT stocks that have already run up (which revert).

Why v2 exists: momentum_v1 put 100% of weight on already-moved factors
(vol_adj_momentum 0.40, volume_expansion 0.25, trend_quality 0.20,
relative_strength 0.15) — ALL with negative forward IC within the ranked pool: the
hottest names mean-revert. Forward-return research (monthly panel, 2019-2026):
  - early base (60d return <5%) + just turning up (5d >1%)  -> +1.75% fwd 10d
  - the dead middle (already up a bit, not extreme)          -> +0.26%
So the edge is the TURN off a low base, not extension.

v2 factors:
  nascent_momentum (0.50) — recent 10d up-move (the turn is happening now)
  low_base         (0.30) — NOT already gained over 60d (room to run)
  reclaim_ma       (0.20) — price back above its 20d MA (turn confirmed, still early)

Higher score = early-stage mover = higher rank = BUY (trending/risk-on regimes).
Calibrate against scripts/signal_ic.sql.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.constants import (
    RANKING_STRATEGY_MOMENTUM_V2,
    RANKING_STRATEGY_MOMENTUM_V2_VERSION,
)
from app.ranking.math_utils import (
    PriceBar,
    bars_on_or_before,
    simple_moving_average,
    total_return,
)
from app.ranking.models import FactorScore, quantize_component, quantize_score
from app.ranking.strategy import RankingStrategy, StrategyRequirements
from app.universe.models import StockSnapshot

SHORT_LOOKBACK = 10   # the recent "turning up" window
BASE_LOOKBACK = 60    # the "not already gained" base window
MA_WINDOW = 20
HISTORY_DAYS = BASE_LOOKBACK + 5

DEFAULT_WEIGHTS: dict[str, Decimal] = {
    "nascent_momentum": Decimal("0.50"),
    "low_base": Decimal("0.30"),
    "reclaim_ma": Decimal("0.20"),
}


class MomentumV2Strategy:
    name = RANKING_STRATEGY_MOMENTUM_V2
    version = RANKING_STRATEGY_MOMENTUM_V2_VERSION

    FACTOR_NASCENT = "nascent_momentum"
    FACTOR_LOW_BASE = "low_base"
    FACTOR_RECLAIM_MA = "reclaim_ma"

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
            self.FACTOR_NASCENT: self._nascent_momentum(bars),
            self.FACTOR_LOW_BASE: self._low_base(bars),
            self.FACTOR_RECLAIM_MA: self._reclaim_ma(bars),
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

    def _nascent_momentum(self, bars: list[PriceBar]) -> Decimal | None:
        """Recent 10d return — the move is starting NOW. Higher = stronger turn."""
        r = total_return(bars, SHORT_LOOKBACK)
        return quantize_component(r) if r is not None else None

    def _low_base(self, bars: list[PriceBar]) -> Decimal | None:
        """Inverse 60d return — penalise already-extended names (room to run).
        Returned negated so a LOW base ranks HIGHER. Combined with nascent_momentum
        (which must be positive to rank), this isolates 'low base + turning up'."""
        r = total_return(bars, BASE_LOOKBACK)
        return quantize_component(-r) if r is not None else None

    def _reclaim_ma(self, bars: list[PriceBar]) -> Decimal | None:
        """Price relative to its 20d MA — back above = turn confirmed, still early."""
        if len(bars) < MA_WINDOW:
            return None
        ma = simple_moving_average(bars, MA_WINDOW)
        if ma is None or ma <= 0:
            return None
        close = Decimal(str(bars[-1].close))
        return quantize_component((close / ma) - Decimal("1"))


def build_momentum_v2_strategy(weights: dict[str, Decimal] | None = None) -> RankingStrategy:
    return MomentumV2Strategy(weights=weights)
