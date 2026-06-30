# PI-PM Discovery Research Program — Version 1
### A deterministic OHLCV alpha-discovery architecture, orthogonal to Breakout_v2

*Author: CQRO · Status: Proposed · Constraint: deterministic, OHLCV-only, no ML black-box, no future leakage*

---

## 1. Executive Summary

Breakout_v2 is closed: it occupies a **single cell** of the deterministic OHLCV information grid —
**single-stock × static-snapshot × level-based × price-dominant.** The peer review established that
exhausting that cell does *not* exhaust the grid. This program targets the **unvisited cells**: information
that is **cross-sectional, time-derivative, path-geometric, volume-structural, and network-topological.**

The central design principle is **information orthogonality, not CAGR maximization.** 2025 proved that a
mono-style engine has a structural failure mode (style rotation). The remedy is not a better single factor —
it is a **portfolio of architecturally-independent deterministic sleeves** engineered so that *some* sleeve
holds edge in any regime, and an **adaptive layer** that detects which style the tape is currently paying.

We propose **six candidate architectures**, of which **four are funded for V1**, one is **Tier-3 R&D**, and
two common ideas are **rejected on orthogonality grounds**. The lead architecture — the **Cross-Sectional
Rotation Engine** — is the direct structural answer to the 2025 failure.

Every architecture must clear one non-negotiable gate before funding: **positive incremental information
coefficient over Breakout_v2, residualized, out-of-sample, under deflated significance.** Novelty is not
sufficient; *additive* novelty is the bar.

---

## 2. Information Taxonomy — what Breakout_v2 cannot see

Breakout_v2 computes, per stock, at one instant, three *level* quantities (proximity, contraction,
consolidation). It is blind to five entire information classes:

### Class I — Temporal derivatives (velocity / acceleration of state)
1. **Information:** the *rate of change* of any state variable — relative rank, relative strength, trend —
   not its level. A stock improving rank 80→40→15 over 60 days is being *discovered*; a stock sitting at
   rank 15 is already *known*.
2. **Why B_v2 is blind:** it evaluates `f(t)`; it has no `df/dt` or `d²f/dt²` term anywhere.
3. **Alpha thesis:** markets price information gradually; the *derivative leads the level.* Acceleration is
   an early-warning of leadership before the snapshot factors register it.
4. **Math:** for state `sᵢ(t)`: velocity `vᵢ = sᵢ(t) − sᵢ(t−k)`; acceleration `aᵢ = vᵢ(t) − vᵢ(t−k)`;
   smoothed by a causal kernel. (Note: this is a *derivative of state*, not a moving average of price.)
5. **Complexity:** O(1) incremental per stock.
6. **Explainability:** high — "climbing the rankings fast."

### Class II — Cross-sectional dynamics (relative position in the universe)
1. **Information:** behavior *relative to the cohort*. +5% on a day the universe is −3% is strong; +5% on a
   +6% day is weak. B_v2 scores stocks in isolation, so it cannot tell these apart.
2. **Why B_v2 is blind:** no universe context enters its score — it is a per-stock function.
3. **Alpha thesis:** relative outperformance is the cleanest deterministic leadership signal and the
   substrate of every cross-sectional equity factor that has ever worked.
4. **Math:** cross-sectional z-score / percentile `zᵢ(t) = (xᵢ − μ_X)/σ_X` of any feature `x`, and its
   evolution `Δzᵢ`.
5. **Complexity:** O(N log N) per day.
6. **Explainability:** high.

### Class III — Path geometry / morphology (the *shape* of the move)
1. **Information:** *how* a stock reached its level. A smooth, efficient advance (institutional) and a
   choppy, news-driven spike can end at the *same* level with opposite continuation odds.
2. **Why B_v2 is blind:** it reads endpoints (close vs high, range vs average); the trajectory between is
   discarded.
3. **Alpha thesis:** trend *quality* (efficiency, smoothness, curvature) predicts *persistence*; B_v2's
   level-snapshot cannot distinguish a durable trend from a fragile one.
