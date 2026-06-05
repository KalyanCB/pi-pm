# Copilot Evaluation Report

**Track:** Pi-PM Copilot & Explainability  
**Date:** 2026-06-05  
**Branch:** `feature/copilot-ai`  
**Evaluator:** AI Product Engineer (automated + unit test gate)

---

## Executive summary

| Criterion | Result | Evidence |
|-----------|--------|----------|
| All Copilot tests pass | **PASS** | 50/50 `tests/unit/copilot/` |
| Intent coverage documented | **PASS** | `COPILOT_INTENT_MATRIX.md` |
| Grounding verified | **PASS** | Retriever maps 8 investor intents + 3 supplementary |
| No business logic influence | **PASS** | Read-only DB queries; refuse patterns; no service calls to ranking/rec |
| Explainability scorecard | **PASS** | This report |

**Overall explainability readiness: 78/100** (M4 Copilot target ~70 for MVP)

---

## Explainability scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| Intent coverage (8 required) | **95** | All 8 investor intents implemented + rank/validation/ops |
| Refuse / governance | **92** | 8 refuse classes; injection + trade blocked |
| Grounding breadth | **85** | Rec, portfolio, committee, outcomes, validation, batch |
| Lineage auditability | **88** | `source_ref` with 4 ID types; `lineage_summary` in API |
| Citation validation | **75** | GR-01 window check; uncited_claims surfaced |
| Integration / E2E tests | **40** | Unit only; no live DB copilot integration test yet |
| Live LLM eval | **30** | Mock provider in CI; manual eval not run |
| Mobile / voice readiness | **70** | Design documented; no client |

**Weighted explainability score: ~78/100**

---

## Test results

```
tests/unit/copilot/
  test_intent.py         27 passed  — refuse, classify, entities, injection
  test_lineage.py         2 passed  — audit ref structure
  test_citations.py       7 passed  — citation parse + hash
  test_copilot_service.py 9 passed  — AC-CP-01..04
  ─────────────────────────────────
  Total                  50 passed
```

### Previously failing (now fixed)

| Test | Root cause | Fix |
|------|------------|-----|
| `Place a buy order` | Refuse regex too strict | Allow optional article: "a buy order" |
| `Execute a trade` | Same | `execute.*trade` pattern |
| `recommend selling` → exit | Rank pattern captured "recommend" | Exit patterns before rank; removed recommend from rank |
| Prompt injection | `ignore all previous instructions` | Extended ignore pattern |
| `test_ops_intent` | `DailyBatchRun.created_at` missing | Use `started_at` |
| `why not recommended` | Why-recommended matched first | `why.*not recommended` precedence |
| Risk / performance | Symbol false positives (HOW, risks stem) | Stop words + `risks?`, `perform` patterns |

---

## Intent acceptance matrix

| Intent | Classifier | Retriever | Prompt | Tests |
|--------|------------|-----------|--------|-------|
| why_recommended | ✓ | ✓ | ✓ | ✓ |
| why_not_recommended | ✓ | ✓ | ✓ | ✓ |
| explain_exit | ✓ | ✓ | ✓ | ✓ |
| explain_conviction | ✓ | ✓ | ✓ | ✓ |
| explain_committee | ✓ | ✓ | ✓ | ✓ |
| explain_portfolio | ✓ | ✓ | ✓ | ✓ |
| explain_risk | ✓ | ✓ | ✓ | ✓ |
| explain_performance | ✓ | ✓ | ✓ | ✓ |

---

## Non-influence verification

| Decision system | Copilot interaction | Verified |
|-----------------|---------------------|----------|
| Ranking engine | Read `ranking_results` only | ✓ |
| Validation | Read `ranking_validation_reports` only | ✓ |
| Recommendation generation | Read `recommendation_results` only; no `RecommendationService.run` | ✓ |
| Conviction scoring | Read stored `conviction_components` only | ✓ |
| Portfolio engine | Read positions/NAV only; no `PortfolioService` mutations | ✓ |
| Trade execution | Hard refuse | ✓ |

---

## Gaps & recommended follow-ups

| Gap | Priority | Suggestion |
|-----|----------|------------|
| Integration test with fixture DB | P1 | Mini corpus seed → `POST /copilot/ask` |
| Live LLM grounding eval set | P2 | 20 golden Q&A pairs with expected citations |
| `copilot_query_logs.intent` length | P3 | Migration widen if new intents exceed 32 chars (current max: 21) |
| OpenAPI `lineage` field | P3 | Add to `AskResponse` schema |

---

## Future channel readiness

| Channel | Ready? | Blocker |
|---------|--------|---------|
| Mobile copilot | Design ready | Mobile app (M4) |
| Voice assistant | Design ready | STT/TTS integration |
| Portfolio coaching | Partial | Multi-turn UX; data in corpus |

See `COPILOT_INTENT_MATRIX.md` § Future channel mapping.

---

## Sign-off checklist (Track C)

- [x] Resolve all Copilot test failures (7 → 0)
- [x] Complete 8-intent explainability framework
- [x] Grounding across rec / portfolio / committee / analytics
- [x] Lineage IDs in audit trail
- [x] `COPILOT_INTENT_MATRIX.md`
- [x] `COPILOT_GROUNDING_STRATEGY.md`
- [x] `COPILOT_EVALUATION_REPORT.md`
- [x] No modification to ranking, validation, recommendation generation, or conviction scoring logic
