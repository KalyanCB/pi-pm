# Pi-PM Phase 2 — Implementation Summary

**Date:** 2026-06-05  
**Branch:** `feature/see-v2`  
**Tests:** 574 passing, 0 failures  
**API version:** 0.4.1

---

## Table of Contents

1. [P1–P2 — Recommendation Engine](#p1p2--recommendation-engine)
2. [P3 — Recommendation Performance & Trust Layer](#p3--recommendation-performance--trust-layer)
3. [M2 — Portfolio Engine](#m2--portfolio-engine)
4. [Ops — Universe & Market Data](#ops--universe--market-data)
5. [Architecture Decisions](#architecture-decisions)
6. [Database Migrations](#database-migrations)
7. [Full API Reference](#full-api-reference)
8. [Test Coverage](#test-coverage)
9. [Non-Negotiables Status](#non-negotiables-status)

---

## P1/P2 — Recommendation Engine

### What was built

The Recommendation Engine sits **between Validation and ARGS** per ADR-021. It transforms validated ranked stocks into auditable product recommendations.

### New files

| File | Purpose |
|------|---------|
| `app/recommendation/conviction_scorer.py` | Deterministic 0–100 conviction scorer (conv_v1.1.0) |
| `app/recommendation/engine.py` | Action assignment engine |
| `app/services/recommendation_service.py` | Orchestration service |
| `app/db/repositories/recommendation_repository.py` | CRUD for all recommendation entities |
| `app/models/recommendation.py` | 5 SQLAlchemy models |
| `app/api/v1/recommendations.py` | 9 REST endpoints |

### Conviction Formula (conv_v1.1.0)

```
conviction_score = clamp(round(
  0.26 × S_rank_quality
+ 0.32 × S_validation
+ 0.16 × S_ic_factor
+ 0.16 × S_regime
+ 0.10 × S_exit_health
), 0, 100)
```

**No LLM. No committee inputs. 100% deterministic.**

| Sub-score | Source | Range |
|-----------|--------|-------|
| `S_rank_quality` | Rank pool membership + score separation | 0–100 |
| `S_validation` | 20d Spearman IC; `insufficient_data` → fixed 35 | 0–100 |
| `S_ic_factor` | Factor IC median (ic_spearman) | 0–100 |
| `S_regime` | risk_on=75, neutral=55, defensive=25 | 0–100 |
| `S_exit_health` | Position state (clean/deteriorating/decay) | 0–100 |

### Conviction Bands

| Band | Score | Recommendation cap |
|------|-------|--------------------|
| BLOCKED | 0–29 | REJECT |
| LOW | 30–49 | WATCH |
| MEDIUM | 50–69 | WATCH or BUY (if slots) |
| HIGH | 70–84 | BUY candidate |
| EXCEPTIONAL | 85–100 | BUY priority (max 3/day) |

### Action Rules

| Rule | Condition | Action |
|------|-----------|--------|
| R-ENTRY-01 | rank ≤ 20 AND validation completed | Eligible |
| R-ENTRY-02 | validation `insufficient_data` | Max WATCH |
| R-ENTRY-03 | conviction = BLOCKED | REJECT |
| R-ENTRY-04 | MEDIUM+ AND regime allows AND slots open | BUY |
| R-ENTRY-05 | LOW or slots full | WATCH |
| R-ENTRY-06 | rank 1–5 AND `rank_v2_promoted=false` | Cap at MEDIUM |
| R-HOLD-01 | ACTIVE, no exit trigger | HOLD |
| R-EXIT-01 | rank > 40 (deterioration) | EXIT_APPROVED + `EXIT_RISK` |
| R-EXIT-02 | alpha decay breached | EXIT_APPROVED + `ALPHA_DECAY` |
| R-EXIT-03 | regime turned defensive | EXIT_APPROVED + `REGIME_BLOCK` |
| R-EXIT-04 | holding_days ≥ 30 | EXIT_APPROVED + `TIME_STOP` |

### Recommendation Lifecycle

```
CANDIDATE → APPROVED → ACTIVE → EXIT_APPROVED → CLOSED
```

### DB Tables (migration 0019)

- `recommendation_configs` — versioned rule weights
- `recommendation_runs` — one per ranking_run per strategy
- `recommendation_results` — per-stock action + conviction
- `recommendation_approvals` — human HITL audit trail
- `recommendation_outcomes` — realized performance

### Daily Batch Integration

`RECOMMENDATIONS` phase inserted **after VALIDATION**, before regime/factor phases.

```
INGEST → RANKINGS → VALIDATION → RECOMMENDATIONS → REGIME → FACTOR_IC → EXIT_RESEARCH
```

### ARGS Packet Enrichment

Every ARGS investment review packet now includes a deterministic `recommendation` block:

```json
{
  "recommendation": {
    "action": "WATCH",
    "conviction_score": 62,
    "conviction_band": "MEDIUM",
    "reason_codes": ["VALIDATION_TAIL_PENDING"],
    "engine_version": "rec_v1.0.0",
    "ranking_run_id": "<uuid>"
  }
}
```

**Committees cannot mutate this block (R-ARGS-04).**

### APIs — Recommendations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/recommendations/run` | Trigger for a ranking_run_id |
| GET | `/api/v1/recommendations/latest` | Latest by strategy/date |
| GET | `/api/v1/recommendations/daily` | All strategies for a date in one call |
| GET | `/api/v1/recommendations/queue` | BUY + EXIT_APPROVED CANDIDATE queue |
| GET | `/api/v1/recommendations/{run_id}` | Full run results |
| GET | `/api/v1/recommendations/{run_id}/stocks/{symbol}` | Per-symbol card |
| GET | `/api/v1/recommendations/why-not/{symbol}` | Deterministic rejection explanation |
| POST | `/api/v1/recommendations/{id}/approve` | Human HITL approve |
| POST | `/api/v1/recommendations/{id}/reject` | Human HITL reject |

---

## P3 — Recommendation Performance & Trust Layer

### What was built

A pure analytics overlay — observation only. No metric feeds back into conviction, engine, or committees.

### New files

| File | Purpose |
|------|---------|
| `app/recommendation_analytics/calculator.py` | Pure metric functions — win rate, alpha, profit factor, calibration |
| `app/recommendation_analytics/trust_metrics.py` | Calibration (Spearman ρ), stability, reliability |
| `app/recommendation_analytics/dtos.py` | Mobile-ready dataclass DTOs |
| `app/services/recommendation_analytics_service.py` | DB orchestration |
| `app/db/repositories/recommendation_outcome_repository.py` | Filtered outcome queries |
| `app/api/v1/recommendation_analytics.py` | 6 REST endpoints |

### RecommendationOutcome Extended (migration 0020)

Added to `recommendation_outcomes`:

| Column | Type | Purpose |
|--------|------|---------|
| `symbol` | varchar | Denormalised for analytics |
| `strategy_name` | varchar | Denormalised |
| `conviction_band` | varchar | Band at entry time |
| `regime_label` | varchar | Regime at recommendation time |
| `days_held` | int | Renamed from holding_days |
| `target_hit` | bool | Price target reached |
| `stop_hit` | bool | Stop loss triggered |
| `exit_reason` | varchar | Human-readable exit |
| `committee_advisory` | varchar | ARGS advisory at entry (display only) |

### Quality Metrics

| Metric | Formula |
|--------|---------|
| Win rate | COUNT(WIN) / COUNT(closed) |
| Average gain | MEAN(alpha_pct) WHERE WIN |
| Average loss | MEAN(alpha_pct) WHERE LOSS |
| Profit factor | SUM(gains) / ABS(SUM(losses)) |
| Average alpha | MEAN(alpha_pct) all closed |
| Median alpha | MEDIAN(alpha_pct) |
| Target hit rate | COUNT(target_hit) / COUNT(closed) |
| Stop hit rate | COUNT(stop_hit) / COUNT(closed) |
| Avg days held | MEAN(days_held) |

### Trust Metrics

**Conviction Calibration**  
Spearman rank correlation of expected band order (EXCEPTIONAL > HIGH > MEDIUM > LOW) vs actual win rates. `ρ ≥ 0.6` = calibrated.

**Recommendation Stability**  
`churn_rate = daily_action_changes / total_evaluations`  
`stability_score = 1 - churn_rate`  
Also tracks reversals (BUY → WATCH → BUY within 3 sessions).

**Recommendation Reliability**  
`reliability_rate = COUNT(completed_validation) / COUNT(all_recommendations)`

**Overall Trust Score**  
`trust = mean([(ρ+1)/2, stability_score, reliability_rate])`  — composite 0–1.

### APIs — Analytics

| Method | Endpoint | Answers |
|--------|----------|---------|
| GET | `/api/v1/analytics/recommendations/summary` | Are recommendations working? |
| GET | `/api/v1/analytics/recommendations/conviction` | Do HIGH picks outperform MEDIUM? |
| GET | `/api/v1/analytics/recommendations/regime` | Do regimes predict outcomes? |
| GET | `/api/v1/analytics/recommendations/committee` | Is ARGS adding advisory value? |
| GET | `/api/v1/analytics/recommendations/trust` | Should I trust the next recommendation? |
| GET | `/api/v1/analytics/recommendations/symbol/{symbol}` | Per-symbol history + why-not |

All endpoints accept `?strategy_name=&from_date=&to_date=` filters.

---

## M2 — Portfolio Engine

### What was built

Capital management, regime-based position count, conviction-weighted allocation, paper trade simulation, and real `portfolio_context` in ARGS packets.

### New files

| File | Purpose |
|------|---------|
| `app/models/portfolio_position.py` | `PortfolioConfig` + extended `PortfolioPosition` |
| `app/services/portfolio_service.py` | Capital math, regime slots, allocation, position lifecycle |
| `app/services/paper_trade_service.py` | Fill simulation ± slippage |
| `app/api/v1/portfolio.py` | 8 REST endpoints |

### Capital Model

| Concept | Default |
|---------|---------|
| `total_equity` | Owner-configured (default ₹10,00,000) |
| `deployable_capital` | `total_equity × 0.85` |
| `cash_floor` | 15% |
| `reserve` | 2% |

### Regime Slot Table (PO-tunable)

| Regime | Max positions | Max BUY/day |
|--------|--------------|-------------|
| risk_on | 8 | 2 |
| neutral | 6 | 1 |
| defensive | 4 | 0 |
| crisis | 2 | 0 |

### Conviction-Weighted Allocation

```
slot_budget = deployable_capital / max_active_slots
position_notional = slot_budget × conviction_weight
```

| Band | Weight | Single-name cap |
|------|--------|-----------------|
| EXCEPTIONAL | 1.15× | 18% NAV |
| HIGH | 1.00× | 18% NAV |
| MEDIUM | 0.75× | 18% NAV |
| LOW | 0 (no BUY) | — |

Sector cap: 30% NAV.

### Paper Trade Fill Rules

| Rule | Behaviour |
|------|-----------|
| Price | Last NSE close from `market_data` |
| BUY slippage | +5 bps |
| SELL slippage | −5 bps |
| Partials | Not supported (v1) — full quantity or reject |
| Fees | ₹20 flat per leg |

### ARGS Packet Fix

`portfolio_context` in ARGS packets now reads **real DB data**:

```json
{
  "portfolio_context": {
    "existing_position": true,
    "quantity": 75.0,
    "avg_cost": 1850.50,
    "market_value": 145000.0,
    "weight_pct": 14.5,
    "unrealized_pnl": 6000.0,
    "conviction_band": "HIGH",
    "entry_date": "2026-05-15",
    "cash_pct": 0.32,
    "slots_available": 3
  }
}
```

Previously hardcoded to `{"existing_position": false}`.

### APIs — Portfolio

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/portfolio/summary` | NAV, cash, deployable, slots |
| GET | `/api/v1/portfolio/positions` | Open positions with P&L |
| GET | `/api/v1/portfolio/limits` | Regime headroom, can_add_position |
| GET | `/api/v1/portfolio/allocation` | Size calculator by conviction band |
| POST | `/api/v1/portfolio/config` | Set equity + parameters |
| POST | `/api/v1/portfolio/recompute` | Mark-to-market all positions |
| POST | `/api/v1/portfolio/trades/entry` | Simulate BUY fill |
| POST | `/api/v1/portfolio/trades/exit` | Simulate SELL fill |

---

## Ops — Universe & Market Data

### Bootstrap endpoint (NEW)

```
POST /api/v1/stocks/bootstrap
```
Loads all 500 NIFTY 500 stocks from `data/nifty500_constituents.csv` into the universe. Idempotent. Required before first ingest on a fresh DB.

**Response:**
```json
{
  "universe_code": "NIFTY_500",
  "constituents_loaded": 500,
  "stocks_created": 500,
  "membership_total": 500
}
```

### Universe ingest endpoint (NEW)

```
POST /api/v1/market-data/ingest-universe
```

Ingests market data for all NIFTY 500 stocks **including `^NSEI` benchmark** automatically.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `universe_code` | `NIFTY_500` | Universe to ingest |
| `months_back` | 13 | Months of history (if no from_date) |
| `from_date` | — | Explicit start date |
| `to_date` | today | Explicit end date |
| `batch_size` | 25 | Symbols per Yahoo batch |
| `benchmark_symbol` | `^NSEI` | Always included |

**Parallel year chunk ingestion (5 concurrent curls):**
```bash
# Year A: 2021–2022
curl -X POST .../ingest-universe -d '{"from_date":"2021-06-05","to_date":"2022-06-05"}'

# Year B: 2022–2023
curl -X POST .../ingest-universe -d '{"from_date":"2022-06-05","to_date":"2023-06-05"}'

# ... C, D, E
```

### Daily batch fixes

- `RECOMMENDATIONS` phase added after `VALIDATION`
- Fresh DB detection: `has_historical_data()` → use `FULL_REFRESH` on empty DB
- Ingest period changed from `5y` to `1y` for daily top-up
- `force_ingest` correctly scoped to incremental mode

### Docker fixes

- `data/` directory now copied into container image (was missing)
- `^NSEI` benchmark always included in universe ingest
- Dummy VEDANTA placeholder symbols removed from `nifty500_constituents.csv`

---

## Architecture Decisions

| ADR | Decision |
|-----|----------|
| ADR-021 | Recommendation Engine sits between Validation and ARGS |
| ADR-022 | Recommendation Performance Framework — analytics are observation-only; no feedback into engine or committees |

---

## Database Migrations

| Migration | Description |
|-----------|-------------|
| `20260606_0019` | Recommendation Platform: 5 new tables |
| `20260606_0020` | Extend `recommendation_outcomes`: analytics columns + indexes |
| `20260606_0021` | Portfolio Engine: `portfolio_configs` + extend `portfolio_positions` |

**Run:** `alembic upgrade head`

---

## Full API Reference

### Recommendations
```
POST /api/v1/recommendations/run
GET  /api/v1/recommendations/latest?strategy_name=&as_of_date=
GET  /api/v1/recommendations/daily?as_of_date=&action=
GET  /api/v1/recommendations/queue
GET  /api/v1/recommendations/{run_id}?action=
GET  /api/v1/recommendations/{run_id}/stocks/{symbol}
GET  /api/v1/recommendations/why-not/{symbol}?strategy_name=
POST /api/v1/recommendations/{id}/approve
POST /api/v1/recommendations/{id}/reject
```

### Recommendation Analytics
```
GET /api/v1/analytics/recommendations/summary?strategy_name=&from_date=&to_date=
GET /api/v1/analytics/recommendations/conviction
GET /api/v1/analytics/recommendations/regime
GET /api/v1/analytics/recommendations/committee
GET /api/v1/analytics/recommendations/trust
GET /api/v1/analytics/recommendations/symbol/{symbol}
```

### Portfolio
```
GET  /api/v1/portfolio/summary?as_of_date=
GET  /api/v1/portfolio/positions
GET  /api/v1/portfolio/limits?as_of_date=
GET  /api/v1/portfolio/allocation?conviction_band=&last_price=&sector=
POST /api/v1/portfolio/config
POST /api/v1/portfolio/recompute
POST /api/v1/portfolio/trades/entry
POST /api/v1/portfolio/trades/exit
```

### Market Data
```
POST /api/v1/market-data/ingest
POST /api/v1/market-data/ingest-universe
```

### Stocks
```
POST /api/v1/stocks/bootstrap
GET  /api/v1/stocks
GET  /api/v1/stocks/{symbol}
GET  /api/v1/stocks/{symbol}/market-data
```

---

## Test Coverage

| Module | Tests | Key criteria |
|--------|-------|-------------|
| `conviction_scorer` | 13 | AC-CS-01..07, golden fixture, LLM-lint |
| `recommendation engine` | 17 | R-ENTRY/HOLD/EXIT rules, AC-RE-01..06, 4 exit triggers |
| `recommendation analytics` | 18 | AC-RP-01..09, calibration, regime, committee |
| `trust metrics` | 11 | Calibration ρ, stability churn, reliability, composite score |
| `portfolio service` | 15 | AC-PE-01..04, regime slots, allocation weights |
| **Total new** | **74** | |
| **Total suite** | **574** | 0 failures |

---

## Non-Negotiables Status

| Rule | Status |
|------|--------|
| LLMs never rank, score conviction, size positions, or approve trades | ✅ Enforced — lint tests in unit suite |
| Ranking and validation math frozen | ✅ Untouched |
| `ARGS_QRC_USE_SQE=false` in prod | ✅ Unchanged |
| Recommendation Engine after Validation, before ARGS | ✅ Implemented |
| ARGS committee outputs: store/display/explain only | ✅ `recommendation` block read-only in packets |
| Conviction: no committee weight | ✅ `conv_v1.1.0` — 5 deterministic inputs only |
| Analytics: no feedback into engine | ✅ Analytics module has no write paths to recommendation tables |
| Portfolio: no auto-execution | ✅ All fills require explicit `POST /trades/entry` or `/exit` |

---

## What's Next (M2 remaining + M3)

| Milestone | Item | Status |
|-----------|------|--------|
| M2 | Paper trading reconciliation + attribution | Pending |
| M2 | Exit monitor job (live EXIT_APPROVED from exit research) | Pending |
| M2 | ARGS live `portfolio_context` → ✅ Done | Done |
| M3 | ARGS advisory actions mapping | Not started |
| M3 | Broker adapter contract | Not started |
| M3 | Auth / multi-tenant | Not started |
| M4 | Mobile MVP | Not started |
| M4 | AI Copilot grounded Q&A | Not started |
