# Exit Engine v2 — A Research Design
### Reframing the exit problem as exposure management under unpredictable failure

*Senior quantitative research note · PI-PM · deterministic, OHLCV-only, no ML / no LLM / no future leakage*

---

## Headline thesis

> **The current engine's flaw is not the score. It's the *action*.** The 4-factor score is roughly
> adequate at measuring weakness. What is broken is that the engine responds to weakness with a
> **binary, raw-percentage, position-symmetric** trailing stop. The recoverable upside lives almost
> entirely in the action layer — **volatility-normalization, partial scaling, and persistence-asymmetry**
> — *not* in new score factors. Most of the candidate features are rejected here, on evidence.

All empirical claims below are grounded in stress-tests run on PI-PM's own data (the V20–V22 runs and
the breakout_v2 ranking/market-data panels), not on generic priors.

---

## 1. Critical review of the current engine

`E = M + K + S + R`, then a drag-from-peak trailing band by score tier
(≥80 exit · 60-79 → 12% · 40-59 → 25% · <40 → 40%).

Four structural defects, in order of severity:

**(a) The action is in raw percentage, not volatility units — the single biggest defect.**
A 40% drag tolerance treats a 4%/day-ATR multibagger and a 1.2%/day-ATR blue chip identically.
For the calm stock 40% is a catastrophe already missed; for the volatile winner 40% is one normal
breath and you clip it. A fixed-% trailing stop is **dimensionally wrong** — drag must be measured in
ATR multiples. This mis-calibrates every exit by the cross-sectional ATR dispersion (large in a
small/mid-cap book, ~3-4×).

**(b) The exit is binary.** Every decision is hold-100% or sell-100%. This forces the central tension —
*improve the average trade vs. preserve the fat tail* — into an all-or-nothing choice that is
**structurally unresolvable in binary form**. The data shows it directly: 43% win rate, 23 multibaggers
carrying the entire +14.1% CAGR. The distribution is so right-skewed that the binary exit optimizes the
wrong moment of the distribution.

**(c) M (momentum percentile) is a lagging, relative signal masquerading as a state variable.**
Measured: stocks ran **+13.9% on average *after* momentum_v3 "faded"** below the hold threshold.
Momentum is a *cross-sectional rank* — a name can fall in the rank while still trending absolutely
(others ran harder). M fires exit pressure on *relative* deceleration, which in a bull tape is mostly
noise. It is the dominant factor and the most theoretically suspect.

**(d) Hidden correlation (M↔S) and a theoretically inverted R.**
- **M ⟂ S is false.** A stock below its 200-SMA almost always has low momentum percentile; S is
  ~60-70% redundant with M. Sensitivity tests showed S adds little independent signal.
- **K is a passenger.** Binary vs 3-level vs 4-level market regime gave **identical results
  (+9.9% excess)**. But K being inert is *not* grounds to drop it — it is the **only systematic
  (market-wide) factor**, and systematic-vs-idiosyncratic is the one axis that genuinely separates
  temporary from permanent failure. K is under-weighted and mis-located, not redundant.
- **R (RSI) is theoretically backwards but empirically helpful.** RSI<30 → +15 exit points says
  "oversold → exit," yet oversold mean-reverts (the reversion thesis). Empirically, adding R cut the
  deep-drawdown tail 11%→6%. A feature that works for the wrong reason is an overfitting flag and needs
  forensic scrutiny.

**Net:** one dominant lagging factor (M), one redundant factor (S), one inert-but-mislocated factor (K),
one inverted-but-useful factor (R). Action layer is dimensionally wrong (raw %) and topologically wrong
(binary).

---

## 2. The missing information — and the hard truth

The brief is to distinguish **temporary weakness from permanent trend failure.** The evidence-backed
answer:

> **Ex-ante, in a bull tape, that distinction is *mostly unpredictable* — and every attempt to predict
> it this session failed.**

Proof:
- **Velocity / return-per-day as a churn signal: net-negative.** Cutting falling-velocity names
  realized −6.8% vs −3.3% if held; cohort median fell +5.8% → −0.8%. Laggards *recover*.
- **No single factor (momentum / SMA / RS / volume / 52w-high) or any combination separated post-exit
  continuation** — the all-factors COMBO was *anti-predictive*.
- **The "ran after" alarm was a measurement artifact** — peak `max(high)` not realized return; honest
  realized ≈ +4.7% ≈ benchmark.

This reframes the problem. There is no reliable failure-predictor in OHLCV. What *is* deterministically
available:

1. **Idiosyncratic vs systematic weakness.** Idiosyncratic weakness in a bull tape ≈ noise (recovers).
   Systematic weakness (regime turn) removes the recovery force → the only thing that makes failure
   persistent. This is the genuine missing axis; current K gestures at it but is buried additively.
