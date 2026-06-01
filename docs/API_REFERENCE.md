# Pi-PM — API Reference

**Base URL:** `http://localhost:8000`  
**Prefix:** `/api/v1`  
**OpenAPI:** `/openapi.json` | **Swagger UI:** `/docs`  
**Last updated:** 2026-06-01

---

## Error Responses

All errors return JSON: `{"detail": "message"}`

| Status | Meaning |
|--------|---------|
| 400 | General application error (`PiPMError`) |
| 404 | Resource not found (`NotFoundError`) |
| 422 | Validation / invalid symbol / strategy not found |
| 500 | Ranking engine failure |
| 502 | External provider error (Yahoo) |
| 207 | Partial success (market data ingest batch) |

---

## Health

### `GET /api/v1/health`

Database connectivity check.

**Response 200:**
```json
{
  "status": "ok",
  "database": "connected",
  "environment": "development"
}
```

---

## Stocks

### `GET /api/v1/stocks`

List all stocks.

**Query parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `data_status` | string | No | Filter: `ACTIVE`, `INACTIVE`, `ERROR` |

**Response 200:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "symbol": "RELIANCE.NS",
    "name": "Reliance Industries Limited",
    "exchange": "NSE",
    "sector": "Energy",
    "industry": "Oil & Gas",
    "is_active": true,
    "data_status": "ACTIVE",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  }
]
```

---

### `GET /api/v1/stocks/{symbol}`

Get single stock by symbol.

**Response 200:** Same object as list item.

**Response 404:** Stock not found.

---

### `GET /api/v1/stocks/{symbol}/market-data`

Get OHLCV bars for a stock.

**Query parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `start_date` | date | No | ISO date |
| `end_date` | date | No | ISO date |
| `source` | string | No | e.g. `yahoo` |
| `limit` | int | No | 1–5000 |

**Response 200:**
```json
[
  {
    "id": "...",
    "stock_id": "...",
    "date": "2025-05-29",
    "open": 1450.0,
    "high": 1465.0,
    "low": 1440.0,
    "close": 1455.0,
    "adj_close": 1455.0,
    "volume": 5000000,
    "source": "yahoo"
  }
]
```

---

## Market Data

### `POST /api/v1/market-data/ingest`

Ingest OHLCV from Yahoo Finance.

**Request:**
```json
{
  "symbols": ["RELIANCE.NS", "TCS.NS", "^NSEI"],
  "period": "5y"
}
```

**Response 200/207:**
```json
{
  "run_id": "...",
  "period": "5y",
  "status": "completed",
  "symbols_requested": 3,
  "symbols_succeeded": 3,
  "symbols_failed": 0,
  "is_unhealthy_batch": false,
  "results": [
    {
      "symbol": "RELIANCE.NS",
      "status": "success",
      "bars_ingested": 1245
    }
  ]
}
```

Returns **207** if any symbol failed (`is_unhealthy_batch: true`).

---

## Rankings

### `POST /api/v1/rankings/run`

Execute a ranking run. Returns **201**.

**Request:**
```json
{
  "universe_code": "NIFTY_500",
  "as_of_date": "2025-05-29",
  "strategy_name": "breakout_v1",
  "strategy_version": "1.0.0",
  "benchmark_symbol": "^NSEI",
  "filter_config": {
    "min_history_days": 63,
    "min_avg_daily_traded_value": "10000000",
    "min_stock_price": "50",
    "require_data_status_active": true,
    "require_stock_active": true,
    "market_data_source": "yahoo"
  }
}
```

All fields optional — defaults from `Settings` (⚠️ `universe_code` defaults to `PI_PM_CORE`).

**Response 201:**
```json
{
  "id": "a1b2c3d4-...",
  "universe_code": "NIFTY_500",
  "as_of_date": "2025-05-29",
  "strategy_name": "breakout_v1",
  "strategy_version": "1.0.0",
  "benchmark_symbol": "^NSEI",
  "inputs_hash": "abc123...",
  "filter_config_hash": "def456...",
  "normalization_method": "percentile",
  "status": "completed",
  "started_at": "2026-05-31T10:00:00Z",
  "completed_at": "2026-05-31T10:00:05Z",
  "error_message": null,
  "metadata": {
    "benchmark_available": true,
    "ranked_stock_count": 439,
    "exclusion_summary": { "DATA_STATUS_NOT_ACTIVE": 65 }
  },
  "results_count": 439,
  "results": [
    {
      "id": "...",
      "stock_id": "...",
      "symbol": "BDL.NS",
      "rank": 1,
      "score": 0.8679,
      "score_components": {
        "high_proximity": 0.95,
        "volume_surge": 0.82
      }
    }
  ]
}
```

---

### `GET /api/v1/rankings/latest`

Get most recent completed ranking run.

**Query parameters:** `universe_code`, `strategy_name`, `strategy_version` (all optional)

**Response 200:** Same shape as `POST /rankings/run`.

---

### `GET /api/v1/rankings/{run_id}`

Get a specific ranking run by UUID.

**Response 200:** Same shape as above.

---

### `GET /api/v1/rankings/{run_id}/top`

Get top N ranked stocks.

**Query parameters:**
| Param | Type | Default | Range |
|-------|------|---------|-------|
| `n` | int | 10 | 1–100 |

**Response 200:**
```json
{
  "run_id": "...",
  "as_of_date": "2025-05-29",
  "strategy_name": "breakout_v1",
  "strategy_version": "1.0.0",
  "top": [
    { "rank": 1, "symbol": "BDL.NS", "score": 0.8679, "stock_id": "..." }
  ]
}
```

---

## Backtest

### `POST /api/v1/backtest/generate-rankings`

Generate historical ranking runs for every trading day in range. Returns **201**.

**Request:**
```json
{
  "universe_code": "NIFTY_500",
  "start_date": "2024-01-01",
  "end_date": "2025-05-31",
  "strategy_name": "breakout_v1",
  "strategy_version": "1.0.0",
  "benchmark_symbol": "^NSEI"
}
```

**Response 201:**
```json
{
  "universe_code": "NIFTY_500",
  "strategy_name": "breakout_v1",
  "strategy_version": "1.0.0",
  "benchmark_symbol": "^NSEI",
  "start_date": "2024-01-01",
  "end_date": "2025-05-31",
  "trading_days_total": 340,
  "runs_created": 280,
  "runs_reused": 60,
  "runs_failed": 0,
  "failed_dates": []
}
```

---

### `GET /api/v1/backtest/summary`

Ranking vs validation coverage for a date range.

**Query parameters (required):** `start_date`, `end_date`  
**Optional:** `universe_code`, `strategy_name`, `strategy_version`

**Response 200:**
```json
{
  "universe_code": "NIFTY_500",
  "strategy_name": "breakout_v1",
  "strategy_version": "1.0.0",
  "start_date": "2024-01-01",
  "end_date": "2025-05-31",
  "ranking_runs_total": 340,
  "validated_runs_total": 320,
  "pending_validation_runs": 20
}
```

---

## Validation (Per-Run)

### `POST /api/v1/validation/backfill`

Validate all completed ranking runs in a date range.

**Request:**
```json
{
  "start_date": "2024-01-01",
  "end_date": "2025-05-31",
  "force_recompute": false
}
```

**Response 200:**
```json
{
  "runs_found": 340,
  "validated": 280,
  "reused": 60,
  "failed": 0
}
```

---

### `POST /api/v1/validation/runs/{run_id}/compute`

Compute validation for a single ranking run. Returns **201**.

**Query parameters:** `force_recompute` (bool, default false)

**Response 201:**
```json
{
  "ranking_run_id": "...",
  "status": "completed",
  "validation_hash": "abc123...",
  "regime_label": "BULL_LOW_VOL",
  "trend_regime": "BULL",
  "vol_regime": "LOW_VOL",
  "horizon_metrics": {
    "20": {
      "status": "ok",
      "ic_spearman": "0.04200000",
      "top_minus_bottom_spread": "0.03500000",
      "sample_size": 439,
      "deciles": [
        { "decile": 1, "count": 44, "mean_return": "0.02500000", "median_return": "0.02000000" }
      ],
      "hit_rates": {
        "top_vs_median_hit_rate": "0.55000000",
        "top_vs_bottom_hit_rate": "0.60000000",
        "rank_directional_hit_rate": "0.52000000"
      }
    }
  },
  "sample_summary": {
    "ranked_stock_count": 439,
    "horizon_valid_counts": { "5": 439, "10": 439, "20": 435, "60": 420 }
  },
  "computed_at": "2026-05-31T12:00:00Z",
  "error_message": null
}
```

---

### `GET /api/v1/validation/runs/{run_id}`

Get validation report for a ranking run.

**Response 200:** Same shape as compute response.

---

### `GET /api/v1/validation/runs/{run_id}/snapshots`

Get per-stock forward return snapshots.

**Response 200:**
```json
[
  {
    "id": "...",
    "stock_id": "...",
    "symbol": "RELIANCE.NS",
    "return_5d": 0.012,
    "return_10d": 0.025,
    "return_20d": 0.041,
    "return_60d": 0.078,
    "captured_at": "2026-05-31T12:00:00Z"
  }
]
```

---

### `GET /api/v1/validation/summary`

Aggregate validation metrics across multiple runs.

**Query parameters:**
| Param | Type | Default |
|-------|------|---------|
| `universe_code` | string | — |
| `strategy_name` | string | — |
| `strategy_version` | string | — |
| `start_date` | date | — |
| `end_date` | date | — |
| `horizon` | int | 20 |

**Response 200:**
```json
{
  "reports_count": 320,
  "horizon": 20,
  "validated_runs": 320,
  "failed_runs": 0,
  "insufficient_data_runs": 5,
  "average_ic_20d": "0.03800000",
  "median_ic_20d": "0.03500000",
  "top_decile_return_20d": "0.02200000",
  "bottom_decile_return_20d": "-0.00800000",
  "spread_20d": "0.03000000",
  "hit_rate_20d": "0.54000000",
  "directional_hit_rate_20d": "0.51000000",
  "bull_market_ic": "0.04500000",
  "bear_market_ic": "0.02000000",
  "high_vol_ic": "0.02500000",
  "low_vol_ic": "0.04200000",
  "regime_ic": {
    "bull_low_vol_ic": "0.04800000",
    "bull_high_vol_ic": "0.03000000",
    "bear_low_vol_ic": "0.02200000",
    "bear_high_vol_ic": "0.01500000"
  },
  "best_regime": "BULL_LOW_VOL",
  "worst_regime": "BEAR_HIGH_VOL"
}
```

---

## Validation (Full-Universe Campaign) — Sprint 6.1

### `POST /api/v1/validation/full-universe/run`

Run a full-universe validation campaign. Generates rankings, validates each day, pools metrics. Returns **201**.

Defaults: `NIFTY_500` + `breakout_v1` v1.0.0.

**Request:**
```json
{
  "start_date": "2024-01-01",
  "end_date": "2025-05-31",
  "force_recompute": false
}
```

**Response 201:**
```json
{
  "campaign_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "completed",
  "ranking_runs_created": 280,
  "ranking_runs_reused": 60,
  "validation_days_completed": 335,
  "validation_days_failed": 5,
  "ranked_days_total": 340
}
```

---

### `GET /api/v1/validation/full-universe/summary`

Pooled campaign metrics. Defaults to latest completed campaign.

**Query parameters:**
| Param | Type | Default |
|-------|------|---------|
| `campaign_id` | UUID | Latest completed |
| `horizon` | int | 20 |
| `universe_code` | string | — |
| `strategy_name` | string | — |
| `strategy_version` | string | — |

**Response 200:**
```json
{
  "campaign_id": "f47ac10b-...",
  "universe_code": "NIFTY_500",
  "strategy_name": "breakout_v1",
  "strategy_version": "1.0.0",
  "start_date": "2024-01-01",
  "end_date": "2025-05-31",
  "status": "completed",
  "horizon": 20,
  "ic": "0.04200000",
  "rank_ic": "0.03800000",
  "hit_rate": "0.55000000",
  "directional_hit_rate": "0.52000000",
  "top_decile_return": "0.02500000",
  "bottom_decile_return": "-0.01000000",
  "spread": "0.03500000",
  "top_20_return": "0.02800000",
  "top_50_return": "0.02200000",
  "sample_size": 147650,
  "ranked_days": 335,
  "is_monotonic": true,
  "best_horizon": 20,
  "worst_horizon": 60,
  "horizons": {
    "5": {
      "ic": "0.03000000",
      "rank_ic": "0.02800000",
      "hit_rate": "0.52000000",
      "spread": "0.01500000",
      "top_decile_return": "0.00800000",
      "bottom_decile_return": "-0.00700000",
      "is_monotonic": false
    },
    "20": { "...": "..." }
  }
}
```

**Response 404:** No campaign found (before first run completes).

---

### `GET /api/v1/validation/full-universe/deciles`

Decile breakdown for a campaign horizon.

**Query parameters:**
| Param | Type | Default |
|-------|------|---------|
| `horizon` | int | 20 |
| `campaign_id` | UUID | Latest completed |
| `universe_code` | string | — |
| `strategy_name` | string | — |
| `strategy_version` | string | — |

**Response 200:**
```json
{
  "campaign_id": "f47ac10b-...",
  "horizon": 20,
  "deciles": [
    {
      "decile": 1,
      "count": 14765,
      "avg_return": "0.02500000",
      "median_return": "0.02000000",
      "win_rate": "0.58000000"
    },
    {
      "decile": 10,
      "count": 14765,
      "avg_return": "-0.01000000",
      "median_return": "-0.01200000",
      "win_rate": "0.42000000"
    }
  ]
}
```

---

## Observability (Sprint 7)

Prefix: `/api/v1/observability`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health/platform` | Platform health summary |
| GET | `/ingestion/batches` | Recent ingestion batches |
| GET | `/ingestion/batches/{batch_id}` | Batch detail |
| GET | `/rankings/runs` | Recent ranking runs with traceability fields |
| GET | `/validation/metrics` | Queryable validation horizon metrics |
| GET | `/lineage/{entity_type}/{entity_id}` | Lineage graph |
| GET | `/rankings/{id}/stocks/{stock_id}/score-reconstruction` | Rebuild score from stored factors |
| GET/POST | `/experiments` | List / start experiments |
| POST | `/experiments/{id}/complete` | Complete experiment |
| GET | `/regime/current` | Current or historical regime |
| GET/POST | `/regime/performance` | List / refresh regime performance rollups |

