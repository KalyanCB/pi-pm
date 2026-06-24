# ADR-040: Stock Intelligence Completeness Framework (SICF)

**Status:** PROPOSED  
**Date:** 2026-06-22  
**Author:** System design — post ADR-039 Fundamental Intelligence Layer  
**Depends on:** ADR-032 (RCEE), ADR-037 (Enhancements), ADR-039 (FIL)

---

## Problem Statement

ADR-039 added news and sector intelligence. But news tells you *what happened* — it does not tell you *who is acting on it* or *whether the fundamentals support the move*. Two identical technical breakouts with identical news catalysts can have very different outcomes depending on:

1. Whether institutions are genuinely accumulating (delivery %) or speculators are driving volume
2. Whether smart money (FII, DII, MF) has been building a position for weeks
3. Whether analyst earnings estimates are rising (earnings upgrade cycle) or falling

These three signals — **Delivery Quality**, **Institutional Flow**, and **Estimate Revision Momentum** — are the highest-ROI additions to the existing stack. They answer: *Who else agrees? And is the fundamental story improving or deteriorating?*

This ADR documents the complete 360° signal framework and defines the three priority additions.

---

## The Complete 360° Signal Stack

```
┌──────────────────────────────────────────────────────────────────┐
│  TIER 1 — FOUNDATION (price truth)               [BUILT]        │
│                                                                  │
│  • Technical ranking (momentum, breakout, reversal, low_vol)    │
│  • Regime classifier (bull/bear × vol, death cross, drawdown)   │
│  • RCEE statistical edge (IC, hit rate, sample floor)           │
│  • Re-entry cooldown, EOD stop confirmation                     │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  TIER 2 — CONFIRMATION (why the price is moving) [ADR-039]      │
│                                                                  │
│  • FIL company catalyst (earnings, orders, approvals)           │
│  • Sector intelligence (tailwind/headwind propagation)          │
│  • Negative catalyst suppression                                │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  TIER 3 — CONVICTION AMPLIFIERS (who else agrees) [THIS ADR]    │
│                                                                  │
│  • Delivery % — institutional vs speculative volume (P-A)       │
│  • Institutional flow — FII/DII/MF accumulation (P-B)          │
│  • Earnings estimate revisions — upgrade cycle (P-C)            │
│  • Promoter activity — insider confidence                        │
│  • Options intelligence — PCR, OI, IV (F&O stocks)             │
│  • Corporate event calendar — timing awareness                   │
│  • Peer relative value — sector discount/premium                │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  TIER 4 — SAFETY FILTERS (what to never buy)     [THIS ADR]    │
│                                                                  │
│  • Piotroski F-Score < 3 → exclude                              │
│  • Altman Z-Score < 1.8 → distress zone → exclude              │
│  • Beneish M-Score > -1.78 → manipulation risk → exclude       │
│  • Promoter pledge > 50% → exclude                              │
│  • Auditor change in last 12 months → exclude                   │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  TIER 5 — MACRO BACKDROP (direction of wind)     [THIS ADR]    │
│                                                                  │
│  • RBI rate cycle → sector bias                                 │
│  • INR direction → IT/export vs import-dependent               │
│  • Crude oil price → energy, paint, tyre, airlines             │
│  • India VIX level → aggression vs caution overlay             │
│  • Advance/Decline breadth (ADR-037 P-14)                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## Priority Addition P-A: Delivery % (Volume Quality)

### What It Is

NSE publishes **delivery-based volume** in the daily bhavcopy — the percentage of total traded volume where shares actually changed hands (vs intraday squaring). High delivery % means investors are taking home shares, not just day-trading.

```
delivery_pct = delivery_quantity / total_traded_quantity × 100
```

### Why It Matters

| Scenario | Delivery % | Interpretation |
|---|---|---|
| Price breakout + delivery > 60% | High | Institutions accumulating — continuation likely |
| Price breakout + delivery < 25% | Low | Speculative froth — high reversal risk |
| Price flat + delivery rising steadily | Rising | Quiet accumulation before a move |
| Price falling + delivery > 50% | High | Forced selling by long-term holders — capitulation |

A breakout with 60%+ delivery is 2–3× more likely to continue for 5+ days than a breakout with <25% delivery. This is the single cheapest signal to add — data is free, published daily by NSE.

### Implementation

**Data source:** NSE Bhavcopy CM (Capital Market) — free, downloaded daily. Fields: `SYMBOL, SERIES, TOTTRDQTY, DELIV_QTY, DELIV_PER`.

**New table:**
```sql
CREATE TABLE stock_delivery_metrics (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id    UUID NOT NULL REFERENCES stocks(id),
    date        DATE NOT NULL,
    delivery_pct        NUMERIC(5,2),   -- 0-100
    delivery_qty        BIGINT,
    total_traded_qty    BIGINT,
    delivery_5d_avg     NUMERIC(5,2),   -- rolling 5-day average
    delivery_20d_avg    NUMERIC(5,2),   -- rolling 20-day average
    UNIQUE (stock_id, date)
);
```

**Integration into ranking (breakout_v1):**
Add delivery quality as a factor with weight 0.10, reducing another factor accordingly. Stocks with 5-day avg delivery > 55% rank higher. Alternatively, use as a **conviction gate** — delivery < 25% on entry day downgrades conviction from HIGH → MEDIUM.

**Integration into recommendation engine:**
```python
# Before finalising BUY:
if delivery_pct < 25.0 and action == RecommendationAction.BUY:
    reason_codes.append("LOW_DELIVERY_VOLUME")
    conviction = _downgrade_conviction(conviction)  # HIGH → MEDIUM
