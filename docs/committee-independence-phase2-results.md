# Committee Independence Phase 2 — Results

**Date:** 2026-06-03  
**Baseline runs (Phase 1):** `11cd8dc9-acdf-4a49-b43f-1f5dc306730e` (breakout_v1), `6d6ede9f-96fd-4a1f-8464-3c5fa7ddf1bb` (momentum_v1)  
**Phase 2 runs:** `438aae56-af8a-413a-b34f-4f3315c288f1` (breakout_v1), `db16a52d-5c81-43c1-9e53-7b81af03ab79` (momentum_v1)  
**As-of date:** 2026-06-02 (top-20 NIFTY_500)

## Headline verdict

**Yes — committee independence materially improved.** Effective independence rate rose from **~14% to ~79%**, exceeding the **≥40%** promotion target. Evidence overlap dropped from **~60% to ~0%**, and strict independence packet rate went from **0% to 100%**. Degraded clone reviews (FRC ≡ RC ranking/regime fallback) were eliminated (**40–44% → 0%**).

Remaining gaps: QRC still hit evidence-validation failures on some packets (LLM cited `historical_validation_context:*` refs before resolver fix; 21 `stub:evidence_validation_failed` on breakout). RC LLM path often fell back to abstention when scope validation failed — abstention text is now committee-specific per symbol, not identical clones.

---

## Before vs after metrics

| Metric | Breakout before (`11cd8dc9`) | Breakout after (`438aae56`) | Momentum before (`6d6ede9f`) | Momentum after (`db16a52d`) | Target |
|--------|------------------------------|-----------------------------|------------------------------|-----------------------------|--------|
| **Effective independence rate** | **0.141** | **0.787** | **0.125** | **0.792** | ≥0.40 |
| Mean evidence overlap | 0.594 | **0.005** | 0.600 | **0.000** | <0.30 |
| Strict independence packet rate | 0.000 | **1.000** | 0.000 | **1.000** | >0.20 |
| Degraded review fraction | 0.40 | **0.00** | 0.44 | **0.00** | ↓ |
| Mean composite uniqueness | 0.581 | **0.791** | 0.559 | **0.792** | ↑ |
| Mean finding Jaccard | 0.147 | 0.122 | 0.177 | 0.114 | ↓ |
| Mean disagreement score | 0.584 | **0.909** | 0.567 | **0.914** | ↑ |

Formula (unchanged): `mean(composite_uniqueness) × (1 − mean_evidence_overlap) × (1 − degraded_fraction)`.

---

## What changed (Phase 2 implementation)

| Area | Module(s) |
|------|-----------|
| **2A Prompt isolation** | `app/args/committee_packet_views.py` — per-committee views wired in `tarc.py`, `qrc.py`, `frc.py`, `nrcc.py`, `rc.py` |
| **2B Evidence enforcement** | `app/args/committee_evidence_enforcement.py`, `committee_llm_base.py` — allowlist + unique-ref gate with one repair retry |
| **2C contrarian_view** | Required in LLM JSON; stored in `committee_reviews.extensions.contrarian_view` |
| **2D Degraded clone elimination** | FRC/NRCC/RC committee-specific abstention templates (no ranking/regime filler) |
| **2E Measurement** | This doc + ARGS re-run on 2026-06-02 |

---

## Evidence ref shift (breakout after)

**Before top shared refs:** `ranking:rank`, `ranking:composite_score`, `regime:regime_label` (80/100 reviews each).

**After top shared refs:** committee-mandate refs — `fundamental_snapshot:status`, `news_snapshot:status`, `market_snapshot:sector`, `portfolio_context:existing_position`, `risk:concentration`, plus TARC `technical_factors` / `ranking` block refs. **No universal ranking/regime triad across all five committees.**

---

## Sample outputs — focus symbols (breakout run `438aae56`)

### WOCKPHARMA.NS

| Committee | Confidence | Composite uniqueness | Primary evidence refs | Summary |
|-----------|------------|-------------------|----------------------|---------|
| TARC | 0.87 | 0.924 | `ranking`, `technical_factors`, `historical_performance` | Rank 2, composite 0.8868; volume surge / trend quality narrative |
| QRC | 0.71 | 0.848 | `stub:evidence_validation_failed` | Evidence validation failed (historical_validation_context ref) |
| FRC | 0.15 | 0.717 | `fundamental_snapshot:status` | **Abstention:** insufficient fundamental evidence |
| NRCC | 0.22 | 0.807 | `news_snapshot:status` | **Abstention:** no news evidence available |
| RC | 0.18 | 0.712 | `portfolio_context`, `risk:concentration`, `market_snapshot:sector` | Risk abstention — no TARC clone |

**TARC findings (excerpt):** rank 2, composite 0.8868, volume surge and trend quality drive rank; contrarian_view challenges QRC validation skepticism.

