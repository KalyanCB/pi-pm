# BULL_HIGH_VOL Strategy Discovery

**Regime:** Market above 200-day MA, elevated volatility  
**Historical avg duration:** 8 days | Max observed: 20 days | Occurrences: 4  
**OOS sample:** breakout_v1 = 28 days, momentum_v1 = 30 days  
**Top-20 return:** breakout_v1 +6.70%, momentum_v1 +7.74%

---

## Critical Caveat

**28–30 OOS days is the smallest sample in the entire dataset.**

BULL_HIGH_VOL has occurred only 4 times in the historical data with an average duration of 8 days. The profit factors (325 for breakout, 152 for momentum) are statistical artifacts of small sample + rising market — not indicators of genuine strategy edge.

This regime is the rarest: high-volatility bull phases are typically brief transitions between regime states. Most BULL_HIGH_VOL periods in India correspond to:
1. Pre-election relief rallies
2. FII buying surges after oversold conditions
3. Short-covering rallies in trending markets
4. Post-crisis recovery phases (COVID bounce in 2020, if data extended)

---

## What the Data Shows

**Return profile:**
- Market (implied from stock data): ~+6.2% average 20d
- Top-20 breakout: +6.70% (+0.47% alpha — very weak)
- Top-20 momentum: +7.74% (+1.54% alpha — marginal)

**Decile pattern:**
- breakout_v1: D1 (+5.99%) → D10 (+9.56%) — INVERTED (bottom decile outperforms)
- momentum_v1: D1 (+7.11%) → D10 (+8.74%) — weak positive ordering at high ends

**Insight:** In BULL_HIGH_VOL, **high-beta stocks rise fastest** regardless of their momentum/breakout quality. The strongest relative performers are stocks that had fallen most (low-proximity to highs = oversold beta stocks). This resembles a mean-reversion/beta-recovery dynamic.

---

## Strategy Families Evaluated

### 1. Momentum Acceleration

**Hypothesis:** During high-vol bull phases, stocks with the strongest near-term momentum acceleration (20d momentum accelerating vs 60d) capture outsized gains.

**Factor definitions:**
```
momentum_accel = total_return(bars, 20) / total_return(bars, 60)
                 (recent vs medium-term momentum ratio)
rs_accel       = RelativeStrengthAccelerationFactor (already exists in breakout_v1)
```

**Historical evidence:** breakout_v1 already uses RS acceleration (5% weight). The decile inversion suggests acceleration is not the winning factor — recovery (reversal) is.

**Assessment:** WEAK EVIDENCE. Not the right factor for this regime.

---

### 2. High Beta Rotation

**Hypothesis:** In volatile bull markets, high-beta stocks outperform due to leverage effect.

**Factor definitions:**
```
beta_60d = CORR(stock_returns, nifty_returns, 60) × 
           (stddev(stock_returns, 60) / stddev(nifty_returns, 60))
```

**Data requirements:** 60 days + benchmark. Rolling correlation requires new math function.

**Historical evidence:** D10 of breakout (+9.56%) = lowest-breakout stocks in bull market. These are high-beta recovering stocks, not pure momentum. This supports beta rotation theory.

**Implementation complexity:** MEDIUM — requires rolling_correlation() function addition

**OOS validation:** Cannot validate with 28-30 days. Need 60+ BULL_HIGH_VOL days.

---

### 3. Relative Strength Breakout

**Hypothesis:** Same as breakout_v1 but with higher sensitivity parameters — shorter lookbacks to capture fast moves.

**Factor modifications:**
```
MOMENTUM_LOOKBACK: 63 → 21  (shorter for fast-moving regimes)
VolumeSurge threshold: lower  (more permissive in high-vol)
ATR expansion: higher threshold  (require larger moves)
```

**Assessment:** Essentially a parameter-tuned variant of breakout_v1. Given D10 outperforms D1 in this regime, even parameter tuning will struggle. The fundamental issue is that breakout signals become noisy when volatility is high — all stocks show "breakout-like" behavior.

---

### 4. Sector Rotation

**Hypothesis:** Specific sectors lead bull-high-vol rallies (e.g., Financials/Banks in India on rate cut expectations, Auto on volume recovery).

**Data requirements:** Sector tags (not available in Pi-PM DB) or sector ETF price proxies.

**Assessment:** Without sector data, this cannot be implemented reliably. Beta-based clustering could partially proxy sectors.

---

## Data Gap Analysis

| Requirement | Have | Need | Gap |
|-------------|------|------|-----|
| OOS days | 28-30 | 60+ | 30+ days |
| Regime occurrences | 4 | 10+ | 6+ more |

**Fastest path:** Extend data to 2019-2020 (COVID recovery = likely BULL_HIGH_VOL). One COVID recovery phase could add 15-30 BULL_HIGH_VOL days.

**Expected timeline to sufficient data:** 3-5 years real-time accumulation OR data extension.

---

## Summary and Recommendation

**Do not build a dedicated BULL_HIGH_VOL strategy now.**

Reasons:
1. 28-30 OOS days — statistically indefensible
2. Average duration 8 days — shorter than 20-day holding period (regime changes before exit)
3. BULL_HIGH_VOL typically transitions to BULL_LOW_VOL (the regime where breakout_v1 already works well)
4. The "alpha" observed (+0.47-1.54%) is within noise bands at this sample size

**Recommended posture in BULL_HIGH_VOL:**
- Continue running breakout_v1 and momentum_v1 (they still generate +6.7-7.7% absolute returns)
- Reduce position sizing to 3 slots (down from 5) — higher vol = tighter risk
- Accept that ranking quality is degraded but absolute returns are still positive
- Hold existing positions through the regime transition (likely back to BULL_LOW_VOL)

**When BULL_LOW_VOL resumes, the full strategy activates automatically.**