```

**Replay availability:** NSE provides historical bhavcopy going back to 2000. Can be ingested retroactively for the full 2021–2026 replay window.

---

## Priority Addition P-B: Institutional Flow (FII / DII / MF)

### What It Is

Three layers of smart money, each with different information horizons:

| Institution | Information Edge | Typical Horizon | Signal Strength |
|---|---|---|---|
| **FII (Foreign Institutional)** | Global macro, sector rotation, EM allocation | Weeks to months | High — large capital |
| **DII (Domestic Institutional)** | Domestic macro, mutual fund mandates | Months | High — patient capital |
| **MF (Mutual Fund via SEBI)** | Retail aggregated + mandate-driven | Months to years | Medium |
| **Promoter** | Own company insight | Months to years | Highest — insider |

**Signal combinations:**

| FII | DII | Promoter | Signal |
|---|---|---|---|
| Buying | Buying | Buying | VERY STRONG — all smart money aligned |
| Buying | Buying | Stable | STRONG — institutional consensus |
| Selling | Buying | Buying | MODERATE — domestic smart money vs foreign |
| Selling | Selling | Buying | WATCH — promoter alone, contrarian signal |
| Selling | Selling | Selling | VERY WEAK — avoid, potential structural decline |

### Data Sources

**Daily FII/DII data:** NSE publishes aggregate FII and DII buy/sell values daily (free). Does NOT give stock-level breakdown daily.

**Quarterly shareholding:** BSE publishes shareholding pattern for every listed company every quarter (31 Mar, 30 Jun, 30 Sep, 31 Dec). This gives per-stock FII %, DII %, Promoter %, Public % changes.

**Monthly MF disclosure:** SEBI mandates mutual funds to disclose portfolio holdings monthly. AMFI publishes this in XML format (free).

**SEBI bulk/block deals:** Real-time — any trade > ₹5 Cr in a single transaction must be disclosed. This is the most timely institutional signal.

### New Tables

```sql
-- Quarterly shareholding pattern per stock
CREATE TABLE shareholding_pattern (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id        UUID NOT NULL REFERENCES stocks(id),
    period_end      DATE NOT NULL,           -- 2024-03-31, 2024-06-30, etc.
    promoter_pct    NUMERIC(6,3),
    promoter_pledge_pct NUMERIC(6,3),        -- pledged as % of promoter holding
    fii_pct         NUMERIC(6,3),
    dii_pct         NUMERIC(6,3),
    mf_pct          NUMERIC(6,3),
    public_pct      NUMERIC(6,3),
    -- change vs previous quarter
    promoter_chg    NUMERIC(6,3),
    fii_chg         NUMERIC(6,3),
    dii_chg         NUMERIC(6,3),
    mf_chg          NUMERIC(6,3),
    source          VARCHAR(30),
    UNIQUE (stock_id, period_end)
);

