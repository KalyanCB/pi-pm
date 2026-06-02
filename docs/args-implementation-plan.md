# ARGS Phase 1 — Implementation Status (PO Review)

**Product:** Pi-PM — ARGS (AI Research & Governance System)  
**Branch:** `feature/args-phase1` (pushed to `origin`)  
**Migration:** `20260608_0016` (after `20260607_0015`)  
**Last updated:** 2026-06-08  
**Commits:** `04fb536` (Phase 1 code), `2f16492` (docs touch-up)  
**Companion:** `docs/args-gap-analysis.md` (design & integration summary)

---

## 1. Executive summary

Phase 1 delivers a **complete research governance loop**:

- Database schema and repositories  
- Investment Review Packet builder (deterministic inputs + content hash)  
- Five LLM committee plugins + CRO aggregation  
- LangGraph workflow (parallel committees → CRO)  
- REST API under `/api/v1/research/*`  
- Lineage and explainability  
- Pluggable **per-agent LLM** configuration (provider, model, API key, base URL)  
- **22 automated tests** (unit + integration)

**Not in Phase 1:** Daily batch auto-trigger, external news/fundamental feeds, Postgres graph checkpointing, admin UI for committee config.

---

## 2. Shipped vs planned

| Deliverable | Planned | Shipped |
|-------------|---------|---------|
| Schema migration `20260608_0016` | Yes | **Yes** |
| Packet builder | Yes | **Yes** (ranking, validation, factor, exit, regime, market, historical) |
| TARC / QRC committees | Yes | **Yes** |
| FRC / NRCC / RC | Stubs in original plan | **Yes** (LLM plugins; data feeds partial) |
| CRO aggregation | Yes | **Yes** |
| LangGraph workflow | Yes | **Yes** (2-node; parallel committees) |
| Evidence validator | Audit follow-up | **Yes** |
| Per-agent LLM ports | Follow-up | **Yes** |
| `/api/v1/research/*` (6 endpoints) | Yes | **Yes** |
| Daily batch hook | Phase 2 | **No** |
| `committee_registry` DB | Phase 2 | **No** (in-code registry) |
| 50 unit tests (arch doc target) | Stretch | **22 tests** |

---

## 3. How to run (PO / QA)

### 3.1 Prerequisites

```bash
cd pi-pm
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
alembic upgrade head   # applies through 20260608_0016
```

Requires a **completed** `ranking_run_id` (from rankings API or daily batch).

### 3.2 Start API

```bash
.venv/bin/uvicorn app.main:app --reload
```

### 3.3 Trigger research run

```bash
curl -X POST http://localhost:8000/api/v1/research/run \
  -H "Content-Type: application/json" \
  -d '{
    "ranking_run_id": "<UUID>",
    "top_n": 20,
    "committee_codes": ["TARC", "FRC", "QRC", "NRCC", "RC"]
  }'
```

### 3.4 Read results

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/research/latest` | Most recent completed run |
| `GET /api/v1/research/{id}` | Run summary + governance report list |
| `GET /api/v1/research/{id}/packet` | Immutable packets (optional `?symbol=`) |
| `GET /api/v1/research/{id}/explain` | Committee + CRO narrative |
| `GET /api/v1/research/{id}/lineage` | Lineage graph edges |

### 3.5 Verification (engineering)

```bash
.venv/bin/pytest tests/unit/args tests/integration/args -q
# Expected: 22 passed
```

---

## 4. API contract summary

**Base path:** `/api/v1/research`

### POST `/run`

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ranking_run_id` | UUID | required | Completed ranking run to explain |
| `top_n` | int | 20 | Top-ranked names to review (1–100) |
| `committee_codes` | list[str] | all five | Subset: TARC, FRC, QRC, NRCC, RC |
| `require_completed_validation` | bool | true | Fail if validation not completed |
| `dry_run` | bool | false | Build packets only; skip committee persist |
| `trigger_mode` | str | `on_demand` | Stored on `research_runs` |

