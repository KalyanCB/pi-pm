# Pi-PM Product Discovery Pack — Index

**Generated:** 2026-06-05  
**Repo:** `/Users/kalyancb/pi-pm`  
**Source of truth:** Application code (`app/`, `tests/`, `migrations/`, `scripts/`, `docker/`)  
**Cross-references:** [`docs/AI/12_HANDOVER/AI_AGENT_HANDOVER.md`](../AI/12_HANDOVER/AI_AGENT_HANDOVER.md), [`docs/PLATFORM-HANDOFF-2026.md`](../PLATFORM-HANDOFF-2026.md)

---

## Purpose

Onboarding pack for a new Product Owner. Each document is evidence-backed from code scans and test collection (312 tests, `pytest --collect-only`, 2026-06-05). Where legacy docs disagree with code, discrepancies are flagged inline.

---

## Reading order (recommended ~4 hours)

| Order | Document | Time | Why read |
|-------|----------|------|----------|
| 1 | [15_EXECUTIVE_SUMMARY.md](./15_EXECUTIVE_SUMMARY.md) | 10 min | Board-level snapshot |
| 2 | [PRODUCT_MATURITY_SCORECARD.md](./PRODUCT_MATURITY_SCORECARD.md) | 10 min | Strengths and gaps by area |
| 3 | [01_PRODUCT_CURRENT_STATE.md](./01_PRODUCT_CURRENT_STATE.md) | 25 min | Capability inventory |
| 4 | [02_ARCHITECTURE_CURRENT_STATE.md](./02_ARCHITECTURE_CURRENT_STATE.md) | 20 min | Runtime and pipeline map |
| 5 | [03_DOMAIN_MODEL.md](./03_DOMAIN_MODEL.md) | 25 min | Entities and relationships |
| 6 | [04_API_CATALOG.md](./04_API_CATALOG.md) | 30 min | HTTP surface for integrations |
| 7 | [05_DATA_PIPELINE_INVENTORY.md](./05_DATA_PIPELINE_INVENTORY.md) | 25 min | Batch and research pipelines |
| 8 | [06_AI_AND_AGENT_INVENTORY.md](./06_AI_AND_AGENT_INVENTORY.md) | 25 min | LLM boundaries and ARGS |
| 9 | [10_RECOMMENDATION_ENGINE_GAP_ANALYSIS.md](./10_RECOMMENDATION_ENGINE_GAP_ANALYSIS.md) | 20 min | Buy/hold/exit signal gaps |
| 10 | [11_PORTFOLIO_ENGINE_GAP_ANALYSIS.md](./11_PORTFOLIO_ENGINE_GAP_ANALYSIS.md) | 15 min | Paper trade / portfolio stubs |
| 11 | [07_TEST_COVERAGE_ASSESSMENT.md](./07_TEST_COVERAGE_ASSESSMENT.md) | 15 min | Test distribution and holes |
| 12 | [08_TECHNICAL_DEBT_REGISTER.md](./08_TECHNICAL_DEBT_REGISTER.md) | 15 min | Known structural debt |
| 13 | [09_REQUIREMENTS_TRACEABILITY_MATRIX.md](./09_REQUIREMENTS_TRACEABILITY_MATRIX.md) | 20 min | PRD → code → tests |
| 14 | [12_MOBILE_READINESS_ASSESSMENT.md](./12_MOBILE_READINESS_ASSESSMENT.md) | 15 min | No mobile app; API readiness |
| 15 | [13_ROADMAP_RECOMMENDATION.md](./13_ROADMAP_RECOMMENDATION.md) | 20 min | P0–P3 from actual state |
| 16 | [14_PO_QUESTIONS_FOR_FOUNDER.md](./14_PO_QUESTIONS_FOR_FOUNDER.md) | 10 min | Unknowns not in code |

---

## Document index

