"""Momentum Strategy v3 (momentum_v3) — CLASSIC long-horizon momentum, for BULL regimes.

Spec intent: rank stocks with strong 6-12 month trends — the persistent winners — and
hold them for a quarter while the trend runs.

Why v3 exists: momentum_v2 keyed off a 10-day move and FAILED (IC -0.027) — at short
horizons momentum REVERTS (you chase the top tick). Classic momentum lives at MONTHS.
Full-sample cross-sectional IC (monthly panel, ^NSEI<200dMA regime split):
    trailing  -> 20d-fwd   -> 60d-fwd
    12mo (252d)  +0.023        +0.075   <- the edge, BULL
    6mo  (126d)  +0.003        +0.044
(bear: -0.04 to -0.08 — classic momentum crash, so BULL-ONLY).

v3 is minimal — two trend factors, no confirmation noise:
    momentum_12m (0.70) — 252d trailing return: the dominant signal
    momentum_6m  (0.30) — 126d trailing return: shorter-trend confirmation

Higher score = stronger durable trend = higher rank = BUY (bull/trending regimes only).
IMPORTANT: the edge needs a ~QUARTER (≈60-trading-day) HOLD — pair with a long-horizon
exit; a 2-day churn captures none of it. Re-calibrate via scripts/signal_ic.sql.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.constants import (
    RANKING_STRATEGY_MOMENTUM_V3,
    RANKING_STRATEGY_MOMENTUM_V3_VERSION,
)
from app.ranking.math_utils import PriceBar, bars_on_or_before, total_return
from app.ranking.models import FactorScore, quantize_component, quantize_score
from app.ranking.strategy import RankingStrategy, StrategyRequirements
from app.universe.models import StockSnapshot

MOM_LONG = 252   # 12-month trend (the dominant signal)
MOM_MID = 126    # 6-month trend (confirmation)
HISTORY_DAYS = MOM_LONG + 5

DEFAULT_WEIGHTS: dict[str, Decimal] = {
    "momentum_12m": Decimal("0.70"),
    "momentum_6m": Decimal("0.30"),
}


class MomentumV3Strategy:
    name = RANKING_STRATEGY_MOMENTUM_V3
    version = RANKING_STRATEGY_MOMENTUM_V3_VERSION

    FACTOR_MOM_12M = "momentum_12m"
    FACTOR_MOM_6M = "momentum_6m"

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
            self.FACTOR_MOM_12M: self._trend(bars, MOM_LONG),
            self.FACTOR_MOM_6M: self._trend(bars, MOM_MID),
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

    def _trend(self, bars: list[PriceBar], lookback: int) -> Decimal | None:
        """Trailing return over ``lookback`` — higher = stronger durable trend."""
        r = total_return(bars, lookback)
        return quantize_component(r) if r is not None else None


def build_momentum_v3_strategy(weights: dict[str, Decimal] | None = None) -> RankingStrategy:
    return MomentumV3Strategy(weights=weights)
