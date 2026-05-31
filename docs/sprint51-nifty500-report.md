# Sprint 5.1 — NIFTY 500 Universe Expansion Report

**Date:** 2026-05-31  
**Branch:** `feature/sprint5-breakout-factors`  
**Strategy under test:** `breakout_v1` vs `momentum_v1`  
**Universe:** `NIFTY_500`

---

## Executive Summary

Sprint 5.1 infrastructure is **complete**: NIFTY 500 constituents are loaded, the universe is bootstrapped with **504 memberships**, benchmark `^NSEI` has **989 bars** (252-day requirement met), and the end-to-end pipeline script is ready.

**Full validation is blocked in the Cursor agent environment** because Yahoo Finance requests fail with `ProxyError: CONNECT tunnel failed, response 403`. After a partial failed ingest, stocks were marked `ERROR`; **15 NIFTY 500 names with existing OHLCV** were reactivated for a smoke-test ranking (**15 ranked**, threshold **>450 not met**).

Run the full pipeline locally (outside proxy-restricted environments) to complete ingest, historical ranking backfill, and validation comparison.

---

## 1. Universe Size

| Metric | Value |
|--------|------:|
| NSE NIFTY 500 CSV constituents | 504 |
| `NIFTY_500` active memberships | **504** |
| Stock master total (incl. benchmark) | 505 |
| New placeholder stocks created | 489 |
| Pre-existing stocks reused | 15 |

**Source:** `data/nifty500_constituents.csv` (downloaded from NSE archives)

---

## 2. Data Coverage Report

**As-of date:** 2025-05-29

| Metric | Value |
|--------|------:|
| Membership count | 504 |
| Stocks with any OHLCV | 15 |
| Stocks with ≥63d filter history | 15 |
| Stocks with ≥252d breakout history | 15 |
| Benchmark `^NSEI` bars | 989 |
| Benchmark available for RS factors | **Yes** |

### Data status breakdown

| Status | Count |
|--------|------:|
| ACTIVE (with data) | 15 |
| INACTIVE (placeholder, no ingest) | 489 |
| ERROR (failed ingest attempt) | 0* |

\*After `reactivate` recovery step; failed ingest temporarily marked all symbols ERROR.

### Blocker

Yahoo Finance ingestion requires network access without HTTP proxy restrictions. In this environment, **489/504** constituents still need 5-year OHLCV ingest.

---

## 3. Ranking Coverage Report

**Strategy:** `breakout_v1` v1.0.0  
**Universe:** `NIFTY_500`  
**As-of:** 2025-05-29

| Metric | Value |
|--------|------:|
| Ranked stock count | **15** |
| Threshold (>450) | **Not met** |
| Benchmark available | true |
| Primary exclusion reason | `DATA_STATUS_NOT_ACTIVE` (489 stocks) |

Once full ingest completes and stocks become `ACTIVE`, expect ranked count **>450** given NIFTY 500 liquidity filters.

---

## 4. Validation Summary Comparison

**Period:** 2024-01-01 → 2025-12-31  
**Status:** **Pending** — requires historical ranking runs for both strategies after full data ingest.

| Strategy | Runs expected | Validated | Avg IC | Median IC | Hit rate |
|----------|--------------:|----------:|-------:|----------:|---------:|
| `momentum_v1` | ~500 trading days | — | — | — | — |
| `breakout_v1` | ~500 trading days | — | — | — | — |

---

## 5. Top Breakout Candidates (Smoke Test — 15 stocks)

Partial ranking from available data only:

| Rank | Symbol | Name | Score |
|-----:|--------|------|------:|
| 1 | BDL.NS | Bharat Dynamics Limited | 0.8679 |
| 2 | BEL.NS | Bharat Electronics Limited | 0.7464 |
| 3 | HAL.NS | Hindustan Aeronautics Limited | 0.6786 |
| 4 | COCHINSHIP.NS | Cochin Shipyard Limited | 0.6714 |
| 5 | BSE.NS | BSE Limited | 0.5821 |
| 6 | ICICIBANK.NS | ICICI Bank Limited | 0.5679 |
| 7 | BHARTIARTL.NS | Bharti Airtel Limited | 0.5429 |
| 8 | HDFCBANK.NS | HDFC Bank Limited | 0.4643 |
| 9 | RELIANCE.NS | Reliance Industries Limited | 0.4536 |
| 10 | LT.NS | Larsen & Toubro Limited | 0.4429 |
| 11 | SBIN.NS | State Bank of India | 0.4214 |
| 12 | ITC.NS | ITC Limited | 0.4071 |
| 13 | HINDUNILVR.NS | Hindustan Unilever Limited | 0.2607 |
| 14 | INFY.NS | Infosys Limited | 0.2071 |
| 15 | TCS.NS | Tata Consultancy Services Limited | 0.1857 |