-- Bulk / block deals (real-time institutional signals)
CREATE TABLE bulk_block_deals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id        UUID NOT NULL REFERENCES stocks(id),
    deal_date       DATE NOT NULL,
    deal_type       VARCHAR(10) NOT NULL,    -- BULK, BLOCK
    client_name     VARCHAR(200),
    side            VARCHAR(4) NOT NULL,     -- BUY, SELL
    quantity        BIGINT NOT NULL,
    price           NUMERIC(12,4) NOT NULL,
    value_cr        NUMERIC(12,2),           -- deal value in Crores
    source          VARCHAR(30) DEFAULT 'NSE',
    INDEX (stock_id, deal_date)
);
```

### Institutional Score

A composite score computed weekly from available data:

```python
def compute_institutional_score(stock_id, as_of_date) -> float:
    """
    Score 0-100. Higher = stronger institutional conviction.
    """
    score = 50.0  # neutral baseline

    # Promoter activity (highest weight — insider signal)
    if promoter_chg_qtr > 0.5:   score += 20
    elif promoter_chg_qtr < -1:  score -= 25
    if pledge_pct > 50:           score -= 30  # hard penalty

    # FII + DII combined (institutional consensus)
    if fii_chg > 0 and dii_chg > 0:  score += 15  # both buying
    elif fii_chg < 0 and dii_chg < 0: score -= 20  # both selling
    elif fii_chg > 0:                  score += 8
    elif dii_chg > 0:                  score += 5

    # Recent bulk/block deals (last 30 days)
    net_deal_value = sum(buys) - sum(sells)  # in Cr
    if net_deal_value > 50:    score += 10
    elif net_deal_value < -50: score -= 15

    return max(0, min(100, score))
```

**Integration:** Stocks with institutional score > 65 get conviction boost in the recommendation engine. Stocks with score < 30 (institutions exiting) are suppressed from BUY regardless of ranking.

---

## Priority Addition P-C: Earnings Estimate Revision Momentum

### What It Is

When multiple analysts simultaneously **raise** their EPS (Earnings Per Share) estimate for a company's upcoming quarter, it signals:
1. The company has given positive management commentary
2. Sector conditions are improving
3. Recent data points (channel checks, order books) suggest an earnings beat

**Estimate revision momentum** = the rate and direction of change in consensus EPS estimates over the past 60 days.

### Why This Is Powerful

Earnings estimate revisions are one of the most robust signals in academic quant research globally (Hawkins et al., 1984; Chan, Jegadeesh & Lakonishok, 1996). Key findings:
- Stocks with rising estimate revisions over 3+ months outperform by 4–8% over the next 6 months
- The effect persists for 6–12 months (analysts under-revise — market slowly catches up)
- Combining estimate revision + price momentum = stronger than either alone
- In Indian markets, this is less competed for than in US markets — the alpha is larger

### Signal Definition

```
revision_score = (current_consensus_eps - consensus_eps_60d_ago) / abs(consensus_eps_60d_ago)

Interpretation:
  > +10%  : Strong upgrade cycle — analysts materially raising estimates
  +3-10%  : Moderate upgrade — positive direction
  -3 to +3: Stable — no clear direction
  -3 to -10: Moderate downgrade
  < -10%  : Earnings deterioration — strong negative signal
