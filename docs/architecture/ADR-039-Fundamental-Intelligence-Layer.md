# ADR-039: Fundamental Intelligence Layer (FIL)

**Status:** PROPOSED  
**Date:** 2026-06-21  
**Author:** System design — post ADR-037 strategy enhancement review  
**Depends on:** ADR-032 (RCEE), ADR-037 (Strategy Enhancements)

---

## Problem Statement

The current system is **100% price-action based**. Every signal — momentum, breakout, reversal, volatility — is derived from OHLCV bars. The system sees *what* is happening in price but not *why*.

This creates a structural blind spot: the biggest multi-week winners (RVNL +200%, IRFC +150%, Dixon +180%) share a common pattern — a **technical setup coinciding with a fundamental catalyst** that the market underprices for days or weeks. Without news intelligence, the system:

1. Enters too late — only after price already moved enough to rank top 20
2. Cannot distinguish a breakout backed by a real catalyst from a random noise breakout
3. Misses the highest-conviction setup in quantitative investing: **technical confirmation + fundamental catalyst**

---

## Proposed Solution: Fundamental Intelligence Layer (FIL)

A parallel subsystem that ingests news and corporate events for all ~1000 universe stocks, uses an AI model to extract structured signals, maintains a **WATCH list** of stocks with active fundamental catalysts, and feeds conviction boosts into the existing recommendation engine when a catalyst-backed stock also satisfies RCEE and ranking gates.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA INGESTION                           │
│                                                             │
│  NSE/BSE XML Feeds  →  AI Extraction  →  news_events table │
│  SEBI Filings       →  AI Extraction  →  news_events table │
│  Financial News RSS →  AI Extraction  →  news_events table │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                   FIL WATCH LIST                            │
│                                                             │
│  Active catalysts with confidence ≥ 0.85                   │
│  Decays by category (earnings: 20d, order: 30d, etc.)      │
│  Stored in: fil_watch_list table                            │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│               RECOMMENDATION ENGINE (existing)              │
│                                                             │
│  IF stock in top 20 (ranking gate)                         │
│  AND RCEE EDGE_PRESENT                                      │
│  AND stock on FIL watch list (catalyst active)             │
│  → Boost conviction band + 1 level                         │
│  → Reason code: FUNDAMENTAL_CATALYST_CONFIRMED             │
│  → Priority BUY slot (fills before non-catalyst stocks)    │
└─────────────────────────────────────────────────────────────┘
```

**FIL sits parallel to RCEE — not replacing it:**
- RCEE answers: *"Does this strategy have statistical edge in this regime?"*
- FIL answers: *"Does this specific stock have a fundamental reason to move right now?"*
- Both YES → EXCEPTIONAL conviction
- Only RCEE YES → HIGH conviction (current behaviour, unchanged)
- Only FIL YES (not in top 20) → WATCH list only, no BUY

---

## Data Sources

### Tier 1 — Structured Official Feeds (Mandatory, Start Here)

| Source | Data | Format | Access |
|---|---|---|---|
| NSE Corporate Announcements | Results, AGM, dividends, board decisions | XML/JSON API | Free, public |
| BSE Corporate Filings | Same + SEBI disclosures | XML/JSON API | Free, public |
| SEBI Bulk/Block Deals | Promoter & institutional buys/sells | CSV | Free, public |
| SEBI Insider Trading | Promoter shareholding changes | XML | Free, public |

Tier 1 covers ~70% of high-impact catalysts. It is structured, timestamped, and machine-readable with zero ambiguity (official regulatory filings).

### Tier 2 — Semi-Structured (Add After Tier 1 Validated)

| Source | Data | Notes |
|---|---|---|
| Screener.in | Quarterly results, analyst estimates, financial ratios | Requires scraping or API |
| Tickertape | Analyst ratings, FII/DII activity | API available |
| Economic Times Markets RSS | Sector news, macro announcements | Needs NLP filtering |
| Moneycontrol News RSS | Company-specific news | Noisy, needs confidence threshold |

### Tier 3 — Unstructured (Future Research)

| Source | Data | Risk |
|---|---|---|
| Twitter/X financial accounts | Early signals, analyst commentary | Very noisy, hallucination risk |
| Management concall transcripts | Forward guidance, qualitative tone | High value but requires parsing |
| Brokerage research PDFs | Target price changes, buy/sell calls | Access limited |

**Implementation order:** Tier 1 only in v1. Add Tier 2 sources one at a time, validate each against backtest before enabling for live signals.

---

## AI Extraction Model

### Input
Raw news text or structured filing + metadata (source, date, stock_id).

### Output Schema
```json
{
  "stock_id": "uuid",
  "event_date": "2025-03-15",
  "source": "BSE_ANNOUNCEMENT",
  "category": "EARNINGS_BEAT",
  "sentiment": "POSITIVE",
  "magnitude": "HIGH",
  "confidence": 0.91,
  "catalyst_duration_days": 20,
  "summary": "Q3 PAT beat estimates by 18%, order book at 5-year high of ₹12,400 Cr",
  "raw_excerpt": "...",
  "flags": ["ORDER_BOOK_HIGH", "MARGIN_EXPANSION"]
}
```

### Categories

| Category | Sentiment | Typical Duration | Notes |
|---|---|---|---|
| `EARNINGS_BEAT` | POSITIVE | 15–20 days | PAT/revenue above estimates |
| `EARNINGS_MISS` | NEGATIVE | 10–15 days | Suppresses BUY even if ranked high |
| `ORDER_WIN` | POSITIVE | 25–35 days | New contract, order book expansion |
| `REGULATORY_APPROVAL` | POSITIVE | 20–30 days | USFDA, NCLT, environmental clearance |
| `REGULATORY_RISK` | NEGATIVE | 30–60 days | SEBI notice, SFIO, import ban |
| `PROMOTER_BUYING` | POSITIVE | 20–30 days | Open market purchase ≥ 0.5% stake |
| `PROMOTER_SELLING` | NEGATIVE | 15–20 days | Large stake sale, pledge creation |
| `DEBT_REDUCTION` | POSITIVE | 30–45 days | Debt repayment, credit upgrade |
| `DEBT_CONCERN` | NEGATIVE | 45–90 days | Rating downgrade, missed payment |
| `CAPEX_ANNOUNCEMENT` | POSITIVE | 30–60 days | Capacity expansion, new plant |
| `SECTOR_TAILWIND` | POSITIVE | 45–90 days | PLI scheme, budget allocation, export incentive |
| `ANALYST_UPGRADE` | POSITIVE | 5–7 days | Short-lived — market prices quickly |
| `ANALYST_DOWNGRADE` | NEGATIVE | 5–7 days | Suppresses BUY for 1 week |
| `MANAGEMENT_CHANGE` | CONTEXT | 15–20 days | AI assesses positive/negative based on context |
| `MERGER_ACQUISITION` | CONTEXT | 30–60 days | Depends on deal terms |

### Magnitude Scoring

| Magnitude | Condition (examples) |
|---|---|
| `HIGH` | PAT beat > 15%, order > ₹500 Cr, USFDA approval, promoter buy > 1% |
| `MEDIUM` | PAT beat 5–15%, order ₹100–500 Cr, analyst upgrade with target raise > 20% |
| `LOW` | PAT beat < 5%, minor analyst note, small contract win |

Only `HIGH` and `MEDIUM` magnitude events eligible to boost conviction. `LOW` events noted but do not affect BUY decisions.

### Confidence Threshold
- Minimum `confidence ≥ 0.85` required for watch list entry
- Events with `0.70 ≤ confidence < 0.85` stored in DB but marked `UNCONFIRMED` — used for analysis only
- Events with `confidence < 0.70` discarded

### Model Selection
- **Primary:** Claude claude-sonnet-4-6 (structured extraction, high accuracy on financial filings)
- **Batch processing:** Run nightly after market close on all Tier 1 feeds from the day
- **Prompt approach:** Few-shot prompting with 20 labelled examples per category
- **Validation:** Weekly human review of 50 random extractions to monitor drift

---

## Database Schema

### `company_news_events`
```sql
CREATE TABLE company_news_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id        UUID NOT NULL REFERENCES stocks(id),
    event_date      DATE NOT NULL,
    source          VARCHAR(50) NOT NULL,   -- BSE_ANNOUNCEMENT, NSE_FEED, etc.
    category        VARCHAR(50) NOT NULL,
    sentiment       VARCHAR(20) NOT NULL,   -- POSITIVE, NEGATIVE, NEUTRAL, CONTEXT
    magnitude       VARCHAR(10) NOT NULL,   -- HIGH, MEDIUM, LOW
    confidence      NUMERIC(4,3) NOT NULL,
    catalyst_duration_days INT NOT NULL,
    summary         TEXT NOT NULL,
    raw_excerpt     TEXT,
    flags           JSONB,                  -- additional tags
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    INDEX (stock_id, event_date),
    INDEX (event_date, category)
);
```

### `fil_watch_list`
```sql
CREATE TABLE fil_watch_list (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id        UUID NOT NULL REFERENCES stocks(id),
    news_event_id   UUID NOT NULL REFERENCES company_news_events(id),
    added_date      DATE NOT NULL,
    expires_date    DATE NOT NULL,          -- added_date + catalyst_duration_days
    catalyst_type   VARCHAR(50) NOT NULL,
    confidence      NUMERIC(4,3) NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    deactivated_at  TIMESTAMPTZ,
    deactivation_reason VARCHAR(50),        -- EXPIRED, CONTRADICTED, MANUAL
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    INDEX (stock_id, is_active, expires_date),
    INDEX (added_date)
);
```

### `fil_conviction_boosts`
```sql
CREATE TABLE fil_conviction_boosts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_result_id UUID REFERENCES recommendation_results(id),
    fil_watch_list_id       UUID REFERENCES fil_watch_list(id),
    original_conviction_band VARCHAR(20),
    boosted_conviction_band VARCHAR(20),
    boost_applied           BOOLEAN NOT NULL,
    reason                  VARCHAR(100),
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Integration with Recommendation Engine

