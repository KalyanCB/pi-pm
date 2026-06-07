# ADR-036: Batch 3 — Morning Paper Trade Execution (N-1 Signal → N Entry)

**Status:** Accepted  
**Date:** 2026-06-07  
**Deciders:** Product Owner, Principal Quant Platform Engineer  
**Supersedes:** N/A — formalises the paper trade entry logic validated by `scripts/backtest_honest.py`  
**Related:** [ADR-034](./ADR-034-Batch1-EOD-Ingestion-Pipeline.md), [ADR-035](./ADR-035-Batch2-Intraday-Exit-Monitor.md), [ADR-030](./ADR-030-Live-Investing-Architecture.md)

---

## Context

The honest backtest (`scripts/backtest_honest.py`, CAGR +24.87%, 1026 trades, 2022-06-06 to 2026-06-05) demonstrated that using prior-day (N-1) recommendations to execute entries at day-N open price eliminates look-ahead bias and is the correct signal-to-execution model. Quantified look-ahead inflation was +0.53% per entry when using same-day signals.

Batch 1 (ADR-034) generates recommendations on day N (signal date = N). Batch 3 must pick up those signals and execute paper trades at day N+1 open — preserving the N-1 → N pattern.

The AI Committee runs as the final Batch 1 phase, producing advisory overlays on each BUY recommendation. However, committees are currently conservative (WATCH) in a BEAR_LOW_VOL regime even when the engine says BUY. A hard block on `COMMITTEE_REJECTED` would eliminate all paper trades in the current regime. The PO has confirmed that **REJECTED is the only hard block** — APPROVED and CANDIDATE (pending human review) both proceed.

---

## Decision

Batch 3 runs **once per trading day at 09:15 IST** (market open), after Batch 2's first exit scan. It reads the prior trading day's recommendations and executes paper trades for all eligible BUY signals.

### Trigger Schedule

- **Time:** 09:15 IST (cron: `45 3 * * 2-6` UTC — Tuesday to Saturday to cover Monday–Friday IST)
- **Must run after:** Batch 2's 09:15 scan (Batch 3 at :15 past, Batch 2 at :45 prior hour — sequenced correctly)
- **Must run before:** 09:30 IST (to get realistic open-price fills before price moves materially)

### Signal Selection Logic

```sql
SELECT rr.as_of_date, res.id, res.stock_id, res.rank,
       res.action, res.lifecycle_state, res.conviction_band
FROM recommendation_results res
JOIN recommendation_runs rr ON rr.id = res.recommendation_run_id
WHERE rr.as_of_date = <last_trading_day>       -- N-1 signal date
  AND rr.strategy_name = 'reversal_v1'
  AND rr.status = 'completed'
  AND res.action = 'BUY'
  AND (res.lifecycle_state IN ('CANDIDATE', 'APPROVED')
       OR res.lifecycle_state IS NULL)          -- REJECTED is the only hard block
ORDER BY res.rank ASC
```

**last_trading_day** = `MAX(as_of_date)` from `recommendation_runs` where `status='completed'` and `as_of_date < today`. This is a trading-calendar-safe lookup — handles weekends and holidays automatically.

### Eligibility Rules (per candidate)

| Rule | Condition | Action |
|------|-----------|--------|
| **Already held** | `portfolio_positions` has OPEN position for this `stock_id` | Skip — no double-entry |
| **Portfolio full** | OPEN position count ≥ `MAX_SLOTS` (10) | Skip all remaining |
| **Slot available** | OPEN count < `MAX_SLOTS` | Proceed to fill |
| **REJECTED** | `lifecycle_state = 'REJECTED'` | Hard skip |
| **Insufficient price data** | yfinance cannot fetch today's open price | Skip with warning |

### Fill Price

- **Paper trading:** yfinance `period=1d interval=1m` → first bar open price (09:15 candle) + 5 bps slippage
- **Sizing:** `MAX_SLOT_ALLOC = ₹500,000` per position → `quantity = floor(500000 / fill_price)`
- **Live (Phase 3):** Broker market order at open — decision deferred

### Output

For each executed entry, Batch 3 writes:
1. `portfolio_positions` row: `position_status=OPEN`, `entry_price=fill_price`, `entry_date=today`, `stop_loss_price=entry_price × 0.99`
2. `paper_trades` row: `side=BUY`, `status=FILLED`, `fill_price=fill_price`, `filled_at=09:15:00 IST`
3. `portfolio_cash_ledger` row: debit entry for the position notional
4. Links `recommendation_result_id` on the position for full traceability

### Stop-Loss Pre-Commitment

Stop-loss price is written at entry time: `stop_loss_price = entry_price × 0.99` (1% stop, consistent with backtest). Batch 2 uses this field for intraday monitoring. The stop is **not** placed with a broker in paper mode.

---

## Consequences

**Positive:**
- Fully mirrors the backtest execution model — paper P&L is directly comparable to backtested CAGR
- CANDIDATE (pending human review) eligibility means no trades are missed due to human delay — critical for paper accuracy
- Stop-loss committed at entry: Batch 2 can begin monitoring from the 10:15 run onward

**Negative / Risks:**
- CANDIDATE execution means PO may see a paper trade they wouldn't have approved — this is intentional for paper mode. For live capital, only APPROVED signals trade (Phase 3 decision)
- yfinance open price is the 09:15 1-minute bar, not the true auction open — small price discrepancy acceptable for paper
- If Batch 1 runs late (e.g. yfinance data lag) and committee is not complete before 09:15 the next day, Batch 3 will use the incomplete committee state. Batch 1 must complete by 21:00 IST (6 hours post-close) to guarantee readiness.

**Non-decisions (deferred):**
- Live broker order placement — Phase 3
- Position sizing by conviction band (EXCEPTIONAL: 1.15×, HIGH: 1.0×, etc.) — currently flat ₹500K regardless of band; Phase 2
- Approval-only mode (`lifecycle_state = 'APPROVED'` only) — Phase 3 (live capital gate)

---

## Execution Order on a Trading Day

```
T = trading day N (e.g. Monday 2026-06-09)

[Previous evening]
  15:45 IST  →  Batch 1: ingest Jun-08 → rank → validate → RCEE → recommend → committee
  (completes by ~18:00 IST)

[Morning of T]
  09:15 IST  →  Batch 2 run #1: scan open positions for exits (none yet on first day)
  09:15 IST  →  Batch 3: pick up Jun-08 BUY signals → paper trade entry at 09:15 open

[Intraday T]
  10:15 IST  →  Batch 2 run #2: check new positions vs stop-loss
  11:15 IST  →  Batch 2 run #3
  ... (hourly until 15:15)

[End of T]
  15:45 IST  →  Batch 1: ingest Jun-09 → ... → committee (signals for Jun-10)
```

---

## Confirmation Checklist (before automation goes live)

- [ ] Signal query tested: `reversal_v1` + `last_trading_day` returns correct 5 BUYs for 2026-06-05
- [ ] Double-entry guard: existing OPEN position correctly skipped
- [ ] `stop_loss_price` written at entry (verified in `portfolio_positions`)
- [ ] `paper_trades` row linked to `recommendation_result_id`
- [ ] Cash ledger debit entry written
- [ ] Batch ordering: Batch 3 confirmed to run after Batch 2's 09:15 scan
- [ ] Batch 1 completion SLA: alert if Batch 1 not completed by 21:00 IST
