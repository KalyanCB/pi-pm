# What a Stock Looks Like *Before* It Breaks Out
### An empirical study of pre-breakout market behavior — successful vs failed attempts

*Deterministic OHLCV only. No indicators, no moving averages, no RSI/MACD. Every conclusion is measured, not asserted.*

---

## Abstract

We study **2,126 deterministic breakout attempts** (new 126-day high emerging from a consolidation base, liquidity-filtered) across 934 NSE stocks, 2019–2026. Each attempt is labelled by its **forward 120-day outcome**: **SUCCESS** (≥ +40%, n=614) or **FAILURE** (≤ +5%, n=1,512). Base success rate **28.9%**. For every attempt we measure nine OHLCV *behaviors* at seven look-back vantages — **180, 120, 90, 60, 30, 15, 5 trading days before the breakout** — and contrast success vs failure.

**Central finding:** the information that separates future winners from future fizzles is **front-loaded** — it is strongest **120–180 days before the breakout** and **decays to near-zero by the breakout day itself.** The single strongest deterministic tell is that **successful breakouts emerge from *deeper* bases** (farther below the 52-week high ~180 days out) **and *climb* into the breakout**, whereas failures start already near their highs and go nowhere. This is precisely the information **Breakout_v2 cannot see, because it measures at the breakout — the one moment when success and failure look identical.**

A Breakout **Readiness** Score built only from the early-discriminating features lifts P(success) from a 28.7% base to **34.0% out-of-sample (1.18×)** — a real but modest edge that, honestly, *degrades* out-of-sample (1.43× in-sample). The pre-breakout signal exists; it is weak; and it lives entirely in the accumulation phase, not the breakout.

---

## 1. The lifecycle of a breakout — designed from evidence

