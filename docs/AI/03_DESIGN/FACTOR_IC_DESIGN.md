# Factor IC Design

**Status:** Production API (Sprint 8.2) · **Owner:** `app/factor_analytics/`

---

## Purpose

Persist factor-level information coefficient and related metrics over time for research and ARGS packet evidence.

---

## API prefix

`/api/v1/analytics/factors`

| Endpoint | Role |
|----------|------|
| `GET /performance` | Time series performance |
| `GET /leaderboard` | Rank factors |
| `GET /compare` | Compare factors |
| `GET /train-holdout-drift` | Drift diagnostics |
| `POST /backfill` | Trigger backfill run |
| `GET /runs`, `GET /runs/{id}` | Run metadata |

---

## Tables

`factor_performance_runs`, `factor_daily_metrics`, `factor_performance_metrics` (migration `20260601_0009`).

---

## Scripts

`scripts/backfill_sprint82_factor_analytics.py`

Legacy: [sprint82-factor-ic-analytics.md](../../sprint82-factor-ic-analytics.md), [factor-reliability-report.md](../../factor-reliability-report.md).
