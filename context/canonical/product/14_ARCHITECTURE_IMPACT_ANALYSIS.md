# Architecture Impact Analysis — Phase 2

**Version:** Phase 2.1 (PO sign-off 2026-06-04)  
**Date:** 2026-06-05  
**Scope:** Reuse vs new per feature; DB, API, test, ops impact. **No implementation** in this pack.

**Baseline:** [02_ARCHITECTURE_CURRENT_STATE.md](../po-discovery/02_ARCHITECTURE_CURRENT_STATE.md), [PRODUCT_MATURITY_SCORECARD.md](../po-discovery/PRODUCT_MATURITY_SCORECARD.md)

---

## 1. Summary matrix

| Feature | Reuse | New build | Risk |
|---------|-------|-----------|------|
| Recommendation Engine | ranking, validation, regime, exit analytics | `app/recommendation/`, tables, APIs, batch phase | Medium — pipeline insert |
| Conviction | validation metrics, factor IC, regime, exit health — **no ARGS** | `conviction` module, golden tests | Low |
| RecommendationOutcome | paper_trade fills, prices | `recommendation_outcomes`, performance APIs | Medium — P3 |
| Why-not-recommended | RE rule evaluation | `reason_codes`, `why-not` API | Low — P2 |
| Lifecycle / approvals | paper_trade idempotency pattern | `recommendation_approvals`, state machine | Low |
| Portfolio | `portfolio_position` ORM, regime_policy | `app/portfolio/` services, APIs | Medium |
| Paper trading | `paper_trade` ORM, `TradeStatus` | `app/execution/` or paper service, routers | Medium |
| Exit monitors | `workspace_exit_research`, ranking daily | scheduler job, position link | Medium |
| ARGS advisory | full `app/args/` graph, packet builder | prompt/schema extensions | Medium — LLM boundary |
| HITL | — | approval APIs, broker port | Low |
| Auth | FastAPI middleware patterns | JWT, user table | High — greenfield |
| Mobile | 60+ existing read APIs | DTO layer, new portfolio/rec APIs | High — client new |
| Copilot | LLM port, `llm_execution_records` | retriever, `copilot_query_logs` | Medium |

---

## 2. Pipeline change

### Current (batch)

`INGEST → RANKINGS → VALIDATION → REGIME → FACTOR_IC → RESEARCH_INTELLIGENCE → EXIT_RESEARCH`

Source: [`daily_batch_service.py`](../../app/services/daily_batch_service.py)

### Target

Insert after VALIDATION:

`→ RECOMMENDATION → (optional ARGS trigger)`

Optional post-close:

`→ PORTFOLIO_MARK → EXIT_MONITOR`

**Impact:** Batch planner weights, artifact types, daily run docs under `docs/dailyruns/`.

---

## 3. Database impact

| Change | Type | Migration |
|--------|------|-----------|
| `recommendation_runs`, `recommendation_results`, `recommendation_approvals`, `recommendation_configs` | New tables | Alembic post `20260609_0018` (P1) |
| `recommendation_outcomes` | New table | P1 schema; P3 population job |
| `paper_trades.recommendation_result_id` | FK add | M2 |
| `watchlist_items`, `users` (auth) | New tables | M3–M4 |
| `copilot_query_logs` | New table | M4 |
| Ranking / validation tables | **Frozen** — no alter without PO | — |

**Reuse unchanged:** `ranking_runs`, `ranking_results`, `ranking_validation_reports`, ARGS tables, exit research tables.

---

## 4. API impact

| Router group | Change |
|--------------|--------|
| `/api/v1/recommendations/*` | **New** module |
| `/api/v1/recommendations/why-not/{symbol}` | **New** — rejection codes ([16_WHY_NOT](../product/16_WHY_NOT_RECOMMENDED_FRAMEWORK.md)) |
| `/api/v1/recommendations/performance/*` | **New** P3 — read-only analytics |
| `/api/v1/portfolio/*`, `/paper-trades/*` | **New** |
| `/api/v1/approvals/*` | **New** (may alias recommendations) |
| `/api/v1/research/*` | Extend request/response DTOs |
| `/api/v1/copilot/*` | **New** M4 |
| Existing rankings, validation, analytics | Read-only reuse |

