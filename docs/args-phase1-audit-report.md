# ARGS Phase 1 — Implementation Audit Report

**Date:** 2026-06-08  
**Auditor role:** Principal Engineer / Technical Auditor  
**Branch reviewed:** `feature/args-phase1`  
**References:**

- `docs/aics-ai-investment-committee-architecture.md`
- `docs/args-gap-analysis.md`
- `docs/args-implementation-plan.md`

**Scope:** Read-only audit of existing ARGS code. No code changes.

---

## 1. Executive Summary

ARGS Phase 1 delivers a **runnable vertical slice**: schema migration `20260608_0016`, packet builder, committee registry, TARC/QRC LLM plugins (mockable), FRC/NRCC/RC stubs, a minimal LangGraph workflow, CRO aggregation, governance report persistence, `/api/v1/research/*` endpoints, and **9 passing tests**.

The implementation **correctly avoids trade recommendations** in persisted outputs and uses `governance_research_reports` instead of the legacy per-stock `research_reports` table.

However, against the **user ARGS Phase 1 mission** (full packet enrichment, evidence grounding, complete lineage, LangGraph hardening), the build is **partially complete**:

| Area | Verdict |
|------|---------|
| Constitutional (no BUY/SELL/sizing) | **Pass** (with minor schema/column caveats) |
| Packet builder | **Partial** — factor/exit/historical/market data largely empty |
| QRC grounding | **Partial** — prompt-only; no runtime evidence validation |
| Traceability chain | **Partial** — missing `ranking_result` and committee→CRO links |
| LangGraph (checkpoint/retry/observability) | **Stub / missing** |
| Test depth | **Below plan** — 9 tests vs architecture acceptance “50 unit tests” |

**Recommendation:** **Conditional No-Go** for production research governance until packet quant blocks are populated, evidence validation exists, and lineage covers the full chain. **Go** for continued development, mock-LLM demos, and integration testing on `feature/args-phase1`.

---

## 2. Architecture Compliance Score

**Score: 72 / 100**

| Architecture expectation | Status | Evidence |
|--------------------------|--------|----------|
| ARGS naming (`research_runs`, `cro_reviews`, `/research/*`) | Implemented | `app/models/args.py`, `app/api/v1/research.py` |
| No `final_recommendations` / CIO trade path | Implemented | CRO → `governance_research_reports` only |
| `governance_research_reports` vs legacy `research_reports` | Implemented | Gap doc + `GovernanceResearchReport` model |
| Canonical packet + SHA-256 hash | Implemented | `app/workspace_args/packet_schema.py`, builder |
| Committee plugin registry | Implemented | `app/args/plugins/registry.py` |
| LangGraph orchestration | Partial | 2-node graph; load/build/persist outside graph |
| Parallel committee execution | Incorrect | Sequential nested loops in `workflow.py` |
| Checkpointing | Stub | `checkpoint_ref = f"memory:{run.id}"` only |
| Retry / observability hooks | Missing | No retry; no `ObservabilityService` integration |
| Daily batch hook | Missing (deferred in plan) | No phase in `daily_batch_service.py` |
| `committee_registry` DB table | Missing (deferred) | In-code `CommitteeRegistry` only |
| Phase 1 arch doc acceptance (50 unit tests) | Not met | 9 tests total |

---

## 3. Constitutional Compliance Score

**Score: 88 / 100**

### Verified: no trade outputs in ARGS paths

Grep over `app/args/` and `app/workspace_args/` found **no** persisted `BUY`, `SELL`, `HOLD`, `STRONG_BUY`, `STRONG_SELL`, `position_size`, or `stop_loss` values—only **prohibitions in prompt strings**:

| File | Line | Content |
|------|------|---------|
| `app/args/plugins/tarc.py` | 19 | `"Do not recommend buy/sell/hold or position sizes."` |
| `app/args/plugins/qrc.py` | 20 | `"Do not invent statistics or trade recommendations."` |
| `app/args/agents/cro_agent.py` | 34 | `"Never recommend buy/sell/hold, rank securities, or suggest position sizes."` |

`committee_reviews` schema omits `vote`, `recommendation`, and trade-leaning scores (`app/models/args.py` lines 108–134).

