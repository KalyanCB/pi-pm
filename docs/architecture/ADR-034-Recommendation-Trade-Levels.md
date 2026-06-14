# ADR-034: Deterministic Trade Levels on Recommendations (Entry Range & Stop-Loss)

**Status:** Accepted
**Date:** 2026-06-10
**Supersedes / relates to:** ADR-031 (Unified Execution), ADR-032 (Live Entry-Timing
Validation Gate), ADR-033 (Intraday Exit Monitor & Stop Override)

---

## Context

A recommendation today (`RecommendationResult`) carries the *decision* — `action`,
`rank`, `composite_score`, `conviction_*`, `reason_codes` — but **no price levels**.
There is nothing on a BUY telling the analyst **at what price to enter** or **where the
stop sits**. Entry price only appears *after* execution (`RecommendationOutcome.entry_price`,
`PortfolioPosition.entry_price`), and stop percentages (`advisory_stop_pct = -8`,
`critical_stop_pct = -10`) are applied later by the exit monitor against `avg_cost`.
`portfolio_positions.stop_loss_price` exists but is unexposed (see GOTCHAS.md).

The recommendation engine (`app/recommendation/engine.py`) is **intentionally
price-blind** — it consumes only `{stock_id, rank, composite_score, score_components}`
and emits conviction/action. This separation is correct: execution prices must not
contaminate the conviction score.

However, by the time the **recommendation phase** of the daily batch runs
(`ingestion → ranking → RCEE → recommendation`), the latest per-stock OHLCV is already
ingested and in the DB. So the *phase* has everything needed to attach tradeable levels,
even though the *engine* does not see them.

## Decision

Add **deterministic trade levels** to BUY recommendations, computed in the
**recommendation service** (not the engine) as an enrichment step after the engine
returns, using the freshly-ingested market data. No LLM. No change to conviction,
ranking, validation, or engine logic.

### Levels (per BUY result)

Let `C` = latest close for the stock (`reference_close`), `ATR%` = ATR as a percent of
close over `recommendation_atr_period` sessions.

- **Entry range** (volatility-aware band around the signal close):
  - half-width `h = entry_band_atr_mult × (ATR%/100) × C` when ATR is available,
    else `h = entry_band_pct_fallback% × C`.
  - `entry_low = C − h`, `entry_high = C + h`.
- **Stop-loss range** (reuses the SAME config the exit monitor uses, so pre-trade and
  in-trade stops are consistent):
  - `stop_advisory = C × (1 + advisory_stop_pct/100)`  (−8% → `0.92·C`)
  - `stop_critical = C × (1 + critical_stop_pct/100)`  (−10% → `0.90·C`)

Stops are computed off `reference_close` as a pre-trade proxy for entry (no fill exists
yet). All values rounded to 2 dp (INR).

### Scope

- **BUY and WATCH** are enriched, distinguished by `levels_basis`:
  - `BUY → "actionable"` (enter now if approved).
  - `WATCH → "indicative"` (a plan for *if/when* it becomes actionable — most useful for
    blocked-but-qualified names, e.g. `REGIME_BLOCK` / `PORTFOLIO_FULL`). Consumers must
    treat indicative levels as guidance, never as an order.
  - `REJECT` and all other actions get **no** levels.
- Computed once per recommendation run; because the batch runs daily, levels are
  re-emitted fresh each session off that day's close. `reference_close` is stamped so
  staleness is self-evident.

> **Update (same iteration):** WATCH was originally deferred but is included — the
> enrichment is identical and only the `levels_basis` label differs. Surfaced on the
> recommendations UI and grounded into the copilot's recommendation answers.

### Persistence & exposure

- New **nullable** columns on `recommendation_results`: `reference_close`, `atr_pct`,
  `entry_low`, `entry_high`, `stop_advisory`, `stop_critical`, `levels_basis`.
- Exposed on `RecommendationResultRead` (API) and available to the copilot for citation.

### New settings (`app/core/config.py`)

```
recommendation_trade_levels_enabled: bool = True
recommendation_atr_period: int = 14
recommendation_entry_band_atr_mult: float = 0.5     # half-width = mult × ATR
recommendation_entry_band_pct_fallback: float = 1.0 # when ATR unavailable
```

Stop levels reuse the existing `advisory_stop_pct` / `critical_stop_pct`.

## Consequences

**Positive**
- BUY recommendations become directly actionable (entry band + stop range) with full
  determinism and provenance (`reference_close`, `atr_pct` stored).
- Stop levels are consistent with the exit monitor (same config), avoiding two
  conflicting stop definitions.
- Engine purity preserved; enrichment is an additive, isolated, unit-testable module
  (`app/recommendation/trade_levels.py`), mirroring `position_sizing.py`.
- Backward compatible: columns are nullable; existing rows and consumers unaffected.

**Negative / risks**
- Levels are indicative guidance off the signal-day close; actual entry occurs next
  session and may gap outside the band. Mitigated by daily re-emission + the
  ADR-032 entry-timing gate, and by storing `reference_close`/`as_of_date`.
- ATR may be unavailable for thin/young listings → fixed-% fallback band.
- A naive consumer might treat the stop as an order; it is advisory pre-trade only.

**Out of scope**
- WATCH levels (next iteration), per-position `stop_loss_price` exposure, broker GTC
  stop placement, and any auto-execution. The hard rule stands: the system explains and
  proposes levels; it never places orders.

## Alternatives considered

1. **Compute in the engine** — rejected; pollutes the price-blind decision layer.
2. **Store in `conviction_components` JSONB** — rejected; levels aren't conviction, and
   explicit columns are queryable/typed.
3. **Fixed-% entry band only** — rejected as the default; ATR band is volatility-aware.
   Retained as the fallback.
4. **Stop off `entry_high` (worst entry)** — rejected for v1 in favor of the simpler,
   transparent `reference_close` basis; revisit if PO prefers conservative stops.
