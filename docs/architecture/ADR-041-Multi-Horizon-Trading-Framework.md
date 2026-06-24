# ADR-041: Multi-Horizon Trading Framework (MHTF)

**Status:** PROPOSED  
**Date:** 2026-06-22  
**Author:** System design — post ADR-040 360° signal completeness review  
**Depends on:** ADR-032 (RCEE), ADR-037 (Enhancements), ADR-039 (FIL), ADR-040 (SICF)

---

## Problem Statement

The current system operates as a **single-horizon system**: all four strategies (momentum_v1, breakout_v1, reversal_v1, low_vol_v1) use daily bars, identical stop widths, and the same exit logic. Every position implicitly targets a hold of 3–25 days.

This creates a structural gap:
- **Swing (15–30d):** System already attempts this but lacks delivery % and FIL confirmation — noise entries dilute returns
- **Short term (1–3m):** Estimate revision cycles and earnings beats drive these moves — system has no visibility
- **Mid term (3–9m):** Sector rotation + institutional multi-quarter accumulation — system exits too early
- **Long term (1–1.5yr):** Business cycle + fundamentals dominate — pure price stops destroy these positions

A resilient system should allocate capital across all four horizons simultaneously, each running its own entry logic, exit logic, stop width, and conviction requirements. When market conditions favour one horizon, that book runs fuller. When conditions turn uncertain, longer-horizon books hold while shorter-horizon books pause.

---

## The Four Horizons

```
SWING       │ 15–30 days   │ Technical + FIL + Delivery
SHORT TERM  │ 1–3 months   │ Technical + Estimate Revisions + Institutional
MID TERM    │ 3–9 months   │ Sector Rotation + Multi-quarter Institutional + Quality
LONG TERM   │ 1–1.5 years  │ Fundamentals + Macro Cycle + Promoter Accumulation
```

Each horizon is a separate **trading book** with independent:
- Capital allocation
- Position slot count
- Stop width and exit logic
- Signal requirements
- RCEE calibration window
- Strategy variants

---

## Horizon 1: SWING (15–30 Days)

### What Drives These Moves
Short-term mean reversion and momentum continuation. A stock oversold on no news bounces. A breakout on volume sustains for 2–3 weeks. A result beat rallies for 15–20 trading days. These are the highest-frequency, highest-precision trades.

### Signal Requirements

| Signal | Requirement | Gate Type |
|---|---|---|
| Technical rank | Top 20 in any strategy | Entry gate |
| RCEE | EDGE_PRESENT (ic_lower_95 ≥ 0.010) | Entry gate |
| Delivery % | ≥ 45% on entry day | Conviction filter |
| FIL catalyst | Optional — boosts priority if present | Conviction boost |
| Regime | BULL_LOW_VOL or BEAR_LOW_VOL only | Regime gate |
| Quality gate | F-Score ≥ 4, no pledge block | Safety filter |

### Stop and Exit Logic

```
Stop loss:          5–7% from entry (strategy-dependent)
Trailing stop:      Activates after +8% unrealised gain
Target:             No fixed target — trail until stop
Time stop:          Exit at day 25 if < +3% gain (alpha decay)
Exit on catalyst:   If FIL fires NEGATIVE catalyst → exit immediately
```

### RCEE Calibration
- IC measurement at **7–9d and 14–16d** windows (already implemented)
- Minimum samples: **45** (existing threshold)

### Portfolio Parameters
- **Slots:** 6–8 open positions (current BULL_LOW_VOL regime allocation)
- **Capital per position:** 8–12% of book
- **Book allocation:** 30% of total portfolio capital

### Currently closest to this horizon. Missing: delivery % gate, better FIL integration.

---

## Horizon 2: SHORT TERM (1–3 Months)

### What Drives These Moves
Earnings upgrade cycles. Sector rotation. A stock where 3 consecutive analyst upgrades happen over 6 weeks sees sustained buying from institutional mandates. The price doesn't move all at once — it grinds up over 6–10 weeks as each fund manager adds exposure.

### Signal Requirements

