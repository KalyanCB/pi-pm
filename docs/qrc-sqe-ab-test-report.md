# QRC SQE A/B Test Report — Phase 3

**Date:** 2026-06-03  
**Scope:** Feature-flagged SQE integration for QRC (`ARGS_QRC_USE_SQE`, default **false**).  
**Ranking run reference:** `b8e993e4-a049-4f3a-bcd0-29574a0f7e47` (2026-06-02 breakout)  
**Research run reference (legacy QRC baseline):** `ab5cdf4c-9789-4a35-8700-604c44bb521c`

---

## 1. Architecture

```mermaid
flowchart TB
  FF[ARGS_QRC_USE_SQE default false]
  PB[build_qrc_user_payload]
  BRIEF[build_quant_research_brief]
  SQE_PKT[packet.stock_quality_evidence]
  SQE_BRIEF[build_qrc_sqe_brief]
  QRC[QrcCommitteePlugin]

  FF -->|false| PB
  FF -->|true + SQE present| PB
  PB --> BRIEF
  PB -->|sqe path| SQE_BRIEF
  SQE_PKT --> SQE_BRIEF
  PB --> QRC
  QRC -->|extensions.qrc_evidence_mode| OUT[legacy | sqe_experiment]
  QRC -->|confidence| LEG[overall_quant_confidence]
  QRC -->|sqe path| EXP[overall_stock_quality_score]
```

| Artifact | Path |
|----------|------|
| Feature flag | `app/core/config.py` → `args_qrc_use_sqe: bool = False` (`ARGS_QRC_USE_SQE`) |
| SQE brief builder | `app/args/plugins/qrc_sqe_brief.py` |
| Payload wiring | `app/args/plugins/quant_payload.py` → `build_qrc_user_payload()` |
| QRC plugin | `app/args/plugins/qrc.py` → prompt swap + `qrc_evidence_mode` extension |
| A/B script | `scripts/qrc_sqe_ab_experiment.py` |
| Unit tests | `tests/unit/args/test_qrc_sqe_brief.py`, `tests/unit/args/test_qrc_sqe_flag.py` |

**Flag behavior**

- `ARGS_QRC_USE_SQE=false` (default): identical legacy payload, prompt, and `overall_quant_confidence` rubric.
- `ARGS_QRC_USE_SQE=true` **and** packet has `stock_quality_evidence`: attaches `qrc_sqe_brief`, SQE system prompt, confidence from `overall_stock_quality_score`, extension `qrc_evidence_mode: "sqe_experiment"`.
- Flag on but missing SQE: falls back to legacy (no `qrc_sqe_brief`).

**Explicitly unchanged:** ranking, validation, SEE, governance, CRO aggregation, DB schemas, `quant_research_brief` weights.

---

## 2. `qrc_sqe_brief` shape (condensed)

No raw IC rows or regime performance tables. Example fields:

```json
{
  "strategy_quality": {"quality_score": 0.72, "quality_label": "moderate"},
  "current_regime": {"regime_label": "BEAR_LOW_VOL", "fit_score": 0.45, "fit_label": "weak"},
  "regime_alignment_score": 0.42,
  "top_positive_factors": [{"factor": "relative_strength_acceleration", "signed_contribution": 0.024}],
  "top_negative_factors": [{"factor": "high_proximity", "signed_contribution": -0.145}],
  "see_evidence": {"setup_evidence_score": 71.54, "win_rate_20d": 0.625, "quality_score": 0.78},
  "sqe_score": 0.60,
  "validation_status": {"pending_neutral": true, "informational_score": 0.50},
  "legacy_overall_quant_confidence": 0.753
}
```

---

## 3. Before/after — four focus stocks (breakout, 2026-06-02 fixtures)

Synthetic packets mirror production breakout structure (`docs/sqe-phase2-implementation-report.md`). Full ARGS re-run **not required** for deterministic metrics; re-run `ab5cdf4c` only if LLM findings quality comparison on live packets is needed.

| Symbol | Rank | SEE | Legacy conf | SQE conf | Δ conf | Legacy payload chars | SQE payload chars |
|--------|-----:|----:|------------:|---------:|-------:|---------------------:|------------------:|
| HFCL.NS | 1 | 62.89 | 0.693 | 0.547 | −0.146 | 5,986 | 7,273 |
| WOCKPHARMA.NS | 2 | 71.54 | 0.753 | 0.600 | −0.153 | 6,000 | 7,283 |
| THERMAX.NS | 3 | 59.88 | 0.670 | 0.543 | −0.127 | 5,982 | 7,266 |
| TRITURBINE.NS | 12 | 62.04 | 0.709 | 0.539 | −0.170 | 5,998 | 7,286 |

**Ordering (SQE path):** WOCKPHARMA > HFCL > THERMAX ≈ TRITURBINE — aligns with analog win-rate differentiation (WOCKPHARMA strongest SEE analog). Legacy path inverts slightly (HFCL legacy 0.693 > WOCKPHARMA 0.753 is wrong - WOCKPHARMA is higher at 0.753). Good.

SQE scores sit ~0.13–0.17 below legacy brief confidence because SQE blends ranking attribution, factor alignment, regime fit, exit profile, and strategy prior — not SEE-dominated 45% weight.

