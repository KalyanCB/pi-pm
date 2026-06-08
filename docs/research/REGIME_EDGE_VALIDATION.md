# Regime Edge Validation Report

**Produced:** 2026-06-06  
**Methodology:** Walk-forward OOS, as_of_date ≤ today − 30 days, 2022-01-01 onward  
**Data:** 521,855 price rows, 578,514 ranking results, 2,470 ranking runs

---

## Executive Summary

The core RCEE finding — that breakout_v1 and momentum_v1 have no edge in non-BULL_LOW_VOL regimes — is **confirmed but requires important qualification**:

> In BEAR_LOW_VOL, the strategies produce **positive absolute returns** (+0.92% top-20, 20d horizon)  
> but the **ranking order is inverted** — bottom-ranked stocks outperform top-ranked stocks.  
> This is a NO_EDGE condition (negative IC) not a negative-return condition.

This distinction is critical for strategy discovery in Phase 2.

---

## 1. Benchmark Returns by Regime

Market (NIFTY ^NSEI) 20-day forward return by regime:

| Regime | Avg 20d Market Return |
|--------|----------------------|
| BULL_LOW_VOL | +2.01% |
| BULL_HIGH_VOL | n/a (data gap) |
| BEAR_LOW_VOL | **−2.08%** |
| BEAR_HIGH_VOL | **−4.62%** |

**Implication:** In BEAR_LOW_VOL, stocks generating +0.92% are outperforming a −2.08% market by 300bps. The problem is not absolute returns — it is the failure of rank ordering to predict which stocks outperform.

---

## 2. Full Metrics Matrix — breakout_v1

### BULL_LOW_VOL (748 OOS days — primary evidence base)

| Metric | Top 5 | Top 10 | Top 20 | Universe |
|--------|-------|--------|--------|----------|
| Avg 20d return | +3.74% | +3.56% | +3.31% | +1.80% |
| Spread vs universe | +1.94% | +1.76% | +1.51% | — |
| Hit rate | 75.8% | — | 75.8% | — |
| Std dev (top-20) | 5.24% | — | — | — |
| Sharpe (daily Δ) | 0.72 | — | — | — |

**Decile returns (D1 = best ranked → D10 = worst ranked):**

| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|----|----|----|----|----|----|----|----|----|-----|
| +2.96% | +2.11% | +1.87% | +1.72% | +1.43% | +1.31% | +1.23% | +1.39% | +1.18% | +1.54% |

Monotonic decline D1→D6, then flat. **Positive but weakening spread. Strategy works.**

**Profit factor:** 4.97 | **Max drawdown:** −123% equity curve | **Win rate:** 75.8% | **Avg win:** +5.47% | **Avg loss:** −3.45%

---

### BEAR_LOW_VOL (157 OOS days — current regime)

| Metric | Top 5 | Top 10 | Top 20 | Universe |
|--------|-------|--------|--------|----------|
| Avg 20d return | +1.69% | +1.22% | +0.92% | +1.78% |
| Spread vs universe | −0.09% | −0.56% | **−0.86%** | — |
| Hit rate | 63.7% | — | 63.7% | — |
| Std dev (top-20) | 6.25% | — | — | — |

**⚠️ Top-20 UNDERPERFORMS the universe average by 86bps.**

**Decile returns (D1 = best ranked → D10 = worst ranked):**

| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|----|----|----|----|----|----|----|----|----|-----|
| +0.65% | +0.81% | +0.94% | +1.09% | +0.92% | +1.37% | +1.54% | +1.70% | +2.62% | **+3.04%** |

**⚠️ RANKING IS FULLY INVERTED: D10 (+3.04%) beats D1 (+0.65%) by 239bps.**  
The worst-ranked stocks by breakout criteria outperform the best-ranked by 2.4%. This is the most important finding of this analysis.

**Profit factor:** 1.42 | **Max drawdown:** −277% equity curve | **Win rate:** 63.7% | **Avg win:** +4.91% | **Avg loss:** −6.07%

**Quintile analysis (5 buckets):**

| Quintile | Avg Return | Sharpe |
|----------|-----------|--------|
| Q1 (top-ranked) | +0.73% | 0.065 |
| Q2 | +1.02% | 0.099 |
| Q3 | +1.15% | 0.110 |
| Q4 | +1.57% | 0.155 |
| **Q5 (bottom-ranked)** | **+2.85%** | **0.251** |

**Q5 produces 3.9× the Sharpe of Q1 in BEAR_LOW_VOL.**

---

### BEAR_HIGH_VOL (31 OOS days — very limited sample)

