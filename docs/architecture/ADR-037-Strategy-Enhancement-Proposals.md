# ADR-037: Strategy Enhancement Proposals for Higher CAGR and Win Rate

**Status:** PROPOSED  
**Date:** 2026-06-21  
**Author:** System review post clean-slate backtest (2021–2026 replay)  
**Context:** After fixing core bugs (intraday stop EOD confirmation, exit reason tracking, re-entry cooldown, regime classifier, MTM subquery), a systematic review of every layer of the strategy pipeline was conducted to identify improvements that could increase CAGR and win rate beyond the baseline fixes.

---

## Background

The clean-slate replay (Jan 2021 → Jun 2026, 4 strategies, paper trading from day 1) revealed:
- Win rate: 14–34% depending on period
- Average hold: 2–3 days (too short — stop-loss and rank-drop exits dominating)
- Long holds (9–17 days) avg +₹150–270K; short holds (1–3 days) avg −₹7–35K
- RCEE blocks BUYs for first ~5 months (ic_lower_95 < 0.010 with only 52 samples)
- `low_vol_v1` was entirely missing from the strategy list (fixed in this session)
- No BUYs in BEAR_HIGH_VOL ever (full dead zone)

The proposals below are grouped by pipeline layer and prioritized by expected impact.

---

## Proposals

---

### P-01: Cross-Strategy Consensus Scoring
**Layer:** Recommendation Engine  
**Priority:** 1 — Highest impact on win rate  

**Problem:** Each strategy runs independently. A stock ranked #3 by momentum_v1 AND #5 by breakout_v1 on the same day is treated identically to one ranked #3 by only one strategy.

**Proposal:** When ≥ 2 strategies independently rank the same stock in their top 10 on the same day, boost the conviction band by one level (MEDIUM → HIGH, HIGH → EXCEPTIONAL). Record reason code `CROSS_STRATEGY_CONSENSUS`.

**Rationale:** Independent factor models agreeing on the same stock is a multiplicative confidence signal. In quantitative research this is called "signal stacking" and consistently improves hit rate.

**Expected impact:** +8–12% win rate on consensus entries.

**Implementation notes:**
- Collect all ranking results across strategies for the day before running the recommendation engine
- Pass a `consensus_stock_ids: dict[UUID, int]` (stock_id → count of strategies ranking it top 10) to the engine
- Boost conviction in `_evaluate()` after the standard conviction calculation

---

### P-02: Dynamic Trailing Stop (Profit Ladder)
**Layer:** Exit Monitor — `triggers.py`  
**Priority:** 2 — Direct CAGR improvement  

**Problem:** Current trailing stop is flat: 5% drawback fires as soon as max_gain ≥ 5%. This exits stocks at +20% that pulled back to +15% — surrendering half of large winners unnecessarily.

**Proposal:** Replace flat trailing with a profit-dependent ladder:

| Max Gain Reached | Trail (Drawback to Exit) |
|---|---|
| 5–10% | 5% (current) |
| 10–20% | 8% |
| 20–35% | 12% |
| > 35% | 15% |

**Rationale:** Winning trades need room to run. The 9–17 day holds in the backtest averaged +₹150–270K but a tight 5% trail can fire prematurely on any normal 1-day pullback. A profit ladder respects momentum continuation while still protecting downside.

**Implementation notes:**
- Modify `check_trailing_stop()` in `triggers.py`
- Introduce `_trailing_pct(max_gain_pct: float) -> float` helper mapping gain → trail threshold
- No schema changes needed; `max_gain_pct` already tracked in `RecommendationOutcome`

---

### P-03: Hard Profit Lock at +20%
**Layer:** Exit Monitor — `triggers.py`  
**Priority:** 2 (paired with P-02)  

**Problem:** A position at +25% can theoretically fall all the way to −8% (stop loss) without any floor. Once a trade is significantly in profit, the stop should never go below a minimum positive level.

**Proposal:** Once `max_gain_pct ≥ 20%`, enforce a floor: stop_floor = max_gain_pct × 0.5. The trailing stop can never drop the exit level below this floor.

Example: Stock at +25% max gain. Floor = +12.5%. Even if the standard trailing (at +25% → 15% trail) would allow exit at +10%, the floor clamps it to +12.5%.

**Implementation notes:**
- Computed inside `check_trailing_stop()` after determining the current exit level
- Condition: `if max_gain_pct >= 20.0: exit_floor = max_gain_pct * 0.5`

---

### P-04: Provisional RCEE Edge for Early Regime Samples
**Layer:** RCEE — `regime_edge_engine.py`  
**Priority:** 3 — Unlocks early deployment  

**Problem:** `EDGE_PRESENT` requires `ic_lower_95 ≥ 0.010`. With only 52 samples and typical `ic_std ≈ 0.13`, `ic_lower_95 = avg_ic − 1.645 × (ic_std / sqrt(n))` is deeply negative even when the strategy is genuinely profitable. Result: zero BUYs for the first 5 months of a new run.

**Proposal:** Add a new edge tier `EDGE_PROVISIONAL`:

```
EDGE_PROVISIONAL gates (ALL must pass):
  ic_lower_95 >= -0.005   (barely not significantly negative)
  hit_rate >= 0.52
  sample_count >= 25
  sample_count < 90       (only applies in early period)
```

When `EDGE_PROVISIONAL`: allow 1 BUY/day per strategy, conviction capped at MEDIUM, position sized at 75% of normal slot. Record reason code `PROVISIONAL_EDGE`.

Once sample_count ≥ 90, this tier is no longer available — strategy must meet full EDGE_PRESENT or EDGE_WEAK gates.

**Rationale:** Early in the backtest, no BUYs means no learning. The RCEE's own IC stats are computed from trades — if we never trade, we never get data. Provisional edge breaks this cold-start deadlock with appropriate caution.

**Implementation notes:**
- Add `EDGE_PROVISIONAL` to `EdgeState` enum
- Add gate logic in `load_regime_fit()` after existing EDGE_WEAK check
- Add `provisional_allowed: bool` flag to `RCEEConfig` (default True, disable in live)

---

### P-05: Volume Confirmation on Entry Day
**Layer:** Recommendation Engine / Paper Pilot  
**Priority:** 4 — Win rate improvement  

**Problem:** We enter positions regardless of that day's volume. A breakout or momentum signal with below-average volume is unconfirmed — the price move isn't backed by conviction.

**Proposal:** For `momentum_v1` and `breakout_v1`, require that the entry day's volume ≥ 70% of the stock's 90-day average volume. If volume is low, downgrade action from BUY → WATCH with reason code `LOW_VOLUME_ENTRY`. `reversal_v1` and `low_vol_v1` are exempt (reversal buys quiet names intentionally).

**Implementation notes:**
- Fetch entry-day volume in the paper pilot's buy execution step (available in GlobalBarStore)
- Add `entry_day_volume_ratio` to the conviction context
- Alternatively enforce in the recommendation engine if daily volume is available at ranking time

---

### P-06: Portfolio-Level Drawdown Circuit Breaker
**Layer:** Portfolio Service — `_resolve_regime_posture()`  
**Priority:** 5 — Drawdown protection  

**Problem:** If the regime classifier is wrong (e.g., Jan–Mar 2022: NIFTY fell 15% but 200-day SMA still showed BULL), the portfolio keeps buying into a falling market. The regime fix (ADR-036 death cross + drawdown signals) helps but isn't foolproof.

**Proposal:** Overlay a portfolio-level override: if the portfolio NAV has fallen ≥ 12% from its rolling 60-day peak, force posture to `"defensive"` regardless of regime label. Reset only when NAV recovers above the 60-day peak × 0.93.

**Rationale:** The portfolio knows its own P&L better than the macro regime signal. If we're actually losing money, stop adding new positions until recovery.

**Implementation notes:**
- In `_resolve_regime_posture()`, fetch last 60 days of NAV from `portfolio_nav_history`
- Compute drawdown from rolling peak
- If drawdown ≥ 12%: return "defensive" regardless of regime input
- Add `portfolio_drawdown_override: bool` field to the posture resolution output for audit

---

### P-07: Rank Relative Deterioration Exit
**Layer:** Exit Monitor — `triggers.py`  
**Priority:** 6 — Exit quality improvement  