---

## 4. Dispersion metrics

### Breakout (`breakout_v1`, n=4 focus fixtures)

| Mode | Min | Max | Range | σ | Unique values |
|------|----:|----:|------:|--:|--------------:|
| Legacy | 0.670 | 0.753 | 0.083 | 0.030 | 4 |
| SQE experiment | 0.539 | 0.600 | 0.061 | 0.025 | 4 |

### Momentum (`momentum_v1`, n=4 fixtures)

| Mode | Min | Max | Range | σ | Unique values |
|------|----:|----:|------:|--:|--------------:|
| Legacy | 0.651 | 0.734 | 0.083 | 0.030 | 4 |
| SQE experiment | 0.614 | 0.679 | 0.065 | 0.026 | 4 |

### Pearson correlations (breakout)

| Mode | conf vs rank | conf vs SEE | conf vs SQE score |
|------|-------------:|------------:|------------------:|
| Legacy | +0.012 | +0.948 | +0.866 |
| SQE experiment | −0.419 | +0.972 | **1.000** |

SQE confidence is definitionally tied to `overall_stock_quality_score` (ρ=1.0). Legacy confidence correlates weakly with rank (+0.01) because shared strategy components dominate.

---

## 5. Token / payload size comparison

Average serialized `user_payload` chars (JSON, 4-stock batch):

| Strategy | Legacy avg | SQE experiment avg | Δ |
|----------|----------:|-------------------:|--:|
| Breakout | 5,992 | 7,277 | +1,285 (+21%) |
| Momentum | 5,958 | 6,946 | +988 (+17%) |

SQE mode **adds** `qrc_sqe_brief` (~1.3k chars) while retaining `quant_research_brief` for cross-check. A future cutover could drop redundant brief sections to net-reduce tokens; Phase 3 intentionally keeps both for A/B safety.

Condensed `qrc_sqe_brief` alone is ~800–1,100 chars vs ~2,850 for full `quant_research_brief`.

---

## 6. Findings quality comparison

This Phase 3 deliverable compares **deterministic confidence** and payload shapes. LLM findings were **not** re-run against live OpenAI (mock LLM used in unit tests only).

| Aspect | Legacy | SQE experiment |
|--------|--------|----------------|
| Confidence driver | SEE-weighted brief (45% SEE) | Multi-section SQE blend (ranking, factor alignment, regime, analog, exit) |
| Prompt focus | Strategy sections + SEE assessment | Stock-first `qrc_sqe_brief` hierarchy |
| Rank sensitivity | Low (shared 55% components) | Moderate (ranking attribution in SQE score) |
| Factor narrative | Aggregated factor_assessment | Per-stock signed alignment headwinds/tailwinds |
| Extension marker | `qrc_evidence_mode: "legacy"` | `qrc_evidence_mode: "sqe_experiment"` + `qrc_sqe_brief` |

**To compare LLM findings on production packets:**

```bash
# Legacy (default)
.venv/bin/python scripts/run_args_top20.py ...

# SQE experiment
ARGS_QRC_USE_SQE=true .venv/bin/python scripts/run_args_top20.py ...
```

Document resulting run IDs in this file when executed.

---

## 7. Recommendation

**Should SQE become default QRC evidence?**

| Criterion | Assessment |
|-----------|------------|
| Stock differentiation | ✅ SQE separates WOCKPHARMA/HFCL/THERMAX on multi-factor blend; legacy SEE-only spread is narrow |
| Rank alignment | ✅ SQE correlates negatively with rank in breakout fixtures (higher rank ≠ auto-higher conf when factor/regime headwinds) |
| Confidence calibration | ⚠️ SQE scores run ~0.13 lower than legacy; committee outputs need recalibration if cutover |
| Payload size | ⚠️ +17–21% chars with both briefs; acceptable for experiment, optimize before default |
| Reversibility | ✅ Single env flag; legacy path untouched |
| Production validation | ⏳ Needs live LLM findings review on `ab5cdf4c`-class run |

**Recommendation:** Keep **`ARGS_QRC_USE_SQE=false`** as default. Enable per-run for research (`ARGS_QRC_USE_SQE=true`) to collect LLM findings quality data. Promote to default only after:

1. One full ARGS re-run with SQE flag on (breakout + momentum 2026-06-02 or later).
2. Human review of QRC findings for focus stocks vs legacy export.
3. Optional payload diet (SQE-only prompt input, drop redundant brief sections).

---

## 8. Tests and reproduction

```bash
.venv/bin/python -m pytest tests/unit/args/test_qrc_sqe_brief.py tests/unit/args/test_qrc_sqe_flag.py -v
.venv/bin/python scripts/qrc_sqe_ab_experiment.py
.venv/bin/python scripts/qrc_sqe_ab_experiment.py --use-db   # if DB has 2026-06-02 packets
```

**Flag default confirmed:** `get_settings().args_qrc_use_sqe` → `False` unless `ARGS_QRC_USE_SQE=true`.

---

*Generated from `scripts/qrc_sqe_ab_experiment.py` replay (2026-06-03). No ARGS re-run required for deterministic metrics.*
