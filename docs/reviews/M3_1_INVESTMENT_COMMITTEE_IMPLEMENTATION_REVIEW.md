# M3.1 Investment Committee Evolution — Principal Architect + PO Implementation Review

**Date:** 2026-06-05  
**Reviewer role:** Principal Architect + Product Owner  
**Scope:** M3.1 implementation in `feature/see-v2`  
**Evidence base:** Repository code only — no assumptions

---

## Executive Summary

The M3.1 implementation correctly executes the core mandate: elevate ARGS to an investor-facing Investment Committee as a **presentation-layer enhancement** without rewriting internals. The enum, aggregation logic, HIGH_CONCERN escalation, migration, and tests are well-implemented.

**However, two critical gaps exist:**

1. **`advisory_action` and `cro_advisory_action` are never written to the database** — the fields exist in the ORM model and migration but `_persist_reviews()` and `_persist_cro_and_reports()` in `args_research_run_service.py` do not populate them.

2. **`committee_advisory` packet block is always empty** — the packet builder injects a static placeholder (`cro_advisory_action: null`) and no code ever populates it with real committee data.

These mean HIGH_CONCERN escalation logic is implemented and tested in isolation but **never executes in a real research run**. The feature is inert in production.

**Merge Recommendation: APPROVE WITH MAJOR CHANGES**

---

## Architecture Compliance

### Internal architecture preserved ✅

- `app/args/` plugins (TARC, FRC, QRC, NRCC, RC, CRO): **unchanged**
- `CommitteeResearchLabel` enum: **unchanged** (`app/workspace_args/constants.py:15-20`)
- `DailyBatchPhase.RESEARCH`: **N/A — see Finding C-1 below**
- `app/workspace_args/`, `app/args/graph/workflow.py`: additive changes only

### Deterministic boundaries preserved ✅

- Ranking engine: untouched
- Validation engine: untouched
- Conviction formula: untouched
- Recommendation engine: untouched
- LLM routing: untouched

---

## ADR-021 Compliance

**Pipeline position:** `Ranking → Validation → Recommendation Engine → ARGS → Human → Portfolio`

**Status: ✅ Compliant**

- `committee_advisory` block is injected **after** the `recommendation` block in `investment_review_packet_builder.py:231`
- R-ARGS-04 is preserved in structure: `recommendation` block is set independently and not overwritten by committee code
- No code path allows committee output to mutate `recommendation.action`, `conviction_score`, or `conviction_band`

**Evidence:** `app/args/builders/investment_review_packet_builder.py:208-244`

---

## ADR-022 Compliance

**Recommendation Performance:** Advisory analytics are observational only.

**Status: ✅ Compliant**

- `CommitteeAdvisoryAction` values are `String(32)` stored on `committee_reviews` and `cro_reviews` — no computation feeds back into the recommendation engine
- Committee analytics in `recommendation_analytics_service.py` use `committee_advisory` from `recommendation_outcomes` (denormalised field) — read-only

**Gap:** `committee_advisory` column on `recommendation_outcomes` is never populated from the new advisory fields. The `recommendation_outcomes` table stores `committee_advisory` as a string set at outcome creation time — the new `CommitteeAdvisoryAction` is not wired to it.

---

## ADR-023 Compliance

### Requirement 1 — CommitteeAdvisoryAction enum ✅

All five values present: `APPROVE / WATCH / REJECT / EXIT_APPROVED / HIGH_CONCERN`  
**Evidence:** `app/workspace_args/constants.py:30-40`

### Requirement 2 — Additive DB migration ✅

Migration `20260607_0021` adds:
- `committee_reviews.advisory_action varchar(32)` 
- `committee_reviews.high_concern bool`
- `committee_reviews.high_concern_reason text`
- `cro_reviews.cro_advisory_action varchar(32)`
- `cro_reviews.investment_committee_summary text`

Chain: `0019 → 0020 → 0021` ✅ correctly linked

### Requirement 3 — HIGH_CONCERN escalation ✅ (logic) ❌ (wired)

Logic in `aggregate_cro_advisory()` is correct:
```python
if CommitteeAdvisoryAction.HIGH_CONCERN in actions:
    return CommitteeAdvisoryAction.HIGH_CONCERN
```
**Evidence:** `app/workspace_args/constants.py:56-90`