| Signal | Requirement | Gate Type |
|---|---|---|
| Technical rank | Top 30 in momentum_v1 or breakout_v1 | Entry gate |
| RCEE | EDGE_PRESENT at 28–32d IC window | Entry gate |
| Estimate revisions | UPGRADE or STRONG_UPGRADE (P-C) | Conviction gate |
| Institutional flow | FII or DII increasing QoQ | Confirmation |
| FIL catalyst | Earnings beat OR order win in last 30d | Conviction boost |
| Delivery % | ≥ 40% (3-week moving average) | Quality filter |
| Quality gate | F-Score ≥ 5, Z-Score > 2.0 | Safety filter |
| Regime | Not BEAR_HIGH_VOL | Regime gate |

### Stop and Exit Logic

```
Stop loss:          8–12% from entry (wider — needs room to breathe)
Trailing stop:      Activates after +15% unrealised gain
Fundamental exit:   If estimate revisions turn DOWNGRADE → exit within 5 days
Institutional exit: If FII and DII both reduce QoQ → reduce position 50%
Time stop:          Exit at day 75 if < +5% gain
Target:             No fixed target — hold the upgrade cycle
```

### RCEE Calibration
- IC measurement at **28–32d and 60–65d** windows
- Minimum samples: **60** (stricter — longer window needs more data)
- New IC window needed: **60–65d** (not currently implemented)

### New Exit Signals (Beyond Price Action)
This horizon introduces **fundamental exits** — positions are not just closed on stop loss but when the investment thesis deteriorates:
- Estimate revision turns DOWNGRADE → exit signal
- FIL fires EARNINGS_MISS → exit signal
- Institutional holdings fall two consecutive quarters → reduce to half, then exit

### Portfolio Parameters
- **Slots:** 5–7 positions (smaller count — larger per-position allocation)
- **Capital per position:** 12–18% of book
- **Book allocation:** 35% of total portfolio capital

---

## Horizon 3: MID TERM (3–9 Months)

### What Drives These Moves
Sector rotation driven by macro catalysts. When the government announces a ₹10 lakh crore infrastructure push, infrastructure stocks re-rate over 6–9 months — not in one day. When RBI begins a rate-cut cycle, banking/NBFC stocks see sustained accumulation across multiple quarterly results. These are **multi-quarter stories** best caught by the convergence of:
1. A sector tailwind (macro or policy)
2. Institutional accumulation building over 2+ quarters
3. Earnings upgrade cycle beginning
4. Quality fundamentals (company can actually execute the opportunity)

### Signal Requirements

| Signal | Requirement | Gate Type |
|---|---|---|
| Technical rank | Top 20 in weekly momentum | Entry gate |
| Sector tailwind | Active sector catalyst (ADR-039) | Required |
| Institutional flow | FII + DII both increasing for 2+ quarters | Required |
| Estimate revisions | UPGRADE or STRONG_UPGRADE for 2+ months | Required |
| Macro alignment | Macro overlay positive for sector | Confirmation |
| Promoter activity | Neutral or positive (no pledge concerns) | Confirmation |
| Quality gate | F-Score ≥ 6, Z-Score > 2.5, Beneish < -1.78 | Stricter safety |
| RCEE | EDGE_PRESENT at 88–92d window | Entry gate |

### Weekly Momentum Signal (New — Not Yet Built)
Mid-term entries use **weekly bars** (5-day OHLCV aggregated from daily). Signals are generated once per week, not daily. A stock ranking in the top 20 weekly momentum for 3 consecutive weeks = high-confidence mid-term entry.

```python
# New strategy variant needed
RANKING_STRATEGY_MOMENTUM_WEEKLY_V1 = "momentum_weekly_v1"
# Uses 26-week lookback (vs 12-day current)
# Minimum 52 weeks of data required
```

### Stop and Exit Logic

```
Stop loss:          15–18% from entry (sector rotation needs room)
NO trailing stop:   Position held as long as thesis intact
Fundamental exit:   Estimate revisions turn DOWNGRADE for 2+ months → exit
Institutional exit: FII AND DII both exit over 2 consecutive quarters → exit
Sector exit:        Sector tailwind expires AND no replacement catalyst → exit
Macro exit:         Macro overlay turns negative for sector → reduce 50%
Time stop:          Day 270 maximum hold (9 months)
```

