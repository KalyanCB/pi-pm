# RCEE — Regime Conditional Edge Engine: Detailed Implemented Logic

**ADR-032 | Implemented: 2026-06-06**  
**Source files:**
- `app/recommendation/regime_edge_engine.py`
- `app/recommendation/engine.py`
- `app/recommendation/conviction_scorer.py`
- `app/db/repositories/regime_analytics_repository.py`

---

## 1. Why RCEE Exists

The original recommendation engine used a single gate to block BUYs:

```python
# Old R-ENTRY-02 (pre-ADR-032)
if validation.status == "insufficient_data":
    return WATCH  # reason: VALIDATION_PENDING
```

This was wrong for two reasons:
1. **Validation requires future returns** — it can never complete for today's signals
2. **The real question is not "has this run been validated?" but "does this strategy have edge in today's market?"**

OOS walk-forward analysis (2022–2026) proved that both strategies have **negative predictive power** in BEAR regimes regardless of validation status. RCEE replaces the validation gate with evidence-based regime-conditional edge estimation.

---

## 2. How Regime is Defined

Regime is computed daily from the NIFTY benchmark (`^NSEI`) using two independent dimensions:

### Trend Dimension
```
NIFTY close  >  200-day moving average  →  BULL
NIFTY close  ≤  200-day moving average  →  BEAR
```

### Volatility Dimension
```
30-day rolling volatility  <  threshold  →  LOW_VOL
30-day rolling volatility  ≥  threshold  →  HIGH_VOL
```

### Combined: 4 Regime Labels
| Label | Meaning |
|-------|---------|
| `BULL_LOW_VOL` | Trending up, calm market |
| `BULL_HIGH_VOL` | Trending up, volatile market |
| `BEAR_LOW_VOL` | Trending down, calm market |
| `BEAR_HIGH_VOL` | Trending down, volatile market |

Regime label is stored on every `ranking_run` row at computation time.

---

## 3. OOS Evidence — `strategy_regime_performance` Table

RCEE operates on pre-computed walk-forward out-of-sample statistics stored in `strategy_regime_performance`.

### Computation Method (`refresh_from_market_data`)

**Walk-forward rules (no lookahead bias):**
- Only uses ranking runs where `as_of_date <= today - 30 days`
- Forward return uses nearest closing price `>= as_of_date + 28 calendar days`
- Minimum 100 ranked stocks per day to include that day in the aggregate
- One run per trading day (deduplicated by highest `ranked_stock_count`)

**Per-day IC formula:**
```
IC_day = CORR(composite_score, fwd_return_20d)

where:
  composite_score = ranking engine output score (higher = better ranked stock)
  fwd_return_20d  = (close at +28 days - entry close) / entry close
  CORR            = Pearson correlation across all ranked stocks that day
```
Positive IC = top-ranked stocks outperform. This is the standard quant convention.

**Aggregate statistics per (strategy, regime):**
```
avg_ic               = mean(IC_day)
ic_std               = stddev(IC_day)
n                    = count(days)
hit_rate             = count(IC_day > 0) / n          -- % of days with positive IC
ic_lower_95          = avg_ic - 1.645 × ic_std / √n   -- 95% CI lower bound (one-tailed)
expectancy           = mean(avg top-20 fwd returns per day)
expectancy_after_costs = expectancy - 0.001            -- 10bps round-trip cost hurdle
```

### Live Evidence (as of 2026-06-06)

| Strategy | Regime | avg_ic | ic_lower_95 | hit_rate | n (days) | expectancy |
|----------|--------|--------|-------------|----------|----------|------------|
| breakout_v1 | **BULL_LOW_VOL** | +0.047 | **+0.040** | 66.7% | 748 | +3.31% |
| momentum_v1 | **BULL_LOW_VOL** | +0.053 | **+0.046** | 70.0% | 763 | +3.24% |
| breakout_v1 | BEAR_LOW_VOL | −0.082 | −0.098 | 28.7% | 157 | +0.92% |
| momentum_v1 | BEAR_LOW_VOL | −0.063 | −0.079 | 28.0% | 175 | +0.12% |
| breakout_v1 | BEAR_HIGH_VOL | −0.042 | −0.084 | 51.6% | 31 | +4.61% |
| momentum_v1 | BEAR_HIGH_VOL | −0.005 | −0.034 | 63.8% | 47 | +2.15% |
| breakout_v1 | BULL_HIGH_VOL | −0.160 | −0.205 | 7.1% | 28 | +6.70% |
| momentum_v1 | BULL_HIGH_VOL | −0.124 | −0.170 | 20.0% | 30 | +7.74% |