```

**Revision breadth** (how many analysts are raising vs cutting):
```
breadth = (analysts_raising - analysts_cutting) / total_analysts
```
Breadth > 0.5 (majority raising) = strong confirmation.

### Data Sources

| Source | Coverage | Cost |
|---|---|---|
| Screener.in | ~500 stocks, quarterly estimates | Free (limited) / Paid |
| Tickertape | Analyst consensus, estimate changes | Freemium |
| Bloomberg / Refinitiv | Full universe, daily updates | Expensive |
| NSE/BSE filings | Actuals only (not forecasts) | Free |
| Broker research PDFs | Best coverage, unstructured | Requires parsing |

**Practical approach for Indian markets:** Start with Screener.in API for the NIFTY 500 subset (covers ~85% of our universe by market cap). Supplement with manual broker research for top 100 names.

### New Table

```sql
CREATE TABLE earnings_estimates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id            UUID NOT NULL REFERENCES stocks(id),
    as_of_date          DATE NOT NULL,
    fiscal_period       VARCHAR(10) NOT NULL,   -- "Q2FY26", "FY26"
    period_type         VARCHAR(10) NOT NULL,   -- QUARTERLY, ANNUAL
    consensus_eps       NUMERIC(12,4),
    consensus_revenue   NUMERIC(18,2),
    analyst_count       INT,
    analysts_raising    INT,
    analysts_cutting    INT,
    eps_60d_ago         NUMERIC(12,4),          -- snapshot from 60 days prior
    revision_pct        NUMERIC(8,4),           -- (current - 60d_ago) / |60d_ago|
    revision_breadth    NUMERIC(5,3),           -- (raising - cutting) / total
    revision_momentum   VARCHAR(20),            -- STRONG_UPGRADE, UPGRADE, STABLE, DOWNGRADE, STRONG_DOWNGRADE
    source              VARCHAR(30),
    UNIQUE (stock_id, as_of_date, fiscal_period)
);
```

### Integration with Recommendation Engine

```python
# In _evaluate() after conviction calculation:
revision = estimate_revisions.get(rr.stock_id)
if revision:
    if revision.revision_momentum == "STRONG_UPGRADE":
        conviction = _boost_conviction(conviction)
        reason_codes.append("ESTIMATE_UPGRADE_CYCLE")
    elif revision.revision_momentum in ("DOWNGRADE", "STRONG_DOWNGRADE"):
        if action == RecommendationAction.BUY:
            action = RecommendationAction.WATCH
            reason_codes.append("ESTIMATE_DOWNGRADE_CYCLE")
```

---

## Priority Addition P-D: Promoter Activity Deep Signal

### Beyond Shareholding %

Quarterly shareholding tells you what happened. Insider trading disclosures (Form-C, SEBI) tell you what's happening **now**:

- **Open market purchases** (promoter buying in the market at current prices) = strongest insider signal. They're paying the same price you are.
- **Creeping acquisition** (promoter steadily buying 0.5–1% per quarter for 3+ quarters) = sustained conviction, often precedes a rally or privatisation
- **Pledge creation** = promoter borrowing against shares → forced selling risk if stock falls
- **Pledge reduction** = promoter paying off debt → positive
- **ESOP grants to employees at low strike prices** = management bullish on future price

### Promoter Signal Score

| Activity | Signal Strength | Duration |
|---|---|---|
| Open market purchase > ₹10 Cr | VERY STRONG POSITIVE | 30–60 days |
| Creeping acquisition 3+ consecutive quarters | STRONG POSITIVE | 90 days |
| Buyback announced | STRONG POSITIVE | Until completion |
| Pledge reduction > 10% | MODERATE POSITIVE | 45 days |
| Pledge creation or increase | NEGATIVE | 90 days |
| Insider sale by promoter | MODERATE NEGATIVE | 30 days |
| Pledge > 50% of holding | HARD BLOCK — exclude from BUY | Until below 30% |

---

## Priority Addition P-E: Options Intelligence (F&O Stocks)

### Applicable Universe
~200 NIFTY stocks have active F&O (Futures & Options). For these, derivatives data adds a forward-looking dimension unavailable in price charts alone.

### Key Signals

**Put/Call Ratio (PCR) — Sentiment Gauge**
```
PCR = Total Put OI / Total Call OI