### New parameter to `rec_engine.run()`
```python
def run(
    *,
    ...
    fil_watch_stock_ids: dict[UUID, str] | None = None,
    # maps stock_id → catalyst_type for active watch list entries
) -> tuple[list[RecommendationRow], str]:
```

### Conviction boost logic in `_evaluate()`
```python
# After standard conviction calculation, before slot gate:
if action == RecommendationAction.BUY and fil_watch_stock_ids:
    catalyst = fil_watch_stock_ids.get(rr.stock_id)
    if catalyst:
        # Boost conviction band by 1 level
        conviction = _boost_conviction(conviction)
        reason_codes.append(f"FUNDAMENTAL_CATALYST_CONFIRMED:{catalyst}")
```

### Negative catalyst suppression (new gate)
```python
# Before BUY evaluation — hard block on negative catalysts
NEGATIVE_CATEGORIES = {
    "EARNINGS_MISS", "REGULATORY_RISK", "PROMOTER_SELLING",
    "DEBT_CONCERN", "ANALYST_DOWNGRADE"
}
if rr.stock_id in fil_negative_stock_ids:
    # Downgrade to WATCH regardless of rank/conviction
    return RecommendationAction.WATCH, None, ["NEGATIVE_CATALYST"], conviction, None
```

This means FIL does two things:
1. **Boosts** stocks with positive catalysts
2. **Suppresses** stocks with active negative catalysts — even if the ranker says top 5

