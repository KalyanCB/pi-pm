# Second Opinion: Independent Quant Review of Pi-PM Strategy Research

**Reviewer:** Independent Principal Quant Researcher & Portfolio Architect  
**Date:** 2026-06-06  
**Mandate:** Find flaws. Do not optimize for agreement. Real money at stake.

---

## Prefatory Note

The Pi-PM team has done substantial, rigorous work. The RCEE framework is architecturally sound, the replay engine has genuine point-in-time protections, and the statistical methodology is better than most systematic trading research I encounter. This review is therefore not a dismissal — it is a stress test. Several conclusions survive scrutiny. Several do not.

---

## PART A — Challenging Every Major Conclusion

### A1. "breakout_v1 is production ready"

**Challenge: Partially valid, but incomplete evidence.**

The reported Sharpe of 1.25 is the *blended* Sharpe including cash periods. When the portfolio is in cash, daily NAV change = 0. Adding ~30% of days with zero return to the distribution **reduces the mean return proportionally more than it reduces standard deviation**, artificially deflating the Sharpe below what it would be if the strategy were always invested.

The actual in-market Sharpe (computed only on BULL_LOW_VOL months, 41 months) is **2.04** — materially higher.

**This is not inflation — this is deflation of reported Sharpe.** The strategy looks safer than it is when in-market, and the Sharpe understates its in-market edge. A CIO needs both numbers.

More critically: **CAGR of 21.09% on the NIFTY 500 universe over 2022-2026 must be benchmarked.** NSE-listed mid/small caps experienced a significant bull run in 2023-2024. NIFTY 500 TRI returned approximately 15-18% CAGR over this period. The actual alpha over passive buy-and-hold is therefore **~3-6 percentage points**, not 21%. On a risk-adjusted basis, you are taking concentration and timing risk for 3-6% incremental return over index. Is that justified? That question has not been asked.

**t-statistic for breakout_v1 IC:** 11.55 on 748 daily observations. Superficially very strong. But these are **overlapping 28-day windows** — two consecutive days share 27 of 28 days of return data. The effective degrees of freedom (Newey-West adjusted) may be closer to 748/28 ≈ 27, giving a corrected t-stat of approximately **11.55/√28 ≈ 2.18**. Still significant, but barely. And at that level, in-sample overfitting becomes a genuine concern.

**Verdict on A1:** breakout_v1 shows real edge. The t-stat survives even autocorrelation correction. BUT: (a) alpha over passive is modest, (b) in-market risk is higher than reported Sharpe suggests, (c) the strategy must demonstrate out-of-sample periods it was NOT designed for. Currently there are none — the entire 2022-2026 window was the development period.

---

### A2. "momentum_v1 should be retired"

**Challenge: This conclusion is almost certainly wrong. It is a portfolio construction artifact.**

The comparison is:
- Breakout alone: 5 slots × 365 days = 1,825 potential slot-days → 505 actual trades
- Breakout + Momentum: 5 slots shared between 2 strategies → each strategy gets ~265 trades

When breakout_v1 has exclusive access to 5 slots, it selects its best 5 signals. When it shares with momentum_v1, it may only get 2-3 slots per day. The inferior results of the combination reflect **slot competition**, not evidence that momentum_v1 adds negative value.

**The correct experiment** would give each strategy its own independent slot budget (e.g., breakout gets 5 slots, momentum gets 5 slots, total 10 positions). This experiment was never run.

Further: breakout and momentum factors are known to be complementary in academic literature. Breakout captures price-level signals (proximity to highs, ATR expansion) while momentum captures trend persistence (rate-of-change). Discarding momentum_v1 based on slot-competition results is statistically unjustified.

**Additionally:** momentum_v1's per-trade alpha (₹454/trade, ₹982/trade in EXP10D) being lower than breakout's does NOT mean it has no edge. If momentum's trades are in different stocks at different times, they could be diversifying even at lower per-trade returns. Return-per-trade is not the right metric — information ratio or standalone Sharpe is.

