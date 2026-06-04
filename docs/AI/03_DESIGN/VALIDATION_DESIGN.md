# Validation Design

**Status:** Production (frozen) · **Owner:** `app/validation/`

---

## Purpose

Measure whether ranking signals predict forward returns via IC, hit rate, deciles, and regime-conditioned metrics.

---

## Horizons

5, 10, 20, 60 **trading days** forward from `as_of_date`.

---

## Outputs

| Artifact | Table |
|----------|-------|
| Report | `ranking_validation_reports` |
| Snapshots | `ranking_performance_snapshots` |
| Full-universe | `full_universe_validation_*` |
| Traceability | `validation_horizon_metrics`, `validation_decile_metrics` |

---

## Regime split

`BULL_LOW_VOL`, `BULL_HIGH_VOL`, `BEAR_LOW_VOL`, `BEAR_HIGH_VOL` — MA200 trend + vol vs threshold.

**Research note:** `breakout_v1` 20d alpha concentrated in `BULL_LOW_VOL` ([HANDOFF.md](../../HANDOFF.md)).

---

## Validation pending tail

Recent ranking dates (~from **2026-05-27**) return **`insufficient_data`** until enough forward bars exist. Ops must ingest through forward window, not just ranking date.

---

## API

- `POST /api/v1/validation/runs/{run_id}/compute`
- `GET /api/v1/validation/summary`
- Full-universe: `/validation/full-universe/*`

---

## Performance warning

Do not run `compute_full_horizon_metrics` on 100k+ pooled rows — O(n²). Use `compute_pooled_period_metrics` ([HANDOFF.md](../../HANDOFF.md)).

Legacy: [sprint42-implementation-plan.md](../../sprint42-implementation-plan.md), [sprint61-full-universe-validation-report.md](../../sprint61-full-universe-validation-report.md).
