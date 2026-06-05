# Paper Trading Pilot Readiness Report

**Track:** G — Paper Trading Readiness & Operational Validation  
**Date:** 2026-06-05  
**Question:** Can Pi-PM run for 90 consecutive days without manual intervention?

---

## Verdict

| Mode | Ready? | Score |
|------|--------|-------|
| Research-only daily batch | **Yes** | 90/100 |
| Paper trading with manual HITL | **Partial** | 65/100 |
| **90-day unattended paper pilot** | **Yes (with flags)** | **78/100** |

**Answer:** Yes — when daily batch runs with `phases.portfolio=true`, `pilot_auto_approve=true`, `pilot_auto_execute=true`, and scheduled post-close via cron.

---

## Lifecycle readiness

| Lifecycle | Status | Automation |
|-----------|--------|------------|
| Recommendation | Shipped | Batch generates daily |
| Approval | Shipped | Manual API; **pilot auto-approve** for unattended |
| Paper trade | Shipped | Manual API; **pilot auto-execute** for unattended |
| Position | Shipped | Open/close from paper trades |
| NAV | Shipped | Batch `portfolio_nav` phase |
| Reconciliation | Shipped | Batch `portfolio_reconcile` phase |
| Outcome | Shipped | Created on entry; closed on exit |
| Exit monitor | Shipped | Batch `exit_monitor`; advisory only |
| Committee | Shipped | On-demand only — not in batch |
| Copilot | Shipped | Explain-only; not in batch |

---

## Daily batch phase matrix

| Phase | Batch wired | Pilot needs |
|-------|-------------|-------------|
| Ingest (+ ^CRSLDX) | ✓ | ✓ |
| Rankings | ✓ | ✓ |
| Validation | ✓ | ✓ |
| Recommendations | ✓ | ✓ |
| Regime / factor / exit research | ✓ | ✓ (analytics) |
| Portfolio recompute | ✓ (new) | ✓ |
| Exit monitor | ✓ (new) | ✓ |
| Paper trading | ✓ (new, flag) | ✓ |
| NAV snapshot | ✓ (new) | ✓ |
| Reconciliation | ✓ (new) | ✓ |

---

## Trade ledger lineage

```
recommendation_run → recommendation_result → approval (pilot) → paper_trade
  → portfolio_position → cash_ledger → portfolio_nav_history → recommendation_outcome
```

| Link | Before | After Track G |
|------|--------|---------------|
| `paper_trades.ranking_run_id` | Always null | Populated |
| `metadata.recommendation_run_id` | Partial | Populated |
| `positions.strategy_name` | Null | From rec run |
| `outcomes.benchmark_return_pct` | 0.0 hardcoded | ^NSEI holding return |
| Batch trace recommendation IDs | Missing | Included |

---

## Remaining gaps (non-blocking for pilot)

1. Committee not scheduled in batch (ARGS remains research governance)
2. No portfolio API integration tests
3. Benchmark split (^NSEI vs ^CRSLDX) documented not unified
4. CI workflow still absent
5. `approval_id` not FK on `paper_trades`

---

## Pilot launch command

```bash
curl -X POST http://localhost:8000/api/v1/ops/daily-batch/runs \
  -H "Content-Type: application/json" \
  -d '{
    "universe_code": "NIFTY_500",
    "benchmark_symbol": "^NSEI",
    "assume_session_done": true,
    "phases": {
      "portfolio": true
    },
    "pilot_auto_approve": true,
    "pilot_auto_execute": true,
    "ingest_portfolio_benchmarks": true
  }'
```

Post-run dashboards:

```bash
python scripts/generate_paper_trading_dashboard.py --as-of-date 2026-06-05
```

---

## Test evidence

| Suite | Result |
|-------|--------|
| `tests/unit/ops/test_paper_pilot_ops.py` | 2 passed |
| `tests/unit/ops/test_daily_batch_portfolio_schema.py` | 2 passed |
| `tests/unit/services/test_paper_trade_lineage.py` | 1 passed |
| `tests/unit/portfolio/test_reconciliation.py` | 6 passed |
