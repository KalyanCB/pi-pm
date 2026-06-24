"""Anti-Momentum Reversal Strategy v1 (reversal_v1).

Designed for BEAR_LOW_VOL regime.

Research basis (docs/research/BEAR_LOW_VOL_STRATEGIES.md):
  The bottom quintile (Q5) of breakout_v1 in BEAR_LOW_VOL returns +2.85% per
  20d (Sharpe 0.251) vs Q1 +0.73% (Sharpe 0.065). Q5 characteristics:
    - Weakest relative strength vs benchmark
    - Worst 63d momentum (most fallen stocks)
    - Far from 52-week high (deeply oversold)
    - Low recent volume (not yet crowded)

  These are oversold stocks that mean-revert during bear-low-vol phases when
  panic selling exhausts and capital rotates into beaten-down names.

Factor composition (all INVERSE of breakout signals):
  anti_momentum     (0.35) — inverse 63d return: worst recent performers rank highest
  anti_rs           (0.30) — inverse relative strength vs NIFTY: most underperforming vs index
  low_proximity     (0.25) — proximity to 52w LOW (not high): deepest drawdown ranks highest
  low_volume_surge  (0.10) — inverse volume surge: low recent volume vs avg (not crowded)

Higher score = more oversold = higher rank = BUY candidate in BEAR_LOW_VOL.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.constants import (
    RANKING_STRATEGY_REVERSAL_V1,
    RANKING_STRATEGY_REVERSAL_V1_VERSION,
)
from app.ranking.math_utils import (
    PriceBar,
    annualized_volatility,
    average_volume,
    bars_on_or_before,
    rolling_min_close,
    simple_moving_average,
    total_return,
)
from app.ranking.models import FactorScore, quantize_component, quantize_score
from app.ranking.strategy import RankingStrategy, StrategyRequirements
from app.universe.models import StockSnapshot

MOMENTUM_LOOKBACK = 63       # same as breakout_v1
VOLUME_SHORT = 20
VOLUME_LONG = 50
LOW_52W = 252                # 52-week low window
MA_LONG = 200
MIN_VOL = Decimal("0.001")
MIN_PRICE = Decimal("0.001")

HISTORY_DAYS = max(MA_LONG + 1, LOW_52W + 1, MOMENTUM_LOOKBACK + 1)  # 253

DEFAULT_WEIGHTS: dict[str, Decimal] = {
    "anti_momentum":    Decimal("0.35"),
    "anti_rs":          Decimal("0.30"),
    "low_proximity":    Decimal("0.25"),
    "low_volume_surge": Decimal("0.10"),
}


class ReversalV1Strategy:
    name = RANKING_STRATEGY_REVERSAL_V1
    version = RANKING_STRATEGY_REVERSAL_V1_VERSION

    FACTOR_ANTI_MOMENTUM    = "anti_momentum"
    FACTOR_ANTI_RS          = "anti_rs"
    FACTOR_LOW_PROXIMITY    = "low_proximity"
    FACTOR_LOW_VOLUME_SURGE = "low_volume_surge"

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
            self.FACTOR_ANTI_MOMENTUM:    self._anti_momentum(bars),
            self.FACTOR_ANTI_RS:          None,
            self.FACTOR_LOW_PROXIMITY:    self._low_proximity(bars),
            self.FACTOR_LOW_VOLUME_SURGE: self._low_volume_surge(bars),
        }
        if benchmark_series is not None:
            bench = bars_on_or_before(benchmark_series, as_of_date)
            factors[self.FACTOR_ANTI_RS] = self._anti_rs(bars, bench)
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
        return quantize_score(
            sum((fs.weighted_contribution for fs in factor_scores), Decimal("0"))
        )

    # ── Private factor computations ──────────────────────────────────────────

    def _anti_momentum(self, bars: list[PriceBar]) -> Decimal | None:
        """Inverse 63d return — most-fallen stocks score highest."""
        ret = total_return(bars, MOMENTUM_LOOKBACK)
        if ret is None:
            return None
        # Negate: stocks with worst returns get highest positive raw score
        return quantize_component(-ret)

    def _anti_rs(
        self, stock_bars: list[PriceBar], bench_bars: list[PriceBar]
    ) -> Decimal | None:
        """Inverse relative strength vs NIFTY — weakest RS ranks highest."""
        stock_ret = total_return(stock_bars, MOMENTUM_LOOKBACK)
        bench_ret = total_return(bench_bars, MOMENTUM_LOOKBACK)
        if stock_ret is None or bench_ret is None:
            return None
        rs_spread = stock_ret - bench_ret
        return quantize_component(-rs_spread)

    def _low_proximity(self, bars: list[PriceBar]) -> Decimal | None:
        """Proximity to 52-week LOW — stocks nearest their lows rank highest.

        score = 1 - (close - 52w_low) / 52w_low
        Stocks sitting AT their 52-week low get score ≈ 1.0 (most oversold).
        """
        low_52w = rolling_min_close(bars, LOW_52W)
        if low_52w is None or low_52w <= MIN_PRICE:
            return None
        close = Decimal(str(bars[-1].close))
        if close <= 0:
            return None
        # Normalise: distance above 52w low (lower = better = nearer to bottom)
        distance = (close - low_52w) / low_52w
        # Invert so that stocks near their low score high
        # Use 1 / (1 + distance) so score in (0, 1]
        return quantize_component(Decimal("1") / (Decimal("1") + distance))

    def _low_volume_surge(self, bars: list[PriceBar]) -> Decimal | None:
        """Inverse volume surge — low recent volume vs long avg ranks highest.

        A stock with SUPPRESSED recent volume vs its long-term average is
        not yet crowded — prime for a bounce when buyers return.
        """
        short_vol = average_volume(bars, VOLUME_SHORT)
        long_vol  = average_volume(bars, VOLUME_LONG)
        if short_vol is None or long_vol is None or long_vol <= 0:
            return None
        surge = short_vol / long_vol
        if surge <= 0:
            return None
        # Invert: low surge (quiet stock) → high score
        return quantize_component(Decimal("1") / surge)


def build_reversal_v1_strategy() -> RankingStrategy:
    return ReversalV1Strategy()