See `docs/sprint7-platform-traceability.md` for details.

---

## Regime Policy (Sprint 8.1 — Research Only)

Prefix: `/api/v1/regime-policy`

**Not wired to live ranking or paper trading.**

### `GET /api/v1/regime-policy/configs`

List policy configs. Query: `strategy_name`, `policy_type`, `status`.

### `POST /api/v1/regime-policy/configs`

Create draft policy config.

### `POST /api/v1/regime-policy/configs/presets/load`

Load E1–E4 `breakout_v1` preset configs (not in migration).

```json
{ "dry_run": false }
```

### `POST /api/v1/regime-policy/configs/{id}/activate`

Activate config (archives prior active of same type). Research registry only.

### `GET /api/v1/regime-policy/decisions`

Audit trail. Query: `ranking_run_id`, `as_of_date`, `regime_label`, `action`, `experiment_run_id`.

### `POST /api/v1/regime-policy/evaluate`

Dry-run or persist policy decision for a ranking run.

```json
{
  "ranking_run_id": "uuid",
  "policy_config_id": "uuid",
  "persist": false
}
```

### `POST /api/v1/regime-policy/backtest/run`

Run E1–E4 comparison with holdout split.

```json
{
  "strategy_name": "breakout_v1",
  "strategy_version": "1.0.0",
  "universe_code": "NIFTY_500",
  "horizon": 20,
  "start_date": "2024-01-01",
  "end_date": "2025-12-31",
  "holdout_start_date": "2025-01-01",
  "policy_config_ids": ["e1-uuid", "e2-uuid", "e3-uuid", "e4-uuid"],
  "baseline_policy_config_id": "e1-uuid",
  "experiment_name": "sprint81_regime_gate_comparison"
}
```