**Problem:** Current `EXIT_RANK_DROP` fires when rank > 40. A stock that entered ranked #5 and is now ranked #35 has deteriorated by 30 positions but doesn't trigger. A stock entering ranked #19 that moves to #41 does trigger. The absolute threshold is poorly calibrated for high-quality entries.

**Proposal:** Dual-condition exit:
- Current: `rank > 40` (keep as safety net)
- Add: `rank > entry_rank + 20` (relative deterioration)

Either condition fires `EXIT_RANK_DROP`. The relative condition catches high-conviction entries that have silently degraded without crossing the absolute threshold.

**Implementation notes:**
- Store `entry_rank` in `portfolio_positions` (currently not tracked explicitly — need to join recommendation_result via `recommendation_result_id`)
- Or pass `entry_rank` into the exit monitor context at position open time and store it

---

### P-08: Regime-Dependent Capital Deployment
**Layer:** Portfolio Service — `compute_allocation()`  
**Priority:** 7 — CAGR improvement  

**Problem:** `deploy_pct = 0.85` is flat regardless of regime. In BULL_LOW_VOL (best conditions) we leave 15% idle. In BEAR_HIGH_VOL we still try to deploy 85%.

**Proposal:** Regime-dependent deployment ceiling:

| Regime | Deploy % | Rationale |
|---|---|---|
| BULL_LOW_VOL | 92% | Best conditions — maximize exposure |
| BULL_HIGH_VOL | 80% | Bull but volatile — moderate buffer |
| BEAR_LOW_VOL | 65% | Reversal bets only — preserve capital |
| BEAR_HIGH_VOL | 50% | Defensive — half capital idle |

**Implementation notes:**
- Add `regime_deploy_pct: dict[str, float]` to `PortfolioConfig`
- Resolve in `get_limits()` based on current regime label
- Fall back to 0.85 if regime unknown

---

### P-09: RSI Oversold Filter for reversal_v1
**Layer:** Ranking Strategy — `reversal_v1.py`  
**Priority:** 8 — Win rate for reversal strategy  

**Problem:** reversal_v1 buys the most beaten-down stocks but doesn't distinguish between temporary panic sellers and genuinely deteriorating businesses (debt spirals, governance failures). Both score high on anti-momentum.

**Proposal:** Add RSI(14) as a factor filter in reversal_v1: stock must have RSI(14) < 40 to be eligible (return 0 score if RSI ≥ 40). This confirms the oversold condition technically, not just by return rank. Additionally, add RSI(14) as a small explicit factor with weight 0.05 (lower RSI → higher score) within the top 10% oversold bucket.

**Implementation notes:**
- Add `compute_rsi(bars, window=14)` to `math_utils.py`
- Apply in `reversal_v1.py` as a pre-filter before factor computation

---

### P-10: Multi-Timeframe Momentum in momentum_v1
**Layer:** Ranking Strategy — `momentum_v1.py`  
**Priority:** 8  

**Problem:** Current momentum uses a single 63-day window. Research (Jegadeesh & Titman 1993, Asness 1994) shows that "12-1 month" momentum (return from 252 days ago to 21 days ago, skipping the last month) has significantly less reversal bias than raw 63-day momentum. The last month of price action contains mean-reversion noise.

**Proposal:** Split the existing `volatility_adjusted_momentum` factor (weight 0.40) into two sub-components:
- 63-day risk-adjusted return: weight 0.20 (captures recent thrust)
- 252d-to-21d risk-adjusted return (skip last month): weight 0.20 (captures persistent trend)

**Implementation notes:**
- In `momentum_v1.py`, compute two momentum scores: standard 63d and (close[−21] / close[−252]) − 1
- Normalize both cross-sectionally, combine with 50/50 weight
- Requires 252-day history (currently only needs 201 days) — update `HISTORY_DAYS`

---

### P-11: low_vol_v1 Permitted in BEAR_HIGH_VOL
**Layer:** Portfolio Service — regime slot configuration  
**Priority:** 9  

**Problem:** BEAR_HIGH_VOL is a complete dead zone — 0 BUYs, all strategies blocked. But low_vol_v1 selects the calmest stocks in the universe (FMCG, pharma, utilities, IT services) which historically hold up during high-volatility bear markets. Leaving capital 100% idle in this regime costs opportunity.

**Proposal:** In BEAR_HIGH_VOL: allow low_vol_v1 specifically to place 1 BUY/day, with:
- Max 3 positions (not 4 defensive slots)
- Tighter stop loss: −3% (vs standard −6%)
- Conviction capped at MEDIUM
- RCEE must confirm EDGE_PRESENT for low_vol_v1 in BEAR_HIGH_VOL

**Implementation notes:**
- Add `strategy_overrides: dict[str, str]` to posture config — maps strategy_name to posture_override when main posture is "defensive"
- Gate the override with RCEE confirmation

---

### P-12: BULL_HIGH_VOL Posture Upgrade
**Layer:** Portfolio Service — `_resolve_regime_posture()`  
**Priority:** 9  

**Problem:** BULL_HIGH_VOL maps to "neutral" (6 slots, 1 buy/day). But current backtest data shows breakout_v1 in BULL_HIGH_VOL has ic_lower_95 = +0.021 and hit_rate = 69.8% — the strongest edge observed. Capping at 1 buy/day underutilizes this regime.

**Proposal:** When BULL_HIGH_VOL AND RCEE confirms EDGE_PRESENT for the active strategy: upgrade posture to "limited_risk_on" (7 slots, 2 buys/day). Without RCEE confirmation: keep "neutral".

**Implementation notes:**
- Add new posture tier `"limited_risk_on"`: slots=7, buys_per_day=2
- Resolve conditionally in `_resolve_regime_posture()` based on regime + RCEE state

---

### P-13: Benchmark Alignment (NIFTY 500 vs NIFTY 50)
**Layer:** Ranking Strategies — all strategies using Relative Strength  
**Priority:** 10  

**Problem:** Relative Strength in momentum_v1, breakout_v1, reversal_v1 is computed as `return_stock − return_NIFTY50`. Our universe is NIFTY 1000 which includes many mid/small caps. A NIFTY 1000 small-cap with +15% return vs NIFTY 50's +12% gets RS = +3%. But NIFTY 500 mid-caps may have returned +18% in the same period — so that small-cap actually underperformed its peers. The wrong benchmark distorts RS signals.

**Proposal:** Change benchmark for RS computation to NIFTY 500 (or NIFTY Midcap 150) to match the universe composition. Keep NIFTY 50 only for regime classification (200-day SMA, drawdown) since it's more liquid and represents macro trend.

**Implementation notes:**
- Add a separate `ranking_benchmark_symbol` config distinct from `regime_benchmark_symbol`
- Ingest NIFTY 500 index data (`^CRSLDX` or similar) if not already present
- Pass ranking benchmark bars separately to strategy factor computation

---

### P-14: Market Breadth Signal for Faster Regime Detection
**Layer:** Regime Classifier — `app/validation/regimes.py`  
**Priority:** 5 (tied with P-06 — both are drawdown protection)

**Problem:** The current regime classifier has a realistic detection lag of **3–8 weeks** into a correction before flipping to BEAR. This is because even the fastest current signal (10% drawdown from 52-week high) requires the index itself to fall meaningfully. Large-caps hold the index up while mid/small caps — which make up the bulk of NIFTY 1000 — are already in bear territory. The system keeps buying into a deteriorating underlying market.

**Lag analysis of current signals:**

| Signal | Typical Detection Lag | Notes |
|---|---|---|
| Close < SMA(200) | 3–5 months | Too slow for corrections |
| SMA(50) < SMA(200) death cross | 6–10 weeks | Confirms what already happened |
| Close < 52w high × 0.90 | 3–8 weeks | Fastest current signal |
| **Market breadth < 45%** | **1–3 weeks** | Proposed addition |

**Proposal:** Add a 4th BEAR trigger — **market breadth below threshold**:

```
breadth_score = % of NIFTY 1000 universe stocks with close > SMA(50)

BEAR signal fires if: breadth_score < 0.45 (< 45% of stocks above 50-day SMA)
```

This fires 1–3 weeks into a correction because mid/small caps start breaking their 50-day SMA well before the NIFTY 50 index crosses its 200-day SMA. In the Jan–Mar 2022 correction, breadth below 45% was reached in mid-December 2021 — **3+ months before the SMA(200) signal**.

