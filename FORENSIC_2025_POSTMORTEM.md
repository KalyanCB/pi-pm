# PI-PM Forensic Post-Mortem — Why 2025 Broke
### A root-cause investigation (deterministic, OHLCV-only, evidence-driven)

*All figures from the V22 run + breakout_v2 rankings + market_data. No parameter optimization — this is a diagnosis.*

---

## Executive Summary

The premise that PI-PM "failed to capture 2023 and 2025" is **half wrong, and the correction reframes everything.** Measured against NIFTY:

| Year | Portfolio | NIFTY | Alpha | Cash% | Verdict |
|---|---|---|---|---|---|
| 2021 | +33.9% | +23.8% | **+10pp** | 21% | won |
| 2022 | −2.0% | +2.7% | −5pp | 26% | ~flat (bear) |
| **2023** | **+35.2%** | +19.4% | **+16pp** | 11% | **BEST year — not a failure** |
| 2024 | +25.1% | +8.8% | **+16pp** | 4% | crushed |
| **2025** | **−5.3%** | **+10.1%** | **−15pp** | **29%** | **the only true failure** |
| 2026* | −5.0% | −8.4% | +3pp | 32% | H1 correction |

**2023 was PI-PM's single best year of alpha; so was 2024. The lone genuine failure is 2025** — the portfolio *fell 5% while the market rose 10%.* The investigation is therefore "why did 2025 break," and the answer, demonstrated five independent ways, is the **entry signal's ceiling** — not exits, regime, slots, or any tunable subsystem.

---

## Root-Cause Ranking (final)

```
Signal discovery + durability (the entry factor) ... 85%
Regime/deployment (idle cash; PROTECTIVE, not harmful)  ~10%
Exit eagerness ......................................  ~5%
Slot starvation ..................................... REFUTED (cash was abundant)
```

The two big subsystems people suspect — exits and slots — contributed ~nothing. Every fix that *would* attack the signal was tested and failed.

---

## The evidence chain (each hypothesis, measured)

### 1. Exits — REFUTED as the cause (~5%)
Walk-forward showed the strongest exit intervention (3-day persistence) adds only ~1-3pp, and a from-scratch in-memory test of an ATR/partial/systemic-kill "Exit Engine v2" was **worse** (halved multibaggers via the systemic-kill). Patience helps slightly; exits are not the 2025 problem — you cannot exit your way out of bad entries.

### 2. Slots — REFUTED (~0%)
Slot starvation predicts a *clogged* book blocking buys. 2025 showed the **opposite**: 29% idle cash and 86 entries. Slots were abundant. Refuted directly.

### 3. Regime — measured, and it was PROTECTIVE in 2025
The regime is **daily**, an **OR-of-4 bear trigger** (close<200SMA OR death-cross OR >10% drawdown OR weak breadth) with **no hysteresis**, so it whipsawed to 41% bear in a +10% year. It drove the sleeve switch (`D-1 BEAR → reversion_v3`, else `breakout_v2`). But the data shows it routed capital the **right** way:
```
2025 realized by sleeve:  breakout_v2 −11.3% (7% win)   reversion_v3 +1.2% (51% win)
```
The regime sent money to the *better* sleeve. **Loosening it would have made 2025 worse.** (Earlier "loosen the regime" recommendation: retracted.)

### 4. The signal — the actual failure
breakout_v2 realized return by entry-year collapsed:
```
2021 +21.3%  ·  2022 +38.2%  ·  2023 +36.2% (61% win)  ·  2024 −1.5%  ·  2025 −11.3% (7% win)
```
**The primary alpha source broke.** The case study of every winner (≥75% annual return, 2021-2025) by how breakout_v2 *raw-ranked* them:
```
SIGNAL DISCOVERY (ranked >50 or never) ...... 51%
THRESHOLD (ranked 6-50, below the ≤5 cutoff)  34%
recognized top-5 .......................... 15%
regime-blocked top-5 ...................... 0.3%   ← decision policy is NEGLIGIBLE
```
**85% of all winners were a signal problem.** Why 2021/2023 won but 2025 failed: the factor *always* misses ~50% of winners and only top-5-ranks ~15%; the difference is the *number of winners* (237-289 in the broad good years vs **only 20** in narrow 2025).

### 5. Factor-decay diagnosis — it's STYLE ROTATION, not broken math
Monthly cross-sectional IC of breakout_v2's factors held — even **improved** (composite 0.054→0.079, 2021→2025). No sub-factor collapsed. The *relative* discrimination is intact; the **absolute level** of the near-high/contraction *style* collapsed (rank≤5 fwd 8.3%→2.0%). breakout_v2 is a **mono-style factor** (quiet base near the 52-week high) whose style fell out of favor in 2024-2025.

---

## The fixes that were tested and rejected (the discipline)

| Proposed fix | Result | Verdict |
|---|---|---|
| Momentum-continuation entry sleeve (momentum_v3 / 12-mo) | 2024 +12.8% but **2025 −4.7%**, IC ~0 | helps cross-cycle diversification; **does not fix 2025** (chasing reverts) |
| Shorten high_proximity 252→50d (catch intermediate-base breakouts) | standalone +9.9%/75% in 2025 — promising | **did not survive the composite** |
| Re-rank composite with 50d proximity | 2025 top20 +2.7% ≈ current +2.6% | the 0.55 weight on vol_contraction+consolidation dilutes it |
| Reweight composite toward proximity (0.45→0.90) | 2025 top20 +2.7% → **−0.9%** (worse) | the +9.9% was a fragile tie-break; doesn't generalize |

**Drawdown shape check (anti-chasing):** top-20 breakout entries took a modest −4.6% pullback then recovered — genuine retest, not buying tops. The *philosophy* is sound; the *edge* simply isn't recoverable in 2025 by any reparametrization.

---

## Final conclusion

> **There is no deterministic reparametrization of PI-PM's entry signal that recovers 2025** — not exits, regime, slots, a momentum sleeve, a shorter proximity horizon, or a reweight. The breakout edge was real in 2021-2023, decayed in 2024, and in 2025 every OHLCV-deterministic variant returns ~0% at the top. **2025 is the signal ceiling.**

**PI-PM is a style-cyclical strategy — a structural property, not a bug.** It earns large alpha when the market is broad and breakouts are in favor (2021/2023/2024: +10 to +16pp) and stalls when the market narrows and rotates against breakouts (2025: −15pp). Within the OHLCV-only / no-fundamentals constraint, that cyclicality cannot be engineered away — the winners in years like 2025 are not identifiable from price/volume with edge enough to beat the index.

---

## Recommended decisions (strategic, not technical)

1. **Accept the cyclicality.** Run the engine as the strong style-cyclical strategy it is; size expectations to the cycle (excellent broad markets, flat-to-down narrow ones).
2. **Pursue genuine signal breadth.** Add *truly uncorrelated* deterministic styles over time — eyes open that even a diversified set can have a 2025 (breakout *and* momentum both failed together).
3. **Or relax the constraint.** The only way to pre-identify 2025's winners is information outside OHLCV — explicitly off the table here.

## What NOT to do
- Do not optimize exits, regime, or slots — proven not to be the bottleneck.
- Do not ship the momentum sleeve as a "2025 fix" (diversification only) or the proximity-lookback change (refuted at composite validation).
- Do not re-tune against 2023 — it was the best year; tuning against it risks degrading what works.

---

### Method note
Every claim above is from a measurement run this session (capture ratios, sleeve realized returns, the winner case-study, factor IC by year, the momentum/proximity/composite validation gates). The validation gates did their job — they rejected three appealing fixes *before* any was built, which is the core value of the investigation.