CRO persistence omits `recommendation_label`, `position_size_pct`, `stop_loss_pct` (`app/models/args.py` lines 145–164; `args_research_run_service.py` lines 265–275).

Unit test `tests/unit/args/test_cro_no_trade_fields.py` asserts forbidden keys absent from CRO output blob.

### Caveats (not violations today, but risk)

| Item | Severity | Evidence |
|------|----------|----------|
| `research_label` on committees (`supportive` / `cautious` / `neutral`) | Low | `committee_contracts.py` line 17; used in CRO aggregation — not BUY/SELL but could be misread |
| `governance_research_reports.research_score` column | Low | Migration + model lines 161, 190 — **always set `None`** in service line 293 |
| `rank` referenced in RC stub evidence | Low | `rc_stub.py` lines 21–22 — cites deterministic rank, not LLM ranking |
| Mock LLM default strings mention “rank” in *findings text* | Low | `llm/port.py` lines 38–47 — narrative only, not a trade action |
| No runtime guard preventing future LLM JSON from emitting trade fields | Medium | Trusts prompt + parse only |

**LLM ranking / scoring:** Committees receive pre-computed `rank` and `composite_score` in the packet JSON passed to the LLM; the LLM is **not** asked to re-rank. **No code path** writes LLM-derived ranks back to `ranking_results`.

---

## 4. Packet Builder Score

**Score: 58 / 100** — **Partially Implemented**

**File:** `app/args/builders/investment_review_packet_builder.py`

| Required block (mission / arch §9.3) | Status | Evidence |
|--------------------------------------|--------|----------|
| Ranking metadata | Implemented | Lines 69–78: run id, strategy, universe, date, rank, score, components, inputs_hash |
| Score components | Implemented | Line 77 + `technical_factors` via `_technical_from_components` (126–132) |
| Validation metrics | Implemented | Horizon + decile rows from DB (34–62) |
| Regime metrics | Partial | `regime.regime_label` + validation regime (88–91); **no** `regime_history_id`, **no** `strategy_regime_performance` |
| Factor metrics | **Missing (empty)** | Lines 92–94: `"factor_ic": {}` — no `FactorPerformanceMetricRepository` call |
| Exit research metrics | **Missing (empty)** | Lines 92–94: `"exit_research": {}` — no exit repo call |
| Historical metrics | **Missing** | No `RankingPerformanceRepository` / forward-return snapshots |
| Lineage metadata | Partial | `source_lineage` ranking + validation ids (102–107); **no** `market_data_through`, factor/exit run ids |
| Market snapshot | Partial | Only `sector` (96–98); arch expects `last_close`, `last_date`, `adv_inr` |
| Packet hash | Implemented | `compute_packet_hash` in `packet_schema.py` (sorted-keys SHA-256) |
| Reproducibility | **Incorrect** | `packet_built_at` injected before hash (builder line 101) — **same inputs at different times → different hash** |

**Hash tests:** `tests/unit/args/test_packet_schema.py` validates stability on **static fixture** `golden_breakout_v1.json` — does **not** test live builder output or reproducibility without `packet_built_at`.

---

## 5. TARC Score

**Score: 70 / 100** — **Implemented** (enforcement weak)

**File:** `app/args/plugins/tarc.py`

| Check | Status | Evidence |
|-------|--------|----------|
| Uses ranking / score components | Yes | LLM user payload includes `ranking` (lines 24–25) |
| Uses technical metrics | Partial | `technical_factors` from score_components only — not separate market/TA series |
| Uses regime | Yes | `regime` in payload (line 26) |
| Does not use validation/quant blocks | Prompt-only | Validation not in `user` JSON — **not enforced in code** |
| Outputs findings/strengths/risks/evidence/confidence | Yes | Lines 36–39 |
| Evidence-backed claims | **Not validated** | Accepts any `supporting_evidence` from LLM JSON |

**Unsupported data exposure:** TARC does not receive `market_snapshot`, `validation`, or `quant_evidence` in the serialized user message — good. A malicious or misconfigured LLM could still hallucinate; there is no post-parse evidence checker.

---

## 6. QRC Score

**Score: 62 / 100** — **Partially Implemented**

**File:** `app/args/plugins/qrc.py`

