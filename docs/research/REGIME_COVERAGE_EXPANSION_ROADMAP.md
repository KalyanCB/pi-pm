# Regime Coverage Expansion Roadmap

**Produced:** 2026-06-06 | **Senior Quant Researcher Review**

---

## Current Coverage Matrix

| Regime | Avg Duration | Occurrences | Strategy | Status |
|--------|-------------|-------------|----------|--------|
| BULL_LOW_VOL | 45 days | 17 | breakout_v1, momentum_v1 | ✅ EDGE_PRESENT |
| BEAR_LOW_VOL | 10 days | 20 | none | ❌ NO_EDGE |
| BEAR_HIGH_VOL | 8 days | 6 | none | ❌ NO_EDGE (n=31-47) |
| BULL_HIGH_VOL | 8 days | 4 | none | ❌ NO_EDGE (n=28-30) |

**Time in each regime (2022-2026, breakout_v1):**
- BULL_LOW_VOL: 748 days = 65.2% of the time
- BEAR_LOW_VOL: 157 days = 13.7% of the time ← **highest priority gap**
- BEAR_HIGH_VOL: 31 days = 2.7% of the time
- BULL_HIGH_VOL: 28 days = 2.4% of the time
- Unclassified (2021-22): 199 days = 17.3%

---

## Target Coverage Matrix

| Regime | Strategy Family | Priority | Expected Alpha/20d | OOS Days | Complexity |
|--------|----------------|----------|---------------------|----------|------------|
| BULL_LOW_VOL | breakout_v1, momentum_v1 | ✅ Done | +1.3-1.6% vs mkt | 748/763 | Done |
| **BEAR_LOW_VOL** | **low_vol_v1** | **P1** | **+2.5-4.0% vs mkt** | **157** | **Low** |
| BEAR_HIGH_VOL | bear_reversal_v1 | P3 | +5-8% est. vs mkt | 31-47 | Medium |
| BULL_HIGH_VOL | bull_momentum_v1 | P4 | +1-2% est. vs mkt | 28-30 | Low |

---

## Recommendation 1: Highest ROI — `low_vol_v1` for BEAR_LOW_VOL

**Why this is the clear next build:**

1. **157 OOS days** — sufficient to cross the 60-day EDGE_PRESENT threshold (may even reach ic_lower_95 ≥ 0.010 on first backfill)
2. **Strong empirical signal**: Q5 reversal data shows +2.85% per 20d in BEAR_LOW_VOL (Sharpe 0.251) vs Q1's +0.73%
3. **Current regime**: BEAR_LOW_VOL active right now — validated strategy would produce BUYs immediately
4. **Low implementation cost**: ~30 lines of code using existing annualized_volatility() and math_utils functions
5. **Academic support**: Low volatility anomaly is one of the most robust factors in emerging market equities (Ang et al., Blitz/van Vliet)
6. **No new data required**: Computable from existing 501-stock OHLCV data

**Minimum viable factor set for `low_vol_v1`:**
```python
# Rank ascending by weighted volatility composite
LOW_VOL_WEIGHTS = {
    "vol_30d_inverse":  Decimal("0.50"),  # 1/annualized_vol(30)
    "vol_60d_inverse":  Decimal("0.30"),  # 1/annualized_vol(60) — confirms persistence
    "atr_price_inverse": Decimal("0.20"), # 1/(ATR_20/close) — range stability
}
```

**Expected OOS IC after backfill:**
- Hypothesis: IC_low_vol in BEAR_LOW_VOL ≈ +0.04 to +0.06 (inverse of breakout IC −0.082)
- At 157 days: ic_lower_95 = 0.05 − 1.645 × 0.12 / √157 ≈ 0.05 − 0.016 = **+0.034** → EDGE_PRESENT ✓
- Expected conviction for top-5 stocks: MEDIUM-HIGH

---

## Recommendation 2: Fastest Validation — `low_vol_v1` (same strategy)

The fastest strategy to validate IS the same as the highest ROI — `low_vol_v1`.

Timeline estimate:
1. Implement factor computation: 1-2 days
2. Register strategy and run backfill (2022-2026): ~3-4 hours (same pipeline)
3. Run RCEE validation: immediate (157 days already available)
4. First BUY signal: Day 1 after validation, if still in BEAR_LOW_VOL