### RCEE Calibration
- IC measurement at **88–92d window** (already implemented in validation)
- Add new window: **180–185d** for true 6-month IC
- Minimum samples: **90** (stricter — 6 months of data needed)

### Portfolio Parameters
- **Slots:** 4–6 positions (concentrated)
- **Capital per position:** 15–20% of book
- **Book allocation:** 25% of total portfolio capital
- **Rebalance frequency:** Weekly (not daily)

---

## Horizon 4: LONG TERM (1–1.5 Years)

### What Drives These Moves
Compounding business quality. When a company has:
- A structural tailwind (PLI, China+1, Indian defence indigenisation)
- Consistent earnings growth (15–25% CAGR for 3+ years)
- Promoters continuously buying or holding (not pledging)
- Institutional ownership growing every quarter
- A balance sheet getting stronger each year

...the stock doubles or triples over 18–36 months regardless of short-term market noise.

Long-term positions are the **highest conviction, lowest frequency** trades. One good long-term position can contribute more CAGR than 20 swing trades.

### Signal Requirements

| Signal | Requirement | Gate Type |
|---|---|---|
| Fundamental quality | F-Score ≥ 7, Z-Score > 3.0 | Hard gate |
| Earnings growth | EPS growing ≥ 15% for 3+ consecutive years | Hard gate |
| Promoter activity | Promoter stake stable or increasing for 4+ quarters | Required |
| Institutional trend | FII + DII combined increasing for 3+ quarters | Required |
| Macro / sector | Structural multi-year tailwind identified | Required |
| Debt trajectory | Debt/equity declining or FCF positive | Required |
| Technical | Stock above weekly SMA(40) and monthly SMA(10) | Entry timing gate |
| RCEE | Optional — at 365d IC (not enough samples in replay yet) | Enhancement |

### Entry Timing (Technical Overlay)
Long-term entry does NOT chase price momentum. The fundamental thesis is validated first, then technical is used only to time the **entry point** within the trend:

```
Ideal entry: Stock pulls back 10–15% from recent high within an established uptrend
             — not buying at all-time highs
Entry gate:  Stock above 200-day SMA (bull trend confirmed)
Avoid entry: Stock within 3 days of earnings announcement (wait for clarity)
```

### Stop and Exit Logic

```
Stop loss:          NO PRICE STOP for long-term positions
                    (price stop guarantees you get shaken out by noise)
Fundamental exit:   Earnings growth < 10% for 2 consecutive quarters → exit
Institutional exit: Promoter reduces stake significantly (> 2%) → exit
                   FII + DII both exit for 3 consecutive quarters → exit
Thesis exit:        Structural tailwind collapses (policy reversal, sector disruption) → exit
Target:             Exit at 18 months OR when thesis fully realised (whichever first)
Rebalance:          Review thesis every quarter after each results season
```

**No trailing stop** because a +40% drawdown from the high is normal for a stock that ultimately delivers +200%. Price-based stops destroy long-term positions.

### Portfolio Parameters
- **Slots:** 3–5 positions (highly concentrated, highest conviction)
- **Capital per position:** 20–25% of book
- **Book allocation:** 10% of total portfolio capital (starts small, grows as thesis validates)
- **Rebalance frequency:** Quarterly

---

## Capital Allocation Across Horizons

```
Total Portfolio Capital: ₹1,00,00,000 (example)

┌──────────────┬──────────────┬────────────┬────────────┬──────────────┐
│ Horizon      │ Allocation   │ Amount     │ Max Slots  │ Per Position │
├──────────────┼──────────────┼────────────┼────────────┼──────────────┤
│ SWING        │     30%      │ ₹30,00,000 │   6–8      │ ₹3.75–5L    │
│ SHORT TERM   │     35%      │ ₹35,00,000 │   5–7      │ ₹5–7L       │
│ MID TERM     │     25%      │ ₹25,00,000 │   4–6      │ ₹4–6.25L    │
│ LONG TERM    │     10%      │ ₹10,00,000 │   3–5      │ ₹2–3.33L    │
└──────────────┴──────────────┴────────────┴────────────┴──────────────┘
```