| Check | Status | Evidence |
|-------|--------|----------|
| validation metrics | Yes (if in packet) | `validation` in user JSON (line 25) |
| decile metrics | Yes (if in packet) | Inside `validation.decile_metrics` |
| factor metrics | **Empty in practice** | Packet builder leaves `quant_evidence.factor_ic` as `{}` |
| exit research | **Empty in practice** | `quant_evidence.exit_research` as `{}` |
| regime metrics | Yes | `regime` in user JSON (line 27) |
| Numerical claims evidence-backed | **Not enforced** | No validator; mock returns `validation:horizon:20` ref without schema check |
| Unsupported sources | Prompt-only | QRC not blocked from receiving extra keys if packet payload extended |

Architecture §8.3 requires `strategy_regime_performance` and factor IC summaries in packet — **not loaded**.

---

## 7. CRO Score

**Score: 78 / 100** — **Implemented** (aggregation semantics OK)

**File:** `app/args/agents/cro_agent.py`

| CAN (required) | Status | Evidence |
|----------------|--------|----------|
| Summarize | Yes | LLM + `summary` field (lines 49) |
| Aggregate | Yes | `aggregation_snapshot` with label counts (lines 39–43) |
| Consensus | Partial | `structured.consensus` from mock / LLM (line 50) |
| Disagreements | Partial | Heuristic `disagreements` list (lines 27–31) + LLM `dissent_summary` |

| CANNOT (forbidden) | Status | Evidence |
|--------------------|--------|----------|
| Rank stocks | Pass | No rank output fields |
| Score stocks for trading | Pass | No `final_score` trade signal; `research_score` not set |
| Recommend stocks | Pass | Prompt forbids buy/sell/hold (line 34) |
| Size positions | Pass | Not in `CroAggregationOutput` or persistence |

**Note:** CRO aggregates `research_label` from committees — acceptable for research governance if documented; not equivalent to trade labels.

---

## 8. Traceability Score

**Score: 65 / 100** — **Partially Implemented**

**Lineage enums:** `app/core/constants.py` lines 75–79, 93–96.

**Persisted links** (`args_research_run_service.py`):

| Link | Status | Evidence |
|------|--------|----------|
| `research_run` → `ranking_run` | Yes | Lines 162–168 |
| `investment_review_packet` → `ranking_run` | Yes | `_link_packet_lineage` 321–327 |
| `investment_review_packet` → `research_run` | Yes | Lines 328–334 |
| `committee_review` → `packet` | Yes | Lines 241–247 |
| `cro_review` → `packet` | Yes | Lines 277–283 |
| `governance_report` → `cro_review` | Yes | Lines 308–314 |
| `committee_review` → `cro_review` | **Missing** | No direct edge |
| `packet` → `ranking_result` | **Missing** | No `LineageEntityType` for ranking_result; packet stores `stock_id` only |
| `validation_report` in lineage graph | **Missing** | Only embedded in packet JSON `source_lineage` |

**Incorrect relationship reuse:** Packet → `research_run` uses `LineageRelationshipType.RANKING_PRODUCES_PACKET` (line 333) — semantically wrong; should be a dedicated research-run relationship.

**Explainability API** (`args_explainability_service.py`): Returns reviews, CRO, reports, packet count — does **not** walk `run_lineage_records` for explain (lineage is separate endpoint).

**Lineage API:** Collects edges from `research_run` + packets only (lines 87–119) — does **not** traverse `committee_review`, `cro_review`, or `governance_report` entity edges unless queried separately.

**Required chain (audit mission):**

```
governance_report → cro_review → committee_review → investment_packet → ranking_result → ranking_run
```

**Actual traversable chain (via DB FKs + partial lineage):**

```
governance_report → cro_review → packet → ranking_run  (FK + lineage)
committee_review → packet → ranking_run
ranking_result: only implicit via packet.stock_id + ranking_run_id, not in lineage graph
```

---

## 9. API Score

**Score: 85 / 100** — **Implemented**

**Router:** `app/api/router.py` includes `research.router` at prefix `/research` → full path `/api/v1/research/*`.

