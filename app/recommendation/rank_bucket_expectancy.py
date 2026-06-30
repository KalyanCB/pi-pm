"""Rank-bucketed expectancy provider (ADR-037 P-21, altitude 3 data source).

Builds the ``(strategy, regime, rank_bucket) -> (median_forward_return, n)`` table
the TradePrioritizer orders on. Computed from historical rankings joined to realised
forward returns — the same raw material RCEE uses for IC, with a rank dimension added.

Design choices forced by the backtest:
  * **Horizon-matched** per strategy — a 3-5 day reversal signal's expectancy is
    measured at its native hold, not at 20 days (the P-18 lesson). Breakout/momentum
    use 20.
  * **Winsorized mean**, not plain mean or median. Trend/breakout payoffs are
    strongly right-skewed — most entries fizzle (median ≈ 0) while a few run big,
    so the edge *is* the right tail. A plain median would discard that edge and make
    breakout look untradeable; a plain mean lets one ASAL-type +330% dominate a
    bucket (the P-19 risk). Winsorizing returns to ±``WINSOR_CAP`` keeps the
    right-tail contribution while bounding any single outlier.
  * **Net of a round-trip cost hurdle** so expectancy is comparable to "take nothing".
  * **Bounded lookback** so the build stays cheap and reflects the recent regime.
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.recommendation.trade_prioritizer import rank_bucket

# Native holding horizon per strategy (trading days), matched to observed avg holds
# in the replay (3.9–8 days). The legacy 20-day RCEE horizon over-measured the fade
# for every strategy (the P-18 lesson) — these are all short-hold swing strategies.
STRATEGY_HORIZON: dict[str, int] = {
    "reversal_v1": 5,
    "low_vol_v1": 5,
    "breakout_v1": 10,   # winners held to rank-drop (~8d); 10 captures the run
    "momentum_v1": 10,
    # breakout_v3 holds long (conviction exit, ~quarter+ — exit-patience thesis); a 60d
    # EV horizon prioritises the candidates that carry, not the 10d pop.
    "breakout_v3_broad": 60,
    "breakout_v3_def": 60,
}
DEFAULT_HORIZON = 10

# 10 bps round-trip cost hurdle, matching RCEEConfig.cost_hurdle.
COST_HURDLE = 0.001

# Winsorization cap: clip per-trade forward returns to ±40% before averaging, so a
# single multibagger cannot dominate a bucket while the right-tail edge is retained.
WINSOR_CAP = 0.40


class RankBucketExpectancyProvider:
    """Concrete ``ExpectancyProvider``. Build once (e.g. weekly), then query in-memory."""

    def __init__(self, table: dict[tuple[str, str, str], tuple[float, int]]):
        # key: (strategy, regime, rank_bucket) -> (median_return_after_costs, n)
        self._table = table

    def expected_return(
        self,
        strategy_name: str,
        market_regime: str,
        rank_bucket_label: str,
        segment_state: str,
    ) -> tuple[float | None, int]:
        # segment_state intentionally not keyed yet — folded in once samples are deep
        # enough to support the extra dimension without going thin.
        return self._table.get((strategy_name, market_regime, rank_bucket_label), (None, 0))

    # ── Build ────────────────────────────────────────────────────────────────

    @classmethod
    def build(
        cls,
        db: Session,
        *,
        as_of_date: date,
        lookback_days: int = 504,
        source: str = "kite",
    ) -> "RankBucketExpectancyProvider":
        """Aggregate historical rankings → forward returns by (strategy, regime, bucket).

        One SQL pass: each ranked stock's entry close and its close ``horizon`` trading
        days later (via a per-stock row-number window), joined to the regime on the
        ranking date. Aggregated to a median in Python (robust to outliers).
        """
        start = as_of_date - timedelta(days=int(lookback_days * 1.6))  # cal-day pad
        # No-lookahead: only include rankings whose full forward horizon has ALREADY
        # completed by as_of_date — else the forward-return window peeks at prices in the
        # replay's future. The cutoff must cover the LONGEST strategy horizon in play
        # (trading days -> calendar via ~1.5x, +5d holiday margin). breakout_v3 uses a
        # 60-trading-day horizon (~95 cal days); the legacy hardcoded 30d only covered
        # the old ≤20-day horizons and would leak ~50 cal days for v3.
        _max_horizon_td = max(max(STRATEGY_HORIZON.values(), default=DEFAULT_HORIZON), DEFAULT_HORIZON)
        rank_cutoff = as_of_date - timedelta(days=int(_max_horizon_td * 1.5) + 5)

        rows = db.execute(
            text("""
                WITH ranked AS (
                    SELECT run.strategy_name,
                           res.rank,
                           res.stock_id,
                           run.as_of_date,
                           rh.regime_label
                    FROM recommendation_results res
                    JOIN recommendation_runs run ON run.id = res.recommendation_run_id
                    LEFT JOIN regime_history rh
                           ON rh.as_of_date = run.as_of_date
                    WHERE run.as_of_date >= :start AND run.as_of_date <= :rank_cutoff
                      AND res.rank <= 20
                )
                SELECT r.strategy_name, r.rank, r.regime_label,
                       entry.close AS entry_close,
                       fwd.close    AS fwd_close,
                       fwd.rn       AS fwd_rn
                FROM ranked r
                JOIN LATERAL (
                    SELECT close FROM market_data
                    WHERE stock_id = r.stock_id AND source = :source
                      AND date <= r.as_of_date
                    ORDER BY date DESC LIMIT 1
                ) entry ON true
                JOIN LATERAL (
                    SELECT close, ROW_NUMBER() OVER (ORDER BY date) AS rn
                    FROM market_data
                    WHERE stock_id = r.stock_id AND source = :source
                      AND date > r.as_of_date
                    ORDER BY date LIMIT 20
                ) fwd ON true
                WHERE entry.close > 0
            """),
            {"start": start, "rank_cutoff": rank_cutoff, "source": source},
        ).fetchall()

        # Collect forward returns per (strategy, regime, bucket), horizon-matched.
        buckets: dict[tuple[str, str, str], list[float]] = {}
        for r in rows:
            if r.regime_label is None:
                continue
            horizon = STRATEGY_HORIZON.get(r.strategy_name, DEFAULT_HORIZON)
            if r.fwd_rn != horizon:  # only the close exactly `horizon` days forward
                continue
            ret = (float(r.fwd_close) - float(r.entry_close)) / float(r.entry_close)
            key = (r.strategy_name, r.regime_label, rank_bucket(int(r.rank)))
            buckets.setdefault(key, []).append(ret)

        table: dict[tuple[str, str, str], tuple[float, int]] = {}
        for key, rets in buckets.items():
            if not rets:
                continue
            winsorized = [max(-WINSOR_CAP, min(WINSOR_CAP, r)) for r in rets]
            expectancy_after_costs = statistics.fmean(winsorized) - COST_HURDLE
            table[key] = (expectancy_after_costs, len(rets))
        return cls(table)
