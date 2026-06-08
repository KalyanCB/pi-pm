# ADR-028: Paper Trading Pilot Readiness (90-Day Unattended)

**Status:** Accepted  
**Date:** 2026-06-05  
**Deciders:** Principal Quant Platform Engineer  
**Related:** [ADR-024](./ADR-024-Portfolio-State-Source-Of-Truth.md), [ADR-021](./ADR-021-Recommendation-Platform-Architecture.md), [06_PAPER_TRADING_PRD.md](../product/06_PAPER_TRADING_PRD.md)

---

## Context

Pi-PM has a production research pipeline (ingest → rank → validate → recommend) and an M2 portfolio stack (paper trades, NAV, reconciliation, exit monitor). For a **90-day unattended paper trading pilot**, operations must run daily without manual API calls.

**Constraint:** This ADR adds **orchestration and lineage only**. It does not modify ranking, validation, recommendation generation, conviction formula, or committee logic.

---

## Decision

### 1. Extend daily batch with optional portfolio phases

When `phases.portfolio=true` on `POST /api/v1/ops/daily-batch/runs`, execute after research phases:

| Phase | Service | Purpose |
|-------|---------|---------|
| `portfolio_recompute` | `PortfolioService.recompute()` | Mark-to-market |
| `exit_monitor` | `ExitMonitorService.run()` | Advisory exit candidates |
| `paper_trading` | `PaperPilotOps` | Simulated fills (if `pilot_auto_execute`) |
| `portfolio_nav` | `PortfolioNavService.snapshot()` | Daily NAV history |
| `portfolio_reconcile` | `ReconciliationService.run()` | Ledger integrity gate |

Implementation: `app/ops/daily_batch/paper_pilot_ops.py`, wired in `DailyBatchService`.

### 2. Pilot automation flags (operational, not engine changes)

| Flag | Behaviour |
|------|-----------|
| `pilot_auto_approve` | Calls `RecommendationService.approve()` for BUY — lifecycle only |
| `pilot_auto_execute` | Calls `PaperTradeService.execute_entry/exit()` — simulation only |
| `ingest_portfolio_benchmarks` | Also ingests `^CRSLDX` (NIFTY 500 TR) alongside `^NSEI` |

Human HITL remains the production default (`pilot_auto_*=false`).

### 3. Trade ledger lineage hardening

`PaperTradeService` now populates:

- `paper_trades.ranking_run_id` from `recommendation_runs.ranking_run_id`
- `metadata.recommendation_run_id`
- `portfolio_positions.strategy_name`
- `recommendation_outcomes.strategy_name`, `regime_label`, `benchmark_return_pct`, `exit_reason_codes`

### 4. Reconciliation reported NAV source

`ReconciliationService` uses latest `portfolio_nav_history.total_equity` as `reported_nav` (not static `portfolio_configs.total_equity`), eliminating false FAIL after trading.

### 5. Benchmark policy for pilot

| Use case | Symbol | Notes |
|----------|--------|-------|
| Ranking / regime / validation | `^NSEI` | Unchanged |
| NAV day-return alpha | `^NSEI` | Unchanged |
| Portfolio analytics comparison | `^CRSLDX` | Ingested when portfolio phases on |
| Holding-period outcome alpha | `^NSEI` cumulative | Computed at exit in `PaperTradeService` |

Document split; align in M3 if PO requires single benchmark.

### 6. Dashboards

`scripts/generate_paper_trading_dashboard.py` emits:

- `docs/paper-pilot/dashboards/PILOT_DASHBOARD.md`
- `docs/paper-pilot/dashboards/HEALTH_DASHBOARD.md`
- `docs/paper-pilot/dashboards/RECONCILIATION_DASHBOARD.md`

---

## Consequences

### Positive

- Single daily batch invocation can run research + portfolio ops
- Full lineage in batch trace (`recommendation_run_ids`, `paper_trade_ids`, etc.)
- 90-day pilot feasible with `pilot_auto_execute=true`

### Negative / deferred

- Committee remains on-demand (not batch-scheduled)
- Exit monitor still advisory — human or `pilot_auto_execute` for exits
- No CI gate for portfolio E2E yet
- `approval_id` FK on `paper_trades` deferred (metadata only)

---

## Non-goals (explicit)

- Live broker integration
- Changing recommendation rules or conviction weights
- Auto-running ARGS committees in batch
- Mobile dashboard UI (markdown/JSON only for pilot)
