# Paper Trading Pilot — Risk Report

**Date:** 2026-06-05  
**Scope:** 90-day unattended paper trading pilot

---

## Risk register

| ID | Risk | Severity | Mitigation | Residual |
|----|------|----------|------------|----------|
| R1 | Reconciliation FAIL blocks analytics | Medium | NAV-based reported_nav fix; daily batch reconcile | Low |
| R2 | Pilot auto-approve bypasses HITL | High | Pilot-only flags; default false in prod | Medium (pilot only) |
| R3 | Exit monitor not auto-executed | Medium | `pilot_auto_execute` processes EXIT_APPROVED | Low |
| R4 | Slot limits not enforced at trade time | Medium | `PaperPilotOps` checks `get_limits()` before entry | Low |
| R5 | Benchmark data missing (^CRSLDX) | Medium | `ingest_portfolio_benchmarks` in batch | Low |
| R6 | Validation tail insufficient_data | Low | Does not block paper pilot; affects conviction input | Medium |
| R7 | Rank ordering not calibrated | Low | Documented; pilot uses conviction bands not rank #1 | Low |
| R8 | No CI — regressions undetected | High | Manual pytest before deploy; add CI in M3 | High |
| R9 | Committee Phase 3 not wired | Low | Advisory only; no pilot dependency | Low |
| R10 | Trust score not gating trades | Low | Observation only per PRD | N/A |

---

## Exit monitor review

| Trigger | Implemented | Auto-execute |
|---------|-------------|--------------|
| Rank drop | ✓ | Only via EXIT_APPROVED + pilot flag |
| Time stop | ✓ | Same |
| Stop loss | ✓ | Same |
| Trailing stop | ✓ | Same |
| Regime change | ✓ | Same |
| Alpha decay | ✓ | Same |
| Concentration | ✓ | Same |
| Liquidity | ✓ | Same |

**Governance:** Exit monitor writes `ExitRecommendation` (PENDING). Never mutates positions directly.

---

## Reconciliation gates

| Status | Analytics API | Pilot impact |
|--------|---------------|--------------|
| PASS | Allowed | Continue |
| WARNING | Allowed | Monitor |
| FAIL | 409 blocked | Stop pilot; investigate ledger |

---

## Trust metrics

`app/recommendation_analytics/trust_metrics.py` — **observation only**:

- Conviction calibration (band vs win rate)
- Recommendation stability (action churn)
- Data completeness reliability

**Does not feed back into conviction or recommendation engine** (per constraints).

---

## Recommended pilot risk controls

1. Alert on reconciliation FAIL (email/Slack — manual for pilot)
2. Cap `pilot_auto_execute` to `max_buy_per_day` regime slots
3. Daily dashboard review first 5 sessions
4. Kill switch: set `pilot_auto_execute=false` on batch request
5. Weekly trust metrics review (no auto-action)
