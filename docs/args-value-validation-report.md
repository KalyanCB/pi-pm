# ARGS Value Validation Report

**Principal Quant Research Lead — Pi-PM**  
**Date:** 2026-06-02  
**Status:** Research validation only (no code, schema, or prompt changes)

---

## Executive conclusion

On the latest completed ARGS runs, **ARGS does not materially re-rank** the cross-strategy consensus book relative to a simple combination of raw engine ranks. It **does add structured evidence and qualitative risk language** that raw rankings lack. **Portfolio-level proof of value is not yet established**—a controlled backtest (Phase 5 design below) is required before ARGS can be claimed to improve selection quality.

| Verdict | Assessment |
|---------|------------|
| ARGS adds information? | **Partially yes** — evidence + narrative; **not** rank discrimination on this slice |
| Cross-strategy conviction leaders | **WOCKPHARMA.NS, HFCL.NS, THERMAX.NS** (+ HONASA, LAURUSLABS, ZYDUSLIFE in Tier A) |
| Engine disagreements | **NSLNISP.NS, VIJAYA.NS, RRKABEL.NS** (rank spread ≥ 9) + 10 single-strategy names |
| Governance confidence meaningful? | **Limited** within-run; largely formula-driven banding |
| Ready for portfolio experiment? | **Conditionally yes** — design approved; implementation deferred |

---

## Data basis

| Item | ID / value |
|------|------------|
| Breakout ARGS run | `8cc023c1-ef76-4f28-bced-3452d16c1d19` |
| Momentum ARGS run | `7b4908a1-4819-4149-b299-ff74099d2975` |
| Breakout ranking run | `b8e993e4-a049-4f3a-bcd0-29574a0f7e47` |
| Momentum ranking run | `097bddfe-1cb3-4073-b00b-bfd056040115` |
| As-of | 2026-06-02 |
| Committees | TARC, QRC |

Companion: `docs/consensus-analysis.md` (overlap sets A/B/C).

---

## Phase 2 — Deterministic composite research score

### Formula (0–100, no LLMs)

For each symbol in **both** top-20 lists:

```
research_score =
  0.20 × breakout_rank_percentile
+ 0.20 × momentum_rank_percentile
+ 0.20 × governance_percentile
+ 0.15 × factor_ic_evidence_pct
+ 0.15 × validation_evidence_pct
+ 0.10 × regime_evidence_pct
```

**Definitions:**

| Input | Calculation |
|-------|-------------|
| `breakout_rank_percentile` | `100 × (21 − breakout_rank) / 20` |
| `momentum_rank_percentile` | `100 × (21 − momentum_rank) / 20` |
| `governance_percentile` | `100 × avg(breakout_governance_conf, momentum_governance_conf)` |
| `factor_ic_evidence_pct` | Mean across runs of `(factor_ic component / 20 × 100)` from `evidence_coverage.components` |
| `validation_evidence_pct` | Mean across runs of `((validation_current + validation_historical) / 35 × 100)` |
| `regime_evidence_pct` | Mean across runs of `(regime_strategy / 10 × 100)` |

**Median overlap governance:** 0.8303  
**Median overlap research_score:** 77.0  

### Ranked overlap universe (15 names)

| Rank | Symbol | research_score | B rank | M rank | Gov avg | Factor IC pct | Validation pct | Regime pct |
|-----:|--------|---------------:|-------:|-------:|--------:|--------------:|---------------:|-----------:|
| 1 | WOCKPHARMA.NS | **87.0** | 2 | 1 | 0.830 | 100 | 42.9 | 100 |
| 2 | HFCL.NS | **86.0** | 1 | 3 | 0.830 | 100 | 42.9 | 100 |
| 3 | THERMAX.NS | **85.0** | 3 | 2 | 0.830 | 100 | 42.9 | 100 |
| 4 | ZYDUSLIFE.NS | 77.0 | 5 | 8 | 0.828 | 100 | 42.9 | 100 |
| 5 | HONASA.NS | 76.0 | 10 | 4 | 0.828 | 100 | 42.9 | 100 |
| 6 | LAURUSLABS.NS | 75.0 | 6 | 9 | 0.830 | 100 | 42.9 | 100 |
| 7 | NSLNISP.NS | 73.0 | 4 | 13 | 0.828 | 100 | 42.9 | 100 |
| 8 | GLAND.NS | 72.0 | 9 | 10 | 0.828 | 100 | 42.9 | 100 |
| 9 | VIJAYA.NS | 68.0 | 16 | 7 | 0.827 | 100 | 42.9 | 100 |
| 10 | RRKABEL.NS | 66.0 | 8 | 17 | 0.829 | 100 | 42.9 | 100 |
| 11 | SOLARINDS.NS | 61.0 | 14 | 16 | 0.821 | 100 | 42.9 | 100 |
| 12 | TATATECH.NS | 60.0 | 17 | 14 | 0.829 | 100 | 42.9 | 100 |
| 13 | TRITURBINE.NS | 60.0 | 12 | 19 | 0.820 | 100 | 42.9 | 100 |
| 14 | NEULANDLAB.NS | 58.0 | 18 | 15 | 0.826 | 100 | 42.9 | 100 |
| 15 | ATGL.NS | 53.0 | 20 | 18 | 0.819 | 100 | 42.9 | 100 |

