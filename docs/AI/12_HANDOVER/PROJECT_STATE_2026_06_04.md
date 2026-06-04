# Project State — 2026-06-04

**Branch:** `feature/see-v2`  
**Migration head:** `20260609_0018` (SEE v2 metrics)  
**Tests:** 312 passed  
**API version:** 0.4.1 (`app/main.py`)

---

## Production-ready

| Capability | API / script |
|------------|----------------|
| Market data ingest | `POST /api/v1/market-data/ingest` |
| Rankings `breakout_v1`, `momentum_v1` | `POST /api/v1/rankings/run` |
| Per-run validation | `POST /api/v1/validation/runs/{id}/compute` |
| Full-universe validation campaigns | `/api/v1/validation/full-universe/*` |
| Traceability / observability | `/api/v1/observability/*` |
| Daily NIFTY 500 batch | `POST /api/v1/ops/daily-batch/runs`, `scripts/run_daily_nifty500_batch.py` |
| Factor IC analytics | `/api/v1/analytics/factors/*` |
| Exit research reports | `/api/v1/analytics/exit/*` |
| Research intelligence | `/api/v1/analytics/research-intelligence/*` |
| ARGS Phase 1 + committee Phase 2 | `/api/v1/research/*`, `scripts/run_args_top20.py` |
| SEE v2 | `/api/v1/research/stock-setup/*`, `app/stock_setup_evidence/` |
| Outcome attribution (read-only) | `app/outcome_attribution/`, report scripts |

---

## Research / experimental

| Item | State |
|------|--------|
| Regime policy live trading | Not wired |
| Ranking v2 / isotonic calibration | Research only — no prod change |
| `ARGS_QRC_USE_SQE=true` | A/B only; default **false** |
| Committee Phase 3 | Not started |
| Paper trading / portfolio | Tables exist; services stubbed |

---

## Data health (2026-06-04 run log)

| Area | Status |
|------|--------|
| Ingestion through target date | Requires `^NSEI` through as-of |
| Rankings | Both strategies on `NIFTY_500` |
| Validation | Recent tail `insufficient_data` (forward window) |
| ARGS | Run with `ARGS_QRC_USE_SQE=false` per [dailyruns/08-args.md](../../dailyruns/04-jun-2026/08-args.md) |

---

## PO decisions pending

1. Ranking calibration / v2 promotion criteria  
2. `ARGS_QRC_USE_SQE` default promotion  
3. Committee Phase 3 scope  

See [../11_ROADMAP/CURRENT_PRIORITIES.md](../11_ROADMAP/CURRENT_PRIORITIES.md) and [PLATFORM-HANDOFF-2026.md §17](../../PLATFORM-HANDOFF-2026.md).

---

## Recent research verdicts

- **Outcome attribution:** `partial` — alpha in aggregates, weak rank gradient ([outcome-attribution-report.md](../../outcome-attribution-report.md)).
- **Committee independence:** Phase 2 targets met (~79%) ([committee-independence-phase2-results.md](../../committee-independence-phase2-results.md)).
- **breakout_v1 regime:** Alpha concentrated in `BULL_LOW_VOL` at 20d ([HANDOFF.md](../../HANDOFF.md)).
