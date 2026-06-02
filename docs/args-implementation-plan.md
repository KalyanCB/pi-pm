# ARGS Phase 1 Implementation Plan

**Migration:** `20260608_0016` (after `20260607_0015`)  
**Branch:** `feature/args-phase1`

## Dependency order

1. `app/core/constants.py` — lineage + ARGS status enums
2. `app/models/args.py` + `app/models/__init__.py`
3. `migrations/versions/20260608_0016_args_phase1.py`
4. `app/db/repositories/args_*.py`
5. `app/workspace_args/`* — domain types, packet schema, contracts
6. `app/args/llm/port.py` — injectable LLM port
7. `app/args/builders/investment_review_packet_builder.py`
8. `app/args/plugins/*` + registry
9. `app/args/graph/*` — LangGraph workflow
10. `app/services/args_research_run_service.py`, `args_explainability_service.py`
11. `app/schemas/args.py`
12. `app/api/v1/research.py`, `app/api/deps.py`, `app/api/router.py`
13. Tests + `pyproject.toml` deps

## Files to create


| Path                                                           | Purpose                  |
| -------------------------------------------------------------- | ------------------------ |
| `docs/args-gap-analysis.md`                                    | Gap analysis             |
| `docs/args-implementation-plan.md`                             | This plan                |
| `app/models/args.py`                                           | SQLAlchemy models        |
| `migrations/versions/20260608_0016_args_phase1.py`             | Schema                   |
| `app/db/repositories/research_run_repository.py`               | research_runs            |
| `app/db/repositories/investment_review_packet_repository.py`   | packets                  |
| `app/db/repositories/committee_review_repository.py`           | committee_reviews        |
| `app/db/repositories/cro_review_repository.py`                 | cro_reviews              |
| `app/db/repositories/governance_research_report_repository.py` | governance reports       |
| `app/db/repositories/args_prompt_version_repository.py`        | prompt_versions          |
| `app/db/repositories/llm_execution_record_repository.py`       | llm_execution_records    |
| `app/workspace_args/constants.py`                              | Committee codes          |
| `app/workspace_args/models.py`                                 | Domain dataclasses       |
| `app/workspace_args/packet_schema.py`                          | Packet version + hash    |
| `app/workspace_args/committee_contracts.py`                    | Review output types      |
| `app/args/llm/port.py`                                         | LLM protocol + mock      |
| `app/args/builders/investment_review_packet_builder.py`        | Packet assembly          |
| `app/args/loaders/ranking_candidate_loader.py`                 | Top-N load               |
| `app/args/plugins/base.py`                                     | CommitteePlugin protocol |
| `app/args/plugins/registry.py`                                 | CommitteeRegistry        |
| `app/args/plugins/tarc.py`, `qrc.py`, stubs                    | Plugins                  |
| `app/args/graph/state.py`                                      | Workflow state           |
| `app/args/graph/workflow.py`                                   | LangGraph graph          |
| `app/services/args_research_run_service.py`                    | Run orchestration        |
| `app/services/args_explainability_service.py`                  | Explain + lineage        |
| `app/schemas/args.py`                                          | API DTOs                 |
| `app/api/v1/research.py`                                       | REST endpoints           |
| `tests/unit/args/*`                                            | Unit tests               |
| `tests/integration/args/*`                                     | Integration tests        |
| `tests/fixtures/packets/golden_breakout_v1.json`               | Golden packet            |


## Files to modify


| Path                     | Change                           |
| ------------------------ | -------------------------------- |
| `app/core/constants.py`  | Lineage enums, ResearchRunStatus |
| `app/models/__init__.py` | Export ARGS models               |
| `app/api/deps.py`        | ARGS repositories + services     |
| `app/api/router.py`      | Include research router          |
| `pyproject.toml`         | `langgraph`, `langchain-core`    |


## API surface (`/api/v1/research`)

- `POST /research/run`
- `GET /research/latest`
- `GET /research/{id}`
- `GET /research/{id}/packet`
- `GET /research/{id}/explain`
- `GET /research/{id}/lineage`

## Phase 2 (out of scope)

- Daily batch research phase hook  
- FRC/NRCC/RC full LLM + external data  
- `committee_registry` DB table  
- `recommendation_change_log`, audit export, replay API  
- Postgres LangGraph checkpointer (MemorySaver Phase 1)

## Verification

```bash
pytest tests/unit/args tests/integration/args -q
ruff check app/args app/workspace_args app/models/args.py app/services/args_*.py
```