**OpenAPI:** Regenerate; contract test P1.5 ([po-discovery 13](../po-discovery/13_ROADMAP_RECOMMENDATION.md)).

---

## 5. Domain packages

| Package | Today | Phase 2 |
|---------|-------|---------|
| `app/ranking/` | Production | **No change** (PO gate for v2) |
| `app/validation/` | Production | **No change** |
| `app/recommendation/` | — | **New** |
| `app/portfolio/` | Stub docstring | **New** services |
| `app/execution/` | Stub | Paper/broker adapters |
| `app/args/` | Production | Packet builder + prompt extensions |
| `app/workspace_exit_research/` | Analytics | Consumed by exit monitor — no math change |
| `app/ranking_research/` | Research | Optional promotion into conviction |

---

## 6. Test impact

| Area | Current tests | Add (estimate) |
|------|---------------|----------------|
| Recommendation | 0 | 25 unit + 10 integration |
| Conviction | 0 | 15 golden unit (five factors; no committee fixture) |
| RecommendationOutcome | 0 | 12 unit + 8 integration |
| Why-not API | 0 | 8 contract tests |
| Portfolio / paper | 0 | 20 integration |
| Exit monitor | 25 (research) | 10 integration |
| ARGS advisory | 63+ unit | 5 schema regression |
| Auth | 0 | 10 |
| **Total** | 312 collected | +~95 (target ~400) |

Align [07_TEST_COVERAGE](../po-discovery/07_TEST_COVERAGE_ASSESSMENT.md).

---

## 7. Ops impact

| Process | Change |
|---------|--------|
| Daily batch runbook | New phases REC, PORT_MARK, EXIT_MONITOR |
| `scripts/run_daily_nifty500_batch.py` | Phase flags |
| ARGS `run_args_top20.py` | Input from recommendation queue not raw rank |
| Monitoring | Alert on failed recommendation run |
| CI | P0 pytest required |

---

## 8. LLM / ARGS boundary (critical)

| Component | LLM? |
|-----------|------|
| Ranking | **No** |
| Validation | **No** |
| Conviction | **No** |
| Recommendation rules | **No** |
| Committees + CRO | **Yes** — research/advisory only |
| Copilot | **Yes** — grounded |

**Violation test:** Any PR touching `app/ranking/` or conviction with OpenAI import = block.

---

## 9. Technical debt interactions

| Debt ID | Phase 2 interaction |
|---------|----------------------|
| TD-C01 No CI | Blocks safe M1 delivery — P0 |
| TD-H03 No batch E2E | Address M1/M2 |
| Synthetic portfolio_context | Closed M2 |
| Rank calibration | Gates conviction HIGH band M1 |

[08_TECHNICAL_DEBT_REGISTER.md](../po-discovery/08_TECHNICAL_DEBT_REGISTER.md)

---

## 10. Effort sizing (T-shirt — engineering estimate placeholder)

| Milestone | Size |
|-----------|------|
| M1 | L |
| M2 | L |
| M3 | M |
| M4 | L (client-heavy) |

---

## 11. References

- [02_ARCHITECTURE_CURRENT_STATE.md](../po-discovery/02_ARCHITECTURE_CURRENT_STATE.md)
- [04_API_CATALOG.md](../po-discovery/04_API_CATALOG.md)
- [SERVICE_MAP.md](../AI/02_ARCHITECTURE/SERVICE_MAP.md)
- [ADR-021-Recommendation-Platform-Architecture.md](../decisions/ADR-021-Recommendation-Platform-Architecture.md)
- [PO_SIGNOFF_2026_06_04.md](../po/PO_SIGNOFF_2026_06_04.md)