4. **Math:** efficiency `E = |Cₜ − C_{t−n}| / Σ|ΔC|` (net/gross path); curvature `κ` = 2nd difference of a
   causally-smoothed path; roughness via path-length / range. (Geometry of price, not an oscillator.)
5. **Complexity:** O(window).
6. **Explainability:** high — directly chartable.

### Class IV — Participation / accumulation dynamics (volume-price footprint)
1. **Information:** the *footprint* of accumulation — persistent up-closes on expanding volume, range
   compression *on* volume (absorption), liquidity (₹-volume) growth signalling institutional entry.
2. **Why B_v2 is blind:** it is price-dominant; volume enters, at most, trivially. It has no signed-volume
   cumulation, no volume-price *dynamics*.
3. **Alpha thesis:** institutions accumulate *before* the price breakout; the volume-price relationship
   leads the price signal B_v2 waits for.
4. **Math:** signed-volume flow `Σ sign(ΔC)·V` (dynamics, not a tuned OBV level); up/down-volume ratio
   persistence; volume-price correlation `corr(ΔC, V)`; liquidity growth `Δ(C·V)`.
5. **Complexity:** O(window).
6. **Explainability:** high — "quiet accumulation."

### Class V — Market topology / lead-lag networks (inter-stock structure)
1. **Information:** the *graph* — which stocks lead their correlated cluster, where leadership is
   propagating, how co-movement structure is shifting.
2. **Why B_v2 is blind:** it has zero inter-stock structure; every stock is scored independently.
3. **Alpha thesis:** leadership propagates through correlated groups; the *lead* of an emerging cluster is
   detectable from price-network structure *before* it tops single-stock rankings.
4. **Math:** rolling correlation matrix `ρᵢⱼ`; lead-lag via cross-correlation at lag `τ`; graph centrality /
   community detection on the thresholded network.
5. **Complexity:** O(N²) per rebalance — the expensive class.
6. **Explainability:** moderate (network visualization required).

### Class VI — Rotation / regime-conditional cross-section (adaptive meta-layer)
1. **Information:** *which characteristics the market is currently rewarding* — a second-order signal over
   the factor space itself.
2. **Why B_v2 is blind:** it is style-*static* (always near-high × contraction); it cannot detect that its
   own style is out of favor — the exact 2025 failure.
3. **Alpha thesis:** style leadership rotates on detectable timescales; a deterministic detector of the
   currently-paying characteristic, with a tilt, structurally immunizes against single-style collapse.
4. **Math:** rolling realized spread of each characteristic's top-vs-bottom decile → tilt weights toward the
   characteristic with rising realized spread; or cluster the universe by price behavior and track which
   cluster's relative strength is accelerating.
5. **Complexity:** O(N·F) per rebalance.
6. **Explainability:** moderate — "the market is paying for X right now."

*(Class VII — Temporal-motif / sequence morphology — exists but is parked: research difficulty and
explainability fail the V1 bar. See §6.)*

---

## 3. Architectural Taxonomy

Six candidate engines. Each is a *different ranking philosophy on a different information class* — none is a
breakout variant.

### Architecture A — Rank-Acceleration Engine  *(Class I + II)*
- **Input:** the cross-sectional relative-strength series of every stock.
- **Processing:** compute each stock's relative-rank *velocity* and *acceleration*; rank by acceleration of
  cross-sectional position.
- **Ranking philosophy:** *buy what the market is in the act of discovering* — emerging leaders, not
  established ones.
- **Expected behavior:** leads breakout/momentum by weeks; catches the FORCEMOT-class names *while still
  mid-base* (the 2025 blind spot).
- **Strengths:** early; orthogonal-ish to level factors; cheap; explainable.
- **Weaknesses / failure modes:** false positives in choppy tapes (acceleration is noisy); whipsaw in
  sideways markets; can chase if not paired with a quality gate.
- **Corr:** Breakout LOW-MOD · Momentum MOD-HIGH (derivative of RS) · Value NEG · Trend MOD.

### Architecture B — Cross-Sectional Rotation Engine  *(Class VI)* — **LEAD**
- **Input:** the full universe's characteristic exposures + their realized cross-sectional spreads over time.
- **Processing:** deterministically estimate which characteristic(s) are currently being rewarded (rising
  top-minus-bottom-decile realized spread), tilt capital toward them; re-estimate each rebalance.
