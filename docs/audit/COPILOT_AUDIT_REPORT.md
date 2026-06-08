# Copilot Audit Report

**Audit:** AUDIT-01  
**Date:** 2026-06-05  
**PRD:** `docs/product-next/10_AI_COPILOT_PRD.md`  
**Strategy:** `docs/copilot/COPILOT_GROUNDING_STRATEGY.md`, `COPILOT_INTENT_MATRIX.md`

---

## Executive Question

**Can Copilot influence investment decisions?**

### Verdict

| Influence type | Answer | Confidence |
|----------------|--------|------------|
| **System / automated decisions** | **NO** | High — no write path |
| **Human decisions (informational)** | **YES** | By design — explain-only |
| **Unattended pilot (auto-approve)** | **NO** | Copilot not in batch path |

---

## Architecture (Read-Only by Design)

```
POST /copilot/ask
  → classify() — rule-based intent + refuse patterns FIRST
  → retrieve() — DB SELECT only (app/copilot/retriever.py)
  → build_prompt() — hard rules injected
  → LLM complete
  → validate() — citation extraction
  → _log() → CopilotQueryLog — ONLY write operation
```

**Evidence:** `app/services/copilot_service.py` — no imports of RecommendationService, ExecutionService, or batch modules.

---

## Grounding Controls

| Rule | ID | Status | Evidence |
|------|-----|--------|----------|
| ≥1 citation per numeric claim | GR-01 | **IMPLEMENTED** | `citations.py` validation |
| Low confidence → honest retrieval | GR-02 | **IMPLEMENTED** | retriever confidence thresholds |
| Never invent conviction/action | GR-03 | **IMPLEMENTED** | `prompt_builder.py` hard rules |
| Committee labels verbatim | GR-04 | **IMPLEMENTED** | prompt instructions |
| Link to detail routes | GR-05 | **PARTIAL** | Backend refs; frontend citation nav unwired |
| Lineage IDs in answers | GR-06 | **IMPLEMENTED** | `lineage.py` |

### Prompt hard rules (`prompt_builder.py:21-27`)
- Never place orders
- Never invent scores
- Explain only from retrieved data
- Committee is advisory

---

## Refusal Patterns

**Pre-LLM refusal** in `app/copilot/intent.py:49-93`:

| Pattern category | Examples | Test |
|------------------|----------|------|
| Trade execution | "buy/sell for me" | `test_intent.py` (8 parametrized) |
| Stock picking | "what should I buy" | same |
| Override validation | "ignore validation" | same |
| Prompt injection | "ignore previous instructions" | `test_copilot_service.py` |
| Guarantees | "guaranteed return" | same |
| Position sizing | "how much to invest" | same |
| Prediction | "will this go up" | same |

Refused queries: `refused=True` in response; logged to `copilot_query_logs`; **LLM never called**.

---

## Intent Matrix (12 intents)

| Intent | Purpose | Can mutate state |
|--------|---------|------------------|
| why_recommended | Explain BUY/WATCH | No |
| why_not_recommended | Explain rejection | No |
| explain_exit | EXIT_APPROVED | No |
| explain_conviction | Score breakdown | No |
| explain_committee | ARGS output | No |
| explain_portfolio | Holdings | No |
| explain_risk | Risk flags | No |
| explain_performance | Outcomes | No |
| explain_rank | Ranking only | No |
| explain_validation | Validation status | No |
| ops_status | Batch health | No |
| refused | Trade/pick/override | No |

All intents are explain-only per `COPILOT_INTENT_MATRIX.md`.

---

## Acceptance Criteria Status

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| AC-CP-01 | Golden Q&A fixture citations | **PARTIAL** | Unit tests; no golden fixture suite |
| AC-CP-02 | Prompt injection refused | **IMPLEMENTED** | `test_copilot_service.py` |
| AC-CP-03 | 100% queries audited | **IMPLEMENTED** | `_log()` on every ask |
| AC-CP-04 | p95 latency <8s | **NOT_VERIFIED** | No load tests |
| AC-WNR-03 | Copilot cites API evidence only | **IMPLEMENTED** | retriever-bound; no invented reason codes |

---

## Read-Only Guarantees — Evidence Chain

1. **No mutation APIs** — Copilot module has zero write imports to recommendation/execution/batch
2. **Refused intents short-circuit** — `copilot_service.py:46-70`
3. **Retriever SELECT-only** — `retriever.py`
4. **Investment mutations require OwnerUser** on separate routes
5. **Pilot auto-approve uses `paper_pilot` actor**, not Copilot — `paper_pilot_ops.py:185`
6. **Batch pipeline does not invoke Copilot** — verified in `daily_batch_service.py`

---

## Residual Risks

| Risk | Severity | Mitigation status |
|------|----------|-------------------|
| Persuasive LLM explanations affecting human approvers | Low | By design in HITL mode |
| Uncited numerics flagged but not stripped | Medium | `uncited_claims` returned; answer not auto-redacted |
| Global data reads (no portfolio scope) | Medium | Security review item |
| Mock LLM fallback if API key missing | Low | `copilot_service.py:155-156` |
| Frontend citation deep links unwired | Low | UX gap, not security |

---

## Test Coverage

| File | Tests |
|------|-------|
| `test_copilot_service.py` | Refusal, logging, injection |
| `test_intent.py` | 8 refuse patterns |
| `test_citations.py` | Citation validation |
| `test_lineage.py` | Audit refs |

**Gap:** No `test_copilot_api.py` integration; no golden Q&A harness.

---

## Documented vs Actual

| Doc claim | Code reality |
|-----------|--------------|
| `COPILOT_EVALUATION_REPORT.md` — 78/100 readiness | **Aligned** — core safety implemented |
| `10_AI_COPILOT_PRD.md` — explain only | **Aligned** |
| Frontend citation-first (FP-05) | **Partial** — CitationPanel onPress missing |

---

## Conclusion

Copilot **cannot** change rankings, conviction, recommendations, approvals, portfolio positions, or execution orders. It operates as a **read-only explainer** over persisted engine output with pre-LLM refusal for action requests. The only database write is append-only audit logging.

---

*Evidence: `app/copilot/`, `app/services/copilot_service.py`, `app/api/v1/copilot.py`, `tests/unit/copilot/`.*