**Verdict on A2:** "Retire momentum_v1" is premature and the evidence does not support it. The conclusion is driven by a flawed experimental design. This is the most significant research error in the current body of work.

---

### A3. "reversal_v1 has real edge"

**Challenge: The statistical evidence is strong in aggregate but the sample structure is critically weak.**

The t-statistic for reversal_v1 IC in BEAR_LOW_VOL: **9.11** on 156 days. After autocorrelation correction (28-day overlapping windows): effective t ≈ 9.11/√28 ≈ **1.72**. This is marginally significant at 10% but NOT at 5%.

More damning: the 156 "days" come from **20 BEAR_LOW_VOL episodes**, and the distribution of episode lengths is:

| Episode | Days | Contribution |
|---------|------|-------------|
| 1-9 (2022 micro-episodes) | 1-31 days each | 51 days total |
| 10-12 (2023) | 1-16 days | 18 days |
| 13-14 (late 2024) | 4-8 days | 12 days |
| 15 (2025 major) | 67 days | 67 days |
| 16-17 (2025-26 micro) | 1 day each | 2 days |
| 18-20 (2026) | 1-28 days | 44 days |

Truly **independent regime episodes** (where episode length > holding period of 13 days): 3-4 episodes. The rest are micro-episodes too short for the 13-day hold to complete within the regime.

The **effective number of independent reversal_v1 "bets"** in the regime sense is approximately 4-5. This is an extraordinarily small sample for production deployment of any strategy, let alone one with extreme profit concentration.

The profit concentration finding from the internal review is the correct red flag: top 10 trades = 97.6% of total profit. But the internal review understates the severity. RRKABEL.NS appears as both the 5th-largest winner (+₹3,717) AND the 4th-largest loser (−₹2,578) in the **same strategy**. The reversal factor is applying to the same stock in different periods with wildly different outcomes. This is not edge — this is volatility monetization with high variance. The expected value may be positive but the confidence interval around that estimate is enormous.

**Verdict on A3:** reversal_v1 IC is real but not cleanly significant after autocorrelation correction. The effective sample is 4-5 independent episodes, not 156 days. Paper trading is correct but for the wrong reason given in the internal report — the issue is not "concentration," it is "insufficient independent observations."

---

### A4. "RCEE is correctly designed"

**Challenge: The RCEE has a circularity problem and a threshold selection problem.**

**Circularity:** The strategies were designed with domain knowledge of the NSE market. The RCEE thresholds (ic_lower_95 ≥ 0.010, hit_rate ≥ 0.55, n ≥ 60) were calibrated after observing the strategies' IC by regime. The regimes used to design RCEE were constructed using the same benchmark and parameter choices that informed strategy design.

This is analogous to: (1) you design a fishing net with 2-inch holes, (2) you measure that it catches fish larger than 2 inches, (3) you conclude that fish smaller than 2 inches don't exist in the ocean.

A genuinely out-of-sample RCEE validation would require: thresholds set before strategy development, on an independent dataset, or through a formal cross-validation process where strategies and thresholds are developed on non-overlapping data. This has not been done.

**Threshold selection:** The 18% annualized volatility threshold for LOW_VOL/HIGH_VOL classification — where did this come from? It is hardcoded in the regime detection code. Was it chosen by looking at the data and selecting the threshold that produced the cleanest regime classification? If so, it is overfit to the historical period and will likely mis-classify future regimes.

**The 200 DMA response function:** The binary BULL/BEAR classification creates a cliff edge. NIFTY at 200 DMA + 0.1% = BULL. NIFTY at 200 DMA − 0.1% = BEAR. Near the boundary, regime flips daily. The episode analysis above shows 9 BEAR_LOW_VOL episodes of 1-2 days — these are likely "boundary chatter" rather than genuine regime shifts. A position opened on a 1-day BEAR episode and held for 13 days will experience 12 of those 13 days in BULL — completely invalidating the regime premise for that trade.

---

## PART B — Three Risks That Could Invalidate Everything

### Risk 1: Strategy-Regime Co-Design Bias (Overfitting)

