# Cross-Strategy Consensus Analysis

**Principal Quant Research Lead — Pi-PM**  
**As-of date:** 2026-06-02  
**Universe:** NIFTY_500  

## Source runs

| Strategy | ARGS research run | Ranking run | Top N |
|----------|-------------------|-------------|-------|
| breakout_v1 | `8cc023c1-ef76-4f28-bced-3452d16c1d19` | `b8e993e4-a049-4f3a-bcd0-29574a0f7e47` | 20 |
| momentum_v1 | `7b4908a1-4819-4149-b299-ff74099d2975` | `097bddfe-1cb3-4073-b00b-bfd056040115` | 20 |

Committees on both runs: **TARC, QRC** (`require_completed_validation=false`).

---

## Summary statistics

| Metric | Value |
|--------|------:|
| Breakout top-20 count | 20 |
| Momentum top-20 count | 20 |
| **Overlap (A ∩ B)** | **15** |
| Breakout-only | 5 |
| Momentum-only | 5 |
| Union of top-20 lists | 30 |
| Overlap / union (Jaccard) | **50.0%** |
| Overlap / either list | **75.0%** |

**Interpretation:** Three-quarters of each engine’s top-20 also appear in the other engine’s top-20 on this date. ARGS consensus work should focus on the **15 shared names**; the **10 non-overlapping** names are strategy-specific disagreements.

---

## A) Stocks appearing in both strategies (15)

Ranked by combined engine strength (sum of ranks; lower is better).

| Symbol | Breakout rank | Momentum rank | Rank sum | Rank spread | Breakout gov. conf. | Momentum gov. conf. |
|--------|:-------------:|:-------------:|:--------:|:-----------:|:-------------------:|:-------------------:|
| WOCKPHARMA.NS | 2 | 1 | 3 | 1 | 0.902 | 0.759 |
| HFCL.NS | 1 | 3 | 4 | 2 | 0.902 | 0.759 |
| THERMAX.NS | 3 | 2 | 5 | 1 | 0.902 | 0.759 |
| HONASA.NS | 10 | 4 | 14 | 6 | 0.898 | 0.759 |
| LAURUSLABS.NS | 6 | 9 | 15 | 3 | 0.904 | 0.755 |
| ZYDUSLIFE.NS | 5 | 8 | 13 | 3 | 0.900 | 0.757 |
| NSLNISP.NS | 4 | 13 | 17 | **9** | 0.900 | 0.755 |
| GLAND.NS | 9 | 10 | 19 | 1 | 0.898 | 0.757 |
| VIJAYA.NS | 16 | 7 | 23 | **9** | 0.896 | 0.757 |
| RRKABEL.NS | 8 | 17 | 25 | **9** | 0.902 | 0.755 |
| SOLARINDS.NS | 14 | 16 | 30 | 2 | 0.898 | 0.743 |
| TATATECH.NS | 17 | 14 | 31 | 3 | 0.902 | 0.755 |
| TRITURBINE.NS | 12 | 19 | 31 | 7 | 0.898 | 0.741 |
| NEULANDLAB.NS | 18 | 15 | 33 | 3 | 0.896 | 0.755 |
| ATGL.NS | 20 | 18 | 38 | 2 | 0.896 | 0.741 |

**Cross-strategy leaders (rank sum ≤ 13):** WOCKPHARMA.NS, HFCL.NS, THERMAX.NS, HONASA.NS, LAURUSLABS.NS, ZYDUSLIFE.NS.

**Largest ranking disagreements (spread ≥ 9):** NSLNISP.NS (breakout #4 vs momentum #13), VIJAYA.NS (#16 vs #7), RRKABEL.NS (#8 vs #17). These are prime “engine disagreement” names for ARGS to adjudicate—on this date ARGS narratives flag regime/validation risk but do not remove them from overlap.

---

## B) Stocks appearing only in breakout_v1 (5)

| Symbol | Breakout rank | Composite score | Governance conf. |
|--------|:-------------:|----------------:|:----------------:|
| GRANULES.NS | 7 | 0.849 | 0.902 |
| OFSS.NS | 13 | 0.833 | 0.898 |
| AIAENG.NS | 15 | 0.821 | 0.898 |
| ADANIENSOL.NS | 19 | 0.813 | 0.896 |
| WELCORP.NS | 11 | 0.845 | 0.898 |

**Interpretation:** Breakout-specific candidates skew toward **technical breakout structure** (volume surge, proximity, consolidation quality) that momentum_v1 does not rank in its top 20 on this as-of. None appear in momentum top-20—treat as **breakout-only tilts**, not consensus.

---

## C) Stocks appearing only in momentum_v1 (5)

| Symbol | Momentum rank | Composite score | Governance conf. |
|--------|:-------------:|----------------:|:----------------:|
| SAREGAMA.NS | 5 | 0.957 | 0.759 |
| TEJASNET.NS | 6 | 0.943 | 0.757 |
| ENRIN.NS | 11 | 0.922 | 0.757 |
| POWERINDIA.NS | 12 | 0.922 | 0.743 |
| SCHNEIDER.NS | 20 | 0.900 | 0.741 |

**Interpretation:** Momentum-only names include **high composite momentum scores** (e.g. SAREGAMA.NS, TEJASNET.NS) that breakout_v1 did not place in its top 20—likely weaker breakout-factor profile despite strong trend/momentum. ARGS assigns lower governance confidence on the momentum run (~0.74–0.76 band) uniformly.

---

## Regime context (shared)

All 30 names in the union carry packet regime label **BEAR_LOW_VOL** for 2026-06-02. Current-run forward validation is **not completed** (`validation.status` null); historical validation context (12 completed reports) is present in packets.

---

## Research intelligence (shared notes)

Identical research-intelligence notes appear on both runs’ packets:

1. breakout_v1 outperforms momentum_v1 on pooled IC.  
2. Strongest edge is concentrated in BULL_LOW_VOL.  
3. Regime-aware deployment is recommended pending exit research confirmation.  
4. Research intelligence top-20 as_of=2026-06-02.  
5. IC-by-strategy snapshot available.

---

## Implications for ARGS value (preview)

| Question | Finding on 2026-06-02 |
|----------|------------------------|
| Does ARGS define a consensus book? | Yes — **15 names** vs 30 union. |
| Does ARGS reorder vs engines? | **No** for top-10 consensus vs average-rank on overlap (identical ordering). |
| Where is ARGS additive? | Evidence packaging, committee narrative, disagreement flags on wide-spread names. |

Full scoring, tiers, backtest design, and go/no-go: see `docs/args-value-validation-report.md`.