**BUT:** This function is called in `workflow.py:173` and the result stored in `cro_outputs[row]["cro_advisory_action"]`. However `_persist_cro_and_reports()` in `args_research_run_service.py:272-363` **never reads `cro_advisory_action` from the row** and never writes it to `CroReview`. The escalation logic runs in the workflow but its output is discarded.

### Requirement 4 — DailyBatchPhase.RESEARCH preserved ⚠️ INACCURATE ADR

ADR-023 states: _"DailyBatchPhase.RESEARCH internal name unchanged"_

**Finding:** `DailyBatchPhase.RESEARCH` **does not exist** in the codebase and **never did**. Inspection of `app/core/constants.py` and `git show HEAD~1:app/core/constants.py` both confirm the enum has no `RESEARCH` member. The ARGS run is triggered via `POST /research/run` separately from the daily batch — it is not a batch phase.

This is an ADR documentation error, not an implementation violation. The ADR makes a promise about preserving something that was never there.

### Requirement 5 — Advisory block in packets ⚠️ PLACEHOLDER ONLY

`payload["committee_advisory"]` is injected in `investment_review_packet_builder.py:231-244` but with hardcoded null values:
```python
"cro_advisory_action": None,
"high_concern": False,
"committee_actions": {},
```
No code path populates this block with real committee results.

### Requirement 6 — Investor-facing display names ✅

`COMMITTEE_DISPLAY_NAMES` dict present in `app/workspace_args/constants.py:92-100`  
`/investment-committee/committees/members` endpoint returns them.

### Requirement 7 — Backward compatibility ✅

`CommitteeResearchLabel` unchanged. Old `/research/*` routes registered with tag `research-deprecated` in `app/api/router.py:40`. No breaking changes.

---

## Findings

### CRITICAL

#### C-1 — `advisory_action` never persisted to `committee_reviews`

**File:** `app/services/args_research_run_service.py:240-260`

`_persist_reviews()` creates `CommitteeReview` objects but does not set `advisory_action`, `high_concern`, or `high_concern_reason`. The workflow produces these values in `_review_output_dict()` (`workflow.py:235-249`) and stores them in `row["output"]`, but `_persist_reviews()` does not read them:

```python
review = CommitteeReview(
    ...
    extensions=output.get("extensions"),
    # advisory_action=output.get("advisory_action"),  ← MISSING
    # high_concern=output.get("high_concern", False), ← MISSING
    # high_concern_reason=output.get("high_concern_reason"), ← MISSING
)
```

**Impact:** All `committee_reviews.advisory_action` values will be `NULL` in production. HIGH_CONCERN escalation data is lost.

#### C-2 — `cro_advisory_action` never persisted to `cro_reviews`

**File:** `app/services/args_research_run_service.py:307-320`

`_persist_cro_and_reports()` creates `CroReview` without `cro_advisory_action` or `investment_committee_summary`:

```python
cro = CroReview(
    ...
    confidence=governance_confidence,
    # cro_advisory_action=row.get("cro_advisory_action"),     ← MISSING
    # investment_committee_summary=agg.get("summary"),        ← MISSING
)
```

**Impact:** `cro_reviews.cro_advisory_action` is always `NULL`. The CRO advisory output is discarded.

#### C-3 — `committee_advisory` packet block never populated with real data

**File:** `app/args/builders/investment_review_packet_builder.py:228-244`

The block is injected at packet **build time** (before committees run) with static placeholder values. After committees run, no code updates `payload["committee_advisory"]` with actual committee results. The packet hash is also computed after this block (`compute_packet_hash(payload)` at line 229) — meaning even if the block were updated post-run, it would not match the stored hash.

**Impact:** Every packet served to the mobile app or ARGS explainability endpoint will show `committee_advisory.cro_advisory_action: null` regardless of what the committees decided.

---

### HIGH

#### H-1 — `investment_committee.py` calls methods that don't exist on the service

**File:** `app/api/v1/investment_committee.py`

The following calls reference methods not present on `ArgsResearchRunService`:
- `service.start_run()` — actual method is `service.run()`
- `service.get_packets()` — actual method is `service.get_packet_for_run()`
- `service.get_governance_report()` — no such method exists

**Evidence:** `app/services/args_research_run_service.py:93,216` (actual method names)