- **Ranking philosophy:** *don't pick a style — follow the style the tape is paying.*
- **Expected behavior:** the structural answer to 2025 — when breakout-style stops paying, capital rotates
  to whatever is.
- **Strengths:** *highest orthogonality of the program*; directly immunizes the single-style failure;
  regime-adaptive by construction.
- **Weaknesses / failure modes:** lags at sharp regime turns (it's reactive); can over-fit the
  characteristic library; degenerate if all styles fail simultaneously (a 2025-for-everyone).
- **Corr:** Breakout LOW · Momentum LOW · Value LOW · Trend LOW. *(The prize.)*

### Architecture C — Participation / Accumulation Engine  *(Class IV)*
- **Input:** OHLCV with volume as a first-class citizen.
- **Processing:** rank by accumulation persistence + liquidity expansion + volume-price confirmation
  *before* price breakout.
- **Ranking philosophy:** *follow the institutional footprint, not the price.*
- **Expected behavior:** anticipatory — flags accumulation in the base, before B_v2's price trigger.
- **Strengths:** high orthogonality (volume info is nearly untapped); genuinely *earlier* than price.
- **Weaknesses / failure modes:** volume data quality (small-caps), corporate-action distortions; false
  accumulation signals in illiquid names.
- **Corr:** Breakout LOW · Momentum LOW-MOD · Value LOW · Trend LOW.

### Architecture D — Trend-Geometry Engine  *(Class III)*
- **Input:** the price path.
- **Processing:** rank by trend *efficiency*, curvature, and higher-low geometry — *quality* of the advance,
  not its existence.
- **Ranking philosophy:** *own clean trends, avoid choppy ones.*
- **Expected behavior:** excels in sustained trending regimes; filters the fragile spikes that revert.
- **Strengths:** cheap, explainable, low research risk — a fast first win.
- **Weaknesses / failure modes:** correlated with trend-following; weak in sideways/rotation; late at trend
  inception.
- **Corr:** Breakout LOW-MOD · Momentum MOD · Value LOW · Trend MOD-HIGH.

### Architecture E — Market-Topology / Lead-Lag Engine  *(Class V)* — **Tier-3 R&D**
- **Input:** the universe return matrix.
- **Processing:** rolling correlation/lead-lag network; rank by emerging-cluster leadership / centrality.
- **Ranking philosophy:** *buy the leader of the group that's about to move.*
- **Strengths:** highest *theoretical* orthogonality (pure structure).
- **Weaknesses / failure modes:** O(N²); unstable correlations; explainability and overfitting risk high.
- **Corr:** Breakout LOW · Momentum LOW · Value LOW · Trend LOW.

### Architecture F — Leadership-Persistence Engine  *(Class I+II)* — **REJECTED for V1**
- **Reason for rejection:** persistence of relative strength is **mechanically ~collinear with momentum**
  (a persistent leader *is* a momentum name). It fails the orthogonality bar — it would duplicate exposure
  PI-PM effectively already has, and adds little incremental information. *Park; do not fund.*

*(Volatility-clustering as a standalone engine is also **rejected**: it borders B_v2's vol_contraction and
the prior factor-IC work showed vol-expansion anti-predictive. Fold any vol-transition signal into D.)*

---

## 4. Research Priorities (Task 6 scoring)

Scored on Expected-alpha · Orthogonality · Explainability (higher better) ÷ Complexity · Research-difficulty ·
Maintenance (lower better). 1-5 scale.

| Arch | α | Orthog | Explain | Complexity | Res-difficulty | Maint | **Priority** |
|---|---|---|---|---|---|---|---|
| **B Rotation** | 4 | **5** | 3 | 3 | 4 | 3 | **TIER 1 (lead)** |
| **C Participation** | 4 | **5** | 4 | 2 | 3 | 2 | **TIER 1** |
| **A Rank-Accel** | 3 | 3 | 4 | 1 | 2 | 1 | **TIER 1 (fast)** |
| **D Trend-Geometry** | 3 | 2 | 5 | 1 | 1 | 1 | **TIER 2 (quick win)** |
| **E Topology** | 4 | **5** | 2 | 5 | 5 | 4 | **TIER 3 (R&D)** |
| F Leadership | 2 | 1 | 4 | 1 | 1 | 1 | **REJECTED** |

**Funding logic:** lead with **Rotation (B)** — it is the highest-orthogonality engine *and* the direct fix
for the 2025 failure mode. Pair with **Participation (C)** — the volume-information class is nearly virgin
ground and genuinely anticipatory. Run **Rank-Acceleration (A)** in parallel as the cheap, fast probe.
**Trend-Geometry (D)** is the quick confidence-builder (lowest risk). **Topology (E)** is a longer-horizon
research bet.

---

## 5. Validation Framework (every architecture must pass — no exceptions)

The framework is designed to *kill* false positives, given we are now multiple-hypothesis testing:

1. **Point-in-time universe — no survivorship.** Rankings use only stocks investable on the as-of date;
   delisted names retained to their delisting.
2. **Strict walk-forward, no look-ahead.** All features causal; parameters frozen on train, decided on
   validate, touched on test once. Train 2018-2022 · Validate 2023-2024 · Test 2025 (+ a pre-2018 holdout
   if data permits).
3. **Pre-registration.** Each architecture's feature set, ranking rule, and success threshold are written
   *before* seeing test results — the discipline the breakout work sometimes lacked.
4. **Multiple-testing correction — mandatory.** With ≥4 architectures × parameters, apply **Deflated Sharpe
   Ratio** and **White's Reality Check / SPA**. The significance bar rises with the number of trials; most
   candidates are *expected* to fail this, and that is the correct outcome.
5. **Cross-regime robustness.** Performance reported separately for broad-bull / narrow-bull / sideways /
   bear / high-vol / low-vol / rotation. No architecture is funded on a single-regime win.
6. **THE GATE — incremental IC over Breakout_v2.** Each architecture's signal must show **positive Spearman
   IC on forward returns *after residualizing against Breakout_v2's score* (and against momentum, trend,
   value proxies)**, out-of-sample. *Novelty is necessary but not sufficient — additive information is the
   bar.* An architecture that is merely a relabeled momentum factor fails here even if profitable.
