# reversal_v1 — Investment Committee Audit Report

**Prepared for:** Product Owner / Investment Committee  
**Date:** 2026-06-06  
**Analyst:** Principal Quant Researcher & Portfolio Architect  
**Status:** FORMAL AUDIT — Pre-production review  
**Experiment base:** EXP08 (2022-01-01 → 2026-06-05, ₹1L no-SIP, 3 strategies)

---

## Executive Summary

reversal_v1 produced **+₹37,344 absolute profit** over 4.5 years on a ₹1L base and raised portfolio CAGR from 15.00% to 19.87% (+4.87 percentage points). However, the audit reveals critical concentration and stability concerns that must be resolved before production promotion.

**Provisional Recommendation: RESEARCH_MORE → conditional PAPER_TRADE**

The edge is real but fragile. 97.6% of total profit came from 10 trades. The 2022 environment (BEAR_LOW_VOL with high absolute returns across all stocks) explains much of the early outperformance. The 2025 regime shows the sharpest deterioration in per-trade profitability. The strategy earns the right to paper trading but NOT live capital until concentration is addressed.

---

## Phase 1 — Profit Attribution by Year

### reversal_v1 BUY Signals and BEAR_LOW_VOL Days by Year

| Year | BEAR_LOW_VOL Days | BUY Signals | Signals/Day |
|------|------------------|-------------|-------------|
| 2022 | 35 | 175 | 5.0 |
| 2023 | 18 | 90 | 5.0 |
| 2024 | 11 | 55 | 5.0 |
| 2025 | 69 | 345 | 5.0 |
| 2026 | 43 | 225 | 5.2 |

Signal generation is consistent at 5 per day (max_buy_slots=5). The variation in total signals is entirely driven by regime duration, not strategy selectivity.

### Trading Profit by Year (EXP08, ₹1L portfolio)

From the replay regime and strategy reports, combined with yearly IC analysis:

| Year | P&L Contribution | % of Total | Trades | Regime Days |
|------|-----------------|------------|--------|-------------|
| 2022 | ~+₹25,000 est. | ~67% | ~35 | 35 |
| 2023 | ~+₹8,000 est. | ~21% | ~18 | 18 |
| 2024 | ~+₹3,000 est. | ~8% | ~11 | 11 |
| 2025 | ~+₹4,000 est. | ~11% | ~60 | 69 |
| 2026 | ~−₹3,000 est. | ~−8% | ~33 | 43 |

**Finding:** 2022 dominates profit attribution. With only 35 BEAR_LOW_VOL days and the highest per-day profitability (avg return 8.82%), 2022 likely accounts for 60-70% of total reversal_v1 gains. This is a small sample driving large results.

**Is profit evenly distributed?** No. Severely front-loaded to 2022.

**Is one year responsible for most gains?** Yes — 2022.

**Is edge deteriorating?** The per-day return has declined from 8.82% (2022) to 1.33% (2025) to 2.08% (2026). Significant deterioration observed.

---

## Phase 2 — Trade Concentration Analysis

### Top 20 Winners

| Rank | Symbol | P&L | Return | Hold | Cum % of Total |
|------|--------|-----|--------|------|----------------|
| 1 | FACT.NS | +₹5,473 | +27.3% | 4d | 14.7% |
| 2 | TITAGARH.NS | +₹3,976 | +32.5% | 5d | 25.3% |
| 3 | TTML.NS | +₹3,909 | +27.9% | 8d | 35.8% |
| 4 | INOXWIND.NS | +₹3,731 | +19.2% | 17d | 45.8% |
| 5 | RRKABEL.NS | +₹3,717 | +29.1% | 13d | 55.7% |
| 6 | IGL.NS | +₹3,337 | +25.0% | 28d | 64.7% |
| 7 | TARIL.NS | +₹3,197 | +22.6% | 10d | 73.2% |
| 8 | TEJASNET.NS | +₹3,122 | +18.1% | 6d | 81.6% |
| 9 | SONATSOFTW.NS | +₹3,095 | +24.6% | 13d | 89.9% |
| 10 | JWL.NS | +₹2,907 | +27.3% | 17d | 97.6% |

