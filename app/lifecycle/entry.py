"""Lifecycle ENTRY logic — regime-aware sleeve routing + per-stock entry gate.

Validated on the lifecycle research (true-net, 2021-26): enter on the early/SETUP rank,
gated by the 3-way NIFTY regime AND the stock's own trend:

    BULL      -> breakout_v2  (the coil) — require the stock in its OWN uptrend
    BEAR      -> reversion_v3 (the fresh 20d washout) — the crushed-in-bear bounce
    SIDEWAYS  -> sit out (cash) — both breakouts and reversions whipsaw in chop

A stock enters if it is in the top ``entry_top_pct`` of the regime's entry strategy
(percentile = rank / pool_size) and clears the stock-trend gate. Pure functions — no
DB, no side effects — so they unit-test trivially and slot into the recommendation /
paper-pilot buy loop.
"""
from __future__ import annotations

from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V2,
    RANKING_STRATEGY_REVERSION_V3,
)
from app.validation.constants import (
    TREND_REGIME_BEAR,
    TREND_REGIME_BULL,
    TREND_REGIME_SIDEWAYS,
)

# 3-way regime -> the strategy whose top ranks we ENTER. None = sit out (cash).
LIFECYCLE_ENTRY_STRATEGY: dict[str, str | None] = {
    TREND_REGIME_BULL: RANKING_STRATEGY_BREAKOUT_V2,
    TREND_REGIME_BEAR: RANKING_STRATEGY_REVERSION_V3,
    TREND_REGIME_SIDEWAYS: None,
}

# Top fraction of the entry strategy treated as buy candidates (b2/r1 >= 0.80).
DEFAULT_ENTRY_TOP_PCT = 0.20


def entry_strategy_for_regime(market_regime_3way: str | None) -> str | None:
    """Which strategy to ENTER on for the given 3-way market regime; None = cash
    (SIDEWAYS, or unknown regime)."""
    if not market_regime_3way:
        return None
    return LIFECYCLE_ENTRY_STRATEGY.get(market_regime_3way)


def is_top_pick(rank: int | None, pool_size: int | None, top_pct: float) -> bool:
    """True if ``rank`` is within the top ``top_pct`` of ``pool_size`` (percentile
    >= 1-top_pct). Ranks are 1-based (rank 1 = best)."""
    if rank is None or not pool_size or pool_size <= 0:
        return False
    return rank <= max(1, round(top_pct * pool_size))


def should_enter(
    *,
    strategy: str,
    market_regime_3way: str | None,
    stock_trend_3way: str | None,
    rank: int | None,
    pool_size: int | None,
    entry_top_pct: float = DEFAULT_ENTRY_TOP_PCT,
    top_rank: int = 0,
) -> bool:
    """Per-stock entry gate for the lifecycle. True => BUY this stock today.

    ``strategy`` is the strategy that produced ``rank`` for the stock (the candidate's
    entry sleeve). The stock enters only if that sleeve is the regime's entry sleeve,
    the stock is a top pick, and the stock-trend gate passes.
    """
    # 1. Is this the regime's entry sleeve? (BULL->breakout_v2, BEAR->reversion_v3,
    #    SIDEWAYS->cash -> nothing matches -> no entry.)
    if entry_strategy_for_regime(market_regime_3way) != strategy:
        return False

    # 2. Top pick? An absolute rank cap (top_rank>0, e.g. top-5 bucket) takes precedence
    #    over the percentile gate when set.
    if top_rank > 0:
        if rank is None or rank > top_rank:
            return False
    elif not is_top_pick(rank, pool_size, entry_top_pct):
        return False

    # 3. Stock-trend gate.
    if strategy == RANKING_STRATEGY_BREAKOUT_V2:
        # A breakout needs the stock in its OWN uptrend — don't "break out" a
        # downtrending/sideways name (those are the failed-breakout losers).
        return stock_trend_3way == TREND_REGIME_BULL
    if strategy == RANKING_STRATEGY_REVERSION_V3:
        # Reversion buys the crushed in a bear; the stock is down by design, so no
        # uptrend requirement — but skip a name still in a confirmed uptrend (not
        # actually washed out).
        return stock_trend_3way != TREND_REGIME_BULL

    return True
