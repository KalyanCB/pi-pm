# Replay Simulation Framework — Implementation Reference

## Package Structure

```
app/replay/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── experiment_config.py      # ReplayExperimentConfig, ExperimentMode
├── models.py                     # ReplayPosition, ReplayTrade, ReplayDailySnapshot,
│                                 # ReplayContext, ReplayMetrics
├── portfolio_manager.py          # ReplayPortfolioManager
├── day_processor.py              # ReplayDayProcessor
├── metrics_collector.py          # ReplayMetricsCollector
├── report_generator.py           # ReplayReportGenerator
└── engine.py                     # ReplayEngine (main entry point)

configs/
├── EXP01_SMOKE_2W.yaml
├── EXP02_BEAR_3M.yaml
├── EXP03_REGIME_TRANSITION_6M.yaml
├── EXP04_1Y_REPLAY.yaml
├── EXP05_FULL_REPLAY.yaml
├── EXP06_RCEE_COMPARISON.yaml
└── EXP07_STRATEGY_COMPARISON.yaml

scripts/
└── run_replay.py                 # CLI entry point

tests/unit/replay/
├── __init__.py
├── test_portfolio_manager.py     # 8 tests
├── test_metrics_collector.py     # 7 tests
└── test_experiment_config.py     # 8 tests
```

---

## Key Design Decisions

### 1. Pre-Computed Recommendations

The framework does NOT re-run the recommendation engine for each day. It reads from `recommendation_results` already computed and stored by the pipeline. This gives:
- **True reproducibility**: same DB → same results always
- **Point-in-time correctness**: recs were computed using only data available at that time
- **Speed**: no engine overhead per day
- **Consistency**: RSF sees exactly what the production engine saw

Exception: `AUTONOMOUS_FORCE_EDGE` mode calls the engine with a synthetic `EDGE_PRESENT` regime fit to simulate a world without RCEE blocking.

### 2. Trading Calendar Resolution

Trading days are resolved from `ranking_runs` (filtered by `strategy_name IN config.strategies AND status='completed'`). This means:
- Only days with actual pipeline runs are simulated
- Gaps in the pipeline (weekends, holidays, errors) are automatically skipped
- No dependency on a separate trading calendar table

### 3. DB Queries

All queries are in `ReplayDayProcessor` with explicit `as_of_date` gates. No ORM-level lazy loading — raw SQL via `db.execute(text(...))` for clarity and control.

Critical queries:
- `_load_price_map(db, as_of_date)` → `{UUID: float}` close prices
- `_load_buy_recs(db, as_of_date, strategies)` → list of `_BuyRec`
- `_get_current_rank(db, stock_id, as_of_date, strategies)` → int | None

### 4. Slippage Model

```
BUY fill  = close × (1 + slippage_bps / 10_000)   # worse price
SELL fill = close × (1 - slippage_bps / 10_000)   # worse price
```

Default: 5 bps (0.05%). Configurable via `execution.slippage_bps`.

### 5. Position Sizing

Delegates to production `size_position(SizingInputs(...))`. Slot budget is:
```
slot_budget = available_cash × deploy_pct / slots_remaining
```

where `slots_remaining = max(1, max_positions - active_positions)`.

### 6. Exit Triggers

Reuses production pure functions from `app/portfolio/exit_monitor/triggers.py`:
- `check_rank_drop(current_rank, entry_rank)` → fires if rank > 40
- `check_alpha_decay(cum_alpha_pct, days_held)` → fires if negative alpha before day 15
- `check_regime_change(current_posture, entry_posture)` → fires if regime turns defensive/crisis
- `check_time_stop(days_held)` → fires after 30 days

First fired trigger wins; `exit_reason` is set to that trigger's code.

### 7. SIP Logic

- SIP is contributed on the **first trading day of each month** (when `contribution_day=FIRST_TRADING_DAY`)
- SIP is skipped on day 0 (initial cash already allocated)
- SIP increases `_cash` before the entry phase — so it's immediately deployable

---

## Metric Formulas

| Metric | Formula |
|---|---|
| Total Return | `(final_nav / initial_nav - 1) × 100` |
| CAGR | `(final_nav / initial_nav)^(1/years) - 1` |
| Sharpe | `mean(daily_returns) / std(daily_returns) × sqrt(252)` |
| Max Drawdown | `min((nav - running_peak) / running_peak) × 100` |
| Calmar | `CAGR / abs(MaxDD)` |
| Win Rate | `winning_trades / total_closed_trades × 100` |
| Profit Factor | `gross_profit / gross_loss` |
| Expectancy | `(win_rate × avg_win_pct) - ((1 - win_rate) × abs(avg_loss_pct))` |

---

## Running Tests

```bash
uv run --with pytest pytest tests/unit/replay/ -v
```

All 23 tests should pass. Tests are pure unit tests — no DB, no filesystem, no network.

---

## Adding a New Experiment Mode

1. Add entry to `ExperimentMode` enum in `experiment_config.py`
2. Add handling in `ReplayDayProcessor.process_day()` — specifically in the BUY rec loading section
3. Add corresponding YAML in `configs/`
4. Document in `EXPERIMENT_CATALOG.md`

---

## Known Limitations

1. **No intraday simulation** — all fills at close price with linear slippage
2. **No partial fills** — either full quantity or skip
3. **No margin/leverage** — cash-only
4. **No dividends** — only price return
5. **Single currency** — INR only, no FX
6. **Exit monitor uses unrealized % as alpha proxy** — production alpha decay uses more precise attribution; RSF simplifies to position P&L %
7. **PyYAML required** — install with `uv add pyyaml` if not present