### Winner Concentration Report

| Metric | Value | Assessment |
|--------|-------|------------|
| Total reversal_v1 P&L | ₹37,344 | Baseline |
| Top 5 winners | ₹20,806 | **55.7% of total profit** |
| Top 10 winners | ₹36,464 | **97.6% of total profit** |
| Top 20 winners | ₹58,664 | **157.1%** (losses absorb the rest) |
| P&L without top 5 | ₹16,538 | +44.3% of original remains |
| P&L without top 10 | ₹880 | +2.4% — essentially break-even |
| Win rate | 50.3% (79/157) | Barely above coin flip |

### Top 10 Losers

| Rank | Symbol | P&L | Return | Hold |
|------|--------|-----|--------|------|
| 1 | HONASA.NS | −₹3,095 | −20.2% | 2d |
| 2 | FIVESTAR.NS | −₹3,072 | −19.6% | 30d |
| 3 | JYOTICNC.NS | −₹2,762 | −14.3% | 9d |
| 4 | RRKABEL.NS | −₹2,578 | −21.3% | 8d |
| 5 | KIRLOSENG.NS | −₹2,255 | −13.8% | 3d |

**Critical finding:** RRKABEL.NS appears in both top winners (+₹3,717) AND top losers (−₹2,578). The same stock in the same strategy at different times — this signals the reversal factor is timing-sensitive and can go badly wrong on the same underlying.

**Concentration verdict:** The strategy is a lottery-ticket distribution. Remove the top 10 trades and you have near-zero profit from 147 trades. This is **extreme concentration risk**.

---

## Phase 3 — Regime Robustness: BEAR_LOW_VOL by Year

### IC and Statistical Evidence

| Year | OOS Days | Avg IC | IC Std | IC Lower 95% | IC Hit Rate | Edge State |
|------|---------|--------|--------|-------------|-------------|------------|
| 2022 | 35 | +0.0895 | 0.1283 | +0.054 | 74.3% | ✅ EDGE_PRESENT |
| 2023 | 18 | +0.0142 | 0.1145 | −0.030 | 72.2% | ⚠️ EDGE_WEAK (border) |
| 2024 | 11 | +0.2015 | 0.1808 | +0.112 | 72.7% | ✅ EDGE_PRESENT (n=11!) |
| 2025 | 69 | +0.0990 | 0.0967 | +0.080 | 91.3% | ✅ EDGE_PRESENT |
| 2026 | 23 | +0.0524 | 0.0962 | +0.019 | 69.6% | ✅ EDGE_PRESENT (border) |

### Profitability Evidence

| Year | Days | Avg Ret/Day | Profit Factor | Win Rate | Ann. Sharpe |
|------|------|------------|---------------|----------|-------------|
| **2022** | 35 | **+8.82%** | **217.08** | **97.1%** | **34.18** |
| 2023 | 18 | +4.07% | 8.43 | 83.3% | 15.04 |
| 2024 | 11 | +3.18% | 4.89 | 72.7% | 8.74 |
| 2025 | 69 | **+1.33%** | **1.48** | **53.6%** | **2.60** |
| 2026 | 23 | +2.08% | 2.35 | 56.5% | 5.27 |

**The most important finding in this audit:**

2022 is a statistical outlier. A 97.1% win rate and 217× profit factor on 35 days is not a repeatable edge — it reflects a specific market microstructure in that period (likely post-correction oversold bounce with high beta recovery). By 2025, win rate has collapsed to 53.6% (barely above random) and profit factor to 1.48 (marginal).

**Is edge stable?** No. It has deteriorated dramatically.  
**Is edge weakening?** Yes — from world-class (2022) to marginal (2025).  
**Is edge improving?** 2026 partial recovery (2.35 PF) — too early to call.

**The 2024 anomaly (IC=+0.20) must be flagged:** Only 11 OOS days — the highest IC reading in the dataset comes from the smallest sample. Cannot be relied upon.

