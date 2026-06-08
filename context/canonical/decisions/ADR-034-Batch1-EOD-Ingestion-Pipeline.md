# ADR-034: Batch 1 — End-of-Day Ingestion & Signal Generation Pipeline

**Status:** Accepted  
**Date:** 2026-06-07  
**Deciders:** Product Owner, Principal Quant Platform Engineer  
**Supersedes:** N/A — formalises the existing manual `run_daily_nifty500_batch.py` workflow  
**Related:** [ADR-030](./ADR-030-Live-Investing-Architecture.md), [ADR-033](./ADR-033-Intraday-Exit-Monitor-And-Stop-Override.md), [ADR-035](./ADR-035-Batch2-Intraday-Exit-Monitor.md), [ADR-036](./ADR-036-Batch3-Paper-Trade-Execution.md)

---

## Context

The Pi-PM platform generates daily trading signals via a multi-stage pipeline: market data ingestion → factor ranking → validation → conviction scoring (RCEE) → recommendations → AI committee review. Until now this pipeline has been triggered manually via `scripts/run_daily_nifty500_batch.py` or direct API calls. There is no automated trigger after NSE market close.

The backtest (ADR backfilled to 2022-06-06 via `scripts/backtest_honest.py`) demonstrated a CAGR of +24.87% using `reversal_v1` signals executed at T+1 open. The honesty of signal generation — using only data available at N-1 close — is a non-negotiable invariant. Automating Batch 1 must preserve this invariant and must not allow same-day look-ahead.

---

## Decision

Batch 1 runs automatically **after NSE market close each trading day** (trigger: 15:45 IST, ~15 min after the 15:30 close to allow yfinance data propagation). It executes the following sequential phases in order:

### Phase Sequence

| # | Phase | API / Service | Output |
|---|-------|--------------|--------|
| 1 | **Ingest** | `POST /api/v1/market-data/ingest-universe` | OHLCV rows for `target_date` appended to `market_data` |
| 2 | **Ranking** | `POST /api/v1/rankings/run` | `ranking_runs` + `ranking_results` for `target_date` |
| 3 | **Validation** | `POST /api/v1/validation/backfill` | Factor IC re-scored over rolling lookback window (fixes stale/insufficient data) |
| 4 | **RCEE** (Recommendations) | `POST /api/v1/recommendations/run` | `recommendation_runs` + `recommendation_results` with `action=BUY/WATCH/REJECT` and `lifecycle_state=CANDIDATE` |
| 5 | **Committee** | `POST /api/v1/investment-committee/review` | 20 research packets with AI advisory overlays, stored in `investment_committee_*` tables |

### Trigger Logic

- **Trigger time:** 15:45 IST on weekdays (cron: `15 10 * * 1-5` UTC)
- **Trading day guard:** Before running, verify `MAX(as_of_date)` from `recommendation_runs` < `target_date`. If already completed for `target_date`, skip (idempotent).
- **NSE holiday guard:** If yfinance returns no OHLCV rows for `target_date` (zero tickers updated), abort gracefully — do not create empty ranking/recommendation runs.
- **Retry:** On transient failure, retry up to 3 times with 5-minute backoff. Alert on 3rd failure.

### Strategy

- **Primary strategy:** `reversal_v1` (the backtest strategy — produces the signals Batch 3 trades)
- **Secondary strategies** (`momentum_v1`, `breakout_v1`, `low_vol_v1`): also run for research/comparison but **do not feed Batch 3**

### Key Invariant

> Batch 1 on day N processes data for day N only. It never reads intraday prices or future data. Recommendations produced on day N are signals for day N+1 entry (executed by Batch 3).

---

## Consequences

**Positive:**
- Eliminates manual trigger dependency — signals are ready each evening
- Committee review completes overnight, giving PO a full review window before market open
- Consistent with the honest backtest execution model (N-1 signal → N entry)

**Negative / Risks:**
- yfinance data lag: OHLCV for Indian markets sometimes appears 30–60 min after close — the 15:45 trigger may need to be pushed to 16:30 if data staleness is observed
- Holiday detection is heuristic (zero-row guard) — a proper NSE calendar integration is preferred (Phase 2)
- Validation backfill re-scores the rolling window: this is intentional for factor IC hygiene but adds ~2–5 min to pipeline runtime

**Non-decisions (deferred):**
- Slack/email alert on pipeline failure — Phase 2
- NSE holiday calendar API integration — Phase 2
- Live broker OHLCV feed (vs yfinance) — Phase 3 (live capital)

---

## Confirmation Checklist (before automation goes live)

- [ ] Cron scheduler wired to `POST /api/v1/ops/daily-batch/runs`
- [ ] Trading day guard verified (idempotent re-run returns existing run_id)
- [ ] NSE holiday guard tested (2026-08-15 Independence Day dry run)
- [ ] Committee run confirmed for `reversal_v1` (SEE strategy profiles registered ✅ — ADR-034 fix)
- [ ] Alert channel configured for batch failure