2. **Trend *quality* (signal-to-noise), not just magnitude.** M gives the move's size, nothing about
   whether it is a clean trend or lucky chop.
3. **Earned trust (persistence).** A name holding top rank for 200 stable days has revealed itself as a
   probable multibagger; a fresh rank-5 has not. Snapshot M cannot encode this.

Only these three axes are advanced — and each must clear §3's skepticism bar.

---

## 3. New deterministic features — adversarial filtering

### 3a. REJECTED — with evidence

| Candidate | Verdict | Evidence / reason |
|---|---|---|
| Momentum decay slope / velocity | **Reject** | Tested. Anti-predictive as churn; laggards recover (−6.8% cut vs −3.3% held). |
| Relative-strength persistence (vs index) | **Reject** | RS_63 HI/lo = +4.7/+3.7 forward — noise; ~collinear with M. |
| Volume behaviour (vol ratio) | **Reject** | `vol10/50` HI had *lower* forward (+2.7 vs +5.7). Inverse/noise. |
| ATR **expansion** (as direction) | **Reject** | Factor-IC −0.033 (worst of all). Vol expansion ≠ trend failure. |
| Recovery speed | **Reject** | Recovery near-universal in bull; common event ⇒ low discrimination. |
| Regime *duration* | **Reject (for now)** | K itself inert in-sample; duration is 2nd-order on an inert factor. |
| Rolling percentile deterioration | **Reject** | This *is* momentum decay re-expressed. |
| Momentum entropy | **Reject** | ~collinear with trend efficiency; pick the explainable one. |

**Principle:** a feature must add information orthogonal to M and to each other. Velocity, RS,
rolling-percentile, entropy are all re-parametrizations of "momentum changed" — empirics confirm they
add nothing beyond M.

### 3b. SURVIVOR #1 — Volatility-normalized drag *(the action, not a score factor)*

1. **Definition.** `drag_atr = (peak_close_since_entry − close) / ATR₁₄`; tolerance `T = k · ATRpct`
   replacing fixed 40/25/12.
2. **Why it predicts exits.** Removes cross-sectional ATR dispersion so a stop has constant statistical
   meaning (~N-sigma adverse move). Stops clipping volatile multibaggers on 1σ noise; stops over-holding
   calm laggards past their breakdown.
3. **Complexity.** O(1)/position/day (ATR already computed; `atr_map` exists).
4. **Correlation with existing.** Near-zero — M/K/S/R are *levels*; this is a *scale on the action*.
   Orthogonal by construction.
5. **Expected impact.** Highest. The ~3-4× ATR ratio is the magnitude of mis-calibration corrected.
6. **Overfit risk.** Low — one parameter, a first-principles correction.
7. **Explainability.** Maximal ("exit on a 4-ATR drawdown").
8. **Validation.** Sweep `k ∈ {3,4,5,6}` on train, lock on validate, report on test; compare CAGR *and*
   multibagger capture.

### 3c. SURVIVOR #2 — Trend efficiency (Kaufman Efficiency Ratio)

1. **Definition.** `ER_n = |C_t − C_{t−n}| / Σ|C_i − C_{i−1}|`, n≈25. Range [0,1]; 1 clean, →0 chop.
2. **Why.** The one feature orthogonal to M that separates "weakness within a clean trend" (high ER,
   pullback) from "structural decay" (collapsing ER, trend disintegrating). A *falling* ER while drag
   rises is the closest deterministic proxy OHLCV admits for permanent failure.
3. **Complexity.** O(n) rolling, O(1) incremental.
4. **Correlation.** Magnitude-orthogonal to M; partially correlated with R in chop — must prove
   incremental IC.
5. **Expected impact.** Moderate, **as a modifier only** (widen tolerance when ER high, tighten when
   collapsing), never a standalone gate.
6. **Overfit risk.** Moderate — must show incremental IC over {M,K,S,R} on validation or be rejected.
7. **Explainability.** High ("the trend is getting choppier").
8. **Validation.** Residualized Spearman IC of ΔER vs realized forward return; reject if incremental IC
   < ~0.02 or insignificant after multiple-testing correction.

### 3d. SURVIVOR #3 — Leader / rank persistence

1. **Definition.** `P_W = (1/W) Σ 1[rank_i ≤ N]` over trailing W≈60 (or decay-weighted mean rank).
2. **Why.** Multibaggers are *revealed by persistence*, not predicted by a snapshot (BHARTIARTL 1191d,
   MAXHEALTH 856d, M&M 1023d). P justifies **asymmetric patience** — high-P names get wider tolerance
   (protect the tail), low-P standard. The deterministic mechanism for "preserve multibaggers."