### ARGS vs raw engines (overlap top-10)

| Method | Top 10 symbols |
|--------|----------------|
| Top 10 breakout_v1 only | HFCL, WOCKPHARMA, THERMAX, NSLNISP, ZYDUSLIFE, LAURUSLABS, GRANULES*, RRKABEL, GLAND, HONASA |
| Top 10 momentum_v1 only | WOCKPHARMA, THERMAX, HFCL, HONASA, SAREGAMA*, TEJASNET*, LAURUSLABS, VIJAYA, ZYDUSLIFE, GLAND |
| **Avg engine rank (overlap only)** | WOCKPHARMA, HFCL, THERMAX, ZYDUSLIFE, HONASA, LAURUSLABS, NSLNISP, GLAND, VIJAYA, RRKABEL |
| **research_score (ARGS deterministic)** | **Same 10 as avg engine rank** |

\*Not in overlap.

**Jaccard (overlap top-10 research_score vs avg engine rank):** 1.00  
**Jaccard (research_score top-10 vs breakout-only top-10):** 0.82  

**Conclusion:** On this date, the deterministic ARGS composite score **does not change** the consensus top-10 vs averaging raw ranks. Differentiation is driven almost entirely by **rank percentiles**; evidence and governance terms are **flat across overlap names** (same coverage components except governance band differs by run, not by symbol within run).

---

## Phase 3 — Conviction tiers

### Tier A — High conviction (6)

**Criteria (all required):**

- Present in **both** breakout and momentum top-20  
- `research_score` ≥ median overlap (77.0)  
- `avg(governance_conf)` ≥ median overlap (0.8303)  
- `avg(evidence_coverage)` ≥ 72.5 (midpoint of breakout 80 + momentum 65)

| Symbol | Rationale |
|--------|-----------|
| **WOCKPHARMA.NS** | #1 momentum, #2 breakout; rank sum 3; strongest dual-engine agreement. |
| **HFCL.NS** | #1 breakout, #3 momentum; rank sum 4. |
| **THERMAX.NS** | #3 breakout, #2 momentum; rank sum 5. |
| **HONASA.NS** | Top-10 both; rank sum 14; breakout #10 / momentum #4. |
| **LAURUSLABS.NS** | Top-10 both; highest breakout governance (0.904). |
| **ZYDUSLIFE.NS** | Top-10 both; stable mid-ranks (5 / 8). |

### Tier B — Medium conviction (6)

| Symbol | Rationale |
|--------|-----------|
| **GLAND.NS** | Overlap; aligned ranks (9/10); below Tier A score threshold. |
| **ADANIENSOL.NS** | Breakout-only #19; breakout technical candidate, no momentum confirmation. |
| **AIAENG.NS** | Breakout-only #15. |
| **GRANULES.NS** | Breakout-only #7; strong breakout score but absent from momentum book. |
| **OFSS.NS** | Breakout-only #13. |
| **WELCORP.NS** | Breakout-only #11. |
| **ENRIN.NS** | Momentum-only #11. |
| **POWERINDIA.NS** | Momentum-only #12. |
| **SAREGAMA.NS** | Momentum-only #5; high momentum composite (0.957) but no breakout confirmation. |
| **SCHNEIDER.NS** | Momentum-only #20. |
| **TEJASNET.NS** | Momentum-only #6. |

*Note: Tier B includes all **single-strategy** top-20 names (exploratory / engine-specific).*

### Tier C — Low conviction / disagreement (8 overlap)

**Criteria:** overlap plus (`research_score` < 72 **or** rank spread ≥ 9).

| Symbol | Rationale |
|--------|-----------|
| **NSLNISP.NS** | Breakout #4 vs momentum #13 (spread 9)—breakout favors, momentum disagrees. |
| **VIJAYA.NS** | #16 vs #7—momentum favors, breakout disagrees. |
| **RRKABEL.NS** | #8 vs #17—breakout favors, momentum disagrees. |
| **SOLARINDS.NS** | Dual tail ranks (14/16); weak combined signal. |
| **TATATECH.NS** | Dual mid-tail (17/14). |
| **TRITURBINE.NS** | Momentum #19; breakout #12. |
| **NEULANDLAB.NS** | Dual tail (18/15). |
| **ATGL.NS** | Weakest overlap research_score (53); ranks 20/18. |

