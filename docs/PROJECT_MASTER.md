# Pi-PM — Project Master

**Last updated:** 2026-05-31  
**Repository:** `/Users/kalyancb/pi-pm`  
**Active branch:** `feature/sprint6`  
**API version:** 0.4.1 (FastAPI) | **Package version:** 0.1.0

---

## Executive Summary

**Pi-PM (Personal Intelligence Portfolio Manager)** is a personal AI-powered portfolio management platform focused on **deterministic, auditable investment decisions** for Indian equities (NSE). The system ingests market data, filters investable universes, ranks stocks using versioned quantitative strategies, backtests historical rankings, and validates whether ranking signals predict forward returns.

LLMs are explicitly excluded from ranking, sizing, trade approval, and risk override. All money-related logic is deterministic and reproducible.

The platform is currently in **validation phase**: Sprint 6.1 full-universe historical validation for `breakout_v1` on `NIFTY_500` is implemented and a campaign may be running. Production deployment of new signals is blocked until validation answers five success criteria with data.

---

## Vision and Goals

### Vision

Build a personal portfolio manager that combines:
- **Deterministic quant engines** for universe selection, ranking, sizing, and risk
- **LLM research agents** (future) for narrative analysis only — never for trade decisions
- **Full audit trail** — every ranking run is hashed, versioned, and replayable

### Primary Goals

1. Rank ~500 NIFTY stocks daily using reproducible factor models
2. Validate ranking predictive power with IC, decile spreads, and hit rates
3. Support historical backtesting at full-universe scale (5 years of data)
4. Maintain strict domain boundaries (universe → ranking → validation → portfolio)
5. Enable future LLM research layer without compromising deterministic core

### Non-Goals (Current Phase)

- Live trade execution
- LLM-based ranking or sizing
- Options, commodities, news sentiment, or alternative data
- Multi-user SaaS deployment

---

## Current Implementation Status

| Layer | Status | Notes |
|-------|--------|-------|
| Foundation (FastAPI, PostgreSQL, Docker) | ✅ Complete | Sprint 1 |
| Market data ingestion (Yahoo) | ✅ Complete | Sprint 2 |
| Universe management (NIFTY 500) | ✅ Complete | Sprint 5.1 |
| Universe filter engine | ✅ Complete | Sprint 3 |
| Ranking engine (`momentum_v1`, `breakout_v1`) | ✅ Complete | Sprint 3, 5 |
| Ranking hardening (idempotency) | ✅ Complete | Sprint 3.1 |
| Historical ranking generator | ✅ Complete | Sprint 4.1 |
| Per-run signal validation | ✅ Complete | Sprint 4.2 |
| Full-universe validation campaigns | ✅ Implemented | Sprint 6.1 — findings TBD |
| Portfolio / risk / execution | ⏳ Stubs only | Placeholder packages |
| LLM agents / LangGraph | ⏳ Stubs only | Placeholder packages |

---

## Current Metrics and Scale

| Metric | Value | Source |
|--------|------:|--------|
| NIFTY 500 CSV constituents | 504 | `data/nifty500_constituents.csv` |
| Active universe memberships | ~504 | `NIFTY_500` |
| Stocks with ACTIVE data status | ~445 | Post-recovery (4 ERROR remaining) |
| Ranked stocks per run (`NIFTY_500`, `breakout_v1`) | ~439 | User-reported |
| Benchmark bars (`^NSEI`) | ~989 | 5-year history |
| Breakout history requirement | 252 trading days | `BreakoutV1Strategy` |
| Filter history requirement | 63 trading days | Default filter config |
| Validation horizons | 5, 10, 20, 60 days | `VALIDATION_HORIZONS` |
| Database tables | 16 | After migration `20260530_0006` |
| API endpoints | 21 | `/api/v1/*` |
| Automated tests | 121 | `pytest` (all passing) |
| Alembic migrations | 6 | `20260530_0001` → `20260530_0006` |

---

## Completed Milestones

| Milestone | Sprint | Deliverable |
|-----------|--------|-------------|
| Project scaffold | 1 | FastAPI, PostgreSQL, Docker, health check |
| Yahoo ingest + stock master | 2 | `POST /market-data/ingest`, universes |
| Deterministic ranking | 3 | `momentum_v1`, universe filter, ranking API |
| Ranking idempotency | 3.1 | `inputs_hash`, failed-run handling, cache abstraction |
| Historical backtest | 4.1 | `POST /backtest/generate-rankings` |
| Signal validation | 4.2 | IC, deciles, regimes, validation API |
| NIFTY 500 + breakout factors | 5.1 | `breakout_v1`, bootstrap, coverage reports |
| Full-universe validation | 6.1 | Campaign tables, pooled metrics API |

---

## Current Sprint

### Sprint 6.1 — Full Universe Historical Validation

**Objective:** Determine whether `breakout_v1` has predictive power on the full NIFTY 500 universe.

**Status:**
- Migration `20260530_0006` applied ✅
- API endpoints live ✅
- Full-universe validation campaign **in progress or pending results**
- Success criteria findings: **TBD**

**Key endpoints:**
- `POST /api/v1/validation/full-universe/run`
- `GET /api/v1/validation/full-universe/summary`
- `GET /api/v1/validation/full-universe/deciles`

**Gate:** No new signals until five validation questions are answered with data (see `docs/sprint61-full-universe-validation-report.md`).

---

## Next Sprint

### Sprint 6.2 (Proposed) — Validation Analysis & Go/No-Go

Based on Sprint 6.1 campaign results:

1. Document IC, spread, best horizon, decile monotonicity
2. Compare `breakout_v1` vs `momentum_v1` on same date range
3. Production readiness decision for `breakout_v1`
4. Commit Sprint 6.1 code to `main` (currently uncommitted on `feature/sprint6`)

### Sprint 7 (Proposed) — Portfolio Layer

- Position sizing from ranked signals
- Paper trading workflow
- Portfolio snapshot persistence (tables exist, logic stubbed)

---

## Known Risks and Assumptions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Yahoo Finance ingest failures (proxy/network) | Incomplete universe coverage | Local recovery scripts; batch retry |
| Default universe is `PI_PM_CORE` (~15 stocks) | Misleading ranking if omitted | Pass `universe_code: NIFTY_500` explicitly |
| Docker serves stale code without rebuild | 404 on new endpoints | Rebuild/restart after code changes |
| Full-universe campaign runtime | Hours for 500 days × 439 stocks | Idempotent reruns; reuse existing ranking runs |
| 4 ERROR symbols | Minor coverage gap | Acceptable for validation; recover if needed |
| Sprint 6.1 code uncommitted | Loss of work; CI gap | Commit before next sprint |

### Assumptions

- NSE `.NS` suffix symbols via Yahoo Finance are sufficient for Indian equities
- `^NSEI` (Nifty 50 index) is adequate benchmark for relative strength factors
- 5-year OHLCV history is enough for breakout factor lookbacks (252 days max)
- Percentile normalization within daily cross-section is appropriate for ranking
- Forward returns computed on trading-day horizons are valid predictability measure
- Single-user local deployment; no auth required yet

---

## Quick Reference

| Resource | Path |
|----------|------|
| AI onboarding | `docs/AI_CONTEXT.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| Database schema | `docs/DATABASE_SCHEMA.md` |
| API reference | `docs/API_REFERENCE.md` |
| Sprint history | `docs/SPRINT_HISTORY.md` |
| Roadmap | `docs/ROADMAP.md` |
| Decision log | `docs/DECISION_LOG.md` |
| Swagger UI | `http://localhost:8000/docs` |
| OpenAPI JSON | `http://localhost:8000/openapi.json` |
