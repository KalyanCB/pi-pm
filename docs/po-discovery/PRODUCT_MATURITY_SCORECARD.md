# Product Maturity Scorecard

**Date:** 2026-06-05  
**Scoring:** 0 = absent, 50 = partial/production with known gaps, 100 = production-complete with CI/E2E  
**Method:** Code paths, test counts, API surface, doc cross-check

---

## Summary table

| Area | Score | Tier | Primary evidence |
|------|-------|------|------------------|
| Ranking engine (deterministic) | **88** | Production | `app/ranking/`, 25 unit tests, golden hashes |
| Validation & forward returns | **85** | Production | `app/validation/`, 16 unit + 7 integration tests |
| Daily batch orchestration | **82** | Production | `app/services/daily_batch_service.py`, 1 planner test |
| Market data ingest | **80** | Production | `app/providers/yahoo/`, 7 service tests |
| Traceability / observability | **78** | Production | `app/api/v1/observability.py`, Sprint 7 models |
| Factor IC analytics | **78** | Production | `app/factor_analytics/`, 27 unit tests |
| Exit research analytics | **72** | Production (phased) | `app/workspace_exit_research/`, 25 unit tests |
| Regime policy (research) | **70** | Research API | `app/regime_policy/`, 14 unit tests |
| ARGS governance | **75** | Production | 63 unit + 5 integration args tests |
| SEE v2 setup evidence | **68** | Production | `app/stock_setup_evidence/`, 5 unit tests |
| Research intelligence | **65** | Production API | `app/api/v1/research_intelligence.py`, thin tests |
| Outcome attribution | **70** | Analytics only | `app/outcome_attribution/`, 11 unit tests |
| Ranking calibration research | **45** | Research only | `app/ranking_research/`, not in prod registry |
| Recommendation lifecycle | **25** | Missing | No buy/hold/exit product layer |
| Portfolio / paper trading | **12** | Stub | Models + migration only |
| Mobile / consumer UX | **8** | Absent | No mobile codebase |
| CI / release engineering | **35** | Gap | No `.github/workflows` pytest gate |
| Documentation | **85** | Strong | `docs/AI/`, PLATFORM-HANDOFF, dailyruns |

**Weighted product readiness (excluding mobile): ~72/100**  
**End-user investable product (incl. portfolio + mobile): ~38/100**

---

## Score detail by area

### Ranking engine — 88

| Criterion | Met? | Evidence |
|-----------|------|----------|
| Registered strategies | ✓ | `app/ranking/registry.py` — `momentum_v1`, `breakout_v1` |
| Deterministic replay | ✓ | `tests/unit/ranking/test_golden_ranking.py` |
| API + batch integration | ✓ | `app/api/v1/rankings.py`, daily batch phase |
| Rank ordering calibrated | ✗ | Research in `app/ranking_research/calibration.py` |

### Validation — 85

| Criterion | Met? | Evidence |
|-----------|------|----------|
| Horizons 5/10/20/60 | ✓ | `app/validation/` |
| Regime splits | ✓ | `app/validation/regimes.py` |
| Full-universe campaigns | ✓ | `app/models/full_universe_validation.py` |
| Recent tail complete | ✗ | `insufficient_data` per daily run log |

### ARGS governance — 75

| Criterion | Met? | Evidence |
|-----------|------|----------|
| 5 committees + CRO | ✓ | `app/workspace_args/constants.py` |
| Packet builder deterministic | ✓ | `app/args/builders/investment_review_packet_builder.py` |
| Phase 2 packet views | ✓ | `app/args/committee_packet_views.py` |
| Phase 3 independence | ✗ | Not in codebase |
| Live LLM in CI | ✗ | Mock provider only |

### Portfolio / paper trading — 12

| Criterion | Met? | Evidence |
|-----------|------|----------|
| DB tables | ✓ | `migrations/versions/20260530_0001_initial_schema.py` |
| ORM models | ✓ | `app/models/paper_trade.py`, `portfolio_position.py` |
| Services / API | ✗ | `app/portfolio/__init__.py` docstring only |
| Tests | ✗ | Zero tests |

### Mobile — 8

| Criterion | Met? | Evidence |
|-----------|------|----------|
| Mobile repo / screens | ✗ | No matches in repo |
| REST API for consumers | Partial | 60+ endpoints under `/api/v1` |
| Auth for mobile | ✗ | No auth middleware in `app/main.py` |

### CI — 35

| Criterion | Met? | Evidence |
|-----------|------|----------|
| Unit/integration tests | ✓ | 312 collected |
| CI workflow | ✗ | Per `docs/AI/09_TESTING/TEST_GAPS.md` |
| Daily batch E2E test | ✗ | Manual runbook only |

---

## Highest maturity (top 3)

1. **Ranking engine — 88** — Frozen, tested, wired to batch and API.
2. **Validation — 85** — Complete math; only tail freshness blocked.
3. **Documentation — 85** — AI handover package + PLATFORM-HANDOFF.

## Lowest maturity (top 3)

1. **Mobile / consumer UX — 8** — No client application.
2. **Portfolio / paper trading — 12** — Schema-only stub.
3. **Recommendation lifecycle — 25** — Rankings exist; no conviction/signal product.

---

## Discrepancies vs legacy docs

| Doc claim | Code truth | Notes |
|-----------|------------|-------|
| "312 passed" | ✓ Confirmed via collect | Run date 2026-06-05 |
| "Paper trading stub" | ✓ Confirmed | No services beyond models |
| "Committee Phase 3 not started" | ✓ No Phase 3 modules | Design docs only |

See individual gap analyses for detail.
