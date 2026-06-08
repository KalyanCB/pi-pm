# ADR-032 Implementation Review

**Date:** 2026-06-05  
**Author:** Principal Architect  
**Status:** APPROVED — proceed with implementation

---

## 1. Current Architecture — Dependency Graph

```
daily_batch_service
  └─► RecommendationService.run_for_ranking_run(ranking_run_id)
        ├─► _build_engine_config()
        │     ├─► _resolve_regime_posture()    → "defensive" | "neutral" | "risk_on"
        │     └─► _resolve_factor_ic()         → float | None
        ├─► _build_regime_snapshot()           → dict (audit)
        ├─► _load_validation()                 → ValidationSummary
        │     └─► RankingValidationRepository.get_by_ranking_run_id()
        │           → None → status="insufficient_data"   ← BLOCKER
        ├─► _load_ranking_rows()               → list[RankingResultRow]
        ├─► _load_exit_signals()               → dict[UUID, ExitSignal]
        └─► engine.run()
              └─► _evaluate() per stock
                    ├─► R-ENTRY-01: rank pool gate
                    ├─► R-ENTRY-02: validation.status == "insufficient_data" → WATCH  ← BLOCKER 1
                    ├─► _conviction_for() → ConvictionResult
                    ├─► R-ENTRY-03: BLOCKED conviction → REJECT
                    ├─► R-ENTRY-05a: LOW conviction → WATCH
                    ├─► R-ENTRY-04: regime_posture == "defensive" → WATCH  ← BLOCKER 2
                    └─► slot limit → BUY
```

---

## 2. Recommendation Flow — Exact Code Paths

**File:** `app/recommendation/engine.py`

```
run()
  line 126: input_hash = _compute_input_hash(...)
  line 130: top20_scores = [r.composite_score for r in ranking_results if r.rank <= top_pool_size]
  line 143: action, lifecycle, reason_codes, conviction = _evaluate(...)

_evaluate()
  line 214: if rr.rank > config.top_pool_size:         # R-ENTRY-01
  line 218: reason_codes.append(REC_REASON_RANK_POOL_TOP20)
  line 221: if validation.status == "insufficient_data":  # R-ENTRY-02  ← BLOCKER 1
  line 222:     reason_codes.append(REC_REASON_VALIDATION_PENDING)
  line 223:     return WATCH
  line 226: conviction = _conviction_for(...)
  line 229: if conviction.band == BLOCKED:              # R-ENTRY-03
  line 234: if conviction.band == LOW:                  # R-ENTRY-05a
  line 239: if config.regime_posture == "defensive":    # R-ENTRY-04  ← BLOCKER 2
  line 244: if buy_count >= config.max_buy_slots:       # R-ENTRY-05b
  line 256: return BUY
```

---

## 3. Two Confirmed BUY Blockers

### Blocker 1 — R-ENTRY-02: `engine.py` line 221

```python
if validation.status == "insufficient_data":
    conviction = _conviction_for(rr, validation, config, top20_scores, "none")
    reason_codes.append(REC_REASON_VALIDATION_PENDING)
    return RecommendationAction.WATCH, None, reason_codes, conviction
```

**Root cause:** `_load_validation()` in `recommendation_service.py` calls
`RankingValidationRepository.get_by_ranking_run_id()`. The `validation_horizon_metrics`
table has **0 rows** because the 20-day forward window has not closed for recent runs.
Every ranking run since 2026-04-29 returns `ValidationSummary(status="insufficient_data")`.

**Fires first.** Even if this were removed, Blocker 2 would still prevent BUYs.

### Blocker 2 — R-ENTRY-04: `engine.py` line 238–241

```python
if config.regime_posture == "defensive":
    reason_codes.append(REC_REASON_REGIME_BLOCK)
    return RecommendationAction.WATCH, None, reason_codes, conviction
```

**Root cause:** `_resolve_regime_posture()` in `recommendation_service.py` line 231:
```python
if "BEAR" in label or "HIGH_VOL" in label:
    return "defensive"
```
Current regime is `BEAR_LOW_VOL` (76 consecutive days since 2026-04-29).
BEAR → "defensive" → R-ENTRY-04 fires.

**This is the correct behavior** — the OOS IC evidence confirms no edge in BEAR regimes
(IC=-0.091, hit_rate=28% for breakout_v1). The regime gate is functioning as designed.

---

## 4. Conviction Score Breakdown — Actual DB Numbers

Current top-pool rank 1, regime=BEAR_LOW_VOL:

| Component    | Weight | Score | Weighted |
|-------------|--------|-------|----------|
| S_rank_quality | 0.26 | ~90  | 23.4     |
| S_validation   | 0.32 | 35   | 11.2     |
| S_ic_factor    | 0.16 | 50   | 8.0      |
| S_regime       | 0.16 | 25   | 4.0      |
| S_exit_health  | 0.10 | 70   | 7.0      |
| **Total**      |      |      | **53.6 → 54 (MEDIUM)** |

`S_validation=35` is fixed at the `insufficient_data` floor (`_score_validation()` line 93).
`S_regime=25` maps from `"defensive"` posture (25.0 per `_score_regime()` line 127).

**With EDGE_PRESENT (BULL regime):**
- S_regime_fit=85 (replacing S_validation) + S_regime=75 (risk_on)
- Total → ~78 (HIGH) → BUY eligible

