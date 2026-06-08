# Domain Boundaries

Pi-PM enforces strict separation between domains. Each domain owns specific decisions and must not leak responsibilities into adjacent layers.

**Takeover:** [`HANDOFF.md`](./HANDOFF.md) · **Architecture:** [`ARCHITECTURE.md`](./ARCHITECTURE.md)

## Domain Map

```
app/universe/       → Eligibility filtering (pre-ranking)
app/ranking/        → Scoring, normalization, ordering
app/validation/     → Forward-return IC, deciles, regime labels
app/regime_policy/  → Post-ranking gating replay (research only, Sprint 8.1)
app/factor_analytics/ → Factor IC analytics (read-only upstream, Sprint 8.2)
app/workspace_exit_research/ → Exit policy simulation (read-only upstream, Sprint 8.3)
app/workspace_research_reporting/ → Executive research reports (read-only upstream, Sprint 8.5)
app/recommendation/ → Conviction scoring and action assignment (Phase 2, deterministic)
app/portfolio/      → Exit monitor, reconciliation, analytics (Phase 2)
app/execution/      → Unified execution adapter, state machine (paper + live stub)
app/copilot/        → Explain-only Q&A over persisted engine output (read-only retrieval)
app/auth/           → JWT helpers and RBAC role/permission constants
app/backtest/       → Historical ranking replayer
app/market_data/    → Bar loading cache (shared infrastructure)
app/services/       → Orchestration and persistence
app/db/repositories/→ Data access only
app/api/            → HTTP contracts
```

## Universe Domain (`app/universe/`)

**Owns:**
- Membership, active status, data status checks
- Minimum history (63 trading days default)
- Minimum average daily traded value (ADTV)
- Minimum stock price
- Exclusion reason codes for filter phase

**Outputs:** `TradableUniverse` with `included` and `excluded` stocks.

**Must NOT:**
- Compute factor scores
- Assign ranks
- Normalize cross-sectional values

## Ranking Domain (`app/ranking/`)

**Owns:**
- Strategy registry and factor computation
- Percentile normalization
- Composite scoring and tie-breaking (score DESC, symbol ASC)
- `inputs_hash` construction
- Strategy-phase exclusions (`INSUFFICIENT_STRATEGY_HISTORY`, `FACTOR_COMPUTATION_FAILED`)

**Inputs:** `TradableUniverse` (included stocks only), strategy, benchmark.

**Must NOT:**
- Apply universe membership rules
- Modify stock master data
- Persist to database directly

## Market Data Cache (`app/market_data/`)

**Owns:**
- Session-scoped caching of loaded price bars
- Delegating cache misses to `MarketDataRepository`

**Used by:** `UniverseFilterEngine`, `MarketDataLoader`.

**Must NOT:**
- Apply business filters or scoring logic

## Service Layer (`app/services/`)

**Owns:**
- Transaction boundaries
- Idempotent run persistence
- Merging exclusion summaries into run metadata
- Resolving configuration defaults from `Settings`

**Must NOT:**
- Implement factor formulas
- Duplicate filter rules from universe domain

## Validation Domain (`app/validation/`)

**Owns:**
- Forward-return computation from performance snapshots
- Information coefficient (IC), decile spreads
- Regime classification (`{BULL|BEAR}_{LOW_VOL|HIGH_VOL}`)
- Full-universe campaign aggregation

**Must NOT:**
- Change ranking factors, weights, or normalization
- Apply regime policy gating (that is `app/regime_policy/`)

## Regime Policy Domain (`app/regime_policy/`) — Sprint 8.1

**Owns:**
- Deterministic ALLOW / BLOCK / REDUCE decisions from stored regime labels
- Historical replay overlay on existing ranking results
- Pooled period metrics and bootstrap confidence intervals for research

**Inputs (read-only):** `ranking_results`, `ranking_performance_snapshots`, `ranking_validation_reports.regime_label`, `validation_horizon_metrics`

**Must NOT:**
- Rerank securities or recompute factor scores
- Modify validation formulas or ranking strategies
- Wire into live ranking, paper trading, or automatic production activation

## Traceability (Sprint 7 / 7.1)

Implemented in `app/services/traceability_service.py` and repositories — **instrumentation only**.

**Must NOT:** Alter ranking scores, validation IC, or policy decisions.

## Recommendation Domain (`app/recommendation/`) — Phase 2

**Owns:**
- Deterministic conviction scoring (`conv_v1.1.0`)
- Action assignment (BUY / WATCH / HOLD / REJECT / EXIT_APPROVED)
- Reason codes for non-BUY outcomes

**Inputs (read-only):** ranking results, validation status, regime posture, portfolio slot state.

**Must NOT:**
- Import LLM or committee outputs into conviction or action
- Place trades or mutate portfolio positions directly (delegates to execution via services)

## Portfolio Domain (`app/portfolio/`, `app/services/portfolio_*.py`) — Phase 2

**Owns:**
- Position ledger, cash ledger, NAV snapshots
- Reconciliation, exit monitor, attribution analytics
- Slot and sector limit enforcement

**Must NOT:**
- Rerank securities or recompute conviction
- Call broker APIs directly (uses `ExecutionService`)

## Execution Domain (`app/execution/`) — Phase 2

**Owns:**
- Unified order lifecycle (paper + live adapter protocol)
- State machine transitions and execution audit trail
- Idempotent `client_order_id` handling

**Must NOT:**
- Approve recommendations (requires prior HITL approval row)
- Modify conviction or ranking

## Copilot Domain (`app/copilot/`) — Phase 2

**Owns:**
- Intent classification, grounded retrieval, citation validation
- Refusal patterns for trade/override/pick requests

**Must NOT:**
- Write to recommendation, portfolio, or execution tables
- Influence ranking, conviction, or trade approval

## Explicitly Out of Scope

- **Live broker execution** — Zerodha adapter is a contract stub; `enable_live_trading` defaults false
- **Risk pre-trade gates (AC-RISK)** — not implemented
- **LLM ranking / sizing / trade approval** — G8 non-goals (unchanged)
- **Live regime policy activation** — research replay only (Sprint 8.1)
- **Copilot trade execution** — explain-only by design

## Sprint 3.1 Additions

### Benchmark resilience boundary

Benchmark availability is determined inside `RankingEngine`. The universe domain does not know about benchmarks. Weight redistribution is a ranking-domain concern implemented in `app/ranking/normalizer.py`.

### Idempotency boundary

Idempotency is enforced in `RankingService` + `RankingRunRepository.find_completed_by_inputs_hash()`. The ranking engine remains a pure function: same inputs → same output, with no DB awareness.

### Failed run boundary

Run lifecycle (`PENDING` → `COMPLETED` / `FAILED`) is owned by repositories and `RankingService`. Failed runs never participate in idempotent reuse.

### Shared cache boundary

One `MarketDataCache` instance is created per `run_ranking()` call and passed to both universe filtering and ranking loading. This prepares Sprint 4 bar-sharing optimization without changing scoring behavior.

## Cross-Domain Types

| Type | Defined in | Used by |
|------|-----------|---------|
| `FilterDecision` | `app/universe/models.py` | Universe filter, ranking engine (exclusions) |
| `PriceBar` | `app/ranking/math_utils.py` | Universe filter, ranking loader |
| `StockSnapshot` | `app/universe/models.py` | Universe filter, ranking strategies |

These shared types are intentional for audit consistency. Consider extracting to `app/common/` if the coupling surface grows in Sprint 4+.
