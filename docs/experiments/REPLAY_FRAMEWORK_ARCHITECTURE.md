# Replay Simulation Framework (RSF) — Architecture

## Overview

The RSF is a production-grade, configuration-driven experimentation framework that replays the Pi-PM investment pipeline over historical data. It reuses all production code (recommendation engine, conviction scorer, exit triggers, position sizer) and reads exclusively from the production database — **it never writes to any production table**.

---

## Architecture Diagram (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ReplayEngine.run()                               │
│                                                                         │
│  YAML Config ──► ReplayExperimentConfig                                 │
│                           │                                             │
│                           ▼                                             │
│              ┌─────────────────────────┐                                │
│              │  TradingCalendar        │ ── resolves trading days       │
│              └──────────┬──────────────┘                                │
│                         │  for each trading day                        │
│                         ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   ReplayDayProcessor.process_day()               │  │
│  │                                                                  │  │
│  │  1. Load ranking runs from DB (read-only, as_of_date gated)      │  │
│  │  2. Load recommendation results from DB (pre-computed pipeline)  │  │
│  │  3. Load current prices from market_data (close, as_of_date)     │  │
│  │                                                                  │  │
│  │  EXIT PHASE:                                                     │  │
│  │    for each open position:                                       │  │
│  │      check_rank_drop() ─┐                                        │  │
│  │      check_alpha_decay() ├─► any fires → close_position()        │  │
│  │      check_regime_change() ─┘                                    │  │
│  │      check_time_stop()                                           │  │
│  │                                                                  │  │
│  │  ENTRY PHASE:                                                    │  │
│  │    filter BUY recommendations by mode                            │  │
│  │    for each eligible BUY:                                        │  │
│  │      skip if already held                                        │  │
│  │      check slot limits & cash floor                              │  │
│  │      size_position() → quantity                                  │  │
│  │      open_position() → ReplayPosition                            │  │
│  │                                                                  │  │
│  │  MARK-TO-MARKET all positions                                    │  │
│  │  SIP contribution (if applicable)                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                         │                                               │
│                         ▼                                               │
│            ReplayMetricsCollector.record_day()                          │
│                         │                                               │
│                         ▼                                               │
│            ReplayReportGenerator.generate()                             │
│                         │                                               │
│                         ▼                                               │
│                   ReplayResult                                          │
└─────────────────────────────────────────────────────────────────────────┘

Production DB (read-only):
  ranking_runs ──────► day processor reads as_of_date gated
  ranking_results ───► exit trigger: rank lookup
  recommendation_runs/results ──► BUY candidates
  market_data ───────► close prices for fills & MTM
  strategy_regime_performance ──► (RCEE, used via stored recs)
```

---

## Component Model

| Component | File | Responsibility |
|---|---|---|
| `ReplayExperimentConfig` | `app/replay/config/experiment_config.py` | Pydantic config model, YAML loader |
| `ExperimentMode` | same | Enum of simulation modes |
| `ReplayPortfolioManager` | `app/replay/portfolio_manager.py` | In-memory cash+positions, cap enforcement |
| `ReplayDayProcessor` | `app/replay/day_processor.py` | Single-day simulation: exits → entries → MTM |
| `ReplayMetricsCollector` | `app/replay/metrics_collector.py` | NAV series accumulation, final metric computation |
| `ReplayReportGenerator` | `app/replay/report_generator.py` | Markdown output: NAV curve, trade report, breakdowns |
| `ReplayEngine` | `app/replay/engine.py` | Main orchestrator: resolves days, loops, returns result |
| Data models | `app/replay/models.py` | `ReplayPosition`, `ReplayTrade`, `ReplayDailySnapshot`, `ReplayContext`, `ReplayMetrics` |

---

## Replay Lifecycle (Day-by-Day Loop Pseudocode)

```
config = ReplayExperimentConfig.from_yaml(path)
trading_days = TradingCalendar.trading_days_in_range(config.start_date, config.end_date)
portfolio = ReplayPortfolioManager(config)
collector = ReplayMetricsCollector()
hitl_buffer = []   # for HITL_SIMULATION mode

with DB session:
  for i, day in enumerate(trading_days):
    # 1. Resolve regime context
    ranking_runs = query ranking_runs WHERE as_of_date=day AND strategy IN config.strategies
    if not ranking_runs: continue  # holiday / no data
    regime_label = ranking_runs[0].regime_label
    regime_posture = derive_posture(regime_label)  # BULL→risk_on, BEAR→defensive, etc.

    context = ReplayContext(
      as_of_date=day,
      regime_label=regime_label,
      regime_posture=regime_posture,
      trading_day_index=i,
      is_first_trading_day_of_month=(day == first_trading_day_of_month),
      is_sip_day=(config.capital.contribution_day matches context)
    )

    # 2. SIP contribution (before entries, so cash is available)
    if context.is_sip_day and config.capital.monthly_contribution > 0:
      portfolio.add_sip(config.capital.monthly_contribution, day)

    # 3. Fetch close prices for all relevant stocks
    price_map = query market_data WHERE date=day → {stock_id: close}

    # 4. EXIT PHASE
    exits = []
    for pos in portfolio.open_positions:
      current_rank = query ranking_results for pos.stock_id on day
      triggers = [check_rank_drop(...), check_alpha_decay(...), check_regime_change(...), check_time_stop(...)]
      if any(t.fired for t in triggers):
        trade = portfolio.close_position(pos.stock_id, day, price_map[pos.stock_id], trigger_code)
        exits.append(trade)
        collector.record_exit(trade)

    # 5. ENTRY PHASE (mode-dependent)
    buy_recs = load_buy_recommendations(day, config.strategies, db)
    if mode == HITL_SIMULATION:
      buy_recs = hitl_buffer  # yesterday's buys
      hitl_buffer = load_buy_recommendations(day, ...)
    elif mode == AUTONOMOUS_FORCE_EDGE:
      buy_recs = re_run_engine_with_forced_edge(day, ...)

    entries = []
    for rec in sorted(buy_recs, key=lambda r: r.rank):
      if not portfolio.can_open_position(config): break
      if rec.stock_id in portfolio.held_stock_ids: continue
      slot_budget = portfolio.get_slot_budget(config.portfolio.max_positions)
      fill_price = price_map.get(rec.stock_id)
      if fill_price is None: continue
      fill_price = apply_slippage(fill_price, config.execution.slippage_bps, side="BUY")
      sizing = size_position(SizingInputs(rec.conviction_band, slot_budget, fill_price))
      if sizing.quantity == 0: continue
      cost = fill_price * sizing.quantity + config.execution.fee_per_leg
      if cost > portfolio.get_available_cash(): continue
      pos = ReplayPosition(...)
      if portfolio.open_position(pos):
        trade = ReplayTrade(side="BUY", ...)
        entries.append(trade)
        collector.record_entry(trade)

    # 6. Mark to market
    portfolio.mark_to_market(price_map, day)

    # 7. Snapshot
    snap = portfolio.snapshot(day, regime_label)
    collector.record_day(snap)

