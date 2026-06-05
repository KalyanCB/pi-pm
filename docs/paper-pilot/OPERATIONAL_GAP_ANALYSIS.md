# Operational Gap Analysis — Paper Trading Pilot

**Date:** 2026-06-05

---

## Summary

| Category | Gaps closed in Track G | Remaining |
|----------|------------------------|-----------|
| Daily batch orchestration | 5 portfolio phases | Committee scheduling |
| NAV / reconciliation | Automated in batch | Alerting |
| Trade lineage | ranking_run_id, outcomes | approval_id FK |
| Benchmarks | ^CRSLDX ingest flag | Unified alpha definition |
| Testing | +5 unit tests | E2E, CI |
| Dashboards | Script + templates | Live UI |

---

## Gap detail

### Closed

| Gap | Resolution |
|-----|------------|
| Portfolio ops not in daily batch | `phases.portfolio` + `PaperPilotOps` |
| NAV not scheduled | `portfolio_nav` batch phase |
| Reconciliation false FAIL | NAV history as reported_nav |
| `ranking_run_id` null on trades | Populated in `PaperTradeService` |
| Batch trace missing rec IDs | `recommendation_run_ids` in lineage |
| No pilot dashboards | `generate_paper_trading_dashboard.py` |
| Unattended approve/execute | `pilot_auto_approve/execute` flags |

### Open (P1)

| Gap | Impact | Effort |
|-----|--------|--------|
| No cron/scheduler doc in repo | Ops must configure externally | 1h |
| No portfolio integration tests | Regression risk | 2d |
| Committee not in batch | ARGS stale vs recommendations | PO decision |
| Auth module new — deps not in venv | Test/env friction | 1h |

### Open (P2)

| Gap | Impact |
|-----|--------|
| Single benchmark for all alpha | Reporting inconsistency |
| `paper_trades` no recommendation FK column | Audit query complexity |
| Mobile pilot UI | Owner visibility |

---

## Lifecycle gap matrix

| Step | API exists | Batch wired | Lineage complete |
|------|------------|-------------|------------------|
| Recommend | ✓ | ✓ | ✓ |
| Approve | ✓ | ✓ (pilot flag) | Partial |
| Paper entry | ✓ | ✓ (pilot flag) | ✓ |
| Hold / MTM | ✓ | ✓ | ✓ |
| Exit signal | ✓ | ✓ | ✓ |
| Paper exit | ✓ | ✓ (pilot flag) | ✓ |
| Outcome close | ✓ | ✓ | ✓ |
| Committee review | ✓ | ✗ | ✓ (on-demand) |
| Copilot explain | ✓ | ✗ | ✓ |

---

## Ops dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| Postgres running | Infra | Required |
| `portfolio_configs` seeded | Ops | One-time |
| `^NSEI` ingested through T | Batch | Auto |
| `^CRSLDX` ingested | Batch | When portfolio on |
| Cron post NSE close | Ops | **Manual setup** |
