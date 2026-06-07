# Authoritative Requirements Index

**Audit:** AUDIT-01  
**Date:** 2026-06-05  
**Auditor:** Independent Principal Architect (code-verified)  
**Repository:** `/Users/kalyancb/pi-pm`  
**Branch:** `feature/see-v2`

---

## 1. Source Hierarchy (L0 → L7)

| Tier | Role | Primary paths |
|------|------|---------------|
| **L0** | Entry index | `docs/README.md` |
| **L1** | Platform handoff truth | `docs/HANDOFF.md`, `docs/PLATFORM-HANDOFF-2026.md` |
| **L2** | Phase 1 PRD (shipped research) | `docs/AI/01_PRODUCT/PRD.md` (G1–G8) |
| **L3** | Phase 2 product pack | `docs/product-next/*.md`, `docs/product-next/PO_SIGNOFF_2026_06_04.md` |
| **L4** | Architecture ADRs | `docs/architecture/ADR-021` … `ADR-031`, `docs/DECISION_LOG.md` (ADR-001–020) |
| **L5** | Traceability (may be stale) | `docs/po-discovery/09_REQUIREMENTS_TRACEABILITY_MATRIX.md` |
| **L6** | Domain boundaries | `docs/domain-boundaries.md` |
| **L7** | Surface specs | `docs/frontend/`, `docs/mobile/`, `docs/copilot/`, `docs/paper-pilot/` |

**Note:** `docs/DECISION_LOG.md` ADR-021 entry is a proposed factor-interaction draft; governing Phase 2 ADR is `docs/architecture/ADR-021-Recommendation-Platform-Architecture.md`. **ADR-025 does not exist** (sequence jumps 024 → 026).

---

## 2. Document Catalog

| Document | Area | Key IDs | Claims / role |
|----------|------|---------|---------------|
| `docs/README.md` | Meta | — | Index; 312 tests (stale); migration `20260609_0018` |
| `docs/HANDOFF.md` | Meta | — | Sprints 6.1–8.6 complete |
| `docs/PLATFORM-HANDOFF-2026.md` | Platform | ADR-001 | Paper/portfolio **stub** (Jun 4 — superseded) |
| `docs/domain-boundaries.md` | Architecture | ADR-004 | Portfolio/execution out of scope (pre-Phase 2) |
| `docs/AI/01_PRODUCT/PRD.md` | Phase 1 | **G1–G8** | Research pipeline shipped |
| `docs/IMPLEMENTATION_SUMMARY.md` | Phase 2 | R-*, AC-* | P1–P3 + M2 shipped; **386 tests** (stale) |
| `docs/po-discovery/09_REQUIREMENTS_TRACEABILITY_MATRIX.md` | Traceability | G1–G8 | Paper/portfolio **orphan** (stale) |
| `docs/po-discovery/04_API_CATALOG.md` | API | — | **No auth** (stale) |
| `docs/po-discovery/PRODUCT_MATURITY_SCORECARD.md` | Maturity | — | Rec 25%, Portfolio 12%, weighted ~72% |
| `docs/architecture/ADR-021` … `ADR-031` | Architecture | ADR-021–031 | Phase 2 binding decisions |
| `docs/product-next/01`–`21_*.md` | Product | R-*, AC-* | Phase 2 PRDs |
| `docs/frontend/FRONTEND_PRD.md` | Frontend | FP-*, NFR-* | Bloomberg Terminal Lite |
| `docs/mobile/MOBILE_PRD.md` | Mobile | FR-* | Five-screen contracts |
| `docs/copilot/COPILOT_*.md` | Copilot | GR-*, INTENT-* | Grounding + refusal |
| `docs/paper-pilot/*.md` | Pilot | KPI-*, alert codes | 90-day pilot gates |

---

## 3. Requirements Index by Area

### 3.1 Phase 1 — G1–G8 (`docs/AI/01_PRODUCT/PRD.md`)

