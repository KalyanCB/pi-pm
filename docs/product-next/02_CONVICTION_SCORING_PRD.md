# Conviction Scoring — Product Requirements

**Version:** Phase 2.1 (PO sign-off 2026-06-04)  
**Date:** 2026-06-05  
**Constraint:** **100% deterministic** — no LLM, no committee vote, no ARGS override.

---

## 1. Purpose

Provide a single **0–100 conviction score** and **band** per stock per recommendation run so the UI, mobile, and human queue can sort within the top pool without implying rank #1 > rank #10 ([ranking-calibration-root-cause.md](../ranking-calibration-root-cause.md)).

Conviction is an **input** to the Recommendation Engine ([01_RECOMMENDATION_ENGINE_PRD.md](./01_RECOMMENDATION_ENGINE_PRD.md)), not a replacement for ranking.

---

## 2. Design principles

| Principle | Rationale |
|-----------|-----------|
| Reproducible | Same inputs + `conviction_config_version` → same score |
| Explainable | Decomposed sub-scores stored JSON-sidecar |
| Conservative with bad data | `insufficient_data` validation caps score |
| Rank-pool not rank-precision | Favor bucket membership over raw rank until calibration promoted |
| **Committee-neutral (mandatory)** | ARGS / committee outputs are **stored, displayed, and explained only** — they **must not** affect `conviction_score`, `conviction_band`, or `recommendation_action` ([PO_SIGNOFF_2026_06_04.md](./PO_SIGNOFF_2026_06_04.md)) |

---

## 3. Score bands

| Band | Score range | Typical recommendation cap |
|------|-------------|------------------------------|
| `BLOCKED` | 0–29 | `REJECT` or `WATCH` only |
| `LOW` | 30–49 | `WATCH` |
| `MEDIUM` | 50–69 | `WATCH` or `BUY` if slots |
| `HIGH` | 70–84 | `BUY` candidate |
| `EXCEPTIONAL` | 85–100 | `BUY` priority queue (max 3/day PO default) |

PO may tune thresholds in `recommendation_config`.

---

## 4. Formula (v1.1 — deterministic, no committee)

**Conviction raw** is a weighted sum of **five** normalized sub-scores (each 0–100), then clamped. Weights were renormalized after PO removal of committee influence (sum = 1.0):

```
conviction_score = clamp(round(
  0.26 * S_rank_quality
+ 0.32 * S_validation
+ 0.16 * S_ic_factor
+ 0.16 * S_regime
+ 0.10 * S_exit_health
), 0, 100)
```

**Forbidden inputs:** `S_committee_consensus`, ARGS labels, CRO narrative, any LLM output.

### 4.1 S_rank_quality — Ranking Quality (0–100)

| Signal | Calculation | Evidence |
|--------|-------------|----------|
| Pool membership | 100 if rank ≤ 20 else linear decay to 0 at rank 50 | Top-20 alpha [outcome-attribution](../outcome-attribution-report.md) |
| Rank position penalty | If `rank_v2_promoted=false`: `100 - min(rank,5)*8` for rank 1–5 | Inversion guard [po-discovery 10](../po-discovery/10_RECOMMENDATION_ENGINE_GAP_ANALYSIS.md) |
| Score separation | Percentile of `composite_score` within top-20 | Compression note [score-compression-analysis.md](../score-compression-analysis.md) |
| Calibrated overlay | If PO promotes `ranking_research/calibration.py`: use calibrated percentile | Research-only today |

**Default v1:** `S_rank_quality = 0.6 * pool_score + 0.4 * separation_score - rank_penalty`

### 4.2 S_validation — Validation Strength (0–100)

| `ranking_validation_reports.status` | Score |
|-------------------------------------|-------|
| `completed` | Map 20d Spearman IC: `ic ≤ 0 → 20`; `0–0.05 → 50`; `>0.05 → 80`; cap +10 if top-decile spread positive |
| `insufficient_data` | **Fixed 35** — matches QRC brief behavior ([`quant_research_brief.py:369`](../../app/args/plugins/quant_research_brief.py)) |

Uses horizons from [`app/validation/`](../../app/validation/) — 5/10/20/60.

### 4.3 S_ic_factor — Factor Analytics (0–100)