**Response includes:** `experiment_run_id`, `backtest_run_ids`, `summary`, `best_policy_on_holdout`, per-policy `research_findings`.

**Performance:** Uses batch SQL + fast pooled metrics. Do not revert to per-day SQL + `compute_full_horizon_metrics` on pooled data.

### `GET /api/v1/regime-policy/backtest/runs`

List backtest runs. Query: `experiment_run_id`, `policy_config_id`, `status`.

See `docs/sprint81-regime-aware-trading.md`.

---

## Factor Analytics (Sprint 8.2 — Read-Only)

Prefix: `/api/v1/analytics/factors`

Research analytics on factor IC; does not modify rankings or weights.

### `GET /api/v1/analytics/factors/performance`

Filter aggregate metrics. Query: `factor_name`, `regime_label`, `horizon`, `universe_code`, `dataset_split` (`ALL`|`TRAIN`|`HOLDOUT`), `start_date`, `end_date`.

### `GET /api/v1/analytics/factors/leaderboard`

Rank factors by IC for a regime/horizon. **Default `dataset_split=HOLDOUT`.** Exposes `train_ic`, `holdout_ic`, `ic_drift`, resolved weights, stability, coverage.

Query (required): `regime_label`, `horizon`, `universe_code`.

### `GET /api/v1/analytics/factors/compare`