| Requirement | Source | ID | Area | Description |
|-------------|--------|-----|------|-------------|
| Deterministic ranking | PRD | G1 | Ranking | Same inputs → same outputs |
| Forward-return validation | PRD | G2 | Validation | IC, deciles, insufficient_data |
| NIFTY 500 daily ops | PRD | G3 | Universe/Ops | Batch orchestrator |
| Audit traceability | PRD | G4 | Traceability | Lineage, observability |
| Research analytics | PRD | G5 | Analytics | Factor IC, exit, RI |
| ARGS governance | PRD | G6 | Committee | Packets, 5 committees + CRO |
| SEE v2 setup evidence | PRD | G7 | Research | Strategy-aware analog search |
| No LLM ranking/sizing/approval | PRD | G8 | Governance | Non-goals enforced |

### 3.2 Phase 2 — PO Principles (`docs/product-next/PO_SIGNOFF_2026_06_04.md`)

| Requirement | Source | ID | Area |
|-------------|--------|-----|------|
| Deterministic ranking sacred | PO Signoff | Principle 1 | Ranking |
| Validation sacred | PO Signoff | Principle 2 | Validation |
| LLMs must not influence ranking | PO Signoff | Principle 3 | Governance |
| LLMs must not influence conviction | PO Signoff | Principle 4 | Recommendation |
| LLMs must not influence sizing | PO Signoff | Principle 5 | Portfolio |
| LLMs must not approve trades | PO Signoff | Principle 6 | HITL |
| Human in loop entries/exits | PO Signoff | Principle 7 | HITL |
| RE between Validation and ARGS | PO Signoff | Principle 8 | Recommendation |
| ARGS advisory only | PO Signoff | Principle 9 | Committee |

### 3.3 Recommendation Engine (`docs/product-next/01_RECOMMENDATION_ENGINE_PRD.md`)

| ID | Description |
|----|-------------|
| R-ENTRY-01..06 | Entry scoring gates |
| R-HOLD-01 | Active hold |
| R-EXIT-01..04 | Exit triggers |
| R-ARGS-01..04 | Committee advisory boundaries |
| AC-RE-01..07 | Acceptance criteria |

### 3.4 Conviction (`docs/product-next/02_CONVICTION_SCORING_PRD.md`)

| ID | Description |
|----|-------------|
| AC-CS-01..07 | Golden fixture, bands, no LLM, no committee keys |

### 3.5 Lifecycle (`docs/product-next/04_RECOMMENDATION_LIFECYCLE.md`)

| ID | Description |
|----|-------------|
| AC-LC-01..04 | State machine, position integrity, HITL, lineage |

### 3.6 Portfolio (`docs/product-next/05_PORTFOLIO_ENGINE_PRD.md`)

| ID | Description |
|----|-------------|
| AC-PE-01..04 | Reconciliation, slots, ARGS context, idempotent recompute |

### 3.7 Paper Trading (`docs/product-next/06_PAPER_TRADING_PRD.md`)

| ID | Description |
|----|-------------|
| AC-PT-01..04 | Idempotent fills, lineage, recon, attribution |

### 3.8 Exit (`docs/product-next/07_EXIT_DECISION_FRAMEWORK.md`)

| ID | Description |
|----|-------------|
| AC-EX-01..04 | Trigger mapping, replay fidelity, no auto-sell |

### 3.9 Committee (`docs/product-next/08_AI_INVESTMENT_COMMITTEE_PRD.md`)

| ID | Description |
|----|-------------|
| AC-AIC-01..05 | Pipeline order, schema, CRO disagreement, mobile payload |

### 3.10 Copilot (`docs/product-next/10_AI_COPILOT_PRD.md`, `docs/copilot/`)

| ID | Description |
|----|-------------|
| GR-01..06 | Citation, refusal, lineage |
| AC-CP-01..04 | Golden Q&A, injection, audit, latency |
| INTENT-* | 12 explain-only intents |

### 3.11 HITL / Execution / Risk / Live

| Source | IDs |
|--------|-----|
| `11_HUMAN_IN_LOOP_EXECUTION_PRD.md` | AC-HITL-01..04 |
| `18_HUMAN_IN_LOOP_LIVE_INVESTING_PRD.md` | AC-HITL-L01..06 |
| `19_BROKER_ADAPTER_PRD.md` | AC-BRK-01..05 |
| `20_RISK_CONTROL_PRD.md` | AC-RISK-01..06 |
| `21_EXECUTION_WORKFLOW_PRD.md` | AC-EXEC-01..06 |
| `ADR-031` | K-03, K-04, K-13 |

