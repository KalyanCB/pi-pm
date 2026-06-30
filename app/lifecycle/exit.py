"""Lifecycle EXIT logic — the cross-rank HANDOFF.

A position is ENTERED on the new setup rank (breakout_v2 / reversion_v3), but EXITED on
the OLD/active rank — because the setup rank fades *by design* the moment the move
works (vol expands, the base resolves), so it's a false sell signal. The handoff:

    entered on breakout_v2  -> exit on breakout_v1 (B1) FADE   (the active break is spent)
    entered on reversion_v3 -> exit on reversal_v1 (RV1) RECOVERY (no longer oversold)

These are PURE decision functions over a position's *current* percentile in the handoff
strategy (percentile = (pool-rank)/(pool-1), high = strong). They cover only the
rank handoff; the legacy regime exit, hard stop and trailing stop stay as the existing
exit_monitor triggers (per the "use the old one" rule). No DB, no side effects.
"""
from __future__ import annotations

from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_BREAKOUT_V2,
    RANKING_STRATEGY_BREAKOUT_V3_BROAD,
    RANKING_STRATEGY_BREAKOUT_V3_DEF,
    RANKING_STRATEGY_MOMENTUM_V3,
    RANKING_STRATEGY_REVERSAL_V1,
    RANKING_STRATEGY_REVERSION_V3,
)

# entry strategy -> the OLD/active strategy whose rank governs the EXIT (the handoff).
LIFECYCLE_EXIT_RANK_STRATEGY: dict[str, str] = {
    RANKING_STRATEGY_BREAKOUT_V2: RANKING_STRATEGY_BREAKOUT_V1,    # B2 in, B1 exits
    RANKING_STRATEGY_REVERSION_V3: RANKING_STRATEGY_REVERSAL_V1,   # R1 in, RV1 exits
}

# 2nd-leg handoff: once the breakout (B1) is spent, ride MOMENTUM (M3) before exiting.
# breakout_v2 -> breakout_v1 (breakout leg) -> momentum_v3 (trend leg) -> exit.
# breakout_v3 sleeves use the CONVICTION exit (not the B1 handoff), but the conviction
# score's M component still reads the position's momentum_v3 percentile via this map.
LIFECYCLE_MOMENTUM_STRATEGY: dict[str, str] = {
    RANKING_STRATEGY_BREAKOUT_V2: RANKING_STRATEGY_MOMENTUM_V3,
    RANKING_STRATEGY_BREAKOUT_V3_BROAD: RANKING_STRATEGY_MOMENTUM_V3,
    RANKING_STRATEGY_BREAKOUT_V3_DEF: RANKING_STRATEGY_MOMENTUM_V3,
}

# Thresholds (percentile, high = strong), from the validated lifecycle:
B1_SPIKE_PCT = 0.65      # the breakout has fired once B1 reaches here
B1_FADE_PCT = 0.45       # ...and is spent once B1 falls back below here
MOMENTUM_HOLD_PCT = 0.50 # while momentum_v3 is at/above this, the trend leg is ALIVE — hold
RV1_RECOVER_PCT = 0.40   # reversion done once the oversold rank drops below here
RV1_GRACE_DAYS = 5       # don't take the reversion profit before the bounce develops

EXIT_B1_FADE = "EXIT_B1_FADE"
EXIT_MOMENTUM_FADE = "EXIT_MOMENTUM_FADE"
EXIT_RV1_RECOVERED = "EXIT_RV1_RECOVERED"


def momentum_strategy(entry_strategy: str | None) -> str | None:
    """The trend-leg strategy a position rides AFTER its breakout fades (None if n/a)."""
    if not entry_strategy:
        return None
    return LIFECYCLE_MOMENTUM_STRATEGY.get(entry_strategy)


def momentum_alive(momentum_pct: float | None, hold_pct: float = MOMENTUM_HOLD_PCT) -> bool:
    """True while the stock is still a strong momentum_v3 pick — the trend leg is alive,
    so hold even though the breakout has faded. Used by the handoff exit AND the
    alpha-decay gate (don't retire a name momentum is still carrying)."""
    return momentum_pct is not None and momentum_pct >= hold_pct


def exit_rank_strategy(entry_strategy: str | None) -> str | None:
    """Which strategy's rank the EXIT reads for a position entered on ``entry_strategy``
    (the active-rank handoff). None for non-lifecycle strategies."""
    if not entry_strategy:
        return None
    return LIFECYCLE_EXIT_RANK_STRATEGY.get(entry_strategy)


def pct_from_rank(rank: int | None, pool_size: int | None) -> float | None:
    """Percentile (1.0 = rank 1 best, 0.0 = worst) from a 1-based rank in a pool."""
    if rank is None or not pool_size or pool_size <= 1:
        return None
    return (pool_size - rank) / (pool_size - 1)


def b1_has_peaked(handoff_pct: float | None, spike_pct: float = B1_SPIKE_PCT) -> bool:
    """True once B1 has spiked (the breakout fired). Callers OR this across days and
    pass the result back as ``has_peaked`` — the fade exit only arms after a spike."""
    return handoff_pct is not None and handoff_pct >= spike_pct


def should_exit_on_handoff(
    *,
    entry_strategy: str | None,
    handoff_pct: float | None,
    has_peaked: bool = False,
    days_held: int = 0,
    momentum_pct: float | None = None,
    b1_fade_pct: float = B1_FADE_PCT,
    rv1_recover_pct: float = RV1_RECOVER_PCT,
    rv1_grace_days: int = RV1_GRACE_DAYS,
    momentum_hold_pct: float = MOMENTUM_HOLD_PCT,
) -> tuple[bool, str | None]:
    """Lifecycle rank-handoff exit. ``handoff_pct`` is the position's CURRENT percentile
    in the handoff strategy (breakout_v1 / reversal_v1). Returns (exit?, reason).

    - breakout_v2 position (two-leg handoff): ride breakout_v1 (the breakout); once it has
      spiked AND faded (B1 < fade) the breakout is spent — HAND OFF to momentum_v3. While
      ``momentum_pct`` keeps the trend leg ALIVE, HOLD (ride the move); exit only when
      momentum has ALSO faded -> EXIT_MOMENTUM_FADE. A breakout that never fired is left to
      the stop, not cut here. (2021 audit: B1-fade exits left +20-35% on the table.)
    - reversion_v3 position: exit when the stock has RECOVERED out of the oversold zone
      (RV1 < recover), after a short grace so the bounce can develop.
    """
    if entry_strategy == RANKING_STRATEGY_BREAKOUT_V2:
        if has_peaked and handoff_pct is not None and handoff_pct < b1_fade_pct:
            # Breakout spent -> momentum leg. Hold while momentum is alive; else exit.
            if momentum_alive(momentum_pct, momentum_hold_pct):
                return False, None
            return True, EXIT_MOMENTUM_FADE
    elif entry_strategy == RANKING_STRATEGY_REVERSION_V3:
        if (
            days_held >= rv1_grace_days
            and handoff_pct is not None
            and handoff_pct < rv1_recover_pct
        ):
            return True, EXIT_RV1_RECOVERED
    return False, None