**With NO_EDGE (BEAR regime):**
- S_regime_fit=15 + S_regime=25 (defensive)
- Total → ~47 (LOW) → blocked by R-ENTRY-05a

---

## 5. Broken `refresh_strategy_regime_performance` Dependency Chain

**File:** `app/db/repositories/regime_analytics_repository.py` lines 82–131

```
refresh_strategy_regime_performance()
  └─► SELECT ... FROM validation_horizon_metrics
        WHERE strategy_name=... AND strategy_version=... AND horizon=...
        GROUP BY regime_label
```

**`validation_horizon_metrics` has 0 rows.**

The dependency chain:
```
daily_batch_service
  └─► regime_analytics_service.refresh_strategy_regime_performance()
        └─► regime_analytics_repository.refresh_strategy_regime_performance()
              └─► validation_horizon_metrics  [EMPTY]
                    └─► upstream: RankingValidationReport.horizon_metrics JSONB
                          populated by: validation pipeline
                          broken because: 20-day forward window never closes
```

Result: `strategy_regime_performance` has only 2 rows with `sample_count=1` each —
both for `BULL_LOW_VOL`, insufficient for any statistical inference.

**Fix:** Bypass `validation_horizon_metrics` entirely. Compute IC directly from
`ranking_results` + `market_data` using walk-forward OOS methodology.

---

## 6. OOS Walk-Forward IC Evidence

| Strategy     | Regime        | avg_IC  | ic_lower_95 | hit_rate | n_days | Edge State      |
|-------------|---------------|---------|-------------|----------|--------|-----------------|
| breakout_v1  | BULL_LOW_VOL  | +0.028  | +0.019      | 60%      | 453    | EDGE_PRESENT    |
| momentum_v1  | BULL_LOW_VOL  | +0.022  | +0.012      | 59%      | 441    | EDGE_PRESENT    |
| breakout_v1  | BEAR_LOW_VOL  | -0.091  | -0.110      | 28%      | 102    | NO_EDGE         |
| momentum_v1  | BEAR_LOW_VOL  | -0.089  | -0.108      | 16%      | 102    | NO_EDGE         |
| breakout_v1  | BEAR_HIGH_VOL | -0.057  | -0.103      | 44%      | 27     | NO_EDGE (low n) |
| momentum_v1  | BEAR_HIGH_VOL | -0.031  | -0.074      | 63%      | 27     | EDGE_WEAK       |
| breakout_v1  | BULL_HIGH_VOL | -0.159  | -0.202      | 7%       | 29     | NO_EDGE         |
| momentum_v1  | BULL_HIGH_VOL | -0.129  | -0.176      | 21%      | 29     | NO_EDGE         |

**Conclusions:**
1. Edge exists only in BULL_LOW_VOL — both strategies, consistent signal
2. All BEAR regimes: strongly negative IC, hit rates well below 50% — no edge
3. HIGH_VOL regimes: consistently negative IC — no edge
4. Current BEAR_LOW_VOL correctly produces WATCH; this is not a bug

---

## 7. ADR-032 Validation

**Is ADR-032 technically sound?** YES.

ADR-032 proposes replacing the broken `S_validation` / R-ENTRY-02 path with a
Regime Conditional Edge Engine (RCEE) that evaluates statistical edge per
(strategy, regime) pair using IC, hit_rate, and sample size thresholds.

**Architecture alignment:**
- Preserves deterministic behavior (all thresholds are config-driven constants)
- Preserves full lineage (gate_results audit trail in RegimeFit)
- No LLM or committee influence on recommendation action
- Backward compatible (regime_fit=None → legacy R-ENTRY-02 fallback)
- Addresses both blockers simultaneously:
  - R-ENTRY-02 replaced by RCEE edge gate (NO_EDGE → WATCH, as correct)
  - R-ENTRY-04 regime posture gate preserved (still fires in BEAR)
  - In BULL_LOW_VOL with EDGE_PRESENT: both gates pass → BUY eligible

**One modification from ADR-032 original:**
Phase 1 backfill via "validation campaigns" is NOT needed.
The DB already contains `ranking_results` (4,168 runs) + `market_data` (521,855 rows, 2021–2026).
Direct IC computation from these tables is faster, more accurate (avoids re-running the
validation pipeline), and eliminates the broken `validation_horizon_metrics` dependency.

---

## 8. Implementation Recommendation

**PROCEED with full ADR-032 implementation.**

Phase order:
1. DB migration + rewrite `refresh_from_market_data`
2. Regime Conditional Edge Engine (RCEE)
3. Engine integration (replace R-ENTRY-02 with RCEE gate)
4. Conviction model update (S_regime_fit replaces S_validation when RCEE available)
5. Freshness controls
6. Exit symmetry (R-EXIT-05)
7. Tests
8. Documentation

**Expected outcome after Phase 3 goes live in BULL regime:**
- BEAR_LOW_VOL (current): RCEE → NO_EDGE → WATCH (same as today, correctly blocked)
- BULL_LOW_VOL (next regime rotation): RCEE → EDGE_PRESENT → BUY eligible

The system will produce its first BUY recommendations upon regime rotation to BULL_LOW_VOL,
backed by 453+ days of OOS evidence with IC lower bound > 0.019.
