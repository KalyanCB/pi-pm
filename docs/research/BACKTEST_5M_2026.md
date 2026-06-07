# Pi-PM 5-Month Backtest — Jan 1 to Jun 5, 2026

**NIFTY benchmark return: -10.6%**  
**Trading days: 103**  
**Simulation parameters: 5 slots/strategy, 20-day hold, 10bps cost**

---

## 1. Strategy Summary

| Strategy | Trades | Win Rate | Avg Return | Best | Worst | Profit Factor | Total P&L |
|----------|--------|----------|-----------|------|-------|---------------|-----------|
| breakout_v1 | 10 | 60.0% | -2.05% | +16.72% | -21.38% | 0.61 | ₹-41,195 |
| momentum_v1 | 10 | 60.0% | +1.05% | +16.72% | -12.61% | 1.42 | ₹21,033 |
| reversal_v1 | 25 | 40.0% | +1.99% | +30.83% | -12.69% | 1.95 | ₹99,480 |

---

## 2. Regime Performance Breakdown

### breakout_v1

| Regime | Trades | Win Rate | Avg Return | Total P&L |
|--------|--------|----------|-----------|-----------|
| BULL_LOW_VOL | 10 | 60% | -2.05% | ₹-410,400 |

### momentum_v1

| Regime | Trades | Win Rate | Avg Return | Total P&L |
|--------|--------|----------|-----------|-----------|
| BULL_LOW_VOL | 10 | 60% | +1.05% | ₹210,200 |

### reversal_v1

| Regime | Trades | Win Rate | Avg Return | Total P&L |
|--------|--------|----------|-----------|-----------|
| BEAR_LOW_VOL | 25 | 40% | +1.99% | ₹2,487,500 |

---

## 3. Top 10 Performing Symbols

| Symbol | Trades | Total Return | Avg Return/Trade |
|--------|--------|-------------|-----------------|
| HINDCOPPER.NS | 2 | +33.44% | +16.72% |
| TARIL.NS | 1 | +30.83% | +30.83% |
| WHIRLPOOL.NS | 1 | +15.98% | +15.98% |
| TIINDIA.NS | 1 | +14.33% | +14.33% |
| KAYNES.NS | 1 | +12.34% | +12.34% |
| HEXT.NS | 1 | +11.84% | +11.84% |
| VTL.NS | 2 | +10.06% | +5.03% |
| VEDL.NS | 1 | +9.52% | +9.52% |
| PERSISTENT.NS | 1 | +7.98% | +7.98% |
| TORNTPHARM.NS | 1 | +7.20% | +7.20% |

## 4. Bottom 5 Underperformers

| Symbol | Trades | Total Return | Avg Return/Trade |
|--------|--------|-------------|-----------------|
| M&MFIN.NS | 2 | -25.22% | -12.61% |
| TECHM.NS | 1 | -21.38% | -21.38% |
| UPL.NS | 1 | -13.36% | -13.36% |
| INOXWIND.NS | 1 | -12.69% | -12.69% |
| SHRIRAMFIN.NS | 2 | -11.50% | -5.75% |

---

## 5. Improvement Points (Observations Only — Core Logic Unchanged)

### 5.1 Regime Gap: BEAR_HIGH_VOL (Mar 23 – Apr 28, 23 days)

No strategy had EDGE_PRESENT in BEAR_HIGH_VOL. System correctly silent but capital sat idle.
- reversal_v1 had hit_rate=38.7% in BEAR_HIGH_VOL — below the 55% threshold
- The 23-day gap represents ~4.6% of the simulation period with zero deployment
- **Observation:** A BEAR_HIGH_VOL strategy (mean-reversion / oversold bounce) would fill this gap
  but requires ~80+ OOS days for validation. Currently only 31-47 days available.

### 5.2 Exit Timing: Fixed 20-Day Hold vs Regime-Aware Exit

The simulation uses a fixed 20-day hold. In practice:
- Several reversal_v1 positions were entered just before regime flipped (e.g., Jan 23 reversal
  entries ran into BULL_LOW_VOL territory where the reversal signal weakens)
- **Observation:** An exit trigger that fires when regime transitions could improve returns.
  Already in R-EXIT-03 (regime_turned_defensive) and R-EXIT-05 (edge_degraded) —
  but the portfolio engine (M2) is needed to wire per-position holding days.

### 5.3 Slot Utilisation: breakout + momentum Both Running in BULL

breakout_v1 and momentum_v1 both generated 5 BUYs/day in BULL_LOW_VOL — 10 positions total.
Many overlapping symbols appear across both strategies, reducing diversification.
- **Observation:** In BULL_LOW_VOL, consider running only the higher-IC strategy
  (momentum_v1 ic=+0.053 vs breakout_v1 ic=+0.047) or deduplicating cross-strategy positions.

### 5.4 Conviction Band Distribution

| Strategy | MEDIUM | HIGH | EXCEPTIONAL |
|----------|--------|------|-------------|
| breakout_v1 | 2 | 8 | 0 |
| momentum_v1 | 2 | 8 | 0 |
| reversal_v1 | 20 | 5 | 0 |

Majority of reversal_v1 BUYs are MEDIUM conviction. Higher-conviction entries could be
prioritised by reducing max_buy_slots to 3 in non-primary regimes.

### 5.5 Hold Period Analysis

**breakout_v1:** avg hold 20.0 days. 0 trades exited before 15 days (end-of-period cutoff).
**momentum_v1:** avg hold 20.0 days. 0 trades exited before 15 days (end-of-period cutoff).
**reversal_v1:** avg hold 13.2 days. 10 trades exited before 15 days (end-of-period cutoff).

### 5.6 Missing Catalyst Moves (Not Fixable with Price Factors)

| Symbol | Peak Return | System Action | Why Missed |
|--------|------------|---------------|-----------|
| WOCKPHARMA.NS | +51% | WATCH (breakout) / REJECT (reversal) | Earnings catalyst May 6 — not predictable from OHLCV |
| HFCL.NS | In top pool | WATCH (REGIME_NO_EDGE) | Correct — BEAR_LOW_VOL has no edge for breakout |

Single-day catalyst moves (+15-20% in one session) are outside the scope of a
20-day rolling signal system. These require fundamental event detection (earnings surprise,
corporate action) — not a price/volume strategy improvement.

---

## 6. Summary Recommendation Priority

| Priority | Improvement | Type | Expected Impact |
|----------|------------|------|-----------------|
| P1 | Wire portfolio engine — per-position holding days, regime-exit triggers | Code | Sharper exits |
| P2 | Build BEAR_HIGH_VOL strategy (needs 80+ OOS days — accumulate passively) | Research | Fill 23-day gap |
| P3 | Deduplicate breakout/momentum top-pool overlap in BULL | Config | Better diversification |
| P4 | Reduce reversal_v1 slots to 3 in BEAR (most signals are MEDIUM conviction) | Config | Better risk sizing |
| P5 | Regime-aware exit on position open when regime transitions | Code | Protect gains |

---

*Generated: 2026-06-06 | Period: 2026-01-01 – 2026-06-05 | Strategies: breakout_v1, momentum_v1, reversal_v1*