7. **Capacity & cost.** Net-of-cost (the 19-35pp turnover lesson): every signal validated at realistic
   ₹-volume participation and slippage; high-turnover signals must clear a higher gross bar.
8. **Placebo control.** Shuffled/random "features" run through the identical pipeline; if they "pass," the
   pipeline is overfitting and results are void.

---

## 6. ADR Recommendations

- **ADR-D1 — Adopt the information-grid framing.** PI-PM's research is organized by *information class*, not
  by indicator. Breakout_v2 = one cell; the program funds unvisited cells. *Status: proposed.*
- **ADR-D2 — Fund Tier-1 (Rotation, Participation, Rank-Acceleration); fast-track Tier-2 (Trend-Geometry).**
  Each gated by §5.6 incremental-IC before any capital. *Status: proposed.*
- **ADR-D3 — Reject Leadership-Persistence and standalone Volatility-Clustering** on orthogonality grounds;
  document so they are not re-proposed. *Status: accepted (rejection).*
- **ADR-D4 — Portfolio-of-alpha mandate.** The objective function is **portfolio-level diversified alpha**,
  not per-sleeve CAGR. Allocation weights orthogonality, not back-tested return. *Status: proposed.*
- **ADR-D5 — Pre-registration + deflated-significance are mandatory** for every sleeve, enforced at review.
  *Status: proposed.*

---

## 7. 12-Month Research Roadmap