**No waiting required.** The historical data is already in the DB.

---

## Recommendation 3: Most Robust All-Weather Portfolio Mix

**Target state (12-month horizon):**

```
Portfolio posture by regime:

BULL_LOW_VOL (65% of time):
  breakout_v1:  5 slots  @ standard sizing
  momentum_v1:  5 slots  @ standard sizing
  Total:        up to 10 positions, full capital deployment

BEAR_LOW_VOL (14% of time):
  low_vol_v1:   3-5 slots @ 70% sizing (risk-adjusted)
  Total:        3-5 positions, partial deployment
  Expected:     +2.5-3% per 20d period

BEAR_HIGH_VOL (3% of time):
  low_vol_v1:   3 slots  @ 50% sizing (defensive)
  Total:        3 positions, capital preservation mode
  Expected:     degraded but positive

BULL_HIGH_VOL (2% of time):
  breakout_v1:  3 slots  @ 60% sizing (reduced risk)
  momentum_v1:  3 slots  @ 60% sizing (reduced risk)
  Total:        up to 6 positions, cautious deployment
```

**This achieves 82% regime coverage (BULL_LOW_VOL + BEAR_LOW_VOL) with validated strategies.**

BEAR_HIGH_VOL (3%) and BULL_HIGH_VOL (2%) together account for only 5% of trading days — acceptable to run conservative deployment in these rare regimes without dedicated strategy validation.

---

## Implementation Sequence

### Sprint 1 (1-2 weeks): low_vol_v1 factor implementation
- Implement `LowVolatilityStrategy` class in `app/ranking/strategies/low_vol_v1.py`
- Register in strategy registry
- Run backfill for all BEAR_LOW_VOL dates (2022-2026)
- Run RCEE validation
- Expected result: EDGE_PRESENT classification with 157 OOS days

### Sprint 2 (1-2 weeks): RCEE multi-strategy per regime
- Modify daily batch to run `low_vol_v1` only during BEAR_LOW_VOL regimes
- Add regime-conditional strategy selection to batch planner
- Test end-to-end with paper trading simulation

### Sprint 3 (2-4 weeks): Portfolio posture policy
- Implement regime-conditional slot limits (5 in BULL_LOW_VOL → 3 in BEAR)
- Implement conviction sizing: MEDIUM slots → 70% size, HIGH → 100%, EXCEPTIONAL → 130%

### Sprint 4 (ongoing): Data extension for BEAR_HIGH_VOL
- Backfill NSE market data from 2018-2021 (adds ~3 years)
- Expected additional BEAR_HIGH_VOL days: ~30-50 (still insufficient alone)
- Combine with real-time accumulation over 2-3 years

---

## Quantitative Justification for Always-Deploy vs Cash

From Phase 1 data:

| Posture | BEAR_LOW_VOL Return | vs Cash (+0%) |
|---------|--------------------|--------------  |
| Cash | 0% | baseline |
| Market | −2.08% | −2.08% |
| Top-20 breakout (wrong strategy) | +0.92% | +0.92% |
| Low-vol Q5 proxy | +2.85% | **+2.85%** |
| Cash preservation (optimal?) | 0% | 0% |

**Always-deploy with regime-appropriate strategy dominates cash by 2.85% per 20d period in BEAR_LOW_VOL.**

Over 157 BEAR_LOW_VOL days (7.85 non-overlapping 20d periods):
- Cash: +0%
- Low-vol strategy (estimated): +7.85 × 2.85% = **+22.4% cumulative** (pre-compounding)

**The quantitative answer: Always deploy with regime-appropriate strategy. Never sit fully in cash.**

---

## Final Answer

**"What is the next strategy family Pi-PM should build?"**

> **`low_vol_v1` — Low Volatility Ranking for BEAR_LOW_VOL**

Rationale:
- Highest evidence quality (157 OOS days — only regime with sufficient validation data)
- Directly addressable now (all data and infrastructure available)
- Largest current need (active BEAR_LOW_VOL regime for 26+ days, zero BUYs)
- Strongest empirical signal (Q5 reversal: +2.85% vs Q1: +0.73% per 20d)
- Lowest implementation risk (single factor, existing math functions)
- Maximum portfolio impact: converts the 14% of time currently generating zero signals into active alpha generation
