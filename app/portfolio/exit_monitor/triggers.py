"""Exit trigger definitions — pure functions, no DB access.

Each trigger takes position context and returns (fired: bool, details: dict).
All deterministic. No LLM.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerResult:
    fired: bool
    trigger_code: str
    details: dict
    urgency: str = "NORMAL"  # LOW | NORMAL | HIGH | CRITICAL


def check_rank_drop(
    current_rank: int | None,
    entry_rank: int | None,
    rank_deterioration_threshold: int = 40,
    entry_rank_threshold: int = 20,
) -> TriggerResult:
    """EXIT_RANK_DROP: rank fell below absolute threshold OR deteriorated 20+ from entry (P-07)."""
    if current_rank is None:
        return TriggerResult(False, "EXIT_RANK_DROP", {})
    # Absolute threshold (safety net)
    absolute_breach = current_rank > rank_deterioration_threshold
    # P-07: relative deterioration — high-conviction entry that silently degraded
    relative_breach = (
        entry_rank is not None and current_rank > entry_rank + 20
    )
    fired = absolute_breach or relative_breach
    urgency = "HIGH" if current_rank > 60 else "NORMAL"
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_RANK_DROP",
        details={
            "current_rank": current_rank,
            "threshold": rank_deterioration_threshold,
            "entry_rank": entry_rank,
            "absolute_breach": absolute_breach,
            "relative_breach": relative_breach,
        },
        urgency=urgency,
    )


def check_alpha_decay(
    cum_alpha_at_day: float | None,
    days_held: int,
    decay_threshold_day: int = 15,
    decay_min_alpha: float = 0.0,
) -> TriggerResult:
    """EXIT_ALPHA_DECAY: cumulative alpha turned negative before decay_threshold_day (R-EXIT-02)."""
    if cum_alpha_at_day is None:
        return TriggerResult(False, "EXIT_ALPHA_DECAY", {})
    fired = days_held <= decay_threshold_day and cum_alpha_at_day < decay_min_alpha
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_ALPHA_DECAY",
        details={
            "cum_alpha_pct": cum_alpha_at_day,
            "days_held": days_held,
            "decay_threshold_day": decay_threshold_day,
        },
        urgency="HIGH" if fired else "NORMAL",
    )


def check_regime_change(
    current_regime_posture: str,
    entry_regime_posture: str | None,
    unrealized_pnl_pct: float | None = None,
    current_rank: int | None = None,
    entry_pool_size: int = 20,
    own_trend_intact: bool | None = None,
    per_stock_trend_hold: bool = False,
    intra_bear_hold: bool = True,
    market_regime_3way: str | None = None,
    stock_trend_3way: str | None = None,
    hold_through_sideways: bool = False,
) -> TriggerResult:
    """EXIT_REGIME: regime turned defensive or crisis (R-EXIT-03).

    Lifecycle 3-way mode (``hold_through_sideways`` + ``market_regime_3way`` given):
    the legacy 4-way regime whipsaws BULL<->BEAR through chop, market-selling winners
    that then recover (2021 audit: PAGEIND +17% / PGHH/ZFCVINDIA +7-10% left after a
    regime cut). So judge the exit on the *3-way* regime instead — HOLD through every
    SIDEWAYS bar, exit only on a CONFIRMED BEAR, and even then keep a name whose OWN
    trend is still BULL (ride the strong stock in a weak tape). ``crisis`` still always
    exits (systemic). Legacy path is unchanged when the 3-way inputs aren't supplied.

    P-20: make the regime exit *selective* rather than a blanket liquidation.
    A defensive flip previously sold every open position regardless of the
    individual stock's trend — dumping still-trending winners alongside laggards
    (mean post-exit +7.7% vs +2.4% market). Now:

      - ``crisis``    → always exit (capital preservation dominates).
      - ``defensive`` → exit only positions *also* showing individual weakness
                        (negative P&L, or rank fallen out of the entry pool).
                        A position still ranked and in profit is held; the
                        regime signal throttles new buying / tightens stops
                        elsewhere instead of market-selling a working winner.

    Hybrid (per-stock) regime — ``per_stock_trend_hold`` (flag-gated, off by
    default): the market posture is a BOOK-level signal, so a defensive flip
    should not market-sell a name whose *own* trend is intact merely because its
    relative rank slipped. When enabled and ``own_trend_intact`` (close above its
    own fast & slow SMA) and the position is not losing money, it is HELD through
    a *defensive* flip — only genuine per-stock weakness (negative P&L) still
    exits. ``crisis`` is unaffected (systemic crash → always exit). Evidence
    (2026-06): blanket regime-cuts of own-uptrend names beat NIFTY +2.35%/10d.
    """
    if current_regime_posture == "crisis":
        fired = True
    elif hold_through_sideways and market_regime_3way is not None:
        # Lifecycle 3-way: hold through SIDEWAYS; exit only on confirmed BEAR, and keep
        # a stock whose own trend is still BULL.
        fired = (market_regime_3way == "BEAR" and stock_trend_3way != "BULL")
    elif current_regime_posture == "defensive":
        weak_pnl = unrealized_pnl_pct is not None and unrealized_pnl_pct < 0
        weak_rank = current_rank is not None and current_rank > entry_pool_size
        # Intra-bear churn fix: a position ENTERED already in a defensive (bear /
        # high-vol) regime was made *for* that regime (e.g. reversal_v1 in
        # BEAR_LOW_VOL). A defensive re-flip within the same bear must not re-cut it —
        # bear->bear was 76% of EXIT_REGIME exits, 57% of them winners, +1.2% post-exit
        # drift. Hold through intra-bear re-flips; only genuine per-stock P&L weakness
        # exits. crisis still always exits (above); bull->bear keeps the full logic.
        entered_defensive = entry_regime_posture == "defensive"
        # If we have no per-position signal at all, fall back to exiting (safe default).
        if unrealized_pnl_pct is None and current_rank is None:
            fired = True
        elif intra_bear_hold and entered_defensive:
            # Entered defensive AND still defensive == NO regime change (a genuine
            # escalation to `crisis` already exited above). EXIT_REGIME is a regime-
            # *change* signal, so within an unchanged bear it must NOT fire. The old
            # `fired = weak_pnl` made this a 0%-threshold daily stop, guillotining
            # transient dips: 218 BEAR_LOW cuts sold at -0.9% then drifted +2.3%/10d
            # (60% recovered). Hold through the intra-bear noise; genuine failures are
            # caught by stop-loss (-2% in defensive) / rank-drop / alpha-decay.
            fired = False
        elif per_stock_trend_hold and own_trend_intact and not weak_pnl:
            # Own trend intact + not losing → hold through the defensive flip; a
            # mere relative rank-slip no longer forces a market-sell of a winner.
            fired = False
        else:
            fired = weak_pnl or weak_rank
    else:
        fired = False
    urgency = "CRITICAL" if current_regime_posture == "crisis" else ("HIGH" if fired else "NORMAL")
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_REGIME",
        details={
            "current_posture": current_regime_posture,
            "entry_posture": entry_regime_posture,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "current_rank": current_rank,
            "own_trend_intact": own_trend_intact,
            "per_stock_trend_hold": per_stock_trend_hold,
            "market_regime_3way": market_regime_3way,
            "stock_trend_3way": stock_trend_3way,
        },
        urgency=urgency,
    )


def check_time_stop(
    days_held: int,
    max_holding_days: int = 30,
) -> TriggerResult:
    """EXIT_TIME: holding period exceeded swing horizon (R-EXIT-04)."""
    fired = days_held >= max_holding_days
    urgency = "HIGH" if days_held >= max_holding_days + 5 else ("NORMAL" if fired else "LOW")
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_TIME",
        details={"days_held": days_held, "max_holding_days": max_holding_days},
        urgency=urgency,
    )


def check_stop_loss(
    unrealized_pnl_pct: float | None,
    stop_loss_pct: float = -8.0,
) -> TriggerResult:
    """EXIT_STOP_LOSS: position lost more than stop_loss_pct."""
    if unrealized_pnl_pct is None:
        return TriggerResult(False, "EXIT_STOP_LOSS", {})
    fired = unrealized_pnl_pct <= stop_loss_pct
    urgency = (
        "CRITICAL" if unrealized_pnl_pct <= stop_loss_pct * 1.5 else ("HIGH" if fired else "NORMAL")
    )
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_STOP_LOSS",
        details={"unrealized_pnl_pct": unrealized_pnl_pct, "stop_loss_pct": stop_loss_pct},
        urgency=urgency,
    )


def _trailing_pct(max_gain_pct: float) -> float:
    """Profit-ladder trailing stop — wider trail as gains grow. Tuned to bank the quick
    pops (tight low tiers — the <60d give-back fix) while NOT shaking out multibaggers
    (very wide top tiers — a +90% name routinely breathes 20%+)."""
    if max_gain_pct >= 100.0:
        return 25.0   # multibagger — ride it, don't get shaken out on a normal correction
    if max_gain_pct >= 60.0:
        return 20.0
    if max_gain_pct >= 35.0:
        return 15.0
    if max_gain_pct >= 20.0:
        return 11.0
    if max_gain_pct >= 10.0:
        return 7.0    # tightened from 8 — capture the +10-20% pops we were round-tripping
    return 5.0


def check_trailing_stop(
    unrealized_pnl_pct: float | None,
    max_gain_pct: float | None,
    trailing_stop_pct: float = 5.0,
) -> TriggerResult:
    """EXIT_TRAILING_STOP: position pulled back from peak (P-02 dynamic ladder + P-03 profit lock)."""
    if unrealized_pnl_pct is None or max_gain_pct is None or max_gain_pct <= 0:
        return TriggerResult(False, "EXIT_TRAILING_STOP", {})

    # P-02: dynamic trail based on peak gain
    effective_trail = _trailing_pct(max_gain_pct)
    drawback = max_gain_pct - unrealized_pnl_pct

    # Hard profit floor — engages earlier (15%) so the long winners that round-tripped
    # keep half their peak; on a multibagger (>=60%) lock 65% so a +400% name banks >=+260%.
    if max_gain_pct >= 60.0:
        profit_floor = max_gain_pct * 0.65
    elif max_gain_pct >= 15.0:
        profit_floor = max_gain_pct * 0.50
    else:
        profit_floor = None
    exit_level = max_gain_pct - effective_trail
    if profit_floor is not None:
        exit_level = max(exit_level, profit_floor)

    fired = (
        drawback >= effective_trail and max_gain_pct >= effective_trail
    ) or (
        profit_floor is not None and unrealized_pnl_pct < profit_floor
    )
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_TRAILING_STOP",
        details={
            "max_gain_pct": max_gain_pct,
            "current_pnl_pct": unrealized_pnl_pct,
            "drawback_pct": round(drawback, 2),
            "effective_trail_pct": effective_trail,
            "profit_floor_pct": profit_floor,
            "exit_level_pct": round(exit_level, 2),
        },
        urgency="HIGH" if fired else "NORMAL",
    )


def check_concentration(
    weight_pct: float | None,
    single_name_cap_pct: float = 18.0,
) -> TriggerResult:
    """EXIT_CONCENTRATION: position weight exceeds single-name cap."""
    if weight_pct is None:
        return TriggerResult(False, "EXIT_CONCENTRATION", {})
    fired = weight_pct > single_name_cap_pct
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_CONCENTRATION",
        details={"weight_pct": weight_pct, "cap_pct": single_name_cap_pct},
        urgency="HIGH" if weight_pct > single_name_cap_pct * 1.2 else "NORMAL",
    )


def check_liquidity(
    avg_daily_volume: float | None,
    position_value: float | None,
    last_price: float | None = None,
    liquidity_days_threshold: float = 5.0,
) -> TriggerResult:
    """EXIT_LIQUIDITY: position would take too many days to unwind at average volume.

    P-19: ``days_to_unwind`` is position value (₹) divided by *daily value traded* (₹),
    i.e. ``avg_daily_volume`` (shares) × ``last_price`` (₹). Dividing ₹ by raw share
    volume (the previous behaviour) was dimensionally wrong — the metric scaled with
    share price, so a rising winner looked progressively "more illiquid" and self-
    triggered a daily exit, force-selling the strategy's biggest multibaggers.
    """
    if avg_daily_volume is None or position_value is None or avg_daily_volume <= 0:
        return TriggerResult(False, "EXIT_LIQUIDITY", {})
    # Daily traded value in ₹; fall back to share-volume only if price unavailable.
    daily_traded_value = avg_daily_volume * last_price if last_price else avg_daily_volume
    if daily_traded_value <= 0:
        return TriggerResult(False, "EXIT_LIQUIDITY", {})
    days_to_unwind = position_value / daily_traded_value
    fired = days_to_unwind > liquidity_days_threshold
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_LIQUIDITY",
        details={
            "days_to_unwind": round(days_to_unwind, 1),
            "threshold_days": liquidity_days_threshold,
            "avg_daily_volume": avg_daily_volume,
        },
        urgency="HIGH" if fired else "NORMAL",
    )
