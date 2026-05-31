# Pi-PM — Decision Log

**Last updated:** 2026-05-31

Architectural and product decisions with context, alternatives considered, and rationale.

---

## ADR-001: Deterministic Core, LLM-Adjacent Research

**Date:** Sprint 1 (foundational)  
**Status:** Accepted

### Context

Pi-PM aims to combine AI capabilities with portfolio management. Need to define where AI is allowed.

### Decision

LLMs are **never** used for:
- Security ranking
- Position sizing
- Trade approval
- Risk control override

LLMs may be used (future) for:
- Narrative research on already-ranked stocks
- Summarizing filings and news
- Human-readable report generation

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| LLM-generated rankings | Non-reproducible, non-auditable, hallucination risk |
| Hybrid LLM + quant ensemble | Complexity; can't attribute performance |
| Full quant, no LLM | Misses research augmentation value |

### Consequences

- All ranking logic in pure Python with versioned strategies
- `research_reports` table separate from `ranking_results`
- Future agents read rankings as input, never write them

---

## ADR-002: PostgreSQL as System of Record

**Date:** Sprint 1  
**Status:** Accepted

### Decision

PostgreSQL for all persistent state. SQLAlchemy 2.0 ORM. Alembic migrations.

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| SQLite for production | No concurrent write support at scale |
| MongoDB | Relational joins needed for ranking/validation |
| TimescaleDB | Premature; daily bars sufficient for now |

### Consequences

- JSONB for flexible metadata (`score_components`, `horizon_metrics`)
- UUID primary keys throughout
- Docker Compose with Postgres 16

---

## ADR-003: Yahoo Finance as Primary Data Source

**Date:** Sprint 2  
**Status:** Accepted (with caveats)

### Decision

Use `yfinance` / Yahoo Finance for NSE OHLCV data with `^NSEI` as benchmark.

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| NSE official API | Cost, complexity, authentication |
| Alpha Vantage | Rate limits, US-centric |
| Manual CSV import | Not sustainable for 500 stocks |

### Consequences

- Ingest fails in proxy-restricted environments
- `data_status` tracking essential for recovery
- Recovery scripts needed (`recover_universe.py`)
- 4 symbols may remain ERROR indefinitely

### Risk

Yahoo data quality/delisting not fully validated. Acceptable for personal use.

---

## ADR-004: Strict Domain Boundaries

**Date:** Sprint 3  
**Status:** Accepted

### Decision

Separate packages with explicit ownership:
- `app/universe/` — eligibility only
- `app/ranking/` — scoring only
- `app/validation/` — forward returns and metrics only
- `app/services/` — orchestration only

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Monolithic ranking service | Filter logic leaked into scoring |
| Microservices | Over-engineering for single-user app |

### Consequences

- Documented in `docs/domain-boundaries.md`
- Exclusion codes split: filter-phase vs strategy-phase
- Services merge exclusion summaries into metadata

---

## ADR-005: Percentile Normalization for Cross-Sectional Ranking

**Date:** Sprint 3  
**Status:** Accepted

### Decision

Normalize factor values to percentiles (0–1) within each day's cross-section before weighted composite scoring.

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Z-score normalization | Sensitive to outliers in small universes |
| Raw weighted sum | Different factor scales incomparable |
| Rank-only (no scores) | Loses magnitude information for validation IC |

### Consequences

- `PercentileNormalizer` in `app/ranking/normalizer.py`
- Ties broken by symbol ascending after score descending
- IC computed on normalized scores vs forward returns

---

## ADR-006: Inputs Hash Idempotency

**Date:** Sprint 3.1  
**Status:** Accepted

### Decision

SHA-256 hash of (strategy, version, universe, date, filter config, benchmark) stored as `inputs_hash`. Only `COMPLETED` runs with matching hash are reused.

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| No idempotency | Duplicate work on backfill |
| Reuse failed runs | Failed runs may have partial/wrong data |
| Hash includes bar data | Too volatile; strategy inputs are sufficient |

### Consequences

- Pending/failed runs have `inputs_hash = NULL`
- Backtest replayer benefits from automatic reuse
- Same inputs always produce same scores (deterministic)

---

## ADR-007: Benchmark-Dependent Factor Exclusion with Weight Redistribution

**Date:** Sprint 3.1  
**Status:** Accepted

### Decision

When benchmark (`^NSEI`) is missing or has insufficient history, exclude `relative_strength` and `relative_strength_acceleration` factors. Redistribute their weights proportionally among remaining factors. Do **not** fail the ranking run.

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Fail ranking without benchmark | Too brittle for partial data |
| Equal weight redistribution | Distorts intended factor emphasis |
| Use sector ETF as fallback | Not implemented; adds complexity |

### Consequences

- Metadata records `benchmark_available`, `effective_weights`
- Breakout strategy has 2 benchmark-dependent factors (20% combined weight)
- Ranking continues with 80% of intended factor set

---

## ADR-008: Trading-Day Forward Returns (Not Calendar Days)

**Date:** Sprint 4.2  
**Status:** Accepted

### Decision

Forward returns computed over N **trading days** (days with price bars), not calendar days.

