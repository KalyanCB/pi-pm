# QRC Evidence Model Redesign

## Executive Summary

QRC confidence was flat across all Top-20 stocks because `_build_qrc_diagnostics` in `app/args/plugins/qrc.py` scored every packet with the same packet-level rubric (`compute_validation_coverage`, `compute_sample_quality`, regime row count, exit row count). Those inputs are strategy/run-level and identical for every symbol in a batch.

This redesign separates **Historical Evidence Quality (A)** from **Current Signal Validation (B)** and introduces a per-stock `quant_research_brief` with SEE-weighted deterministic confidence.

## Architecture

```text
InvestmentReviewPacket.payload (per stock)
  ├── validation                         [run-level, often pending]
  ├── historical_validation_context      [run-level, shared]
  ├── quant_evidence.factor_ic           [strategy-level, shared]
  ├── quant_evidence.exit_research       [strategy-level, shared]
  ├── regime.strategy_regime_performance [strategy-level, shared]
  └── stock_setup_evidence               [STOCK-SPECIFIC — primary differentiator]

build_quant_research_brief(packet, symbol)
  ├── historical_strategy_assessment     (20% weight)
  ├── current_regime_assessment          (15% weight)
  ├── factor_assessment                  (15% weight)
  ├── see_assessment                     (45% weight)
  ├── validation_status                  (5% informational; pending = neutral 0.50)
  └── overall_quant_confidence           (0.15–0.95, varies per stock)

build_qrc_user_payload → LLM (brief + summaries, no raw factor/SEE dumps)
QrcCommitteePlugin → confidence = brief.overall_quant_confidence (deterministic)
```

## Evidence Hierarchy (When Current Validation Is Pending)

| Priority | Source | Role |
|----------|--------|------|
| 1 | `historical_validation_context.recent_completed_validations` | Strategy hit rate, decile spread, rank IC, sample size |
| 2 | `regime.strategy_regime_performance` | Current regime avg IC/spread, sample count |
| 3 | `quant_evidence.factor_ic` (summarized) | Top +/- factors, stability, aggregate quality |
| 4 | `stock_setup_evidence` | **Primary stock differentiator**: score, matches, win rate, returns |
| 5 | `validation.status` | Display only; pending/insufficient_data never penalizes |

## Implicit Pending Penalties Removed

| Location | Prior behavior | Fix |
|----------|----------------|-----|
| `_build_qrc_diagnostics` | `coverage_score = validation_coverage / 100` — identical across stocks when pending | Replaced with brief component scores; SEE varies per stock |
| `compute_validation_coverage` | Still packet-level (used for diagnostics display only) | No longer drives confidence |
| `compute_sample_quality` | Exit-research sample sizes identical per batch | Retained for extensions; not in confidence formula |
| `compute_regime_reliability` | Row-count label identical per batch | Retained for extensions; regime *fit* uses current-regime IC/spread |
| LLM rubric prompt | "validation_coverage 35%" encouraged flat scoring | Prompt now references `quant_research_brief.overall_quant_confidence` |
| Raw payload dumps | LLM saw identical validation/decile/horizon blocks | Removed; brief summarizes per section |

## Confidence Formula

Deterministic weights (no new DB tables):

| Component | Weight | Score inputs |
|-----------|--------|--------------|
| SEE | 45% | `setup_evidence_score`, qualifying matches, win rate, avg return |
| Historical strategy | 20% | rank IC, decile spread, hit rate, sample size from latest completed validation |
| Regime fit | 15% | current-regime `avg_ic`, `avg_spread`, `sample_count` |
| Factor quality | 15% | avg \|IC\|, stability scores |
| Validation status | 5% | 0.50 neutral when pending; 0.85 when completed |

Output clamped to `[0.15, 0.95]`.

## Before / After — QRC Confidence Dispersion

### Breakout (`2026-06-02`, Top 20)

| Run | Run ID | Min | Max | Mean | Std | Unique values |
|-----|--------|-----|-----|------|-----|---------------|
| **Before** | `dd5aa350-17a7-4f0a-888d-1ab6529a7a48` | 0.93 | 0.93 | 0.93 | 0.0000 | 1 |
| **After** | `575a4dd8-ddf1-42a2-bcb8-ea154c64eab9` | 0.62 | 0.73 | 0.68 | 0.0298 | 10 |

Per-symbol (after):