| Metric | Top 5 | Top 10 | Top 20 | Universe |
|--------|-------|--------|--------|----------|
| Avg 20d return | +2.28% | +3.73% | +4.61% | +5.79% |
| Spread vs universe | −3.51% | −2.06% | **−1.18%** | — |
| Hit rate | 87.1% | — | — | — |

**Decile returns:** No clear monotonic pattern — random. D10 highest (+7.47%), D1 lowest (+5.09%).

**Profit factor:** 20.09 (inflated by small sample) | **Win rate:** 87.1% | **⚠️ n=31 — insufficient for strategy decisions**

Market is down −4.62% while top-20 generates +4.61%. This is likely a survivorship/momentum-reversal effect: high-vol bear regimes have high beta recovery potential. Cannot draw conclusions from 31 days.

---

### BULL_HIGH_VOL (28 OOS days — very limited sample)

| Metric | Top 5 | Top 10 | Top 20 | Universe |
|--------|-------|--------|--------|----------|
| Avg 20d return | +7.27% | +6.46% | +6.70% | +6.23% |
| Hit rate | 96.4% | — | — | — |

Deciles monotonically increasing D1→D10 (opposite of BULL_LOW_VOL). **⚠️ n=28 — statistically unreliable.**

**Profit factor:** 325 (extreme — only 1 losing day out of 28) | **Win rate:** 96.4%

---

## 3. Full Metrics Matrix — momentum_v1

### BULL_LOW_VOL (763 OOS days)

| Metric | Top 5 | Top 10 | Top 20 | Universe |
|--------|-------|--------|--------|----------|
| Avg 20d return | +3.40% | +3.47% | +3.24% | +1.66% |
| Spread vs universe | +1.74% | +1.81% | **+1.58%** | — |
| Hit rate | 73.9% | — | 73.9% | — |

Decile returns monotonically declining D1 (+2.98%) → D10 (+1.23%). Clean ranking.

**Profit factor:** 4.37 | **Max drawdown:** −133% equity curve | **Win rate:** 73.9%

---

### BEAR_LOW_VOL (175 OOS days)

| Metric | Top 5 | Top 10 | Top 20 | Universe |
|--------|-------|--------|--------|----------|
| Avg 20d return | **−0.20%** | **−0.36%** | +0.12% | +1.19% |
| Spread vs universe | −1.39% | −1.55% | **−1.07%** | — |
| Hit rate | 59.4% | — | — | — |

**⚠️ Top-5 and Top-10 produce NEGATIVE absolute returns. Top-20 barely positive. Universe beats top-20 by 107bps.**

Decile returns: D1 (+0.24%) → D10 (+1.95%). Full inversion again.

**Profit factor:** 1.04 (essentially break-even) | **Max drawdown:** −376% equity curve | **Win rate:** 59.4% | **Avg win:** +4.91% | **Avg loss:** −6.90%

---

## 4. Verdict

### Is BEAR_LOW_VOL genuinely unprofitable?

**No — but the ranking model is actively counterproductive.**

| | Absolute Returns | Ranking Quality |
|---|---|---|
| BULL_LOW_VOL | ✅ Positive (+3.3%) | ✅ Positive IC (+0.047) |
| BEAR_LOW_VOL (breakout) | ✅ Positive (+0.92%) | ❌ Negative IC (−0.082) |
| BEAR_LOW_VOL (momentum) | ⚠️ Near-zero (+0.12%) | ❌ Negative IC (−0.063) |

In BEAR_LOW_VOL the universe of stocks is still generating positive 20d returns (+1.78% avg). What is broken is the **signal direction** — breakout/momentum factors identify the wrong stocks. The bottom quintile (Q5) of the ranking generates +2.85% with Sharpe 0.251 vs market −2.08%.

**This is not a cash-preservation regime. This is an inverse-factor regime.**

A strategy that ranks stocks on LOW volatility, LOW momentum, HIGH price stability would select approximately the same stocks as Q5 of the current breakout ranking — and would generate meaningful positive returns in BEAR_LOW_VOL.

### Key Numbers for Portfolio Planning

| Regime | Days (OOS) | Avg Duration | Top-20 Return | Market Return | Alpha |
|--------|-----------|--------------|---------------|---------------|-------|
| BULL_LOW_VOL | 748/763 | 45 days | +3.3% | +2.0% | +1.3% |
| BEAR_LOW_VOL | 157/175 | 10 days | +0.9% | −2.1% | +3.0% |
| BEAR_HIGH_VOL | 31/47 | 8 days | +4.6% / +2.2% | −4.6% | +9.2% |
| BULL_HIGH_VOL | 28/30 | 8 days | +6.7% / +7.7% | n/a | — |

BEAR_HIGH_VOL and BULL_HIGH_VOL have high absolute alpha but insufficient sample sizes (<50 days each) for statistically reliable strategy decisions.