PCR < 0.7  : Overcrowded bullish — contrarian caution (too many bulls)
PCR 0.7–1.0: Balanced — neutral
PCR 1.0–1.3: Fear present — potential bounce territory
PCR > 1.3  : Extreme fear — high-probability reversal zone (for reversal_v1)
```

**Open Interest + Price Direction — Trend Confirmation**
```
Price ↑ + OI ↑ = Fresh longs building — trend continuation (breakout_v1 confirmation)
Price ↑ + OI ↓ = Short covering rally — less sustainable, watch for reversal
Price ↓ + OI ↑ = Fresh shorts building — bearish continuation
Price ↓ + OI ↓ = Long unwinding — weaker bearishness
```

**Implied Volatility (IV) — Before a Breakout**
IV contraction to multi-month lows while price consolidates near 52-week high = calm before storm = highest-quality breakout_v1 setup. When IV then expands with the price breakout, momentum is genuine.

**Max Pain — Near Expiry**
Stock price gravitates toward max pain (where option writers lose least) in the week before monthly expiry. This creates predictable short-term pressure — avoid new entries in the 3 days before expiry if the stock is far from max pain.

### Data Source
NSE F&O bhavcopy — free, daily. Contains OI, volume, IV for all strikes and expiries.

---

## Priority Addition P-F: Quality Safety Filters

### Purpose
These are NOT stock-picking signals. They are **exclusion gates** — stocks failing these filters are removed from BUY consideration regardless of technical ranking. One -50% fraud stock erases months of gains.

### Piotroski F-Score (0–9 points)
Checks 9 binary conditions on annual financial statements:

**Profitability (4 points):**
- ROA > 0 (profitable on assets)
- Operating Cash Flow > 0
- ROA improving YoY
- OCF > Net Income (cash-backed earnings, not accounting tricks)

**Leverage / Liquidity (3 points):**
- Long-term debt ratio decreasing
- Current ratio improving
- No new shares issued (no dilution)

**Operating Efficiency (2 points):**
- Gross margin improving
- Asset turnover improving

```
Score ≥ 7: Strong fundamentals — no exclusion
Score 4–6: Moderate — monitor
Score ≤ 3: Weak fundamentals — EXCLUDE from BUY
```

### Altman Z-Score (Bankruptcy Predictor)
```
Z = 1.2×(Working Capital/Assets) + 1.4×(Retained Earnings/Assets)
  + 3.3×(EBIT/Assets) + 0.6×(Market Cap/Total Liabilities)
  + 1.0×(Revenue/Assets)

Z > 2.99: Safe zone
1.81 < Z < 2.99: Grey zone — caution
Z < 1.81: Distress zone — EXCLUDE
```

### Beneish M-Score (Manipulation Detector)
8-variable model detecting earnings manipulation. Catches Satyam-style frauds before they become public.
```
M > -1.78: Possible manipulator — EXCLUDE or flag for human review
M < -2.22: Unlikely manipulator — safe
```

### Promoter Pledge Hard Block
```
If promoter_pledge_pct > 50% of promoter holding:
    EXCLUDE from all BUY recommendations
    Reason: PROMOTER_PLEDGE_HIGH
```
High pledge means promoter borrowed heavily against their own shares. If stock falls, lender force-sells, creating a cascade.

### Auditor Change Flag
```
If company changed auditor within last 12 months:
    EXCLUDE from BUY for 12 months from change date
    Reason: AUDITOR_CHANGE_RISK