This is the paramount risk. The strategies, the RCEE, and the regime model were all developed by the same team with knowledge of the same historical data. The probability that the observed BULL_LOW_VOL edge for breakout_v1 is partly spurious is material. 

**Quantification:** With 4 regimes × 2+ strategies × multiple parameters, there are hundreds of regime-strategy combinations that could be tested. The ones with positive IC are shown; the ones with negative IC are discarded. This is multiple-testing without correction. The Bonferroni correction for 16 regime-strategy combinations (4 regimes × 4 strategies) would require t > 3.09 for 5% significance — breakout_v1's autocorrelation-corrected t of ~2.18 would fail this test.

**Consequence if real:** The first live year will show significantly lower IC than simulated, and RCEE will fail to classify regimes correctly, generating WATCH signals when BUYs were expected.

### Risk 2: BEAR_LOW_VOL Episode Scarcity

The reversal_v1 strategy has traded through **3-4 meaningful independent regime episodes**. The strategy_regime_performance table shows ic_lower_95 = +0.072 for reversal_v1 in BEAR_LOW_VOL. This appears robust. But the 2022 episode alone (31 days, profit factor 217) dominates the statistics so completely that without it, the remaining evidence (3 episodes, ~100 days) would show much weaker edge.

**Consequence if real:** The next BEAR_LOW_VOL episode (happening right now as of June 2026) may produce mediocre results, causing the RCEE to downgrade edge classification and halt BUYs mid-paper-trade period. The system would show a different pattern from simulation simply because of regime episode randomness.

### Risk 3: Transaction Cost Underestimation

The replay models:
- Slippage: 5 bps
- Fee: ₹20 flat per leg

Actual NSE trading costs:
- Brokerage: ₹20 (Zerodha) ✓
- Securities Transaction Tax (STT): 0.1% on delivery (10 bps per side = 20 bps round-trip)
- Exchange transaction charges: 0.00345% (3.45 bps)
- GST on brokerage: 18% × brokerage
- SEBI charges: 0.0001%
- Stamp duty: 0.015% on buy side
- **Total realistic round-trip: ~35-40 bps**

The replay uses **5 bps slippage + ₹20 flat** which underestimates by approximately 25-30 bps per round-trip.

With 536 trades over 4.5 years (EXP10B), the annual trade count is ~119. At 30 bps additional cost per round-trip on a portfolio averaging ₹5-10L deployed:
- Annual deployed capital: ~₹7L average
- 119 trades × ₹7L average position size (per-trade) ≈ ₹8.4L in annual turnover per strategy
- Additional cost: ₹8.4L × 30 bps = ₹2,520/year
- On ₹10L portfolio: ~0.25% CAGR drag per strategy

This is modest at ₹10L scale but will compound at larger sizes and disproportionately impact mid/small cap trades (wider bid-ask spreads).

---

## PART C — Is the Replay Methodology Sufficient for Live Capital?

**Direct answer: No. For paper trading: Conditionally yes. For any live capital: No.**

### What the replay does well:
- Point-in-time RCEE cache (eliminates key lookahead bias)
- Close-price-of-day as fill assumption (reasonable for EOD systems)
- No future validation data in entry gate (RCEE replaced validation gate)
- Deterministic and reproducible

### What the replay does not model:
1. **Market impact** — buying at the close price assumes infinite liquidity. For mid/small caps constituting the best reversal_v1 trades, you cannot buy ₹70,000+ at close without moving the price.
2. **Execution timing** — an EOD order decision system requires knowing the close price to make the decision, but the decision gates on the close price. In reality, orders are placed before close (15:15 on NSE for CNC). The effective fill would be 15:15 price, not exactly the close.
3. **Position concentration within a day** — when max_buy_slots=5 and you place 5 market orders at 15:15, you are in a lineup with every other system-trader doing the same thing. Slippage is correlated across positions.
4. **Dividend and corporate action handling** — the adj_close adjustment is retrospective. A stock going ex-dividend during a 13-day hold period creates a price gap that is not captured in the replay.
5. **Weekend and holiday effects** — positions held over long weekends and holiday clusters have different distribution profiles. The 13-day average hold spans approximately 3 trading weeks — holiday clustering affects this.

