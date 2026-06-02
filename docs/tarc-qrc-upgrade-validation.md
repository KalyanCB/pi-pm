# TARC + QRC Upgrade Validation (Institutional-Grade Quality Gate)

## Run Metadata

- Before baseline run: `8a2e2960-9db7-4096-b904-c295a1395466`
- After upgrade run: `3fa420d1-9b2d-45f7-a26a-bd47352e2d3d`
- API call: `POST /api/v1/research/run` with `top_n=20`, `committee_codes=["TARC","QRC"]`
- Universe date: `2026-06-01`

## 1) Before vs After Examples

### Representative symbol: `WOCKPHARMA.NS` (Rank 2)

- **Before (TARC, confidence 0.85):** Narrative emphasized high-level factor commentary and repeated confidence defaults.
- **After (TARC, confidence 0.73):** Narrative now explicitly includes factor dominance, weak-factor identification, breadth framing, and regime caveat.
- **Before (QRC, confidence 0.35):** Frequent "insufficient data" style output with low differentiation.
- **After (QRC, confidence 0.56):** Still data-gap heavy, but now explicitly structured around missing horizons/deciles/factor-IC and policy evidence quality context.

### Snapshot delta for target names

- `HFCL.NS`: rank 1, TARC 0.73, QRC 0.56, breadth `STRONG_BREADTH`, coverage 20%, gaps 4
- `WOCKPHARMA.NS`: rank 2, TARC 0.73, QRC 0.56, breadth `STRONG_BREADTH`, coverage 20%, gaps 4
- `TRITURBINE.NS`: rank 12, TARC 0.72, QRC 0.56, breadth `STRONG_BREADTH`, coverage 20%, gaps 4
- `THERMAX.NS`: rank 3, TARC 0.73, QRC 0.56, breadth `STRONG_BREADTH`, coverage 20%, gaps 4

## 2) Confidence Distribution

### Before

- TARC: min `0.65`, max `0.85`, avg `0.75`, unique values `2`
- QRC: min `0.35`, max `0.35`, avg `0.35`, unique values `1`

### After

- TARC: min `0.70`, max `0.74`, avg `0.72`, unique values `5`
- QRC: min `0.56`, max `0.56`, avg `0.56`, unique values `1`

**Assessment:** TARC confidence is now materially less clustered than baseline. QRC confidence remains clustered and still needs differentiation work tied to per-stock evidence variability.

## 3) TARC Breadth Distribution

- `STRONG_BREADTH`: `20`
- `MEDIUM_BREADTH`: `0`
- `NARROW_SIGNAL`: `0`
- Degraded TARC outputs: `0`

**Assessment:** Breadth classification is now consistently populated, but current universe packet characteristics are producing a one-bucket distribution (all strong), so additional within-class differentiation is still needed.

## 4) QRC Validation Coverage Distribution

- `>=80%`: `0`
- `60-79%`: `0`
- `40-59%`: `0`
- `<40%`: `20` (all at 20%)

**Assessment:** QRC correctly detects missing evidence and reports low coverage, but because packet validation blocks are uniformly sparse in this run, coverage differentiation is not present.

## 5) Top 5 Strongest Research Cases (by avg of TARC+QRC confidence)

1. `LAURUSLABS.NS` (rank 6): avg `0.65` (TARC 0.74, QRC 0.56)
2. `GRANULES.NS` (rank 7): avg `0.65` (TARC 0.74, QRC 0.56)
3. `RRKABEL.NS` (rank 8): avg `0.65` (TARC 0.74, QRC 0.56)
4. `HFCL.NS` (rank 1): avg `0.645` (TARC 0.73, QRC 0.56)
5. `WOCKPHARMA.NS` (rank 2): avg `0.645` (TARC 0.73, QRC 0.56)

## 6) Top 5 Weakest Research Cases

1. `ADANIENSOL.NS` (rank 19): avg `0.63` (TARC 0.70, QRC 0.56)
2. `OFSS.NS` (rank 13): avg `0.635` (TARC 0.71, QRC 0.56)
3. `SOLARINDS.NS` (rank 14): avg `0.635` (TARC 0.71, QRC 0.56)
4. `AIAENG.NS` (rank 15): avg `0.635` (TARC 0.71, QRC 0.56)
5. `VIJAYA.NS` (rank 16): avg `0.635` (TARC 0.71, QRC 0.56)

## 7) Remaining Weaknesses

- QRC confidence remains single-valued in this run (`0.56`) despite richer structure.
- QRC coverage and evidence gaps are correctly detected but uniform (`20%`, 4 gaps) because packet validation data is uniformly sparse.
- TARC is improved versus baseline but still over-concentrated in `STRONG_BREADTH`; the breadth classifier needs finer granularity under strong-signal universes.
- Runtime and token usage increased versus baseline due stricter quality and richer prompt contracts:
  - Before: avg tokens/stock `3337.75`, avg seconds/stock `7.97`
  - After: avg tokens/stock `4354.65`, avg seconds/stock `9.37`

## 8) Production Readiness Recommendation

**Recommendation: Not yet production-ready for full institutional deployment.**

### Why

- **TARC:** upgraded from repetitive baseline to materially better packet-specific analysis and non-default confidence variation. This is a meaningful improvement.
- **QRC:** now emits structured evidence-gap reasoning instead of generic one-liners, but confidence and coverage are still effectively clustered due sparse input evidence and insufficient per-stock differentiation in quant metrics.

### Go/No-Go

- **TARC:** Conditional Go (pilot scope only).
- **QRC:** No-Go for institutional production until confidence and coverage become materially differentiated on real top-20 packets.

### Next sprint priority

1. Increase QRC confidence dispersion by binding confidence directly to per-stock policy consistency dispersion and sample heterogeneity.
2. Add finer TARC breadth bucketing under strong-signal cohorts (avoid all-strong collapse).
3. Keep strict quality gate (word range, evidence count, banned generic language) and monitor retry/degraded rates per run.