Latest `factor_performance_metrics` for strategy:

| Condition | Score |
|-----------|-------|
| Factor IC median > 0.03 | 80 |
| 0–0.03 | 55 |
| Negative | 30 |
| Missing run | 50 (neutral) |

Source: [FACTOR_IC_DESIGN.md](../AI/03_DESIGN/FACTOR_IC_DESIGN.md).

### 4.4 S_regime — Regime Alignment (0–100)

From `regime_policy_decisions` / observability current regime:

| Regime posture | Score |
|----------------|-------|
| Risk-on (allow new) | 75 |
| Neutral | 55 |
| Defensive / reduce | 25 |

Source: [REGIME_DESIGN.md](../AI/03_DESIGN/REGIME_DESIGN.md) — post-ranking policy only.

### 4.5 S_exit_health — Exit Health (0–100)

| Position state | Score |
|----------------|-------|
| No position (entry) | 70 default |
| ACTIVE, no deterioration | 80 |
| ACTIVE, rank deterioration trigger | 20 |
| ACTIVE, alpha decay trigger | 15 |

Feeds from [07_EXIT_DECISION_FRAMEWORK.md](./07_EXIT_DECISION_FRAMEWORK.md).

---

## 5. Committee outputs (display only)

| Allowed | Forbidden |
|---------|-----------|
| Store committee labels and narratives on ARGS / packet | Use labels in conviction formula |
| Show in UI next to conviction breakdown | Map labels to conviction sub-scores |
| Copilot cites committee text with evidence refs | Change `conviction_score`, `conviction_band`, or `action` based on committee |

See [08_AI_INVESTMENT_COMMITTEE_PRD.md](./08_AI_INVESTMENT_COMMITTEE_PRD.md) and [16_RECOMMENDATION_PERFORMANCE_PRD.md](./16_RECOMMENDATION_PERFORMANCE_PRD.md) for **measurement** of committee effectiveness (post-hoc only).

---

## 6. Versioning

| Artifact | Field |
|----------|-------|
| Config blob | `conviction_config_version` e.g. `conv_v1.1.0` (no committee weight) |
| Stored on | `recommendation_runs`, each `recommendation_results.conviction_components` |

Weight changes require PO sign-off + backtest note (same gate as ranking v2).

---

## 7. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC-CS-01 | Golden fixture: fixed ranking+validation inputs → exact integer score |
| AC-CS-02 | `insufficient_data` never produces band ≥ `MEDIUM` |
| AC-CS-03 | Rank 1–5 with `rank_v2_promoted=false` never produces `EXCEPTIONAL` |
| AC-CS-04 | API returns `conviction_components` JSON for explain panel (five sub-scores only) |
| AC-CS-05 | No OpenAI/LLM import in conviction module (lint rule) |
| AC-CS-06 | Changing committee text or labels does **not** alter score or band |
| AC-CS-07 | `conviction_components` JSON has **no** committee keys |

---

## 8. UX requirements

- Show **band** + **numeric** + **top 3 reason sub-scores** (deterministic factors only).
- Badge “Validation pending” when `S_validation=35`.
- Tooltip: “Conviction is not a buy guarantee.”
- Committee summary in separate panel — visually distinct from conviction meter.

---

## 9. PO decisions required

| # | Question | Default (post sign-off) |
|---|----------|-------------------------|
| 1 | Promote calibration into S_rank_quality? | No until v2 gate |
| 2 | Include committee in conviction? | **No — removed 2026-06-04** |
| 3 | EXCEPTIONAL daily cap | 3 |
| 4 | Block band threshold | 29 |

---

## 10. References

- [PO_SIGNOFF_2026_06_04.md](./PO_SIGNOFF_2026_06_04.md)
- [10_RECOMMENDATION_ENGINE_GAP_ANALYSIS.md](../po-discovery/10_RECOMMENDATION_ENGINE_GAP_ANALYSIS.md) § Conviction
- [RANKING_DESIGN.md](../AI/03_DESIGN/RANKING_DESIGN.md)
- [app/ranking_research/calibration.py](../../app/ranking_research/calibration.py) (not in prod)
- [ADR-021-Recommendation-Platform-Architecture.md](../architecture/ADR-021-Recommendation-Platform-Architecture.md)
