# Go-Live Checklist — Live Investing (S1)

**Track:** I — Live Investing Readiness  
**Date:** 2026-06-05  
**Target stage:** S1 — Human-approved live investing (not full broker automation)

Use this checklist before enabling `execution_mode=LIVE` on any portfolio.

---

## Phase 0 — Paper pilot complete

- [ ] 90-day paper pilot completed or PO waiver documented
- [ ] Reconciliation PASS rate ≥ 99% over last 30 days
- [ ] Exit monitor producing actionable candidates
- [ ] HITL approval audit trail complete
- [ ] ADR-028 paper batch phases stable

---

## Phase 1 — Architecture & governance

- [ ] ADR-030 reviewed and accepted
- [ ] Human-in-loop PRD (18) signed off
- [ ] Broker Adapter PRD (19) signed off
- [ ] Risk Control PRD (20) signed off
- [ ] Execution Workflow PRD (21) signed off
- [ ] Legal disclaimer and client responsibility agreement in place

---

## Phase 2 — Platform readiness

- [ ] ADR-027 auth enabled (`AUTH_ENABLED=true`, no bypass)
- [ ] JWT secret rotated (32+ bytes)
- [ ] Owner role assigned; viewer accounts restricted
- [ ] Portfolio ownership mapping verified per user
- [ ] Migration head current

---

## Phase 3 — Implementation gates (before live)

- [ ] `BrokerAdapter` protocol + contract tests green
- [ ] `ExecutionService` routes all fills through adapter
- [ ] `RiskControlService` pre-trade gates implemented
- [ ] Unified exit queue (ExitRecommendation → RecommendationResult)
- [ ] Active positions wired to recommendation engine re-run
- [ ] `approve()` handles EXIT approval type
- [ ] HIGH_CONCERN soft-block + override audit
- [ ] `execution_audits` table populated
- [ ] Pilot auto-approve disabled for LIVE portfolios

---

## Phase 4 — Broker preparation (when PO selects vendor)

- [ ] Broker account opened and verified
- [ ] API credentials in secret manager (not .env in prod)
- [ ] Adapter implementation passes sandbox tests
- [ ] `get_positions()` reconciliation job scheduled
- [ ] Manual test: single share BUY + SELL in sandbox
- [ ] Failover: broker down → orders blocked, owner notified

---

## Phase 5 — Risk controls

- [ ] `max_deployable_capital` configured
- [ ] Daily loss limit set and tested (WARN + BLOCK)
- [ ] Regime slots match live risk appetite
- [ ] Single-name and sector caps verified
- [ ] Emergency stop tested (`ENTRIES_BLOCKED`, `ALL_BLOCKED`)
- [ ] Manual override audit trail verified

---

## Phase 6 — Compliance & audit

- [ ] Approval trail export for date range
- [ ] Execution audit export for date range
- [ ] Full lineage spot-check: 5 random trades trace to ranking_run
- [ ] Committee override audit (if HIGH_CONCERN used)
- [ ] Portfolio review sign-off process documented

---

## Phase 7 — Go-live day

- [ ] Database backup taken
- [ ] Set `execution_mode=LIVE` on target portfolio only
- [ ] Confirm paper portfolios remain `PAPER`
- [ ] First live entry: single small position with owner approval
- [ ] Verify fill in broker console matches `execution_audit`
- [ ] Reconciliation PASS post-trade
- [ ] Monitor for 5 trading sessions before scaling

---

## Phase 8 — Post-go-live (first 30 days)

- [ ] Daily reconciliation review
- [ ] Weekly risk utilization review
- [ ] No pilot auto flags enabled on live portfolio
- [ ] Incident log for any blocked/rejected orders
- [ ] PO retrospective at day 30

---

## Rollback triggers

Initiate rollback to `execution_mode=PAPER` if:

- Reconciliation FAIL persists > 1 session
- Unexplained position mismatch with broker
- Risk limit breach without owner acknowledgment
- Broker adapter error rate > 5%

See [rollback-guide.md](./rollback-guide.md) for platform rollback; live rollback = stop new orders + manual broker reconciliation.

---

## Sign-off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Product Owner | | | |
| Principal Architect | | | |
| Platform Engineering | | | |
| Owner (capital) | | | |

---

## Quick reference — maturity path

```
S0 Paper Trading          ← current (ADR-028)
    ↓ human approve + simulated fill
S1 Human-Approved Live    ← this checklist
    ↓ broker adapter + reconciliation
S2 Broker Integration     ← future (19_BROKER_ADAPTER_PRD)
```

Investment engines unchanged at every stage.