**Dynamic reallocation:** Allocation shifts with regime:
- BULL_LOW_VOL: Shift 5% from Long Term to Short Term (momentum environment)
- BEAR_HIGH_VOL: Shift 10% from Swing to Long Term (reduce frequency, increase quality)
- Extreme VIX (> 25): Park 20% in cash across all books; resume on VIX < 20

---

## Signal Stack by Horizon

| Signal | SWING | SHORT | MID | LONG |
|---|---|---|---|---|
| Technical rank (daily) | ✅ Core | ✅ Core | — | ⏱ Timing only |
| Technical rank (weekly) | — | — | ✅ Core | ✅ Core |
| RCEE (7–16d IC) | ✅ Required | — | — | — |
| RCEE (28–65d IC) | — | ✅ Required | — | — |
| RCEE (88–185d IC) | — | — | ✅ Required | — |
| Delivery % | ✅ Gate | ✅ Filter | — | — |
| FIL company catalyst | ✅ Boost | ✅ Gate | ✅ Context | — |
| Sector tailwind | ✅ Boost | ✅ Boost | ✅ Required | ✅ Required |
| Estimate revisions | — | ✅ Gate | ✅ Required | ✅ Confirmation |
| FII/DII flow (quarterly) | — | ✅ Confirmation | ✅ Required | ✅ Required |
| Promoter activity | ✅ Safety | ✅ Safety | ✅ Confirmation | ✅ Required |
| F-Score | ≥ 4 | ≥ 5 | ≥ 6 | ≥ 7 |
| Z-Score | > 1.8 | > 2.0 | > 2.5 | > 3.0 |
| Macro overlay | — | ✅ Context | ✅ Required | ✅ Required |
| Options (PCR, OI) | ✅ F&O stocks | — | — | — |
| Earnings growth trend | — | — | ✅ Confirmation | ✅ Required |

---

## Exit Logic by Horizon

```
                    SWING       SHORT       MID         LONG
                    ─────────   ─────────   ─────────   ─────────
Price stop          5–7%        8–12%       15–18%      NONE
Trailing stop       +8% gain    +15% gain   NONE        NONE
Time stop           Day 25      Day 75      Day 270     Day 540
Alpha decay exit    ✅           ✅           —           —
Estimate downgrade  —           ✅           ✅           ✅
Institutional exit  —           Partial     Full        Full
Sector exit         —           —           ✅           ✅
Thesis exit         —           —           ✅           ✅
Negative catalyst   Immediate   5-day exit  Review      Review
```

The critical insight: **longer horizons need more exit reasons beyond price**. A long-term position exiting on a 15% price stop is almost always wrong — it's the fundamental thesis that should determine exit, not day-to-day price noise.

---

## RCEE Adaptation Per Horizon

RCEE currently measures IC at fixed forward windows (7–9d, 14–16d, 28–32d, 88–92d). Multi-horizon requires expanding the IC measurement framework:

```
Current windows (days):
  7–9   → SWING confirmation
  14–16 → SWING primary
  28–32 → SHORT TERM confirmation
  88–92 → MID TERM confirmation

New windows needed:
  60–65   → SHORT TERM primary
  180–185 → MID TERM primary
  365–370 → LONG TERM (needs 18-month history — not available in current replay)
```

Per-horizon minimum sample floors:
```
SWING:       n ≥ 45 signals at 14d window   (current)
SHORT TERM:  n ≥ 60 signals at 60d window   (new)
MID TERM:    n ≥ 90 signals at 180d window  (new — 2023 onwards in replay)
LONG TERM:   n ≥ 30 signals at 365d window  (sparse — use qualitative screen instead)
```

---

## Database Schema Additions

### Book-level tracking