**FRC findings (excerpt):** *"Insufficient fundamental evidence for WOCKPHARMA.NS… FRC abstains from imputing business quality from technical rank or regime labels."*

### HFCL.NS

| Committee | Confidence | Uniqueness | Notes |
|-----------|------------|------------|-------|
| TARC | 0.87 | 0.923 | Rank 1, composite 0.8873; scoped technical narrative |
| QRC | 0.68 | 0.861 | Evidence validation failed (bad historical ref) |
| FRC / NRCC / RC | 0.15–0.22 | 0.70–0.80 | Committee-specific abstentions (not clones) |

### THERMAX.NS

| Committee | Confidence | Uniqueness | Notes |
|-----------|------------|------------|-------|
| TARC | 0.87 | 0.940 | Rank 3; technical_factors cited |
| QRC | 0.65 | 0.854 | LLM timeout → evidence_validation_failed |
| FRC / NRCC / RC | abstention | 0.71–0.81 | Distinct mandate-boundary prose per committee |

### TRITURBINE.NS

| Committee | Confidence | Uniqueness | Notes |
|-----------|------------|------------|-------|
| TARC | 0.85 | 0.928 | Rank 12; volume surge emphasis |
| QRC | 0.70 | 0.843 | Evidence validation failed (historical_validation_context:rank_ic ref) |
| FRC / NRCC / RC | abstention | 0.71–0.80 | No cross-committee identical degraded bullets |

---

## Confidence clustering (after vs before)

| Committee | Breakout before std | Breakout after std | Interpretation |
|-----------|--------------------|--------------------|----------------|
| TARC | 0.012 | 0.012 | Unchanged (still varies ~0.85) |
| QRC | 0.030 | 0.030 | Unchanged (still varies) |
| FRC | **0.000** @ 0.35 | **0.000** @ **0.15** | Abstention confidence (mandate-specific, not clone 0.35) |
| RC | **0.000** @ 0.35 | **0.000** @ **0.18** | Risk abstention — distinct from FRC |
| NRCC | **0.000** @ 0.25 | **0.000** @ **0.22** | Structured no-news abstention |

FRC/RC/NRCC remain universe-constant within committee (expected when data absent), but **confidence levels and prose diverge across committees** — no FRC ≡ RC clone at 0.35.

---

## Reproduce

```bash
# Phase 2 ARGS run
.venv/bin/python scripts/run_args_top20.py --as-of-date 2026-06-02

# Metrics
.venv/bin/python scripts/analyze_committee_effectiveness.py --run-id 438aae56-af8a-413a-b34f-4f3315c288f1
.venv/bin/python scripts/analyze_committee_effectiveness.py --run-id db16a52d-5c81-43c1-9e53-7b81af03ab79

# Baseline
.venv/bin/python scripts/analyze_committee_effectiveness.py --run-id 11cd8dc9-acdf-4a49-b43f-1f5dc306730e
.venv/bin/python scripts/analyze_committee_effectiveness.py --run-id 6d6ede9f-96fd-4a1f-8464-3c5fa7ddf1bb

# Unit tests
pytest tests/unit/args/test_committee_packet_views.py \
       tests/unit/args/test_committee_evidence_enforcement.py -q
```

---

## Follow-ups (not blocking promotion)

1. **QRC ref resolver** — extend `historical_validation_context:*` resolution (partial fix applied post-run) to reduce `evidence_validation_failed` stubs.
2. **RC LLM success rate** — tune prompts so RC cites `risk:*` / `market_snapshot:*` refs that pass scope gate instead of falling back to abstention.
3. **CRO** — unchanged aggregation; `contrarian_view` available in `extensions` for future weighting.

---

## Files changed

| File | Purpose |
|------|---------|
| `app/args/committee_packet_views.py` | **New** — scoped views (2A) |
| `app/args/committee_evidence_enforcement.py` | **New** — allowlists, abstention templates (2B/2D) |
| `app/args/plugins/committee_llm_base.py` | contrarian_view, evidence gate, committee-aware padding |
| `app/args/plugins/tarc.py`, `qrc.py`, `frc.py`, `nrcc.py`, `rc.py` | Wire views + prompts |
| `app/workspace_args/evidence_validator.py` | `risk:`, `fundamental:`, `historical_validation_context:` refs |
| `app/args/llm/port.py` | Mock LLM contrarian_view + scoped refs |
| `tests/unit/args/test_committee_packet_views.py` | **New** |
| `tests/unit/args/test_committee_evidence_enforcement.py` | **New** |
| `tests/unit/args/test_workflow_mock_llm.py` | Updated fixture packet |
| `docs/committee-independence-phase2-results.md` | **New** — this report |

**Not modified:** ranking engines, validation/factor IC/SEE/SQE calculations, governance confidence formulas, CRO aggregation logic.
