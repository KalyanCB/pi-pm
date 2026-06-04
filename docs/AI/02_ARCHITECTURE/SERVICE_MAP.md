# Service Map

Orchestration lives in `app/services/` unless noted.

---

## Production services

| Service | Module | Responsibility |
|---------|--------|----------------|
| MarketDataService | `market_data_service.py` | Ingest, cache, read bars |
| StockService | `stock_service.py` | Stock CRUD |
| RankingService | `ranking_service.py` | Run strategies, persist runs |
| SignalValidationService | `signal_validation_service.py` | Per-run validation compute |
| FullUniverseValidationService | (validation package + service) | Campaign backfill |
| ObservabilityService | `observability_service.py` | Ingestion/ranking/validation views |
| TraceabilityService | `platform_traceability` paths | Score reconstruction, lineage |
| RegimePolicyService | `regime_policy_service.py` | Configs, evaluate, backtest |
| FactorAnalyticsService | `factor_analytics_service.py` | IC backfill, reports |
| ExitResearchService | `exit_research_service.py` | Phased exit backfill |
| ResearchIntelligenceService | `research_intelligence_service.py` | Executive summaries |
| DailyBatchService | `daily_batch_service.py` | NIFTY 500 orchestration |
| ArgsResearchService | `args_research_service.py` | Packet build, committee workflow |
| StockSetupResearchService | `stock_setup_research_service.py` | SEE generation |
| UniverseBootstrapService | `universe_bootstrap_service.py` | Seed memberships |
| UniverseCoverageService | `universe_coverage_service.py` | Coverage checks |

---

## Domain engines (not thin services)

| Engine | Package |
|--------|---------|
| RankingEngine | `app/ranking/engine.py` |
| Validation stats | `app/validation/` |
| Regime replay | `app/regime_policy/replay.py` |
| SEE engine | `app/stock_setup_evidence/` |
| Outcome attribution | `app/outcome_attribution/service.py` |
| ARGS graph / committees | `app/args/` |

---

## API → service mapping

| Router prefix | Primary service |
|---------------|-----------------|
| `/stocks` | StockService |
| `/market-data` | MarketDataService |
| `/rankings` | RankingService |
| `/validation` | SignalValidationService, FullUniverseValidationService |
| `/observability` | ObservabilityService, TraceabilityService |
| `/regime-policy` | RegimePolicyService |
| `/analytics/factors` | FactorAnalyticsService |
| `/analytics/exit` | ExitResearchService |
| `/analytics/research-intelligence` | ResearchIntelligenceService |
| `/research` | ArgsResearchService |
| `/research/stock-setup` | StockSetupResearchService |
| `/ops/daily-batch` | DailyBatchService |
| `/backtest` | Backtest ranking replayer |

---

## Dependency injection

FastAPI `Depends(get_*_service)` factories in `app/api/deps.py` (or per-router deps). Scripts use `scripts/pipm_service_factory.py`.