The stages below are *derived from the measured success-vs-failure separation* (Cohen's *d*, success − fail) at each vantage, not assumed:

```
                        STRONGEST SEPARATION ........................ SEPARATION ~ GONE
                        180d        120d       90d        60d    30d   15d    5d    DAY 0
Stage:                  └─ S1 ─┘  └── S2 ──┘ └──── S3 ────┘  └─── S4 ───┘      S5
                        Silent     Leadership  Pressure       Breakout        EXPANSION
                        Accumulation Emergence  Building       Readiness    (Breakout_v2 fires HERE)
```

### Stage 1 — Silent Accumulation (≈180→120 days before)
The base is *deep and alive.* Successful names sit **farthest from their 52-week high** here (proximity **0.787** vs failures **~0.85**; *d* = **−0.32**, the largest separation in the entire study), with **elevated volatility/range** (not a dead chart) and **expanding rupee-volume** (+55% vs the prior window; *d* = +0.18). This is quiet institutional footprint, not price strength.

### Stage 2 — Leadership Emergence (≈120→90 days before)
**Relative strength turns positive** versus the universe (cumulative excess return *d* = **+0.20** at 120d) and **up-volume share peaks** (accumulation, *d* = **+0.25** at 120d). The base begins to **rise** (proximity 0.81→0.82). The stock starts *leading* before it *breaks*.

### Stage 3 — Pressure Building / Compression (≈90→30 days before)
Volatility and intraday range **compress** (success volatility 0.024→0.023; range tightening). Pullbacks **shrink** (max-drawdown 0.111→0.107). Tellingly, **closes sit *low* in the daily range** (*d* = **−0.33** at 90d) — i.e., pre-winners are *absorbing supply*, not closing on their highs. Failures look superficially stronger here (closing high) and fizzle. Proximity climbs 0.82→0.84.

### Stage 4 — Breakout Readiness (≈30→5 days before)
Proximity approaches the prior high (0.84→0.88), drawdowns reach their **shallowest** (0.087), compression is tightest. **But the predictive separation has largely *collapsed*** — by 5 days out, almost every feature's *d* has decayed below 0.1. The window of edge is closing.

### Stage 5 — Expansion (day 0)
A new 126-day high prints. **Breakout_v2 fires here. Success-vs-failure separation ≈ 0.** This is *confirmation*, not *prediction*.

---

## 2. Per-stage characteristics, math, and confidence

| Stage | Observable | Deterministic measurement | Separation (peak *d*) | Confidence |
|---|---|---|---|---|
| **S1 Accumulation** | deep base, away from high | `prox = close / max(high, 252d)` | **−0.32 @180d** | **High** (strongest, earliest) |
| S1 | liquidity expanding | `Δ mean(close·vol)/prior-60d − 1` | +0.18 @180d | Moderate |
| S1 | stock alive (not dead) | `mean((high−low)/close)` | +0.27 @180d | Moderate |
| **S2 Leadership** | relative strength rising | `Σ(ret − median_universe_ret)` | **+0.20 @120d** | **Moderate** |
| **S2** | accumulation footprint | `Σ vol[up-days] / Σ vol` | **+0.25 @120d** | **Moderate** |
| S3 Pressure | volatility compression | `std(daily ret)` falling | +0.26→+0.09 (fades) | Moderate |
| S3 | supply absorption | `mean((close−low)/(high−low))` **low** | **−0.33 @90d** | Moderate |
| S3 | pullbacks shrinking | `max drawdown` falling | +0.16 @30d | Low |
| S4 Readiness | proximity climbing to high | `prox` trajectory ↑ | converging → <0.1 | **Low** (edge gone) |
| — rejected — | trend smoothness | efficiency ratio `\|net\|/Σ\|step\|` | **no separation** | **None** (hypothesis killed) |

**Honest negatives (hypotheses the data *rejected*):** *trend efficiency / smoothness* does **not** separate winners from fizzles (*d* ≈ 0 at every horizon). *Liquidity growth* and *pullback-shrink* are **weak** (OOS corr +0.06, −0.07). Not every plausible "accumulation" story survives measurement.

---

## 3. The Breakout **Readiness** Score (not a Breakout Score)

Built **only from early/mid-horizon features** (vantage ≈90–120 days out) so it provides *lead time*. Direction fixed on train (pre-2023), tested on 2023+:

| Feature | Definition | Train corr w/ success |
|---|---|---|
| **base depth** | `−prox_180` (started far from high) | **+0.238** ← strongest |
| accumulation | `up-volume share @120d` | +0.154 |
| relative strength | `cum excess return @120d` | +0.154 |
| base climb | `prox_90 − prox_180` | +0.126 |
| liquidity expansion | `liq growth @120d` | +0.060 |
| pullback shrink | `dd_120 − dd_30` | −0.068 (weak) |

`Readiness = Σ z-score(feature)`, z-normalized on train only.

**Walk-forward result:**

| | LOW tercile | MID | HIGH tercile | Lift (HIGH/base) |
|---|---|---|---|---|
| **TRAIN (<2023)** base 29.1% | 20.1% | 25.7% | **41.6%** | **1.43×** |
| **TEST (2023+)** base 28.7% | 26.5% | 25.6% | **34.0%** | **1.18×** |

**Reading it honestly:** the score *generalizes* (HIGH > base out-of-sample) but the edge **shrinks from 1.43× to 1.18×** out-of-sample. A high-readiness stock is ~**18% more likely** than average to be a successful breakout. That is a *probabilistic tilt*, not a crystal ball — and the OOS decay is the **same signal-ceiling fingerprint** seen everywhere else in PI-PM's 2025 work. The right use is as **one orthogonal sleeve in a portfolio of styles**, not as a standalone oracle.

---

## 4. Which characteristics appear *earliest* (the lead-time ranking)

The most valuable signals are the ones with the **longest lead** — they buy the most time before the crowd:

```
EARLIEST (180d)  Base depth (proximity low)        d=−0.32   ← #1 tell, longest lead
                 Intraday range elevated           d=+0.27
                 Volatility elevated               d=+0.26
                 Liquidity expansion               d=+0.18
MID (120d)       Accumulation (up-volume share)    d=+0.25
                 Relative strength rising          d=+0.20
LATE (90d)       Supply absorption (low close-loc) d=−0.33   (strong but later)
LATEST (30d)     Pullback shrink                   d=+0.16   (weak, little lead)
NEVER            Trend smoothness                  d≈0       (no signal at all)
```

**The earliest, strongest, most actionable signal is *base depth* — how far below its 52-week high the stock sits 180 days out — combined with the *climb* off that base.** Everything Breakout_v2 rewards (being *at* the high) is the *opposite* end of this trajectory.

---

## 5. Breakout_v2 vs Breakout Readiness — why v2 arrives late

**Breakout_v2's `high_proximity` factor rewards `close/252d-high ≈ 0.98` — a stock *at* its high.** The evidence shows that is **Stage 5**, the expansion moment, where **success and failure are statistically indistinguishable** (every feature's separation has decayed to ~0). Breakout_v2 is therefore structurally a **confirmation engine**: it can only act *after* the very information that predicts success has already dissipated.

