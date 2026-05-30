# Domain Boundaries

Pi-PM enforces strict separation between domains. Each domain owns specific decisions and must not leak responsibilities into adjacent layers.

## Domain Map

```
app/universe/     → Eligibility filtering (pre-ranking)
app/ranking/      → Scoring, normalization, ordering
app/market_data/  → Bar loading cache (shared infrastructure)
app/services/     → Orchestration and persistence
app/api/          → HTTP contracts
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

## Explicitly Out of Scope (All Sprints to Date)

- Portfolio management
- Risk officer logic
- Trade execution
- LLM / LangGraph integration
- Performance analytics (snapshots are placeholder only)

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
