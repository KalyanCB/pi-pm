# Sprint 4.2 — Signal Validation Framework

## Migration `20260530_0005`

### New table: `ranking_validation_reports`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| ranking_run_id | UUID FK UNIQUE | → ranking_runs CASCADE |
| status | VARCHAR(32) | pending/completed/insufficient_data/failed |
| validation_hash | VARCHAR(64) NULL | Set on completed |
| regime_label | VARCHAR(32) | BULL_HIGH_VOL, BULL_LOW_VOL, BEAR_HIGH_VOL, BEAR_LOW_VOL |
| trend_regime | VARCHAR(16) | BULL / BEAR |
| vol_regime | VARCHAR(16) | HIGH_VOL / LOW_VOL |
| horizon_metrics | JSONB | Per-horizon IC, deciles, hit rates |
| sample_summary | JSONB | Valid counts, null counts |
| computed_at | TIMESTAMPTZ NULL | |
| error_message | TEXT NULL | |

No changes to `ranking_performance_snapshots` (fill existing columns).

## Phases

1. Migration + model + constants
2. `app/validation/` domain (forward returns, statistics, regimes, hashing, report builder)
3. Repository extensions + `MarketDataCache` forward load
4. `SignalValidationService`
5. API routes + backtest summary
6. Unit, integration, golden tests

## Regime rules

- **BULL:** benchmark close > SMA(200) at as_of_date
- **BEAR:** benchmark close ≤ SMA(200)
- **HIGH_VOL:** 20-day annualized vol > threshold (config, default 0.20)
- **LOW_VOL:** otherwise
- **regime_label:** `{trend_regime}_{vol_regime}` e.g. `BULL_LOW_VOL`

## Forward returns

N **trading days** forward; entry = latest bar ≤ as_of; NULL if insufficient data.

## Summary API

Aggregates completed validation reports in optional date/universe filter:
`average_ic_20d`, decile returns, spread, hit_rate, IC by trend/vol regime.