### The missing out-of-sample test:

The entire 2022-2026 period was used for **both strategy development and strategy evaluation**. There is no truly out-of-sample window. An acceptable OOS test would require:
- **At minimum:** Walk-forward cross-validation where the strategy is designed on 2022-2023 and evaluated on 2024-2026
- **Better:** A synthetic OOS using data from a different market (SGX Nifty, or Indian pre-2021 data)
- **Best:** Simply waiting: deploy on paper in 2026-H2, evaluate in 2027

---

## PART D — Additional Experiments Required

### Before Production Deployment of breakout_v1:

1. **Walk-forward OOS test** — Train on 2022-2023 only. Evaluate on 2024-2026 holdout. The RCEE thresholds must be set using only 2022-2023 data. This has not been done.

2. **Realistic transaction cost simulation** — Re-run EXP05 with 35 bps round-trip cost instead of 5 bps. If CAGR falls below 18%, the breakeven alpha over passive becomes questionable.

3. **Position sizing sensitivity** — The conviction-band based sizing (EXCEPTIONAL=1.15× budget, HIGH=1.0×, MEDIUM=0.75×) needs validation. Does higher conviction actually predict better outcomes? Test conviction_band as a predictor of per-trade returns.

4. **Strategy performance by BULL_LOW_VOL sub-period** — Does breakout work equally well in all BULL regimes, or is it concentrated in high-momentum BULL environments? The 2022-2024 BULL included a major SME/midcap bull run in India that may not repeat.

5. **Correct momentum_v1 experiment** — Run momentum_v1 with its OWN 5-slot budget (independent of breakout), across the same period. Compare standalone momentum Sharpe to standalone breakout Sharpe.

### Before Paper Trading of reversal_v1:

1. **Single-stock concentration limit** — Implement a rule: maximum 1 position per symbol across any rolling 60-day window. Rerun EXP08 with this constraint. If total profit collapses (RRKABEL.NS wins AND loses, TTML.NS appears twice, SONATSOFTW.NS appears twice), the edge largely disappears.

2. **Episode-level performance analysis** — Calculate P&L per BEAR_LOW_VOL episode (not per day, not per trade). With 20 episodes, what is the win rate at episode level? How many of the 20 episodes were profitable?

3. **Micro-episode filter** — Episodes shorter than 5 days are "boundary chatter" from the regime classifier. No positions should be opened in episodes that begin and end within 5 days. Re-run reversal_v1 excluding these. What happens to returns when episodes 1, 4, 5, 7, 8, 9, 10, 11, 16, 17 (all ≤ 2 days) are excluded?

4. **Autocorrelation-corrected IC significance** — Formally compute Newey-West HAC standard errors on the IC time series with lag = 28. The t-statistic reported (9.11) is not valid for serially correlated data. The corrected statistic is the appropriate gate.

### Before Retiring momentum_v1:

1. **Independent slot test** — Run momentum_v1 alone with 5 slots (EXP12_MOMENTUM_ONLY). Compare its standalone CAGR and Sharpe to breakout_v1 alone. If momentum has positive standalone Sharpe, retirement is premature.

2. **Correlation analysis** — Compute correlation of daily returns between breakout_v1 and momentum_v1 within BULL_LOW_VOL. If correlation < 0.5, they are meaningfully independent despite targeting the same regime, and combining them with separate budgets would improve portfolio diversification.

---

## PART E — CIO Decision: If Real Money Were at Stake Today

| Strategy | Decision | Rationale |
|----------|----------|-----------|
| **breakout_v1** | **Paper Trade → Production in 6 months** | Real IC (t=11.55, corrected ~2.18), genuine regime gating. But: no true OOS period, benchmarking against passive needed. Paper trade with full transaction costs for 6 months. If Sharpe remains >1.0 and alpha >3% over NSE 500, promote. |
| **momentum_v1** | **Research More** | The "retire" conclusion is wrong. Run it standalone first. If standalone Sharpe >0.8, give it its own slot budget alongside breakout. Do not discard a strategy based on slot competition. |
| **reversal_v1** | **Research More** | Despite high aggregate t-stat (9.11), only 3-4 independent regime episodes. Cannot distinguish edge from lucky draw on small samples. Apply micro-episode filter, single-stock concentration cap, and re-evaluate. If edge survives, THEN paper trade. |