**Why 45% and SMA(50)?**
- 50-day SMA: moves fast enough to detect new downtrends, slow enough to filter 1–3 day noise
- 45% threshold: in a healthy bull market, typically 55–70% of stocks are above their 50-day SMA. Dropping below 45% signals genuine deterioration, not a brief dip
- Confirmed non-noisy: requires 3 consecutive daily closes with breadth < 45% before flipping (avoids triggering on a single bad day)

**Confirmation window to reduce false positives:**
```
BEAR if ANY of:
  - bear_200 (close < SMA200)
  - bear_death_cross (SMA50 < SMA200)
  - bear_drawdown (close < 52w_high × 0.90)
  - bear_breadth (breadth < 0.45 for 3 consecutive days)
```

**Implementation notes:**
- `classify_regime()` currently takes only benchmark bars. Needs an additional `universe_bars: dict[UUID, list[PriceBar]]` parameter (or pre-computed breadth score)
- Breadth pre-computation: in `daily_batch_service.py`, after rankings are complete (all 1000 stocks have bars available), compute `breadth_pct = count(close > SMA50) / total_stocks` and pass to regime classification
- Store breadth score in `regime_history` table as a new column `breadth_pct` for audit and analysis
- GlobalBarStore already has all universe bars in memory — breadth computation is O(n) with no additional DB queries
- 3-day confirmation: requires storing last 3 days of breadth scores; can be derived from `regime_history` lookback

**Expected impact:**
- Regime flip: 1–3 weeks earlier vs current fastest signal
- Avoids entering momentum/breakout positions in the last 3–4 weeks before a bear market becomes obvious
- Complementary to P-06 (portfolio circuit breaker): breadth catches market-wide deterioration early, circuit breaker catches portfolio-specific damage

**False positive risk:** Medium. Breadth can dip below 45% briefly during sharp but temporary corrections (e.g., a 5% flash correction that recovers in 2 weeks). The 3-day confirmation window mitigates this but does not eliminate it. Backtest comparison will quantify false positive rate.

**Live evidence — 2024 H1 (replay):** The cleanest real-world confirmation of the P-13/P-14 thesis. Through Jan–Mar 2024 the regime stayed **BULL_LOW_VOL for all 50 days** (NIFTY 50 large-cap held up), yet the breakout portfolio **lost 13%** (NAV ₹15.86M → ₹13.75M; −19% from the Feb-7 peak of ₹17.03M) during the mid-March 2024 small-cap correction. Diagnosis:
- **The picks were right, the regime read was wrong.** The 69 names breakout entered that window *averaged +14.4% (median +15.8%, only 19/69 down)* over the period — the universe was fine in aggregate, but the *timing* was late-cycle.
- **Entry quality decayed monotonically as small-caps rolled over while the large-cap regime stayed bullish:** Jan entries 36% win / +0.94%; early-Feb 21% / −3.68%; late-Feb 20% / −1.59%; March 14% / −4.91%.
- **The system kept buying the falling knife:** 36 new breakout entries during the Feb-14→Mar-13 decline, at full BULL_LOW_VOL deploy% (P-08 risk_on = 92%).
- Exits were **not** the primary culprit here — 2024 losers were flat after exit (avg close +10d −0.07%), so this is an **entry/regime-segment** failure, not exit mistuning. Large-cap regime classification cannot see a small/mid-cap correction; breadth (P-14) computed on the NIFTY 1000 universe would have flipped weeks earlier and throttled the late-cycle entries.

This window is the strongest single argument for prioritising P-14 (and P-13 RS alignment) above their original Priority 5/10 — the drawdown it would have prevented (~₹2–3M, ~15% of NAV) dwarfs most other proposals' estimated impact.

---

### P-15: Minimum Hold Period Before Analytical Exits
**Layer:** Exit Monitor — `triggers.py`  
**Priority:** 1 (tied with P-01 — highest single impact finding from paper trade review)

**Problem:** Paper trade analysis of 75 losing positions (Jan–Sep 2021) revealed that EXIT_ALPHA_DECAY and EXIT_RANK_DROP are firing after 1 day at losses of -0.1% to -5%, crystallising losses in positions that **48% of the time recover +14.7% on average within the next 10 days**.

Concrete examples of the damage:
| Stock | Exited at | Why | Stock then did (10d) |
|---|---|---|---|
| NAHARCAP | -0.44% | EXIT_ALPHA_DECAY | +**59%** |
| SEAMECLTD | -1.52% | EXIT_ALPHA_DECAY | +**36.6%** |
| TANLA | -1.10% | EXIT_ALPHA_DECAY | +**32.6%** |
| GLOBUSSPR | -0.75% | EXIT_RANK_DROP | +**26.4%** |
| JBMA | -4.84% | EXIT_RANK_DROP | +**27.2%** |

The stop loss (at -6%) was the right protection mechanism — it never fired on these 36 recoveries because the stock never breached -6%. EXIT_ALPHA_DECAY and EXIT_RANK_DROP fired before the stop had a chance to protect, and before the position had any time to work.

**Full breakdown (75 losers):**

| Exit Reason | Trades | Recovered +1% within 10d | Hit Stop (-6%) within 10d |
|---|---|---|---|
| EXIT_ALPHA_DECAY | 46 | 20 (43%) — avg max +13.5% | 25 (54%) |
| EXIT_RANK_DROP | 31 | 16 (52%) — avg max +16.2% | 15 (48%) |

**The 52% that would have hit stop anyway** — early exit saved only ~2.8% vs holding to stop. The **48% that recovered** — early exit cost avg 17.4% of upside (exited at -2.7%, stock recovered to +14.7%).

**Proposal:** Enforce a **minimum 5-day hold** before EXIT_ALPHA_DECAY or EXIT_RANK_DROP can fire. The stop loss (-6%) remains active from day 1. No other analytical exits fire in the first 5 days.

```python
# In triggers.py — before evaluating EXIT_ALPHA_DECAY / EXIT_RANK_DROP:
hold_days = (today - position.entry_date).days
if hold_days < 5:
    return []   # suppress all analytical exits; stop loss handled separately
```

**Why 5 days specifically:**
- Most 1-day rank drops recover within 2–3 days (normal noise in a volatile market)
- 5 days is the minimum time for a momentum/breakout setup to show directional commitment
- The alpha decay check already requires the stock to have dropped significantly in rank — waiting 5 days filters out 1-day noise and confirms genuine trend reversal

**Expected impact:**
- Win rate improvement: +10–15% (48% of losers turn into holds that recover)
- Average loss reduction on surviving losers: -0.5% (slight increase from holding to stop vs early exit on the 52% that would stop anyway)
- Net: significantly positive — asymmetry strongly favours holding (avg +14.7% upside capture vs avg -2.8% extra downside risk)

**Implementation notes:**
- Modify `_evaluate_triggers()` in exit monitor to check `hold_days < min_hold`
- Make `min_hold_days: int = 5` a configurable parameter in `ExitMonitorConfig`
- Apply minimum hold only to: `EXIT_ALPHA_DECAY`, `EXIT_RANK_DROP`
- Never apply to: `EXIT_STOP_LOSS`, `EXIT_TRAILING_STOP`, `EXIT_LIQUIDITY` (these are price-based and must fire immediately)
- Log suppressed exits as `ALPHA_DECAY_SUPPRESSED_MIN_HOLD` for audit

---

### P-16: Minimum Hold for Re-Entry After Analytical Exit
**Layer:** Recommendation Engine — `recommendation_service.py`  
**Priority:** 2

**Problem:** The 7-day re-entry cooldown (implemented for EXIT_STOP_LOSS) does not apply to EXIT_ALPHA_DECAY or EXIT_RANK_DROP exits. After exiting NAHARCAP at -0.44% via alpha decay, the ranker immediately re-enters it the next day or a few days later — paying spread and commissions again and often exiting for another small loss.

Evidence from paper trades: NAHARCAP traded **5 times** (avg -0.94%), GLOBUSSPR **4 times** (avg -1.32%), VLSFINANCE **4 times** (avg -1.16%), TEJASNET **3 times** (avg -1.40%). Each round trip costs 0.5–1% in friction plus the realised loss.