```
Mid-year auditor changes (especially from big-4 to unknown firm) precede many accounting frauds.

### Quality Score Table

```sql
CREATE TABLE stock_quality_scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id        UUID NOT NULL REFERENCES stocks(id),
    as_of_date      DATE NOT NULL,
    piotroski_score INT,             -- 0-9
    altman_z_score  NUMERIC(8,4),
    beneish_m_score NUMERIC(8,4),
    promoter_pledge_pct NUMERIC(6,3),
    auditor_changed BOOLEAN DEFAULT FALSE,
    auditor_change_date DATE,
    quality_gate_passed BOOLEAN NOT NULL,  -- summary: pass/fail
    exclusion_reasons JSONB,               -- list of reasons if failed
    computed_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (stock_id, as_of_date)
);
```

Quality scores computed quarterly (after each financial results season). Gate checked on every BUY recommendation.

---

## Priority Addition P-G: Macro Overlay

### Sector Sensitivity Matrix

Each sector's sensitivity to macro variables is pre-defined. When a macro signal fires, it adjusts the sector posture automatically:

| Macro Signal | Trigger | Sector Boost | Sector Headwind |
|---|---|---|---|
| RBI rate cut | Repo rate decreases | Banks, NBFC, Real Estate, Auto | None |
| RBI rate hike | Repo rate increases | None | Banks (NIM pressure), Real Estate |
| INR weakens > 2% (1 month) | USD/INR rises | IT, Pharma exporters | Oil, metals importers |
| INR strengthens > 2% | USD/INR falls | Oil, paint, tyre, airlines | IT |
| Crude > $90 | Brent futures | Oil PSUs, ONGC | Paint, tyre, airlines, FMCG |
| Crude < $70 | Brent futures | Paint, tyre, airlines, FMCG | Oil PSUs |
| Monsoon > 105% normal | IMD forecast | Agri, rural FMCG, tractors, seeds | None |
| Monsoon < 90% normal | IMD forecast | None | Agri, rural FMCG, 2-wheelers |
| India VIX > 22 | VIX index | None (caution overlay) | All — reduce position sizes |
| India VIX < 13 | VIX index | All (complacency check) | None |

### Integration
Macro overlay feeds into the sector intelligence layer (ADR-039) — a sector can gain or lose tailwind not just from news but from macro variable changes. RBI rate cut fires automatically as a sector tailwind for Banks and NBFCs without requiring a news article to be parsed.

---

## Priority Addition P-H: Corporate Event Calendar Intelligence

### Time-Aware Entry and Exit

Knowing what is coming allows the system to:
1. **Enter before** a high-probability positive event (earnings beat expected based on estimate revisions)
2. **Exit before** an uncertain event (company with history of missing estimates + high IV = reduce exposure)
3. **Avoid** entering in the 3 days before monthly F&O expiry (max pain distortion)

### Event Types

| Event | Action | Lead Time |
|---|---|---|
| Earnings date (estimate upgrade trend) | Prioritise BUY entry | 5–10 days before |
| Earnings date (estimate downgrade trend) | Exit or avoid entry | 7 days before |
| Dividend record date | Hold existing; new entry risky post-record | Track |
| Index inclusion date (confirmed) | BUY before passive fund purchase | 5–10 days before |
| Index exclusion date (confirmed) | EXIT before passive fund selling | Immediately on confirmation |
| Bonus/split record date | Hold — retail surge creates volatility | Track |
| F&O monthly expiry | Avoid new entries 3 days before | -3 days |
| AGM date | Monitor for forward guidance surprises | +1 day after |

### Data Source
NSE corporate calendar — free, updated continuously. Index rebalancing: NSE publishes 4 weeks in advance.

---

## Integrated Conviction Scoring Model

With all layers active, the conviction score gains new inputs:

```
conviction_score (0-100) built from:

  Tier 1 — Technical & RCEE (existing):      0-35 points
    • Ranking position within top 20           0-15
    • RCEE edge state                          0-10
    • Regime posture alignment                 0-10

  Tier 2 — FIL Catalyst (ADR-039):           0-20 points
    • Company catalyst present + magnitude     0-12
    • Sector tailwind active                   0-8

  Tier 3 — Conviction Amplifiers (this ADR): 0-30 points
    • Delivery % quality                       0-8
    • Institutional flow score                 0-10
    • Estimate revision momentum               0-8
    • Promoter activity signal                 0-4

  Tier 4 — Quality gates (binary):           pass/fail
    • F-Score < 3 → EXCLUDE (override all above)
    • Z-Score < 1.8 → EXCLUDE
    • Pledge > 50% → EXCLUDE
    • Auditor change → EXCLUDE

  Tier 5 — Macro/Event adjustments:         -10 to +5
    • Macro headwind for sector               -10
    • Index inclusion pending                 +5
    • F&O expiry proximity                   -5