Single-factor view across regimes and horizons. Query: `factor_name`, `universe_code`.

### `GET /api/v1/analytics/factors/train-holdout-drift`

Drift detection with verdicts (`holdout_confirmed`, `overfit_suspect`, etc.). Default `regime_label=BULL_LOW_VOL`, `horizon=20`, `holdout_start_date=2025-01-01`.

### `POST /api/v1/analytics/factors/backfill`

Trigger analytics backfill from traceability data.

**Body:**
```json
{
  "universe_code": "NIFTY_500",
  "start_date": "2023-01-01",
  "end_date": "2025-05-30",
  "holdout_start_date": "2025-01-01",
  "force_recompute": false,
  "write_daily_metrics": true
}
```

### `GET /api/v1/analytics/factors/runs`

List backfill runs. Query: `status`, `limit`.

### `GET /api/v1/analytics/factors/runs/{run_id}`

Single backfill run detail.

See `docs/sprint82-factor-ic-analytics.md` and `docs/sprint82-implementation-summary.md`.

---

## Exit Research (Sprint 8.3 — Read-Only)

Prefix: `/api/v1/analytics/exit`

Simulates exit policies on validated ranking signal entries. Does not modify rankings, validation, or execution.

### `POST /api/v1/analytics/exit/backfill`

