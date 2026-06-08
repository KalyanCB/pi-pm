# Paper Trading Audit

**Audit:** AUDIT-01  
**Date:** 2026-06-05  
**ADRs:** ADR-028 (Paper Readiness), ADR-029 (Pilot Ops), ADR-031 (Unified Execution)  
**PRDs:** `06_PAPER_TRADING_PRD.md`, `11_HUMAN_IN_LOOP_EXECUTION_PRD.md`

---

## Executive Question

**Can the system run a 90-day unattended paper pilot?**

### Verdict: **CONDITIONAL YES**

The investment lifecycle code path is sufficient when batch is triggered daily with pilot flags and infrastructure is healthy. It is **not turnkey** — documented HTTP cron conflicts with owner-only auth; alerting and kill-switch require external ops.

---

## Lifecycle Verification

### Orchestration flow (code-verified)

```
POST /ops/daily-batch/runs
  phases.portfolio=true, pilot_auto_approve=true, pilot_auto_execute=true
    → DailyBatchService (app/services/daily_batch_service.py ~454-526)
      → PaperPilotOps (app/ops/daily_batch/paper_pilot_ops.py)
        → PortfolioService.recompute
        → ExitMonitorService.run
        → RecommendationService.approve (auto, actor=paper_pilot)
        → ExecutionService → PaperExecutionAdapter → PaperTradeService
        → PortfolioNavService.snapshot
        → ReconciliationService.run
```

### Stage-by-stage status

| Lifecycle | Implementation | Automated in batch | Status | Evidence |
|-----------|----------------|-------------------|--------|----------|
| **Recommendation** | RecommendationEngine in batch | Yes | **IMPLEMENTED** | `daily_batch_service.py` |
| **Approval** | `RecommendationService.approve()` | Yes with `pilot_auto_approve` | **IMPLEMENTED** | `paper_pilot_ops.py:179-188` |
| **Paper entry** | ExecutionService → PaperAdapter | Yes with `pilot_auto_execute` | **IMPLEMENTED** | `paper_pilot_ops.py:100-149` |
| **Paper exit** | Auto for EXIT_APPROVED | Yes (auto-approves if needed) | **IMPLEMENTED** | `paper_pilot_ops.py:112-149` |
| **Position update** | PaperTradeService | Yes | **IMPLEMENTED** | `execution/adapters/paper.py` |
| **NAV** | PortfolioNavService.snapshot | Yes | **IMPLEMENTED** | `paper_pilot_ops.py:81-88` |
| **Reconciliation** | ReconciliationService.run | Yes | **IMPLEMENTED** | `paper_pilot_ops.py:90-96` |
| **Exit signal** | ExitMonitorService | Yes (advisory) | **IMPLEMENTED** | `paper_pilot_ops.py:68-73` |
| **Outcome close** | On exit fill | Yes | **IMPLEMENTED** | `execution_service.py` |
| **Committee** | On-demand API only | No | **PARTIAL** | ARGS not in batch schedule |
| **Attribution** | Portfolio analytics | On demand | **IMPLEMENTED** | 409 gate on recon FAIL |

### AC-PT acceptance criteria

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| AC-PT-01 | Idempotent paper trade key | **IMPLEMENTED** | `pilot-entry:{rec.id}`, `pilot-exit:{rec.id}` |
| AC-PT-02 | Filled BUY has lineage | **IMPLEMENTED** | `execution_orders` + `paper_trades` FK chain |
| AC-PT-03 | Positions reconcile to trades | **IMPLEMENTED** | `test_reconciliation.py` |
| AC-PT-04 | Attribution golden fixture | **IMPLEMENTED** | `test_analytics.py` |

### Execution guards

| Guard | Status | Evidence |
|-------|--------|----------|
| No fill without APPROVED | **IMPLEMENTED** | `ExecutionValidationError` in service + unit test |
| Live trading blocked | **IMPLEMENTED** | `enable_live_trading=false`; Zerodha stub |
| State machine terminal states | **IMPLEMENTED** | `test_state_machine.py` |
| Idempotency on orders | **IMPLEMENTED** | client_order_id in execution |

