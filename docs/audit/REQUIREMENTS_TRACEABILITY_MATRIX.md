# Requirements Traceability Matrix

**Audit:** AUDIT-01  
**Date:** 2026-06-05  
**Verification method:** Source code + pytest (574 passed)

Legend: **IMPLEMENTED** | **PARTIALLY_IMPLEMENTED** | **DOCUMENTED_ONLY** | **BROKEN** | **NOT_STARTED** | **DEPRECATED**

---

## Phase 1 — PRD Goals (G1–G8)

| Req ID | Description | Source | Priority | Expected Component | Expected API | Expected DB | Expected Tests | Status | Evidence |
|--------|-------------|--------|----------|-------------------|--------------|-------------|----------------|--------|----------|
| G1 | Deterministic ranking | PRD | P0 | `app/ranking/engine.py` | `POST /rankings/run` | `ranking_runs`, `ranking_results` | `test_golden_ranking.py` | **IMPLEMENTED** | Engine + 4 API endpoints + golden tests |
| G2 | Forward-return validation | PRD | P0 | `app/validation/` | `/validation/*` | `ranking_validation_reports` | `test_validation_api.py` | **IMPLEMENTED** | Tail `insufficient_data` ops pending |
| G3 | NIFTY 500 daily batch | PRD | P0 | `daily_batch_service.py` | `POST /ops/daily-batch/runs` | `daily_batch_runs` | `test_daily_batch_planner.py` | **PARTIALLY_IMPLEMENTED** | Planner unit tests only; no E2E; cron auth gap |
| G4 | Audit traceability | PRD | P0 | `platform_traceability.py` | `/observability/lineage/*` | `run_lineage_records` | `test_platform_traceability.py` | **IMPLEMENTED** | Lineage API + score reconstruction |
| G5 | Research analytics | PRD | P1 | factor/exit/RI services | `/analytics/factors/*`, `/analytics/exit/*` | factor/exit tables | 50+ unit tests | **IMPLEMENTED** | Full analytics stack |
| G6 | ARGS governance | PRD | P0 | `app/args/` | `/investment-committee/*` | args tables | 63+ unit tests | **IMPLEMENTED** | Real LLM plugins registered |
| G7 | SEE v2 | PRD | P1 | `app/stock_setup_evidence/` | `/research/stock-setup/*` | `stock_setup_research` | unit + API test | **IMPLEMENTED** | Strategy-aware analog search |
| G8 | No LLM ranking/sizing/approval | PRD | P0 | boundaries | — | — | `test_qrc_sqe_flag.py` | **IMPLEMENTED** | Ranking isolated from ARGS |

---

## Phase 2 — Recommendation Engine

| Req ID | Description | Source | Priority | Component | API | DB | Tests | Status | Evidence |
|--------|-------------|--------|----------|-----------|-----|-----|-------|--------|----------|
| R-ENTRY-01..06 | Entry rules | PRD 01 | P0 | `recommendation/engine.py` | `/recommendations/run` | `recommendation_results` | `test_engine.py` (17) | **IMPLEMENTED** | All rules in engine |
| R-HOLD-01 | Hold active | PRD 01 | P0 | same | same | same | same | **IMPLEMENTED** | |
| R-EXIT-01..04 | Exit triggers | PRD 01 | P0 | engine + exit_monitor | `/portfolio/exits/run` | `portfolio_exit_recommendations` | `test_exit_triggers.py` | **IMPLEMENTED** | |
| R-ARGS-01..04 | ARGS boundaries | PRD 01/08 | P0 | engine + ARGS | committee APIs | — | `test_advisory.py` | **IMPLEMENTED** | No action mutation |
| AC-RE-01 | Deterministic replay | PRD 01 | P0 | engine | — | — | golden in `test_engine.py` | **IMPLEMENTED** | |
| AC-RE-02 | Lineage on records | PRD 01 | P0 | models | GET endpoints | `ranking_run_id` FK | model tests | **IMPLEMENTED** | |
| AC-RE-03 | LLM cannot mutate action | PRD 01 | P0 | isolation | — | — | committee tests | **IMPLEMENTED** | |
| AC-RE-04 | BUY ≤ regime slots | PRD 01 | P0 | engine | — | — | engine tests | **IMPLEMENTED** | |
| AC-RE-05 | EXIT has reason_code | PRD 01 | P0 | engine | — | — | engine tests | **IMPLEMENTED** | |
| AC-RE-06 | Latest per strategy API | PRD 01 | P0 | service | `/recommendations/latest`, `/daily` | — | — | **IMPLEMENTED** | No integration API test |
| AC-RE-07 | ARGS packet block | PRD 01 | P1 | packet builder | committee | — | packet tests | **IMPLEMENTED** | |
| AC-CS-01..07 | Conviction scoring | PRD 02 | P0 | `conviction_scorer.py` | response schema | components JSON | `test_conviction_scorer.py` | **IMPLEMENTED** | conv_v1.1.0 |
| AC-LC-01 | Illegal transitions rejected | PRD 04 | P0 | service | approve/reject | `recommendation_approvals` | service tests | **PARTIALLY_IMPLEMENTED** | No explicit state machine module |
| AC-LC-02 | One current position | PRD 04 | P0 | portfolio service | `/portfolio/positions` | `portfolio_positions` | portfolio tests | **IMPLEMENTED** | |
| AC-LC-03 | Human approval gates | PRD 04 | P0 | API | approve/reject | approvals table | — | **IMPLEMENTED** | OwnerUser enforced |
| AC-LC-04 | Full lineage chain | PRD 04 | P1 | observability | lineage API | lineage records | integration | **PARTIALLY_IMPLEMENTED** | ranking→trade chain partial |
| AC-WNR-01..04 | Why-not framework | PRD 16 | P1 | engine | `/why-not/{symbol}` | reason_codes | engine | **IMPLEMENTED** | 9 reason codes in `engine.py` |

