# Entity Relationship Guide

---

## Core path (ranking day)

```mermaid
erDiagram
    stocks ||--o{ market_data : has
    stock_universes ||--o{ universe_memberships : contains
    stocks ||--o{ universe_memberships : member
    ranking_runs ||--o{ ranking_results : produces
    stocks ||--o{ ranking_results : scored
    ranking_runs ||--o| ranking_validation_reports : validates
    ranking_runs ||--o{ ranking_performance_snapshots : tracks
```

---

## Traceability extension

```mermaid
erDiagram
    ranking_runs ||--o{ ranking_factor_contributions : explains
    ranking_runs ||--o{ validation_horizon_metrics : metrics
    ranking_runs ||--o{ run_lineage_records : lineage
    market_data_ingestion_runs ||--o{ ingestion_batch_runs : batches
```

---

## Daily batch

```mermaid
erDiagram
    daily_batch_runs ||--o{ daily_batch_run_artifacts : links
    daily_batch_run_artifacts }o--|| ranking_runs : optional
    daily_batch_run_artifacts }o--|| ranking_validation_reports : optional
```

---

## ARGS

```mermaid
erDiagram
    ranking_runs ||--o{ args_research_runs : inputs
    args_research_runs ||--|| investment_review_packets : has
    args_research_runs ||--o{ committee_reviews : produces
```

(Exact table names in migration `20260608_0016` — see `app/models/args.py`.)

---

## Analytics (read-mostly)

| Parent | Children |
|--------|----------|
| `factor_performance_runs` | `factor_daily_metrics`, `factor_performance_metrics` |
| Exit research run | Phase progress + report aggregates |
| `full_universe_validation_campaigns` | runs, metrics, deciles |

---

## Foreign key discipline

- UUID PKs throughout
- `stock_id` CASCADE on market data
- JSONB for `score_components`, `horizon_metrics`, `plan_snapshot`, packet extensions

Full ER diagram: [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) and [../../DATABASE_SCHEMA.md](../../DATABASE_SCHEMA.md).
