# Trust Dashboard — Future Product Vision

**Version:** Phase 2.1 (PO sign-off 2026-06-04)  
**Date:** 2026-06-05  
**Status:** Vision / post-M2 — not MVP scope

---

## 1. Purpose

Expose **transparent system performance** so the owner can judge whether to trust recommendations, conviction bands, exits, and committee advice — without blending advisory signals into deterministic scores.

Feeds executive narrative in [15_EXECUTIVE_PRODUCT_STRATEGY.md](./15_EXECUTIVE_PRODUCT_STRATEGY.md) and metrics in [16_RECOMMENDATION_PERFORMANCE_PRD.md](./16_RECOMMENDATION_PERFORMANCE_PRD.md).

---

## 2. Dashboard panels (future)

| Panel | Source metrics | User question answered |
|-------|----------------|------------------------|
| **Recommendation win rate** | Quality metrics §3 | Are BUY recommendations profitable? |
| **Conviction accuracy** | Band vs outcome ([16](./16_RECOMMENDATION_PERFORMANCE_PRD.md) §4) | Do HIGH bands outperform LOW? |
| **Exit effectiveness** | `exit_reason`, stop_hit, time stops | Are exits timed well? |
| **Strategy effectiveness** | Per `strategy_name` | momentum_v1 vs breakout_v1 |
| **Regime effectiveness** | Regime buckets §6 | When should we deploy capital? |
| **Committee effectiveness** | Advisory vs outcomes §5 | Is ARGS adding value? (advisory only) |

---

## 3. UX principles

- **Separation:** Deterministic metrics vs committee metrics in distinct sections.
- **Lineage drill-down:** Click metric → list of `recommendation_outcome` rows with `ranking_run_id`.
- **No auto-tuning:** Dashboard is read-only; no “apply weights” buttons.
- **Mobile:** Summary tiles; detail on desktop first.

---

## 4. Dependencies

| Dependency | Milestone |
|------------|-----------|
| `recommendation_outcomes` populated | P3 |
| Paper book reconciliation | P5 |
| Performance APIs | P3 |
| Auth | P6+ |

---

## 5. References

- [16_RECOMMENDATION_PERFORMANCE_PRD.md](./16_RECOMMENDATION_PERFORMANCE_PRD.md)
- [PO_SIGNOFF_2026_06_04.md](./PO_SIGNOFF_2026_06_04.md)