| # | File | Summary |
|---|------|---------|
| 01 | [01_PRODUCT_CURRENT_STATE.md](./01_PRODUCT_CURRENT_STATE.md) | Capability table, workflows, implemented/partial/missing |
| 02 | [02_ARCHITECTURE_CURRENT_STATE.md](./02_ARCHITECTURE_CURRENT_STATE.md) | Mermaid: runtime, batch, AI, validation, committees, storage |
| 03 | [03_DOMAIN_MODEL.md](./03_DOMAIN_MODEL.md) | ORM entities from `app/models/`, ER diagrams |
| 04 | [04_API_CATALOG.md](./04_API_CATALOG.md) | OpenAPI-style groups from `app/api/v1/` |
| 05 | [05_DATA_PIPELINE_INVENTORY.md](./05_DATA_PIPELINE_INVENTORY.md) | Ingest, daily batch, ranking, validation, factor, exit, regime, ARGS |
| 06 | [06_AI_AND_AGENT_INVENTORY.md](./06_AI_AND_AGENT_INVENTORY.md) | LLM, prompts, committees, SQE, risks |
| 07 | [07_TEST_COVERAGE_ASSESSMENT.md](./07_TEST_COVERAGE_ASSESSMENT.md) | 312 tests by area; gaps |
| 08 | [08_TECHNICAL_DEBT_REGISTER.md](./08_TECHNICAL_DEBT_REGISTER.md) | Structural debt (no code TODO/FIXME found) |
| 09 | [09_REQUIREMENTS_TRACEABILITY_MATRIX.md](./09_REQUIREMENTS_TRACEABILITY_MATRIX.md) | PRD goals → modules → tests |
| 10 | [10_RECOMMENDATION_ENGINE_GAP_ANALYSIS.md](./10_RECOMMENDATION_ENGINE_GAP_ANALYSIS.md) | Rankings, conviction, lifecycle |
| 11 | [11_PORTFOLIO_ENGINE_GAP_ANALYSIS.md](./11_PORTFOLIO_ENGINE_GAP_ANALYSIS.md) | Paper trade models vs services |
| 12 | [12_MOBILE_READINESS_ASSESSMENT.md](./12_MOBILE_READINESS_ASSESSMENT.md) | Hypothetical screens vs APIs |
| 13 | [13_ROADMAP_RECOMMENDATION.md](./13_ROADMAP_RECOMMENDATION.md) | P0–P3 priorities |
| 14 | [14_PO_QUESTIONS_FOR_FOUNDER.md](./14_PO_QUESTIONS_FOR_FOUNDER.md) | Founder-only unknowns |
| 15 | [15_EXECUTIVE_SUMMARY.md](./15_EXECUTIVE_SUMMARY.md) | Board summary |
| — | [PRODUCT_MATURITY_SCORECARD.md](./PRODUCT_MATURITY_SCORECARD.md) | 0–100 scores with evidence |

---

## Verified key facts (code-backed)

| Fact | Evidence |
|------|----------|
| Strategies: `breakout_v1`, `momentum_v1` only | `app/ranking/registry.py` |
| Alpha at bucket level; rank calibration research-only | `app/ranking_research/`, `docs/outcome-attribution-report.md` |
| Validation tail `insufficient_data` ~2026-05-27+ | `app/validation/constants.py`, `docs/dailyruns/04-jun-2026/03-validation.md` |
| 5 committees + CRO; Phase 2 packet views | `app/workspace_args/constants.py`, `app/args/committee_packet_views.py` |
| SQE on packets; `ARGS_QRC_USE_SQE=false` default | `app/args/plugins/stock_quality_evidence.py`, `app/core/config.py:79` |
| `outcome_attribution`, `ranking_research` modules | `app/outcome_attribution/`, `app/ranking_research/` |
| Paper trade / portfolio tables; no services | `app/models/paper_trade.py`, `app/portfolio/__init__.py` |
| Migration head `20260609_0018` | `migrations/versions/20260609_0018_see_v2_metrics.py` |
| Tests: **312 collected** | `pytest tests/ --collect-only -q` (2026-06-05) |

---

## External deep dives (not duplicated here)

- [`docs/AI/01_PRODUCT/PRD.md`](../AI/01_PRODUCT/PRD.md)
- [`docs/AI/07_API/API_REFERENCE.md`](../AI/07_API/API_REFERENCE.md)
- [`docs/AI/08_DATA_MODEL/DATABASE_SCHEMA.md`](../AI/08_DATA_MODEL/DATABASE_SCHEMA.md)
- [`docs/dailyruns/04-jun-2026/`](../dailyruns/04-jun-2026/) — operational run logs