---

## Phase 2 — Portfolio & Paper

| Req ID | Description | Source | Priority | Component | API | DB | Tests | Status | Evidence |
|--------|-------------|--------|----------|-----------|-----|-----|-------|--------|----------|
| AC-PE-01 | Reconciliation ±0.1% | PRD 05 | P0 | `reconciliation/service.py` | `/portfolio/reconciliation` | `portfolio_reconciliation_reports` | `test_reconciliation.py` | **IMPLEMENTED** | Not portfolio-scoped |
| AC-PE-02 | Slot enforcement | PRD 05 | P0 | portfolio service | config | `portfolio_configs` | `test_position_sizing.py` | **IMPLEMENTED** | |
| AC-PE-03 | ARGS context truthful | PRD 05 | P1 | packet builder | committee | — | packet tests | **PARTIALLY_IMPLEMENTED** | Single-tenant context |
| AC-PE-04 | Idempotent recompute | PRD 05 | P0 | portfolio service | `/portfolio/recompute` | positions | service tests | **IMPLEMENTED** | |
| AC-PT-01 | Idempotent paper trade | PRD 06 | P0 | `PaperTradeService` | `/portfolio/trades/*` | `paper_trades` | service tests | **IMPLEMENTED** | No `portfolio_id` on trades |
| AC-PT-02 | BUY lineage | PRD 06 | P0 | execution adapter | execution API | execution_orders | execution tests | **IMPLEMENTED** | |
| AC-PT-03 | Positions reconcile | PRD 06 | P0 | reconciliation | reconcile | reports | recon tests | **IMPLEMENTED** | |
| AC-PT-04 | Attribution golden | PRD 06 | P1 | analytics | `/portfolio/attribution` | — | `test_analytics.py` | **IMPLEMENTED** | 409 gate on recon FAIL |
| AC-EX-01..04 | Exit framework | PRD 07 | P0 | exit_monitor | exits API | exit_recommendations | `test_exit_triggers.py` | **IMPLEMENTED** | No auto-sell (AC-EX-03) |

---

## Phase 2 — HITL, Execution, Risk, Live

| Req ID | Description | Source | Priority | Component | API | DB | Tests | Status | Evidence |
|--------|-------------|--------|----------|-----------|-----|-----|-------|--------|----------|
| AC-HITL-01 | No fill without APPROVED | PRD 11 | P0 | `ExecutionService` | `/execution/orders` | approvals | `test_execution_service.py` | **IMPLEMENTED** | |
| AC-HITL-02 | Approval audit export | PRD 11 | P2 | — | — | approvals | — | **NOT_STARTED** | No CSV export endpoint |
| AC-HITL-03 | Broker mock contract | PRD 11 | P1 | paper adapter | — | — | execution tests | **IMPLEMENTED** | Paper adapter full |
| AC-HITL-04 | ARGS disagreement non-blocking | PRD 11 | P1 | frontend | — | — | — | **PARTIALLY_IMPLEMENTED** | Backend OK; UX partial |
| AC-HITL-L01..06 | Live HITL | PRD 18 | P1 | execution | execution API | execution_* | partial | **PARTIALLY_IMPLEMENTED** | Paper works; live stub |
| AC-EXEC-01..02 | Unified ExecutionService | PRD 21 | P0 | `execution_service.py` | execution + portfolio trades | execution_orders | unit tests | **IMPLEMENTED** | Paper path |
| AC-EXEC-03 | Lineage on audit | PRD 21 | P0 | execution | — | execution_audit | unit test | **IMPLEMENTED** | |
| AC-EXEC-04 | Risk gate before order | PRD 21 | P0 | — | — | — | — | **NOT_STARTED** | No RiskControlService |
| AC-EXEC-05 | LIVE rejects pilot_auto | PRD 21 | P0 | config | daily batch | — | — | **PARTIALLY_IMPLEMENTED** | Flag exists; live stub |
| AC-EXEC-06 | Entry/exit same flow | PRD 21 | P0 | execution | same endpoints | — | unit | **IMPLEMENTED** | |
| AC-BRK-01..05 | Broker adapter | PRD 19 | P1 | adapters | — | — | zerodha test | **PARTIALLY_IMPLEMENTED** | Zerodha returns `not_implemented` |
| AC-RISK-01..06 | Risk controls | PRD 20 | P0 | — | — | — | — | **NOT_STARTED** | No pre-trade risk gates |
| K-03 | Approval endpoint unchanged | ADR-031 | P0 | recommendations | approve/reject | — | — | **IMPLEMENTED** | |
| K-04 | POST /execution/orders needs APPROVED | ADR-031 | P0 | execution | POST orders | — | unit | **IMPLEMENTED** | |
| K-13 | OWNER/ADMIN submit orders | ADR-031 | P0 | auth | OwnerUser + EXECUTION_WRITE | — | unit | **IMPLEMENTED** | |