| Endpoint | Status | Handler |
|----------|--------|---------|
| `POST /research/run` | Implemented | `research.py` lines 16–31 |
| `GET /research/latest` | Implemented | lines 34–48 |
| `GET /research/{id}` | Implemented | lines 51–56 |
| `GET /research/{id}/packet` | Implemented | lines 59–66 |
| `GET /research/{id}/explain` | Implemented | lines 69–74 |
| `GET /research/{id}/lineage` | Implemented | lines 77–82 |

**Schemas:** `app/schemas/args.py` — `ResearchRunRequest` / `ResearchRunResponse` (not used as response_model on routes — handlers return raw `dict`).

**Gaps:**

- No OpenAPI response models for explain/lineage payloads
- No pagination on packet list
- No RBAC (noted Phase 2 in plan)

Integration test `tests/integration/args/test_research_api.py` exercises full happy path (201 + explain + lineage).

---

## 10. Test Coverage Assessment

**Score: 45 / 100**

| Suite | Files | Coverage |
|-------|-------|----------|
| Packet hash | `test_packet_schema.py` | Fixture-only; **no builder unit test** |
| Registry | `test_committee_registry.py` | Codes registered |
| Workflow + mock LLM | `test_workflow_mock_llm.py` | 2 committees → 1 CRO |
| CRO trade fields | `test_cro_no_trade_fields.py` | Forbidden keys absent |
| Lineage enums | `test_lineage.py` | Enum existence + idempotent link — **not full chain** |
| API E2E | `test_research_api.py` | Single symbol, TARC+QRC only |

**Missing tests (critical):**

- `InvestmentReviewPacketBuilder` integration with DB fixtures (validation rows, factor/exit when added)
- QRC rejects/handles invented statistics
- Evidence ref validation against packet paths
- Full lineage chain assertion after E2E run
- TARC isolation (validation block not in LLM input)
- LangGraph failure/retry paths
- Stub committees (FRC/NRCC/RC) in workflow
- `dry_run` behavior
- Golden packet generated from builder vs static JSON

**Executed:** 9 passed (per prior verification on branch).

---

## 11. Component Checklist (Implemented / Partial / Stub / Missing / Incorrect)

| # | Component | Status | Evidence |
|---|-----------|--------|----------|
| 1 | InvestmentReviewPacketBuilder | **Partially Implemented** | Builder file; empty quant blocks; reproducibility issue |
| 2 | Committee Framework | **Implemented** | `base.py`, `registry.py`, 5 plugins registered |
| 3 | TARC | **Implemented** | `tarc.py`; weak enforcement |
| 4 | QRC | **Partially Implemented** | `qrc.py`; packet lacks quant data |
| 5 | CRO | **Implemented** | `cro_agent.py` + persistence |
| 6 | LangGraph Workflow | **Partially Implemented** | `workflow.py` — 2 nodes; no checkpoint/retry/obs |
| 7 | Traceability | **Partially Implemented** | Lineage links incomplete / wrong type on one edge |
| 8 | Explainability | **Partially Implemented** | `args_explainability_service.py` — DB join style, not full graph walk |
| 9 | Database Models | **Implemented** | `app/models/args.py` + migration `20260608_0016` |
| 10 | Repositories | **Implemented** | 7 repos under `app/db/repositories/` |
| 11 | APIs | **Implemented** | All 6 endpoints present |
| 12 | Tests | **Partially Implemented** | 9 tests; gaps above |
| — | FRC | **Stub** | `frc_stub.py` |
| — | NRCC | **Stub** | `nrcc_stub.py` |
| — | RC | **Stub** | `rc_stub.py` (no sizing — compliant) |

---

## 12. Evidence Audit (Most Important)

### Findings

1. **No runtime evidence validator** — `supporting_evidence` is stored as opaque JSON from LLM output (`committee_review` lines 125, persistence lines 233).
2. **Mock evidence refs are not verified** — e.g. `{"ref":"validation:horizon:20"}` in `llm/port.py` line 47 may not exist in packet.
3. **CRO `evidence_refs`** — copied from first 3 committee evidence dicts per review (`cro_agent.py` lines 51–56) without dereferencing packet paths.
4. **`GovernanceResearchReportEvidence`** — stores `evidence_ref` string + payload; **no FK** to validation report, factor metric, or ranking result.
5. **Stubs** — FRC/NRCC use `stub:frc` refs (`frc_stub.py` line 21) — honest about stub mode.
6. **Free-text findings** — `findings` field can contain unsourced numerics; QRC prompt forbids invention but **no post-condition check**.

