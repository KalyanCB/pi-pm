# ARGS Gap Analysis — AICS → ARGS on Pi-PM

**Date:** 2026-06-08  
**Reference:** `docs/aics-ai-investment-committee-architecture.md`  
**Codename:** ARGS (AI Research & Governance System)

## Constitutional mapping


| AICS concept             | ARGS concept                             | Phase 1 status                                                  |
| ------------------------ | ---------------------------------------- | --------------------------------------------------------------- |
| Investment committee run | `research_runs`                          | New table                                                       |
| CIO Agent                | CRO Agent                                | Summarize/aggregate/consensus/disagreement only                 |
| CIO decisions            | `cro_reviews`                            | No `recommendation_label`, `position_size_pct`, `stop_loss_pct` |
| Final recommendations    | `governance_research_reports` + evidence | Research narrative only; no BUY/SELL/HOLD                       |
| `/committee/*`           | `/research/*`                            | New router                                                      |


**Hard rules (unchanged intent):** LLMs never rank securities, never emit trade decisions, never size positions or stops. Deterministic engines own investment decisions.

## Naming conflict: `research_reports`


| Table / model                                    | Purpose                                                         | ARGS action                                                                   |
| ------------------------------------------------ | --------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `research_reports` / `ResearchReport`            | Per-stock LLM equity research (`app/models/research_report.py`) | **Keep unchanged**                                                            |
| User term "research_reports" (governance output) | Multi-committee governance artifact                             | `**governance_research_reports`** + `**governance_research_report_evidence**` |


Models: `GovernanceResearchReport`, `GovernanceResearchReportEvidence`.

## Existing Pi-PM capabilities → ARGS inputs

### Ranking (`app/ranking/`, `ranking_runs`, `ranking_results`)

- **Reuse:** `RankingRunRepository`, `RankingResultRepository.list_top`
- **Packet field:** `ranking` block (rank, composite_score, score_components, inputs_hash)
- **Gap:** None for Phase 1; read-only

### Validation (`app/validation/`, `ranking_validation_reports`, horizon/decile metrics)

- **Reuse:** `RankingValidationRepository`, `ValidationMetricsRepository`
- **Packet field:** `validation` (report_id, status, horizon_metrics, decile_metrics, regime_label)
- **Gap:** `require_completed_validation` gate in run config (Phase 1 supported)

### Factor analytics (`factor_performance_metrics`, `FactorPerformanceMetricRepository`)

- **Reuse:** Latest IC summaries by strategy/universe/regime
- **Packet field:** `quant_evidence.factor_ic`
- **Gap:** Optional empty when no factor run exists (QRC cites absence)

### Exit research (`exit_research_`*, `ExitResearchMetricRepository`)

- **Reuse:** Policy metrics / alpha decay for strategy
- **Packet field:** `quant_evidence.exit_research`
- **Gap:** Optional; stub committees tolerate missing exit block

### Lineage (`run_lineage_records`, `RunLineageRepository`, `TraceabilityService`)

- **Reuse:** Same repository + link pattern as ranking/validation/daily batch
- **Extend:** `LineageEntityType` / `LineageRelationshipType` in `app/core/constants.py`
- **Gap:** New entity types for research_run, packet, committee_review, cro_review, governance_report

### Daily batch (`daily_batch_runs`, Sprint 8.6)

- **Reuse:** Optional `daily_batch_run_id` on `research_runs`
- **Gap:** Phase 2 — trigger research phase after rankings (not wired in Phase 1)

### Research intelligence (`research_intelligence_`*, `/analytics/research-intelligence`)

- **Reuse:** Optional `research_context.research_intelligence_report_id` in packet
- **Gap:** Not required for Phase 1 E2E

### Regime (`regime_history`, `strategy_regime_performance`)

- **Reuse:** `RegimeAnalyticsRepository` / validation report regime_label
- **Packet field:** `regime`

### Per-stock `research_reports`

- **No merge** with governance reports; separate product surface

## AICS tables deferred to Phase 2+

- `committee_registry`, `committee_configurations` (in-code registry Phase 1)
- `committee_votes`, `committee_execution_logs` (logs via `llm_execution_records` only)
- `recommendation_explanations`, `recommendation_change_log`
- `agent_execution_audit` (minimal audit via run status + LLM records)

## Committee review schema (Phase 1)

Omit AICS `vote`, `recommendation`, trade-leaning `score`. Store:

- `findings`, `strengths`, `risks`, `supporting_evidence`, `confidence`, `extensions`
- Status: pending | completed | failed | degraded | timeout

## CRO review schema (Phase 1)

- `aggregation_snapshot`, `rationale`, `dissent_summary`, `confidence`
- Explicitly **omit:** `recommendation_label`, `position_size_pct`, `stop_loss_pct`, `final_score` as trade signal

## Plugin parity (Phase 1)


| Committee | Phase 1                                                   |
| --------- | --------------------------------------------------------- |
| TARC      | LLM (mockable); ranking factors + technical metrics only  |
| QRC       | LLM (mockable); validation/decile/factor/exit/regime only |
| FRC       | Stub                                                      |
| NRCC      | Stub                                                      |
| RC        | Stub (no position_size / stop_loss in output)             |


## TARC doc (`docs/tarc-architecture-design.md`)

Rule-based TARC prototype remains reference for factor mapping; ARGS TARC is LLM interpretive layer on packet technical block only.

## Summary

Pi-PM already provides deterministic ranking, validation, factor IC, exit research, and lineage. ARGS Phase 1 adds governance workflow tables (distinct from `research_reports`), packet builder, committee plugins, CRO aggregation, LangGraph orchestration, and `/api/v1/research/`* — without trade recommendations or LLM ranking.