```sql
CREATE TABLE portfolio_books (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_name       VARCHAR(20) NOT NULL UNIQUE,  -- SWING, SHORT_TERM, MID_TERM, LONG_TERM
    capital_pct     NUMERIC(5,2) NOT NULL,        -- % of total portfolio
    max_slots       INT NOT NULL,
    stop_pct        NUMERIC(5,2),
    trailing_stop_pct NUMERIC(5,2),
    time_stop_days  INT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Positions tagged with their book
ALTER TABLE portfolio_positions
    ADD COLUMN book_name VARCHAR(20) REFERENCES portfolio_books(book_name),
    ADD COLUMN hold_thesis JSONB,        -- structured reason for holding (for mid/long)
    ADD COLUMN thesis_last_reviewed DATE,
    ADD COLUMN exit_thesis TEXT;         -- narrative reason for exit
```

### Weekly signal store

```sql
CREATE TABLE ranking_runs_weekly (
    -- Same as ranking_runs but computed from weekly aggregated bars
    -- Separate table to avoid polluting daily ranking history
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name   VARCHAR(60) NOT NULL,
    strategy_version VARCHAR(20) NOT NULL,
    week_ending     DATE NOT NULL,        -- Friday of the ranking week
    universe_code   VARCHAR(30) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (strategy_name, week_ending, universe_code)
);
```

---

## Conviction Score by Horizon

The 0–90 scoring model (ADR-040) maps to conviction differently per book:

```
SWING book:
  Score ≥ 75 → EXCEPTIONAL (max slots, full position size)
  Score 60–74 → HIGH (standard position)
  Score 45–59 → MEDIUM (half position)
  Score < 45  → WATCH (no entry)

SHORT TERM book:
  Score ≥ 70 → HIGH or above required for entry
  Estimate revision STRONG_UPGRADE mandatory for EXCEPTIONAL

MID TERM book:
  Score ≥ 65 required
  Sector tailwind + institutional both required
  Weekly technical rank required

LONG TERM book:
  Score from fundamentals only (no technical rank score)
  Custom long-term quality score (F-Score + earnings trajectory + institutional)
  Minimum threshold: quality_score ≥ 80/100
```

---

## How the Same Stock Can Appear in Multiple Books

A stock like RVNL can simultaneously be:
- **SWING book:** Recent technical breakout with delivery confirmation
- **MID TERM book:** Railway sector tailwind + institutional accumulation
- **LONG TERM book:** Structural defence/infra play with 5-year earnings visibility

This is not duplication — it's **layered conviction**. The swing trade captures the next 3 weeks. The mid-term position captures the next 6 months. The long-term position captures the full re-rating.

**Position sizing across books is additive but capped:**
```
Max combined exposure to any single stock: 15% of total portfolio
  = swing portion + short-term portion + mid-term portion + long-term portion
```

---

## Regime × Horizon Matrix

Not all horizons are equally good in all regimes:

```
Regime            │ SWING │ SHORT │ MID  │ LONG
──────────────────┼───────┼───────┼──────┼──────
BULL_LOW_VOL      │  ✅✅  │  ✅✅  │  ✅  │  ✅
BULL_HIGH_VOL     │  ⚠️   │  ✅   │  ✅  │  ✅✅
BEAR_LOW_VOL      │  ✅   │  ⚠️   │  ⚠️  │  ✅
BEAR_HIGH_VOL     │  ❌   │  ⚠️   │  ❌  │  ✅✅

✅✅ = ideal conditions
✅  = acceptable
⚠️  = reduce allocation 50%
❌  = suspend new entries
```

**Key insight:** Long-term positions are most valuable in BEAR regimes — they should not be exited on market fear if the thesis is intact. This is where most investors make their biggest mistake (selling their best long-term positions in a panic). The framework explicitly protects long-term positions from regime-driven exits.

---

## What CAGR Can Each Horizon Contribute?

Rough estimates assuming signal stack fully built:

| Horizon | Trade Frequency | Average Hold | Win Rate Target | Average Win | CAGR Contribution |
|---|---|---|---|---|---|
| SWING | 3–5/week | 18 days | 50–55% | +6–8% | 15–20% |
| SHORT TERM | 1–2/week | 55 days | 55–60% | +12–18% | 20–28% |
| MID TERM | 2–4/month | 5 months | 60–65% | +25–40% | 15–22% |
| LONG TERM | 1–2/quarter | 14 months | 65–70% | +60–120% | 12–18% |
| **Combined** | | | | | **45–70% CAGR** |