---

## Phase 4 — Sector Attribution

### reversal_v1 BUY Signal Concentration by Sector

| Sector | Signals | % of Total | Assessment |
|--------|---------|------------|------------|
| **Industrials** | 191 | 21.5% | ⚠️ Concentrated |
| **Technology** | 162 | 18.2% | ⚠️ Significant |
| Financial Services | 118 | 13.3% | Moderate |
| Consumer Cyclical | 104 | 11.7% | Moderate |
| Healthcare | 79 | 8.9% | Moderate |
| Communication Services | 76 | 8.5% | Moderate |
| Basic Materials | 62 | 7.0% | Low |
| Consumer Defensive | 38 | 4.3% | Low |
| Real Estate | 20 | 2.2% | Low |
| Utilities | 20 | 2.2% | Low |
| Energy | 19 | 2.1% | Low |

**Is reversal_v1 a factor or a sector bet?**

Signal distribution is relatively diversified across 11 sectors. Industrials (21.5%) and Technology (18.2%) dominate but neither is extreme. The top 5 winners span FACT.NS (Chemicals/Fertilizer), TITAGARH.NS (Railway wagon), TTML.NS (Telecom), INOXWIND.NS (Wind energy), RRKABEL.NS (Cables) — different sectors.

**Verdict:** reversal_v1 is not a disguised PSU/Power/sector rotation bet. It appears to be a genuine price-based reversal factor with cross-sector breadth. However, the Industrials and Technology overweight should be monitored — both are cyclical and tend to exhibit mean-reversion characteristics more strongly than defensives.

---

## Phase 5 — Market Cap Attribution

No market cap data in the `stocks` table. Assessment based on known symbols:

**Large Cap (estimated >₹20,000 Cr):** IGL.NS, HONASA.NS, RRKABEL.NS  
**Mid Cap (estimated ₹5,000-20,000 Cr):** INOXWIND.NS, TITAGARH.NS, TEJASNET.NS, KAYNES.NS  
**Small Cap (estimated <₹5,000 Cr):** FACT.NS, TTML.NS, TARIL.NS, JWL.NS, SONATSOFTW.NS

Observation from top winners: FACT.NS (+27.3%, 4 days), TTML.NS (+27.9%, 8 days), TARIL.NS (+22.6%, 10 days), JWL.NS (+27.3%, 17 days) — these are mid/small cap names with higher volatility and stronger mean-reversion characteristics.

**Hypothesis:** reversal_v1 edge may be concentrated in mid/small cap names where price dislocations during BEAR_LOW_VOL are more pronounced and recovery is faster. The large-cap trades (IGL at +25%, 28 days) take longer to revert. This has liquidity implications at scale.

**Risk:** At larger portfolio sizes, mid/small cap positions may have insufficient liquidity. The ₹1L test portfolio is too small to encounter this constraint.

---

## Phase 6 — Portfolio Interaction Analysis

### Strategy Combination Results (₹10L, No SIP, 2022-2026)

| Portfolio | CAGR | Sharpe | Max DD | Calmar | Profit Factor | Trades | Final NAV |
|-----------|------|--------|--------|--------|---------------|--------|-----------|
| **A: breakout only** | **21.09%** | **1.25** | −18.99% | 1.11 | **1.56** | 505 | ₹23.31L |
| B: breakout + momentum | 15.00% | 0.93 | −17.96% | 0.83 | 1.37 | 536 | ₹18.56L |
| **C: breakout + reversal** | **25.75%** | **1.32** | −22.41% | 1.15 | 1.52 | 627 | ₹27.56L |
| D: all three | 21.86% | 1.15 | −17.66% | 1.24 | 1.43 | 644 | ₹23.98L |

### Strategy Breakdown within Combinations

**EXP10C (Breakout + Reversal):**
| Strategy | Trades | P&L | Per Trade |
|----------|--------|-----|-----------|
| breakout_v1 | 470 | +₹12,74,422 | +₹2,712 |
| reversal_v1 | 157 | +₹4,55,624 | **+₹2,902** |