---

## Ingestion Pipeline

### Daily Batch Integration

```
After market close (18:00 IST):
  1. Fetch all NSE/BSE announcements since last run
  2. Filter for universe stocks only (stock_id lookup)
  3. Batch send to Claude API for extraction (max 50 items/batch)
  4. Write confirmed events (confidence ≥ 0.85) to company_news_events
  5. Create/update fil_watch_list entries
  6. Expire entries past their catalyst_duration_days
  7. Write audit log
```

New phase in `DailyBatchPhaseFlags`:
```python
@dataclass
class DailyBatchPhaseFlags:
    ...
    fundamental_intelligence: bool = True  # new
```

### Backtest Replay Handling

For the historical replay (2021–2026), the FIL cannot be built in real-time since we don't have historical news archives easily. Two options:

**Option A — Replay without FIL:** Run the clean baseline first (current replay), establish the baseline CAGR. Add FIL for live trading only.

**Option B — Historical news backfill:** Source historical BSE/NSE announcement archives (available via BSE website for past years), run AI extraction retroactively, then re-run a third replay with FIL active. Compare: baseline vs FIL-enhanced.

**Recommendation:** Option A first. FIL in live trading from day 1 of live deployment. Historical backfill as a separate research project to quantify the CAGR improvement.

---

## Expected Impact

