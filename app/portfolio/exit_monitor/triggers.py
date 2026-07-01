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
    """Profit-ladder trailing stop — WIDENED (2026 give-back audit: 93% of trailing
    exits ran further, avg +11.5% left on the table, even the 60%+ tier leaked +18%).
    Below the activation floor the stop is DISARMED entirely (hard stop only); once armed,
    give names real room — they routinely breathe 20%+. Tiers apply only to peaks ≥ the
    activation threshold (default 18%), so the lower tiers exist just as a safety floor."""
    if max_gain_pct >= 100.0:
        return 35.0   # multibagger — wide; a +200% name swings 30%+ without breaking trend
    if max_gain_pct >= 60.0:
        return 30.0
    if max_gain_pct >= 35.0:
        return 22.0
    return 18.0       # 18-35% armed tier — let it establish a trend, don't clip the noise


def check_trailing_stop(
    unrealized_pnl_pct: float | None,
    max_gain_pct: float | None,
    trailing_stop_pct: float = 5.0,
    min_activation_pct: float = 0.0,
) -> TriggerResult:
    """EXIT_TRAILING_STOP: position pulled back from peak (P-02 dynamic ladder + P-03 profit lock).

    ``min_activation_pct``: don't trail until the position has peaked at least this much.
    Fat-tail protection — a small breakout rides the hard stop only, so a routine pullback
    can't clip it near breakeven before it runs (audit: +8-13% peaks gave back to ~0 then
    ran +15-33%)."""
    if unrealized_pnl_pct is None or max_gain_pct is None or max_gain_pct <= 0:
        return TriggerResult(False, "EXIT_TRAILING_STOP", {})
    if max_gain_pct < min_activation_pct:
        return TriggerResult(False, "EXIT_TRAILING_STOP", {})

    # P-02: dynamic trail based on peak gain
    effective_trail = _trailing_pct(max_gain_pct)
    drawback = max_gain_pct - unrealized_pnl_pct

    # Hard profit floor — RAISED band so winners keep more of the peak alongside the wider
    # trail: a +400% multibagger banks >=+260% (0.65), a +44% name keeps >=+24% (0.55).
    if max_gain_pct >= 60.0:
        profit_floor = max_gain_pct * 0.65
    elif max_gain_pct >= 35.0:
        profit_floor = max_gain_pct * 0.55
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


def check_stall(
    days_held: int,
    unrealized_pnl_pct: float | None,
    momentum_rising: bool | None = None,
    grace_days: int = 60,
    slope_floor_pct_per_day: float = 0.12,
) -> TriggerResult:
    """EXIT_STALL: a long-held position that fails to COMPOUND — realized slope
    (gain%/day) below the floor after a grace window. Catches the 'dragging momentum'
    blind spot: not a loss (no stop fires) and momentum technically alive (no handoff
    exit), but dead money hogging a slot below the hurdle (VPS: such names ate ~38% of
    slot-days for ~+13% avg, vs +139% for the >=0.20/day winners).

    Guards that spare real holds: (1) grace window — never fires early; (2) slope, not
    level — a big-but-fast gain clears the floor, only FLAT holds fail; (3) momentum_rising
    — spare a flat name whose momentum is still building (coiling for a move)."""
    if unrealized_pnl_pct is None or days_held < grace_days:
        return TriggerResult(False, "EXIT_STALL", {})
    slope = unrealized_pnl_pct / days_held
    fired = slope < slope_floor_pct_per_day and momentum_rising is not True
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_STALL",
        details={
            "days_held": days_held,
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
            "slope_pct_per_day": round(slope, 4),
            "slope_floor_pct_per_day": slope_floor_pct_per_day,
            "grace_days": grace_days,
            "momentum_rising": momentum_rising,
        },
        urgency="NORMAL" if fired else "LOW",
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


def breakout_conviction_score(
    momentum_pct: float | None,
    market_label: str | None,
    stock_below_sma: int,
    rsi14: float | None,
) -> tuple[int, dict]:
    """Exit conviction score (0-115) for a breakout_v2 position — higher = more
    pressure to exit. Four INDEPENDENT signals (the redundant ones — market-tier
    granularity, RS-vs-benchmark — were tested and added nothing):

      M momentum_v3 percentile (RELATIVE rank, 1.0=best): >=.50→0 .40→15 .30→30 .20→40 <.20→50
      K market regime (4-way vol label): BULL_LOW→0 BULL_HIGH(fading)→10 BEAR_LOW→15 BEAR_HIGH→30
      S stock vs own 200-SMA (0 above / 1 below / 2 >10% below): →0 / 10 / 20
      R RSI(14) — own ABSOLUTE thrust (independent of M's relative rank): >=50→0 40→5 30→10 <30→15
    """
    if momentum_pct is None or momentum_pct >= 0.50:
        m = 0
    elif momentum_pct >= 0.40:
        m = 15
    elif momentum_pct >= 0.30:
        m = 30
    elif momentum_pct >= 0.20:
        m = 40
    else:
        m = 50

    lab = (market_label or "").upper()
    if "BEAR_HIGH" in lab:
        k = 30
    elif "BEAR" in lab:
        k = 15
    elif "BULL_HIGH" in lab:
        k = 10  # fading bull (high vol in an uptrend = topping)
    else:
        k = 0

    s = {2: 20, 1: 10}.get(stock_below_sma, 0)

    if rsi14 is None or rsi14 >= 50:
        r = 0
    elif rsi14 >= 40:
        r = 5
    elif rsi14 >= 30:
        r = 10
    else:
        r = 15

    return m + k + s + r, {"M": m, "K": k, "S": s, "R": r}