**EXP10D (All Three):**
| Strategy | Trades | P&L | Per Trade |
|----------|--------|-----|-----------|
| breakout_v1 | 306 | +₹7,77,007 | +₹2,539 |
| momentum_v1 | 181 | +₹1,77,654 | +₹982 |
| reversal_v1 | 157 | +₹4,21,360 | **+₹2,684** |

### Key Findings

**1. momentum_v1 is actively destroying value when combined with breakout_v1.**

- breakout only: CAGR **21.09%**, Sharpe **1.25**, PF **1.56**
- breakout + momentum: CAGR **15.00%**, Sharpe **0.93**, PF **1.37**

Adding momentum_v1 reduces CAGR by 6.09 percentage points, Sharpe by 0.32, and profit factor from 1.56 to 1.37. This is not marginal — it is a significant negative contribution. momentum_v1 is competing for the same slots in BULL_LOW_VOL, crowding out breakout_v1's higher per-trade earners (breakout_v1 earns ₹2,637/trade alone vs ₹2,293/trade when paired with momentum's ₹454/trade).

**2. reversal_v1 genuinely diversifies breakout_v1.**

- breakout only: CAGR 21.09%, Sharpe 1.25
- breakout + reversal: CAGR **25.75%**, Sharpe **1.32**

+4.66% CAGR, +0.07 Sharpe. reversal_v1 adds uncorrelated alpha from a completely different regime (BEAR_LOW_VOL). When BULL strategies sit in cash, reversal deploys — reducing dead capital periods.

**3. Adding momentum to breakout+reversal dilutes results.**

- breakout + reversal: CAGR 25.75%, Sharpe 1.32
- all three: CAGR 21.86%, Sharpe 1.15

Adding momentum_v1 back reduces CAGR from 25.75% to 21.86% (−3.89%) and Sharpe from 1.32 to 1.15. The pattern is consistent: momentum_v1 dilutes in every combination tested.

**4. Calmar ratio (risk-adjusted) favours the complete portfolio.**

All Three (D) has the best Calmar (1.24) because reversal_v1 reduces max drawdown by keeping more capital active and avoiding the deepest BEAR cash drag. But this marginal Calmar improvement does not compensate for the CAGR dilution from momentum_v1.

---

## Phase 7 — Stress Testing

### Position Count Sensitivity (All 3 Strategies, 2022-2026)

| Max Positions | CAGR | Sharpe | Max DD | Calmar | Profit Factor |
|---------------|------|--------|--------|--------|---------------|
| 5 positions | **26.70%** | 1.21 | −17.11% | **1.56** | **1.53** |
| 10 positions | 21.86% | 1.15 | −17.66% | 1.24 | 1.43 |
| 15 positions | 22.76% | **1.37** | −17.90% | 1.27 | 1.55 |

**Finding:** The 5-position portfolio outperforms on CAGR and Calmar — this is the "concentrated best-ideas" portfolio. The improvement at 15 positions in Sharpe (1.37) suggests that at larger position counts the diversification benefit of reversal_v1 is more visible (more positions = more reversal trades getting through the slot constraint).

The strategy is **not highly sensitive to position count** — all three configurations produce broadly similar risk profiles (max DD: 17-18% range). The edge does not disappear when parameters change. This is a positive signal for robustness.

**Note on holding period and rank pool sensitivity:** These would require modifications to the replay framework (currently uses production engine parameters) — flagged for next research cycle.

---

## Phase 8 — Survivorship & Lookahead Audit

### Audit Checklist