### Why the Biggest Winners Come From This

Multi-week winners (10–30%+ moves) almost always have a fundamental catalyst behind them:
- A stock breaking out on volume without a catalyst reverts ~60% of the time within 5 days
- A stock breaking out on volume WITH a confirmed fundamental catalyst continues in the same direction ~70% of the time

The quantitative signal captures the *price evidence* of a catalyst. FIL captures the *fundamental evidence* directly. Their intersection is where the highest-probability trades live.

### Quantitative Estimates

| Metric | Current (price-only) | With FIL | Basis |
|---|---|---|---|
| Win rate on FIL-confirmed BUYs | ~34% | ~55–65% | Catalyst + confirmation filter |
| Average hold on FIL-confirmed BUYs | 3 days | 8–15 days | Catalyst provides holding conviction |
| Average gain on FIL-confirmed BUYs | −₹7K | +₹40–80K | Catching early phase of catalyst move |
| CAGR contribution | baseline | +5–8% | Rough estimate, requires backtest |

*Note: These are directional estimates. Actual impact requires historical validation (Option B above).*

---

## Sector Intelligence Layer

### Why Sector News Matters

A company-specific catalyst affects one stock. A sector catalyst affects every stock in that sector simultaneously — and the ranking system already picks the best-positioned ones within it. Combining sector tailwinds with individual stock rankings creates a powerful multiplier:

- **PLI scheme for electronics** → watch all electronics manufacturers; ranking picks the strongest balance sheet/momentum name among them
- **Railway budget allocation** → watch RVNL, IRFC, Texmaco, Titagarh; ranking picks the one nearest breakout
- **RBI rate cut** → watch NBFCs and housing finance; ranking picks the highest-momentum name
- **China+1 trend** → persistent tailwind for textiles, chemicals, electronics manufacturing

The sector layer means even a stock with no company-specific news gets elevated watch list priority if its entire sector has a live tailwind — and the probability that the top-ranked name in a tailwind sector continues to outperform is significantly higher than a top-ranked name in a neutral sector.

---

### Indian Market Sector Taxonomy

| Sector | Key Catalyst Types | Typical Duration |
|---|---|---|
| **Banking & Finance** | RBI rate decisions, credit growth data, NPA disclosures, SLR/CRR changes | 30–60 days |
| **NBFC / Housing Finance** | RBI rate cut, liquidity injection, affordable housing policy | 45–90 days |
| **IT Services** | USD/INR, US tech spending, large deal wins, client commentary | 20–40 days |
| **Pharma & Healthcare** | USFDA approvals/warning letters, NLEM pricing, PLI scheme, biosimilar launches | 30–90 days |
| **Auto & EV** | Monthly sales data, PLI for EV, raw material (steel/aluminium) prices, emission norms | 20–45 days |
| **Infrastructure & Capital Goods** | Budget capex allocation, NHAI project awards, order inflows, cement demand | 45–90 days |
| **Defence & Aerospace** | Defence budget, indigenisation mandate (Make in India), export orders | 60–120 days |
| **Railways** | Railway budget, electrification targets, Vande Bharat expansion, DFC progress | 60–90 days |
| **Metals & Mining** | Global steel/aluminium prices, China demand, iron ore availability, anti-dumping duty | 20–45 days |
| **Energy & Power** | Coal availability, renewable energy targets, power tariff revision, fuel price | 30–60 days |
| **Chemicals & Specialty** | China+1 sourcing shift, raw material prices, export data, anti-dumping | 45–90 days |
| **Textiles & Apparel** | PLI scheme, export incentives, cotton prices, US/EU trade policy | 45–90 days |
| **FMCG & Consumer** | Monsoon forecast, rural demand indicators, raw material (palm oil, crude) deflation | 30–60 days |
| **Real Estate** | RBI rate cuts, stamp duty reduction, inventory absorption data, launches | 45–90 days |
| **Telecom** | ARPU trends, spectrum auction, data consumption growth, tariff hike | 30–60 days |

