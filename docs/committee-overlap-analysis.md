# Committee Overlap Analysis (Phase 1)

Read-only metrics on completed ARGS research runs. No production prompt or committee execution changes.

## Data sources

| Strategy | `research_run_id` | `as_of_date` | Completed (UTC) |
|----------|-------------------|--------------|-----------------|
| `breakout_v1` | `11cd8dc9-acdf-4a49-b43f-1f5dc306730e` | 2026-06-02 | 2026-06-03 12:10 |
| `momentum_v1` | `6d6ede9f-96fd-4a1f-8464-3c5fa7ddf1bb` | 2026-06-02 | 2026-06-03 12:15 |

Each run: **20 packets** (top-N), **100 committee reviews** (TARC, QRC, FRC, NRCC, RC × 20), **20 CRO reviews**.

Reproduce:

```bash
.venv/bin/python scripts/analyze_committee_effectiveness.py --run-id 11cd8dc9-acdf-4a49-b43f-1f5dc306730e
.venv/bin/python scripts/analyze_committee_effectiveness.py --run-id 6d6ede9f-96fd-4a1f-8464-3c5fa7ddf1bb
```

## Executive summary

Committees are **not independent narrators**. Surface findings differ by committee code, but:

1. **Evidence is shared** — ~59–60% mean Jaccard overlap on `supporting_evidence` refs per packet; 80/100 reviews cite the same three refs (`ranking:rank`, `ranking:composite_score`, `regime:regime_label`).
2. **Two committees are clones per packet** — FRC and RC fail LLM quality validation and emit **identical degraded fallback** bullets on every packet (40% of all reviews).
3. **NRCC is a single-value committee** — confidence fixed at **0.25** on all 20 packets (news unavailable).
4. **FRC / RC confidence is frozen** at **0.35** with **0.0 std** within committee across the universe.
5. **Effective independence rate ~14%** — composite of uniqueness, non-overlapping evidence, and non-degraded reviews (see `app/args/analytics/committee_effectiveness.py`).

## Run-level metrics

| Metric | breakout_v1 | momentum_v1 |
|--------|-------------|-------------|
| Mean finding token Jaccard (pairwise) | 0.147 | 0.177 |
| Mean evidence ref overlap | 0.594 | 0.600 |
| Mean composite uniqueness | 0.581 | 0.559 |
| Mean agreement echo score | 0.416 | 0.433 |
| Mean disagreement score | 0.584 | 0.567 |
| Degraded review fraction | 40% | 44% |
| **Effective independence rate** | **14.1%** | **~13.5%** |
| Strict independence packet rate (score ≥ 0.65, evidence overlap < 0.5) | 0% | 0% |
| Headline disagreement rate (packets ≥ 0.55 threshold) | 100% | 80% |

The loose “headline disagreement rate” is driven by moderate text divergence between TARC and QRC while citations stay aligned. The **effective independence rate** is the better headline for “do committees actually disagree?” — **~14%**.

## Confidence clustering

| Committee | breakout mean | breakout std | unique conf (rounded) |
|-----------|---------------|----------------|------------------------|
| TARC | 0.857 | 0.012 | 5 |
| QRC | 0.678 | 0.030 | 10 |
| FRC | 0.350 | **0.000** | **1** |
| RC | 0.350 | **0.000** | **1** |
| NRCC | 0.250 | **0.000** | **1** |

Three of five committees produce **no confidence variance** across the top-20 universe — a strong sign of templated output, not calibrated judgment.

## Evidence overlap

Top shared refs (both runs):

| Ref | Review count (of 100) |
|-----|----------------------|
| `ranking:rank` | 80 |
| `ranking:composite_score` | 80 |
| `regime:regime_label` | 80 |
| `news_snapshot:status` | 20 |

Per packet, committees average **~4 unique refs** total — almost entirely the ranking/regime triad plus NRCC news status.

## Finding similarity (TARC vs QRC)

On successful LLM paths, TARC and QRC write different paragraphs but recycle packet vocabulary:

| Pair | Mean token Jaccard |
|------|-------------------|
| TARC ↔ QRC | 0.17 (breakout), 0.16 (momentum) |
| TARC ↔ RC | 0.07–0.12 |

QRC often mentions negative regime IC while TARC emphasizes rank and factor strength — **narrative tension without independent evidence**.

## Example: `WOCKPHARMA.NS` (breakout run)

**Shared evidence (all committees):** `ranking:rank`, `ranking:composite_score`, `regime:regime_label`

| Committee | Composite uniqueness | Notes |
|-----------|---------------------|--------|
| NRCC | 0.947 | Only unique ref: `news_snapshot:status` |
| QRC | 0.677 | Distinct validation narrative |
| TARC | 0.660 | Technical narrative |
| FRC | 0.329 | Degraded fallback |
| RC | 0.324 | Degraded fallback (mirror template) |

**TARC (excerpt):** rank 2, composite 0.8868, volume surge / trend quality / high proximity.

**QRC (excerpt):** quality score 0.7325, rank-IC 0.1401, decile spread -0.0103 — challenges historical edge while citing the **same ranking/regime refs**.

## Generic overlap patterns

1. **Degraded strength/risk bullets** — 60 of 240 strength strings (25%) are duplicate across committees on a packet, e.g. “Packet context was available for deterministic fallback.”
2. **FRC ≡ RC template** — Same validation failure, same three evidence refs, same confidence 0.35.
3. **NRCC boilerplate** — “News/catalyst feed unavailable; NRCC review degraded.” with `news_snapshot:status` only.
4. **Ranking vocabulary bleed** — TARC, QRC, and degraded committees all anchor on rank, composite score, and `BEAR_LOW_VOL` regime text from the packet.

## Committee uniqueness (illustrative)

`compute_committee_uniqueness_score(review, peer_reviews)` for `WOCKPHARMA.NS`:

```json
{
  "TARC": { "overlap_with_other_committees": 0.0715, "unique_evidence_count": 0, "composite_uniqueness": 0.6599 },
  "QRC": { "overlap_with_other_committees": 0.0658, "unique_evidence_count": 0, "composite_uniqueness": 0.6771 },
  "FRC": { "overlap_with_other_committees": 0.2806, "unique_evidence_count": 0, "composite_uniqueness": 0.3292 },
  "RC":  { "overlap_with_other_committees": 0.2809, "unique_evidence_count": 0, "composite_uniqueness": 0.3236 },
  "NRCC": { "overlap_with_other_committees": 0.0072, "unique_evidence_count": 1, "composite_uniqueness": 0.9468 }
}
```

High uniqueness for NRCC is **wording isolation**, not substantive news research.

## Conclusion

ARGS committees today behave as **multiple narrators over one packet**, not adversarial experts. Phase 2 should enforce scoped mandates, minimum unique evidence per committee, and contrarian requirements (see `committee-independence-design.md`).