```
Q1 — Foundations & first signals
  • Build point-in-time universe + cross-sectional feature library (Classes I-IV)
  • Trend-Geometry (D): full validate→test  [quick win, lowest risk]
  • Rank-Acceleration (A): feature build + incremental-IC gate
  • Deliverable: validation harness + first two incremental-IC reports

Q2 — The orthogonality core
  • Participation/Accumulation (C): build, validate, incremental-IC gate
  • Cross-Sectional Rotation (B): prototype the characteristic-spread detector
  • Deliverable: pairwise-correlation matrix of surviving sleeves

Q3 — The adaptive layer + integration
  • Rotation (B): full walk-forward, cross-regime, deflated-significance
  • Combine surviving Tier-1 sleeves into a diversified deterministic portfolio
  • Deliverable: portfolio-level orthogonality + regime-coverage report

Q4 — R&D bet + hardening
  • Topology/Lead-Lag (E): research prototype (no capital)
  • Stress: 2025-style narrow/rotation regimes; capacity & cost; placebo controls
  • Deliverable: Program V1 result; go/no-go per sleeve; V2 hypotheses
```

**Gate discipline:** any sleeve failing §5.6 at its quarter is killed, not iterated — iteration is how
single-architecture overfitting crept into the breakout work.

---

## 8. Portfolio of Research — the orthogonality objective (Task 8)

The deliverable is **not five strategies; it is one diversified alpha portfolio.** Target: a covariance
structure where *some* sleeve has edge in any regime. Estimated pairwise return correlations (priors, to be
measured):

```
                B_v2   A-Accel  B-Rot  C-Part  D-Geom  E-Topo
Breakout_v2     1.00
A Rank-Accel    0.45    1.00
B Rotation      0.10    0.20   1.00
C Participation 0.20    0.30   0.15   1.00
D Trend-Geom    0.55    0.40   0.10   0.20    1.00
E Topology      0.10    0.20   0.25   0.15    0.15   1.00
```

**Reading:** D (Trend-Geometry) is the *least* additive (0.55 to breakout) — funded only as a cheap
confidence-builder, weighted low. **B (Rotation), C (Participation), E (Topology) are the diversifiers**
(0.10-0.25 to breakout) — they carry the portfolio's regime-coverage. A target portfolio of
{B_v2, Rotation, Participation, Rank-Accel} has an estimated average pairwise correlation **~0.25**, versus
the current mono-architecture **1.00** — the entire point. **Allocation is inverse to correlation, not
proportional to back-tested CAGR.** A sleeve with modest standalone alpha but ~0 correlation is worth more
to the portfolio than a high-CAGR sleeve correlated with breakout.

---

## Risk Assessment

1. **Multiple-testing / discovery bias (dominant risk).** Searching many architectures inflates false
   positives. *Mitigation:* §5.4 deflated significance + §5.8 placebo + pre-registration. Expect most
   candidates to die; that is success, not failure.
2. **Orthogonality decay.** "Independent" sleeves can correlate in crises (everything goes to 1.0 in a
   crash). *Mitigation:* measure *conditional* correlation in stress regimes, not just unconditional.
3. **Volume-data quality (Participation).** Small-cap volume is noisy / corporate-action-distorted.
   *Mitigation:* liquidity floors, adjusted data, capacity gates.
4. **Rotation engine lag.** Being reactive, B underperforms at sharp turns and degenerates if *all* styles
   fail at once (2025-for-everyone). *Mitigation:* pair with anticipatory sleeves (A, C); accept it cannot
   solve the all-styles-fail case — *no deterministic engine can* (the honest limit from the post-mortem).
5. **The ceiling may be real anyway.** The program may discover that the unvisited cells *also* hold no
   robust OHLCV alpha. *That is a legitimate, publishable result* — it would convert "Breakout_v2 ceiling"
   into a properly-evidenced "deterministic OHLCV ceiling," which the current evidence does **not** support.
6. **Maintenance / complexity creep.** A stable of sleeves costs more to run than one factor. *Mitigation:*
   kill non-additive sleeves ruthlessly; the portfolio should be small and orthogonal, not large.

---

### Closing principle
The question is never "what indicator?" It is **"what information?"** Breakout_v2 measured *where a stock is*.
This program measures *how fast it's getting there* (A), *what the market is paying for* (B), *who's
accumulating it* (C), *how clean its path is* (D), and *where it sits in the leadership graph* (E). Those are
five different questions about the same OHLCV tape — and PI-PM has only ever asked one of them.