Trigger exit policy simulation backfill.

**Body:**
```json
{
  "strategy_name": "breakout_v1",
  "strategy_version": "1.0.0",
  "universe_code": "NIFTY_500",
  "start_date": "2024-01-01",
  "end_date": "2025-05-30",
  "holdout_start_date": "2025-01-01",
  "force_recompute": false
}
```

### Report endpoints

Query params typically include `run_id`, `strategy_name`, `regime_label`, `horizon`, `dataset_split`.

| GET path | Report |
|----------|--------|
| `/reports/comparison` | Exit policy comparison |
| `/reports/alpha-decay` | Alpha decay |
| `/reports/rank-deterioration` | Rank deterioration |
| `/reports/regime-exit` | Regime exit |
| `/reports/trend-failure` | Trend failure |
| `/reports/recommended` | Recommended exit policy |

### `GET /api/v1/analytics/exit/runs`

List backfill runs. Response includes:

| Field | Description |
|-------|-------------|
| `status` | `running`, `completed`, `failed` |
| `current_phase` | e.g. `simulating`, `persisting_policy_metrics`, `completed` |
| `processed_entries` / `total_entries` | Simulation progress |
| `percent_complete` | Capped at 90% during simulation; 90–100% during persistence |
| `persistence_items_processed` / `persistence_items_total` | Post-simulation write progress |