---

## 4. Edge State Classification

### Thresholds (`RCEEConfig` — all config-driven)

```python
@dataclass(frozen=True)
class RCEEConfig:
    # EDGE_PRESENT
    edge_present_ic_lower_95: float = 0.010   # 95% CI lower bound must exceed 1%
    edge_present_hit_rate:    float = 0.55    # IC must be positive on >55% of days
    edge_present_sample_days: int   = 60      # minimum 60 days of evidence

    # EDGE_WEAK
    edge_weak_ic_lower_95:    float = 0.000   # CI lower bound must be non-negative
    edge_weak_hit_rate:       float = 0.50    # IC positive on >50% of days
    edge_weak_sample_days:    int   = 30      # minimum 30 days

    cost_hurdle: float = 0.001                # 10bps round-trip
```

### Decision Logic (`evaluate()`)

```
Given (avg_ic, ic_lower_95, hit_rate, sample_days) for a (strategy, regime) pair:

gate_ic_present  = ic_lower_95  ≥  0.010
gate_hr_present  = hit_rate     ≥  0.55
gate_n_present   = sample_days  ≥  60

gate_ic_weak     = ic_lower_95  ≥  0.000
gate_hr_weak     = hit_rate     ≥  0.50
gate_n_weak      = sample_days  ≥  30

if gate_ic_present AND gate_hr_present AND gate_n_present:
    → EDGE_PRESENT

elif gate_ic_weak AND gate_hr_weak AND gate_n_weak:
    → EDGE_WEAK

else:
    → NO_EDGE

if no row in DB for this (strategy, regime):
    → UNKNOWN  (fallback to legacy validation gate)
```

Every gate result is individually recorded in `gate_results` dict for full auditability.

### Current Edge States

| Strategy | Regime | Edge State |
|----------|--------|------------|
| breakout_v1 | BULL_LOW_VOL | ✅ **EDGE_PRESENT** (lb=+0.040, hr=0.667, n=748) |
| momentum_v1 | BULL_LOW_VOL | ✅ **EDGE_PRESENT** (lb=+0.046, hr=0.700, n=763) |
| breakout_v1 | BEAR_LOW_VOL | ❌ **NO_EDGE** (lb=−0.098, hr=0.287, n=157) |
| momentum_v1 | BEAR_LOW_VOL | ❌ **NO_EDGE** (lb=−0.079, hr=0.280, n=175) |
| breakout_v1 | BEAR_HIGH_VOL | ❌ **NO_EDGE** (lb=−0.084, hr=0.516, n=31) |
| momentum_v1 | BEAR_HIGH_VOL | ❌ **NO_EDGE** (lb=−0.034, n=47, fails hit_rate) |
| Both | BULL_HIGH_VOL | ❌ **NO_EDGE** (deeply negative IC) |

---

## 5. Recommendation Engine Integration

### R-ENTRY-02-RCE (replaces old R-ENTRY-02)

Entry gate evaluation order in `engine.py`:

