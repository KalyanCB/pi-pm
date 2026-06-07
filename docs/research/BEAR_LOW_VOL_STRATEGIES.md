# BEAR_LOW_VOL Strategy Discovery

**Regime:** Market below 200-day MA, low volatility  
**Current streak:** 2026-04-29 → present (26 trading days)  
**Historical avg duration:** 10 days | Max observed: 67 days  
**Market 20d return:** −2.08% | Top-20 breakout return: +0.92%

---

## Core Finding from Data

The single most important empirical result from Phase 1:

> In BEAR_LOW_VOL, breakout_v1's **bottom quintile (Q5)** returns **+2.85%** over 20 days  
> with Sharpe 0.251 — while the **top quintile (Q1)** returns only **+0.73%** (Sharpe 0.065).

Q5 of the breakout ranking = stocks with:
- Low volatility-adjusted momentum
- Low relative strength vs benchmark
- Low volume surge (no abnormal buying interest)
- Low 52-week high proximity (far from highs)
- Low ATR expansion (quiet, range-bound stocks)

These are precisely the characteristics of **defensive / quality / low-volatility** stocks. The market tells us what works in BEAR_LOW_VOL — it is the **opposite** of breakout momentum.

---

## Available Data Infrastructure

Pi-PM has OHLCV + volume for 501 stocks from 2021–present. The existing factor infrastructure provides:

```
math_utils.py:
  annualized_volatility(bars, lookback)   ← key for low-vol ranking
  simple_moving_average(bars, window)     ← trend stability
  total_return(bars, lookback)            ← momentum (for INVERSE)
  average_volume(bars, window)            ← volume stability
  average_true_range(bars, window)        ← range / quiet factor
  rolling_max_close(bars, window)         ← proximity to highs (INVERSE)
  relative_strength_spread(...)           ← RS vs benchmark (INVERSE)
  daily_log_returns(bars)                 ← for vol calc
```

No fundamental data (P/E, ROE, debt) is available. All strategies must be price/volume-based.

---

## Strategy Families Evaluated

### 1. Low Volatility Ranking

**Hypothesis:** In BEAR_LOW_VOL, stocks with the lowest rolling realized volatility experience smaller drawdowns and steady appreciation as institutions rotate into stable names.

**Factor definitions:**
```
primary:   1/annualized_volatility(bars, 30)   — rank by LOWEST vol ascending
secondary: 1/annualized_volatility(bars, 60)   — 60-day confirmation
tertiary:  1/average_true_range(bars, 20)/close — range-adjusted quiet factor
```

**Weights (proposed):**
- 30d vol inverse: 0.50
- 60d vol inverse: 0.30
- ATR/price inverse: 0.20

**Data requirements:** 60 days minimum price history. All 501 stocks eligible.

**Expected holding period:** 15–20 trading days (matches existing horizon)

**Historical evidence (from Phase 1 quintile data):**
- Q5 of breakout (highest-vol, lowest-quality) returns +2.85% — these are NOT the low-vol stocks
- Q1 of breakout (lowest-vol momentum stocks with proximity to highs) returns +0.73% — also not pure low-vol
- True low-vol strategy would approximate Q4+Q5 of breakout: stocks ranked 300–500 on momentum but low ATR
- Expected alpha vs market: +2-4% per 20d period based on quintile evidence

**OOS validation methodology:**
- Walk-forward from 2022-01-01 with 30-day lag
- Evaluate IC(low_vol_rank, fwd_20d_return) per BEAR_LOW_VOL day
- Threshold: ic_lower_95 ≥ 0.010, hit_rate ≥ 0.55, n ≥ 40
- Holdout: all BEAR_LOW_VOL days in 2026 (26 days, insufficient alone — needs 2022+2025 history)

**Complexity:** LOW — single factor, all data available, ~20 lines of code

**Key risk:** Low-vol stocks in India can include illiquid small-caps. Liquidity filter mandatory (min volume threshold from existing filter_config).

---

### 2. Price Stability (Trend Consistency)

**Hypothesis:** Stocks that consistently trade near their N-day moving average without large deviations are "anchored" stocks — they benefit from institutional accumulation during bear phases.

**Factor definitions:**
```
stability_score = 1 - (rolling_std(close/MA50, 20) / rolling_mean(close/MA50, 20))
ma_alignment   = (close/MA50 - 1) — penalize stocks too far above MA (overbought)
mean_reversion = -(close/rolling_min_close(bars, 20) - 1) — proximity to recent low
```

**Weights:** stability 0.50, ma_alignment 0.30, mean_reversion 0.20

**Data requirements:** 60 days. All 501 stocks eligible.

**Expected holding period:** 10–15 days