3. **Complexity.** O(W) rolling over stored ranking history.
4. **Correlation.** P is the time-integral of M — correlates with current M but carries independent
   *trajectory* information (two names at M=0.4: one decaying from 0.9-held-200d, one a fresh spike).
   Must prove incremental IC.
5. **Expected impact.** Small but targeted at the tail, where CAGR is made.
6. **Overfit risk.** **Highest** — persistence mechanically correlates with past return (survivorship);
   must be measured strictly causally.
7. **Explainability.** High ("proven leaders get more rope").
8. **Validation.** Stratify exits by causal P-quartile; reject if the effect is just past-return
   autocorrelation.

**Full defended set:** one action-normalizer (ATR), one trend-quality modifier (ER), one
persistence-modifier (P). Everything else is rejected on evidence.

---

## 4. Recommended architecture — Exit Engine v2

**Design principle (from §2):** since failure is unpredictable, stop predicting it — manage exposure.
Three layers, strict precedence.

```
  daily, per position →  LAYER 0 — SYSTEMIC KILL  (the one real permanent-failure signal)
                         regime CONFIRMED bear (k-day) AND stock below own long trend → FULL EXIT
                               │ survives
                         LAYER 1 — VOL-SCALED PARTIAL TRAIL
                         drag_atr = (peak−close)/ATR₁₄ ;  tolerance T = k·ATRpct·μ(P)·ν(ER)
                         confirmed breach → TRIM a fraction (¼–⅓), not full exit
                               │ survives
                         LAYER 2 — RUNNER STUB
                         never fully sold while Layer-0 quiet; keep ≥X% riding the 100–400% tail
```

- **Scoring philosophy.** Replace "predict failure" with "price the response to weakness." Weakness →
  graded exposure reduction scaled by volatility, earned trust, trend quality. No full exit except the
  one systematic signal that removes the recovery force (Layer 0).
- **Layer 0** is the only full-exit path; **K is elevated from a summand to a gate** (confirmed-bear AND
  own-trend-broken). This is where K finally earns its keep — idiosyncratic weakness recovers, systematic
  does not.
- **Layer 1** is the workhorse: ATR-normalized trail, tolerance *modulated* by persistence `μ(P)` and
  efficiency `ν(ER)`; on confirmed breach it **trims**, never liquidates.
- **Layer 2** guarantees a runner stub — once trimmed to X% of original, only Layer 0 can take it to
  zero. **Multibagger capture preserved by construction.**
- **Weighting.** M, R become inputs to *trim-size confidence*, not the gate. K is a gate. S is
  demoted/merged into ER + the own-trend gate.
- **Threshold derivation.** No hand-set numbers — tolerances are ATR multiples calibrated so the median
  *winner* pullback sits inside tolerance and only the p85+ tail breaches.
- **Hysteresis.** Trim requires k-day confirmation; no re-entry on the stub (re-entry verified
  structurally near-impossible — only 9% of trailed names re-entered within 90d).
- **Partial exits (core innovation).** ⅓ trims on successive breaches, floored at the stub. Decouples
  "improve the average" from "preserve the tail."
- **Confidence adjustment.** trim `f = base · g(agreement)`, agreement = fraction of
  {M-fade, R-weak, ER-collapse} concurring.
- **Opportunity-cost.** Deliberately minimal — aggressive recycling was proven loss-making. No forced
  eviction of incumbents.

---

## 5. Mathematical formulas

```
ATR₁₄ = EMA₁₄(TrueRange);   ATRpct = ATR₁₄ / close
drag_atr = (max_{τ≤t} close_τ − close_t) / ATR₁₄

Efficiency:  ER_n = |C_t − C_{t−n}| / Σ|C_i − C_{i−1}|,  n = 25
Persistence: P_W = (1/W) Σ 1[rank_i ≤ N],   W = 60, N = 10

Tolerance:   T_t = k · ATRpct_t · μ(P) · ν(ER)
   μ(P)  = 1 + a·P            (proven leaders → wider;  a ≈ 0.5)
   ν(ER) = 1 + b·(ER − ER̄)    (clean trend → wider;     b ≈ 0.5)
   k from train calibration ≈ winners' p85 drawdown in ATR units

Layer 0 (gate, full exit):
   1[ regime_3way = BEAR ≥ d days ]  AND  1[ close < SMA_long AND ER < ER_floor ]

Layer 1 (partial trim) on confirmed breach:
   fire = (drag_atr > T_t for ≥ h consecutive days)
   trim_fraction = f_base · g(agreement),   stub floor = X%
```

---

## 6. Backtesting methodology (overfitting-resistant)