**Response (201):** `run_id`, `status`, `candidates_reviewed`, `governance_reports_issued`, `token_usage_total`, `dry_run`.

---

## 5. Database objects (Phase 1)

| Table | Purpose |
|-------|---------|
| `research_runs` | Top-level ARGS workflow run |
| `investment_review_packets` | Immutable packet JSONB + `packet_hash` |
| `committee_reviews` | One row per (packet, committee) |
| `cro_reviews` | CRO aggregation per packet |
| `governance_research_reports` | Final research output per symbol |
| `governance_research_report_evidence` | Evidence rows linked to report |
| `prompt_versions` | Prompt template registry (stub seeds) |
| `llm_execution_records` | Model, tokens per LLM call |

**Lineage:** Extended via existing `run_lineage_records` (no duplicate lineage system).

---

## 6. Code map (shipped)

### 6.1 Workspace & domain

| Path | Role |
|------|------|
| `app/workspace_args/` | Packet schema, contracts, evidence validator, constants |
| `app/args/builders/investment_review_packet_builder.py` | Deterministic packet assembly |
| `app/args/loaders/ranking_candidate_loader.py` | Top-N from ranking run |

### 6.2 Committees & CRO

| Path | Role |
|------|------|
| `app/args/plugins/tarc.py` | Technical committee |
| `app/args/plugins/frc.py` | Fundamental committee |
| `app/args/plugins/qrc.py` | Quant committee |
| `app/args/plugins/nrcc.py` | News/catalyst committee |
| `app/args/plugins/rc.py` | Risk committee |
| `app/args/plugins/registry.py` | In-code committee registry |
| `app/args/agents/cro_agent.py` | CRO aggregation |

### 6.3 LLM (loosely coupled)

| Path | Role |
|------|------|
| `app/args/llm/port.py` | `LlmPort` protocol + `MockLlmPort` |
| `app/args/llm/config.py` | Per-agent settings resolution |
| `app/args/llm/registry.py` | `CommitteeLlmRegistry` |
| `app/args/llm/providers/factory.py` | `register_llm_provider()` extensibility |
| `app/args/llm/providers/openai_compatible.py` | OpenAI-compatible HTTP client |

### 6.4 Orchestration & API

| Path | Role |
|------|------|
| `app/args/graph/workflow.py` | LangGraph: parallel committees → CRO |
| `app/services/args_research_run_service.py` | Run lifecycle + persistence |
| `app/services/args_explainability_service.py` | Explain + lineage queries |
| `app/api/v1/research.py` | REST endpoints |
| `app/db/repositories/*` | ARGS repositories (7 files) |
| `app/models/args.py` | SQLAlchemy models |

### 6.5 Tests

| Path | Coverage |
|------|----------|
| `tests/unit/args/` | Packet hash, builder, evidence, LLM registry, workflow, CRO |
| `tests/integration/args/` | Full API E2E, lineage chain |
| `tests/fixtures/packets/golden_breakout_v1.json` | Golden packet fixture |

---

## 7. LLM configuration (operations)

Each agent independently resolves: **provider → model → API key → base URL → timeout**, with global fallbacks.

### 7.1 Global defaults

```bash
ARGS_LLM_PROVIDER=mock              # mock | openai | openai_compatible | custom
ARGS_LLM_DEFAULT_MODEL=gpt-4o-mini
ARGS_LLM_OPENAI_API_KEY=            # fallback key
ARGS_LLM_OPENAI_BASE_URL=https://api.openai.com/v1
ARGS_LLM_TIMEOUT_SECONDS=60
```

### 7.2 Per-agent overrides (empty = inherit global)

For each of **TARC, FRC, QRC, NRCC, RC, CRO**:

