# QRC SQE vs Legacy — Live OpenAI Evaluation (2026-06-02)

**Date:** 2026-06-03  
**Ranking as-of:** 2026-06-02 (NIFTY_500 breakout + momentum)  
**LLM:** OpenAI `gpt-4o-mini` via `ARGS_LLM_PROVIDER=openai`  
**Flag:** `ARGS_QRC_USE_SQE` — default remains **false** (`get_settings().args_qrc_use_sqe == False`)

---

## 1. Research run IDs (4 runs)

| Mode | Strategy | Research run ID | Export |
|------|----------|-----------------|--------|
| Legacy (`ARGS_QRC_USE_SQE=false`) | breakout_v1 | `3faf591f-e558-46cc-bb0e-913542a7e6e4` | [args-legacy-breakout-2026-06-02.md](./args-legacy-breakout-2026-06-02.md) |
| Legacy | momentum_v1 | `0fe26a2c-705a-4941-967c-9b88b763f50a` | [args-legacy-momentum-2026-06-02.md](./args-legacy-momentum-2026-06-02.md) |
| SQE (`ARGS_QRC_USE_SQE=true`) | breakout_v1 | `02ddf3ac-ba68-499b-a84e-b9507da92a53` | [args-sqe-breakout-2026-06-02.md](./args-sqe-breakout-2026-06-02.md) |
| SQE | momentum_v1 | `bf534985-a179-4a66-a008-c3efd06ce751` | [args-sqe-momentum-2026-06-02.md](./args-sqe-momentum-2026-06-02.md) |

**Ranking run IDs (shared):** breakout `b8e993e4-a049-4f3a-bcd0-29574a0f7e47`, momentum `097bddfe-1cb3-4073-b00b-bfd056040115`.

**Commands used:**

```bash
cd /Users/kalyancb/pi-pm
# Docker DB: docker compose -f docker/docker-compose.yml up -d db

ARGS_QRC_USE_SQE=false .venv/bin/python scripts/run_args_top20.py --as-of-date 2026-06-02
ARGS_QRC_USE_SQE=true  .venv/bin/python scripts/run_args_top20.py --as-of-date 2026-06-02
```

All four runs completed (`status=completed`, 20 candidates, 20 governance reports each). Full exports include committee reviews (QRC/TARC/FRC/RC/NRCC), CRO, and governance sections.

---

## 2. Token usage and estimated cost

Aggregated from `llm_execution_records` linked to committee + CRO reviews per run (OpenAI provider rows; degraded/mock rows have `input_tokens=0`).

| Run | Input tokens | Output tokens | Est. cost (USD)* |
|-----|-------------:|--------------:|-----------------:|
| Legacy breakout | 86,155 | 27,618 | $0.0295 |
| Legacy momentum | 83,160 | 29,206 | $0.0300 |
| SQE breakout | 103,165 | 32,487 | $0.0350 |
| SQE momentum | 93,014 | 31,422 | $0.0328 |
| **Total (4 runs)** | **365,494** | **120,733** | **~$0.127** |

\*Cost estimate: gpt-4o-mini list pricing **$0.15 / 1M input**, **$0.60 / 1M output** (approximate; excludes cached/discount tiers).

SQE adds **~+20% input tokens** on breakout (86k → 103k) from larger QRC payloads (`qrc_sqe_brief` + dual-brief context). Runtime: legacy ~21 min, SQE ~10.6 min (wall clock; variance normal).

---

## 3. Focus stocks — breakout QRC (legacy vs SQE)

Extensions: legacy → `qrc_evidence_mode: "legacy"`; SQE → `"sqe_experiment"` + `qrc_sqe_brief` (factor signed contributions, `regime_alignment_score`, SEE block).

### 3.1 Confidence and mode

| Symbol | Rank | Legacy conf | SQE conf | Δ | SQE `sqe_score` | Legacy rubric (pre-SQE) |
|--------|-----:|------------:|---------:|--:|----------------:|------------------------:|
| HFCL.NS | 1 | 0.68 | 0.58 | −0.10 | 0.577 | 0.679 |
| WOCKPHARMA.NS | 2 | 0.71 | 0.61 | −0.10 | 0.609 | 0.714 |
| THERMAX.NS | 3 | 0.65 | 0.54 | −0.11 | 0.542 | 0.648 |
| TRITURBINE.NS | 12 | 0.70 | 0.53 | −0.17 | 0.525 | 0.695 |

SQE confidence uses `overall_stock_quality_score` / `sqe_experiment` rubric, not legacy SEE-weighted `overall_quant_confidence`.

### 3.2 Findings (representative contrast)

| Symbol | Legacy QRC (lead) | SQE QRC (lead) |
|--------|-------------------|----------------|
| HFCL.NS | Opens with **shared** historical template: sample 347, rank-IC 0.1401, decile −0.0103 | Opens **stock-first**: “stands out within its ranked batch”; cites **regime_alignment_score 0.15**, **high_proximity −0.1464** |
| WOCKPHARMA.NS | Same 347 / 0.1401 / −0.0103 boilerplate | Names **high_proximity −0.1464**, **62.5% win rate** / **1.47% median** from SEE analogs |
| THERMAX.NS | Same boilerplate + generic factor IC language | **high_proximity −0.1452**, regime spread **−0.03197** |
| TRITURBINE.NS | Same boilerplate | **regime_alignment_score 0.15**, names **consolidation_breakout** / **relative_strength** in narrative |

### 3.3 Strengths / risks differentiation (breakout)

