# Test Scenario Catalog

Representative scenarios by area. File paths under `tests/`.

---

## Ranking

| Scenario | Test location |
|----------|---------------|
| Momentum strategy smoke | `unit/ranking/test_momentum_v1.py` |
| Breakout strategy smoke | `unit/ranking/test_breakout_v1.py` |
| Engine ordering | `unit/ranking/test_engine.py` |
| Normalizer bounds | `unit/ranking/test_normalizer.py` |
| Golden ranking snapshot | `unit/ranking/test_golden_ranking.py` |
| Per-factor math | `unit/ranking/factors/test_*.py` |
| API create + top | `integration/api/test_rankings_api.py` |

---

## Validation

| Scenario | Test location |
|----------|---------------|
| Forward returns | `unit/validation/test_forward_returns.py` |
| Regime classification | `unit/validation/test_regimes.py` |
| Summary aggregation | `unit/validation/test_summary_aggregator.py` |
| Full horizon metrics | `unit/validation/test_full_horizon_metrics.py` |
| Golden validation | `unit/validation/test_golden_validation.py` |
| Validation API | `integration/api/test_validation_api.py` |
| Full-universe API | `integration/api/test_full_universe_validation_api.py` |

---

## ARGS

| Scenario | Test location |
|----------|---------------|
| Packet schema | `unit/args/test_packet_schema.py` |
| Packet builder | `unit/args/test_packet_builder.py` |
| Evidence validator | `unit/args/test_evidence_validator.py` |
| Committee evidence enforcement | `unit/args/test_committee_evidence_enforcement.py` |
| Committee effectiveness metrics | `unit/args/test_committee_effectiveness.py` |
| QRC SQE flag default off | `unit/args/test_qrc_sqe_flag.py` |
| QRC SQE brief when enabled | `unit/args/test_qrc_sqe_brief.py` |
| Quant research brief | `unit/args/test_quant_research_brief.py` |
| SQE on packet | `integration/args/test_packet_sqe.py` |
| Research API | `integration/args/test_research_api.py` |
| Lineage | `integration/args/test_lineage.py`, `test_lineage_chain.py` |

---

## Regime policy

| Scenario | Test location |
|----------|---------------|
| Policy engine decisions | `unit/regime_policy/test_engine.py` |
| Replay backtest | `unit/regime_policy/test_replay.py` |
| Pooled metrics fast path | `unit/regime_policy/test_pooled_metrics.py` |
| Regime API | `integration/api/test_regime_policy_api.py` |

---

## Factor analytics

| Scenario | Test location |
|----------|---------------|
| Metrics engine | `unit/factor_analytics/test_metrics_engine.py` |
| Backfill service | `unit/factor_analytics/test_service_backfill.py` |
| Factor API | `integration/api/test_factor_analytics_api.py` |

---

## Exit research

| Scenario | Test location |
|----------|---------------|
| Policy simulators | `unit/workspace_exit_research/test_policy_simulators.py` |
| Forward returns index | `unit/workspace_exit_research/test_forward_returns_index.py` |
| Exit + research API | `integration/api/test_exit_and_research_api.py` |

---

## SEE

| Scenario | Test location |
|----------|---------------|
| Strategy profiles | `unit/stock_setup_evidence/test_strategy_profiles.py` |
| Similarity / outcomes | `unit/stock_setup_evidence/test_similarity_and_outcomes.py` |
| Stock setup API | `integration/api/test_stock_setup_research_api.py` |

---

## Outcome attribution

| Scenario | Test location |
|----------|---------------|
| Service aggregation | `unit/outcome_attribution/test_service.py` |
| Statistics | `unit/outcome_attribution/test_statistics.py` |

---

## Platform

| Scenario | Test location |
|----------|---------------|
| Health endpoint | `test_health.py` |
| Traceability ensure | `unit/services/test_sprint71_traceability.py` |
| Daily batch planner | `unit/ops/test_daily_batch_planner.py` |
| Market data API | `integration/api/test_market_data_api.py` |