### Recommendations (audit-only)

1. Add `EvidenceRefValidator` that resolves refs like `validation:horizon:20` against packet JSON paths.
2. Reject committee outputs with empty `supporting_evidence` when findings contain numeric tokens.
3. Persist structured evidence rows with `source_type`, `source_id`, `field_path`.
4. Extend lineage: `committee_review` → `validation_report` / `factor_metric` when cited.
5. Golden tests: builder output + committee output with mandatory refs.

---

## 13. Critical Defects

| ID | Defect | Impact |
|----|--------|--------|
| C1 | Packet `factor_ic` and `exit_research` always `{}` | QRC cannot perform grounded quant research per mission/arch §8.3 |
| C2 | No evidence validation pipeline | Hallucinated statistics may persist in `findings` |
| C3 | Lineage chain incomplete (`ranking_result`, committee→CRO) | Explainability/audit cannot fully reconstruct provenance |
| C4 | `packet_built_at` included in hashed payload | Breaks content-addressed reproducibility invariant (arch §9.3) |

---

## 14. Medium Defects

| ID | Defect | Impact |
|----|--------|--------|
| M1 | LangGraph: no checkpointing, retry, or observability hooks | Operational resilience below Phase 1 mission |
| M2 | Committees run sequentially, not in parallel | Performance / arch diagram mismatch |
| M3 | Workflow omits Load/Build/Persist nodes (in service only) | Harder to replay/resume graph state |
| M4 | `investment_review_packets.ranking_run_id` has no DB FK | Referential integrity risk |
| M5 | Lineage API does not return full subgraph | `/lineage` under-reports edges |
| M6 | No unit test for packet builder | Regressions likely on quant block work |

---

## 15. Low Defects

| ID | Defect | Impact |
|----|--------|--------|
| L1 | `research_score` column unused | Future misuse risk |
| L2 | API returns `dict` not Pydantic response models | Contract drift |
| L3 | `daily_batch_run_id` on model never set | Optional hook unused |
| L4 | Wrong lineage relationship type packet→research_run | Semantic confusion in observability UI |
| L5 | Market snapshot minimal | TARC lacks price/volume context from arch |
| L6 | Test count far below architecture Phase 1 acceptance | Quality gate not met |

---

## 16. Phase 1 Completion %

Estimated against **user ARGS Phase 1 mission** (12 components + constitutional + evidence):

| Category | Weight | Completion |
|----------|--------|------------|
| Schema + repos | 15% | 95% |
| Packet builder | 15% | 55% |
| Committees (TARC/QRC + stubs) | 15% | 75% |
| CRO + governance reports | 10% | 80% |
| LangGraph + ops hooks | 10% | 40% |
| Traceability + explainability | 15% | 60% |
| APIs | 10% | 85% |
| Tests + evidence | 10% | 40% |

**Overall Phase 1 completion: ~68%**

Against **architecture doc Phase 1** (skeleton + dry_run + 50 tests): **~75%** (skeleton exceeded with real TARC/QRC, but tests short).

---

## 17. Go / No-Go Recommendation

| Gate | Decision |
|------|----------|
| **Merge to main for production governance** | **No-Go** until C1–C4 addressed |
| **Continue on feature branch / dev demo** | **Go** — code runs; 9 tests pass; constitutional trade rules respected in schema and persistence |
| **Pilot with mock LLM only** | **Go** with documented limitations |
| **Pilot with real LLM** | **No-Go** until evidence validator + full packet quant blocks |

**Sign-off criteria for Phase 1 complete:**

1. Packet builder loads factor IC + exit research + market snapshot (+ optional historical performance).
2. Evidence refs validated before persist.
3. Full lineage chain including `ranking_result` (or explicit `stock_id`+`ranking_run_id` edge type).
4. Hash excludes non-deterministic timestamps (or hash canonical subset).
5. Test suite ≥ 25 targeted tests including builder golden + lineage E2E + QRC grounding negative cases.

---

*End of audit report.*