```
1. R-ENTRY-01: rank > top_pool_size (20)  →  REJECT  [reason: RANK_OUTSIDE_POOL]

2. R-ENTRY-02-RCE (RCEE gate):
   if regime_fit available:
     NO_EDGE   →  WATCH  [reason: REGIME_NO_EDGE,    confidence: UNKNOWN]
     EDGE_WEAK →  WATCH  [reason: LOW_EXPECTANCY,    confidence: EARLY]
     EDGE_PRESENT → continue ↓
   else (fallback — regime_fit=None):
     insufficient_data → WATCH  [reason: VALIDATION_PENDING]

3. Conviction scoring (see §6)

4. R-ENTRY-03: conviction.band == BLOCKED  →  REJECT  [reason: CONVICTION_LOW]

5. R-ENTRY-05a: conviction.band == LOW     →  WATCH   [reason: CONVICTION_LOW]

6. R-ENTRY-04: regime_posture == "defensive" → WATCH  [reason: REGIME_BLOCK]
   (fires even with EDGE_PRESENT — defence in depth)

7. R-ENTRY-05b: buy_count >= max_buy_slots (5) → WATCH [reason: PORTFOLIO_FULL]

8. Exceptional daily cap: EXCEPTIONAL band + count >= 3 → WATCH

9.  →  BUY  [lifecycle: CANDIDATE, confidence: VALIDATED/HIGH_CONFIDENCE/EARLY]
```

### Recommendation Confidence for BUY

```python
if EDGE_PRESENT and sample_days >= 200:  →  HIGH_CONFIDENCE
if EDGE_PRESENT and sample_days >= 60:   →  VALIDATED
if EDGE_PRESENT and sample_days < 60:    →  EARLY
else:                                    →  UNKNOWN
```

Both strategies in BULL_LOW_VOL have 748/763 days → all BUYs get `HIGH_CONFIDENCE`.

---

## 6. Conviction Scoring Integration

### Formula (`conviction_scorer.py`)

```
conviction_score = clamp(round(
    0.26 × S_rank_quality
  + 0.32 × S_regime_fit          ← replaced S_validation (ADR-032)
  + 0.16 × S_ic_factor
  + 0.16 × S_regime
  + 0.10 × S_exit_health
), 0, 100)
```

### S_regime_fit Mapping

```
EDGE_PRESENT  →  85.0   (strong evidence, high weight)
EDGE_WEAK     →  50.0   (marginal evidence, neutral weight)
NO_EDGE       →  15.0   (negative evidence, heavy penalty)
UNKNOWN/None  →  35.0   (legacy floor, same as old insufficient_data)
```

### S_rank_quality

```
pool_score       = 100  if rank ≤ 20
                 = 100 × (50 - rank) / 30  if 20 < rank ≤ 50
                 = 0    if rank > 50

separation_score = % of top-20 scores below this stock's score × 100

rank_penalty     = min(rank, 5) × 8  if rank ∈ [1..5] and not rank_v2_promoted

S_rank = 0.6 × pool_score + 0.4 × separation_score - rank_penalty
       clamp to [0, 100]
```

### S_ic_factor (live factor IC health)
```
factor_ic_median > 0.03   →  80.0  (factors working well)
factor_ic_median ∈ [0, 0.03] →  55.0  (factors marginal)
factor_ic_median < 0      →  30.0  (factors failing)
None                      →  50.0  (unknown)
```

### S_regime (macro posture)
```
risk_on    →  75.0   (BULL_LOW_VOL maps here)
neutral    →  55.0
defensive  →  25.0   (BEAR* maps here)
```

### S_exit_health (position state)
```
none                 →  70.0
active_clean         →  80.0
active_deteriorating →  20.0
active_decay         →  15.0
```

### Conviction Bands
```
score ≤ 29   →  BLOCKED      (never BUY)
score 30–49  →  LOW          (WATCH only)
score 50–69  →  MEDIUM       (BUY eligible)
score 70–84  →  HIGH         (BUY eligible)
score 85–100 →  EXCEPTIONAL  (BUY eligible, daily cap = 3)
```

**Rank inversion guard:** ranks 1–5 with `rank_v2_promoted=False` are capped at HIGH (max 84) — top scores in a compressed ranking cannot claim EXCEPTIONAL without calibration.

### Worked Example — HFCL.NS today (BEAR_LOW_VOL, rank 8)