---

### Sector News Sources

| Source | Coverage | Access |
|---|---|---|
| Ministry of Finance / PIB press releases | Budget, PLI schemes, tax policy | Free RSS |
| Ministry of Railways announcements | Project awards, budget allocation | Free RSS |
| Ministry of Defence procurement | Defence tenders, Make-in-India orders | Free RSS |
| RBI policy statements and circulars | Rate decisions, banking regulation | Free RSS / structured |
| DGFT (Directorate General of Foreign Trade) | Export incentives, import policy | Free |
| SEBI circulars | Sector-wide regulatory changes | Free |
| NSE/BSE sector index price action | Breadth of sector movement | Already available |
| Economic Times Sector news RSS | Macro sector commentary | Tier 2 |

---

### Sector-Stock Mapping

A `sector_stocks` mapping table links each sector to all NIFTY 1000 stocks within it. This is maintained separately from price data and updated quarterly (when index constituents change).

```sql
CREATE TABLE sector_classifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id        UUID NOT NULL REFERENCES stocks(id),
    sector          VARCHAR(60) NOT NULL,
    sub_sector      VARCHAR(60),
    index_membership JSONB,   -- ["NIFTY_500", "NIFTY_MIDCAP_150", "NIFTY_INFRA"]
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (stock_id, sector)
);

CREATE TABLE sector_news_events (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_date             DATE NOT NULL,
    sector                 VARCHAR(60) NOT NULL,
    sub_sector             VARCHAR(60),
    source                 VARCHAR(80) NOT NULL,
    category               VARCHAR(50) NOT NULL,   -- same taxonomy as company events
    sentiment              VARCHAR(20) NOT NULL,
    magnitude              VARCHAR(10) NOT NULL,
    confidence             NUMERIC(4,3) NOT NULL,
    catalyst_duration_days INT NOT NULL,
    summary                TEXT NOT NULL,
    raw_excerpt            TEXT,
    affected_stocks_count  INT,   -- how many universe stocks in this sector
    created_at             TIMESTAMPTZ DEFAULT NOW(),
    INDEX (sector, event_date),
    INDEX (event_date, sentiment)
);
```

---

### How Sector Signal Propagates to Stocks

When a sector event is extracted, it is **fanned out** to all stocks in that sector as a lower-confidence watch list entry:

```
Company-specific catalyst confidence: as extracted (0.85–0.99)
Sector catalyst propagated confidence: base_confidence × 0.70

Example:
  Sector event: PLI_ELECTRONICS, magnitude=HIGH, confidence=0.92
  Propagated to Dixon: confidence = 0.92 × 0.70 = 0.64  (below 0.85 threshold)
  → Enters sector_watch_list (NOT fil_watch_list for conviction boost)
  → Acts as a tiebreaker between stocks of equal rank
```

The 0.70 haircut reflects that a sector catalyst doesn't guarantee the specific stock benefits as much as a company-specific event. A company-specific `ORDER_WIN` is far more precise than a sector-wide `SECTOR_TAILWIND`.

**Three-tier confidence hierarchy:**

| Signal Type | Confidence | Effect |
|---|---|---|
| Company-specific, Tier 1 source | ≥ 0.85 | Full conviction boost (BUY priority) |
| Company-specific + sector tailwind (both active) | Combined | Boost TWO levels (MEDIUM → EXCEPTIONAL) |
| Sector-only, Tier 1 source | 0.60–0.75 | Tiebreaker between equal-ranked stocks |
| Sector-only, Tier 2 source | 0.40–0.60 | Informational WATCH only, no BUY influence |

---

### Sector Headwinds — The Other Side