**Proposal:** Extend the existing re-entry cooldown logic (currently stop-loss only) to also apply after EXIT_ALPHA_DECAY exits:
- EXIT_STOP_LOSS: 7-calendar-day cooldown (existing)
- EXIT_ALPHA_DECAY: **3-calendar-day cooldown** (new — shorter since not a stop, just noise)
- EXIT_RANK_DROP: no cooldown (rank drop means the stock genuinely lost its edge; if it recovers rank legitimately, that's a valid signal)

```python
# Extended cooldown logic in recommendation_service._load_cooldown_stock_ids()
COOLDOWN_BY_EXIT_REASON = {
    "EXIT_STOP_LOSS":    timedelta(days=7),
    "EXIT_ALPHA_DECAY":  timedelta(days=3),
}
```

**Expected impact:**
- Eliminates 60–70% of churn round-trips (NAHARCAP, GLOBUSSPR, VLSFINANCE pattern)
- Reduces transaction friction by estimated ₹50–80K over a 12-month replay
- Forces the ranker to wait for a cleaner re-entry signal

**Implementation notes:**
- Modify `_load_cooldown_stock_ids()` to accept a dict of `{exit_reason: cooldown_days}`
- Pass `cooldown_stock_ids` per-reason to the recommendation engine
- No schema changes needed — `exit_reason` already stored on `portfolio_positions`

---

### P-17: Stop Loss Floor After Minimum Hold (Breakeven Protection)
**Layer:** Exit Monitor — `triggers.py`  
**Priority:** 3

**Problem:** Once a position has been held 5+ days (past the P-15 minimum hold), it has survived the noise period. At this point, if the position is flat (0% to +3%), the -6% stop is still exposed. A random bad day can take a breakeven position to -6% and close it as a loser unnecessarily.

**Proposal:** After the minimum hold period (day 5+), raise the stop floor progressively:

| Hold Period | Stop Floor |
|---|---|
| Day 1–5 | -6% (initial stop, stop loss only fires) |
| Day 6–10 | -4% (tighter — position has had time to work) |
| Day 11–15 | -3% OR breakeven, whichever is higher |
| Day 16+ | Breakeven + 0.5% (never give back initial profit) |

This is distinct from the trailing stop (P-02) which only activates after significant gains. This progressive floor protects positions that haven't moved much but have survived long enough that the original thesis should have shown some sign.

**Rationale:** A position held for 10 days without showing +3% has likely lost momentum. Tightening the stop from -6% to -3% at day 6 captures the downside of a stalling position without exiting it prematurely in the first 5 days.

**Implementation notes:**
- Add `progressive_stop_floor(entry_date, entry_price, today, max_gain) -> float` helper
- Integrate into `check_stop_loss()` in triggers.py alongside the existing -6% check
- `min(dynamic_floor, stop_loss_price)` — never widen the stop beyond what was set at entry

---

### P-18: Horizon-Matched RCEE Edge Gate (reversal_v1 silently disabled)
**Layer:** RCEE — `regime_analytics_service.py`, `regime_edge_engine.py`, conviction/engine edge gate  
**Priority:** 1 (highest — a regime-routed strategy never trades)

**Problem:** `reversal_v1` was routed correctly to BEAR_LOW_VOL but generated **zero entries across all of 2023** despite 54 BEAR_LOW_VOL days and 1,719 candidates reaching MEDIUM+ conviction with slots wide open. During the Mar–May BEAR_LOW_VOL cluster (53 days) the portfolio sat **100% in cash**.

Root cause is a **horizon mismatch in the RCEE edge gate**, not the regime thesis:

- `strategy_regime_performance` computes edge at **horizon = 20 days only** (every strategy, one horizon).
- `reversal_v1` is a 3–5 day mean-reversion strategy (observed avg hold **3.9 days**).
- At h=20 the mean-reversion signal has fully decayed/inverted:
  - `ic_lower_95 = −0.034` (gate needs ≥ +0.010) ❌
  - `hit_rate = 0.36` (gate needs ≥ 0.55) ❌
  - → `edge_state = NO_EDGE`
- [`engine.py` R-ENTRY-02-RCE](../../app/recommendation/engine.py): `NO_EDGE` forces **WATCH** regardless of conviction or open slots → no buy ever fires.

**The proof it is a measurement artifact, not a real absence of edge:** the same row has `expectancy_after_costs = +0.0423` (**positive** — the strategy makes money per trade). The strategy is profitable at its native 3–5 day horizon but judged at 20 days where its edge does not exist. By contrast `breakout_v1` @ BULL_LOW_VOL passes (ic_lo95 +0.039, hr 0.73) only because it genuinely *is* a ~20-day trend strategy — its native horizon matches the gate.

This is the most likely explanation for the gap between this replay's CAGR and the earlier 19→24% backtest, where reversal-in-bear was a contributor.

**Proposal (two options):**
1. **Multi-horizon RCEE (proper fix):** compute IC / hit-rate at h=1,3,5,10,20 and gate each strategy on its native horizon — reversal_v1 / low_vol_v1 → short (h≈3–5); breakout_v1 / momentum_v1 → h=20. Requires a `horizon` dimension already present in `strategy_regime_performance` but only ever populated with 20.
2. **Expectancy-based gate (immediate unblock):** gate on `expectancy_after_costs > 0` (horizon-agnostic, already positive for reversal) in addition to / instead of the IC+hit-rate test in `regime_edge_engine.py`. Smaller change; unblocks reversal without restructuring RCEE.

**Recommendation:** ship #2 as the immediate unblock, #1 as the structural fix.

**Implementation notes:**
- Per-strategy native horizon config (e.g. `STRATEGY_RCEE_HORIZON = {"reversal_v1": 5, "low_vol_v1": 5, "breakout_v1": 20, "momentum_v1": 20}`).
- `regime_analytics_service` must compute and store all horizons (currently h=20-only).
- Edge-state classifier reads the strategy's matched horizon row.
- Must be validated by a full clean-slate replay — expect reversal_v1 to begin trading in BEAR_LOW_VOL and the Mar–May-type idle-cash gaps to close.

**Evidence base:** 2023 deep-dive over the completed replay (749/1348 days). reversal_v1: 245 rec runs, 0 BUYs, 1,719 MEDIUM-band candidates all `REGIME_NO_EDGE`; portfolio 100% cash on the four sampled BEAR_LOW_VOL dates. RCEE row `reversal_v1 / BEAR_LOW_VOL / h=20`: n=139, ic_lo95=−0.034, hr=0.36, expectancy_after_costs=+0.0423.

---

### P-19: EXIT_LIQUIDITY units bug + min-hold bypass (cuts breakout multibaggers)
**Layer:** Exit Monitor — `triggers.py:check_liquidity`, `service.py:_evaluate_triggers`  
**Priority:** 1 (highest — a units bug force-sells the strategy's biggest winners)

**Problem:** A forward-return study of all 943 closed breakout_v1 exits (price 15 trading days *after* each exit).

> **Correction / calibration note:** an initial read using *peak-over-30-days* overstated the effect — peak is volatility-biased (any small-cap peaks +10% sometime in a month). Re-run on **forward-15d-close vs the market drift baseline (+2.43%/15d in this 2021–23 bull run)**, most exits are *correctly* tuned: EXIT_STOP_LOSS −2.56% excess (good — stocks keep falling), EXIT_RANK_DROP −0.19% (≈market), EXIT_ALPHA_DECAY +0.87% (mildly eager). EXIT_LIQUIDITY's **median is −2.09%** (below market) — the *typical* liquidity exit correctly dumps a fader. **The liquidity defect is therefore a TAIL risk, not an average drag**: the units bug concentrates damage in the rare multibagger (p90 +24%, max +108%, 41/337 ran >+20% after exit). Because breakout's CAGR lives in a few big winners, the tail is exactly what must be protected.

The dominant tail offender is `EXIT_LIQUIDITY`:

- 330 liquidity exits: **56% fire at a 1-day hold, 94% at ≤4-day holds.**
- 74 of them (22%) ran ≥20% after we sold; avg post-exit peak **+12.6%**.
- **ASAL.NS** ran ₹215 → ₹926 (**+330%**) over Nov 2021–Jan 2022 and was captured as **~16 separate 1-day round-trips** booking ~+4.9% each, re-buying the next day every time. High "win rate," catastrophic opportunity cost.

**Two root causes:**

1. **Units bug in `check_liquidity`:**
   ```python
   days_to_unwind = position_value / avg_daily_volume   # ₹ / shares  ← dimensionally wrong
   ```
   `position_value` is `market_value` in **rupees**; `avg_daily_volume` is `latest.volume` in **shares**. The ratio is missing the `× price` factor, so `days_to_unwind` scales with the share **price**. As a breakout winner climbs, it looks progressively *more* illiquid and self-triggers a daily exit — the exact mechanism that shredded ASAL. Correct formula:
   ```python
   days_to_unwind = position_value / (avg_daily_volume * last_price)   # ₹ / (₹ traded per day)
   # equivalently: position_shares / avg_daily_volume_shares
   ```

2. **Liquidity exits bypass the P-15 minimum hold.** P-15 suppresses only *analytical* exits (rank drop, alpha decay); `EXIT_LIQUIDITY` is classified as a hard exit and fires from day 1. So even after the units fix, a genuinely-thin name can still be chopped before the thesis plays out.

**Proposal:**
- Fix the units in `check_liquidity` (value ÷ traded-value, not value ÷ shares). Highest-confidence, smallest change.
- Treat liquidity as a **sizing constraint at entry**, not a daily exit signal: size the position to ADV at entry so it never needs a liquidity exit later.
- If kept as an exit, exempt it during the P-15 minimum hold **and** when the position is still ranked in the entry pool (a top-ranked winner is not a position to dump for liquidity).

**Implementation notes:**
- `check_liquidity(avg_daily_volume, position_value, last_price, ...)` — pass `last_price` (already in ctx) and divide by `avg_daily_volume * last_price`.
- Re-validate the threshold (`liquidity_days_threshold=5.0`) after the units fix — the old threshold was calibrated against the broken (price-inflated) metric and will be far too tight once corrected.
- Full clean-slate replay to validate — expect breakout winners (ASAL-type names) to be held instead of round-tripped, and the 1-day-hold share of liquidity exits to collapse.

**Evidence base:** Forward-return deep-dive over the completed-years replay (Jan 2021–Jan 2024). Forward-15d-**close** vs market baseline +2.43%: EXIT_LIQUIDITY mean +2.16% but **median −2.09%** (typical exit fine), p90 +24%, max +108%, 41/337 ran >+20%. EXIT_LIQUIDITY hold-time: 1d 56%, ≤4d 94%. ASAL.NS round-trip log: 16 closes, mostly 1-day holds, against a +330% underlying move.

---

### P-20: EXIT_REGIME blanket liquidation dumps still-trending winners
**Layer:** Exit Monitor — `triggers.py:check_regime_change`, `service.py`  
**Priority:** 2

**Problem:** `EXIT_REGIME` is the one exit that is **broadly** mistuned (not just a tail). On forward-15d-close it returns **+7.70% vs the +2.43% market baseline — +5.27% excess**, the worst of any exit reason. [`check_regime_change`](../../app/portfolio/exit_monitor/triggers.py) fires whenever `current_regime_posture in ("defensive","crisis")` and **liquidates every open position indiscriminately** — it takes no account of the individual stock's trend, rank, unrealized P&L, or whether it is still in the entry pool. When the market posture flips, names in strong uptrends get dumped alongside genuine laggards: ASAL.NS (+108% in the 15 days after the regime exit), CHENNPETRO (+58%), GMDCLTD (+30%), COCHINSHIP (+26%), ZENTEC (+24%).

**Proposal:** Make the regime exit **selective** rather than a blanket liquidation:
- Only force-exit positions that are *also* showing individual weakness (negative unrealized P&L, or rank fallen out of the entry pool, or below a moving-average trend filter).
- Keep positions that are still ranked and trending — a portfolio-level risk signal should *stop new buying* and *tighten stops*, not market-sell a working winner.
- Alternatively, on a defensive flip, **scale down** (trim to a reduced target weight) instead of full exit, so the upside tail is retained while gross exposure drops.

**Rationale:** Regime posture is a *portfolio* signal; applying it as a *per-position* sell ignores that the best individual winners often run hardest right as breadth deteriorates (late-cycle blow-off). Pair with P-08 (regime-dependent deploy%) — deploy% already throttles new exposure on defensive regimes, so the blanket exit is partly redundant risk control bought at the cost of the biggest winners.

**Implementation notes:**
- `check_regime_change(current_posture, entry_posture, unrealized_pnl_pct, current_rank, entry_pool_size)` — fire only when defensive/crisis **AND** (pnl<0 OR rank outside pool).
- Consider urgency tiers: `crisis` → full exit (capital preservation dominates); `defensive` → selective/trim only.
- Validate via clean-slate replay — expect the EXIT_REGIME post-exit excess to collapse toward the market baseline and the multibagger tail (ASAL-type) to be retained through late-cycle.

**Evidence base:** Forward-return deep-dive (Jan 2021–Jan 2024), breakout_v1, forward-15d-close vs +2.43% market baseline. EXIT_REGIME n=42, mean +7.70%, excess +5.27% (highest). Top post-exit runners: ASAL +108%/+88%, CHENNPETRO +58%, GMDCLTD +30%, COCHINSHIP +26%, ZENTEC +24%. Trigger logic confirmed as unconditional on `posture in (defensive, crisis)`.

---

### P-21: Trade Decision Layer — rank *relative*, gate *absolute*, order by *expected value*
**Layer:** New seam between recommendation and entry — `paper_pilot_ops` + new `TradePrioritizer` (+ `TradeEligibility`)  
**Priority:** 1 (architectural — the missing layer that several other proposals are really components of)

**Core principle: three altitudes, not one.** The system currently collapses ranking, eligibility, and trade selection into a single conviction-ordered list. They are three different questions:

1. **RANK — relative, per strategy.** "Which stocks best express breakout-/momentum-/reversal-ness right now, *vs their peers*?" Factor-based, strategy-versioned, the signal RCEE measures edge on. In a falling segment the *best* breakout is still rank #1 — **rank #1 ≠ tradeable, and rank #1 ≠ most profitable.** Unchanged; never contaminated with regime/trend (that would break RCEE's per-regime measurement).
2. **ELIGIBILITY — absolute, binary veto.** "Is this specific stock, in this tape, healthy enough to own at all?" A pre-filter that removes candidates, never reorders.
3. **PRIORITIZE — cross-strategy, expected value.** "Of the eligible set, which earn the most per scarce slot?" The final ordering, by **expected forward return** — *not* by raw rank or conviction.

**Why altitude 3 is the part that was missing.** Slots are scarce (≤2 buys/day, ~8 positions). When slots bind, *ordering is the decision*. Strategy rank is the wrong sort key for it: rank is relative *within one strategy* and says nothing about how much that rank is worth. Worked example from the backtest: if rank #2 in this regime historically returns 5–6% but rank #8 returns 8–10%, taking #2 first (because conviction tracks rank) leaves 3–4% on the table every time slots bind. The correct sort key is **expected value**, pooled across all active strategies so a reversal pick and a breakout pick compete on one comparable axis.

**Expected-value definition:**
```
E[candidate] = expected_forward_return( strategy, market_regime, stock_segment_state, rank_bucket )
               net of costs, horizon-matched to the strategy's native hold
```
This needs one new data structure — **rank-bucketed expectancy**: today RCEE stores expectancy per `(strategy, regime)`; this extends it to `(strategy, regime, rank_bucket, segment_state)` ("stocks ranked 6–10 by reversal_v1 in BEAR_LOW_VOL in a downtrending segment historically returned X%"). Raw material already exists (historical rankings joined to forward returns — the same data RCEE computes IC from); only the rank dimension is added. Same discipline: bucket ranks (1–5 / 6–10 / 11–20), enforce a sample floor, condition on current regime, **horizon-match** (a 3-day reversal signal's expectancy measured at 3 days, not 20 — the P-18 lesson), and use **median / trimmed mean** so a single ASAL-type +100% outlier cannot inflate a bucket (P-19 lesson).

**The HITL dimension (why the output shape matters).** The system is designed to run HITL **on or off** (`hitl_enabled`). The output of this layer is the artifact the human reviews, so it must be **one priority-ordered, explainable queue** — identical in both modes:
- **HITL on** → the reviewer sees the queue best-EV-first and approves from the top. Ordering *is* the product: it puts the 8–10% name above the 5–6% name so scarce slots and human attention go to the right candidates. Each row is explainable: *stock · strategy · rank · market regime · segment state · expected return · conviction · eligibility reasons*.
- **HITL off** → the pilot auto-approves top-N within slot/buy limits using the **same ordering**.

Today `paper_pilot_ops` sorts BUY candidates by `conviction_score` — a relative-quality proxy, not expected return. P-21 replaces that sort key with expected value and surfaces the ordered list as the HITL review queue.

**Eligibility checks (altitude 2, all absolute):**

| Check | Altitude | Subsumes |
|---|---|---|
| Stock above its own 50-day SMA (individual uptrend) | per-stock | (new) |
| RS positive vs a *broad/segment* benchmark — synthetic equal-weight universe mean if no index ingested | per-stock | **P-13** |
| Volume confirmation (today ≥ 70% of 90d avg) | per-stock | **P-05** |
| Universe breadth above threshold (also governs *how many* slots open) | market | **P-14** |

**Pipeline:**
```
RANK (per strategy, RELATIVE)                                   ← unchanged
  → Recommendation (BUY/WATCH; rank pool + conviction + RCEE)        ← unchanged
    → ELIGIBILITY gate (ABSOLUTE veto: per-stock trend + RS + volume + breadth)   ← P-21 part A
      → PRIORITIZE (EXPECTED VALUE: rank-bucket × regime × segment, pooled, dedup)  ← P-21 part B ★
        → HITL queue  ──(on)──►  human approves top-N
                       ──(off)─►  auto-approve top-N within slot/buy limits
          → Entry (sizing, submit)
```

**Edge cases the design must handle (from the backtest so far):**
- **Cold start / thin buckets** (first months, 0–25 samples): no reliable EV → fall back to conviction ordering for those candidates; never trade on a 3-sample bucket. (Mirrors the 5-month cold-start deadlock P-04 addresses.)
- **Outlier-inflated buckets** (ASAL +330% in a bucket): use median/trimmed mean, not raw mean.
- **Same stock from multiple strategies**: dedup in the pooled queue — keep the highest-EV instance, tag `CROSS_STRATEGY_CONSENSUS` (ties to P-01).
- **All-negative EV** (bad regime, every eligible name has negative expectancy): take nothing — an empty queue is a valid, correct output. The system should be willing to sit in cash.
- **Regime just flipped**: condition EV strictly on the *current* regime so stale expectations don't leak across the boundary (the 2024 H1 failure mode).
- **Horizon mismatch**: EV horizon must match the strategy's hold (P-18) or short-horizon strategies are mis-valued.
- **EV ties / missing data**: deterministic tiebreak by conviction then rank, so replays stay reproducible.

**Why this structure (the payoff):**
- **Ranking stays pure** — versioned, RCEE-measurable; factor model untouched.
- **One place to reason about tradeability and selection** — instead of regime/trend logic scattered across deploy%, posture, conviction and exits, there is one eligibility veto + one EV ordering, fully auditable.
- **It unifies floating proposals** — P-05, P-13, P-14 become eligibility components; P-01 becomes a prioritization tag; P-18's horizon lesson becomes the EV horizon rule. P-21 is the seam they all belong in.
- **It is the entry-side counterpart to the exit-side findings (P-15/P-18/P-19/P-20):** both the buy decision and the sell decision must weigh absolute market/segment health and expected value, not just relative strategy fit.

**Implementation notes:**
- `TradeEligibility.evaluate(candidate, ctx) -> (eligible, reasons)` — pure, per-candidate veto.
- `TradePrioritizer.order(eligible_candidates, expectancy_provider, limits) -> ordered_queue` — pure ordering by EV with conviction fallback, dedup, deterministic tiebreak.
- `RankBucketExpectancy` provider: precomputed (weekly, like `strategy_regime_performance`) from `recommendation_results` (rank, strategy, regime) joined to `compute_forward_return`; cached; `None` for thin buckets.
- Wire into `paper_pilot_ops`: replace `sorted(..., key=conviction_score)` with the prioritizer's ordered queue; emit the queue (with explainable columns) to the batch result as the HITL review artifact.
- Fed by `GlobalBarStore` (per-stock + universe bars in memory → no new per-day DB load).
- **Sequencing:** (1) eligibility per-stock trend gate, (2) breadth (P-14) + synthetic-universe RS (P-13 intent), (3) rank-bucket expectancy + prioritizer, (4) HITL queue surfacing. Each validated by clean-slate replay.

---

### P-22: Defensive gold rotation in BEAR regimes (DEFERRED → v18 testing phase)
**Layer:** Portfolio / regime defensive sleeve  
**Priority:** High value, deferred — test after the current equity-only baseline (v17) is established.

**Problem:** In BEAR regimes the equity strategies are at best marginal (BEAR_LOW_VOL) or have *negative* edge (BEAR_HIGH_VOL — momentum/reversal buy the violent bounces and get crushed on reversal). The system currently sits in cash (0% return) in the defensive regime — a dead, ~half-the-timeline opportunity.

**Proposal:** Rotate the defensive sleeve into **gold (GOLDBEES)** during BEAR regimes instead of holding cash.

**Evidence — rolling 15-day forward returns by regime (2021–2026), gold vs NIFTY:**

| Regime | Windows | Gold 15d | NIFTY 15d | Action |
|---|--:|--:|--:|---|
| BULL_LOW_VOL | 42 | +0.53% | +0.42% | stay equity (breakout works) |
| BULL_HIGH_VOL | 3 | −2.28% | +0.05% | stay equity |
| **BEAR_LOW_VOL** | **36** | **+2.42%** | +0.46% | **gold sleeve (biggest, most robust edge)** |
| **BEAR_HIGH_VOL** | **8** | **+1.63%** | +2.84%* | **rotate to gold** (*index bounce we don't capture; our edge is negative here) |

Key points: gold's edge is concentrated in BEAR (both), **strongest and most robust in BEAR_LOW_VOL (+2.42%, 36 windows)**. ~49% of all windows are BEAR — a large unused return stream. Single-window gold returns during the dead BEAR_HIGH_VOL stretches: Feb–May 2022 +5.8%, full 2022 +12.1%, **2024 (equity −24% drawdown year) +19.3%** — the hedge fires exactly when equity hurts most. Gold ~3.5× in INR 2020→2026 (gold rally + rupee depreciation tailwind).

**Proposed rule:**
> Any BEAR regime → allocate the deployable defensive sleeve to GOLDBEES. Full rotation in BEAR_HIGH_VOL; in BEAR_LOW_VOL, blend gold with reversal_v1 (both have edge — likely a blend beats either alone).

**Data readiness (already done):** GOLDBEES daily OHLCV 2020-01-01 → 2026-06-22 (1,603 bars) is ingested into `market_data` (source=`yahoo`), added to `stocks`, and deliberately **kept out of `universe_memberships`** so the ranking strategies never trade it as an equity — only the gold-rotation rule references it. Source is Yahoo (no live Kite token at ingest time); identical prices, can be re-pulled from Kite later if desired.

**Caveats:** BEAR_HIGH_VOL sample is thin (8 windows); gold-vs-reversal in BEAR_LOW_VOL needs a traded backtest (both work); gold can sell off briefly in acute liquidity crises (Mar-2020); rotation timing on the regime flip matters (breadth P-14 helps catch the turn early). This is forward-return analysis, not yet a traded backtest with entry/exit/slippage on the gold leg.

**Status:** DEFERRED to v18 testing phase. Data is loaded and ready; implementation + head-to-head backtest (cash-in-bear vs gold-in-bear) to follow once the v17 equity baseline is complete.

---

### P-23: Regime-aware RCEE sample floor (rare bear regimes starved)
**Layer:** RCEE — `RCEEConfig.edge_present_sample_days_by_regime`  
**Priority:** Medium (v18) — unblocks reversal in young bear windows.

**Problem:** EDGE_PRESENT needs a flat 60-sample floor. But bear regimes are *rare* — they accumulate IC samples slowly (one per regime-day with a completed forward window). In v17, **reversal_v1 / BEAR_LOW_VOL had genuine edge by June 2022** (ic_lower_95 +0.0104 ✓, hit_rate 0.585 ✓, expectancy +0.029 ✓) but only **41 samples** (61 BEAR_LOW_VOL days minus ~20 with incomplete forward windows) — one batch short of 60. It dropped to PROVISIONAL_EDGE, and the **defensive-posture gate (`REGIME_BLOCK`) only honors EDGE_PRESENT** — so reversal sat out the entire BEAR_LOW_VOL window despite a statistically valid edge.

**Proposal:** Populate the ADR-036 regime-aware floor (currently an empty dict → flat 60) so rare regimes get a lower count floor:
```python
edge_present_sample_days_by_regime = {"BEAR_LOW_VOL": 40, "BEAR_HIGH_VOL": 35}
```
The IC's 95% CI already penalizes small samples, so a lower *count* floor doesn't weaken the significance test — it stops double-penalizing structurally-rare regimes. At n=41 reversal would clear EDGE_PRESENT → bypass the defensive gate → trade. Alternatively (or additionally), let PROVISIONAL_EDGE bypass the defensive gate.

---

### P-24: Turnover-aware / net-of-STT optimization (live-viability)
**Layer:** Cross-cutting — exits (hold period), RCEE cost hurdle, cost model, reversal_v1.  
**Priority:** HIGHEST for live (v18) — this is the gap between the backtest CAGR and reality.

**Problem:** The backtest charges only **~10 bps slippage + ₹40/trade flat brokerage** — it does **NOT include STT** (0.1% buy + 0.1% sell on delivery), GST, exchange, or stamp charges. STT is a **toll on turnover, not a tax on profit** — every trade pays it, win/lose/flat. The strategy holds ~5 days (reversal_v1: 1.8 days), turning the book over **~40–50×/year** — so it pays the ~0.2% STT round-trip ~50× a year ≈ **~10%/yr drag**. Cumulative traded value in v17: **₹4.85B → ~₹6–7M missing cost → true CAGR ~14–16%, not the ~24% headline.**

**Key reframe:** the backtest optimizes *gross* return (rewards many small wins); live optimizes **return-per-trade *net* of ~0.3% cost** (rewards *fewer, bigger* wins). **Win rate is not the lever — hold period and per-trade magnitude are.** reversal_v1 has the *higher* win rate (56%) but is the worst STT offender (1.8-day flips, ~140× turnover); breakout (40% win, 5–8 day holds, +6.95% avg win) survives costs. EXIT_RANK_DROP (longest holds, "let winners run") is the STT-friendly model the whole system should lean toward.

**CRITICAL distinction — the cost hurdle does NOT reduce turnover (verified):** Raising the RCEE `cost_hurdle` to 0.3% was tested against the rank-bucket EVs and **barely changes anything — 46 of 48 (strategy×regime×rank) buckets still clear 0.3%.** The reason: the per-trade *edge* (1–15% forward moves) is far larger than a 0.3% toll, so the gate keeps trading nearly everything. **Per-trade profitability and aggregate turnover cost are two separate things:**
- The **cost hurdle** answers "is this setup's edge > cost?" → almost always yes → it does **not** cut trade count.
- **Turnover cost (STT)** comes from *how often* you pay the toll — i.e. the **hold period** — not from per-trade unprofitability. At ~40× portfolio turnover/yr × ~0.2% STT ≈ ~8%/yr drag *even when every trade is profitable net of cost.*

Therefore the cost hurdle is for **honest edge measurement**, and **turnover reduction is *exclusively* an exit-side (hold-period) change.** Do not expect the hurdle to lower STT — it won't.

**Proposal (v18):**
1. **Add a full Indian cost model** to the fill/P&L path: STT (0.1%/side delivery), exchange txn (~0.003%), GST (18% on brokerage+txn), SEBI, stamp duty. Report **net-of-all-cost** CAGR. *(This is the measurement fix.)*
2. **Raise the RCEE `cost_hurdle` 10 bps → ~30 bps** — for **honest edge measurement** and to bench the genuinely-marginal strategies (low_vol loses 2/12 buckets at 0.3%). **Note: this does NOT reduce turnover** (46/48 buckets still clear it) — don't rely on it for STT relief.
3. **Lengthen holds — THE turnover/STT lever (exit-side).** This is the *only* thing that cuts the toll count. Implement the **day-5 "graduation" tiering**: days 1–5 only the hard stop is live (no analytical churn); at day 5, positions that are **green AND still ranked → winner-track** (loose trailing, run to 12–20 days), **red OR rank-dropped → cut now**. v17 data proves the separation is real and emergent — 1–5 day holds are 25–35% win/−1%, 11–20 day holds are **85% win/+11.3%**. Making it *deliberate* cuts the 1–5 day churn (the STT bleed) and extends the 11+ day winners (the profit engine). Halving turnover ≈ halving STT.
4. **Rework or retire reversal_v1 for live** — at ~140× turnover its per-trade edge is real but its *turnover toll* is lethal; only a much-longer-hold reversal_v2 survives real STT.
5. **Turnover as a first-class metric** — track annual turnover and net-of-cost CAGR per strategy; the decision metric is **(per-trade edge − full cost) × trade count**, optimised by *fewer, longer-held, bigger-move* trades — not by win rate.

**Evidence:** v17 (through Mar 2025): gross CAGR +23.7%, but ₹4.85B cumulative traded value × ~0.12–0.15%/leg missing cost ≈ ₹6–7M drag on ₹14M gross profit → net CAGR ~14–16%. Cost-hurdle test: 46/48 rank buckets clear 0.3% → confirms the hurdle is a *measurement* tool, not a turnover lever. Hold-period test: 1–5 day trades 25–35% win, 11–20 day trades 85% win — confirms turnover reduction must come from the exit/graduation rule. Relative comparisons (v17 vs v12, capped-stop impact) remain valid (same light cost model both runs); only the *absolute* CAGR is optimistic.

**Status:** DEFERRED to v18. The single most important change for a live go/no-go decision.

---

### P-25: Trend-persistence validation (select long-winners over short-losers at entry)
**Layer:** Validation — new metric alongside `validation_horizon_metrics` (IC) / `validation_decile_metrics`.  
**Priority:** High (v18) — the entry-side complement to P-24's exit-side turnover fix.

**Problem:** Current validation measures forward *return* (IC: does the rank predict where price goes). It does **not** measure **persistence/durability** (does the signal predict a *sustained trend* vs a *quick fade*). This is the missing piece for the turnover problem: 63% of v17 trades are 1–5 day holds that **lose ₹16.7M** *and* drive most of the STT, while the 11+ day holds (85% win) make all the money. Validation tells us *where* the average edge is (which buckets/regimes), but not *which individual entry* will become a 15-day winner vs a 5-day stop-out — that separation is currently only revealed *post-entry* (the P-24 day-5 graduation rule). A validation metric that predicts persistence would move part of that separation *to entry*.

**What validation can / can't do (the ceiling):**
- **Can (already):** population-level selectivity — concentrate entries in validated high-IC, stable-monotonic-decile zones; skip the marginal rank-11–20 / weak-regime zones that produce most short-churn losers.
- **Can't (today):** separate the individual future-long-winner from the future-short-loser at entry — they look identical until the stock's own price action reveals it.

**Proposal:** Add a **persistence/durability validation metric**, computed over history per (factor-profile or rank-bucket, regime):
> Conditional on entering here, P(sustained ≥10-day favourable move) vs P(fade/stop within 5 days), and the expected hold-to-peak.

Use it at the entry/prioritization layer (P-21) to **tilt selection toward high-persistence setups** — i.e. select for *future long-winners*, which simultaneously: (a) raises win rate of the trades taken, (b) lengthens average hold, (c) cuts the short-churn count → **attacks turnover and the winner/loser separation at the same time, at entry.**

**Why it's the biggest validation unlock:** P-24 reduces turnover on the *exit* side (hold survivors longer). P-25 reduces it on the *entry* side (take fewer fade-prone setups). Together they compress the 707 short-churn losers from both directions. Also synergistic with P-23 — richer/longer validation history makes all edge estimates (including persistence) fire with confidence sooner, so young bear-regime edges aren't benched.

**Status:** DEFERRED to v18. New validation dimension; pairs with P-24 (exit graduation) as the two-sided turnover fix.

---

## Implementation Priority Matrix

| ID | Proposal | Layer | Est. Win Rate Δ | Est. CAGR Δ | Effort | Status |
|---|---|---|---|---|---|---|
| P-01 | Cross-strategy consensus | Engine | +8–12% | +3% | Medium | N/A under single-strategy routing (realized in P-21 prioritizer) |
| P-02 | Dynamic trailing stop | Exit | +2% | +4% | Small | PROPOSED |
| P-03 | Hard profit lock +20% | Exit | +1% | +3% | Small | PROPOSED |
| P-04 | Provisional RCEE edge | RCEE | +3% | +2% | Small | IMPLEMENTED |
| P-05 | Volume confirmation | Engine | +5% | +1% | Small | PROPOSED |
| P-06 | Portfolio circuit breaker | Portfolio | 0% | +2% (drawdown) | Small | PROPOSED |
| P-07 | Rank relative deterioration | Exit | +2% | +1% | Small | PROPOSED |
| P-08 | Regime-dependent deploy% | Portfolio | 0% | +2% | Small | PROPOSED |
| P-09 | RSI filter reversal_v1 | Strategy | +4% | +1% | Small | PROPOSED |
| P-10 | Multi-timeframe momentum | Strategy | +3% | +2% | Medium | PROPOSED |
| P-11 | low_vol_v1 in BEAR_HIGH_VOL | Portfolio | +2% | +1% | Medium | PROPOSED |
| P-12 | BULL_HIGH_VOL posture upgrade | Portfolio | 0% | +2% | Small | PROPOSED |
| P-13 | Segment RS benchmark (synthetic equal-weight universe) | Strategy | +2% | +1% | Medium | IMPLEMENTED (synthetic; index ingest still optional) |
| P-14 | Market breadth regime signal | Regime | 0% | +3% (drawdown) | Medium | IMPLEMENTED |
| **P-15** | **Min 5-day hold before analytical exits** | **Exit** | **+10–15%** | **+8–12%** | **Small** | **PROPOSED** |
| **P-16** | **Cooldown after EXIT_ALPHA_DECAY** | **Engine** | **+3%** | **+2%** | **Small** | **PROPOSED** |
| **P-17** | **Progressive stop floor after min hold** | **Exit** | **+2%** | **+2%** | **Small** | **PROPOSED** |
| **P-18** | **Horizon-matched RCEE edge gate (reversal_v1 unblock)** | **RCEE** | **+4–6%** | **+3–5%** | **Small (opt 2) / Medium (opt 1)** | **IMPLEMENTED** (expectancy route) |
| **P-19** | **EXIT_LIQUIDITY units bug (multibagger tail protection)** | **Exit** | **0% (tail)** | **+3–6% (tail)** | **Small** | **IMPLEMENTED** |
| **P-20** | **EXIT_REGIME selective (stop dumping trending winners)** | **Exit** | **+2%** | **+3–5%** | **Small** | **IMPLEMENTED** |
| **P-21** | **Trade Decision Layer (rank relative, gate absolute, order by EV)** | **Trade decision (new seam)** | **+8–12%** | **+5–10% (drawdown)** | **Medium** | **IMPLEMENTED** (core: eligibility + EV prioritization; breadth/segment pending) |

*All impact estimates are qualitative. Actual impact should be validated via full replay comparison.*

**P-21 is an architectural container, not a point fix.** P-05 (volume), P-13 (segment RS benchmark) and P-14 (universe breadth) are re-cast as *components* of the Trade Eligibility Gate rather than standalone proposals. The headline principle — **rank relative, gate absolute** — separates the strategy ranking (relative, RCEE-measurable, untouched) from the trade decision (absolute market/segment/stock health). It is the entry-side counterpart to the exit-side findings P-15/P-18/P-19/P-20.

**Exit forward-return study (Jan 2021–Jan 2024, breakout_v1, forward-15d-close vs +2.43% market baseline):** Most exits are correctly tuned — EXIT_STOP_LOSS (−2.56% excess, good), EXIT_RANK_DROP (−0.19%, ≈market). Two are mistuned: **EXIT_REGIME +5.27% excess** (broad — blanket liquidation, P-20) and **EXIT_LIQUIDITY tail** (median −2.09% but max +108%, units bug, P-19). EXIT_ALPHA_DECAY mildly eager (+0.87%). Earlier peak-over-30d framing overstated the effect; close-based vs-baseline is the unbiased measure.

**Evidence base for P-15/P-16/P-17:** Derived from systematic analysis of 75 losing paper trades (Jan–Sep 2021 replay). P-15 is the highest single-impact finding in this ADR — 48% of all losing positions would have recovered +14.7% on average had a 5-day minimum hold been enforced. P-16 eliminates the churn pattern (same stock traded 4–5× at small losses each time). P-17 closes the gap between the minimum hold ending and the trailing stop activating.

---

## Decision

All proposals are **PROPOSED**. No implementation until the current clean-slate replay completes and establishes a baseline CAGR. After baseline is known, implement in priority order (P-01 through P-06 first as a batch), run a second replay, and compare.

Proposals should be implemented as a new strategy version (e.g., `momentum_v2`, `breakout_v2`) rather than modifying existing v1 strategies in-place, to preserve the ability to compare replay results cleanly.

---

## Consequences

- Each implemented proposal requires a full clean-slate replay to validate
- P-01 (consensus) and P-04 (provisional RCEE) together may be the largest single unlock — first 5 months going from 0 BUYs to active trading
- P-02 + P-03 together form a complete profit protection framework
- P-10 and P-13 require strategy version bumps and longer warm-up periods
- P-11 requires validation data for low_vol_v1 in BEAR_HIGH_VOL — may need 2+ years of backtest data before RCEE can confirm EDGE_PRESENT
- P-14 (market breadth) reduces regime detection lag from 3–8 weeks to 1–3 weeks; paired with P-06 (circuit breaker) these form the complete drawdown defence layer — breadth catches market deterioration early, circuit breaker catches portfolio-specific damage when breadth misses
- P-15 + P-16 + P-17 form the **exit quality trilogy** and should be implemented together: P-15 prevents premature exits, P-16 prevents churn re-entries, P-17 tightens the stop progressively once the noise window has passed. These three together address the single largest source of losses observed in paper trading — crystallising small losses in stocks that go on to recover significantly
- P-21 is the **architectural keystone** for regime correctness: it establishes that ranking (relative, per-strategy) and the trade decision (absolute, market-aware) are different altitudes, and gives the absolute checks a single home. P-05/P-13/P-14 fold into it as components. Implement its per-stock trend gate first (small, fast to validate), then segment RS, then breadth. Once P-21 exists, the 2024-H1-class failure (buying rank-#1 names into a falling segment) is structurally prevented, not patched
- P-18 is an **availability defect, not an enhancement**: a correctly-routed strategy (`reversal_v1` in BEAR_LOW_VOL) never trades because the RCEE edge gate measures its short-horizon signal at a 20-day horizon. Until fixed, every BEAR_LOW_VOL period runs the portfolio idle in cash. It pairs with the regime-routing work (paper_pilot_ops `_REGIME_STRATEGY`) — routing is necessary but insufficient while the edge gate vetoes the routed strategy. Highest priority because it is the leading suspect for the gap vs the earlier 19→24% backtest
- P-19 is a **correctness defect, not an enhancement**: a units error (₹ ÷ shares) makes the liquidity exit fire harder as a stock's price rises, so the strategy force-sells its own multibaggers — ASAL.NS (+330%) booked as 16× +4.9% round-trips. It is the exit-side twin of P-18 (P-18 stops a strategy from ever buying; P-19 stops breakout from ever holding a runner). P-19 also exposes a gap in the P-15 exit-quality trilogy: P-15 was scoped to *analytical* exits and does not cover the hard exits (liquidity, regime), which the forward-return study shows are the largest sources of cut-short winners (post-exit peak +12.6% liquidity, +16.2% regime). Consider extending the P-15 minimum hold to hard exits as well, or gating them on still-ranked status

---

## References

- ADR-032: Regime Conditional Edge Engine (RCEE)
- ADR-033: Advisory Stop Thresholds
- ADR-035: Regime Dynamic Exits and Concentration
- ADR-036: Regime-Aware RCEE Sample Floor
- Jegadeesh & Titman (1993): Returns to Buying Winners and Selling Losers
- Asness (1994): Variables that Explain Stock Returns
