# Database Audit Report

**Audit:** AUDIT-01  
**Date:** 2026-06-05  
**ORM:** SQLAlchemy 2.x  
**Migrations:** Alembic — 28 revision files in `migrations/versions/`  
**Models:** 55 SQLAlchemy models in `app/models/`

---

## Executive Summary

| Check | Result |
|-------|--------|
| Models vs migrations alignment | **ALIGNED** — 58 tables from migrations match model definitions |
| Orphan models (no migration) | **NONE found** |
| Unused tables (no repository access) | **2 suspected** — `research_reports` (legacy), possibly stale |
| Missing migrations | **NONE** — head at `20260610_0026_unified_execution` |
| Migration drift | **NONE detected** — single merge head `14de8dccf1e0` |
| Dead schema | **PARTIAL** — `research_reports` legacy; global NAV/recon tables |
| Multi-tenant gaps | **CRITICAL** — 6 tables lack `portfolio_id` |

---

## Table Inventory (58 tables)

### Core / Universe (Sprint 1–2)
`stocks`, `market_data`, `stock_universes`, `universe_memberships`, `market_data_ingestion_runs`

### Ranking / Validation (Sprint 3–6)
`ranking_runs`, `ranking_results`, `ranking_performance_snapshots`, `ranking_validation_reports`, `ranking_factor_contributions`, `validation_horizon_metrics`, `validation_decile_metrics`, `full_universe_validation_campaigns`, `full_universe_validation_runs`, `full_universe_validation_metrics`, `full_universe_validation_deciles`

### Platform Traceability (Sprint 7)
`ingestion_batch_runs`, `ingestion_batch_symbol_runs`, `run_lineage_records`, `experiment_runs`, `regime_history`, `strategy_regime_performance`

### Regime / Analytics (Sprint 8.1–8.5)
`regime_policy_configs`, `regime_policy_decisions`, `regime_backtest_runs`, `factor_performance_runs`, `factor_daily_metrics`, `factor_performance_metrics`, `exit_research_runs`, `exit_research_policy_metrics`, `exit_research_alpha_decay_points`, `research_intelligence_runs`, `research_intelligence_reports`

### Phase 2 — Recommendation (0019–0020)
`recommendation_configs`, `recommendation_runs`, `recommendation_results`, `recommendation_approvals`, `recommendation_outcomes`

### Phase 2 — Portfolio (0021–0022)
`portfolio_configs`, `portfolio_positions`, `portfolio_nav_history`, `portfolio_cash_ledger`, `portfolio_reconciliation_reports`, `portfolio_exit_recommendations`, `paper_trades`

### Ops / ARGS (0015–0017)
`daily_batch_runs`, `daily_batch_run_artifacts`, `prompt_versions`, `llm_execution_records`, `research_runs`, `investment_review_packets`, `committee_reviews`, `cro_reviews`, `governance_research_reports`, `governance_research_report_evidence`, `stock_setup_research`, `stock_setup_research_metrics`

### Auth / Execution / Copilot (0024–0026)
`users`, `roles`, `permissions`, `role_permissions`, `portfolios`, `user_portfolio_memberships`, `user_preferences`, `refresh_tokens`, `copilot_query_logs`, `execution_orders`, `execution_events`, `execution_configs`, `execution_audit`

### Legacy
`research_reports` — initial schema; superseded by ARGS governance reports

---

## Model → Repository Mapping

| Model | Repository | Used in service | Status |
|-------|------------|-----------------|--------|
| RankingRun/Result | `ranking_*_repository.py` | RankingService | Active |
| Recommendation* | `recommendation_repository.py` | RecommendationService | Active |
| PortfolioPosition/Config | portfolio repos | PortfolioService | Active |
| PaperTrade | via PaperTradeService | ExecutionAdapter | Active — **no portfolio_id** |
| PortfolioNavHistory | nav service | PortfolioNavService | Active — **global** |
| PortfolioReconciliationReport | recon service | ReconciliationService | Active — **global** |
| CashLedger | ledger service | PortfolioService | Active — **global** |
| ExitRecommendation | exit monitor | ExitMonitorService | Active — **global** |
| ExecutionOrder/Event/Audit | execution_repository | ExecutionService | Active — scoped |
| CopilotQueryLog | copilot service | CopilotService | Active |
| ResearchReport | — | **No active service** | **ORPHAN / DEAD** |
| RefreshToken | auth_repository | AuthService | Active |

---

## Relationships & Indexes

### Key FK chains (lineage)
```
ranking_runs → ranking_results → recommendation_runs → recommendation_results
  → recommendation_approvals → execution_orders → paper_trades → portfolio_positions
```

### Indexes verified
- `ix_execution_orders_portfolio_status` on `(portfolio_id, status)` — `execution.py:54`
- `ix_user_portfolio_memberships_portfolio` — `auth.py:114`
- `uq_user_portfolio_membership` on `(user_id, portfolio_id)` — `auth.py:112`

### Problematic constraints
- `PortfolioNavHistory`: `unique(as_of_date)` — **single-tenant assumption** (`portfolio_analytics.py`)
- `paper_trades`: no `portfolio_id` — cannot isolate trades per tenant

---

## Multi-Tenant Column Audit

| Table | `portfolio_id` | Required by ADR-027 | Status |
|-------|----------------|---------------------|--------|
| `portfolio_configs` | ✓ (nullable FK) | Yes | OK |
| `portfolio_positions` | ✓ (nullable FK) | Yes | OK |
| `execution_orders` | ✓ | Yes | OK |
| `execution_configs` | ✓ | Yes | OK |
| `paper_trades` | ✗ | Yes | **GAP** |
| `portfolio_nav_history` | ✗ | Yes | **GAP** |
| `portfolio_cash_ledger` | ✗ | Yes | **GAP** |
| `portfolio_reconciliation_reports` | ✗ | Yes | **GAP** |
| `portfolio_exit_recommendations` | ✗ | Yes | **GAP** |
| `recommendation_*` | ✗ | Implicit global | Acceptable for single-pilot |
| `ranking_*` | ✗ | N/A (research) | By design |

---

## Migration Timeline

| Revision | Date prefix | Purpose |
|----------|-------------|---------|
| 0001 | 20260530 | Initial schema |
| 0002–0007 | 20260530–31 | Universe, ranking, validation, traceability |
| 0008–0012 | 20260531–0604 | Regime, factors, exit, RI |
| 0015–0017 | 20260607–08 | Daily batch, ARGS, SEE v2 |
| 0019–0022 | 20260606 | Recommendation + portfolio |
| 0024–0026 | 20260609–10 | Copilot, auth, execution |
| merge | 14de8dccf1e0 | Portfolio + committee heads |

**Drift check:** No pending model changes without migration detected via grep of `__tablename__` vs migration `op.create_table`.

---

## Dead / Legacy Schema

| Item | Evidence | Recommendation |
|------|----------|----------------|
| `research_reports` | `model_id` default `"stub"`; no service imports | Deprecate or document |
| `/research/*` API | Uses `research_runs` not `research_reports` | `research_reports` likely dead |
| Committee stub plugins | Not in production registry | Test utilities only |

---

## Repository Coverage

All active domain models have corresponding repositories under `app/db/repositories/` except:
- `ResearchReport` — no repository
- Some analytics snapshot tables written directly in services

---

*Evidence: `app/models/*.py`, `migrations/versions/*.py`, `app/db/repositories/`.*