```bash
ARGS_LLM_{AGENT}_PROVIDER=
ARGS_LLM_{AGENT}_MODEL=
ARGS_LLM_{AGENT}_API_KEY=
ARGS_LLM_{AGENT}_BASE_URL=
ARGS_LLM_{AGENT}_TIMEOUT_SECONDS=
```

Example — different vendors per committee:

```bash
ARGS_LLM_PROVIDER=openai
ARGS_LLM_OPENAI_API_KEY=sk-global-fallback

ARGS_LLM_TARC_PROVIDER=openai
ARGS_LLM_TARC_API_KEY=sk-tarc-account
ARGS_LLM_TARC_MODEL=gpt-4o

ARGS_LLM_QRC_PROVIDER=openai
ARGS_LLM_QRC_API_KEY=sk-azure-qrc
ARGS_LLM_QRC_BASE_URL=https://my-resource.openai.azure.com/openai/deployments/qrc
ARGS_LLM_QRC_MODEL=gpt-4o-mini

ARGS_LLM_NRCC_PROVIDER=mock
```

### 7.3 Adding a custom provider (engineering)

```python
from app.args.llm.providers.factory import register_llm_provider

register_llm_provider("anthropic", build_anthropic_port)
```

Then set `ARGS_LLM_TARC_PROVIDER=anthropic`.

---

## 8. Workflow behavior

```text
RankingCandidateLoader
  → InvestmentReviewPacketBuilder (per top-N stock)
  → LangGraph: parallel_committees (ThreadPoolExecutor, retry ×2)
  → LangGraph: cro_aggregate
  → Persist: committee_reviews, cro_reviews, governance_research_reports
  → Link lineage edges
```

- **Mock LLM (default):** No network; deterministic JSON for demos/tests.  
- **OpenAI mode:** Requires API key(s); JSON response format; temperature 0.

---

## 9. Phase 2 backlog (PO prioritization)

| Priority | Item | User value |
|----------|------|------------|
| P1 | Daily batch phase: auto-run ARGS after rankings | Nightly research without manual trigger |
| P1 | News feed → `news_snapshot` (NRCC full mode) | Catalyst-aware research |
| P1 | Fundamental data → `fundamental_snapshot` (FRC) | Real fundamental committee |
| P2 | Postgres LangGraph checkpoint + replay API | Failure recovery |
| P2 | `committee_registry` + admin configuration | Non-env config management |
| P2 | RBAC on `/research/*` | Production access control |
| P2 | Audit export + change log | Compliance |
| P3 | Expand test suite toward 50+ cases | Release confidence |
| P3 | Hook `research_intelligence` into packet | Richer research context |

---

## 10. Dependency order (as built)

1. `app/core/constants.py` — lineage + status enums  
2. `app/models/args.py`  
3. `migrations/versions/20260608_0016_args_phase1.py`  
4. Repositories under `app/db/repositories/`  
5. `app/workspace_args/*`  
6. `app/args/llm/*` + `app/args/plugins/*`  
7. `app/args/graph/workflow.py`  
8. Services + API + deps  
9. Tests + `pyproject.toml` (`langgraph`, `langchain-core`, `httpx`)

---

## 11. PO sign-off template

**Phase 1 — ARGS research governance (internal pilot)**

- [ ] Product principles (no trade outputs) understood and accepted  
- [ ] User journey (ranking run → research run → explain) demonstrated  
- [ ] NRCC degraded mode acceptable until news feed (Phase 2)  
- [ ] FRC limited to market/sector until fundamental feed (Phase 2)  
- [ ] LLM cost model understood (per-agent keys/models)  
- [ ] Phase 2 backlog prioritized (daily batch hook, data feeds)

**Sign-off:** _________________ **Date:** _________

---

## 12. References

| Document | Purpose |
|----------|---------|
| `docs/args-gap-analysis.md` | Design & integration (PO-facing) |
| `docs/aics-ai-investment-committee-architecture.md` | Full architecture |
| `docs/args-phase1-audit-report.md` | Engineering audit (scores, defects) |
