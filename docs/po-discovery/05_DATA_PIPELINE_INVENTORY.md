# Data Pipeline Inventory

**Date:** 2026-06-05  
**Scope:** Ingest, batch, ranking, validation, factor, exit, regime, ARGS

---

## Pipeline overview

| Pipeline | Type | Entry points | Output artifacts |
|----------|------|--------------|------------------|
| Market data ingest | Online + batch phase | API, batch P1 | `market_data`, `market_data_ingestion_runs` |
| Universe bootstrap | Ops script | `scripts/recover_universe.py` | `stock_universes`, `universe_memberships` |
| Ranking | Online + batch P2 | API, backtest | `ranking_runs`, `ranking_results` |
| Validation | Online + batch P3 | API | `ranking_validation_reports` |
| Regime history/perf | Batch P4–P5 | batch only | `regime_history`, `strategy_regime_performance` |
| Factor IC | Batch P6 | API backfill | `factor_*` tables |
| Research intelligence | Batch P7 | API generate | `research_intelligence_*` |
| Exit research | Batch P8 | API backfill | `exit_research_*` |
| Full-universe validation | Campaign | API | `full_universe_validation_*` |
| ARGS top-20 | On-demand | API, script | `research_runs`, packets, reviews |
| SEE v2 | On-demand | API | `stock_setup_research_*` |
| Outcome attribution | Offline report | Script | Markdown only |
| Ranking research | Offline report | Script | Markdown only |

---

## 1. Market data ingest

| Item | Detail |
|------|--------|
| Provider | Yahoo — `app/providers/yahoo/client.py` |
| Service | `app/services/market_data_service.py` |
| API | `POST /api/v1/market-data/ingest` |
| Default period | `1y` — `app/core/config.py:19` |
| Batch integration | `DailyBatchPhase.INGEST` — weight 12% |
| Traceability | `ingestion_batch_runs` — Sprint 7 |

**Scripts:** `scripts/reingest_symbols_since.py`, `scripts/test_batch_ingest.py`

---

## 2. Daily batch orchestrator

| Item | Detail |
|------|--------|
| Service | `app/services/daily_batch_service.py` |
| Planner | `app/ops/daily_batch/batch_planner.py` |
| Trading days | `app/ops/daily_batch/trading_day_resolver.py` |
| Evidence windows | `app/ops/daily_batch/evidence_windows.py` |
| API | `/api/v1/ops/daily-batch/*` |
| CLI | `scripts/run_daily_nifty500_batch.py` |

**Phases (ordered):**

1. INGEST (12%)
2. RANKINGS (20%) — both `breakout_v1` and `momentum_v1` per planner specs
3. VALIDATION (11%)
4. REGIME_HISTORY (5%)
5. REGIME_PERFORMANCE (7%)
6. FACTOR_IC (17%)
7. RESEARCH_INTELLIGENCE (9%)
8. EXIT_RESEARCH (19%)

**Idempotency:** `idempotency_key` on batch runs; reuses completed validation with `insufficient_data` status (`batch_planner.py:24`).

**Dry-run:** `--dry-run` exposes `ranking_gaps` without execution.

---

## 3. Ranking pipeline

| Item | Detail |
|------|--------|
| Engine | `app/ranking/engine.py` |
| Strategies | `momentum_v1`, `breakout_v1` — `app/ranking/registry.py` |
| Factors | `app/ranking/factors/` — consolidation_breakout, volume_surge, etc. |
| Normalization | `app/ranking/normalizer.py` |
| Universe filter | `app/universe/filter_engine.py` |
| Default benchmark | `^NSEI` — must be ingested |
| Ops universe | `NIFTY_500` (not config default `PI_PM_CORE`) |

**Backtest replay:** `app/backtest/ranking_replayer.py`, `POST /api/v1/backtest/generate-rankings`

**Research (not prod):** `app/ranking_research/` — calibration, score compression, backtest simulators

---

## 4. Validation pipeline

| Item | Detail |
|------|--------|
| Service | `app/services/signal_validation_service.py` |
| Core | `app/validation/` — forward returns, IC, deciles |
| Horizons | 5, 10, 20, 60 trading days |
| Regimes | Bull/bear × high/low vol — `app/validation/regimes.py` |
| Statuses | `completed`, `insufficient_data`, etc. — `app/validation/constants.py` |