| Symbol | QRC confidence | SEE score |
|--------|----------------|-----------|
| LAURUSLABS.NS | 0.73 | 77.38 |
| WOCKPHARMA.NS | 0.71 | 71.54 |
| ADANIENSOL.NS | 0.71 | — |
| WELCORP.NS | 0.71 | — |
| HONASA.NS | 0.70 | — |
| SOLARINDS.NS | 0.70 | — |
| TRITURBINE.NS | 0.70 | — |
| HFCL.NS | 0.68 | 62.89 |
| VIJAYA.NS | 0.68 | — |
| ZYDUSLIFE.NS | 0.68 | — |
| GRANULES.NS | 0.69 | — |
| NEULANDLAB.NS | 0.69 | — |
| RRKABEL.NS | 0.67 | — |
| TATATECH.NS | 0.67 | — |
| AIAENG.NS | 0.66 | — |
| OFSS.NS | 0.64 | — |
| THERMAX.NS | 0.65 | — |
| NSLNISP.NS | 0.65 | — |
| ATGL.NS | 0.62 | 58.63 |
| GLAND.NS | 0.62 | — |

### Momentum (`2026-06-02`, Top 20)

| Run | Run ID | Min | Max | Mean | Std | Unique values |
|-----|--------|-----|-----|------|-----|---------------|
| **Before** | `aae04acf-dfa6-48c3-98ea-e9eff1093520` | 0.86 | 0.86 | 0.86 | 0.0000 | 1 |
| **After** | `485c79fa-f1cf-4a70-91ab-52dd6860ce91` | 0.61 | 0.72 | 0.67 | 0.0277 | 8 |

Per-symbol (after):

| Symbol | QRC confidence |
|--------|----------------|
| LAURUSLABS.NS | 0.72 |
| NEULANDLAB.NS | 0.70 |
| POWERINDIA.NS | 0.70 |
| HONASA.NS | 0.68 |
| RRKABEL.NS | 0.68 |
| SAREGAMA.NS | 0.68 |
| TRITURBINE.NS | 0.68 |
| VIJAYA.NS | 0.68 |
| WOCKPHARMA.NS | 0.68 |
| SOLARINDS.NS | 0.69 |
| HFCL.NS | 0.67 |
| ZYDUSLIFE.NS | 0.67 |
| TATATECH.NS | 0.66 |
| TEJASNET.NS | 0.66 |
| THERMAX.NS | 0.66 |
| ATGL.NS | 0.61 |
| SCHNEIDER.NS | 0.61 |
| ENRIN.NS | 0.64 |
| GLAND.NS | 0.64 |
| NSLNISP.NS | 0.64 |

## Files Changed

| File | Change |
|------|--------|
| `app/args/plugins/quant_research_brief.py` | **New** — `build_quant_research_brief()` with 5 assessment sections + weighted confidence |
| `app/args/plugins/quant_payload.py` | `build_qrc_user_payload()` uses brief; removes raw factor/SEE/horizon dumps |
| `app/args/plugins/qrc.py` | Confidence from brief; prompt references brief sections; extensions include `quant_research_brief` |
| `tests/unit/args/test_quant_research_brief.py` | **New** — dispersion + pending-neutral tests |
| `tests/unit/args/test_quant_payload.py` | Updated for brief-based payload |
| `docs/qrc-evidence-model-redesign.md` | This document |
| `docs/args-breakout-2026-06-02-qrc-redesign.md` | Exported new breakout run |
| `docs/args-momentum-2026-06-02-qrc-redesign.md` | Exported new momentum run |

## Remaining Gaps

1. **Shared strategy-level evidence** — historical validation, factor IC, regime performance, and exit research remain identical across all 20 stocks; only SEE (and brief weighting) differentiates confidence today.
2. **Absolute confidence range** — post-redesign mean ~0.67–0.68 with std ~0.03; stronger SEE differentiation or stock-level validation would widen spread further.
3. **`validation_coverage` extension** — still packet-level and uniform; retained for transparency but not used in confidence.
4. **LLM narrative** — findings may still echo shared strategy evidence; confidence is now deterministic and stock-specific regardless.

## Recommendations (Out of Scope for This Change)

- Attach per-stock ranking validation slices when available (would add stock-level historical quality).
- Surface stock-specific factor exposures in the brief when factor attribution exists in packets.
- Consider decoupling governance confidence from committee LLM confidence for QRC now that quant confidence is deterministic.
- Monitor SEE coverage: stocks with `status=insufficient_data` cluster near the neutral SEE floor (~0.42 component → lower overall confidence).

## Exports

```bash
.venv/bin/python scripts/export_args_research_run.py 575a4dd8-ddf1-42a2-bcb8-ea154c64eab9 -o docs/args-breakout-2026-06-02-qrc-redesign.md
.venv/bin/python scripts/export_args_research_run.py 485c79fa-f1cf-4a70-91ab-52dd6860ce91 -o docs/args-momentum-2026-06-02-qrc-redesign.md
```
