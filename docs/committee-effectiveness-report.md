# Committee Effectiveness Report (Phase 1)

**Status:** Analysis + design only. Production committee prompts and plugins unchanged.

## Objective

Prove that ARGS committees **agree too easily** (shared evidence, templated fallbacks, frozen confidence) and design **independence** for Phase 2.

## Methodology

1. Loaded latest completed runs for **2026-06-02** (`breakout_v1`, `momentum_v1`).
2. Queried `committee_reviews` and `cro_reviews` per packet (TARC, QRC, FRC, NRCC, RC, CRO).
3. Computed read-only metrics in `app/args/analytics/committee_effectiveness.py`:
   - Finding similarity (token Jaccard, sequence similarity helper)
   - Evidence overlap (ref Jaccard)
   - Confidence clustering (std, unique values per committee code)
   - Committee uniqueness (`compute_committee_uniqueness_score`)
   - Disagreement / agreement echo scores per packet

## Key findings

### 1. Low effective independence (~14%)

| Run | Effective independence rate |
|-----|----------------------------|
| breakout_v1 (`11cd8dc9-…`) | **14.1%** |
| momentum_v1 (`6d6ede9f-…`) | **~13.5%** |

Formula: `mean(composite_uniqueness) × (1 − mean_evidence_overlap) × (1 − degraded_fraction)`.

**Headline disagreement rate (recommended):** treat **effective independence ~14%** as the operational disagreement rate. Loose packet-level disagreement (threshold 0.55) is **80–100%** but misleading — it counts text variance while citations stay aligned.

### 2. Evidence echo dominates

- Mean evidence overlap **59–60%** per packet.
- **80%** of reviews share the same three refs: `ranking:rank`, `ranking:composite_score`, `regime:regime_label`.

### 3. Clone committees (40–44% of reviews)

FRC and RC consistently fail LLM structural validation and emit **degraded fallback** prose with identical strength bullets. NRCC is always news-degraded at confidence **0.25**.

### 4. Confidence clustering failure

| Committee | Std (breakout) | Interpretation |
|-----------|----------------|----------------|
| TARC | 0.012 | Narrow band ~0.85 |
| QRC | 0.030 | Some spread |
| FRC / RC / NRCC | **0.000** | **Universe-constant confidence** |

### 5. Surface narrative vs true disagreement

- Mean TARC↔QRC token Jaccard **~0.16** — paragraphs differ.
- Mean strength↔risk cross-committee Jaccard **~0.02** — little true thematic opposition.
- QRC text often challenges TARC (negative regime IC) but **without independent evidence refs**.

### 6. Strict independence: 0% of packets

No packet meets `disagreement_score ≥ 0.65` and `evidence_overlap < 0.5` simultaneously.

## Example uniqueness scores (`WOCKPHARMA.NS`, breakout run)

| Committee | overlap_with_peers | unique_evidence | composite_uniqueness |
|-----------|-------------------|-----------------|----------------------|
| NRCC | 0.007 | 1 | 0.947 |
| QRC | 0.066 | 0 | 0.677 |
| TARC | 0.072 | 0 | 0.660 |
| FRC | 0.281 | 0 | 0.329 |
| RC | 0.281 | 0 | 0.324 |

## Recommendations (Phase 2)

1. **Scope enforcement** — per-committee forbidden fields and refs (`committee-independence-design.md`).
2. **Ban cross-committee degraded clones** — FRC/RC must return “insufficient evidence” stubs, not TARC-style fallback.
3. **Unique evidence minimum** — ≥1 ref per committee not used by peers; validator rejects otherwise.
4. **Contrarian_view required** — QRC must challenge strong TARC ranks; RC must publish veto themes.
5. **Confidence calibration** — reject universe-constant confidence per committee code.
6. **Track effective_independence_rate** — promote prompts only when metric ≥ 40% on golden packets.

## Artifacts

| Artifact | Path |
|----------|------|
| Metrics module | `app/args/analytics/committee_effectiveness.py` |
| CLI analysis | `scripts/analyze_committee_effectiveness.py` |
| Unit tests | `tests/unit/args/test_committee_effectiveness.py` |
| Overlap analysis | `docs/committee-overlap-analysis.md` |
| Independence design | `docs/committee-independence-design.md` |

## Test plan (Phase 1)

```bash
pytest tests/unit/args/test_committee_effectiveness.py -q
.venv/bin/python scripts/analyze_committee_effectiveness.py
```

## Explicit non-changes

- No edits to ranking, validation, factor IC, SEE, SQE
- No edits to governance confidence or CRO aggregation
- No edits to committee LLM prompts/plugins