Total possible (without quality block):       0-90 points
```

**Conviction bands remain unchanged** (BLOCKED/LOW/MEDIUM/HIGH/EXCEPTIONAL) but are now fed by a richer scoring model.

---

## Implementation Roadmap

### Batch 1 — Quick Wins (Implement immediately after current replay)
| Item | Data | Effort | Impact |
|---|---|---|---|
| P-A Delivery % | NSE bhavcopy (free, historical available) | Small | High |
| P-F Quality gates (F-Score, pledge) | Screener.in / quarterly results | Small | Medium (risk reduction) |
| P-G Macro overlay (VIX, crude, INR triggers) | NSE VIX free, crude from Yahoo Finance | Small | Medium |

### Batch 2 — Institutional Intelligence (After Batch 1 validated)
| Item | Data | Effort | Impact |
|---|---|---|---|
| P-B Shareholding pattern (quarterly) | BSE quarterly filings (free, structured) | Medium | High |
| P-B Bulk/block deals (daily) | NSE bulk deal data (free, daily) | Small | High |
| P-H Corporate event calendar | NSE corporate calendar (free) | Small | Medium |

### Batch 3 — Estimate Revisions (Requires external data partnership)
| Item | Data | Effort | Impact |
|---|---|---|---|
| P-C Estimate revisions | Screener.in API or Tickertape | Medium | Very High |
| P-D Promoter insider trading | SEBI Form-C disclosures (free, XML) | Medium | High |
| P-E F&O intelligence | NSE F&O bhavcopy (free, daily) | Medium | High (F&O stocks only) |

---

## Decision

**Status: PROPOSED.**

No implementation until:
1. Current clean-slate replay completes (baseline CAGR)
2. ADR-037 proposals P-01 through P-06 implemented and validated (replay 2)
3. ADR-039 FIL Phase 1 data collection running (30 days)

Then implement SICF Batch 1 (delivery %, quality gates, macro overlay) in parallel with ADR-039 Phase 2. These three cost almost nothing (all free data) and provide immediate risk reduction and quality improvement.

---

## Consequences

- 8 new data ingestion pipelines (NSE bhavcopy, BSE filings, SEBI disclosures, etc.)
- 7 new database tables
- Recommendation engine gains a richer scoring model (0-90 point scale vs current simpler model)
- Quality gates are hard exclusions — they will suppress some technically strong stocks. This is intentional.
- Estimate revision data (P-C) requires a paid or semi-paid data partnership for full coverage
- Full SICF implementation requires 3–4 months of parallel development alongside live paper trading

---

## References

- ADR-032: Regime Conditional Edge Engine
- ADR-037: Strategy Enhancement Proposals (P-14 market breadth)
- ADR-039: Fundamental Intelligence Layer (FIL)
- Piotroski (2000): Value Investing — the use of historical financial statement information to separate winners from losers
- Altman (1968): Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy
- Beneish (1999): The Detection of Earnings Manipulation
- Chan, Jegadeesh & Lakonishok (1996): Momentum Strategies — the role of earnings estimate revisions
- Hawkins, Chamberlin & Daniel (1984): Earnings Expectations and Security Prices
