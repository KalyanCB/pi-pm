# RCEE Operations Runbook

**Component:** Regime Conditional Edge Engine  
**ADR:** 032

---

## How to Run refresh_from_market_data Backfill

### Via Python (script or shell)

```python
from app.db.session import get_session
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V1, RANKING_STRATEGY_BREAKOUT_V1_VERSION,
    RANKING_STRATEGY_MOMENTUM_V1, RANKING_STRATEGY_MOMENTUM_V1_VERSION,
)

with get_session() as db:
    repo = RegimeAnalyticsRepository(db)
    for strategy_name, strategy_version in [
        (RANKING_STRATEGY_BREAKOUT_V1, RANKING_STRATEGY_BREAKOUT_V1_VERSION),
        (RANKING_STRATEGY_MOMENTUM_V1, RANKING_STRATEGY_MOMENTUM_V1_VERSION),
    ]:
        rows = repo.refresh_from_market_data(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            horizon=20,
            # cutoff_date defaults to today - 30 days (OOS cutoff)
        )
        print(f"{strategy_name}: wrote {len(rows)} regime rows")
        for r in rows:
            print(f"  {r.regime_label}: avg_ic={r.avg_ic:.4f}, ic_lower_95={r.ic_lower_95:.4f}, "
                  f"hit_rate={r.hit_rate:.2%}, n={r.sample_count}, from={r.computed_from}")
    db.commit()
```

### Expected output (after successful backfill)

```
breakout_v1: wrote 4 regime rows
  BEAR_HIGH_VOL: avg_ic=-0.0570, ic_lower_95=-0.1030, hit_rate=44.00%, n=27, from=market_data_direct
  BEAR_LOW_VOL:  avg_ic=-0.0910, ic_lower_95=-0.1100, hit_rate=28.00%, n=102, from=market_data_direct
  BULL_HIGH_VOL: avg_ic=-0.1590, ic_lower_95=-0.2020, hit_rate=7.00%,  n=29,  from=market_data_direct
  BULL_LOW_VOL:  avg_ic=+0.0280, ic_lower_95=+0.0190, hit_rate=60.00%, n=453, from=market_data_direct
```

---

## How to Verify strategy_regime_performance Is Populated

```sql
SELECT
    strategy_name,
    regime_label,
    avg_ic,
    ic_lower_95,
    hit_rate,
    sample_count,
    computed_from,
    last_updated
FROM strategy_regime_performance
ORDER BY strategy_name, regime_label;
```

**Healthy state:** `computed_from = 'market_data_direct'` for all rows.  
**Warning:** `sample_count = 0` or `computed_from IS NULL` → backfill has not run.  
**Action:** Run `refresh_from_market_data` as above.

---

## How to Read Edge States

The RCEE evaluates each (strategy, regime) pair on three gates:

| Edge State | Meaning | Action Implication |
|------------|---------|-------------------|
| EDGE_PRESENT | Strong positive OOS IC, high hit rate, large sample | BUY eligible (if regime non-defensive) |
| EDGE_WEAK | Marginal positive IC, borderline hit rate | WATCH + LOW_EXPECTANCY |
| NO_EDGE | Negative or zero IC in this regime | WATCH + REGIME_NO_EDGE |
| UNKNOWN | No DB row for this (strategy, regime) pair | Legacy R-ENTRY-02 fallback |

To inspect current edge states for today's recommendations:

```sql
SELECT
    rr.strategy_name,
    rr.regime_snapshot->>'rcee_edge_state'      AS edge_state,
    rr.regime_snapshot->>'rcee_sample_days'      AS sample_days,
    rr.regime_snapshot->>'rcee_ic_lower_95'      AS ic_lower_95,
    rr.regime_snapshot->>'regime_label'          AS regime_label,
    COUNT(res.id) FILTER (WHERE res.action = 'BUY')   AS buys,
    COUNT(res.id) FILTER (WHERE res.action = 'WATCH') AS watches
FROM recommendation_runs rr
JOIN recommendation_results res ON res.recommendation_run_id = rr.id
WHERE rr.as_of_date = CURRENT_DATE
GROUP BY 1, 2, 3, 4, 5
ORDER BY 1;
```

---

## What REGIME_NO_EDGE in Recommendations Means

When a recommendation has `REGIME_NO_EDGE` in its `reason_codes`, it means:

1. The stock ranked in the top-20 pool (R-ENTRY-01 passed)
2. RCEE evaluated the (strategy, current_regime) pair
3. OOS IC evidence shows **no statistical edge** in this regime (ic_lower_95 < 0.010 and/or hit_rate < 0.55 and/or insufficient data)
4. Action is WATCH — the system is correctly withholding BUY signals

**This is correct behavior in BEAR regimes.** The OOS evidence for BEAR_LOW_VOL shows
ic_lower_95 = -0.110 — strongly negative. Generating BUY signals in this regime would
be contrary to all evidence.

To distinguish REGIME_NO_EDGE (RCEE) from old VALIDATION_PENDING:

```sql
SELECT action, reason_codes, recommendation_confidence, COUNT(*)
FROM recommendation_results res
JOIN recommendation_runs rr ON rr.id = res.recommendation_run_id
WHERE rr.as_of_date >= CURRENT_DATE - 7
  AND res.rank <= 20
GROUP BY 1, 2, 3
ORDER BY 4 DESC;
```

---

## How to Trigger Regime Rotation Manually

The RCEE does not control regime detection — it reads from `regime_history` and
`strategy_regime_performance`. To simulate regime rotation for testing:

### Step 1: Insert a new regime_history row

```sql
INSERT INTO regime_history (id, as_of_date, benchmark_symbol, trend_regime, vol_regime, regime_label, recorded_at)
VALUES (gen_random_uuid(), CURRENT_DATE, '^NSEI', 'BULL', 'LOW', 'BULL_LOW_VOL', NOW());
```

### Step 2: Ensure RCEE data exists for BULL_LOW_VOL

Run `refresh_from_market_data` (see above). With 453 days of OOS history,
`BULL_LOW_VOL` will show `EDGE_PRESENT`.

### Step 3: Create a ranking run with the new regime_label

The recommendation service reads `ranking_run.regime_label`. A new ranking run
tagged with `BULL_LOW_VOL` will trigger RCEE evaluation with EDGE_PRESENT.

### Step 4: Verify BUY signals appear

```sql
SELECT res.action, COUNT(*) 
FROM recommendation_results res
JOIN recommendation_runs rr ON rr.id = res.recommendation_run_id
WHERE rr.as_of_date = CURRENT_DATE
GROUP BY 1;
```

Expected: `BUY` count > 0 when BULL_LOW_VOL EDGE_PRESENT and posture=risk_on.

---

## Daily Batch Integration

The daily batch now automatically runs `refresh_from_market_data` during the
`REGIME_PERFORMANCE` phase (called via `regime_analytics_service.refresh_from_market_data`).

This means `strategy_regime_performance` is refreshed every trading day with the latest
walk-forward OOS IC — no manual intervention needed.

OOS cutoff: ranking runs from the last 30 days are excluded to prevent lookahead bias.
The 30-day lag means IC estimates update with a one-month delay, which is appropriate
for a 20-day forward return horizon.