---

## Phase 2 — Auth, Multi-Tenant, Pilot, Copilot, Frontend

| Req ID | Description | Source | Priority | Component | API | DB | Tests | Status | Evidence |
|--------|-------------|--------|----------|-----------|-----|-----|-------|--------|----------|
| ADR-027 | JWT + RBAC | ADR-027 | P0 | `auth_service.py` | `/auth/*` | users, roles, tokens | `test_auth_api.py` | **IMPLEMENTED** | Default JWT secret risk |
| ADR-027 | Portfolio-scoped tenancy | ADR-027 | P0 | `auth_deps.py` | PortfolioScope routes | memberships | `test_tenant_isolation.py` | **PARTIALLY_IMPLEMENTED** | Analytics tables global |
| ADR-028 | 90-day batch phases | ADR-028 | P0 | `paper_pilot_ops.py` | daily batch flags | — | `test_paper_pilot_ops.py` | **PARTIALLY_IMPLEMENTED** | Cron auth gap |
| ADR-029 | Pilot command center | ADR-029 | P1 | pilot service | `/pilot/*` (10 routes) | — | unit tests | **IMPLEMENTED** | No API integration tests |
| GR-01..06 | Copilot grounding | PRD 10 | P0 | `app/copilot/` | `/copilot/ask` | copilot_query_logs | 5 unit files | **IMPLEMENTED** | |
| AC-CP-01..04 | Copilot acceptance | PRD 10 | P1 | copilot service | ask + audit | logs | unit | **PARTIALLY_IMPLEMENTED** | No latency/load tests |
| AC-FE-01..08 | Frontend architecture | ADR-026 | P1 | `frontend/packages/*` | client hooks | — | route tests | **PARTIALLY_IMPLEMENTED** | 8/10 screens |
| AC-MOB-01..04 | Mobile MVP | PRD 09 | P1 | apps/mobile | same APIs | — | — | **PARTIALLY_IMPLEMENTED** | Missing /exits, /analytics |
| FP-01..06 | Frontend principles | FRONTEND_PRD | P1 | ui package | — | — | component tests | **PARTIALLY_IMPLEMENTED** | Citation nav unwired |
| FR-D/R/P/C/CP-* | Mobile FRs | MOBILE_PRD | P1 | screens | API clients | — | — | **PARTIALLY_IMPLEMENTED** | ~70% wired |

---

## Pilot KPIs

| Req ID | Description | Source | Status | Evidence |
|--------|-------------|--------|--------|----------|
| KPI-batch_completion | ≥95% batch completion | SUCCESS_METRICS | **PARTIALLY_IMPLEMENTED** | Metrics API exists; no historical proof |
| KPI-recon_pass | ≥98% recon pass | SUCCESS_METRICS | **PARTIALLY_IMPLEMENTED** | Recon service works; not multi-tenant |
| KPI-nav_coverage | ≥95% NAV days | SUCCESS_METRICS | **PARTIALLY_IMPLEMENTED** | NAV snapshot in batch; global table |
| GO-NOGO-recon | Zero recon FAIL 14d | SUCCESS_METRICS | **DOCUMENTED_ONLY** | Manual gate; not automated |

---

## Summary Counts (this matrix subset)

| Status | Count (approx.) |
|--------|-----------------|
| IMPLEMENTED | 52 |
| PARTIALLY_IMPLEMENTED | 28 |
| NOT_STARTED | 8 |
| DOCUMENTED_ONLY | 2 |
| BROKEN | 0 |
| DEPRECATED | 3 (`/research/*` routes) |

---

*Cross-reference: `API_AUDIT_REPORT.md`, `DATABASE_AUDIT_REPORT.md`, `TEST_COVERAGE_AUDIT.md` for module-level detail.*