**Impact:** All Investment Committee API endpoints except `GET /committees/members` and `GET /{review_id}/explain` will raise `AttributeError` at runtime. The router imports successfully but endpoints fail on first call.

#### H-2 — HIGH_CONCERN is unreachable via current label mapping

**File:** `app/workspace_args/constants.py:47-51`

`_LABEL_TO_ADVISORY` maps only `supportive→APPROVE`, `neutral→WATCH`, `cautious→REJECT`. `HIGH_CONCERN` is in `CommitteeAdvisoryAction` but has no path from `CommitteeResearchLabel`. LLM plugins emit `research_label` (a `CommitteeResearchLabel` value). Since no plugin emits `HIGH_CONCERN` as a research label, and `label_to_advisory_action()` falls back to `WATCH` for unknowns, `HIGH_CONCERN` **can never be set by the current system**.

**Evidence:** `app/args/plugins/` — zero occurrences of `HIGH_CONCERN` (`grep -rn "HIGH_CONCERN" app/args/plugins/` returns empty)

**Impact:** The escalation logic is correct but functionally dead. Phase 3 prompt updates (noted in ADR-023 §Consequences) are required before HIGH_CONCERN can be raised.

#### H-3 — `DailyBatchPhase.RESEARCH` referenced in ADR-023 but does not exist

**File:** `docs/architecture/ADR-023-Investment-Committee-Evolution.md:27,56,121`

The ADR states _"Preserve DailyBatchPhase.RESEARCH"_ and _"DailyBatchPhase.RESEARCH internal name unchanged"_. This phase was never part of the enum — the ADR makes a false promise.

**Impact:** Documentation drift. Any engineer reading ADR-023 will look for this phase and not find it, creating confusion.

---

### MEDIUM

#### M-1 — `committee_advisory` in `recommendation_outcomes` not wired to new enum

**File:** `app/models/recommendation.py:149`, `app/db/repositories/recommendation_repository.py`

`recommendation_outcomes.committee_advisory` is a `String(32)` field populated at outcome creation. It is never updated with `CommitteeAdvisoryAction` values from the new system. The P3 analytics (`recommendation_analytics_service.py`) read this field for committee effectiveness metrics — they will always see `null` until wired.

#### M-2 — Deprecation is tag-only, no HTTP header or OpenAPI marker

**File:** `app/api/router.py:40`

Old `/research/*` routes are tagged `research-deprecated` in OpenAPI but no `Deprecated: true` OpenAPI extension, `X-Deprecated` HTTP header, or `deprecated=True` on individual endpoints is set. FastAPI supports `deprecated=True` per route.

#### M-3 — `EXIT_APPROVED` advisory action unreachable in current aggregation

`EXIT_APPROVED` is lowest priority in `aggregate_cro_advisory()` tiebreak logic and cannot be emitted by any label mapping. This is acceptable for Phase 1 of M3.1 but needs tracking.

#### M-4 — `INTERNAL_TO_EXTERNAL_TERMS` dict is unused

**File:** `app/workspace_args/constants.py:101-108`

`INTERNAL_TO_EXTERNAL_TERMS` is declared but not imported or used anywhere in the codebase.

---

### LOW

#### L-1 — No `get_governance_report()` on service, old endpoint uses different path

**File:** `app/api/v1/research.py` — no `governance_report` endpoint exists on the old router. The new `/{review_id}/report` endpoint maps to a non-existent service method (see H-1).

#### L-2 — `high_concern_reason` in ORM model but never set by any code path

No code path currently sets `high_concern_reason`. It is `nullable=True` so no runtime error, but it will always be `NULL`.

#### L-3 — Missing `__all__` export for new constants

`CommitteeAdvisoryAction`, `aggregate_cro_advisory`, `label_to_advisory_action` are not added to any `__all__` list. Minor discoverability issue.

---

## Missing Tests

