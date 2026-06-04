# Database Schema

Synthesized from [DATABASE_SCHEMA.md](../../DATABASE_SCHEMA.md), `app/models/`, and Alembic `migrations/versions/`.

**Migration head:** `20260609_0018` (SEE v2 metrics)  
**Approximate tables:** 35+

---

## Migration timeline

| Revision | Sprint | Highlights |
|----------|--------|------------|
| `20260530_0001` | 1 | Core stocks, rankings, market_data |
| `20260530_0002` | 2 | Universes, ingestion runs |
| `20260530_0003`–`0005` | 3–4.2 | Performance snapshots, validation |
| `20260530_0006` | 6.1 | Full-universe validation |
| `20260530_0007` | 7 | Traceability tables |
| `20260531_0008` | 8.1 | Regime policy |
| `20260601_0009`–`0010` | 8.2 | Factor analytics |
| `20260603_0011`–`0014` | 8.3 | Exit research + phases |
| `20260604_0012` | 8.5 | Research intelligence |
| `20260607_0015` | 8.6 | Daily batch |
| `20260608_0016`–`0017` | ARGS, stock setup research |
| `20260609_0018` | SEE v2 | SEE metrics columns |

---

## Core groups

### Market & universe
- `stocks`, `market_data`, `stock_universes`, `universe_memberships`
- `market_data_ingestion_runs`, `ingestion_batch_runs`

### Ranking & validation
- `ranking_runs`, `ranking_results`, `ranking_performance_snapshots`
- `ranking_validation_reports`
- `full_universe_validation_*`

### Traceability (Sprint 7)
- `ranking_factor_contributions`, `validation_horizon_metrics`, `validation_decile_metrics`
- `run_lineage_records`, `experiment_runs`, `regime_history`, `strategy_regime_performance`

### Analytics sprints
- Regime: `regime_policy_configs`, `regime_policy_decisions`, `regime_backtest_runs`
- Factor: `factor_performance_runs`, `factor_daily_metrics`, `factor_performance_metrics`
- Exit: exit research tables (see migrations 11–14)
- Research intel: sprint 8.5 tables
- Daily batch: `daily_batch_runs`, `daily_batch_run_artifacts`

### ARGS & SEE
- ARGS research runs, packets, committee reviews (migration 16)
- Stock setup research (migration 17)
- SEE v2 metric fields (migration 18)

### Stub / future
- `paper_trades`, `portfolio_positions`, `research_reports`

---

## ORM modules

`app/models/`: `stock.py`, `market_data.py`, `ranking_run.py`, `ranking_result.py`, `ranking_validation_report.py`, `ranking_performance_snapshot.py`, `args.py`, `regime_policy.py`, `factor_analytics.py`, `exit_research.py`, `daily_batch.py`, `stock_setup_research.py`, `platform_traceability.py`, `full_universe_validation.py`, `research_intelligence.py`, `paper_trade.py`, `portfolio_position.py`, `research_report.py`, …

---

## Full reference

Column-level detail: [../../DATABASE_SCHEMA.md](../../DATABASE_SCHEMA.md) (update head revision when editing legacy file).
