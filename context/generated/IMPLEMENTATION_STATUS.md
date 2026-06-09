---
generated_at: 2026-06-09T00:56:52Z
generator: scripts/generate_context.py
---

# Implementation Status

Designed → Planned → Implemented → Left off. Source: `context/registry/requirements.yaml`.

| ID | Capability | Designed | Planned | Status | Left off |
|----|------------|----------|---------|--------|----------|
| G1 | Deterministic ranking | yes | no | **IMPLEMENTED** | — |
| G2 | Forward-return validation | yes | no | **IMPLEMENTED** | Validation tail ops (insufficient_data ingest expectation) |
| G3 | NIFTY 500 daily batch | yes | yes | **PARTIALLY_IMPLEMENTED** | E2E batch integration tests; Cron auth hardening |
| G4 | Audit traceability | yes | no | **IMPLEMENTED** | — |
| G5 | Research analytics | yes | no | **IMPLEMENTED** | — |
| G6 | ARGS governance | yes | no | **IMPLEMENTED** | — |
| G7 | Stock Setup Evidence Engine v2 | yes | no | **IMPLEMENTED** | — |
| G8 | No LLM ranking/sizing/approval | yes | no | **IMPLEMENTED** | — |
| R-ENTRY | Entry rules (R-ENTRY-01..06) | yes | no | **IMPLEMENTED** | — |
| R-HOLD | Hold active positions (R-HOLD-01) | yes | no | **IMPLEMENTED** | — |
| R-EXIT | Exit triggers (R-EXIT-01..04) | yes | no | **IMPLEMENTED** | — |
| R-ARGS | ARGS boundaries (R-ARGS-01..04) | yes | no | **IMPLEMENTED** | — |
| AC-RE-01 | Deterministic replay | yes | no | **IMPLEMENTED** | — |
| AC-RE-02 | Lineage on recommendation records | yes | no | **IMPLEMENTED** | — |
| AC-RE-03 | LLM cannot mutate action | yes | no | **IMPLEMENTED** | — |
| AC-RE-04 | BUY ≤ regime slots | yes | no | **IMPLEMENTED** | — |
| AC-RE-05 | EXIT has reason_code | yes | no | **IMPLEMENTED** | — |
| AC-RE-06 | Latest per strategy API | yes | no | **IMPLEMENTED** | No integration API test for /recommendations/latest and /daily |
| AC-RE-07 | ARGS packet block | yes | no | **IMPLEMENTED** | — |
| AC-CS | Conviction scoring (AC-CS-01..07) | yes | no | **IMPLEMENTED** | — |
| AC-LC-01 | Illegal transitions rejected | yes | yes | **PARTIALLY_IMPLEMENTED** | No explicit state machine module |
| AC-LC-02 | One current position per symbol | yes | no | **IMPLEMENTED** | — |
| AC-LC-03 | Human approval gates | yes | no | **IMPLEMENTED** | — |
| AC-LC-04 | Full lineage chain | yes | yes | **PARTIALLY_IMPLEMENTED** | ranking→trade chain partial |
| AC-WNR | Why-not framework (AC-WNR-01..04) | yes | no | **IMPLEMENTED** | — |
| AC-PE-01 | Reconciliation ±0.1% | yes | no | **IMPLEMENTED** | Not portfolio-scoped reconciliation |
| AC-PE-02 | Slot enforcement | yes | no | **IMPLEMENTED** | — |
| AC-PE-03 | ARGS context truthful | yes | yes | **PARTIALLY_IMPLEMENTED** | Single-tenant portfolio context in packet builder |
| AC-PE-04 | Idempotent recompute | yes | no | **IMPLEMENTED** | — |
| AC-PT-01 | Idempotent paper trade | yes | no | **IMPLEMENTED** | No portfolio_id on paper_trades |
| AC-PT-02 | BUY lineage on paper trade | yes | no | **IMPLEMENTED** | — |
| AC-PT-03 | Positions reconcile after trade | yes | no | **IMPLEMENTED** | — |
| AC-PT-04 | Attribution golden test | yes | no | **IMPLEMENTED** | — |
| AC-EX | Exit framework (AC-EX-01..04) | yes | no | **IMPLEMENTED** | No auto-sell (AC-EX-03) except paper auto / ADR-033 critical (proposed); Exit... |
| AC-HITL-01 | No fill without APPROVED | yes | no | **IMPLEMENTED** | — |
| AC-HITL-02 | Approval audit export | yes | yes | **NOT_STARTED** | No CSV export endpoint for approvals |
| AC-HITL-03 | Broker mock contract | yes | no | **IMPLEMENTED** | — |
| AC-HITL-04 | ARGS disagreement non-blocking | yes | yes | **PARTIALLY_IMPLEMENTED** | Backend OK; frontend UX partial |
| AC-HITL-L | Live HITL (AC-HITL-L01..06) | yes | yes | **PARTIALLY_IMPLEMENTED** | Paper path works; live broker stub |
| AC-EXEC-01 | Unified ExecutionService (paper path) | yes | no | **IMPLEMENTED** | — |
| AC-EXEC-02 | ExecutionService shared by portfolio trades | yes | no | **IMPLEMENTED** | — |
| AC-EXEC-03 | Lineage on execution audit | yes | no | **IMPLEMENTED** | — |
| AC-EXEC-04 | Risk gate before order | yes | yes | **NOT_STARTED** | No RiskControlService pre-trade gate |
| AC-EXEC-05 | LIVE rejects pilot_auto | yes | yes | **PARTIALLY_IMPLEMENTED** | Flag exists; live broker stub |
| AC-EXEC-06 | Entry/exit same execution flow | yes | no | **IMPLEMENTED** | — |
| AC-BRK | Broker adapter (AC-BRK-01..05) | yes | yes | **PARTIALLY_IMPLEMENTED** | Zerodha adapter returns not_implemented |
| AC-RISK | Pre-trade risk controls (AC-RISK-01..06) | yes | yes | **NOT_STARTED** | No RiskControlService; No pre-trade risk gates |
| K-03 | Approval endpoint unchanged | yes | no | **IMPLEMENTED** | — |
| K-04 | POST /execution/orders requires APPROVED | yes | no | **IMPLEMENTED** | — |
| K-13 | OWNER/ADMIN submit orders | yes | no | **IMPLEMENTED** | — |
| ADR-027-JWT | JWT auth + RBAC | yes | no | **IMPLEMENTED** | Default JWT secret risk in dev |
| ADR-027-TENANCY | Portfolio-scoped tenancy | yes | yes | **PARTIALLY_IMPLEMENTED** | Analytics tables global (not portfolio-scoped) |
| ADR-028 | 90-day paper trading batch phases | yes | yes | **PARTIALLY_IMPLEMENTED** | Cron auth gap |
| ADR-029 | Pilot command center | yes | no | **IMPLEMENTED** | No API integration tests for /pilot/* |
| GR-COPILOT | Copilot grounding (GR-01..06) | yes | no | **IMPLEMENTED** | — |
| AC-CP | Copilot acceptance (AC-CP-01..04) | yes | yes | **PARTIALLY_IMPLEMENTED** | No latency/load acceptance tests |
| AC-FE | Frontend architecture (AC-FE-01..08) | yes | yes | **PARTIALLY_IMPLEMENTED** | 8/10 screens wired; Missing /exits and /analytics routes |
| AC-MOB | Mobile MVP (AC-MOB-01..04) | yes | yes | **PARTIALLY_IMPLEMENTED** | Missing /exits and /analytics screens |
| FP-FE | Frontend principles (FP-01..06) | yes | yes | **PARTIALLY_IMPLEMENTED** | Citation deep-link navigation unwired |
| FR-MOB | Mobile functional requirements (FR-D/R/P/C/CP-*) | yes | yes | **PARTIALLY_IMPLEMENTED** | ~70% API wiring complete |
| KPI-batch | ≥95% batch completion | yes | yes | **PARTIALLY_IMPLEMENTED** | Metrics API exists; no historical proof |
| KPI-recon | ≥98% recon pass rate | yes | yes | **PARTIALLY_IMPLEMENTED** | Recon service works; not multi-tenant scoped |
| KPI-nav | ≥95% NAV coverage days | yes | yes | **PARTIALLY_IMPLEMENTED** | NAV snapshot in batch; global table |
| GO-NOGO-recon | Zero recon FAIL for 14 days | yes | yes | **DOCUMENTED_ONLY** | Manual gate; not automated |
| RCEE | Regime Coverage Edge Engine | yes | no | **IMPLEMENTED** | Live validation gate integration (ADR-032) |
| ADR-033 | Intraday exit monitor + stop override | yes | yes | **PARTIALLY_IMPLEMENTED** | PO sign-off checklist (A–G); Live QuoteProvider (Kite); Intraday scheduler (1... |
| ADR-032 | Entry timing & validation gate | yes | yes | **PROPOSED** | PO gate mode selection (per_run_strict vs strategy_trust vs watch_hitl); Fres... |
| ADR-030 | Live investing (S0→S1→S2) | yes | yes | **PARTIALLY_IMPLEMENTED** | Zerodha live order placement; Broker reconciliation sync; Unified exit queue ... |
| ADR-031 | Unified execution architecture | yes | no | **IMPLEMENTED** | — |
| FP-REC-HIST | Recommendations historical date picker + execution panel | yes | no | **IMPLEMENTED** | Link paper trade exit_reason on expand panel |

## Summary

- **DOCUMENTED_ONLY**: 1
- **IMPLEMENTED**: 45
- **NOT_STARTED**: 3
- **PARTIALLY_IMPLEMENTED**: 20
- **PROPOSED**: 1