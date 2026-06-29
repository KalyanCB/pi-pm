from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://pipm:pipm@localhost:5432/pipm"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_pre_ping: bool = True

    yahoo_request_timeout_seconds: int = 30
    market_data_default_period: str = "1y"
    # "yahoo" | "kite" — selects the OHLCV data provider for ingestion
    market_data_provider: str = "yahoo"

    ranking_default_strategy: str = "momentum_v1"
    ranking_default_strategy_version: str = "1.0.0"
    ranking_default_benchmark: str = "^NSEI"
    ranking_default_universe_code: str = "PI_PM_CORE"
    ranking_min_history_days: int = 63
    ranking_min_avg_daily_traded_value: float = 10_000_000.0
    ranking_min_stock_price: float = 50.0
    ranking_market_data_source: str = "yahoo"
    # Persist the per-stock×per-factor contribution audit table on every ranking run.
    # It's research/explainability only — the trade path reads ranking_results, never
    # this. In bulk replays it's the write bottleneck (tens of millions of rows, LWLock
    # contention across workers), so set False to skip it.
    ranking_factor_contributions_enabled: bool = True

    # ── Mega-liquidity diversifier (flag-gated, REGIME-CONDITIONAL) ───────────
    # Counter-cyclical sleeve: tilt the tradable universe to highly liquid "mega"
    # names (avg daily traded value ≥ mega_min_adtv_inr) ONLY in DEFENSIVE regimes
    # (BEAR / HIGH_VOL). The mega tier is the inverse of the smallcap-momentum book:
    # net-POSITIVE in bear (+1.0%/trade @25bps, 60% win in BEAR_LOW_VOL) where the
    # full book bleeds, but net-negative in BULL_LOW_VOL (−0.21%) where smallcaps run.
    # So in bull/neutral the full universe stands (smallcaps lead); in bear the book
    # rotates to liquid, scalable, bear-resilient mega names — a flight-to-liquidity
    # hedge alongside (or instead of) the gold sleeve. ~5 mega BUYs/day → ample
    # supply. Default OFF preserves the full universe in every regime.
    mega_diversifier_enabled: bool = False
    mega_min_adtv_inr: float = 2_000_000_000.0   # ₹200 cr avg daily traded value
    # Defensive regimes normally cap max_buy_per_day at 0 (sit in cash/gold), which
    # blocks the bear-resilient mega names from EVER being bought — gold fills the
    # slots by default (1,880 mega BUY recs → 0 equity buys in BEAR_LOW_VOL). When the
    # diversifier is on, allow a few mega buys in bear/crisis so the book deploys
    # liquid mega (net-positive in bear) instead of leaving the slots to gold.
    mega_diversifier_bear_max_buy: int = 4      # defensive EQUITY slot cap (gold fills 5−4=1+)
    mega_diversifier_crisis_max_buy: int = 2    # crisis EQUITY slot cap (gold fills 5−2=3+)
    # Total slots are fixed at mega_diversifier_total_slots in every regime. Equity is
    # capped per regime above; GOLD fills the RESIDUAL (total − equity held) and ALWAYS
    # yields to buys (no floor). In bear the deploy ceiling is raised to fund all slots.
    # Works with fast_deploy — the dynamic gold path sizes gold to the residual too.
    mega_diversifier_total_slots: int = 5

    validation_high_vol_threshold: float = 0.20

    # ARGS LLM routing — global defaults (per-agent vars override when set)
    # provider: mock | openai | openai_compatible | custom via register_llm_provider()
    args_llm_provider: str = "mock"
    args_llm_default_model: str = "gpt-4o-mini"
    args_llm_openai_api_key: str = ""
    # Backward-compatible generic key name sometimes used in .env files.
    openai_api_key: str = ""
    args_llm_openai_base_url: str = "https://api.openai.com/v1"
    args_llm_timeout_seconds: int = 60
    # TARC
    args_llm_tarc_provider: str = ""
    args_llm_tarc_model: str = ""
    args_llm_tarc_api_key: str = ""
    args_llm_tarc_base_url: str = ""
    args_llm_tarc_timeout_seconds: int = 0
    # FRC
    args_llm_frc_provider: str = ""
    args_llm_frc_model: str = ""
    args_llm_frc_api_key: str = ""
    args_llm_frc_base_url: str = ""
    args_llm_frc_timeout_seconds: int = 0
    # QRC
    args_llm_qrc_provider: str = ""
    args_llm_qrc_model: str = ""
    args_llm_qrc_api_key: str = ""
    args_llm_qrc_base_url: str = ""
    args_llm_qrc_timeout_seconds: int = 0
    # NRCC
    args_llm_nrcc_provider: str = ""
    args_llm_nrcc_model: str = ""
    args_llm_nrcc_api_key: str = ""
    args_llm_nrcc_base_url: str = ""
    args_llm_nrcc_timeout_seconds: int = 0
    # RC
    args_llm_rc_provider: str = ""
    args_llm_rc_model: str = ""
    args_llm_rc_api_key: str = ""
    args_llm_rc_base_url: str = ""
    args_llm_rc_timeout_seconds: int = 0
    # CRO
    args_llm_cro_provider: str = ""
    args_llm_cro_model: str = ""
    args_llm_cro_api_key: str = ""
    args_llm_cro_base_url: str = ""
    args_llm_cro_timeout_seconds: int = 0

    # QRC evidence mode — SQE experiment (default off; legacy brief unchanged when false)
    args_qrc_use_sqe: bool = False

    # Authentication (Track E)
    auth_enabled: bool = True
    jwt_secret_key: str = "change-me-in-production-use-openssl-rand"
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 15
    jwt_refresh_token_days: int = 7
    auth_bypass_for_tests: bool = False

    # CORS — comma-separated browser origins (local UI preview + Expo web dev)
    cors_allowed_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:8081,http://127.0.0.1:8081"
    )

    # Execution platform (Track K)
    enable_live_trading: bool = False
    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_access_token: str = ""
    # Headless token refresh (daily cron)
    kite_user_id: str = ""
    kite_password: str = ""
    kite_totp_secret: str = ""

    # ── Human-In-The-Loop (HITL) feature flag ────────────────────────────────
    # True  = require explicit human approval before any BUY is executed (default, production)
    # False = auto-approve BUYs after recommendation + committee review (paper trading mode)
    # Set HITL_ENABLED=false in .env to enable autonomous paper trading.
    hitl_enabled: bool = True

    # ── Paper trading mode ────────────────────────────────────────────────────
    # True  = execute paper trades in daily batch when HITL_ENABLED=false
    # False = generate recommendations only, no execution
    paper_trading_enabled: bool = False

    # ── ADR-033: Intraday exit monitor ────────────────────────────────────────
    # T1 intraday price monitor (stop_loss + trailing_stop).
    # For paper mode uses last known close as LTP proxy.
    # For live, inject a real QuoteProvider (Kite adapter).
    intraday_exit_monitor_enabled: bool = False
    intraday_interval_sec: int = 300  # poll cadence when run by a scheduler

    # ── ADR-037 v18 Tier-1/2 (post-entry management + gold) — all default OFF so the
    # v17 equity baseline is unchanged; enable per-feature for v18 A/B runs. ──────
    # Tier 1: day-5 follow-through graduation. After the 5-day noise window, a
    # position that is green AND still ranked is "winner-track" (loosen the leash,
    # hold to run); red OR rank-dropped is "loser-track" (cut). Raises realized win%
    # and cuts the 1-5 day short-churn that bleeds STT.
    graduation_enabled: bool = True
    graduation_winner_trail_pct: float = 12.0   # wide trail for winner-track (let it run)
    # Tier 1: runner tier — an exceptional winner (still top-N ranked + large gain)
    # is promoted to a months-long position trade on a very loose trail; rides the
    # multibaggers we already find, with near-zero added turnover.
    runner_tier_enabled: bool = True
    runner_max_rank: int = 5
    runner_min_gain_pct: float = 20.0
    runner_trail_pct: float = 25.0
    # ATR-scaled DYNAMIC stops & trails (flag-gated). Stop/trail distances scale with
    # each stock's own ATR(14)%/price (daily-recomputed) so a volatile name breathes
    # wider and a quiet one keeps a tight leash. The run-tier sets the trail multiplier
    # (normal/winner/runner). Clamped so no absurd stop. Calibrated to ≈ today's fixed
    # values at the median NIFTY ATR% (~3.4%).
    atr_dynamic_exits_enabled: bool = False
    atr_stop_mult_bull: float = 2.5      # bull/neutral stop = 2.5×ATR (~-8% median)
    atr_stop_mult_bear: float = 1.2      # bear stop = 1.2×ATR (~-4% median)
    atr_trail_mult_normal: float = 2.0   # un-graduated trail (~-7% median)
    atr_trail_mult_winner: float = 3.5   # winner-track trail (~12% median)
    atr_trail_mult_runner: float = 6.0   # runner trail (~20% median)
    atr_stop_floor_pct: float = 3.0      # min |stop| (no whipsaw-tight)
    atr_stop_cap_pct: float = 12.0       # max |stop| (no disaster-wide)
    atr_trail_floor_pct: float = 4.0
    atr_trail_cap_pct: float = 30.0
    # Tier 2: gold rotation — in BEAR regimes deploy the defensive sleeve to GOLDBEES
    # instead of holding cash (P-22). Diversifier with positive bear-regime expectancy.
    gold_rotation_enabled: bool = False
    gold_symbol: str = "GOLDBEES.NS"
    gold_alloc_pct: float = 0.50   # fraction of deployable capital into gold in bear
    # Gold ALWAYS yields to equity buys: gold is a pure residual idle-cash sleeve — it
    # only deploys cash no equity slot wants, and sells (fully, no floor) the moment an
    # equity BUY needs the capital. So equity slots have absolute priority in every
    # regime and are never blocked by gold. Default OFF preserves the legacy bear floor
    # (gold_min_pct) below which gold would NOT yield.
    gold_yield_to_buys_enabled: bool = False

    # Advisory stop — creates PENDING exit + notifies owner (HITL required).
    advisory_stop_pct: float = -8.0   # unrealized % vs avg_cost; e.g. -8.0

    # Critical stop — bypasses HITL; only when auto_exit_on_critical_stop=true.
    critical_stop_pct: float = -10.0  # e.g. -10.0

    # Whether the critical stop fires an automatic SELL (no HITL).
    # PO must explicitly enable. Never auto-enabled.
    auto_exit_on_critical_stop: bool = False

    # ── ADR-036: Regime-aware RCEE EDGE_PRESENT sample floor ───────────────────
    # Rare regimes (bear / high-vol) accumulate far fewer regime-days, so the flat
    # 60-day floor blocks genuinely-significant edge there (e.g. reversal_v1 in
    # BEAR_LOW_VOL: IC_low95 +0.072, hit 81%, but n=53 < 60). ic_lower_95 already
    # gates sample uncertainty, so a lower floor for rare regimes is principled.
    rcee_edge_present_sample_days: int = 60          # common regimes (BULL_LOW_VOL)
    rcee_rare_regime_sample_days: int = 40           # P-23: 45→40 so a valid young bear edge (reversal hit n=41) isn't benched
    rcee_rare_regimes: str = "BEAR_LOW_VOL,BEAR_HIGH_VOL,BULL_HIGH_VOL"

    # ── ADR-035: Regime-dynamic stops & time-stop removal (flag-off default) ───
    # When enabled, the advisory stop is resolved per-day from the market regime
    # (regime_history, ^NSEI) via regime_stop_map; critical = advisory + offset.
    # Defaults preserve current behaviour (static advisory/critical, time stop on).
    regime_dynamic_stops_enabled: bool = False
    regime_stop_map: str = (
        '{"BULL_LOW_VOL": -6.0, "BULL_HIGH_VOL": -8.0, '
        '"BEAR_LOW_VOL": -2.0, "BEAR_HIGH_VOL": -3.0}'
    )
    regime_stop_fallback_pct: float = -4.0   # no regime row / unknown label
    regime_critical_offset_pct: float = -2.0  # critical = advisory + this
    # ADR-035 D2: master switch for the 30-day time stop (engine R-EXIT-04 +
    # T2 exit monitor EXIT_TIME). True = current behaviour.
    time_stop_enabled: bool = True

    # ── Hybrid (per-stock) regime exit ────────────────────────────────────────
    # The market regime (^NSEI + breadth) is a BOOK-level signal; today a
    # defensive flip can EXIT_REGIME a position purely because its *relative* rank
    # slipped, even while the stock is still in its OWN uptrend and in profit.
    # Evidence (2026-06): such blanket-cut own-uptrend names went on to beat NIFTY
    # +2.35%/10d, and EXIT_REGIME is the #1 churn driver (60% of exits, 1.8d hold).
    # When enabled, a defensive flip HOLDS positions still above their own
    # 50 & 200-day SMA and not losing money (rank-slip alone no longer forces the
    # sell); a *crisis* posture still always exits (systemic crash protection).
    # Default False preserves current behaviour.
    regime_exit_per_stock_trend_enabled: bool = False
    regime_exit_trend_sma_fast: int = 50
    regime_exit_trend_sma_slow: int = 200

    # Intra-bear churn fix: suppress the *defensive* EXIT_REGIME when the position was
    # ENTERED already in a defensive (bear / high-vol) regime — the trade was made for
    # that regime (e.g. reversal_v1 in BEAR_LOW_VOL), so a re-flip within the same bear
    # should not re-cut it. bear->bear was 76% of EXIT_REGIME exits (57% winners).
    # crisis still always exits; bull->bear keeps the full defensive logic.
    regime_exit_intra_bear_hold: bool = True

    # ── P-26: ALPHA_DECAY timing — judge thesis decay at its intended threshold ─
    # check_alpha_decay is *meant* to test alpha decay at its day-15 threshold, but
    # the P-15 day-5 grace made it cut every still-red name the instant the grace
    # lifted: 54% of EXIT_ALPHA_DECAY exits fire on exactly day 5 (median hold 5d,
    # max 10d — the 15-day ceiling is never reached). On the names that recover, that
    # day-5 cut threw away +14.4% alpha by day 15 (87% positive), then re-bought them
    # ~11.5% higher as breakouts (paying two STT round-trips). Deferring the judgement
    # to this many days lets the recoverers (green by day 15) be HELD while the genuine
    # decayers (still red at day 15) are still cut. STOP_LOSS (-8%) + the P-17
    # progressive stop floor the downside in the interim, so the only thing deferred is
    # the premature day-5 cut. Default 5 preserves the legacy day-5 window [5,15];
    # set to 15 to judge at the day-15 horizon (floor semantics, gap-robust).
    alpha_decay_grace_days: int = 5

    # ── Horizon-aware exits ───────────────────────────────────────────────────
    # Each validated edge plays out over a different horizon (breakout ~10d, deep-
    # oversold reversion ~20d, 12mo momentum ~quarter). The legacy ~2-day churn
    # (rank-drop / alpha-decay) sells before momentum & reversion pay. When enabled,
    # the analytical-exit suppression window AND the progressive-stop schedule scale
    # to the position's strategy hold (see exit_monitor._STRATEGY_MIN_HOLD), so each
    # sleeve breathes for its signal's timescale. Hard stops still fire throughout.
    horizon_aware_exits_enabled: bool = False

    # ── Let winners run ───────────────────────────────────────────────────────
    # Breakout is fat-tailed — a few monster runs make the strategy. The graduation/
    # runner tiers only protect winners that are STILL top-ranked; a winner whose
    # RANK FADES but keeps making new highs still gets rank-dropped/regime-cut (2021:
    # cut at +7% while it ran another +7.6%; ATGL exited at +1% then ran +213%). When
    # enabled, a position in solid profit AND still near its peak (small pullback =
    # making higher highs) is exempt from RANK_DROP and EXIT_REGIME regardless of its
    # current rank — it rides a wide trailing stop to capture the fat tail. Hard stop
    # and the trailing stop still fire (risk + profit-lock intact).
    let_winners_run_enabled: bool = True
    win_run_min_profit_pct: float = 3.0      # only protect positions up at least this
    # "near peak" tolerance = within this of max_gain. ATR-scaled: a volatile name
    # breathes wider so a normal pullback doesn't drop winner-protection (audit: peaks
    # of +8-13% gave back to ~breakeven through an 8% band, then ran +15-33%).
    win_run_pullback_band_pct: float = 15.0      # floor band (%)
    win_run_pullback_atr_mult: float = 3.0       # effective band = max(floor, mult × ATR%)
    # Don't trail at all below this peak gain — a small breakout rides on the hard ATR
    # stop only, so a routine pullback in a +8-13% name can't clip it before it runs.
    # The fat tail (multibaggers) needs room; tight trails on small gains kill it.
    # 2026 give-back audit: 93% of trailing exits ran further (avg +11.5% left, 190/246 cut
    # at +2.7% peak); raised 15->18 so the trail only arms with a real cushion.
    trailing_min_activation_pct: float = 18.0

    # ── Lifecycle wiring (regime-aware breakout/reversion; flag-gated, default off) ──
    # ENTRY: gate the buy loop with app.lifecycle.entry.should_enter — only buy a
    # candidate that is the 3-way regime's entry sleeve (BULL->breakout_v2,
    # BEAR->reversion_v3, SIDEWAYS->cash), a top pick, and clears the stock-trend gate.
    lifecycle_entry_enabled: bool = False
    lifecycle_entry_top_pct: float = 0.20
    # reversion_v3 turn-confirmation: rank a deeply-crushed name ONLY once it has STARTED
    # to turn (close back above a short SMA) — skip the falling knife. Entry-timing audit:
    # un-confirmed bounce entries dipped -3.8% more after entry (vs -1.9% for breakouts),
    # 34% went 5%+ underwater, tripping the stop (48% stopped, 76% then recovered). Entering
    # after the turn removes that knife-dip + the stop whipsaw at the source.
    reversion_turn_confirm_enabled: bool = True
    reversion_turn_confirm_sma: int = 5
    #  reversion_v3 STOP: oversold bounces pull back WITHIN the recovery, so the tiered
    #  regime stop (-2/-4) whipsaws them (confirmed-turn bounces dip ~-5% median, 88% then
    #  recover +16%). Give the bounce sleeve a wide, volatility-scaled stop (~3x ATR, floor
    #  -8% = the p25 dip, cap -15%) routed through the ATR path; leaders keep the tiered stop.
    reversion_atr_stop_mult: float = 3.0
    reversion_atr_stop_floor_pct: float = 8.0
    reversion_atr_stop_cap_pct: float = 15.0
    # Slot experiment: many small slots restricted to the top-N rank bucket. When
    # lifecycle_max_positions > 0 it overrides the regime slot cap; sizing auto-falls to
    # ~deployable/max_positions (18 slots ≈ 5%/name). top_rank>0 admits only rank<=N.
    lifecycle_max_positions: int = 0
    lifecycle_max_buy_per_day: int = 0
    lifecycle_entry_top_rank: int = 0
    # EXIT: add the cross-rank HANDOFF exit — a breakout_v2 position exits on
    # breakout_v1 (B1) fade, a reversion_v3 position on reversal_v1 (RV1) recovery.
    # The legacy regime exit / hard stop / trailing stop are unchanged.
    lifecycle_handoff_exits_enabled: bool = False
    # Lifecycle EXIT tuning (active only with lifecycle_handoff_exits_enabled):
    #  1) regime exit on the 3-way regime — HOLD through SIDEWAYS chop, exit only on a
    #     CONFIRMED BEAR, and even then keep a stock whose OWN trend is still BULL.
    #  2) regime/stock-tiered hard stop (8/6/4/2%) instead of the progressive day-stop
    #     that was cutting names at ~0% after day 10.
    #  3) alpha-decay tolerance — don't retire a name at -0.4%; give it room.
    lifecycle_regime_exit_3way: bool = True
    lifecycle_stop_bull_bull_pct: float = 8.0   # market BULL + stock BULL
    lifecycle_stop_bull_pct: float = 6.0        # market BULL, stock not BULL
    lifecycle_stop_sideways_pct: float = 4.0    # market SIDEWAYS
    lifecycle_stop_bear_pct: float = 2.0        # market BEAR
    lifecycle_alpha_decay_tolerance_pct: float = 5.0  # alpha-decay only if down > this
    #  4) EXIT_STALL — recycle a long-held position that fails to COMPOUND: realized
    #     slope (gain%/day) below the floor after a grace window. Catches the 'dragging
    #     momentum' blind spot (VPS: such names ate ~38% of slot-days for ~+13% avg, vs
    #     +139% for the >=0.20/day winners). Slope floor spares multibaggers; the
    #     momentum-rising guard spares coilers. Default OFF (flag-gated for A/B).
    lifecycle_stall_enabled: bool = True
    lifecycle_stall_grace_days: int = 60          # never fire before this hold
    lifecycle_stall_slope_floor_pct: float = 0.12  # gain%/day below this -> stall (~30%/yr)

    # ── P-24: transaction-cost model (net-of-cost backtest) ───────────────────
    # When enabled, every fill incurs the NSE delivery-equity cost stack so NAV /
    # CAGR are reported NET of costs (the legacy behaviour applied only a flat
    # per-leg brokerage fee, ≈0.004%, which hid the real ~0.22%+slippage/round-trip
    # drag — material at this strategy's 68× turnover). Pct values are PERCENT of
    # trade value (0.10 == 0.10%). STT applies both legs on delivery; stamp on buy.
    transaction_costs_enabled: bool = False
    cost_stt_buy_pct: float = 0.10
    cost_stt_sell_pct: float = 0.10
    cost_stamp_buy_pct: float = 0.015
    cost_exchange_txn_pct: float = 0.00297
    cost_sebi_pct: float = 0.0001
    cost_gst_rate: float = 0.18
    # Slippage / market-impact applied to the fill price, per side (basis points).
    # The charge stack above (STT/stamp/etc.) is NOT the real execution cost — on the
    # NIFTY_1000 small-cap tail, market impact dominates. At this strategy's turnover
    # (~₹78cr traded / ₹10-31L book over 2021-25) a 25bps/side slippage costs ~₹19.6L,
    # ≈ the entire net profit (true-net CAGR +28%→+3.6%). Default 5bps preserves the
    # legacy fill; set 25 (COST_SLIPPAGE_BPS=25) for a realistic small-cap true-net.
    cost_slippage_bps: float = 5.0

    # ── Smarter daily-OHLC fills (no intraday data needed; backtestable) ──────
    # Replaces the flat slippage with a realistic OHLC-based fill on the NEXT session
    # (no same-bar look-ahead). BUY/EOD-exit = median(open, (high+low)/2, (open+close)/2)
    # — a gap-robust typical price whose dispersion stands in for slippage. Price-
    # triggered exits (stop/trailing) fill at their trigger level (gap → open). No flat
    # slippage is added when on. Default OFF preserves the slippage-factor fills.
    ohlc_fills_enabled: bool = False

    # ── Execution realism: next-open fills (removes same-bar look-ahead) ──────
    # Default OFF = same-bar close fills (decide and fill on day D's close — not
    # executable live). ON = the day-D-close decision fills at the NEXT trading day's
    # OPEN, the first price you could actually trade at. Applies to entries AND exits.
    next_open_fills_enabled: bool = False

    # Date the entry on the FILL session, not the rec session: a BUY decided on D-1's
    # close fills the NEXT session (D, where the band gate already runs), so the position
    # is dated D — not D-1. Off = legacy (entry dated on the rec/batch day).
    entry_execute_next_session: bool = False

    # Exit-monitor SELLs fill at the DECISION day's close ("D close as mocked") — the
    # exit fired on this bar, so selling at its close is the conservative backtest mock.
    # Overrides next_open/ohlc for SELLs only; entries (band-mid) are unaffected.
    exit_fills_at_close_enabled: bool = False

    # ── Execution realism: entry-band LIMIT fills (price-tag gate) ────────────
    # Each BUY rec carries a price band [entry_low, entry_high] (reference_close ±
    # 0.5×ATR). With this ON, a BUY is treated as a limit order on the band: it fills
    # ONLY if D+1's intraday range OVERLAPS the band (D+1_low ≤ entry_high AND
    # D+1_high ≥ entry_low), filling at the committed band level (see
    # entry_band_fill_level). If D+1 gaps entirely away from the band (up = chasing,
    # down = possibly broken/no momentum into band), the order is SKIPPED — mirrors the
    # live momentum monitor that only fires inside the band. Supersedes next_open.
    entry_band_fills_enabled: bool = False
    # Where in the band a momentum-confirmed entry fills: "mid" = band midpoint
    # (reference_close — fires only if D+1 trades THROUGH the mid), "high" = entry_high
    # (top of band). Only applies when entry_band_fills_enabled.
    entry_band_fill_level: str = "mid"
    # Missed-fill retry: when a BUY misses its band/mid, keep it eligible for this many
    # subsequent trading days. On each later day it's re-checked against that day's bar
    # and, if the mid is touched + regime still active + an open slot exists, executed —
    # ranked by its ORIGINAL rank then composite_score. 0 disables the retry queue.
    entry_band_retry_days: int = 3

    # ── Fast-deploy: refill bull/neutral slots faster (idle-cash fix) ─────────
    # In bull regimes max_buy_per_day is 2 (1 neutral), so after a batch exit the
    # book refills only a trickle/day → ~40% idle cash in bull years against 20+
    # candidates/day (measured 2021). Idle cash earns 0% while each bull trade nets
    # ~+0.87% (gross − 0.23% cost), so deploying faster is net-accretive. This only
    # multiplies max_buy_per_day where it is already > 0 (bull/neutral) — bear
    # postures stay at 0, adding no downside-regime risk. Default off.
    fast_deploy_enabled: bool = False
    fast_deploy_buy_multiplier: int = 2

    # ── Execution realism: intraday VWAP fills + size-vs-ADV market impact ────
    # Default OFF = the legacy close/next-open fill with flat cost_slippage_bps.
    # ON = fill at the NEXT session's intraday VWAP (first ``vwap_window_minutes``)
    # and replace the flat slippage with a square-root market-impact model:
    #   slip_bps = impact_spread_bps/2 + impact_coeff_bps * sqrt(order_value / ADV)
    # so a small order in a liquid name pays ~half-spread, while a large order in a
    # thin small-cap pays a participation-scaled impact — the true-net cost driver.
    # Falls back to next-open (then close) when intraday data is missing for a bar.
    realistic_fills_enabled: bool = False
    intraday_interval: str = "60minute"  # Kite interval: "60minute" | "minute" | ...
    vwap_window_minutes: int = 60  # T+1 window used to compute the fill VWAP
    impact_spread_bps: float = 8.0  # round-trip half-spread proxy (per leg = /2)
    impact_coeff_bps: float = 35.0  # √-impact coefficient (bps at 100% participation)
    adv_lookback_days: int = 20  # trailing window for average daily traded value
    # NOTE: statutory charges (STT/stamp/exchange/SEBI/GST) are modelled separately by
    # PaperTradeService._leg_cost under ``transaction_costs_enabled`` (P-24) and compose
    # with realistic fills automatically — no extra flag needed here.


    # _REGIME_DEPLOY_PCT): BULL_LOW_VOL=risk_on 0.95, BULL_HIGH_VOL=limited_risk_on
    # 0.75, BEAR_LOW_VOL=neutral 0.45 (reversal dip-buy), BEAR_HIGH_VOL=defensive 0.00.
    fast_deploy_risk_on_pct: float = 1.00  # BULL_LOW_VOL: fully deployed across 5 names (~20%/name)
    fast_deploy_limited_pct: float = 0.75
    fast_deploy_neutral_pct: float = 0.45
    fast_deploy_defensive_pct: float = 0.00
    # Gold sleeve as a dynamic band (% of TOTAL portfolio), demand-driven: soaks idle
    # cash up to gold_max, yields to stock buys down to gold_min, rides winners (no
    # auto-sell on regime flip), cuts losers. gold_buy_cooldown_days prevents the
    # buy-yield-rebuy thrash. Active when fast_deploy_enabled.
    gold_min_pct: float = 0.25
    gold_max_pct: float = 0.50
    gold_buy_cooldown_days: int = 6

    # ── ADR-034: Recommendation trade levels (deterministic, BUY) ──────────────
    # Entry range + stop-loss range decorated onto BUY recommendations at the
    # recommendation phase. Stops reuse advisory_stop_pct / critical_stop_pct above.
    recommendation_trade_levels_enabled: bool = True
    recommendation_atr_period: int = 14
    recommendation_entry_band_atr_mult: float = 0.5      # half-width = mult × ATR
    recommendation_entry_band_pct_fallback: float = 1.0  # used when ATR unavailable


def parse_cors_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
