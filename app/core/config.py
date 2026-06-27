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
    graduation_enabled: bool = False
    graduation_winner_trail_pct: float = 12.0   # wide trail for winner-track (let it run)
    # Tier 1: runner tier — an exceptional winner (still top-N ranked + large gain)
    # is promoted to a months-long position trade on a very loose trail; rides the
    # multibaggers we already find, with near-zero added turnover.
    runner_tier_enabled: bool = False
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

    # ── Execution realism: next-open fills (removes same-bar look-ahead) ──────
    # Default OFF = same-bar close fills (decide and fill on day D's close — not
    # executable live). ON = the day-D-close decision fills at the NEXT trading day's
    # OPEN, the first price you could actually trade at. Applies to entries AND exits.
    next_open_fills_enabled: bool = False

    # ── Fast-deploy: refill bull/neutral slots faster (idle-cash fix) ─────────
    # In bull regimes max_buy_per_day is 2 (1 neutral), so after a batch exit the
    # book refills only a trickle/day → ~40% idle cash in bull years against 20+
    # candidates/day (measured 2021). Idle cash earns 0% while each bull trade nets
    # ~+0.87% (gross − 0.23% cost), so deploying faster is net-accretive. This only
    # multiplies max_buy_per_day where it is already > 0 (bull/neutral) — bear
    # postures stay at 0, adding no downside-regime risk. Default off.
    fast_deploy_enabled: bool = False
    fast_deploy_buy_multiplier: int = 2
    # When fast_deploy is on, the stock deploy ceiling per regime posture (overrides
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