---

## Pilot Observability

| Component | Path | Status |
|-----------|------|--------|
| Alerting (13 codes) | `app/ops/pilot/alerting.py` | **IMPLEMENTED** — read-only, no side effects |
| Reporting | `app/ops/pilot/reporting.py` | **IMPLEMENTED** |
| Command center | `pilot_command_center_service.py` | **IMPLEMENTED** |
| API (10 routes) | `app/api/v1/pilot_ops.py` | **IMPLEMENTED** |
| Unit tests | `test_paper_pilot_ops.py`, `test_pilot_command_center.py`, `test_pilot_alerting.py` | **IMPLEMENTED** |
| API integration tests | — | **MISSING** |
| E2E 90-day simulation | — | **MISSING** |

### KPI targets (`docs/paper-pilot/SUCCESS_METRICS.md`)

| KPI | Target | Measurable in code | Historical proof |
|-----|--------|-------------------|------------------|
| Batch completion ≥95% | 90-day gate | `/pilot/metrics/success` | **No** — no production run data |
| Recon pass ≥98% | 90-day gate | recon reports table | **No** |
| NAV coverage ≥95% | 90-day gate | nav_history table | **No** |
| Zero recon FAIL 14d | GO/NO-GO | manual check | **DOCUMENTED_ONLY** |

---

## Blockers for Turnkey Unattended Operation

| Blocker | Severity | Evidence |
|---------|----------|----------|
| Cron script no auth | **P0** | `scripts/run_daily_nifty500_batch.py:77` POST without Authorization; batch requires OWNER JWT |
| Cron not in repo | **P1** | `OPERATIONAL_GAP_ANALYSIS.md` |
| External alerting only | **P1** | `ALERTING_FRAMEWORK.md` — Slack/email outside app |
| Kill switch manual | **P1** | 2× recon FAIL → stop auto-execute documented but not automated |
| No E2E pilot tests | **P1** | Unit tests only |
| Single-portfolio assumption | **P2** | Batch queries lack `portfolio_id` |
| Committee not scheduled | **P3** | Non-blocking for paper fills |
| Default JWT secret | **P0** (security) | `config.py:83` |

### Minimum ops checklist for true unattended

1. Cron with service-account JWT **or** direct `DailyBatchService.create_and_execute()` Python invocation
2. External monitor on `GET /api/v1/pilot/alerts` for `critical` severity
3. Production: `JWT_SECRET_KEY` set, `AUTH_BYPASS_FOR_TESTS=false`
4. Manual kill-switch playbook for consecutive recon FAIL

---

## Docs vs Code

| Document | Claim | Code reality |
|----------|-------|--------------|
| `PLATFORM-HANDOFF-2026.md` (Jun 4) | Paper stub | **Stale** — full lifecycle since Jun 5 |
| `po-discovery/09 RTM` | Paper orphan | **Stale** |
| `PILOT_READINESS_REPORT.md` | 78/100 with flags | **Aligned** with this audit |
| `IMPLEMENTATION_SUMMARY.md` | P5 paper shipped | **Aligned** |
| `OPERATIONAL_GAP_ANALYSIS.md` | Cron external, no E2E | **Aligned** |

---

## Pilot Readiness Score (audit-derived)

| Dimension | Score | Notes |
|-----------|-------|-------|
| Lifecycle code | 85/100 | Full path exists |
| Automation | 60/100 | Flags work; cron/auth gap |
| Observability | 80/100 | Dashboards + alerts; no push |
| Test confidence | 55/100 | Unit only |
| Multi-tenant | 40/100 | Single portfolio |
| **Composite** | **68/100** | Conditional go |

---

*Evidence: `app/ops/daily_batch/paper_pilot_ops.py`, `app/execution/`, `app/services/daily_batch_service.py`, pilot tests.*
