# Step 09 — Top 3 best bets (2026-06-04)

**As-of:** 2026-06-04 | **Universe:** NIFTY_500 | **Regime:** BEAR_LOW_VOL

Selection mirrors Jun-3 style: prioritize names in **both** strategy factor top-10, then ARGS composite + governance confidence on each side, with **SEE v2** (`setup_evidence_score` from momentum ranking run) as tie-breaker.

## Dual top-10 overlap (factor ranks)

`ACMESOLAR.NS`, `HFCL.NS`, `HONASA.NS`, `IFCI.NS`, `THERMAX.NS`, `VIJAYA.NS`, `WOCKPHARMA.NS`

## Top 3

| # | Symbol | Breakout rank | Momentum rank | ARGS composite (bo / mo) | Gov conf (bo / mo) | SEE v2 |
|---|--------|---------------|---------------|--------------------------|--------------------|--------|
| 1 | **HONASA.NS** | 2 | 2 | 0.870 / 0.972 | 0.720 / 0.718 | 61.31 |
| 2 | **THERMAX.NS** | 3 | 1 | 0.865 / 0.975 | 0.717 / 0.717 | 60.68 |
| 3 | **IFCI.NS** | 4 | 3 | 0.863 / 0.960 | 0.718 / 0.717 | 60.24 |

### One-line rationales

1. **HONASA.NS** — Tight dual #2/#2 factor ranks with the strongest joint ARGS composites and aligned governance scores; SEE solidly above 60.
2. **THERMAX.NS** — Momentum #1 and breakout top-3; highest momentum ARGS composite in the trio with consistent gov confidence.
3. **IFCI.NS** — Dual top-5 ranks with strong dual ARGS composites; slightly lower SEE than HONASA/THERMAX but excellent cross-strategy agreement.

## Caveats

- **Validation:** Both ranking runs for 2026-06-04 are `insufficient_data` until forward horizons have enough bars; forward-return evidence not yet in validation reports.
- **Rank ordering research:** ARGS committee ranks (e.g. HFCL ARGS rank 1 with momentum factor rank 9) can diverge from factor ranks 6–20 — do not treat ARGS rank as identical to factor rank.
- **QRC:** Committee QRC outputs are embedded in packet exports; not duplicated in governance `structured` JSON. Review [args-breakout.md](./args-breakout.md) / [args-momentum.md](./args-momentum.md) for committee detail.
- **Factor IC / exit research:** Batch completed but `metrics_written: 0` for same-day window (expected without completed validation).

## Run IDs (reference)

| Artifact | ID |
|----------|-----|
| Daily batch | `f4f7bf42-8d7a-432e-a9f5-13156de861ea` |
| Breakout ranking | `1ffc946f-4e09-4700-a89e-974b41b853bd` |
| Momentum ranking | `8c4109d4-0f83-4cf4-8bf3-f2c1cf0c7d30` |
| ARGS breakout | `48a517f5-e5f5-4709-a7d9-5b27e60427b0` |
| ARGS momentum | `8e93bbde-cdf3-4a3e-86c6-e610c449f3b5` |