| Symbol | Legacy strengths pattern | SQE strengths pattern |
|--------|-------------------------|----------------------|
| HFCL | Regime fit 0.83; rank-IC 0.1401; exit 4.66% | Regime fit; **strategy quality 0.7325**; exit policy |
| WOCKPHARMA | Regime fit; rank-IC; exit hit rate | Regime fit; **WOCK-specific win rate 62.5%** |
| THERMAX | Historical 0.7325; regime fit; FIXED_HOLD_60 | Regime fit; **factor-level** high_proximity risk |
| TRITURBINE | Historical 0.7325; regime fit; best exit | Regime fit; flags **weak headwind** (alignment 0.15) |

| Symbol | Legacy risks pattern | SQE risks pattern |
|--------|---------------------|-------------------|
| All four | Repeated: decile −0.0103, regime IC −0.0913, “mixed factors” | **Stock-named factors** (high_proximity, relative_strength) with **signed_contribution** magnitudes |
| HFCL | Median return −3.65% (SEE) | Pending validation + factor headwinds |
| TRITURBINE | Generic decile / IC | **regime_alignment_score 0.15** explicit |

### 3.4 Supporting evidence refs

Both modes still emit the same three refs in LLM `supporting_evidence`: `ranking:rank`, `ranking:composite_score`, `regime:regime_label`. **SQE does not yet add** refs like `stock_quality_evidence:top_negative_factors` in the JSON list — attribution appears in **findings text** and **`extensions.qrc_sqe_brief`**, not new evidence ref types.

---

## 4. Focus stocks — momentum QRC (abbreviated)

| Symbol | Legacy conf | SQE conf | Notes |
|--------|------------:|---------:|-------|
| HFCL.NS | 0.67 | 0.58 | SQE stock-first narrative; conf ↓ |
| WOCKPHARMA.NS | 0.68 | 0.62 | **Legacy QRC degraded** (evidence ref validation); SQE completed with stock-specific findings |
| THERMAX.NS | 0.66 | 0.56 | **Both degraded** on SQE run (ref validation); legacy template findings |
| TRITURBINE.NS | 0.68 | 0.51 | SQE conf ↓0.17; stock-first lead |

Momentum shows the same SQE narrative pattern where QRC completes; degraded paths remain a reliability issue unrelated to SQE flag alone.

---

## 5. Evaluation questions

### 1. More stock-specific findings with SQE?

**Yes, moderately.** SQE findings routinely lead with the **symbol** and “ranked batch” framing, and cite **per-stock factor contributions** (e.g. high_proximity −0.146) and **regime_alignment_score**. Legacy breakout QRC heavily reuses **identical** historical validation sentences (sample 347, rank-IC 0.1401, decile −0.0103) across HFCL, WOCKPHARMA, THERMAX, and TRITURBINE.

### 2. Less generic strategy language?

**Partially.** SQE reduces copy-paste historical-validation paragraphs and adds SQE-brief vocabulary (alignment score, top positive/negative factors). **Residual genericness:** regime fit **0.83** and strategy quality **0.7325** still repeat across names; exit-policy **4.66% / FIXED_HOLD** still appears often.

### 3. More refs to ranking attribution, factor attribution, regime alignment, SEE?

**In narrative and extensions, not in `supporting_evidence`.**  
- **Factor attribution:** SQE findings name factors and signed contributions; `qrc_sqe_brief.top_positive_factors` / `top_negative_factors` stored in extensions.  
- **Regime alignment:** `regime_alignment_score` appears in SQE findings (e.g. 0.15 “weak headwind”).  
- **SEE:** Win rate / median return cited when analogs differ (WOCKPHARMA 62.5% vs HFCL 42.86%).  
- **Ranking attribution:** “ranked batch” phrasing; composite/rank refs unchanged in evidence list.

### 4. More differentiated strengths/risks?

**Yes for risks; mixed for strengths.** SQE risks vary by **named factors and contributions**; legacy risks cluster on decile spread and regime IC. SQE strengths still share regime-fit bullets but add stock-level SEE stats where they diverge.

### 5. Better research narratives?

**Improved specificity; lower calibrated confidence.** SQE reads more like **stock research notes**; legacy reads like **validation report templates**. Committee/governance/CRO pipelines unchanged. SQE confidence is **systematically lower** (~0.10–0.17 on focus names), aligning with pre-run fixture expectations — downstream committees should not treat SQE confidence as interchangeable with legacy without recalibration.

---

## 6. Recommendation

| Decision | Choice |
|----------|--------|
| Production default | **Keep `ARGS_QRC_USE_SQE=false`** |
| Research / experiments | **Enable per run** with `ARGS_QRC_USE_SQE=true` |
| Code change | **Do not** flip default in `app/core/config.py` |

**Rationale:** Live OpenAI run confirms SQE improves **wording differentiation** and surfaces **SQE brief signals** in QRC output, at the cost of **higher token spend**, **lower confidence scores**, and **unchanged evidence-ref schema**. Promote to default only after: (1) human sign-off on governance impact, (2) optional prompt/ref work so `supporting_evidence` cites SQE fields, (3) confidence calibration vs legacy committee thresholds.

---

## 7. Reproduction

```bash
.venv/bin/python scripts/export_args_research_run.py <run_id> -o docs/args-<label>-2026-06-02.md
```

Prior deterministic A/B: [qrc-sqe-ab-test-report.md](./qrc-sqe-ab-test-report.md) (fixture replay, no LLM).

---

*Live evaluation completed 2026-06-03. No ranking, validation, SEE, governance, or CRO logic was modified.*