---

## Phase 4 — Tier A research quality sheets

### WOCKPHARMA.NS

| Dimension | Value |
|-----------|-------|
| Breakout rank / score | 2 / 0.887 |
| Momentum rank / score | 1 / 0.983 |
| Governance conf. (B / M) | 0.902 / 0.759 |
| Regime | BEAR_LOW_VOL |
| Factor evidence | 256 IC rows (breakout), 128 (momentum); factor_ic coverage maxed |
| Validation evidence | Current: null; **12 historical** completed validations in packet |
| Research intelligence | breakout_v1 IC > momentum_v1; edge in BULL_LOW_VOL; regime-aware deployment note |
| TARC (breakout) | Strong volume surge, trend quality, proximity; weak consolidation breakout |
| QRC (breakout) | Moderate validation coverage; negative regime IC in BEAR_LOW_VOL |
| QRC (momentum) | Low committee confidence (0.46)—flags missing horizons / weak exit metrics |

### HFCL.NS

| Dimension | Value |
|-----------|-------|
| Breakout rank / score | 1 / 0.887 |
| Momentum rank / score | 3 / 0.974 |
| Governance conf. (B / M) | 0.902 / 0.759 |
| Regime | BEAR_LOW_VOL |
| Factor / validation | Same packet pattern as WOCKPHARMA (256/128 IC; 12 hist. validations) |
| Research intelligence | Shared platform notes (IC, BULL_LOW_VOL edge) |
| TARC | #1 breakout—volume surge, trend quality, relative strength dominant |
| Disagreement risk | QRC momentum run flags limited validation coverage (40%) |

### THERMAX.NS

| Dimension | Value |
|-----------|-------|
| Breakout rank / score | 3 / 0.886 |
| Momentum rank / score | 2 / 0.977 |
| Governance conf. (B / M) | 0.902 / 0.759 |
| Regime | BEAR_LOW_VOL |
| Factor / validation | 256/128 IC rows; historical validation only |
| TARC | Strong breadth on breakout factors; weak consolidation breakout |
| Note | Tight rank spread (1)—third leg of consensus “podium” with WOCKPHARMA and HFCL |

### ZYDUSLIFE.NS

| Dimension | Value |
|-----------|-------|
| Breakout rank / score | 5 / 0.853 |
| Momentum rank / score | 8 / 0.928 |
| Governance conf. (B / M) | 0.900 / 0.757 |
| Regime | BEAR_LOW_VOL |
| Factor / validation | Standard overlap evidence bundle |
| Role | Mid-consensus; supports Tier A depth but lower research_score than podium three |

### HONASA.NS

| Dimension | Value |
|-----------|-------|
| Breakout rank / score | 10 / 0.846 |
| Momentum rank / score | 4 / 0.962 |
| Governance conf. (B / M) | 0.898 / 0.759 |
| Regime | BEAR_LOW_VOL |
| Disagreement | Momentum likes more than breakout (spread 6)—ARGS still Tier A on combined score |

### LAURUSLABS.NS

| Dimension | Value |
|-----------|-------|
| Breakout rank / score | 6 / 0.850 |
| Momentum rank / score | 9 / 0.925 |
| Governance conf. (B / M) | 0.904 / 0.755 (highest breakout gov. in Tier A) |
| Regime | BEAR_LOW_VOL |
| Note | Balanced mid-ranks; highest breakout-side governance in tier |

---

## Phase 5 — Backtest readiness (design only)

### Objective

Test whether **selection quality** improves when using ARGS consensus vs raw engine tops.

### Portfolios (equal-weight, N=10)

| Portfolio | Construction | Rebalance |
|-----------|--------------|-----------|
| **A — Raw breakout** | Top 10 by breakout_v1 rank on rebalance date | Monthly |
| **B — Raw momentum** | Top 10 by momentum_v1 rank | Monthly |
| **C — ARGS consensus** | Top 10 overlap names by `research_score` (deterministic formula above); if \|overlap\| < 10, fill with next-best rank-sum from union | Monthly |

### Holding period & horizon

- **Primary holding period:** 20 trading days (aligned with validation horizon and regime analytics).  
- **Secondary:** 5d and 60d robustness.  
- **Warm-up:** Exclude first 63 trading days after platform data start per universe filter.

### Transaction costs

- **Baseline:** 10 bps one-way (commission + slippage) for NIFTY_500 liquidity.  
- **Stress:** 25 bps one-way.  
- **Turnover:** Report monthly; ARGS C may differ if consensus set changes.

### Evaluation metrics