**Note:** I would NOT move breakout_v1 to live capital until a genuine walk-forward OOS evaluation is complete, even with 6 months of favorable paper trading. The in-sample period is the entire design period.

---

## PART F — Is the Regime Architecture Correct?

### Challenge 1: The 200 DMA is Crowded Information

The 200-day moving average of NIFTY 500 is monitored by every mutual fund, FII, and retail participant in the Indian market. When price approaches 200 DMA, it becomes a self-fulfilling support/resistance level. The regime signal you are using is the most-watched technical level in the market.

This creates two opposing effects:
1. **Mean-reversion amplification near 200 DMA** — Markets tend to bounce off 200 DMA, meaning BEAR regimes triggered at 200 DMA often reverse quickly. This could explain why reversal_v1 (mean reversion) works in BEAR_LOW_VOL — it's not a regime effect, it's a 200 DMA bounce effect.
2. **Edge decay** — If enough capital uses 200 DMA-triggered regime strategies, the arbitrage disappears.

**Alternative regime definition to test:** Replace 200 DMA binary with a z-score of current price vs 6-month rolling mean (normalized distance). This would create a continuous regime variable rather than a binary cliff, eliminating boundary chatter and providing more stable classification.

### Challenge 2: Volatility Threshold is Arbitrary

The 18% annualized volatility threshold splits LOW_VOL and HIGH_VOL. Source: hardcoded in `app/validation/regimes.py`. This number was not derived from factor analysis, cross-validation, or regime stability testing. It was chosen by the developer.

Test required: What happens to RCEE edge classifications at 15% and 21% thresholds? If the breakout_v1 edge in BULL_LOW_VOL disappears at a different threshold, the 18% choice is overfit.

Additionally: 30-day rolling volatility to classify a regime that is traded with a 13-day hold is **temporally inconsistent**. You are using backward-looking 30-day volatility to classify a forward 13-day trading regime. If volatility spikes on day 31 (one day outside your measurement window), the regime is unchanged despite the market being in a completely different risk environment.

### Challenge 3: Four Regimes May Be Too Few — or Too Many

**Too few:** The NIFTY 500 index has distinct sub-regimes within BULL_LOW_VOL:
- Early-cycle BULL (rising earnings expectations)
- Mature BULL (valuation-driven, narrowing breadth)
- Momentum-driven BULL (speculative, small-cap leadership)

breakout_v1 likely behaves differently in each. The strategy may appear robust in BULL_LOW_VOL because 2023-2024 was a momentum-driven BULL, which is the exact environment breakout strategies are designed for. In an early-cycle or mature-BULL environment, performance could differ materially.

**Too many:** With only 28-47 OOS days in BULL_HIGH_VOL and BEAR_HIGH_VOL, these regimes are effectively unclassifiable. The four-regime model creates regime cells with insufficient data to make statistically valid decisions. A two-regime model (BULL vs BEAR, ignoring volatility) would be better for strategy gating until more data is available.

### Challenge 4: Index-Level Regime for Stock-Level Trading

NIFTY 500 regime classification is applied uniformly to individual stock trades across sectors. A stock in the FMCG or Pharma sector often has near-zero correlation with the NIFTY 500 in BEAR phases (defensive sectors). Classifying FMCG stocks as "in BEAR regime" because NIFTY is below 200 DMA may be incorrect for those specific stocks.

Reversal_v1's sector distribution shows Healthcare (8.9%) and Consumer Defensive (4.3%) — precisely the sectors that don't follow index regime logic. These stocks may be generating their reversal signals for completely different reasons than the regime framework assumes.

