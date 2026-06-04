# Implementation Status

**As of:** 2026-06-04

---

## By subsystem

| Subsystem | Package | Status | Tests (approx) |
|-----------|---------|--------|----------------|
| Health / core | `app/core`, `test_health` | Done | 6+ |
| Stocks / market data | `services`, `providers` | Done | 15+ |
| Universe | `app/universe` | Done | 4+ |
| Ranking | `app/ranking` | Done (frozen) | 25+ |
| Validation | `app/validation` | Done (frozen) | 20+ |
| Backtest replayer | `app/backtest` | Done | 4+ |
| Traceability | models + services | Done | 15+ |
| Regime policy | `app/regime_policy` | Done (research) | 14+ |
| Factor analytics | `app/factor_analytics` | Done | 25+ |
| Exit research | `workspace_exit_research` | Done (backfill ongoing) | 25+ |
| Research intelligence | services + models | Done | API integration |
| Daily batch | `app/ops/daily_batch` | Done | 4+ |
| ARGS | `app/args` | Done Phase 1–2 | 50+ |
| SEE v2 | `stock_setup_evidence` | Done | 5+ |
| Outcome attribution | `outcome_attribution` | Done | 11+ |
| Ranking research | `ranking_research` | Reports only | 10+ |
| Paper / portfolio | models | Stub | 0 |

**Total:** 312 pytest tests.

---

## Migrations

18 revisions; head **`20260609_0018`**.

---

## Not implemented

- Paper trading service layer
- Portfolio construction
- CI workflow in `.github/`
- Committee Phase 3
- Production ranking calibration v2

---

## Branch note

README root may cite older branch (`feature/sprint8`); active handoff branch is **`feature/see-v2`**.

See [CODE_MAP.md](./CODE_MAP.md).