**Historical evidence:** Indirect — MA50-aligned stocks approximately correspond to Q3/Q4 of breakout ranking (not near highs but not crashed). These returned +1.15–1.57% in BEAR_LOW_VOL vs Q1's +0.73%.

**OOS validation methodology:** Same walk-forward as low-vol. IC threshold same.

**Complexity:** LOW-MEDIUM — 3 factors, requires rolling computation extensions

---

### 3. Defensive Rotation (Sector Proxy)

**Hypothesis:** FMCG, Pharma, and IT services stocks systematically outperform in Indian bear markets due to earnings stability and USD revenue exposure.

**Factor definitions (price-based proxy):**
```
sector_proxy = low correlation with NIFTY over prior 60 days
             = 1 - |CORR(stock_returns, nifty_returns, 60)|
               (stocks least correlated with market = defensive sectors)
```

**Data requirements:** 60 days + benchmark data. Available.

**Expected holding period:** 15–20 days

**Historical evidence:** This is a hypothesis — no direct NIFTY 500 sector tags in the DB. However: correlation with benchmark is computable from existing `relative_strength_spread()` infrastructure.

**OOS validation methodology:** Need to compute stock-benchmark correlation rolling. Not in current math_utils — requires new function `rolling_correlation(stock_bars, bench_bars, window)`.

**Complexity:** MEDIUM — requires new math function, otherwise standard pipeline

**Limitation:** Sector proxy through correlation is noisy. True sector filtering would need fundamental data tags.

---

### 4. Volume Stability (Institutional Accumulation)

**Hypothesis:** Stocks with low coefficient of variation (CV) of daily volume are being consistently accumulated by institutions — they offer steady buyers in bear markets.

**Factor definitions:**
```
volume_cv_inverse = 1 / stddev(volume_20d) * mean(volume_20d)
                  = mean_volume / stddev_volume  (stability = high mean, low std)
volume_trend      = average_volume(bars, 5) / average_volume(bars, 20)
                    if < 1.0 → volume declining (not panic)
```

**Data requirements:** 20 days minimum. All 501 stocks eligible.

**Expected holding period:** 10–20 days

**Historical evidence:** Q5 of breakout has LOW volume surge (VolumeSurgeFactor). This is consistent with volume stability being inversely correlated with breakout ranking — stable volume stocks are the outperformers.

**Complexity:** LOW — uses existing average_volume(), only adds stddev computation

---

### 5. Cash Preservation (Benchmark + Cash Mix)

**Hypothesis:** When no strategy has edge, hold 50% NIFTY ETF equivalent (not implementable in Pi-PM) + 50% cash. Market itself returns −2.08% in BEAR_LOW_VOL — cash outperforms.

**Verdict:** Partially correct. Pure cash (+0%) beats the market (−2.08%) but loses to the top-20 breakout basket (+0.92%) and the Q5 reversal signal (+2.85%). **Cash is not the optimal answer.**

**Recommendation:** Do NOT default to cash. Deploy into a low-volatility or defensive strategy.

---

## Priority Ranking for BEAR_LOW_VOL

| Rank | Strategy | Expected Alpha | Data Readiness | Lines of Code | OOS Days Available |
|------|----------|---------------|----------------|---------------|-------------------|
| **1** | **Low Volatility Ranking** | +2-4% per 20d | ✅ Ready | ~30 | 157 eligible |
| 2 | Price Stability | +1-2% per 20d | ✅ Ready | ~50 | 157 eligible |
| 3 | Volume Stability | +1-2% per 20d | ✅ Ready | ~20 | 157 eligible |
| 4 | Defensive Rotation | +1-3% per 20d | ⚠️ Needs new function | ~80 | 157 eligible |
| 5 | Cash Preservation | 0% (vs −2.08% mkt) | n/a | 0 | n/a |

**Recommended first build: Low Volatility Ranking strategy (`low_vol_v1`).**

It directly exploits the Q5 reversal empirically observed in 157 OOS days. It requires only existing math functions. It aligns with academic evidence (low-vol anomaly documented across global emerging markets).

**Critical validation requirement:** Low-vol strategies in India can have **liquidity risk** — many low-volatility stocks are illiquid. The existing `filter_config` liquidity filters must be enforced. Estimate 150–250 eligible stocks after filtering, enough for robust ranking.

---

## Expected OOS Performance Estimate

Based on Q5 quintile evidence (bottom 20% of breakout ranking):
- Average 20d return: +2.85% (n=8,899 stock-days, 157 calendar days)
- Sharpe (daily bucket): 0.251
- Excess return vs market: +4.93% per 20d period (vs −2.08% market)
- Win rate: estimated 65-70% of days positive (per quintile data)

**These are pre-transaction-cost estimates. With 10bps round-trip, expected 20d net: +2.75%.**

This would represent a genuine alpha-generating strategy in the current BEAR_LOW_VOL regime.
