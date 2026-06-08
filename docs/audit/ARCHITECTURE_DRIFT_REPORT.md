# Architecture Drift Report

**Audit:** AUDIT-01  
**Date:** 2026-06-05  
**Method:** Compare authoritative docs vs `app/` + `frontend/` source

---

## 1. PRD / ADR Says X → Code Does Y

| Doc says | Code does | Severity | Evidence |
|----------|-----------|----------|----------|
| ADR-027 portfolio-scoped tenancy on all investor data | NAV, cash, recon, paper_trades are **global** | **P1** | `app/models/portfolio_analytics.py` — no `portfolio_id` |
| ADR-024 recon FAIL blocks analytics (409) | **Implemented** on attribution API | ✓ Aligned | `portfolio.py` performance gating |
| AC-RISK pre-trade gates before every order | **No RiskControlService** | **P0** | No `app/risk/` module |
| AC-BRK live broker adapter | Zerodha returns `not_implemented` | **P1** | `zerodha_kite.py:51-74` |
| ADR-028 unattended 90-day via HTTP cron | Cron script **lacks auth** | **P0** | `run_daily_nifty500_batch.py:77` |
| ADR-023 HIGH_CONCERN soft-block on live entry | **Not implemented** in execution path | **P1** | AC-HITL-L03 missing |
| Domain boundaries: portfolio out of scope | Full portfolio engine shipped | Doc stale | `domain-boundaries.md` pre-Phase 2 |
| PLATFORM-HANDOFF: paper/portfolio stub | Full lifecycle implemented | Doc stale | Jun 4 handoff vs Jun 5 implementation |
| Ranking v2 production | Only in `ranking_research/` | ✓ Aligned | Correctly research-only |
| ARGS Phase 3 committee independence | Phase 2 ~79% per handoff | Partial | Real plugins registered; HIGH_CONCERN path may be unreachable |

---

## 2. Documentation Drift

**Doc refresh (2026-06-05):** Primary handoff docs, API catalog, RTM, domain boundaries, auth prep, frontend reports, and maturity scorecard were updated. Gap analyses 10–12 carry stale banners.

| Document | Stated truth | Actual truth (2026-06-05) | Action |
|----------|--------------|---------------------------|--------|
| `docs/README.md` | 312 tests | **574 tests** | Update count |
| `docs/IMPLEMENTATION_SUMMARY.md` | 386 tests | **574 tests** | Update count |
| `po-discovery/04_API_CATALOG.md` | No auth | **JWT on all domain routes** | Supersede |
| `po-discovery/09 RTM` | Paper/portfolio orphan | **Services + APIs exist** | Supersede |
| `PLATFORM-HANDOFF-2026.md` | Paper stub | **Implemented** | Update §portfolio |
| `domain-boundaries.md` | Portfolio out of scope | **In scope — shipped** | Update boundaries |
| `docs/frontend/AUTHENTICATION_PREPARATION.md` | Not implemented | **Full JWT in frontend** | Archive or update |
| `frontend/docs/ARCHITECTURE_REPORT.md` | Placeholder screens | **Live API screens** | Update |
| `po-discovery/04_API_CATALOG.md` | ~67 endpoints | **~130 endpoints** | Regenerate catalog |
| `PRODUCT_MATURITY_SCORECARD.md` | Rec 25%, Portfolio 12% | **~65% / ~58%** (audit estimate) | Rescore |
| `DECISION_LOG.md` ADR-021 | Factor interaction draft | **Superseded** by `ADR-021-Recommendation-Platform-Architecture.md` | Clarify index |

---

## 3. Naming Drift

| Context | Doc name | Code name | Notes |
|---------|----------|-----------|-------|
| Committee | "Investment Committee" (ADR-023) | `/investment-committee/*` + internal ARGS | Aligned |
| Research API | `/research/*` deprecated | `/investment-committee/*` canonical | Router tag `research-deprecated` |
| Paper trades | `paper_trades` table | Also `execution_orders` via unified execution | ADR-031 migration |
| Actor for auto-approve | "pilot" in docs | `paper_pilot` actor string in code | Minor |
| Conviction version | conv_v1.1 in PRD | `conv_v1.1.0` in code | Aligned |
| Mobile PRD | 5 screens | 8 routes (missing 2 spec screens) | Partial |

---

## 4. Dead Documentation

| Path | Why dead |
|------|----------|
| `docs/frontend/AUTHENTICATION_PREPARATION.md` | Auth fully implemented |
| `po-discovery/04_API_CATALOG.md` (auth section) | Auth added in migration 0025 |
| `PLATFORM-HANDOFF-2026.md` portfolio section | Superseded by IMPLEMENTATION_SUMMARY |
| `docs/AI/09_HANDOVER/DOCUMENT_INVENTORY.md` | May lag new ADRs 029-031 |

---

## 5. Dead / Legacy Code

| Code | Status | Evidence |
|------|--------|----------|
| `app/models/research_report.py` | **Dead** — no repository/service | Legacy from initial schema |
| `app/api/v1/research.py` | **Deprecated** — still mounted | Tag `research-deprecated` |
| `app/args/plugins/*_stub.py` | **Unused in prod** | Registry uses real plugins |
| `app/services/__init__.py` docstring | **Stale** — "placeholders" | Services fully implemented |
| `app/execution/adapters/zerodha_kite.py` | **Stub** — not dead, intentional | Returns not_implemented |

---

## 6. Implementation Ahead of Documentation

| Feature | Code | Docs lag |
|---------|------|----------|
| Auth + multi-tenant foundation | migration 0025 | API catalog, AUTHENTICATION_PREPARATION |
| Unified execution | migration 0026, ADR-031 | RTM still says placeholder |
| Pilot command center | 10 API routes | API catalog missing |
| Frontend investor app | 8 screens + auth | ARCHITECTURE_REPORT placeholders |
| Recommendation engine P1-P2 | Full engine | Maturity scorecard 25% |

---

## 7. Documentation Ahead of Implementation

| Feature | Docs | Code gap |
|---------|------|----------|
| Risk controls AC-RISK | PRD 20 | No implementation |
| Live investing S1+ | ADR-030, PRD 18 | Zerodha stub only |
| Emergency stop | PRD 20, runbooks | No API |
| Approval CSV export | AC-HITL-02 | No endpoint |
| Trust dashboard vision | PRD 17 | Partial trust card only |
| Frontend /exits, /analytics | SCREEN_SPEC | Routes missing |
| HIGH_CONCERN soft-block live | AC-HITL-L03 | Not in execution |
| E2E pilot tests | PILOT_READINESS | Not in repo |

---

## Drift Severity Summary

| Category | Items | P0 | P1 | P2 |
|----------|-------|----|----|-----|
| Architecture drift | 10 | 2 | 5 | 3 |
| Documentation drift | 11 | 1 | 4 | 6 |
| Dead docs | 4 | — | — | 4 |
| Dead code | 3 | — | 1 | 2 |
| Docs ahead of code | 8 | 2 | 4 | 2 |
| Code ahead of docs | 5 | — | 3 | 2 |

---

*This report should be used to prioritize documentation refresh in Track DOC-01.*
