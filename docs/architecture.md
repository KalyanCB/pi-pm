# Pi-PM — Architecture

**Last updated:** 2026-05-31

---

## System Overview

Pi-PM is a layered monolith: a single FastAPI application with strict domain separation, PostgreSQL persistence, and deterministic quant pipelines. Future LLM agents will sit adjacent to — not inside — the ranking and portfolio layers.

```mermaid
flowchart TB
    subgraph Client
        UI[Swagger / curl / Postman]
    end

    subgraph API["API Layer (app/api/)"]
        Health[health]
        Stocks[stocks]
        MD[market-data]
        Rank[rankings]
        BT[backtest]
        Val[validation]
    end

    subgraph Services["Service Layer (app/services/)"]
        SS[StockService]
        MDS[MarketDataService]
        UFS[UniverseFilterService]
        RS[RankingService]
        BTS[BacktestService]
        SVS[SignalValidationService]
        FUVS[FullUniverseValidationService]
    end

    subgraph Domains["Domain Layer"]
        UF[UniverseFilterEngine]
        RE[RankingEngine]
        VAL[Validation Statistics]
        BC[Backtest Replayer]
    end

    subgraph Data["Data Layer"]
        Repo[Repositories]
        PG[(PostgreSQL)]
        Yahoo[Yahoo Finance]
    end

    UI --> API
    API --> Services
    Services --> Domains
    Services --> Repo
    Domains --> Repo
    Repo --> PG
    MDS --> Yahoo
```

---

## Core Principles

1. **LLMs never rank securities**
2. **LLMs never determine position sizes**
3. **LLMs never approve trades**
4. **LLMs never override risk controls**
5. **All money-related decisions must be deterministic**

---

## Layer Responsibilities

| Layer | Package | Responsibility |
|-------|---------|----------------|
| API | `app/api/` | HTTP contracts, query params, status codes |
| Services | `app/services/` | Transactions, orchestration, config defaults |
| Universe | `app/universe/` | Pre-ranking eligibility filters |
| Ranking | `app/ranking/` | Factor computation, normalization, scoring |
| Validation | `app/validation/` | Forward returns, IC, deciles, campaigns |
| Backtest | `app/backtest/` | Trading calendar, historical replayer |
| Market data | `app/market_data/` | Session-scoped bar cache |
| Providers | `app/providers/` | External data sources (Yahoo) |
| Repositories | `app/db/repositories/` | CRUD, queries |
| Models | `app/models/` | SQLAlchemy ORM (system of record) |

### Stub Packages (Future)

`app/agents/`, `app/workflows/`, `app/portfolio/`, `app/risk/`, `app/execution/`, `app/research/`, `app/monitoring/` — contain `__init__.py` only.

---

## Ranking Pipeline

```mermaid
sequenceDiagram
    participant API as POST /rankings/run
    participant RS as RankingService
    participant UF as UniverseFilterEngine
    participant Cache as MarketDataCache
    participant RE as RankingEngine
    participant Norm as PercentileNormalizer
    participant DB as PostgreSQL

    API->>RS: RankingRunRequest
    RS->>DB: create_pending(ranking_run)
    RS->>UF: build_tradable_universe()
    UF->>Cache: load bars per stock
    UF-->>RS: TradableUniverse (included + excluded)
    RS->>RE: score(included stocks, strategy)
    RE->>Cache: load extended history
    RE-->>RS: ScoredStock[]
    RS->>Norm: normalize(scores)
    Norm-->>RS: percentile scores
    RS->>DB: complete(run, results, snapshots)
    RS-->>API: RankingRunRead
```

### Ranking Properties

- **Deterministic:** Same inputs → same `inputs_hash` → same scores and ranks
- **Idempotent:** Completed runs with matching hash are reused
- **Auditable:** `score_components` JSONB per result; exclusion reasons in metadata
- **Versioned:** Strategy name + version in every run

---

## Universe Filter Pipeline

```mermaid
flowchart LR
    A[Universe Membership] --> B{Stock Active?}
    B -->|No| X[Exclude: STOCK_INACTIVE]
    B -->|Yes| C{Data Status ACTIVE?}
    C -->|No| X2[Exclude: DATA_STATUS_NOT_ACTIVE]
    C -->|Yes| D{≥63d History?}
    D -->|No| X3[Exclude: INSUFFICIENT_HISTORY]
    D -->|Yes| E{ADTV ≥ ₹1Cr?}
    E -->|No| X4[Exclude: INSUFFICIENT_TRADED_VALUE]
    E -->|Yes| F{Price ≥ ₹50?}
    F -->|No| X5[Exclude: MIN_PRICE_FAILED]
    F -->|Yes| G[Included in TradableUniverse]
```

Strategy-phase exclusions (applied inside `RankingEngine`):
- `INSUFFICIENT_STRATEGY_HISTORY` — e.g. 252 days for `breakout_v1`
- `FACTOR_COMPUTATION_FAILED`

---

## Backtest Pipeline (Sprint 4.1)

```mermaid
flowchart TB
    A[POST /backtest/generate-rankings] --> B[BacktestService]
    B --> C[TradingCalendar]
    C --> D[Benchmark-anchored trading days]
    D --> E[RankingReplayer]
    E --> F{For each as_of_date}
    F --> G[RankingService.run_ranking_with_outcome]
    G --> H[Idempotent via inputs_hash]
    H --> F
    F --> I[BacktestGenerationResult]
```

