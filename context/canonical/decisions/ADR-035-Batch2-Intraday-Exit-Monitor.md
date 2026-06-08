# ADR-035: Batch 2 — Intraday Exit Monitor (Hourly, Market Hours)

**Status:** Accepted  
**Date:** 2026-06-07  
**Deciders:** Product Owner, Principal Quant Platform Engineer, Risk Owner  
**Supersedes:** N/A — extends ADR-033 (intraday exit monitor design) with automation cadence decision  
**Related:** [ADR-033](./ADR-033-Intraday-Exit-Monitor-And-Stop-Override.md), [ADR-034](./ADR-034-Batch1-EOD-Ingestion-Pipeline.md), [ADR-036](./ADR-036-Batch3-Paper-Trade-Execution.md)

---

## Context

ADR-033 identified that the exit monitor runs only once per day (post-close), meaning a position can breach stop-loss intraday and not be flagged until the next EOD run. For paper trading this represents missed exit signals and P&L measurement inaccuracy. For eventual live capital this is a hard safety risk.

The backtest uses daily close prices for exit evaluation (stop-loss capped at `entry_price × 0.99`, time-stop at 30 trading days, rank-drop at >40 positions). For the live/paper regime, intraday evaluation on hourly prices adds exit precision without changing the exit logic.

Open positions as of 2026-06-07: **0** (backtest ended 2026-06-05 with FORCE_CLOSE on all positions). First real open positions will appear after Batch 3 runs on 2026-06-09 (Mon market open).

---

## Decision

Batch 2 runs **every hour during NSE market hours** on trading days (09:15–15:30 IST). Each run evaluates all `OPEN` positions against current intraday price data and fires exit signals where thresholds are breached.

### Trigger Schedule

| Run | IST | UTC (cron) | Notes |
|-----|-----|-----------|-------|
| 1 | 09:15 | `03:45 * * * 1-5` | Post-open: first intraday read |
| 2 | 10:15 | `04:45 * * * 1-5` | |
| 3 | 11:15 | `05:45 * * * 1-5` | |
| 4 | 12:15 | `06:45 * * * 1-5` | |
| 5 | 13:15 | `07:45 * * * 1-5` | |
| 6 | 14:15 | `08:45 * * * 1-5` | |
| 7 | 15:15 | `09:15 * * * 1-5` | Final intraday check before close |

> Batch 2 does **not** run after 15:30 IST — EOD exit evaluation is covered by Batch 1's portfolio phase.

### Exit Evaluation Logic

For each OPEN position, evaluate in priority order:

| Priority | Trigger | Condition | Exit Reason |
|----------|---------|-----------|-------------|
| 1 | **Stop-loss** | `current_price ≤ entry_price × 0.99` | `STOP_LOSS` |
| 2 | **Time-stop** | Trading days held > 30 | `TIME_STOP` |
| 3 | **Rank-drop** | Current rank > 40 (using latest ranking run for the day) | `RANK_DROP` |

- **Price source (paper):** yfinance intraday quote (`period=1d, interval=1m` → latest close bar). Not a real-time tick feed.
- **Price source (live, Phase 3):** Broker WebSocket tick feed (decision deferred).
- **Stop-loss cap:** Exit is recorded at `max(current_price, entry_price × 0.99)` — consistent with backtest convention. Does not assume we exit exactly at the stop price.

### Output

- Creates `portfolio_exit_recommendations` row with `status=PENDING` for each triggered position
- Does **not** auto-execute — PO must confirm via UI (ADR-030 HITL invariant)
- Duplicate guard: if a PENDING exit already exists for a position, skip (no second row)
- Surfaced in UI → Recommendations → EXIT tab and Portfolio → Positions exit monitor

### No-Op Conditions

- Zero OPEN positions → skip silently (no error)
- Non-trading day (weekend/holiday) → guard via `MAX(as_of_date)` from `market_data`: if latest date < today, skip
- Rank-drop check: only if a ranking run exists for today (Batch 1 may not have run yet at 09:15 — rank-drop skipped for first 2 hourly runs until Batch 1 completes)

---

## Consequences

**Positive:**
- Intraday stop-loss breach is caught within 1 hour, not next-day EOD
- Rank-drop signals are fresher (uses today's ranking if available)
- P&L measurement for paper trades more accurately reflects real execution

**Negative / Risks:**
- yfinance intraday data has occasional gaps — stale price during market hours is treated as "no update" (conservative: do not fire exit on stale data)
- 7 API calls/day per position adds load — acceptable for ≤20 positions (current max slot count)
- Human confirmation latency remains: signal fires at 10:15, PO confirms at 13:00 → position held 3 extra hours. This is by design (ADR-030).

**Non-decisions (deferred):**
- Auto-execute stop-loss in paper mode (`pilot_auto_execute=true`) — requires PO sign-off per ADR-033
- Trailing stop (5% from peak) intraday — Phase 2
- WhatsApp/push notification on exit signal — Phase 2

---

## Confirmation Checklist (before automation goes live)

- [ ] Hourly cron wired to `POST /api/v1/portfolio/exits/run` (or equivalent batch endpoint)
- [ ] Intraday price fetch tested (yfinance `period=1d interval=1m` → last bar)
- [ ] Duplicate PENDING guard verified (second hourly run does not create second exit row)
- [ ] No-op on zero positions verified
- [ ] Rank-drop skip verified when today's ranking run not yet available
