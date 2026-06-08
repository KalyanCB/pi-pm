# Portfolio Posture Design: Always-Deploy vs Cash Preservation

**Question:** Should Pi-PM stay in cash when no edge exists, or always maintain at least one strategy per regime?

---

## Quantitative Answer: Always Deploy

### Evidence

**BEAR_LOW_VOL (current regime, 157 OOS days):**

| Posture | 20d Return | Sharpe | Annual Return Equiv. |
|---------|-----------|--------|---------------------|
| Cash | 0.00% | — | 0% |
| Market (NIFTY) | −2.08% | — | negative |
| breakout_v1 top-20 (wrong strategy) | +0.92% | 0.147 | ~11% |
| low_vol Q5 proxy | **+2.85%** | **0.251** | **~37%** |

**Even the WRONG strategy (breakout_v1) beats cash in BEAR_LOW_VOL.** The universe of NIFTY 500 stocks generates positive absolute returns even when the index falls. The problem is not "should we deploy" — it is "which stocks should we own."

### Regime Coverage Math

At current strategy coverage:
- BULL_LOW_VOL (65% of time): full deployment, generating +1.3-1.6% alpha per 20d
- All other regimes (35% of time): zero BUYs, sitting flat

With `low_vol_v1` added:
- BULL_LOW_VOL (65%): unchanged
- BEAR_LOW_VOL (14%): estimated +2.85% per 20d from low-vol strategy
- Other (21%): flat or reduced deployment

**Expected improvement in annual return from regime coverage expansion:**
- Additional alpha from BEAR_LOW_VOL: 7.85 periods × 2.85% = 22.4% cumulative over 157 days
- Annualized contribution: ~14% additional alpha (14% of 250 trading days at +2.85% per 20d)

### The Case Against Cash Preservation

1. **NIFTY 500 is not the index.** Even in bear markets, 30-40% of NSE stocks generate positive returns in any 20-day window. The task is identifying which ones.

2. **Opportunity cost is real.** 157 BEAR_LOW_VOL days in the historical record represent 7.85 non-overlapping deployment windows. Sitting in cash foregoes this.

3. **Cash creates behavioral risk.** If the system says "no BUYs" for 26+ consecutive trading days, the investor either overrides the system (bad) or loses confidence in it (also bad). Having a regime-appropriate recommendation maintains system utility.

4. **The Q5 reversal is not noise.** With 8,899 stock-days of evidence, the 2.12% spread between Q5 (+2.85%) and Q1 (+0.73%) in BEAR_LOW_VOL has statistical substance. The Sharpe differential (0.251 vs 0.065) is 4× — this is a meaningful signal.

### The Case For Cash Preservation (Steel-Manned)

1. **Unvalidated strategy risk.** If `low_vol_v1` has not been validated with RCEE (ic_lower_95 ≥ 0.010 confirmed), deploying capital is speculative. The Q5 proxy is evidence for a hypothesis, not a validated strategy.

2. **Transaction costs.** Deploying 3-5 positions per regime with 10-day average BEAR_LOW_VOL streaks means frequent entry/exit. At 10bps round-trip, frequent trading in short regime windows erodes alpha.

3. **Regime mis-classification risk.** If the regime detector is wrong by 1-2 days (BEAR_LOW_VOL classified when it is actually transitioning), a defensive strategy position can catch a momentum rip in the wrong direction.

### Verdict

**Always deploy, with three conditions:**

1. The deployed strategy must be RCEE-validated (ic_lower_95 ≥ 0.010, n ≥ 60) before receiving real capital
2. Position sizing is reduced in non-BULL_LOW_VOL regimes (3 slots at 70% size vs 5 at 100%)
3. Paper trading precedes real deployment for any new regime strategy

**During the gap period (before `low_vol_v1` is built and validated):**
- Current behavior is correct: WATCH with REGIME_NO_EDGE
- This is not "cash" — it is "honest system" operating within its validated scope
- Do not force BUYs by weakening RCEE thresholds

---

## Recommended Portfolio Policy

```
BULL_LOW_VOL:
  Slots:   5 per strategy (10 total)
  Sizing:  100% conviction-weighted
  Capital: Full deployment target

BEAR_LOW_VOL (after low_vol_v1 validated):
  Slots:   3-4 (low_vol_v1 only)
  Sizing:  70% standard
  Capital: 40-50% deployment

BEAR_HIGH_VOL:
  Slots:   2-3 (low_vol_v1 defensive posture, if RCEE ≥ EDGE_WEAK)
  Sizing:  50% standard
  Capital: 20-30% deployment

BULL_HIGH_VOL:
  Slots:   3 per strategy (breakout + momentum, reduced)
  Sizing:  60% standard
  Capital: 30-40% deployment

No validated strategy available:
  Slots:   0
  Capital: 0% deployment
  Action:  WATCH with honest reason code
```

This policy maximizes risk-adjusted returns while preserving the integrity of the RCEE validation gate.