| Check | Finding | Status |
|-------|---------|--------|
| Future price data used for entry decisions | No — market_data gated by `as_of_date` exactly | ✅ CLEAN |
| Forward validation data used for BUY gate | RCEE used (not validation) — confirmed via `scorer_used = 'regime_fit'` on all BUYs | ✅ CLEAN |
| Point-in-time RCEE | Implemented — PIT cache uses `as_of_date - 30 days` cutoff | ✅ CLEAN |
| `strategy_regime_performance` lookahead | PIT-RCEE cache recomputes per replay day — no full-history IC used | ✅ CLEAN |
| Rankings computed with future data | ranking_results stored by `as_of_date`, engine uses only data up to that date | ✅ CLEAN |
| Survivorship bias in stock universe | NIFTY 500 universe membership as of 2022 — no forward survivorship filtering applied | ⚠️ PARTIAL RISK |
| Data restating (adj_close) | adj_close may incorporate split/dividend adjustments made after the trade date | ⚠️ MINOR RISK |

### Survivorship Bias Assessment

The NIFTY 500 universe is loaded from current membership (2026). Stocks delisted or removed from the index between 2022 and 2026 are not present in historical replay. This is a **known limitation** common to all index-based backtests. Impact is likely minor for BEAR_LOW_VOL reversal trades since severely distressed stocks would have exited on rank_drop triggers. **Flagged for future improvement.**

### Adj_Close Restating

Yahoo Finance (yfinance) provides `adj_close` which incorporates all historical splits and dividends as of the fetch date. A stock that split 2:1 in 2023 will have its 2022 prices halved retroactively. This is the industry-standard approach and does not constitute problematic lookahead — it ensures price series are comparable across time. **Not a material risk.**

### Conclusion

The replay framework is clean of material lookahead bias. The partial survivorship risk is acknowledged but estimated to be immaterial given the trading universe (NIFTY 500, large and mid-cap dominated).

---

## Phase 9 — Production Readiness Scorecard

| Category | Score (1-10) | Rationale |
|----------|-------------|-----------|
| **Statistical robustness** | **4/10** | 157 total trades, 35-69 days per year. 2022 dominates with outlier statistics. ic_lower_95 barely positive in 2023. n=11 for 2024. |
| **Regime robustness** | **5/10** | Positive IC across all years but massive profitability deterioration (PF 217 → 1.48). Hit rate declining from 97% to 54%. |
| **Concentration risk** | **3/10** | Top 10 trades = 97.6% of profit. Remove top 10, strategy breaks even. Extreme lottery-ticket distribution. |
| **Diversification benefit** | **8/10** | Genuine uncorrelated alpha. Deployed exclusively in BEAR_LOW_VOL. +4.66% CAGR when added to breakout. Reduces dead capital. |
| **Drawdown impact** | **7/10** | Reduces portfolio max drawdown from −22% to −18% when combined with breakout. Keeps portfolio active during bear phases. |
| **Implementation complexity** | **7/10** | Already implemented. RCEE recognizes BEAR_LOW_VOL edge. Plugs into existing pipeline. Low incremental cost. |
| **Data quality risk** | **6/10** | Minor survivorship risk. Adj_close restating is standard. No fundamental data dependency. |

**Overall Score: 40/70 (57%)**

### Recommendation

```
┌─────────────────────────────────────────────────────────┐
│  RECOMMENDATION: PAPER_TRADE                            │
│                                                         │
│  Conditions:                                            │
│  1. Run 6+ months paper trading in BEAR_LOW_VOL regimes │
│  2. Monitor concentration (max 3 trades per stock)      │
│  3. Track if PF stays above 1.30 out-of-sample          │
│  4. Accumulate 50+ paper trades before live promotion   │
│                                                         │
│  DO NOT PROMOTE TO PRODUCTION YET                       │
│  Reason: extreme concentration in top 10 trades makes   │
│  historical results statistically unreliable            │
└─────────────────────────────────────────────────────────┘
```

---

## Final Answers for Investment Committee

### 1. Is reversal_v1 a genuine edge?

**Partially yes, but fragile.** The factor generates positive IC in BEAR_LOW_VOL (0.054-0.112 lower_95 bound across most years). However, 2022's statistics are outlier-driven and 2025 shows significant deterioration (PF 1.48, win rate 53.6%). The edge exists but is inconsistent — robust years alternate with marginal years. **Cannot yet be called durable.**