*Note: These are directional estimates based on institutional quant research benchmarks for Indian markets. Actual CAGR depends on execution quality, market conditions, and signal accuracy. Requires historical backtesting to validate.*

---

## Implementation Roadmap

### Phase 1 — Swing book hardening (Current focus)
Current system IS the swing book. Complete the replay baseline first.
- [ ] Delivery % gate (ADR-040 P-A)
- [ ] Quality gate enforcement (F-Score ≥ 4, pledge block)
- [ ] FIL company catalyst integration (ADR-039 Phase 1-2)
- [ ] Target: ≥ 50% win rate, 15–20% CAGR

### Phase 2 — Short term book
- [ ] 60–65d RCEE IC window
- [ ] Estimate revision data integration (ADR-040 P-C)
- [ ] FII/DII quarterly shareholding ingestion (ADR-040 P-B)
- [ ] Fundamental exit logic (estimate downgrade → exit)
- [ ] Separate `portfolio_books` table and book-tagged positions
- [ ] Wider stop parameters for short-term entries

### Phase 3 — Mid term book
- [ ] Weekly bar aggregation (OHLCV weekly from daily)
- [ ] Weekly ranking strategy (momentum_weekly_v1)
- [ ] 180–185d RCEE IC window
- [ ] Sector rotation detection from ADR-039
- [ ] Multi-quarter institutional accumulation tracker
- [ ] Thesis-based exit framework (not price-based)
- [ ] Quarterly review workflow

### Phase 4 — Long term book
- [ ] Long-term quality score model (F-Score + earnings growth + institutional trend)
- [ ] Promoter pattern detection (creeping acquisition)
- [ ] Business cycle / structural tailwind framework
- [ ] No-price-stop exit logic (thesis only)
- [ ] 365d IC validation (requires 2+ years of live data)
- [ ] Quarterly results-based thesis refresh

---

## Decision

**Status: PROPOSED — Not yet implemented.**

Implementation sequence strictly follows:
1. Replay baseline completion (current)
2. ADR-037 P-01 to P-06 (ranking improvements)
3. ADR-039 FIL Phase 1-2 (news intelligence)
4. ADR-040 Batch 1 (delivery %, quality gates)
5. **MHTF Phase 1** (swing book hardening — these are just parameter changes)
6. **MHTF Phase 2** (short-term book — requires estimate revisions data)
7. **MHTF Phase 3–4** (mid/long — 6–12 months after Phase 2 live)

The long-term book in particular requires **live trading data** to validate. It cannot be backtested on the 2021–2026 replay alone because the RCEE needs 365-day IC measurement, which requires at least 18 months of live signals to compute reliably.

---

## Consequences

- Portfolio becomes a **4-book system** — different entry, hold, and exit logic per book
- Position table gains `book_name` and `hold_thesis` columns
- Weekly ranking pipeline needs to be built (new job, separate from daily)
- RCEE gains two new IC measurement windows (60–65d, 180–185d)
- Exit monitor gains fundamental exit signals (not just price signals)
- Capital allocation becomes dynamic (regime-adjusted per book)
- Reporting and NAV tracking need book-level breakdowns
- The long-term book is the most patient and the most profitable — but also the hardest to systematize. Qualitative judgment still required for thesis validation in Phase 4.

---

## References

- ADR-032: Regime Conditional Edge Engine
- ADR-037: Strategy Enhancement Proposals
- ADR-039: Fundamental Intelligence Layer
- ADR-040: Stock Intelligence Completeness Framework
- Jegadeesh & Titman (1993): Returns to Buying Winners and Selling Losers — momentum horizons
- Asness, Moskowitz & Pedersen (2013): Value and Momentum Everywhere — multi-horizon factor persistence
- Chan, Jegadeesh & Lakonishok (1996): Momentum Strategies — estimate revisions in short-term
- O'Neil, William (1988): How to Make Money in Stocks — CANSLIM method (long-term fundamentals + technical timing)