# 8. Final metrics & reports
metrics = collector.compute_final_metrics(config.start_date, config.end_date)
ReplayReportGenerator(config).generate(collector, metrics)
return ReplayResult(config=config, metrics=metrics, snapshots=collector.snapshots, trades=collector.all_trades)
```

---

## Configuration Model

`ReplayExperimentConfig` is a Pydantic `BaseModel` loaded from YAML. Sub-configs:

- **`CapitalConfig`** — initial cash, SIP amount & timing
- **`ExecutionConfig`** — slippage, fees, auto-approve flags
- **`RecommendationConfig`** — RCEE on/off, committee on/off, validation gate
- **`PortfolioConfig`** — position limits, sizing policy, cash floor
- **`OutputConfig`** — which reports to generate, output directory

`ExperimentMode` controls how BUY recommendations are sourced/filtered:

| Mode | Behavior |
|---|---|
| `AUTONOMOUS_RCEE` | Use pre-computed pipeline recs as-is (RCEE already applied) |
| `AUTONOMOUS_NO_RCEE` | Filter to only recs not blocked by regime (legacy gate) |
| `AUTONOMOUS_FORCE_EDGE` | Re-run engine with EDGE_PRESENT forced — shows max possible buys |
| `HITL_SIMULATION` | Apply 1-day delay: process yesterday's BUYs today |
| `COMMITTEE_BYPASS` | Skip committee review gate |
| `CUSTOM` | Full config control via RecommendationConfig flags |

---

## How Each Production Service Is Reused

| Production Asset | Reuse In RSF |
|---|---|
| `ranking_runs` table | `ReplayDayProcessor` reads as_of_date-gated runs to get regime_label and ranking context |
| `ranking_results` table | Exit monitor reads current rank for `check_rank_drop()` |
| `recommendation_results` table | `ReplayDayProcessor` reads BUY recs — pre-computed by pipeline, no re-run needed |
| `market_data` table | Close prices for fill simulation and mark-to-market |
| `check_rank_drop()`, `check_alpha_decay()`, `check_regime_change()`, `check_time_stop()` | Called directly in exit phase — pure functions, no DB |
| `size_position()` | Called in entry phase with `SizingInputs` built from rec + portfolio state |
| `TradingCalendar.trading_days_in_range()` | Resolves the set of trading days for the experiment window |
| `engine.run()` | Called only in `AUTONOMOUS_FORCE_EDGE` mode with forced regime fit |

---

## No-Future-Leakage Guarantee

Every data access in the framework is gated by `as_of_date`:

1. **Ranking runs**: `WHERE as_of_date = :day` — only that day's run
2. **Recommendation results**: joined through `ranking_runs.as_of_date = :day` — only recs from that pipeline run
3. **Market data**: `WHERE date = :day` — only that day's close price (no look-ahead)
4. **Ranking results for exit monitor**: joined through `ranking_runs.as_of_date = :day` — same constraint
5. **Regime label**: taken from `ranking_run.regime_label` — stored at run time, not recomputed

The framework **never** uses `MAX(date)`, `LIMIT 1`, or unbounded queries. Every query has an explicit date gate.

---

## Risks and Assumptions

| Risk | Mitigation |
|---|---|
| Missing market data for a stock on a day | `price_map.get(stock_id)` returns None → skip that entry/exit gracefully |
| No ranking run for a trading day (e.g., gap in pipeline) | `if not ranking_runs: continue` — day skipped, position held |
| Survivorship bias | RSF uses actual pipeline universe at each date — stocks delisted mid-period are naturally absent |
| Fill price realism | Close-price fills with configurable slippage_bps. In reality, intraday fills may differ |
| SIP timing | Assumes SIP executes at end-of-day close on the configured contribution day |
| Slippage model | Linear BPS slippage is a simplification; market impact not modeled |
| `AUTONOMOUS_FORCE_EDGE` engine re-run | Requires all upstream inputs to be available for re-computation; will log warnings if missing |
| PyYAML dependency | Required for YAML config loading. Added to `pyproject.toml` if not present |
| Time zone | All dates are naive `date` objects (IST market dates). No TZ conversion needed |