Sector headwinds are equally valuable as tailwinds. When a sector has an active negative catalyst, the system should suppress BUYs for all stocks in that sector, even if they individually rank high:

| Sector Headwind | Example | Suppression Period |
|---|---|---|
| Import duty removal | Steel imports liberalised → domestic steel margins compress | 30–45 days |
| USFDA import alert (industry-wide) | Indian pharma API exports flagged | 45–90 days |
| Raw material price spike | Crude spike → paint, tyre, FMCG margin compression | 20–30 days |
| Regulatory crackdown | RBI tightening NBFC lending norms | 30–60 days |
| Policy reversal | PLI scheme modification reducing benefits | 45–90 days |
| Export ban | Wheat/rice export ban → agri stock headwind | Until lifted |

Suppression logic mirrors the company-level negative catalyst gate — stocks in headwind sectors are downgraded to WATCH regardless of individual ranking.

**Override:** If a company in a headwind sector has a strong company-specific positive catalyst (e.g., a pharma stock gets USFDA approval while the broader pharma sector has import alerts), the company-specific signal wins — reason code `COMPANY_OVERRIDES_SECTOR_HEADWIND`.

---

### Combined Signal Matrix

| Company Catalyst | Sector Signal | Action |
|---|---|---|
| POSITIVE (company) | TAILWIND (sector) | Boost TWO conviction levels — highest priority BUY |
| POSITIVE (company) | Neutral | Boost ONE conviction level — standard FIL BUY |
| POSITIVE (company) | HEADWIND (sector) | Company wins — boost ONE level + flag `SECTOR_HEADWIND_PRESENT` |
| None | TAILWIND (sector) | Tiebreaker only — no conviction boost |
| None | Neutral | Standard price-only path (current behaviour) |
| NEGATIVE (company) | TAILWIND (sector) | Sector loses — suppress BUY + reason `NEGATIVE_CATALYST` |
| NEGATIVE (company) | HEADWIND (sector) | Double suppress — hard block, no override possible |
| None | HEADWIND (sector) | Suppress BUY — reason `SECTOR_HEADWIND` |

---

### Sector Intelligence in the Recommendation Engine

```python
def run(
    *,
    ...
    fil_watch_stock_ids: dict[UUID, str] | None = None,       # company-level
    fil_sector_tailwind_stock_ids: set[UUID] | None = None,   # sector-level (positive)
    fil_sector_headwind_stock_ids: set[UUID] | None = None,   # sector-level (negative)
) -> tuple[list[RecommendationRow], str]:
```

Both sector sets are pre-computed in `RecommendationService._load_fil_context()` by joining `sector_news_events → sector_classifications → stocks` for active events.

---

### Sector Rotation Detection

A higher-order use of sector intelligence: when multiple stocks across a sector all start ranking in the top 20 simultaneously, and the sector has a confirmed tailwind, this is a **sector rotation signal**. The system should:

1. Detect when ≥ 3 stocks from the same sector appear in top 20 across strategies
2. Cross-reference with active sector tailwind in `sector_news_events`
3. If confirmed: generate a `SECTOR_ROTATION_ALERT` in the daily batch output (not a trade signal — a portfolio awareness signal)

This tells the portfolio manager: "Capital is rotating into Infrastructure today — 4 of our top-20 candidates are infra stocks." This is useful context even if only 2 BUY slots are available.

---

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| AI misclassifies sentiment (e.g., earnings beat but guidance cut = POSITIVE when should be MIXED) | Medium | Multi-label extraction; human review weekly; confidence floor 0.85 |
| News already fully priced in at time of extraction | Medium | Check: if stock has already moved > 5% since event_date, mark catalyst as `PRICED_IN` and don't boost |
| Tier 2/3 sources contain rumours or false news | High | Gate Tier 2/3 to WATCH only — never use for conviction boost without Tier 1 confirmation |
| API cost (Claude calls) at 1000 stocks × multiple events/day | Low | Batch processing nightly; filter for universe stocks first; typical 50–200 events/day |
| Lookback bias in backtesting (using news available at time T+1 for a T decision) | High | Strict event_date discipline; only use events with event_date ≤ as_of_date in replay |
| Negative catalyst suppression blocks a genuine recovery stock | Medium | Add `CATALYST_OVERRIDE` flag for manual review; never auto-block for > 90 days |

