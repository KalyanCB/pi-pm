# AI Investment Committee (ARGS) — Phase 2 Product Requirements

**Version:** Phase 2.1 (PO sign-off 2026-06-04)  
**Date:** 2026-06-05  
**Code owner:** `app/args/`, `app/workspace_args/`  
**Baseline:** 5 committees + CRO, ~79% Phase 2 independence ([ARGS_DESIGN.md](../AI/03_DESIGN/ARGS_DESIGN.md))

---

## 1. Purpose

Evolve ARGS from **research governance** into an **AI Investment Committee** that advises the owner on recommendations **after** the deterministic Recommendation Engine — without violating PRD G8.

**Future advisory actions (not trade execution):** `APPROVE`, `WATCH`, `REJECT`, `EXIT_APPROVED` — mapped from committee consensus for **UI only**; they **cannot** override machine `REJECT` or force `BUY`.

---

## 2. Pipeline position (mandatory)

```
Ranking → Validation → Recommendation Engine → ARGS → Human → Portfolio
```

ARGS packets **must** include `recommendation` block ([01](../product/01_RECOMMENDATION_ENGINE_PRD.md)). Committees cite `recommendation:*` and `portfolio_context:*` evidence ([`rc.py`](../../app/args/plugins/rc.py), [`evidence_validator.py`](../../app/workspace_args/evidence_validator.py)).

---

## 3. Current vs future outputs

| Today (`CommitteeResearchLabel`) | Future advisory (`CommitteeAdvisoryAction`) |
|----------------------------------|---------------------------------------------|
| `supportive` | `APPROVE` (research alignment) |
| `neutral` | `WATCH` |
| `cautious` | `REJECT` (research concern) |
| — | `EXIT_APPROVED` (RC/CRO exit alignment only) |
| — | `HIGH_CONCERN` (see §3.1 — advisory only) |

**Storage:** New enum in product config; LLM prompts updated to emit advisory action **in addition to** legacy label for backward compatibility during transition.

**CRO:** Aggregates committee advisories into `cro_advisory_action` + narrative — still **no** trade fields ([`test_cro_no_trade_fields.py`](../../tests/unit/args/test_cro_no_trade_fields.py) pattern must hold).

### 3.1 `HIGH_CONCERN` (future enhancement — advisory only)

| Use when | Examples |
|----------|----------|
| Material governance risk | Fraud allegations, accounting restatement risk |
| Severe risk flags | Concentrated litigation, regulatory action |

| Rule | Detail |
|------|--------|
| Scope | UI badge + CRO narrative + copilot citation |
| Cannot | Override `recommendation.action`, `conviction_score`, or `conviction_band` |
| Human | Final decision maker — may still approve `BUY` with documented override |
| Measurement | Post-hoc in [16_RECOMMENDATION_PERFORMANCE_PRD.md](../product/16_RECOMMENDATION_PERFORMANCE_PRD.md) |

**Not in MVP:** Prompt/schema changes scheduled M3; design locked at PO sign-off.

---

## 4. Committee responsibilities (Phase 2)

| Committee | Code | Primary question | Evidence families |
|-----------|------|------------------|-------------------|
| Technical | TARC | Setup quality, trend | `stock_setup_evidence:*`, market |
| Fundamentals | FRC | Earnings quality, valuation | fundamentals refs |
| Quant | QRC | Validation, factors | `validation:*`, QRC brief (deterministic) |
| News | NRCC | Event risk | news refs |
| Risk | RC | Concentration, portfolio | `portfolio_context:*`, `risk:*`, `regime:*` |
| CRO | CRO | Synthesis | All committees — no rank primary evidence |

**QRC + SQE:** `ARGS_QRC_USE_SQE` remains **false** until PO A/B ([`app/core/config.py:79`](../../app/core/config.py)).

---

## 5. Non-negotiables (preserve)

| Rule | Enforcement |
|------|-------------|
| No LLM ranking | Committees never output rank order or composite_score changes |
| No position sizing | No `quantity`, `notional`, `weight` in LLM JSON schema |
| No trade approval | No `execute`, `broker_order` fields |
| No validation override | Cannot set `validation.status=completed` |
| No conviction influence | Cannot affect conviction or machine action ([02](../product/02_CONVICTION_SCORING_PRD.md)) |
| Evidence allowlist | [`committee_evidence_enforcement.py`](../../app/args/committee_evidence_enforcement.py) |

---

## 6. Advisory vs recommendation matrix

| Machine action | Committee may | Committee may not |
|----------------|---------------|-------------------|
| `BUY` | `APPROVE`, `WATCH`, `REJECT` advisory | Upgrade to bypass human |
| `WATCH` | `APPROVE` (research interest), `REJECT` | Force `BUY` |
| `REJECT` | Agree `REJECT` | `APPROVE` advisory that implies buy |
| `EXIT_APPROVED` | `EXIT_APPROVED`, `WATCH` (defer) | Cancel human requirement |
| `HOLD` | `WATCH`, `EXIT_APPROVED` advisory | Auto-sell |

**UI rule:** Show **both** machine action and `cro_advisory_action`; human decides when they disagree.

---

## 7. Phase 3 independence (product prep)

| Target | Metric |
|--------|--------|
| Effective independence | ≥ 85% (from ~79%) |
| Evidence overlap | 0% maintained |
| Packet views | Extend [`committee_packet_views.py`](../../app/args/committee_packet_views.py) |

Not started in code — design-only per po-discovery.

---

## 8. APIs (existing + proposed)

| Method | Path | Change |
|--------|------|--------|
| POST | `/api/v1/research/run` | Accept `recommendation_run_id` |
| GET | `/api/v1/research/{id}/packet` | Includes recommendation + advisory |
| GET | `/api/v1/research/{id}/lineage` | Link recommendation + committees |
| NEW | `/api/v1/research/{id}/advisory` | Slim mobile DTO |

---

## 9. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC-AIC-01 | ARGS runs only after recommendation_run exists for symbol |
| AC-AIC-02 | LLM output schema validated — no trade/sizing fields |
| AC-AIC-03 | `cro_advisory_action` disagrees with machine in ≥1 fixture test without crash |
| AC-AIC-04 | `portfolio_context.existing_position` truthful when portfolio live |
| AC-AIC-05 | Mobile explain text ≤ 2KB per symbol |

---

## 10. References

- [06_AI_AND_AGENT_INVENTORY.md](../po-discovery/06_AI_AND_AGENT_INVENTORY.md)
- [COMMITTEE_DESIGN.md](../AI/03_DESIGN/COMMITTEE_DESIGN.md)
- [GOVERNANCE_DESIGN.md](../AI/03_DESIGN/GOVERNANCE_DESIGN.md)
- [args-gap-analysis.md](../args-gap-analysis.md)