| Category | Metrics |
|----------|---------|
| Return | CAGR, total return, hit rate vs NIFTY_500 |
| Risk | Volatility, max drawdown, beta to ^NSEI |
| Risk-adj | Sharpe, Sortino, information ratio vs benchmark |
| Selection | Spread: top-decile minus bottom-decile forward return; rank IC of prior-month score |
| ARGS-specific | Incremental IR of C−A and C−B; overlap stability; Tier A vs Tier C forward return spread |
| Statistical | Bootstrap 95% CI on Sharpe difference; HAC-adjusted t-test on monthly alphas |

### Success criteria (pre-registered)

1. Portfolio **C** Sharpe > **A** and **C** > **B** after costs (primary).  
2. **C** top-decile forward return spread > max(A, B) in ≥ 60% of rebalance months.  
3. Tier A basket beats Tier C basket on forward 20d return (ARGS tiering adds value).  
4. Failure: C ≈ average(A,B) → ARGS is **synthesis only**, not alpha.

### Data requirements

- Point-in-time rankings (no look-ahead).  
- ARGS packets rebuilt **as-of each rebalance date** (not static 2026-06-02 run).  
- Corporate actions adjusted prices (existing Yahoo ingest).

**Implementation:** explicitly **out of scope** for this validation exercise.

---

## Research questions — direct answers

### 1. Is ARGS adding information?

**Yes, but not in rank ordering on 2026-06-02.**

| Added | Not added (this slice) |
|-------|-------------------------|
| Factor IC windows, exit research counts, regime performance tables | Different top-10 vs avg engine rank on overlap |
| 12-report historical validation context | Current-run forward validation (still null) |
| Research intelligence notes | Cross-sectional governance spread (mostly banded) |
| TARC/QRC narrative risk (e.g. BEAR_LOW_VOL negative IC) | New symbols outside engine top-20 |

ARGS is currently a **research enrichment layer**, not a demonstrated **alpha layer**.

### 2. Which stocks have highest cross-strategy conviction?

**WOCKPHARMA.NS, HFCL.NS, THERMAX.NS** — then **HONASA.NS, LAURUSLABS.NS, ZYDUSLIFE.NS** (Tier A).  
Engine rank-sum podium: WOCKPHARMA (3), HFCL (4), THERMAX (5).

### 3. Which stocks are ranking-engine disagreements?

**Within overlap (large spread):** NSLNISP.NS, VIJAYA.NS, RRKABEL.NS.  
**Across lists (single-strategy top-20):**  
- Breakout-only: GRANULES.NS, WELCORP.NS, OFSS.NS, AIAENG.NS, ADANIENSOL.NS  
- Momentum-only: SAREGAMA.NS, TEJASNET.NS, ENRIN.NS, POWERINDIA.NS, SCHNEIDER.NS  

### 4. Is governance confidence meaningful?

**Partially, with important caveats.**

| Observation | Implication |
|-------------|-------------|
| Breakout run: 5 unique values in [0.896, 0.904] | Tracks rank tier weakly; not fine-grained |
| Momentum run: 5 unique values in [0.741, 0.759] | Entire run ~15 pts lower due to coverage 65 vs 80 |
| Formula: 60% evidence + 40% committee avg | Committee conf. (TARC ~0.87–0.89, QRC ~0.46–0.79) drives spread |
| research_score correlation with gov | **Inflated**—governance is 20% of the same score |

**Use governance confidence for:** coarse run-level quality (breakout packet richer than momentum on this date).  
**Do not use for:** cross-stock sorting within a run without recalibration.

### 5. Is ARGS ready for a portfolio-level experiment?

**Yes — for a research backtest, not for production capital.**

| Ready | Not ready |
|-------|-----------|
| Two completed ARGS runs with enriched packets | Multi-date ARGS history for walk-forward |
| Deterministic consensus score defined | Proof of outperformance |
| Tier A/B/C framework | Live trading integration |
| Phase 5 experiment spec | Automated rebalance pipeline |

**Recommendation:** Proceed with **Phase 5 backtest** on a **6–12 month** rebalance history; hold production ARGS allocation until C beats A and B on net Sharpe with pre-registered criteria.

---

## Appendix — Evidence coverage by run

| Run | evidence_coverage (all 20 packets) | factor_ic rows (sample) | hist. validations |
|-----|-----------------------------------|-------------------------|-------------------|
| Breakout ARGS | 80 (uniform) | 256 | 12 |
| Momentum ARGS | 65 (uniform) | 128 | 12 |

Missing on all packets: `validation.horizon_metrics` (current run), `quant_evidence.factor_daily` on some ranking_run_ids before fallback (post-fix builder addresses for new runs).

---

*End of report. No production code, schemas, prompts, or committee logic were modified.*