---

## Phased Implementation Plan

### Phase 1 — Foundation (Implement Before Live Trading)
- [ ] NSE/BSE Tier 1 ingestion pipeline (daily batch)
- [ ] AI extraction with Claude — categories, sentiment, magnitude, confidence
- [ ] `company_news_events` and `fil_watch_list` tables + migrations
- [ ] Negative catalyst suppression in recommendation engine
- [ ] Daily batch FIL phase integration

### Phase 2 — Conviction Boost (After 30 Days of Data Collection)
- [ ] `fil_conviction_boosts` table
- [ ] Conviction boost integration in `rec_engine.run()`
- [ ] Reason code `FUNDAMENTAL_CATALYST_CONFIRMED` in recommendation results
- [ ] Monitoring dashboard: FIL watch list size, boost rate, boost win rate vs non-boost

### Phase 3 — Sector Intelligence (Parallel to Phase 2)
- [ ] `sector_classifications` table — map all 1000 stocks to sectors
- [ ] `sector_news_events` table + migration
- [ ] Ministry/RBI/DGFT feed ingestion (sector-level sources)
- [ ] Sector catalyst fan-out to `sector_watch_list`
- [ ] Sector headwind suppression in recommendation engine
- [ ] Sector rotation detection (`SECTOR_ROTATION_ALERT` in batch output)
- [ ] Combined signal matrix (company + sector → two-level boost)

### Phase 4 — Enrichment (After Phase 3 Validated)
- [ ] Tier 2 sources (Screener.in, ET Markets RSS)
- [ ] `PRICED_IN` detection (event date vs price move check)
- [ ] Historical news backfill for replay comparison (Option B)
- [ ] Concall transcript analysis (management tone, guidance keywords)
- [ ] `COMPANY_OVERRIDES_SECTOR_HEADWIND` logic and monitoring

### Phase 5 — Research (Long Term)
- [ ] Per-category win rate tracking (does `EARNINGS_BEAT` actually improve outcomes more than `ORDER_WIN`?)
- [ ] Catalyst duration calibration per sector (pharma USFDA duration ≠ metals duty duration)
- [ ] Promoter activity pattern detection (repeated buying over 3+ months = very strong signal)
- [ ] Sector rotation timing: how many days after a sector catalyst does price confirm?
- [ ] Cross-sector correlation: does a railway budget boost also lift cement and steel?

---

## Decision

**Status: PROPOSED — Not yet implemented.**

FIL is a significant subsystem addition. Before implementing:
1. Complete the current clean-slate replay to establish the price-only baseline CAGR
2. Implement ADR-037 proposals P-01 through P-06 and re-run a second replay
3. Begin Phase 1 FIL data collection in parallel (no impact on trading decisions yet)
4. After 30 days of Phase 1 data, enable conviction boost and monitor in paper trading

FIL should never be the *only* gate — it is always additive on top of RCEE + ranking. A stock on the FIL watch list with NO ranking confirmation does not get a BUY.

---

## Consequences

- Adds a new daily data pipeline (NSE/BSE feed ingestion + Claude API calls)
- Adds 3 new database tables
- Adds one new phase to `DailyBatchPhaseFlags`
- Recommendation results gain new reason codes (`FUNDAMENTAL_CATALYST_CONFIRMED`, `NEGATIVE_CATALYST`)
- Replay backtesting for FIL requires historical news archive sourcing (non-trivial)
- Win rate on FIL-confirmed trades should be tracked separately from non-FIL trades for ongoing validation

---

## References

- ADR-032: Regime Conditional Edge Engine (RCEE) — FIL is parallel, not a replacement
- ADR-037: Strategy Enhancement Proposals — FIL is P-15 (omitted from that ADR as it merited its own)
- NSE Corporate Announcements API: https://www.nseindia.com/companies-listing/corporate-filings-announcements
- BSE Corporate Filings: https://www.bseindia.com/corporates/ann.html
- Claude API — claude-sonnet-4-6 for structured extraction
