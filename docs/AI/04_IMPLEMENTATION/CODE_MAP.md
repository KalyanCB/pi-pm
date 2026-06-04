# Code Map

Quick navigation from feature → file.

---

## API routers (`app/api/v1/`)

| File | Prefix |
|------|--------|
| `health.py` | `/health` |
| `stocks.py` | `/stocks` |
| `market_data.py` | `/market-data` |
| `rankings.py` | `/rankings` |
| `backtest.py` | `/backtest` |
| `validation.py` | `/validation` |
| `observability.py` | `/observability` |
| `regime_policy.py` | `/regime-policy` |
| `factor_analytics.py` | `/analytics/factors` |
| `exit_analytics.py` | `/analytics/exit` |
| `research_intelligence.py` | `/analytics/research-intelligence` |
| `research.py` | `/research` |
| `stock_setup_research.py` | `/research/stock-setup` |
| `daily_batch.py` | `/ops/daily-batch` |

Mount: `app/api/router.py`

---

## Schemas (`app/schemas/`)

| Module | Used by |
|--------|---------|
| `ranking.py` | rankings, backtest |
| `validation.py` | validation |
| `stock.py`, `market_data.py` | stocks, ingest |
| `regime_policy.py` | regime-policy |
| `factor_analytics.py` | factor analytics |
| `exit_research.py` | exit analytics |
| `research_intelligence.py` | research-intelligence |
| `args.py` | research |
| `daily_batch.py` | daily-batch |
| `observability.py` | observability |
| `backtest.py` | backtest |
| `common.py` | shared types |

---

## ARGS (`app/args/`)

| Area | Files |
|------|-------|
| Workflow | `workflow.py`, `graph.py` |
| Packet | `packet_builder.py`, `packet_schema.py` |
| Committees | `tarc.py`, `qrc.py`, `frc.py`, `nrcc.py`, `rc.py`, `cro.py` |
| QRC flag | `qrc.py` + `config.args_qrc_use_sqe` |
| Evidence | `committee_evidence_enforcement.py`, `committee_packet_views.py` |
| LLM | `llm_registry.py`, `committee_llm_base.py` |

---

## Ranking (`app/ranking/`)

`engine.py`, `strategies/`, `factors/`, `normalizer.py`

---

## Scripts (frequent)

| Script | Function |
|--------|----------|
| `run_daily_nifty500_batch.py` | Daily ops |
| `run_args_top20.py` | ARGS |
| `generate_ranking_root_cause_reports.py` | 5 reports |
| `backfill_sprint7_traceability.py` | Traceability |

Full list: [09_HANDOVER/DOCUMENT_INVENTORY.md](../09_HANDOVER/DOCUMENT_INVENTORY.md).