### 3.12 Frontend / Mobile

| Source | IDs |
|--------|-----|
| `docs/frontend/FRONTEND_PRD.md` | FP-01..06, NFR-01..06 |
| `docs/frontend/IMPLEMENTATION_ROADMAP.md` | AC-FE-01..08 |
| `docs/mobile/MOBILE_PRD.md` | FR-D/R/P/C/CP-*, NFR-01..05 |
| `docs/product-next/09_MOBILE_APP_PRD.md` | AC-MOB-01..04 |

### 3.13 Pilot Operations

| Source | IDs |
|--------|-----|
| `docs/paper-pilot/SUCCESS_METRICS.md` | KPI-batch_completion, KPI-recon_pass, KPI-nav_coverage |
| `docs/paper-pilot/runbooks/ALERTING_FRAMEWORK.md` | batch_failed, reconciliation_fail, etc. |
| `docs/architecture/ADR-028`, `ADR-029` | 90-day batch phases, `/pilot/*` |

### 3.14 Architecture ADRs 021–031

| ADR | Area | Key decision |
|-----|------|--------------|
| ADR-021 | Recommendation | RE between Validation & ARGS; HITL mandatory |
| ADR-022 | Analytics | Observation-only; no feedback loops |
| ADR-023 | Committee | External Investment Committee; HIGH_CONCERN |
| ADR-024 | Portfolio | Ledger = SoT; recon FAIL → 409 |
| ADR-026 | Frontend | RN + RN Web monorepo |
| ADR-027 | Auth | JWT + portfolio-scoped RBAC |
| ADR-028 | Paper | 90-day unattended batch phases |
| ADR-029 | Pilot Ops | Command center read-only APIs |
| ADR-030 | Live | S0→S1→S2 maturity path |
| ADR-031 | Execution | Unified ExecutionAdapter; state machine |

---

## 4. Documented Completion Claims (for drift comparison)

| Source | Claim | Value |
|--------|-------|-------|
| `docs/README.md` / `HANDOFF.md` | Tests | 312 |
| `docs/IMPLEMENTATION_SUMMARY.md` | Tests | 386 |
| `docs/ops/production-readiness-scorecard.md` | Platform readiness | 85/100 |
| `docs/po-discovery/PRODUCT_MATURITY_SCORECARD.md` | Weighted product | ~72/100 |
| `docs/po-discovery/PRODUCT_MATURITY_SCORECARD.md` | Recommendation | 25/100 |
| `docs/po-discovery/PRODUCT_MATURITY_SCORECARD.md` | Portfolio | 12/100 |
| `docs/paper-pilot/PILOT_READINESS_REPORT.md` | 90-day unattended | 78/100 |
| `docs/copilot/COPILOT_EVALUATION_REPORT.md` | Copilot readiness | 78/100 |

**Code-verified (2026-06-05):** **574 tests collected, 574 passed** (`.venv/bin/python -m pytest tests/`).

---

## 5. Stale Document Warnings

**Updated 2026-06-05** — primary handoff docs refreshed. Items below were stale at audit time; status after doc refresh:

| Document | Was stale | Now |
|----------|-----------|-----|
| `README.md`, `HANDOFF.md`, `PLATFORM-HANDOFF-2026.md` | 312 tests, migration 0018 | **Updated** — 574 tests, 0026 |
| `po-discovery/04_API_CATALOG.md` | No auth, ~67 routes | **Updated** — JWT + ~130 routes |
| `po-discovery/09 RTM` | Paper/portfolio orphan | **Updated** |
| `domain-boundaries.md` | Portfolio out of scope | **Updated** — Phase 2 domains |
| `AUTHENTICATION_PREPARATION.md` | Auth not implemented | **Updated** — implemented |
| `frontend/docs/ARCHITECTURE_REPORT.md` | Placeholders | **Updated** — live integration |
| `po-discovery/10–12 gap analyses` | Pre-Phase 2 | **Banner added** — point to audit |

---

*Next: `REQUIREMENTS_TRACEABILITY_MATRIX.md` for per-requirement implementation status.*
