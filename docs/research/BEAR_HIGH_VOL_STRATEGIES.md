# BEAR_HIGH_VOL Strategy Discovery

**Regime:** Market below 200-day MA, elevated volatility  
**Historical avg duration:** 8 days | Max observed: 23 days  
**OOS sample:** breakout_v1 = 31 days, momentum_v1 = 47 days  
**Market 20d return:** −4.62% | Top-20 breakout return: +4.61%

---

## Critical Caveat

**31–47 OOS days is not sufficient for statistical strategy validation.**

To put this in context: EDGE_PRESENT classification requires 60+ sample days. We have 31 for breakout and 47 for momentum in BEAR_HIGH_VOL. Any IC computed from this data has very wide confidence intervals. The profit factor of 20.09 for breakout_v1 in this regime is inflated by small sample noise.

**Any strategy built for BEAR_HIGH_VOL will face a chicken-and-egg problem: you need ~100 more BEAR_HIGH_VOL days to validate before deploying.**

Historical BEAR_HIGH_VOL duration: avg 8 days, max 23 days. At this rate, accumulating 100 validation days requires ~6-8 years of real-time observation or a deliberate backfill from NSE data prior to 2021.

---

## What the Data Actually Shows

Despite the small sample, the directional signal is strong:

**breakout_v1 BEAR_HIGH_VOL (31 days):**
- Top-20 returns +4.61% while market returns −4.62% → 9.23% relative outperformance
- BUT: Decile D10 (+7.47%) beats D1 (+5.09%) — inversion again, though weaker
- Win rate 87.1% — almost all days positive return in top-20

**momentum_v1 BEAR_HIGH_VOL (47 days):**
- Top-20 returns +2.15% vs market −4.62% → 6.77% relative outperformance
- Decile pattern is random (no clear ordering) — no IC, but positive absolute return

**Interpretation:** In BEAR_HIGH_VOL, most ranked stocks generate positive 20d returns regardless of specific rank. The high-vol environment creates mean-reversion opportunities across the board. This is not a ranking-quality problem — it is a beta/recovery effect.

---

## Strategy Families Evaluated

### 1. Mean Reversion (Oversold Bounce)

**Hypothesis:** After high-volatility sell-offs, the most oversold stocks (largest price drops) revert most aggressively in the subsequent 20 days.

**Factor definitions:**
```
drawdown_20d    = close / rolling_max_close(bars, 20) - 1  (negative = down from peak)
drawdown_60d    = close / rolling_max_close(bars, 60) - 1  (deeper context)
rsi_proxy       = total_return(bars, 14) normalized         (price momentum reversal)
below_ma50      = -(close / simple_moving_average(bars, 50) - 1)  (negative = below MA)
```

**Ranking:** Stocks ranked by LARGEST drawdown (most oversold) ascending

**Data requirements:** 60 days minimum. All 501 stocks eligible.

**Expected holding period:** 10–15 days (reversion is fast)

**Historical evidence:** D10 of breakout (worst-ranked = most momentum-broken stocks) returns +7.47% in BEAR_HIGH_VOL. These are precisely the oversold stocks.

**OOS validation methodology:**
- Need 60+ BEAR_HIGH_VOL days (currently have 31-47)
- Cannot validate with current data alone
- Option: Extend market data back to 2019 and rerun regime detection

**Complexity:** LOW — uses existing rolling_max_close(), total_return()

**Implementability with current data:** PARTIAL — factor computable, OOS validation insufficient

---

### 2. Capitulation Reversal (Volume-Price Pattern)

**Hypothesis:** Capitulation = large price drop accompanied by volume spike. Post-capitulation stocks revert sharply as selling exhausts.

**Factor definitions:**
```
volume_spike    = average_volume(bars, 3) / average_volume(bars, 20)  (recent/long ratio)
price_drop      = -total_return(bars, 5)                              (recent drop magnitude)
capitulation    = volume_spike × price_drop                           (combined signal)
atr_normalized  = 1 / (average_true_range(bars, 10) / close)         (low ATR = settled)
```

**Expected holding period:** 5–10 days (faster reversion after capitulation)

**Historical evidence:** Indirect — volume_surge is already a factor in breakout_v1 but in the POSITIVE direction. Inverting it (high recent volume relative to historical = capitulation) could capture the BEAR_HIGH_VOL reversal pattern.

**Data requirements:** 20 days minimum. Available.

**Complexity:** LOW-MEDIUM — repurposes existing VolumeSurgeFactor in reverse

**Key risk:** Capitulation signal can identify stocks in secular decline (true falling knives) not just oversold bounces. Requires minimum holding quality filter.

**Implementability with current data:** YES — can be computed, but validation sample too small (31-47 days)

---

### 3. Volatility Compression (Anticipation of Mean Reversion)

**Hypothesis:** After high-volatility phases, stocks whose volatility is DECREASING (compressing from a spike) are closest to their reversal point.

**Factor definitions:**
```
vol_ratio       = annualized_volatility(bars, 10) / annualized_volatility(bars, 30)
                  (if < 1.0, vol is compressing — good)
vol_spike_decay = max(annualized_vol, 60) / current_annualized_vol(30)
                  (how much vol has decayed from peak — higher = more compression)
```

**Expected holding period:** 10–20 days

**Historical evidence:** Theoretical — not directly observable in 31-day BEAR_HIGH_VOL sample

**Complexity:** MEDIUM — requires computing vol at multiple windows

**Implementability:** YES for factors, NO for reliable OOS validation

---

## Data Gap Analysis

**Root problem for all BEAR_HIGH_VOL strategies:**

| Requirement | Have | Need | Gap |
|-------------|------|------|-----|
| OOS days | 31-47 | 100+ | 53-69 days |
| Regime streaks | 6 | 10+ | 4+ more occurrences |
| Years of data | 2022-2026 | 2018-2026 | 2-4 years earlier |

**Fastest path to sufficient data:**

Option A: Wait and accumulate in real-time (~3-5 years to get 100+ BEAR_HIGH_VOL days)

Option B: Extend market data pull to 2018-2021 (4 years × ~8 days/year = ~30-40 additional days — still insufficient)

Option C: **Monthly rebalancing with 60-day holding period** — longer horizon increases each streak's contribution from 8 to potentially 8+ days with overlap

**Recommendation: Do not build a dedicated BEAR_HIGH_VOL strategy now.**

The regime is too rare and too short-lived (avg 8 days) to justify a strategy. When BEAR_HIGH_VOL occurs:
- It typically transitions to BEAR_LOW_VOL (as volatility subsides) or BULL_HIGH_VOL (recovery)
- Duration too short for 20-day holding period
- Risk of regime change mid-hold is very high

**Better approach:** In BEAR_HIGH_VOL, default to the BEAR_LOW_VOL defensive strategy with tighter position sizing (reduced slots: 3 instead of 5). The defensive strategy should degrade gracefully into high-vol conditions.

---

## Summary

| Strategy | Expected Alpha | Data Ready | OOS Days | Verdict |
|----------|---------------|------------|----------|---------|
| Mean Reversion | +6-8% per 20d (estimated) | ✅ | ❌ (31) | Too early |
| Capitulation Reversal | +4-6% per 20d (estimated) | ✅ | ❌ (31) | Too early |
| Volatility Compression | +3-5% per 20d (estimated) | ✅ | ❌ (31) | Too early |

**Actionable decision:** Use BEAR_LOW_VOL low-vol strategy in BEAR_HIGH_VOL with 60% position sizing. Accumulate validation data passively.