Horizons: 5, 10, 20, 60 trading days.

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Calendar day returns | Weekend/holiday gaps distort comparison |
| Weekly/monthly only | Too coarse for short-term signal validation |

### Consequences

- `compute_forward_returns()` walks bar series
- Stocks near end of data may have NULL returns for longer horizons
- `sample_summary.horizon_valid_counts` tracks coverage

---

## ADR-009: Regime Classification for Conditional Analysis

**Date:** Sprint 4.2  
**Status:** Accepted

### Decision

Classify each validation date into 4 regimes:
- Trend: BULL (close > SMA200) / BEAR
- Volatility: HIGH_VOL (>20% annualized) / LOW_VOL

Store regime on validation report. Aggregate IC by regime in summary API.

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| No regime analysis | Misses conditional performance |
| VIX-based regimes | No VIX data ingested |
| More granular regimes | Overfitting risk with limited history |

### Consequences

- `classify_regime()` in `app/validation/regimes.py`
- Summary API returns `regime_ic` breakdown
- Best/worst regime identified in cross-run summary

---

## ADR-010: NIFTY 500 as Primary Universe

**Date:** Sprint 5.1  
**Status:** Accepted

### Decision

Expand from `PI_PM_CORE` (~15 stocks) to `NIFTY_500` (504 constituents) as the primary validation universe. Bootstrap from CSV rather than live NSE API.

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| NIFTY 50 only | Too small for statistical validation |
| All NSE stocks | Data ingest impractical |
| Live NSE index API | Authentication, rate limits |

### Consequences

- `data/nifty500_constituents.csv` as source of truth
- `UniverseBootstrapService` for idempotent membership creation
- Must explicitly pass `universe_code: NIFTY_500` in API (default remains `PI_PM_CORE`)

---

## ADR-011: Breakout Strategy as Separate Versioned Strategy

**Date:** Sprint 5  
**Status:** Accepted

### Decision

Implement `breakout_v1` as a new strategy in the registry, not a modification of `momentum_v1`. Requires 252-day history. 8 factors with distinct weights.

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Extend momentum_v1 with breakout factors | Conflates two hypotheses |
| Single mega-strategy | Can't compare momentum vs breakout |
| ML feature selection | Violates deterministic principle |

### Consequences

- Both strategies coexist in registry
- Separate validation campaigns per strategy
- 252-day history eliminates more stocks than 63-day filter

---

## ADR-012: Pooled Campaign Metrics vs Per-Day Averaged IC

**Date:** Sprint 6.1  
**Status:** Accepted

### Decision

Full-universe validation pools **all stock-day observations** across validated ranking dates into a single IC/decile calculation per horizon. Not an average of per-day ICs.

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Average daily IC | Small days overweighted equally with large days |
| Per-day IC only (existing Sprint 4.2) | Insufficient for production decision |
| Fama-MacBeth regression | Over-engineering for current scale |

### Consequences

- `campaign_aggregator.py` joins all results + snapshots
- `sample_size` reflects total observations (e.g. 335 days × 439 stocks)
- `ranked_days` tracks number of validated dates
- New campaign tables separate from per-run validation reports

---

## ADR-013: Pearson IC + Spearman Rank IC as Separate Metrics

**Date:** Sprint 6.1  
**Status:** Accepted

### Decision

Report both Pearson IC (linear correlation of scores vs returns) and Spearman Rank IC (rank correlation) in full-universe campaigns. Sprint 4.2 per-run validation uses Spearman only.

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Spearman only | User requested both |
| Pearson only | Sensitive to outliers in returns |

### Consequences

- `pearson_ic()` and `spearman_ic()` in `statistics.py`
- Campaign metrics store both as `ic_pearson` and `rank_ic_spearman`
- Summary API exposes as `ic` and `rank_ic`

---

## ADR-014: Validation Gate Before New Signals

**Date:** Sprint 6.1  
**Status:** Accepted (in progress)

### Decision

No new signals, indicators, AI models, news, sentiment, options, or commodities until Sprint 6.1 answers five success criteria with data.

### Rationale

Building more signals before validating existing ones risks compound complexity without knowing if the foundation works.

### Consequences

- Roadmap P3 items explicitly blocked
- Sprint 6.2 focused on analysis, not new factors
- Production deployment decision deferred

---

## ADR-015: Docker Image Build vs Volume Mount

**Date:** Operational (Sprint 6.1)  
**Status:** Accepted with documentation

### Decision

Production Docker Compose bakes code into image at build time. Dev compose mounts source but requires container restart (no `--reload` in entrypoint).

### Consequences

- Code changes require `docker compose build api && docker compose up -d api`
- Stale Docker image caused 404 on Sprint 6.1 endpoints
- Local `uvicorn --reload` recommended for active development

---

## Decision Template (Future Entries)

```markdown
## ADR-NNN: Title

**Date:** Sprint X  
**Status:** Proposed | Accepted | Deprecated

### Context
What is the issue?

### Decision
What was decided?

### Alternatives Considered
What else was evaluated?

### Consequences
What are the implications?
```

---

## Related Documentation

- `docs/ARCHITECTURE.md` — System design
- `docs/domain-boundaries.md` — Domain rules
- `docs/ROADMAP.md` — Future plans
- `docs/SPRINT_HISTORY.md` — When decisions were implemented