**Alternative to consider:** Per-sector regime classification, or stock-level relative strength against sector average instead of NIFTY index.

### Could a Better Regime Model Materially Change Conclusions?

**Yes — significantly.** If the volatility threshold is optimized differently, the number of BULL_LOW_VOL days changes, altering the entire IC calculation and RCEE edge classification. If the 200 DMA is replaced with a smoother indicator, boundary chatter disappears and reversal_v1's micro-episode problem resolves. If two regimes replace four, momentum_v1's performance in BULL (undifferentiated from BULL_LOW_VOL and BULL_HIGH_VOL) might look very different.

The regime model is the foundation of the entire RCEE architecture. It has been specified without out-of-sample validation and without parameter sensitivity analysis. This is the most important unvalidated assumption in the system.

---

## PART G — Final Investment Committee Memo

**TO:** Pi-PM Investment Committee  
**FROM:** Independent Principal Quant Researcher  
**RE:** Pi-PM Strategy Research — Second Opinion  
**SUBJECT:** Findings, disagreements, and required actions before capital commitment

---

### What I Agree With

1. **RCEE concept is correct.** Regime-conditional edge gating is the right architecture for systematic trading in a regime-shifting market like India. The framework is well-designed.

2. **breakout_v1 shows genuine IC.** The t-statistic (11.55 raw, ~2.18 autocorrelation-corrected) is positive and the regime specificity is real. This is not random noise.

3. **reversal_v1 diversifies by regime.** It genuinely operates in a different market environment. Regime diversification is structurally valuable regardless of the specific edge strength.

4. **Lookahead controls are real.** The PIT-RCEE cache and as_of_date gating are properly implemented. The team deserves credit for taking this seriously.

5. **Paper trading is the right next step** — but not production.

---

### What I Disagree With

1. **"momentum_v1 should be retired."** This conclusion is a portfolio construction error masquerading as a strategy evaluation. The experiment was flawed. Before retirement, momentum_v1 must be evaluated standalone with its own slot budget.

2. **"reversal_v1 is ready for paper trading."** The effective sample is 3-4 independent regime episodes, not 156 days. With autocorrelation correction, the t-stat is borderline. The micro-episode filter and single-stock concentration cap must be implemented and validated first.

3. **"breakout_v1 CAGR of 21% represents strong outperformance."** This has not been benchmarked against passive NSE 500 buy-and-hold with dividends reinvested. If the benchmark returned 17% CAGR over the same period, the strategy's alpha is ~4%, not 21%. This is a profoundly important reframing.

4. **"The regime model is correctly calibrated."** The 18% volatility threshold has not been sensitivity-tested. The 200 DMA boundary chatter creates spurious regime episodes. The four-regime model has insufficient data in two of four cells.

5. **"In-sample evidence is sufficient for production."** There is no out-of-sample period. The entire 2022-2026 window is both the development and evaluation period.

---

### Evidence Still Missing

| Missing Evidence | Criticality | Time to Obtain |
|-----------------|-------------|----------------|
| Walk-forward OOS test (train 2022-23, test 2024-26) | **Critical** | 1-2 weeks |
| Autocorrelation-corrected t-statistics (Newey-West) | **Critical** | 1-2 days |
| Benchmark comparison (NSE 500 TRI vs strategies) | **Critical** | 1 day |
| Realistic transaction costs (35 bps vs 5 bps) | **High** | 1 day |
| momentum_v1 standalone with own slot budget | **High** | 1 day |
| reversal_v1 with micro-episode filter (<5 days excluded) | **High** | 2 days |
| reversal_v1 with single-stock concentration cap | **High** | 1 day |
| Volatility threshold sensitivity (15%, 18%, 21%) | **Medium** | 2 days |
| Per-episode P&L for reversal_v1 (20 episodes) | **Medium** | 1 day |
| Conviction band vs actual per-trade return validation | **Medium** | 2 days |

---

### What Could Blow Up in Live Trading

In order of probability × severity:

