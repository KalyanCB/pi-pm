---
generated_at: 2026-06-07T03:43:13Z
generator: scripts/generate_context.py
---

# Gaps & Deferred Work

> Aggregated `left_off` from requirements registry + proposed ADRs.

## G2 — Forward-return validation (IMPLEMENTED)

- [ ] Validation tail ops (insufficient_data ingest expectation)

Evidence:
- `app/validation/`
- `tests/integration/api/test_validation_api.py`

## G3 — NIFTY 500 daily batch (PARTIALLY_IMPLEMENTED)

- [ ] E2E batch integration tests
- [ ] Cron auth hardening

Evidence:
- `app/services/daily_batch_service.py`
- `app/api/v1/daily_batch.py`
- `tests/unit/ops/test_daily_batch_planner.py`

## AC-RE-06 — Latest per strategy API (IMPLEMENTED)

- [ ] No integration API test for /recommendations/latest and /daily

Evidence:
- `app/api/v1/recommendations.py`
- `app/services/recommendation_service.py`

## AC-LC-01 — Illegal transitions rejected (PARTIALLY_IMPLEMENTED)

- [ ] No explicit state machine module

Evidence:
- `app/services/recommendation_service.py`
- `app/api/v1/recommendations.py`

## AC-LC-04 — Full lineage chain (PARTIALLY_IMPLEMENTED)

- [ ] ranking→trade chain partial

Evidence:
- `app/services/traceability_service.py`
- `tests/unit/services/test_platform_traceability.py`

## AC-PE-01 — Reconciliation ±0.1% (IMPLEMENTED)

- [ ] Not portfolio-scoped reconciliation

Evidence:
- `app/portfolio/reconciliation/service.py`
- `tests/unit/portfolio/test_reconciliation.py`

## AC-PE-03 — ARGS context truthful (PARTIALLY_IMPLEMENTED)

- [ ] Single-tenant portfolio context in packet builder

Evidence:
- `app/args/builders/investment_review_packet_builder.py`
- `tests/unit/args/test_packet_builder.py`

## AC-PT-01 — Idempotent paper trade (IMPLEMENTED)

- [ ] No portfolio_id on paper_trades

Evidence:
- `app/services/paper_trade_service.py`
- `tests/unit/services/test_paper_trade_lineage.py`

## AC-EX — Exit framework (AC-EX-01..04) (IMPLEMENTED)

- [ ] No auto-sell (AC-EX-03) except paper auto / ADR-033 critical (proposed)
- [ ] Exit monitor skipped in daily batch when HITL_ENABLED=true
- [ ] stop_loss_price on DB model; not exposed on position API/UI

Evidence:
- `app/portfolio/exit_monitor/service.py`
- `app/api/v1/portfolio.py`
- `tests/unit/portfolio/test_exit_triggers.py`

## AC-HITL-02 — Approval audit export (NOT_STARTED)

- [ ] No CSV export endpoint for approvals

## AC-HITL-04 — ARGS disagreement non-blocking (PARTIALLY_IMPLEMENTED)

- [ ] Backend OK; frontend UX partial

Evidence:
- `app/args/`
- `frontend/packages/ui/src/screens/CommitteeScreen.tsx`

## AC-HITL-L — Live HITL (AC-HITL-L01..06) (PARTIALLY_IMPLEMENTED)

- [ ] Paper path works; live broker stub

Evidence:
- `app/execution/services/execution_service.py`
- `app/execution/adapters/zerodha_kite.py`
- `tests/unit/execution/test_execution_service.py`

## AC-EXEC-04 — Risk gate before order (NOT_STARTED)

- [ ] No RiskControlService pre-trade gate

## AC-EXEC-05 — LIVE rejects pilot_auto (PARTIALLY_IMPLEMENTED)

- [ ] Flag exists; live broker stub

Evidence:
- `app/ops/daily_batch/paper_pilot_ops.py`
- `app/execution/adapters/zerodha_kite.py`

## AC-BRK — Broker adapter (AC-BRK-01..05) (PARTIALLY_IMPLEMENTED)

- [ ] Zerodha adapter returns not_implemented

Evidence:
- `app/execution/adapters/zerodha_kite.py`
- `tests/unit/execution/test_zerodha_adapter.py`

## AC-RISK — Pre-trade risk controls (AC-RISK-01..06) (NOT_STARTED)

- [ ] No RiskControlService
- [ ] No pre-trade risk gates

## ADR-027-JWT — JWT auth + RBAC (IMPLEMENTED)

- [ ] Default JWT secret risk in dev

Evidence:
- `app/services/auth_service.py`
- `app/api/v1/auth.py`
- `tests/integration/api/test_auth_api.py`

## ADR-027-TENANCY — Portfolio-scoped tenancy (PARTIALLY_IMPLEMENTED)

- [ ] Analytics tables global (not portfolio-scoped)

Evidence:
- `app/api/auth_deps.py`
- `tests/integration/api/test_tenant_isolation.py`

## ADR-028 — 90-day paper trading batch phases (PARTIALLY_IMPLEMENTED)

- [ ] Cron auth gap

