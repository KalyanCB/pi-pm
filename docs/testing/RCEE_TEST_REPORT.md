# RCEE Test Report

**Date:** 2026-06-05  
**ADR:** 032  
**Total new tests:** 32 (11 RCEE + 21 engine RCEE + 3 conviction scorer)  
**All tests pass:** 62/62

---

## New Test Files

### `tests/unit/recommendation/test_regime_edge_engine.py` — 11 tests

| Test | Description |
|------|-------------|
| `test_edge_present_all_gates_pass` | ic_lower_95=0.02, hit_rate=0.60, sample_days=100 → EDGE_PRESENT |
| `test_no_edge_ic_below_threshold` | ic_lower_95=-0.05 → NO_EDGE regardless of other gates |
| `test_edge_weak_marginal_ic` | ic_lower_95=0.005, hit_rate=0.52, sample_days=40 → EDGE_WEAK |
| `test_no_edge_insufficient_samples` | Good IC but only 10 days → NO_EDGE |
| `test_unknown_when_no_row` | None input → UNKNOWN, all fields None/empty |
| `test_gate_results_audit_trail` | gate_results populated with all 6 expected gate names, all bool values |
| `test_threshold_config_captured` | threshold_config reflects custom RCEEConfig values |
| `test_no_edge_when_hit_rate_too_low` | hit_rate=0.40 → NO_EDGE, both hit_rate gates False |
| `test_edge_present_gate_results_all_true` | EDGE_PRESENT → all 3 edge_present gates True |
| `test_unknown_returns_empty_gate_results` | None row → gate_results={} |
| `test_none_ic_lower_treated_as_negative_inf` | ic_lower_95=None → treated as -inf → NO_EDGE |

### `tests/unit/recommendation/test_engine_rcee.py` — 21 tests

| Test | Description |
|------|-------------|
| `test_no_edge_produces_watch_with_regime_no_edge_reason` | NO_EDGE → WATCH + REGIME_NO_EDGE for top-pool stocks |
| `test_edge_weak_produces_watch_with_low_expectancy_reason` | EDGE_WEAK → WATCH + LOW_EXPECTANCY |
| `test_edge_present_allows_buy_path` | EDGE_PRESENT + risk_on → BUY eligible |
| `test_fallback_to_legacy_when_no_regime_fit` | regime_fit=None + insufficient_data → WATCH (legacy R-ENTRY-02) |
| `test_defensive_regime_still_blocks_even_with_edge_present` | EDGE_PRESENT but defensive → WATCH (R-ENTRY-04 still fires) |
| `test_confidence_high_on_large_sample` | sample_days=250, EDGE_PRESENT → HIGH_CONFIDENCE |
| `test_confidence_validated_on_medium_sample` | sample_days=80, EDGE_PRESENT → VALIDATED |
| `test_confidence_unknown_without_regime_fit` | No regime_fit → BUY confidence=UNKNOWN |
| `test_conviction_uses_regime_fit_score` | EDGE_PRESENT → conviction.validation=85.0, scorer=regime_fit |
| `test_no_edge_conviction_uses_s15` | NO_EDGE → conviction.validation=15.0 |
| `test_legacy_conviction_uses_validation_scorer` | regime_fit=None → scorer=legacy_validation |
| `test_deterministic_replay_with_regime_fit` | Same inputs → same hash and results (determinism) |
| `test_edge_state_in_input_hash` | Different edge states → different input hashes |
| `test_edge_degraded_exit_signal_triggers_exit_approved` | edge_degraded=True → EXIT_APPROVED + EDGE_DEGRADED |
| `test_freshness_check_stale_age` | age > max_age_days → STALE_AGE |
| `test_freshness_check_rank_exited_pool` | Stock at rank 25 → RANK_EXITED_POOL |
| `test_freshness_check_regime_edge_lost` | NO_EDGE regime_fit → REGIME_EDGE_LOST |
| `test_freshness_check_all_pass` | Fresh stock, EDGE_PRESENT → is_fresh=True |

### Updates to `tests/unit/recommendation/test_conviction_scorer.py` — 3 new tests

| Test | Description |
|------|-------------|
| `test_regime_fit_edge_present_raises_conviction` | EDGE_PRESENT gives higher score than insufficient_data |
| `test_regime_fit_no_edge_lowers_conviction` | NO_EDGE gives lower score than insufficient_data |
| `test_legacy_path_unchanged_when_no_regime_fit` | regime_fit=None → legacy scorer, no regime_fit fields |

**Updated existing test:** `test_components_five_keys_no_committee` — expected keys set updated
to include `validation_scorer_used` and `regime_fit_edge_state` (ADR-032 audit fields).

---

## Existing Tests (all pass, unchanged behavior)

All 30 original tests in `test_engine.py` and `test_conviction_scorer.py` continue to pass.
Key backward-compat tests:

| Test | Verifies |
|------|----------|
| `test_insufficient_data_caps_at_watch` | Legacy R-ENTRY-02 still fires when regime_fit=None |
| `test_insufficient_data_caps_band` | Legacy S_validation=35 floor still works |
| `test_defensive_regime_blocks_buy` | R-ENTRY-04 unchanged |
| `test_deterministic_replay` | Hash determinism preserved (new optional edge_state param defaults to None) |

---

## Coverage Summary

| Module | Tests | Areas covered |
|--------|-------|---------------|
| `regime_edge_engine.py` | 11 | All 3 edge states, UNKNOWN, gate audit trail, threshold config, edge cases (None IC) |
| `engine.py` (RCEE paths) | 21 | R-ENTRY-02-RCE (3 states), fallback, R-ENTRY-04 still fires, confidence derivation, conviction integration, determinism, R-EXIT-05, freshness checks |
| `conviction_scorer.py` (ADR-032) | 3 | S_regime_fit mapping (EDGE_PRESENT/NO_EDGE), legacy fallback |

**All 62 tests pass in 0.07s.**
