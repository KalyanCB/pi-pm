# RCEE Design Document

**Component:** Regime Conditional Edge Engine (RCEE)  
**ADR:** 032  
**File:** `app/recommendation/regime_edge_engine.py`

---

## Purpose

Replace the broken `validation_horizon_metrics`-dependent R-ENTRY-02 gate with a
statistically grounded, fully auditable edge gate that evaluates whether a strategy
has demonstrated positive OOS IC in the current market regime.

---

## Inputs

| Input | Source | Description |
|-------|--------|-------------|
| `strategy_name` | `RankingRun.strategy_name` | e.g. "breakout_v1" |
| `strategy_version` | `RankingRun.strategy_version` | e.g. "1.0.0" |
| `regime_label` | `RankingRun.regime_label` | e.g. "BULL_LOW_VOL" |
| `horizon` | Config | Default 20 (trading days) |
| `StrategyRegimePerformance` row | DB | Populated by `refresh_from_market_data` |
| `RCEEConfig` | Config dataclass | All thresholds, config-driven |

---

## Outputs: `RegimeFit`

| Field | Type | Description |
|-------|------|-------------|
| `strategy_name` | str | Strategy identifier |
| `regime_label` | str | Regime identifier |
| `avg_ic` | float\|None | Average daily IC (Spearman) |
| `ic_lower_95` | float\|None | Lower 95% confidence bound on IC |
| `hit_rate` | float\|None | Fraction of days with IC > 0 |
| `expectancy` | float\|None | Avg top-20 forward return |
| `expectancy_after_costs` | float\|None | expectancy − 10bps |
| `sample_days` | int | Number of OOS days in estimate |
| `edge_state` | EdgeState | EDGE_PRESENT \| EDGE_WEAK \| NO_EDGE \| UNKNOWN |
| `threshold_config` | dict | Exact thresholds used (auditability) |
| `gate_results` | dict[str,bool] | Each gate → passed/failed (auditability) |

---

## Edge State Decision Tree

```
if row is None:
    → UNKNOWN

ic_lower = row.ic_lower_95 or -∞
hr = row.hit_rate or 0
n = row.sample_count

EDGE_PRESENT gates:
  gate_ic:  ic_lower >= 0.010
  gate_hr:  hr >= 0.55
  gate_n:   n >= 60

if gate_ic AND gate_hr AND gate_n:
    → EDGE_PRESENT

EDGE_WEAK gates:
  gate_ic_w: ic_lower >= 0.000
  gate_hr_w: hr >= 0.50
  gate_n_w:  n >= 30

if gate_ic_w AND gate_hr_w AND gate_n_w:
    → EDGE_WEAK

else:
    → NO_EDGE
```

---

## Threshold Values and Rationale

### EDGE_PRESENT

| Threshold | Value | Rationale |
|-----------|-------|-----------|
| `ic_lower_95` | 0.010 | OOS evidence: BULL_LOW_VOL ic_lower=+0.019; 0.010 is conservative floor |
| `hit_rate` | 0.55 | OOS BULL_LOW_VOL: 60% hit rate; 0.55 provides small buffer |
| `sample_days` | 60 | Minimum for stable statistics; 2-3 months of daily IC observations |

### EDGE_WEAK

| Threshold | Value | Rationale |
|-----------|-------|-----------|
| `ic_lower_95` | 0.000 | IC lower bound just above zero — marginal positive expectation |
| `hit_rate` | 0.50 | IC positive more often than not |
| `sample_days` | 30 | ~6 weeks minimum |

### Confirmed NO_EDGE regimes (from OOS evidence)

| Regime | avg_IC | ic_lower_95 | hit_rate | Edge State |
|--------|--------|-------------|----------|------------|
| BEAR_LOW_VOL | -0.091 | -0.110 | 28% | NO_EDGE |
| BEAR_HIGH_VOL | -0.057 | -0.103 | 44% | NO_EDGE |
| BULL_HIGH_VOL | -0.159 | -0.202 | 7% | NO_EDGE |

---

## Conviction Formula Before/After

### Before (legacy)

```
conviction = 0.26*S_rank + 0.32*S_validation + 0.16*S_ic + 0.16*S_regime + 0.10*S_exit

S_validation:
  insufficient_data → 35
  ic_20d <= 0       → 20
  ic_20d <= 0.05    → 50
  ic_20d > 0.05     → 80 (+10 spread bonus)
```

### After (ADR-032, when regime_fit_edge_state is provided)

```
conviction = 0.26*S_rank + 0.32*S_regime_fit + 0.16*S_ic + 0.16*S_regime + 0.10*S_exit

S_regime_fit:
  EDGE_PRESENT  → 85
  EDGE_WEAK     → 50
  NO_EDGE       → 15
  UNKNOWN/None  → 35  (same as insufficient_data floor)
```

**Weights unchanged.** Only the sub-scorer for the 0.32-weight slot changes.  
Legacy path intact when `regime_fit_edge_state=None`.

---

## Integration Points

| Component | Integration |
|-----------|-------------|
| `EngineConfig.regime_fit` | Set by `RecommendationService._load_regime_fit()` |
| `engine._evaluate()` | R-ENTRY-02-RCE gate checks `config.regime_fit.edge_state` |
| `engine._conviction_for()` | Passes `regime_fit.edge_state.value` to `ConvictionInputs` |
| `conviction_scorer.score()` | Routes to `_score_regime_fit()` or `_score_validation()` based on field |
| `RecommendationResult.recommendation_confidence` | Persisted for each result |
| `RecommendationRun.regime_snapshot` | RCEE gate_results + ic_lower_95 + sample_days included |
| `ExitSignal.edge_degraded` | Populated by `_load_exit_signals()` from current `regime_fit` |
| `check_recommendation_freshness()` | Checks regime_fit.edge_state at approval time |

---

## Auditability Guarantees

1. Every gate is separately recorded in `gate_results` (not a composite)
2. `threshold_config` captures the exact RCEEConfig values applied
3. `computed_from='market_data_direct'` on every DB row written by the new method
4. `regime_snapshot` in `recommendation_runs` includes full RCEE state
5. `recommendation_confidence` on every result row traces back to sample_days evidence
6. No LLM, no committee input affects edge_state — pure statistical computation
