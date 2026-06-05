# 90-Day Paper Trading Pilot — Execution Plan

**Start:** T+0 (first trading day after go-live)  
**Duration:** 90 calendar days (~63 trading sessions)  
**Universe:** NIFTY_500  
**Capital:** `portfolio_configs.total_equity` (configure before Day 0)

---

## Phase 0 — Pre-flight (Days -7 to -1)

| Day | Task | Owner |
|-----|------|-------|
| -7 | `alembic upgrade head` | Eng |
| -7 | Seed `portfolio_configs` (equity, regime_slots) | Ops |
| -6 | Run full batch dry-run: `"dry_run": true, "phases": {"portfolio": true}` | Ops |
| -5 | Run live batch one session with `pilot_auto_execute=false` — verify recs | Ops |
| -4 | Enable `pilot_auto_approve=true`, `pilot_auto_execute=true` for one session | Ops |
| -3 | Verify lineage: paper_trade → position → NAV → recon PASS | Eng |
| -2 | Configure cron: `run_daily_nifty500_batch.py` post-close IST | Ops |
| -1 | Generate baseline dashboards; PO sign-off | PO |

---

## Phase 1 — Pilot run (Days 1–30)

### Daily (automated)

```bash
# Cron (example 18:00 IST weekdays)
python scripts/run_daily_nifty500_batch.py \
  --portfolio \
  --pilot-auto-approve \
  --pilot-auto-execute

python scripts/generate_paper_trading_dashboard.py
```

### Weekly (manual, 30 min)

- Review `RECONCILIATION_DASHBOARD.md` — zero FAIL
- Review trust metrics via `/api/v1/analytics/recommendations/trust`
- Check pending `ExitRecommendation` count
- Validate batch trace includes `recommendation_run_ids`

### Success criteria (Day 30)

| Metric | Target |
|--------|--------|
| Batch completion rate | ≥ 95% |
| Reconciliation PASS/WARN | 100% (no FAIL) |
| NAV snapshots | 1 per trading day |
| Orphan paper trades | 0 |

---

## Phase 2 — Steady state (Days 31–60)

- Reduce manual review to weekly
- Add alerting on reconciliation FAIL (external monitor on batch status API)
- Mid-pilot report: conviction calibration, outcome win rate by band

### Success criteria (Day 60)

| Metric | Target |
|--------|--------|
| Cumulative alpha vs ^NSEI | Documented (not gated) |
| Max drawdown | Within portfolio risk limits |
| Exit trigger false positive rate | PO review |

---

## Phase 3 — Closeout (Days 61–90)

| Week | Task |
|------|------|
| 61–75 | Continue unattended batch |
| 76 | Freeze pilot config |
| 77–83 | Generate full outcome attribution report |
| 84–90 | PO decision: promote to M3 HITL or extend pilot |

### Exit criteria (Day 90)

| Deliverable | Required |
|-------------|----------|
| 90 NAV snapshots | ✓ |
| 90 reconciliation reports | ✓ |
| Full trade ledger export | ✓ |
| Pilot readiness retrospective | ✓ |
| PO go/no-go for live HITL | ✓ |

---

## Kill switch

If reconciliation FAIL **2 consecutive days**:

1. Set `pilot_auto_execute=false` on batch request
2. Investigate cash ledger vs positions
3. Resume only after manual recon PASS

---

## Batch request template (production)

```json
{
  "universe_code": "NIFTY_500",
  "benchmark_symbol": "^NSEI",
  "assume_session_done": true,
  "idempotency_key": "pilot-2026-06-05",
  "phases": {
    "ingest": true,
    "rankings": true,
    "validation": true,
    "recommendations": true,
    "regime_history": true,
    "regime_performance": true,
    "factor_ic": true,
    "research_intelligence": true,
    "exit_research": true,
    "portfolio": true
  },
  "portfolio_phases": {
    "recompute": true,
    "exit_monitor": true,
    "paper_trading": true,
    "nav_snapshot": true,
    "reconcile": true
  },
  "pilot_auto_approve": true,
  "pilot_auto_execute": true,
  "ingest_portfolio_benchmarks": true
}
```

---

## Architecture constraint compliance

| Forbidden change | Compliant? |
|------------------|------------|
| Ranking | ✓ Not modified |
| Validation | ✓ Not modified |
| Recommendation logic | ✓ Not modified |
| Conviction formula | ✓ Not modified |
| Committee logic | ✓ Not modified |

Track G changes are **orchestration, lineage, and ops only**.
