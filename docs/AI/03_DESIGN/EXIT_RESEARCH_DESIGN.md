# Exit Research Design

**Status:** Production API (Sprint 8.3) · **Owner:** `app/workspace_exit_research/`, exit services

---

## Purpose

Simulate and compare exit policies (alpha decay, rank deterioration, regime transitions, trend failure) on historical ranking paths.

---

## API prefix

`/api/v1/analytics/exit`

Reports: exit-policy-comparison, alpha-decay, rank-deterioration, regime-transition, trend-failure, recommended-exit-policy.

---

## Phased backfill

Progress tracked in DB (migrations `0011`, `0013`, `0014`). Monitor via service progress + [sprint83-backfill-performance.md](../../sprint83-backfill-performance.md).

---

## Gate

Portfolio construction deferred until exit framework selected ([ROADMAP.md](../../ROADMAP.md)).

Legacy: [sprint83-exit-research-design.md](../../sprint83-exit-research-design.md), [sprint83-85-implementation-summary.md](../../sprint83-85-implementation-summary.md).
