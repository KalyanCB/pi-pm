# Committee Independence Design (Phase 2 Proposal)

Phase 1 analytics (`app/args/analytics/committee_effectiveness.py`) show ~14% effective independence and 40–44% degraded clone reviews. This document defines **per-committee scope** and **independence rules** for a future prompt/schema rollout. **No production prompts are changed in Phase 1.**

## Design goal

Transform the ARGS committee stage from “multiple narrators reading the same packet” into **adversarial expert reviewers** that:

- Cite evidence **unique to their mandate**
- Produce **minimum contrarian friction** with peers
- Refuse filler when data is missing

## Per-committee scope (hard boundaries)

### TARC — Technical Analysis Review Committee

**Only:**

- Technical structure, chart/ranking context
- Ranking factors (volume surge, trend quality, breakout proximity, momentum factors per strategy)
- Momentum, trend, volume, breakout mechanics
- Regime label **as it affects technical interpretation** (not validation statistics)

**Never:**

- Validation, factor IC, SEE, SQQ
- Fundamentals, earnings, valuation
- News, macro, sector narratives

**Adversarial duty:** State what technical rank **overstates** given weak factor legs.

---

### QRC — Quant / Validation Review Committee

**Only:**

- Factor IC, validation history, decile separation
- Regime performance, SEE, SQE summaries
- Historical sample quality, rank IC stability

**Must challenge TARC when:** technical rank is strong but historical/regime validation is weak (negative regime IC, poor decile spread, sparse samples).

**Never:**

- Repeat TARC factor storytelling without validation framing
- Fundamentals, news, or position-sizing language

---

### FRC — Fundamental Review Committee

**Only:**

- Business quality, profitability, balance sheet, earnings trajectory, valuation

**If fundamentals absent in packet:** output **“insufficient fundamental evidence”** — no generic strengths/risks, no ranking/regime filler.

**Never:**

- Technical ranking narrative
- Macro/news headlines
- Degraded clone of RC/TARC templates

---

### NRCC — News, Regime, Catalyst Committee

**Only:**

- News, corporate events, macro, sector context

**If news unavailable:** report **“no news evidence”** with `news_snapshot:status` only — no invented catalysts.

**Never:**

- Rank/composite score as primary evidence
- Validation IC tables
- Technical factor lists

---

### RC — Risk Committee

**Only:**

- Drawdown, regime risk, liquidity, concentration, volatility
- Explicit **reasons not to own** / veto themes

**Must:** search for disqualifying risk; low confidence when technical rank is high but risk stack is elevated.

**Never:**

- Bullish factor promotion (RC strengths should not mirror TARC strengths)
- Fundamental quality scoring

---

### CRO — Chief Research Officer (aggregation only)

Unchanged in Phase 1. Consumes committee outputs; Phase 2 may weight committees by **independence score** (read-only metric) but must not alter governance confidence formulas in Phase 1.

## Independence rules (proposed Phase 2 schema)

| Rule | Requirement |
|------|-------------|
| Minimum strengths | ≥ 3, scoped to committee mandate |
| Minimum risks | ≥ 3, at least one **peer-challenge** risk (e.g. QRC challenges TARC) |
| Minimum evidence | ≥ 3 refs; **≥ 1 ref not cited by any other committee** on same packet |
| Contrarian view | ≥ 1 explicit `contrarian_view` string disagreeing with another committee’s conclusion |
| Confidence | Float 0.0–1.0; committee-specific calibration (no universe-constant 0.35/0.25) |
| Degraded output | Forbidden for FRC/RC when mandate data missing — use **insufficient evidence** stub instead of TARC clone |
| Banned refs for non-TARC | `ranking:rank` + `ranking:composite_score` only as secondary context, not primary evidence for FRC/NRCC/RC |

### Proposed JSON extensions (Phase 2)

```json
{
  "findings": "...",
  "strengths": ["...", "...", "..."],
  "risks": ["...", "...", "..."],
  "supporting_evidence": [{"ref": "validation:rank_ic", "note": "..."}],
  "contrarian_view": "TARC rank 2 overstates edge given negative BEAR_LOW_VOL regime IC.",
  "confidence": 0.62,
  "evidence_unique": true
}
```

## Cross-committee challenge matrix

| If committee A says… | Committee B must… |
|----------------------|-------------------|
| TARC: strong technical rank | QRC: cite IC/regime weakness or confirm with numbers |
| QRC: moderate validation | TARC: acknowledge validation cap on rank |
| TARC + QRC: constructive | RC: articulate veto path (liquidity, drawdown, concentration) |
| FRC: insufficient data | CRO: down-weight fundamental leg, not impute |
| NRCC: no news | NRCC: abstain from catalyst claims; NRCC confidence ≤ 0.3 |

## Enforcement (Phase 2 implementation notes)

1. **Prompt isolation** — strip forbidden packet sections per committee user payload (already partially done; extend for FRC/RC/NRCC).
2. **Post-LLM validator** — reject outputs citing forbidden refs or duplicate degraded templates across FRC/RC.
3. **Uniqueness gate** — `compute_committee_uniqueness_score` ≥ 0.45 composite before persisting (read-only metric exists today).
4. **AB metric** — track `effective_independence_rate` per research run; target ≥ 40% before promoting prompts.

## Out of scope (per Phase 1 constraints)

- Ranking, validation, factor IC, SEE, SQE calculation changes
- Governance confidence formulas, CRO aggregation logic changes
- New committees or ARGS packet enrichers

## References

- Metrics module: `app/args/analytics/committee_effectiveness.py`
- Analysis script: `scripts/analyze_committee_effectiveness.py`
- Overlap evidence: `docs/committee-overlap-analysis.md`
