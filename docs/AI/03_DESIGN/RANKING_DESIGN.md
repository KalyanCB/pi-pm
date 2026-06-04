# Ranking Design

**Status:** Production (frozen) · **Owner:** `app/ranking/`

---

## Purpose

Deterministic composite scoring of universe members into ordered `ranking_results` per `ranking_run`.

---

## Components

| Piece | Path |
|-------|------|
| Engine | `app/ranking/engine.py` |
| Strategies | `app/ranking/strategies/momentum_v1.py`, `breakout_v1.py` |
| Factors | `app/ranking/factors/` |
| Normalizer | `app/ranking/normalizer.py` |

---

## Strategies

| Code | Factors | Min history |
|------|---------|-------------|
| `momentum_v1` | 4 | 201 sessions |
| `breakout_v1` | 8 | 252 sessions |

---

## Key research finding

**Rankings generate alpha** at bucket level (top-5/10/20), but **rank ordering within top-20 is not calibrated** due to score compression.

| Report | Link |
|--------|------|
| Root cause | [ranking-calibration-root-cause.md](../../ranking-calibration-root-cause.md) |
| Score compression | [score-compression-analysis.md](../../score-compression-analysis.md) |
| Reliability | [rank-reliability-report.md](../../rank-reliability-report.md) |
| Calibration research | [calibrated-ranking-research.md](../../calibrated-ranking-research.md) |

**PO gate:** No ranking v2 in production without explicit approval.

---

## Constraints

- Must not filter universe (universe layer only).
- Must not call LLMs.
- Version string stored on `ranking_runs.strategy_version`.

Legacy: [architecture.md](../../architecture.md), [sprint4-implementation-plan.md](../../sprint4-implementation-plan.md).