Output: one `ranking_runs` row per trading day in range.

---

## Validation Pipeline (Sprint 4.2)

```mermaid
flowchart TB
    A[POST /validation/runs/id/compute] --> B[SignalValidationService]
    B --> C[Load ranking_results]
    C --> D[MarketDataCache extended bars]
    D --> E[compute_forward_returns 5/10/20/60d]
    E --> F[classify_regime BULL/BEAR × VOL]
    F --> G[compute_horizon_metrics IC/deciles/hit rates]
    G --> H[Persist ranking_validation_report]
    G --> I[Update performance_snapshots]
```

### Regime Classification

| Dimension | Rule |
|-----------|------|
| Trend | BULL if close > SMA200; else BEAR |
| Volatility | HIGH_VOL if 20d annualized vol > threshold (default 20%); else LOW_VOL |
| Label | `{trend}_{vol}` e.g. `BULL_LOW_VOL` |

---

## Full-Universe Validation Campaign (Sprint 6.1)

```mermaid
flowchart TB
    A[POST /validation/full-universe/run] --> B[FullUniverseValidationService]
    B --> C[Create campaign PENDING]
    C --> D[BacktestService.generate_rankings]
    D --> E[NIFTY_500 + breakout_v1 per day]
    E --> F{For each ranking_run}
    F --> G[SignalValidationService.validate_run]
    G --> H[Record validation_run row]
    H --> F
    F --> I[campaign_aggregator pool all stock-days]
    I --> J[compute_full_horizon_metrics per horizon]
    J --> K[Persist metrics + deciles]
    K --> L[Campaign COMPLETED]
```

Pooled metrics aggregate **all stock-day observations** across validated days — not per-day averages of IC.

---

## Data Flow — End to End

```mermaid
flowchart LR
    subgraph External
        YF[Yahoo Finance]
    end

    subgraph Ingest
        YF -->|OHLCV| MD[market_data table]
        YF -->|status| ST[stocks.data_status]
    end

    subgraph Rank
        ST --> UF[Universe Filter]
        MD --> UF
        UF --> RE[Ranking Engine]
        MD --> RE
        RE --> RR[ranking_results]
        RE --> RUN[ranking_runs]
    end

    subgraph Validate
        RR --> FWD[Forward Returns]
        MD --> FWD
        FWD --> SNAP[performance_snapshots]
        FWD --> RPT[validation_reports]
    end

    subgraph Campaign
        RR --> POOL[Pooled Observations]
        SNAP --> POOL
        POOL --> MET[full_universe_validation_metrics]
        POOL --> DEC[full_universe_validation_deciles]
    end
```

---

## Dependency Injection

FastAPI `Depends()` in `app/api/deps.py` wires:

```
get_db → Session
get_*_repository → Repository(db)
get_ranking_service → RankingService(db, settings, repos, registry)
get_backtest_service → BacktestService(db, ranking_service, ...)
get_signal_validation_service → SignalValidationService(...)
get_full_universe_validation_service → FullUniverseValidationService(...)
```

---

## Configuration Resolution

API request fields are optional; services resolve from `Settings`:

```
universe_code  → ranking_default_universe_code  (default: PI_PM_CORE ⚠️)
strategy_name  → ranking_default_strategy         (default: momentum_v1)
strategy_version → ranking_default_strategy_version
benchmark_symbol → ranking_default_benchmark      (default: ^NSEI)
```

Full-universe validation **overrides** defaults to `NIFTY_500` + `breakout_v1`.

---

## Error Handling

| Exception | HTTP Status |
|-----------|-------------|
| `NotFoundError` | 404 |
| `ValidationError` | 422 |
| `InvalidSymbolError` | 422 |
| `StrategyNotFoundError` | 422 |
| `ProviderError` | 502 |
| `RankingError` | 500 |
| `PiPMError` | 400 |

---

## Deployment Architecture

```mermaid
flowchart TB
    subgraph Docker Compose
        API[api container<br/>uvicorn :8000]
        DB[(db container<br/>postgres:16 :5432)]
    end

    API -->|DATABASE_URL| DB
    API -->|alembic upgrade head| DB

    Dev[Developer localhost:8000] --> API
```

- **Production compose:** `docker/docker-compose.yml` — code baked into image at build time
- **Dev compose:** `docker/docker-compose.dev.yml` — volume mount `..:/app`, requires container restart for code changes (no `--reload` in entrypoint)
- **Local dev:** `uvicorn app.main:app --reload` against Docker DB only

Entrypoint: `scripts/entrypoint.sh` → migrate → uvicorn

---

## Testing Architecture

- **Integration tests:** SQLite in-memory with PostgreSQL type compilers (JSONB, UUID)
- **Unit tests:** Pure domain logic (statistics, factors, filters)
- **Fixtures:** `tests/conftest.py` — db session, FastAPI TestClient, mock Yahoo provider
- **Count:** 121 tests across 39 modules

---

## Related Documentation

- `docs/domain-boundaries.md` — Original domain boundary spec
- `docs/architecture.md` — Legacy sprint-focused architecture (superseded in part by this doc)
- `docs/DATABASE_SCHEMA.md` — Table definitions
- `docs/API_REFERENCE.md` — Endpoint catalog