The named multibaggers confirm the trajectory. Their proximity 180 days before breakout: **FORCEMOT 0.79, OLECTRA 0.62, PGEL 0.80, BEL 0.85** — all *well below* the high, then climbing. By the time each reached `prox ≈ 1.0` (Breakout_v2's trigger) the move was underway. *(Caveat: per-stock trajectories are noisy and idiosyncratic — OLECTRA's liquidity spiked only 5 days out, RVNL's 60 days out. There is **no chart template**; the edge is cross-sectional and statistical, which is exactly why a deterministic *score* over the population beats eyeballing any single chart.)*

| | Breakout_v2 (the old philosophy) | Breakout **Readiness** (the new one) |
|---|---|---|
| **Question asked** | "Has this stock broken out?" | "How close is this to a *high-probability* breakout?" |
| **Vantage** | Day 0 (the high) | 90–180 days before |
| **Information used** | level *at* the high | *trajectory* into the high + accumulation |
| **Separation available** | ≈ 0 (success≈fail) | *d* up to 0.32 |
| **Failure mode** | buys late, at tops that revert (2025) | false positives in dead bases that never ignite |
| **Lead time** | none | up to 6 months |

**Why the new philosophy gets there first:** it keys on the *deep base + rising relative strength + accumulation* of **Stages 1–2**, weeks-to-months before price confirms — the same names (FORCEMOT-class) that Breakout_v2 ranks `>50 or never` until they are already at the high.

---

## 6. Limitations (stated plainly)

1. **The edge is modest and decays OOS** (1.43×→1.18×). This is consistent with — not a refutation of — the 2025 signal-ceiling finding. Pre-breakout OHLCV information is *real but weak.*
2. **Effect sizes are small** (peak *d* ≈ 0.2–0.33). No single feature is a strong classifier; only the *early combination* carries usable signal.
3. **Survivorship:** the panel is current-universe; delisted names are under-represented, which can flatter success rates. A point-in-time universe is required before any capital.
4. **Event definition is one of many.** "New 126-day high from a base" is a deterministic but specific breakout definition; alternative definitions should be stress-tested.
5. **Named-stock trajectories are noisy.** The signal is statistical across 2,126 events, *not* a repeatable single-chart pattern — important to prevent over-fitting a "shape."

---

## 7. Conclusion

A successful breakout does **not** begin at the breakout. It begins **~6 months earlier**, in a **deep, alive base** that **accumulates** (rising up-volume share), **leads** (relative strength turns positive vs the universe), then **compresses and absorbs supply** while **climbing toward** the prior high. By the time price *confirms* — the moment Breakout_v2 measures — the predictive separation between future winners and future fizzles has **collapsed to zero**.

The redefinition is therefore not a new indicator but a new *vantage point*: **measure the transition `Base → Accumulation → Expansion` while it is still in the accumulation phase.** The deterministic Readiness Score that operationalizes this earns a genuine, if modest, out-of-sample edge (1.18×) — best deployed as the **early-lead, anticipatory sleeve** of the orthogonal research portfolio, the natural empirical home of the *Rank-Acceleration* and *Participation/Accumulation* architectures proposed in the Discovery Research Program.

---

### Method note
2,126 attempts / 934 stocks / 2019–2026 from `market_data`. Breakout = close > prior 126d high, emerging from a base (range ≤ 1.8×, not at highs in prior 20d), ₹-vol ≥ ₹1cr. Label by forward-120d return (≥+40% success / ≤+5% fail). Features measured in a 30-day window ending at each of 7 vantages before the event; relative strength is excess over the cross-sectional universe-median daily return. Readiness score: equal-weight z-sum of early features, normalized on pre-2023 train, evaluated on 2023+ test. Harness: `scratchpad/prebreakout.py`, `scratchpad/readiness.py`.