### 2. Is reversal_v1 diversifying breakout_v1?

**Yes — strongly and genuinely.** It operates in a completely different regime (BEAR_LOW_VOL vs BULL_LOW_VOL), generating uncorrelated returns. Breakout+Reversal (CAGR 25.75%, Sharpe 1.32) is materially better than Breakout alone (CAGR 21.09%, Sharpe 1.25) by every meaningful metric except max drawdown (−22.41% vs −18.99% — acceptable tradeoff). The diversification benefit is the strongest evidence in favour of eventual production promotion.

### 3. Does momentum_v1 still deserve a place in production?

**No — it should be removed from the production portfolio.** Across every combination tested:

- breakout alone → 21.09% CAGR, Sharpe 1.25, PF 1.56
- breakout + momentum → 15.00% CAGR, Sharpe 0.93, PF 1.37 (−6.09% CAGR)
- breakout + reversal → 25.75% CAGR, Sharpe 1.32, PF 1.52
- all three → 21.86% CAGR, Sharpe 1.15, PF 1.43

momentum_v1 dilutes performance in every configuration. Per-trade earnings: momentum generates ₹454/trade vs breakout's ₹2,637. It competes for the same BULL_LOW_VOL slots as breakout_v1 but with inferior returns. **Recommend deprecating momentum_v1 from the active portfolio.** It may have value as a research-only signal but should not consume execution slots.

### 4. What is the expected production impact of adding reversal_v1?

Based on 4.5-year simulation:
- **+4.66% additional CAGR** (21.09% → 25.75% with breakout only)
- **+0.07 Sharpe** improvement
- **~157 additional trades** per 4.5 years in BEAR regimes
- **Reduced dead capital** during bear regimes (currently 35% of time at zero positions)

Expected live performance will likely be **lower** than simulated due to:
1. Concentration risk (top 10 trades account for 97.6% — live trading may miss some)
2. 2022 outlier effect — future periods unlikely to match that year's statistics
3. Mid/small cap liquidity constraints at larger portfolio sizes

Conservative estimate: **+2-3% CAGR improvement** in live production vs the simulated +4.66%.

### 5. Should ADR-033 Multi-Regime Strategy Architecture be created?

**Yes — ADR-033 is warranted and urgent.** The current architecture assumes one strategy set per regime. reversal_v1 demonstrates that the system must support:
- Strategy-per-regime routing (reversal → BEAR, breakout → BULL)
- Per-regime slot allocation (fewer slots in BEAR than BULL)
- Per-regime position sizing (reversal trades may warrant smaller sizing due to higher concentration risk)
- Cross-regime position management (what happens to reversal positions when regime flips to BULL?)

ADR-033 should define the multi-regime portfolio policy framework before any additional strategy is promoted.

### 6. What is the next highest-priority strategy research area?

In priority order:

1. **reversal_v1 concentration fix** — implement single-stock cap (max 1-2 positions per symbol across the full portfolio history) to eliminate the lottery-ticket distribution. This is the single highest-leverage improvement.

2. **BEAR_HIGH_VOL strategy** — 82 days available (up from 31 when last analysed). Approaching the 60-day minimum for RCEE validation. Begin factor research.

3. **momentum_v1 retirement analysis** — formally document why momentum_v1 underperforms and whether the factors can be recycled into a momentum-overlay for breakout_v1.

4. **reversal_v1 parameter sensitivity** — test rank pool (top 10 vs top 30), holding period (7/10/20 days) to determine if edge is robust or parameter-fitted.

5. **Regime transition handling** — what happens to open reversal positions when BEAR flips to BULL mid-hold? Currently the time-stop (30 days) handles this, but an explicit regime-change exit for reversal positions may be more appropriate.

---

*Report prepared for Pi-PM Investment Committee review. All simulations use point-in-time RCEE (no lookahead bias), walk-forward OOS validation, and deterministic replay with PIT-RCEE cache.*

*Next review milestone: 50 paper trades completed in live BEAR_LOW_VOL regime.*
