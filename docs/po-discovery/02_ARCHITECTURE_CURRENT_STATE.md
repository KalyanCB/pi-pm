# Architecture Current State

**Date:** 2026-06-05  
**Stack:** FastAPI 0.4.1, PostgreSQL 16, SQLAlchemy, Alembic, LangGraph (ARGS workflow)

---

## Runtime topology

```mermaid
flowchart TB
  subgraph clients [Clients]
    CLI[scripts/*.py]
    HTTP[HTTP clients / future mobile]
    OPS[Ops cron / manual]
  end

  subgraph docker [Docker - docker/docker-compose.yml]
    API[uvicorn app.main:app :8000]
    PG[(PostgreSQL 16 pipm)]
  end

  subgraph external [External]
    YAHOO[Yahoo Finance API]
    LLM[OpenAI / compatible LLM]
  end

  CLI --> API
  HTTP --> API
  OPS --> CLI
  API --> PG
  API --> YAHOO
  API --> LLM
```

**Evidence:** `docker/docker-compose.yml`, `app/main.py`, `app/providers/yahoo/client.py`, `app/args/llm/`

---

## Application layers

```mermaid
flowchart TB
  subgraph api [API layer app/api/v1/]
    R[rankings validation stocks]
    O[observability daily-batch]
    A[analytics research]
  end

  subgraph services [Services app/services/]
    MDS[market_data_service]
    RS[ranking_service]
    SVS[signal_validation_service]
    DBS[daily_batch_service]
    ERS[exit_research_service]
  end

  subgraph domains [Domain engines]
    RANK[app/ranking/]
    VAL[app/validation/]
    ARGS[app/args/]
    SEE[app/stock_setup_evidence/]
    FAC[app/factor_analytics/]
    EXIT[app/workspace_exit_research/]
  end

  subgraph data [Data layer]
    REPO[app/db/repositories/]
    MODELS[app/models/]
  end

  api --> services
  services --> domains
  domains --> REPO
  REPO --> MODELS
  MODELS --> PG[(PostgreSQL)]
```

---

## Batch pipeline architecture

```mermaid
flowchart LR
  subgraph batch [Daily batch app/services/daily_batch_service.py]
    P1[INGEST 12%]
    P2[RANKINGS 20%]
    P3[VALIDATION 11%]
    P4[REGIME_HISTORY 5%]
    P5[REGIME_PERFORMANCE 7%]
    P6[FACTOR_IC 17%]
    P7[RESEARCH_INTELLIGENCE 9%]
    P8[EXIT_RESEARCH 19%]
  end

  P1 --> P2 --> P3 --> P4 --> P5 --> P6 --> P7 --> P8
```

**Planner:** `app/ops/daily_batch/batch_planner.py` — gap detection, `already_current`, reuses `insufficient_data` validation reports.

---

## Validation architecture

```mermaid
flowchart TB
  RR[ranking_run] --> FR[forward returns app/validation/]
  FR --> HM[horizon metrics 5/10/20/60]
  HM --> IC[Spearman/Pearson IC]
  HM --> DEC[decile spreads]
  RR --> REG[regime classifier app/validation/regimes.py]
  REG --> SPLIT[regime-grouped metrics]
  HM --> STATUS{forward bars?}
  STATUS -->|no| INSUF[insufficient_data]
  STATUS -->|yes| OK[completed]
```

**Tail behavior:** Recent as-of dates lack ≥5 forward trading days → `insufficient_data` (`app/validation/constants.py`).

---

## AI / ARGS architecture

```mermaid
flowchart TB
  subgraph deterministic [Deterministic - no LLM]
    RB[ranking engine]
    VB[validation metrics]
    PB[packet builder]
    QRB[quant_research_brief]
    SQE[stock_quality_evidence enricher]
    SEE2[SEE v2 analog search]
  end

  subgraph llm [LLM - research labels only]
    TARC[TARC technical]
    FRC[FRC fundamentals]
    QRC[QRC quant]
    NRCC[NRCC news]
    RC[RC risk]
    CRO[CRO aggregate]
  end

  RB --> PB
  VB --> PB
  SEE2 --> PB
  SQE --> PB
  PB --> CPV[committee_packet_views Phase 2]
  CPV --> TARC & FRC & QRC & NRCC & RC
  TARC & FRC & QRC & NRCC & RC --> CRO
  QRB -.->|default| QRC
  SQEB[qrc_sqe_brief] -.->|ARGS_QRC_USE_SQE=false| QRC
```

**Committee registry:** `app/args/plugins/registry.py` — 5 plugins, no stubs in production registry.

**Workflow:** `app/args/graph/workflow.py` — LangGraph parallel committees → CRO.

---

## Storage model (PostgreSQL)

```mermaid
erDiagram
  stocks ||--o{ market_data : has
  stocks ||--o{ ranking_results : ranked_in
  ranking_runs ||--o{ ranking_results : contains
  ranking_runs ||--o| ranking_validation_reports : validated_by
  research_runs ||--o{ investment_review_packets : produces
  investment_review_packets ||--o{ committee_reviews : reviewed_by
  research_runs ||--o{ cro_reviews : aggregates
  daily_batch_runs ||--o{ daily_batch_run_artifacts : traces
  stocks ||--o{ paper_trades : stub
  stocks ||--o{ portfolio_positions : stub
```

**Migration chain:** 18 versions, head `20260609_0018_see_v2_metrics.py`.

---

## Research modules (read-only analytics)

| Module | Path | Wired to batch? |
|--------|------|-----------------|
| Outcome attribution | `app/outcome_attribution/` | No (scripts) |
| Ranking research | `app/ranking_research/` | No (scripts) |
| Committee effectiveness | `app/args/analytics/committee_effectiveness.py` | No (scripts) |

---

## Security & boundaries

| Boundary | Implementation |
|----------|----------------|
| No LLM ranking | Rankings only in `app/ranking/` |
| No auth middleware | `app/main.py` — open API (**assumption:** trusted network) |
| Frozen ranking/validation math | Documented in handover; golden tests |

---

## Discrepancies

| Item | Note |
|------|------|
| `app/portfolio/`, `app/execution/` | Placeholder packages only — not in architecture diagram as active |
| `docs/architecture.md` | Legacy; prefer code paths cited here |

---

## References

- [03_DOMAIN_MODEL.md](./03_DOMAIN_MODEL.md)
- [05_DATA_PIPELINE_INVENTORY.md](./05_DATA_PIPELINE_INVENTORY.md)
- [06_AI_AND_AGENT_INVENTORY.md](./06_AI_AND_AGENT_INVENTORY.md)
- [`docs/AI/02_ARCHITECTURE/SYSTEM_ARCHITECTURE.md`](../AI/02_ARCHITECTURE/SYSTEM_ARCHITECTURE.md)