**Walk-forward split, zero look-ahead:**
- **Train 2021-2023** — derive `k,a,b,X`; calibrate `T` to winners' drawdown distribution. Only here.
- **Validate 2024** — gatekeeper. Each feature must show **incremental residualized Spearman IC over
  {M,K,S,R}** or be dropped. Params frozen; only inclusion decided here.
- **Test 2025** — touched once. Report CAGR, multibagger capture, max-DD, turnover, net-of-cost.

**Mandatory robustness (where most "improvements" die):**
1. **Effective-sample correction.** ~20 independent multibagger outcomes *are* the P&L. Apply
   deflated-Sharpe / White's Reality Check / Bonferroni for the number of features & thresholds. The bar
   is brutal — most candidates will (correctly) fail.
2. **Drop-the-top-K stress test.** Remove top 1/3/5 winners; if v2's edge vanishes, it was luck.
3. **Regime stratification.** Bull/bear/sideways separately — must not win only in 2021 bull.
4. **Parameter plateau test.** Chosen `k,a,b` must sit on a flat neighborhood, not a spike.
5. **Cost sensitivity.** Partials raise turnover (historical #1 killer: 68×/yr ate 19-35pp). Re-run at
   0/15/30/50 bps; reject any trim schedule that doubles turnover for <1pp gross.
6. **Honest metric.** Forward returns close-to-close realized + benchmark-excess, never `max(high)`.
7. **Placebo features.** Inject shuffled "features"; if they "improve" the backtest, the pipeline overfits.

---

## 7. Expected improvement — honest range

| Change | Realistic contribution | Confidence |
|---|---|---|
| ATR-normalized + partial-exit action layer | **+0.7 to +2.0pp** | High (first-principles) |
| Persistence-asymmetric patience (tail protection) | **+0.3 to +0.8pp** | Medium (targets the ~20 events that matter) |
| Trend-efficiency modifier | **+0.0 to +0.5pp** | Low (may not clear validation) |
| K elevated to systematic gate | **±0.3pp** | Medium (better drawdown control) |

Underwrite **+1.5pp expected, +3pp optimistic.** 3-5% is achievable only if partial/vol-scaling compounds
favorably with turnover controlled. **Constraint:** multibagger-capture (held names reaching ≥100%) must
be **≥ v1** — buying CAGR by clipping the tail is a failure regardless of the CAGR number.

---

## 8. Risks

1. **Overfitting on ~20 effective events** — dominant risk; only the deflated-significance gate controls
   it. Expect it to kill ER and possibly P.
2. **Partials raise turnover** → reintroduce cost drag (historical #1 problem). Keep trims coarse.
3. **Vol-scaling mis-calibration across regimes** — `k` fit in calm 2021, applied in a vol spike, could
   over-hold. Regime-stratified calibration mitigates.
4. **Persistence = survivorship.** P mechanically correlates with past return; causal measurement
   non-negotiable.
5. **The fundamental ceiling.** The entry signal is mostly beta. No exit redesign manufactures alpha that
   isn't in the entries — v2 improves capital efficiency and tail capture, not edge. 3-5% may not be in
   the data.

---

## 9. ADR-level justification

**Decision.** Replace the additive 4-factor binary exit with a 3-layer exposure-management engine:
systematic-kill gate (K elevated), volatility-normalized **partial** trail (ATR units,
persistence/efficiency-modulated tolerance), and a never-fully-sold **runner stub**.

**Status.** Proposed — pending the §6 train/validate/test protocol, with feature inclusion gated on
deflated incremental IC.

**Context.** Empirical work established: (1) idiosyncratic weakness in a bull tape recovers — failure is
largely unpredictable from OHLCV; (2) the trailing stop is dimensionally wrong (raw % not ATR); (3) the
binary form cannot simultaneously improve the average and preserve the fat tail.

**Consequences.**
- *Positive* — tail capture preserved by construction (stub); volatility-invariant, explainable
  calibration; patience concentrated on proven leaders.
- *Negative* — higher turnover (cost risk); more parameters (overfit risk, controlled by the gate);
  added complexity (mitigated by strict layer precedence and per-rule explainability).

**Rejected alternatives.** (a) adding velocity/RS/volume/ATR-expansion factors — rejected on measured
non-incrementality / anti-predictiveness; (b) opportunity-cost slot recycling — rejected, empirically
loss-making; (c) threshold re-optimization of v1 — rejected as optimizing the wrong layer.

---

### Next step (decisive)
Run the **§6.1 incremental-IC gate on 2024** for ER and P, residualized against {M,K,S,R}, with
multiple-testing correction. Expect it to reject at least one survivor — a senior quant should *want*
that, since the prior says most features are noise. Advance the action-layer changes
(ATR-normalization + partial stub) regardless, as first-principles corrections independent of any fitted
edge.