Evidence:
- `app/ops/daily_batch/paper_pilot_ops.py`
- `tests/unit/ops/test_paper_pilot_ops.py`

## ADR-029 — Pilot command center (IMPLEMENTED)

- [ ] No API integration tests for /pilot/*

Evidence:
- `app/services/pilot_command_center_service.py`
- `app/api/v1/pilot_ops.py`
- `tests/unit/ops/test_pilot_command_center.py`

## AC-CP — Copilot acceptance (AC-CP-01..04) (PARTIALLY_IMPLEMENTED)

- [ ] No latency/load acceptance tests

Evidence:
- `app/services/copilot_service.py`
- `tests/unit/copilot/test_copilot_service.py`

## AC-FE — Frontend architecture (AC-FE-01..08) (PARTIALLY_IMPLEMENTED)

- [ ] 8/10 screens wired
- [ ] Missing /exits and /analytics routes

Evidence:
- `frontend/packages/ui/src/screens/`
- `frontend/packages/hooks/src/queries/`
- `context/canonical/frontend/FEATURE_INTEGRATION_REPORT.md`

## AC-MOB — Mobile MVP (AC-MOB-01..04) (PARTIALLY_IMPLEMENTED)

- [ ] Missing /exits and /analytics screens

Evidence:
- `frontend/apps/mobile/`
- `context/canonical/frontend/FEATURE_INTEGRATION_REPORT.md`

## FP-FE — Frontend principles (FP-01..06) (PARTIALLY_IMPLEMENTED)

- [ ] Citation deep-link navigation unwired

Evidence:
- `frontend/packages/ui/`
- `context/canonical/frontend/DESIGN_SYSTEM.md`

## FR-MOB — Mobile functional requirements (FR-D/R/P/C/CP-*) (PARTIALLY_IMPLEMENTED)

- [ ] ~70% API wiring complete

Evidence:
- `frontend/apps/mobile/`
- `context/canonical/frontend/FEATURE_INTEGRATION_REPORT.md`

## KPI-batch — ≥95% batch completion (PARTIALLY_IMPLEMENTED)

- [ ] Metrics API exists; no historical proof

Evidence:
- `app/api/v1/pilot_ops.py`
- `app/services/pilot_command_center_service.py`

## KPI-recon — ≥98% recon pass rate (PARTIALLY_IMPLEMENTED)

- [ ] Recon service works; not multi-tenant scoped

Evidence:
- `app/portfolio/reconciliation/service.py`
- `tests/unit/portfolio/test_reconciliation.py`

## KPI-nav — ≥95% NAV coverage days (PARTIALLY_IMPLEMENTED)

- [ ] NAV snapshot in batch; global table

Evidence:
- `app/services/daily_batch_service.py`
- `app/services/portfolio_service.py`

## GO-NOGO-recon — Zero recon FAIL for 14 days (DOCUMENTED_ONLY)

- [ ] Manual gate; not automated

Evidence:
- `context/canonical/runbooks/LIVE_TRADING_SAFETY_CHECKLIST.md`

## RCEE — Regime Coverage Edge Engine (IMPLEMENTED)

- [ ] Live validation gate integration (ADR-032)

Evidence:
- `app/recommendation/regime_edge_engine.py`
- `tests/unit/recommendation/test_regime_edge_engine.py`

## ADR-033 — Intraday exit monitor + stop override (PARTIALLY_IMPLEMENTED)

- [ ] PO sign-off checklist (A–G)
- [ ] Live QuoteProvider (Kite)
- [ ] Intraday scheduler (1–5 min NSE session)
- [ ] Notification service wired to urgency
- [ ] Broker GTC stop at entry (live S1)
- [ ] AUTO_EXIT_ON_CRITICAL_STOP live path

Evidence:
- `app/portfolio/exit_monitor/intraday_service.py`
- `app/portfolio/exit_monitor/quote_provider.py`
- `app/portfolio/exit_monitor/notification.py`
- `tests/unit/portfolio/test_intraday_exit_monitor.py`

## ADR-032 — Entry timing & validation gate (PROPOSED)

- [ ] PO gate mode selection (per_run_strict vs strategy_trust vs watch_hitl)
- [ ] Freshness check at approve()
- [ ] Deploy lane API

Evidence:
- `context/canonical/decisions/ADR-032-IMPLEMENTATION.md`

## ADR-030 — Live investing (S0→S1→S2) (PARTIALLY_IMPLEMENTED)

- [ ] Zerodha live order placement
- [ ] Broker reconciliation sync
- [ ] Unified exit queue (exit rec → RecommendationResult)

Evidence:
- `app/execution/adapters/zerodha_kite.py`
- `context/canonical/runbooks/LIVE_TRADING_SAFETY_CHECKLIST.md`

## FP-REC-HIST — Recommendations historical date picker + execution panel (IMPLEMENTED)

- [ ] Link paper trade exit_reason on expand panel

Evidence:
- `frontend/packages/ui/src/atoms/DatePicker.tsx`
- `frontend/packages/ui/src/molecules/RecommendationExecutionPanel.tsx`
- `frontend/packages/ui/src/molecules/ExitMonitorCard.tsx`