```
S_rank_quality  = 0.6×100 + 0.4×(75%) - 0 = 90.0  (rank 8 in top pool, high separation)
S_regime_fit    = 15.0  (NO_EDGE)
S_ic_factor     = 50.0  (factor_ic unknown / neutral)
S_regime        = 25.0  (defensive — BEAR_LOW_VOL)
S_exit_health   = 70.0  (no active position)

raw = 0.26×90 + 0.32×15 + 0.16×50 + 0.16×25 + 0.10×70
    = 23.4 + 4.8 + 8.0 + 4.0 + 7.0
    = 47.2  →  score = 47  →  band = LOW

Conviction: 47 LOW
Action: WATCH  [RANK_POOL_TOP20, REGIME_NO_EDGE]
```

---

## 7. Exit Symmetry — R-EXIT-05

When a position is already open, RCEE monitors for edge degradation:

```python
# In ExitSignal
edge_degraded: bool = False  # regime edge deteriorated since entry

# In _resolve_position_state (engine.py)
if exit_signal.edge_degraded:
    exit_reasons.append("EDGE_DEGRADED")
    → EXIT_APPROVED  (HITL must confirm, no auto-execution)
```

`edge_degraded` is set to `True` in `recommendation_service._load_exit_signals` when:
```
regime_fit is not None AND regime_fit.edge_state == NO_EDGE
```

---

## 8. Freshness Check (Approval-time)

Before an investor approves a BUY, `check_recommendation_freshness()` validates:

```
1. STALE_AGE         — recommendation older than 3 trading days
2. RANK_EXITED_POOL  — stock no longer in top 20
3. REGIME_EDGE_LOST  — regime has since rotated to NO_EDGE
```

If any check fails → `STALE_BREACH` → execution is prohibited.

---

## 9. Governance Constraints (Unchanged)

| Constraint | Status |
|-----------|--------|
| LLMs may not modify recommendation actions | ✅ Enforced |
| Committees are advisory only | ✅ Enforced |
| Conviction scoring is deterministic | ✅ Enforced |
| Human approval required before execution | ✅ Enforced |
| Full lineage and audit trail | ✅ `gate_results` + `conviction_components` stored per result |
| Ranking math frozen | ✅ Not touched |

---

## 10. Full Data Flow

```
daily market data (NIFTY ^NSEI + 500 stocks)
        ↓
regime_label computation (200d MA + 30d vol)
        ↓
ranking engine → ranking_results (score per stock)
        ↓
refresh_from_market_data() [every daily batch]
  → joins ranking_results × market_data (28d forward)
  → computes IC per day per regime
  → aggregates: avg_ic, ic_lower_95, hit_rate, expectancy
  → upserts strategy_regime_performance
        ↓
RCEE evaluate() [per recommendation run]
  → loads strategy_regime_performance for (strategy, regime_label)
  → evaluates 6 gates → EdgeState
  → returns RegimeFit with full audit trail
        ↓
recommendation engine R-ENTRY-02-RCE
  → NO_EDGE    → WATCH + REGIME_NO_EDGE
  → EDGE_WEAK  → WATCH + LOW_EXPECTANCY
  → EDGE_PRESENT → continue to conviction scoring
        ↓
conviction scorer
  → S_regime_fit = f(EdgeState): 85 / 50 / 15 / 35
  → weighted sum → score → band
        ↓
BUY / WATCH / REJECT with confidence label
        ↓
HITL approval → freshness check → paper trade
```

---

## 11. When Will BUYs Return

BUYs will appear the **first day** that:
```
NIFTY close  >  200-day moving average    (BULL trend)
AND
30-day rolling volatility  <  threshold   (LOW_VOL)
```

On that day:
- `regime_label` → `BULL_LOW_VOL`
- RCEE loads ic_lower_95=+0.040 (breakout) / +0.046 (momentum)
- Both pass all EDGE_PRESENT gates
- Engine generates up to 5 BUYs per strategy
- Confidence: `HIGH_CONFIDENCE` (748/763 days evidence)
- Top candidates: HFCL.NS (#1–8), KARURVYSYA.NS, HINDCOPPER.NS, VTL.NS

Current streak: BEAR_LOW_VOL since **2026-04-29** (26 trading days as of Jun 6).
