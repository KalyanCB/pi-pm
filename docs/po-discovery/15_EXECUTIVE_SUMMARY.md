# Executive Summary — Pi-PM Product Discovery

**Audience:** Board, founders, incoming PO  
**Date:** 2026-06-05  
**Evidence base:** Code scan + 312 pytest tests + handover docs

---

## What Pi-PM is

Pi-PM (Personal Intelligence Portfolio Manager) is a **FastAPI + PostgreSQL** platform for **deterministic** ranking and forward-return validation of Indian NSE equities, with research analytics and an **ARGS** (AI Research Governance System) layer that runs LLM committees over structured investment review packets. It is **not** a live trading or mobile consumer app today.

**Non-negotiable (code-enforced design):** LLMs do not rank securities, size positions, approve trades, or override risk. See [`docs/AI/01_PRODUCT/PRD.md`](../AI/01_PRODUCT/PRD.md) G8.

---

## Maturity at a glance

| Dimension | Status | Score (see scorecard) |
|-----------|--------|----------------------|
| Core ranking + validation pipeline | Production-ready, frozen math | **88 / 100** |
| Daily NIFTY 500 batch ops | Production orchestrator + API | **82 / 100** |
| Research analytics (factor IC, exit, regime) | Production APIs, read-only | **78 / 100** |
| ARGS governance (5 committees + CRO) | Production; Phase 2 independence ~79% | **75 / 100** |
| Rank **ordering** calibration | Research only; bucket alpha partial | **45 / 100** |
| Portfolio / paper trading | DB schema only; no services | **12 / 100** |
| Mobile / consumer UX | No app codebase | **8 / 100** |
| CI / automated E2E | Local pytest only | **35 / 100** |

Full scorecard: [PRODUCT_MATURITY_SCORECARD.md](./PRODUCT_MATURITY_SCORECARD.md).

---

## What works (verified)

1. **Two ranking strategies** — `momentum_v1` and `breakout_v1` registered in `app/ranking/registry.py`; deterministic golden tests exist.
2. **Forward-return validation** — IC, deciles, regime splits; `insufficient_data` when forward bars missing (`app/validation/constants.py`).
3. **Daily batch** — Ingest → rank → validate → regime → factor IC → research intelligence → exit research (`app/services/daily_batch_service.py`).
4. **Outcome attribution** — Top-20 buckets show selective alpha vs benchmark; verdict `partial` ([`docs/outcome-attribution-report.md`](../outcome-attribution-report.md)).
5. **ARGS** — Investment review packets, 5 committees (TARC, FRC, QRC, NRCC, RC) + CRO aggregator, lineage API (`app/args/`).
6. **SEE v2 + SQE** — Setup evidence and stock quality evidence enrich packets; SQE does not change QRC default path (`args_qrc_use_sqe: bool = False` in `app/core/config.py`).

---

## Critical gaps (PO decisions needed)

| Gap | Impact | Evidence |
|-----|--------|----------|
| Rank ordering not monotonic | Top-5 may underperform ranks 6–20 | [`docs/ranking-calibration-root-cause.md`](../ranking-calibration-root-cause.md), `app/ranking_research/` |
| Validation tail pending | Recent as-of dates lack forward metrics | [`docs/dailyruns/04-jun-2026/03-validation.md`](../dailyruns/04-jun-2026/03-validation.md) |
| No buy/hold/exit product signals | Rankings ≠ recommendations; exit research is analytics | `app/api/v1/exit_analytics.py` (reports only) |
| Portfolio engine stub | Tables exist; `app/portfolio/` empty | `app/models/paper_trade.py`, `app/portfolio/__init__.py` |
| No mobile app | APIs only; no React Native / Flutter in repo | Repo scan (no matches) |
| No CI pipeline | Merge risk | [`docs/AI/09_TESTING/TEST_GAPS.md`](../AI/09_TESTING/TEST_GAPS.md) |

---

## Recommended near-term focus (P0)

1. **Operational:** Ingest forward bars; clear validation `insufficient_data` tail.
2. **Product:** PO sign-off criteria for ranking v2 / calibration promotion.
3. **Product:** PO sign-off on `ARGS_QRC_USE_SQE` (default stays `false` until approved).
4. **Engineering:** CI with `pytest` + Alembic head check.
5. **Branch:** Stabilize `feature/see-v2` → `main` (per [`docs/PLATFORM-HANDOFF-2026.md`](../PLATFORM-HANDOFF-2026.md)).

Detail: [13_ROADMAP_RECOMMENDATION.md](./13_ROADMAP_RECOMMENDATION.md).

---

## Investment thesis for continuing build

Pi-PM has a **credible deterministic core** (rank + validate + trace) and a **differentiated governance layer** (ARGS committees with evidence isolation). The platform is **research- and ops-ready** for NIFTY 500 daily workflows. **Capital deployment features** (portfolio construction, paper trading, mobile UX, explicit recommendation lifecycle) are **not implemented** — by design or deferral — and represent the largest product delta from a consumer portfolio manager.

---

## Document map

Start at [INDEX.md](./INDEX.md) for full discovery pack navigation.
