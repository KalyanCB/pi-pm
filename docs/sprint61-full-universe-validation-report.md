# Sprint 6.1 — Full Universe Historical Validation Report

**Strategy:** `breakout_v1` v1.0.0  
**Universe:** `NIFTY_500`  
**Horizons:** 5, 10, 20, 60 trading days

---

## Objective

Determine whether `breakout_v1` has predictive power on the full NIFTY 500 universe using pooled historical validation (rankings + forward returns). No new signals were added in this sprint — validation only.

---

## How to Run

### 1. Apply migration

```bash
cd /Users/kalyancb/pi-pm
alembic upgrade head
```

### 2. Run full-universe validation campaign

Generates historical `breakout_v1` rankings for each trading day in range, validates forward returns, and persists campaign metrics + deciles.

```bash
curl -X POST http://localhost:8000/api/v1/validation/full-universe/run \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2025-05-31"
  }'
```

Optional: `"force_recompute": true` to recompute existing validation reports.

### 3. Summary (default horizon 20d)

```bash
curl 'http://localhost:8000/api/v1/validation/full-universe/summary?horizon=20'
```

With explicit campaign:

```bash
curl 'http://localhost:8000/api/v1/validation/full-universe/summary?campaign_id=<UUID>&horizon=20'
```

### 4. Decile breakdown

```bash
curl 'http://localhost:8000/api/v1/validation/full-universe/deciles?horizon=20'
```

Other horizons: `horizon=5`, `horizon=10`, `horizon=60`.

---

## Metrics Stored

Per horizon (pooled across all validated ranking dates):

| Category | Metrics |
|----------|---------|
| Ranking quality | IC (Pearson), Rank IC (Spearman), Hit Rate, Directional Hit Rate |
| Portfolio quality | Top Decile Return, Bottom Decile Return, Long-Short Spread, Top 20 Return, Top 50 Return |
| Distribution | Average / Median / Win Rate by decile (D1–D10), Count |

---

## Success Criteria Checklist

Run the campaign locally against your NIFTY 500 dataset (~439 ranked stocks/day) and fill in results:

| Question | How to answer | Result |
|----------|---------------|--------|
| 1. Does breakout_v1 beat random? | Rank IC / IC significantly > 0; hit rate > 50% | _TBD_ |
| 2. Does Top Decile beat Bottom Decile? | `spread` > 0; D1 avg return > D10 | _TBD_ |
| 3. Best horizon? | `best_horizon` in summary | _TBD_ |
| 4. Historical spread? | `spread` per horizon in summary | _TBD_ |
| 5. Production ready? | Monotonic deciles + stable IC across horizons | _TBD_ |

---

## Example Summary Response

```json
{
  "campaign_id": "...",
  "universe_code": "NIFTY_500",
  "strategy_name": "breakout_v1",
  "horizon": 20,
  "ic": "0.04200000",
  "rank_ic": "0.03800000",
  "hit_rate": "0.55000000",
  "top_decile_return": "0.02500000",
  "bottom_decile_return": "-0.01000000",
  "spread": "0.03500000",
  "best_horizon": 20,
  "worst_horizon": 60,
  "is_monotonic": true
}
```

---

## Architecture

```
POST /full-universe/run
  → create campaign
  → BacktestService.generate_rankings (NIFTY_500, breakout_v1)
  → SignalValidationService.validate_run (each day)
  → pool ranking_results + performance_snapshots
  → compute_full_horizon_metrics (IC, deciles, spread, top-N)
  → persist full_universe_validation_metrics + deciles
```

Tables: `full_universe_validation_campaigns`, `full_universe_validation_runs`, `full_universe_validation_metrics`, `full_universe_validation_deciles`.

---

## Notes

- Default universe/strategy for the run endpoint: `NIFTY_500` + `breakout_v1`.
- Summary/deciles default to the latest **completed** campaign if `campaign_id` is omitted.
- Per-run validation still uses existing `ranking_validation_reports` and `ranking_performance_snapshots`; campaign tables store **aggregated** full-universe results.

---

## Findings

> **Status:** Pending local run against production dataset.  
> After running the curl commands above, record IC, spread, best horizon, and decile monotonicity here before adding new signals.