---

## Implementation Delivered

| Component | Path |
|-----------|------|
| NIFTY 500 CSV | `data/nifty500_constituents.csv` |
| Constituent loader | `app/universe/nifty500_loader.py` |
| Universe bootstrap | `app/services/universe_bootstrap_service.py` |
| Coverage reporting | `app/services/universe_coverage_service.py` |
| End-to-end pipeline | `scripts/sprint51_nifty500_pipeline.py` |
| Unit tests | `tests/unit/universe/test_nifty500_loader.py`, `tests/unit/services/test_universe_bootstrap_service.py`, `tests/unit/services/test_universe_coverage_service.py` |

**Tests:** 113 passed

---

## Run Full Pipeline Locally

```bash
cd pi-pm

# Ensure Postgres is running and migrations applied
alembic upgrade head

# Full Sprint 5.1 pipeline (~30–90 min for Yahoo ingest)
.venv/bin/python scripts/sprint51_nifty500_pipeline.py --phases all --verbose \
  --as-of-date 2025-05-29 \
  --output docs/sprint51-nifty500-report.json
```

### Phases (individual)

| Phase | Purpose |
|-------|---------|
| `bootstrap` | Load CSV → create stocks + NIFTY_500 memberships |
| `reactivate` | Recover ERROR stocks that already have OHLCV |
| `ingest` | 5y Yahoo OHLCV for all constituents + `^NSEI` |
| `coverage` | 252-day history verification report |
| `rank` | Single `breakout_v1` ranking run |
| `backfill-rankings` | Daily rankings 2024–2025 for both strategies |
| `validate` | Validation backfill for completed runs |
| `compare` | `momentum_v1` vs `breakout_v1` summary |
| `top20` | Top 20 breakout candidates from latest run |

### API equivalents (after ingest)

```bash
# Rank
curl -X POST localhost:8000/api/v1/rankings/run -H 'Content-Type: application/json' \
  -d '{"strategy_name":"breakout_v1","strategy_version":"1.0.0","universe_code":"NIFTY_500"}'

# Validation backfill
curl -X POST localhost:8000/api/v1/validation/backfill -H 'Content-Type: application/json' \
  -d '{"start_date":"2024-01-01","end_date":"2025-12-31"}'

# Compare summaries
curl 'localhost:8000/api/v1/validation/summary?universe_code=NIFTY_500&strategy_name=breakout_v1&start_date=2024-01-01&end_date=2025-12-31'
curl 'localhost:8000/api/v1/validation/summary?universe_code=NIFTY_500&strategy_name=momentum_v1&start_date=2024-01-01&end_date=2025-12-31'
```

---

## Acceptance Checklist

| # | Task | Status |
|---|------|--------|
| 1 | Create NIFTY_500 universe | ✅ (migration seed + bootstrap) |
| 2 | Load NIFTY 500 constituents | ✅ 504 symbols |
| 3 | Stock master ~500 stocks | ✅ 505 total |
| 4 | Ingest 5y OHLCV for all | ⏳ Blocked (Yahoo proxy); 15/504 have data |
| 5 | Ingest benchmark ^NSEI | ✅ 989 bars |
| 6 | Verify 252-day history | ✅ for 15 stocks + benchmark |
| 7 | Run ranking on NIFTY_500 | ✅ smoke test (15 ranked) |
| 8 | ranked_stock_count > 450 | ❌ pending full ingest |
| 9 | Validation backfill 2024–2025 | ⏳ pending ranking backfill |
| 10 | Compare momentum_v1 vs breakout_v1 | ⏳ pending validation |