**1. In-sample overfitting materializing (High × High)**
First 6-12 months of live trading show IC ~50% of simulated. RCEE reclassifies edge as EDGE_WEAK. BUYs stop. Capital sits in cash. Opportunity cost. The regime framework designed for observed 2022-2026 market conditions does not transfer cleanly to 2026-2027.

**2. reversal_v1 micro-episode problem (Medium × Medium)**
The current BEAR_LOW_VOL streak (started April 29, 2026) ends before open reversal positions can close. Positions entered in a BEAR episode get held through regime flip to BULL. The regime-change exit trigger fires (R-EXIT-03), creating forced exits at potentially unfavorable times. The exit logic for cross-regime position management has not been fully tested.

**3. Liquidity at scale (Low × High)**
Once the system manages more than ₹25-30L (2-3 million INR), mid/small cap positions will move markets. FACT.NS (which generated the largest reversal_v1 winner at +27.3%) has limited daily volume. An institutional-size position would not fill at close price. The simulation's best trades become unreachable at scale.

**4. Transaction cost erosion (Medium × Medium)**
With realistic 35-bps round-trip costs, annual CAGR degrades by 1-2 percentage points. For breakout_v1 alone, CAGR falls from 21% to 19-20%. Still acceptable. But this narrows the margin for error.

**5. Regime misclassification at 200 DMA boundary (Low × Medium)**
Extended periods of NIFTY oscillating around 200 DMA generate multiple 1-2 day regime flips. The reversal strategy opens positions that immediately face a regime-change exit trigger. Net result: frequent entries and forced exits near 200 DMA with negative expectancy due to transaction costs on short holds.

---

### What Should Be Done Next

**Week 1 (Critical path, no capital deployment until complete):**
1. Compute Newey-West corrected t-statistics for all strategy-regime IC pairs
2. Benchmark all replay results against NIFTY 500 TRI passive buy-and-hold
3. Re-run EXP10B with momentum_v1 given its own independent 5-slot budget (EXP12_MOMENTUM_INDEPENDENT)
4. Re-run EXP10C with 35-bps transaction costs (EXP13_REALISTIC_COSTS)

**Week 2 (reversal_v1 validation):**
5. Apply micro-episode filter (exclude BEAR_LOW_VOL episodes < 5 days)
6. Apply single-stock concentration cap (max 1 position per stock per 60-day window)
7. Compute per-episode P&L for reversal_v1 across all 20 episodes
8. Re-evaluate reversal_v1 IC with episode-level autocorrelation correction

**Week 3-4 (Walk-forward OOS):**
9. Train all strategies using only 2022-2023 data
10. Calibrate RCEE thresholds using only 2022-2023 IC
11. Evaluate OOS performance on 2024-2026 holdout
12. If OOS IC > 0 and t > 1.65 corrected: confirm production readiness
13. If OOS IC ≈ 0: significant overfitting — restart research process

**Month 2-6 (Conditional paper trading):**
If and only if walk-forward OOS confirms edge:
- Paper trade breakout_v1 with realistic costs
- Continue accumulating reversal_v1 regime episodes for statistical power
- Do NOT paper trade reversal_v1 until micro-episode and concentration fixes are validated

---

### Final Verdict

**breakout_v1:** Research More → Walk-Forward OOS validation required. Evidence is promising but insufficient for production commitment.

**momentum_v1:** Research More → Not "retire." Run standalone experiment first.

**reversal_v1:** Research More → Not "paper trade" yet. Episode filter, concentration cap, and corrected statistics needed first.

**Regime architecture:** Research More → Sensitivity analysis on volatility threshold and alternative regime models required.

The Pi-PM system is architecturally sophisticated and the team's statistical rigor is above average. But the fundamental issue is that 2022-2026 was both the laboratory and the examination hall. No exam taken in your own laboratory is valid. The next step is finding the examination hall — a genuinely out-of-sample window — and sitting the test there.

*This review reflects my independent judgment. I have no stake in any outcome. I would make the same recommendations if my own capital were at risk.*

---

*Prepared for Pi-PM Investment Committee*  
*Independent Review — Not for circulation without authorization*
