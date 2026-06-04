# Regime Design

**Status:** Research API (Sprint 8.1) · **Owner:** `app/regime_policy/`

---

## Purpose

Evaluate **post-ranking** policies (allow/hold/reduce) by market regime without changing factor weights or reranking.

---

## Components

| Component | Path |
|-----------|------|
| Engine | `app/regime_policy/engine.py` |
| Replay | `app/regime_policy/replay.py` |
| Metrics | `app/regime_policy/metrics.py` (incl. pooled fast path) |
| API | `/api/v1/regime-policy/*` |

---

## Tables

`regime_policy_configs`, `regime_policy_decisions`, `regime_backtest_runs`, `regime_history`, `strategy_regime_performance`.

---

## Not wired to

- Live order execution
- Ranking engine inputs

---

## Known fixes

Backtest hang from O(n²) horizon metrics — fixed via `compute_pooled_period_metrics` and batch scored-return loader ([HANDOFF.md](../../HANDOFF.md)).

Legacy: [sprint81-regime-aware-trading.md](../../sprint81-regime-aware-trading.md), [regime-rank-reliability-report.md](../../regime-rank-reliability-report.md).
