# ADR-036: Regime-Aware RCEE EDGE_PRESENT Sample Floor

**Status:** Accepted (config-flagged, tunable)
**Date:** 2026-06-18
**Relates to:** ADR-032 (RCEE / Live Entry-Timing Validation Gate)
**Code:** `app/recommendation/regime_edge_engine.py`, `app/services/recommendation_service.py`, `app/core/config.py`

---

## Context

RCEE (ADR-032) decides whether a strategy may issue BUY *on the latest day* using the
historical `(strategy × regime)` edge in `strategy_regime_performance` — **not** that
day's own forward validation. `EDGE_PRESENT` (BUY-eligible) requires ALL of:

- `ic_lower_95 ≥ 0.010` (lower bound of the 95% CI on rank IC)
- `hit_rate ≥ 0.55`
- `sample_count ≥ 60`

**Problem observed:** in the current `BEAR_LOW_VOL` regime, the daily feed was 100%
WATCH. Diagnosis (live data, horizon 20):

| Strategy (BEAR_LOW_VOL) | ic_lower_95 | hit_rate | n | EdgeState | Failing gate |
|---|---|---|---|---|---|
| breakout_v1 | −0.098 | 0.287 | 172 | NO_EDGE | IC, HIT (real) |
| momentum_v1 | −0.079 | 0.280 | 190 | NO_EDGE | IC, HIT (real) |
| low_vol_v1 | −0.011 | 0.446 | 175 | NO_EDGE | IC, HIT (real) |
| **reversal_v1** | **+0.072** | **0.808** | **53** | **EDGE_WEAK** | **N only (53 < 60)** |

`reversal_v1` — the strategy designed for bear-low-vol — has **genuinely strong,
statistically-significant edge** (IC lower bound +0.072, hit-rate 81%) but was demoted
to `EDGE_WEAK` (→ WATCH) **purely because it was 7 samples short of the flat 60-day
floor**. Bear/high-vol regimes are structurally rare (over 5 years: BULL_LOW_VOL 764
days vs BEAR_LOW_VOL 200, BEAR_HIGH_VOL 47, BULL_HIGH_VOL 31), so they cannot
accumulate 60 validated regime-days as readily as the dominant bull regime — the flat
floor systematically suppresses rare-regime edge.

### Why this is over-conservative, not unsafe

`ic_lower_95` is the **lower bound of the 95% confidence interval** on IC — it already
penalizes small samples (a thin sample widens the CI and lowers the bound). A strategy
whose `ic_lower_95` clears `0.010` at n=53 has *already* passed a sample-aware
significance test. The separate `sample_days ≥ 60` gate therefore **double-counts**
sample uncertainty for the IC dimension, and for rare regimes it does so at a level
they can rarely reach.

## Decision

Make the `EDGE_PRESENT` sample floor **regime-aware**:

- Common regimes (default, e.g. `BULL_LOW_VOL`): floor **60** (unchanged).
- Rare regimes (`BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `BULL_HIGH_VOL`): floor **45**.

Implemented as `RCEEConfig.edge_present_sample_days_by_regime` (per-regime override of
`edge_present_sample_days`), resolved by `RCEEConfig.sample_floor_for(regime_label)`.
The IC and hit-rate gates are **unchanged** — only the sample floor moves, and only for
rare regimes, so genuinely-weak strategies stay blocked.

### Settings (tunable, `app/core/config.py`)

```
rcee_edge_present_sample_days: int = 60                       # common-regime floor
rcee_rare_regime_sample_days: int = 45                        # rare-regime floor
rcee_rare_regimes: str = "BEAR_LOW_VOL,BEAR_HIGH_VOL,BULL_HIGH_VOL"
```

`_load_regime_fit` builds the per-regime map from these and passes it into `RCEEConfig`.

## Consequences

**Effect (verified on live data, 2026-06-17, BEAR_LOW_VOL):**
- `reversal_v1` flips `EDGE_WEAK → EDGE_PRESENT` → the latest-day feed produces **10
  BUY** (HIGH conviction, ranks 1–8) where it was previously all-WATCH.
- The other three bear strategies remain `NO_EDGE` (negative IC) — correctly blocked.
- `BEAR_HIGH_VOL` / `BULL_HIGH_VOL`: no strategy currently has positive IC there, so
  nothing flips; and `reversal_v1` in `BULL_HIGH_VOL` (n=28) stays blocked (28 < 45).
- `BULL_LOW_VOL` (floor still 60): unchanged — breakout_v1 (n=748) and momentum_v1
  (n=763) remain `EDGE_PRESENT`.

So the **only** behavioral change is unblocking the one rare-regime strategy whose edge
was already statistically significant. Latest-day BUY is restored without weakening the
significance bar (IC / hit-rate untouched) or the common-regime floor.

**Positive**
- Fixes the "always WATCH on the daily feed in bear regimes" problem at its true cause.
- Fully tunable via Settings; no recompiled thresholds.
- IC/hit gates unchanged → no increase in false positives from weak edge.

**Negative / risks**
- A 45-sample floor carries marginally wider CIs than 60; mitigated by the unchanged
  `ic_lower_95 ≥ 0.010` gate (which already encodes sample size).
- Recommendation runs are idempotent per ranking run; existing frozen WATCH runs do
  **not** auto-upgrade. They must be regenerated to pick up the new floor (done for the
  latest reversal_v1 run; future daily runs apply it natively once the API is rebuilt).

## Alternatives considered

1. **Lower the flat floor 60 → 50 for all regimes** — simpler, but needlessly loosens
   the data-rich bull regime where 60 is comfortably met. Rejected.
2. **Drop the EDGE_PRESENT sample gate entirely, rely on `ic_lower_95`** — cleanest in
   theory, but removes the floor for *all* regimes including thin-but-noisy ones.
   Rejected as too broad for one fix.
3. **Wait for the sample to reach 60 naturally** — the BUY would appear ~7 bear-low-vol
   sessions later. Rejected: defeats the latest-day requirement, and the edge is already
   significant.