**Tail issue:** Dates from ~2026-05-27 onward return `insufficient_data` until forward bars exist — verified in `docs/dailyruns/04-jun-2026/03-validation.md`.

**Full-universe:** Campaign aggregator — `app/validation/campaign_aggregator.py`

---

## 5. Factor IC pipeline

| Item | Detail |
|------|--------|
| Module | `app/factor_analytics/` |
| Service | `app/services/factor_predictive_power_service.py` |
| Metrics engine | `app/factor_analytics/metrics_engine.py` |
| API | `/api/v1/analytics/factors/*` |
| Backfill script | `scripts/backfill_sprint82_factor_analytics.py` |

---

## 6. Exit research pipeline

| Item | Detail |
|------|--------|
| Module | `app/workspace_exit_research/` |
| Service | `app/services/exit_research_service.py` |
| Simulators | `policy_simulators.py` — fixed hold, rank exit, ATR trail, etc. |
| API | `/api/v1/analytics/exit/*` |
| Backfill | `scripts/backfill_sprint83_exit_research.py` |
| Progress phases | Migration `20260605_0013`, `20260606_0014` |

**Note:** Analytics only — not wired to trade execution.

---

## 7. Regime pipeline

| Item | Detail |
|------|--------|
| Analytics (batch) | Regime history + strategy regime performance |
| Policy engine (research) | `app/regime_policy/engine.py` |
| Replay | `app/regime_policy/replay.py` |
| API | `/api/v1/regime-policy/*`, observability regime endpoints |
| Presets | `scripts/init_regime_policy_presets.py` |

---

## 8. ARGS pipeline

| Item | Detail |
|------|--------|
| Packet builder | `app/args/builders/investment_review_packet_builder.py` |
| Candidate loader | `app/args/loaders/ranking_candidate_loader.py` |
| SQE enricher | `app/args/plugins/stock_quality_evidence.py` |
| SEE enricher | `app/stock_setup_evidence/packet_enricher.py` |
| Workflow | `app/args/graph/workflow.py` |
| CLI | `scripts/run_args_top20.py` |
| Export | `scripts/export_args_research_run.py` |

**Committees:** TARC, FRC, QRC, NRCC, RC → CRO  
**Packet views:** `app/args/committee_packet_views.py` (Phase 2)  
**QRC path:** Default `quant_research_brief`; optional `qrc_sqe_brief` when `ARGS_QRC_USE_SQE=true`

---

## 9. Research reporting pipelines (offline)

| Script | Output |
|--------|--------|
| `generate_outcome_attribution_report.py` | `docs/outcome-attribution-report.md` |
| `generate_ranking_root_cause_reports.py` | 5 ranking research MD files |
| `generate_see_v2_validation_report.py` | `docs/see-v2-validation-report.md` |
| `analyze_committee_effectiveness.py` | Committee independence metrics |
| `qrc_sqe_ab_experiment.py` | QRC A/B comparison |
| `generate_sprint85_research_intelligence.py` | RI reports |

---

## 10. Recovery / ops scripts

| Script | Purpose |
|--------|---------|
| `run_recovery_batch.py` | Platform recovery |
| `run_full_rebuild_from_date.py` | Full rebuild |
| `resume_rebuild_from_validation.py` | Resume from validation |
| `run_research_platform_recovery.py` | Research platform recovery |
| `prune_stale_ranking_runs.py` | Cleanup |
| `backfill_sprint7_traceability.py` | Traceability backfill |

---

## Data lineage (Sprint 7)

`run_lineage_records` links ingestion → ranking → validation → experiments.  
API: `GET /api/v1/observability/lineage/{entity_type}/{entity_id}`

ARGS lineage: `GET /api/v1/research/{run_id}/lineage`

---

## Discrepancies

| Item | Note |
|------|------|
| PLATFORM-HANDOFF lists TRACE in prod pipeline | Traceability is instrumentation via observability, not separate batch phase |
| Ranking v2 calibration | Scripts under `run_calibrated_ranking_backtest.py` — research only |

---

## References

- [02_ARCHITECTURE_CURRENT_STATE.md](./02_ARCHITECTURE_CURRENT_STATE.md)
- [`docs/daily-nifty500-batch-runbook.md`](../daily-nifty500-batch-runbook.md)
- [`docs/AI/06_OPERATIONS/RUNBOOK.md`](../AI/06_OPERATIONS/RUNBOOK.md)