Long runs: metric rows are visible before completion (batch commits every 25 upserts). See `docs/sprint83-backfill-performance.md`.

See `docs/sprint83-exit-research-design.md` and `docs/sprint83-85-implementation-summary.md`.

---

## Research Intelligence (Sprint 8.5 — Read-Only)

Prefix: `/api/v1/analytics/research-intelligence`

Committee-grade reporting from validation, ranking, and factor analytics outputs.

### `POST /api/v1/analytics/research-intelligence/generate`

Generate report pack: coverage, ranking stats, IC/spread by strategy and regime, factor contribution, top 20, executive summary.

**Body:**
```json
{
  "universe_code": "NIFTY_500",
  "start_date": "2024-01-01",
  "end_date": "2025-05-30",
  "holdout_start_date": "2025-01-01",
  "persist": true
}
```

### `GET /api/v1/analytics/research-intelligence/runs` / `runs/{run_id}`

List and retrieve persisted generation runs.

See `docs/sprint83-85-implementation-summary.md`.

---

## Endpoint Summary

| Method | Path | Tag |
|--------|------|-----|
| GET | `/api/v1/health` | health |
| GET | `/api/v1/stocks` | stocks |
| GET | `/api/v1/stocks/{symbol}` | stocks |
| GET | `/api/v1/stocks/{symbol}/market-data` | stocks |
| POST | `/api/v1/market-data/ingest` | market-data |
| POST | `/api/v1/rankings/run` | rankings |
| GET | `/api/v1/rankings/latest` | rankings |
| GET | `/api/v1/rankings/{run_id}` | rankings |
| GET | `/api/v1/rankings/{run_id}/top` | rankings |
| POST | `/api/v1/backtest/generate-rankings` | backtest |
| GET | `/api/v1/backtest/summary` | backtest |
| POST | `/api/v1/validation/backfill` | validation |
| POST | `/api/v1/validation/runs/{run_id}/compute` | validation |
| GET | `/api/v1/validation/runs/{run_id}` | validation |
| GET | `/api/v1/validation/runs/{run_id}/snapshots` | validation |
| GET | `/api/v1/validation/summary` | validation |
| POST | `/api/v1/validation/full-universe/run` | validation |
| GET | `/api/v1/validation/full-universe/summary` | validation |
| GET | `/api/v1/validation/full-universe/deciles` | validation |
| GET | `/api/v1/observability/*` | observability |
| GET/POST | `/api/v1/regime-policy/*` | regime-policy |
| GET/POST | `/api/v1/analytics/factors/*` | factor-analytics |
| GET/POST | `/api/v1/analytics/exit/*` | exit-analytics |
| GET/POST | `/api/v1/analytics/research-intelligence/*` | research-intelligence |

**Total:** 45+ endpoints (see OpenAPI `/docs` for full list)

---

## Related Documentation

- `docs/HANDOFF.md` — Takeover guide
- `docs/sprint7-platform-traceability.md`
- `docs/sprint81-regime-aware-trading.md`
- `docs/sprint82-factor-ic-analytics.md`
- `docs/sprint83-exit-research-design.md`
- `docs/sprint83-85-implementation-summary.md`

---

## Postman Collection

`docs/PiPM-Sprint5.postman_collection.json` — covers Sprint 5 endpoints; extend for Sprint 6.1 full-universe routes.