| Test | Priority | Evidence of gap |
|------|----------|----------------|
| `_persist_reviews` sets `advisory_action` on CommitteeReview | Critical | `args_research_run_service.py:240` — field not set |
| `_persist_cro_and_reports` sets `cro_advisory_action` on CroReview | Critical | `args_research_run_service.py:307` — field not set |
| `committee_advisory` packet block populated with real data after workflow | Critical | `investment_review_packet_builder.py:231` — static placeholder |
| Investment Committee API endpoints return correct data | High | `investment_committee.py` — methods don't exist |
| `GET /investment-committee/{id}/report` returns governance report | High | No service method |
| R-ARGS-04: committee run does not mutate `recommendation.action` in integration | High | Only type-level test exists |
| HIGH_CONCERN escalation in full workflow integration (not unit) | Medium | Only unit test of `aggregate_cro_advisory()` |
| `EXIT_APPROVED` advisory via direct set (not label mapping) | Low | No path exists |

---

## Documentation Gaps

| Document | Gap |
|----------|-----|
| `ADR-023` | Claims `DailyBatchPhase.RESEARCH` exists and must be preserved — it does not exist |
| `ADR-023` | HIGH_CONCERN described as available "now" but requires Phase 3 prompt updates before reachable |
| `08_AI_INVESTMENT_COMMITTEE_PRD.md` | Not updated to reflect M3.1 implementation state and gaps |
| `HANDOFF.md` | No mention of Investment Committee evolution or deprecated `/research/*` routes |
| `docs/AI/12_HANDOVER/PROJECT_STATE_2026_06_04.md` | Not updated with M3.1 completion |

---

## Technical Debt

| Item | Risk | Suggested timeline |
|------|------|--------------------|
| Phase 3 LLM prompt updates to emit HIGH_CONCERN | HIGH — escalation is dead without this | M3.2 |
| Wire `advisory_action` in `_persist_reviews()` | Critical functional gap | Immediate fix |
| Wire `cro_advisory_action` in `_persist_cro_and_reports()` | Critical functional gap | Immediate fix |
| Populate `committee_advisory` packet block post-workflow | Critical for packet consumers | Immediate fix |
| Fix investment_committee.py method names | Critical for API usability | Immediate fix |
| Add `deprecated=True` to `/research/*` endpoints | Medium — API hygiene | Before M4 |
| Remove `INTERNAL_TO_EXTERNAL_TERMS` unused dict or wire it | Low | M4 cleanup |

---

## Recommended Fixes (Priority Order)

### Fix 1 — Wire advisory fields in `_persist_reviews()`

```python
# app/services/args_research_run_service.py ~line 253
review = CommitteeReview(
    ...
    advisory_action=output.get("advisory_action"),
    high_concern=output.get("high_concern", False),
    high_concern_reason=output.get("high_concern_reason"),
)
```

### Fix 2 — Wire advisory fields in `_persist_cro_and_reports()`

```python
# app/services/args_research_run_service.py ~line 307
cro = CroReview(
    ...
    cro_advisory_action=row.get("cro_advisory_action"),
    investment_committee_summary=agg.get("summary"),
)
```

### Fix 3 — Fix `investment_committee.py` method names

```python
# start_committee_review: service.run() not service.start_run()
# get_committee_packets: service.get_packet_for_run() not service.get_packets()
# get_committee_report: needs new service method or map to governance_report_repo
```

### Fix 4 — Populate `committee_advisory` block after workflow

The packet builder runs before committees. The block needs to be updated in `_persist_cro_and_reports()` after CRO aggregation, using `packet.payload["committee_advisory"]` update + re-hash, or the block should be populated from stored DB values at read time (via a packet enricher).

### Fix 5 — Correct ADR-023

Remove references to `DailyBatchPhase.RESEARCH`. Replace with accurate statement: _"ARGS research runs are triggered via `POST /research/run` (external API call), not via a daily batch phase. The internal `DailyBatchPhase` enum does not include an ARGS phase and this remains unchanged."_

---

## Merge Recommendation

### **APPROVE WITH MAJOR CHANGES**

The architectural foundation is correct and well-designed:
- HIGH_CONCERN escalation logic is sound and tested
- Migration is additive and correctly chained
- Enum, display names, and backward compatibility are all correct
- ADR-023 documents the intent accurately (with one factual error)
- Internal architecture is fully preserved

However the four critical issues (C-1, C-2, C-3, H-1) mean the feature is **inert in production** — every API call returns null advisory actions and the committee_advisory packet block is always empty. These must be fixed before this branch can be used for any real Investment Committee functionality.

Fixes 1–4 above are mechanical changes with low regression risk. They can be implemented alongside the existing tests with no architectural impact.
