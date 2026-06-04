# Product Status

**As of:** 2026-06-04 · **Branch:** `feature/see-v2`

---

## Shipped

| Feature | Version / sprint | Notes |
|---------|------------------|-------|
| Market data + universes | Sprint 2 | Yahoo ingest; `NIFTY_500` |
| Ranking engine | Sprint 3–3.1 | `momentum_v1`, `breakout_v1` frozen |
| Validation | Sprint 4.2, 6.1 | Per-run + full-universe campaigns |
| Traceability | Sprint 7, 7.1 | Observability API |
| Regime policy replay | Sprint 8.1 | Research only |
| Factor IC | Sprint 8.2 | `/analytics/factors` |
| Exit research | Sprint 8.3 | Phased backfill |
| Research intelligence | Sprint 8.5 | Executive reports API |
| Daily batch | Sprint 8.6 | `/ops/daily-batch` |
| ARGS Phase 1 | 20260608_0016 | `/research/*` |
| Stock setup research | 20260608_0017 | SEE pipeline API |
| SEE v2 metrics | 20260609_0018 | Strategy profiles |
| Committee Phase 2 | Research sprint | ~79% independence |
| SQE on packets | Phase 2 | Observability; QRC flag off |
| Outcome attribution | Analytics | Read-only service + reports |
| Ranking research reports | Scripts | Five root-cause reports |

---

## In progress / blocked

| Item | Blocker |
|------|---------|
| Validation tail completeness | Forward bars after ~2026-05-27 |
| Exit research backfill at scale | Time/compute; monitor phases |
| PO: ranking v2 | Non-monotonic ranks documented |
| PO: QRC SQE default | A/B shows keep `false` |
| Committee Phase 3 | Design TBD |

---

## Not started

| Item |
|------|
| Paper trading services |
| Portfolio construction |
| Live broker |
| AI research agent (Sprint 8.4 plan) |

---

## Health dashboard (qualitative)

| Area | Green | Yellow | Red |
|------|-------|--------|-----|
| Rankings | ✓ deterministic | | |
| Bucket-level alpha | ✓ partial | | |
| Rank calibration | | ✓ research | |
| Validation recency | | ✓ tail pending | |
| ARGS committees | ✓ Phase 2 | | Phase 3 |
| QRC SQE path | ✓ default off | ✓ experiment | |

See [PROJECT_STATE_2026_06_04.md](../12_HANDOVER/PROJECT_STATE_2026_06_04.md).