def check_breakout_conviction_exit(
    momentum_pct: float | None,
    market_label: str | None,
    stock_below_sma: int,
    rsi14: float | None,
    drag_from_peak_pct: float | None,
    below_entry: bool,
    low_score_drag_pct: float = 40.0,
    mid_score_drag_pct: float = 25.0,
    tight_drag_pct: float = 12.0,
) -> TriggerResult:
    """EXIT_CONVICTION: the consolidated breakout_v2 exit. A daily conviction score IS
    the trail/stop — the leash tightens as exit conviction rises:

        E >= 80        → EXIT now
        60 <= E < 80   → EXIT if drag-from-peak > tight   OR position below entry
        40 <= E < 60   → EXIT if drag-from-peak > mid
        E < 40         → EXIT if drag-from-peak > low      (widest patience while healthy)

    ``drag_from_peak_pct`` is the % drawdown from the peak CLOSE since entry (0..100).
    No separate fixed stop / trailing / momentum-fade — they are all subsumed here; the
    gap-down tail is handled by a wide catastrophe stop outside this score."""
    score, comp = breakout_conviction_score(
        momentum_pct, market_label, stock_below_sma, rsi14
    )
    drag = drag_from_peak_pct if drag_from_peak_pct is not None else 0.0
    if score >= 80:
        fired, rule = True, "score>=80"
    elif score >= 60:
        fired = drag > tight_drag_pct or bool(below_entry)
        rule = "60-80:drag>tight|below_entry"
    elif score >= 40:
        fired = drag > mid_score_drag_pct
        rule = "40-60:drag>mid"
    else:
        fired = drag > low_score_drag_pct
        rule = "<40:drag>low"
    urgency = "HIGH" if score >= 80 else ("NORMAL" if fired else "LOW")
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_CONVICTION",
        details={
            "score": score,
            **comp,
            "drag_from_peak_pct": round(drag, 2),
            "below_entry": bool(below_entry),
            "momentum_pct": round(momentum_pct, 3) if momentum_pct is not None else None,
            "rsi14": round(rsi14, 1) if rsi14 is not None else None,
            "market_label": market_label,
            "stock_below_sma": stock_below_sma,
            "rule": rule,
        },
        urgency=urgency,
    )


def check_slot_recycle(
    recent_slope_pct_per_day: float | None,
    days_held: int,
    momentum_rising: bool | None = None,
    grace_days: int = 75,
    slope_floor_pct_per_day: float = 0.12,
    spare_momentum_rising: bool = True,
) -> TriggerResult:
    """EXIT_SLOT_RECYCLE — PASS 2 of the breakout_v2 gauntlet (slot efficiency). A
    position that has survived the conviction (health) pass but whose RECENT velocity
    has stalled (recent slope < floor after a grace window) is dead money clogging a
    slot a fresh setup could compound — recycle it.

    Uses RECENT slope (last N trading days), not since-entry, so a banked winner that's
    still drifting up keeps its slot while genuine draggers (e.g. +35% over 2yr ≈
    0.05%/day) are freed. The momentum-rising guard spares a coiling name about to break.
    Opportunity-blind by design (Pass 3 adds the opportunity test); set the floor to the
    engine's hurdle (≈0.12%/day ≈ 30%/yr)."""
    if recent_slope_pct_per_day is None or days_held < grace_days:
        return TriggerResult(False, "EXIT_SLOT_RECYCLE", {})
    fired = recent_slope_pct_per_day < slope_floor_pct_per_day
    if fired and spare_momentum_rising and momentum_rising is True:
        fired = False
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_SLOT_RECYCLE",
        details={
            "recent_slope_pct_per_day": round(recent_slope_pct_per_day, 3),
            "slope_floor_pct_per_day": slope_floor_pct_per_day,
            "days_held": days_held,
            "grace_days": grace_days,
            "momentum_rising": momentum_rising,
        },
        urgency="NORMAL" if fired else "LOW",
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


def check_proximity_break_exit(
    proximity: float | None,
    drag_from_peak_pct: float | None,
    prox_floor: float,
    peak_drop_pct: float,
) -> TriggerResult:
    """EXIT_PROXIMITY_BREAK — the def-sleeve exit (NO momentum term). def buys low-vol
    names holding near their 52-week high; the thesis is "hold quality near the high".
    So it exits only when the stock LEAVES that zone:
      * proximity (close / 252d-high) falls below ``prox_floor`` (e.g. 0.85), OR
      * it gives back ``peak_drop_pct`` from its own peak close since entry (wide trail).
    This replaces the momentum-based conviction gauntlet for def, which cut the calm
    low-vol names precisely when their (already low) momentum faded."""
    prox_break = proximity is not None and proximity < prox_floor
    peak_break = drag_from_peak_pct is not None and drag_from_peak_pct >= peak_drop_pct
    return TriggerResult(
        fired=prox_break or peak_break,
        trigger_code="EXIT_PROXIMITY_BREAK",
        details={
            "proximity": proximity,
            "prox_floor": prox_floor,
            "drag_from_peak_pct": drag_from_peak_pct,
            "peak_drop_pct": peak_drop_pct,
            "reason": "prox_break" if prox_break else ("peak_drop" if peak_break else None),
        },
        urgency="HIGH" if (prox_break or peak_break) else "NORMAL",
    )
