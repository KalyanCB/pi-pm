# SEE v2 — Momentum Strategy Support

## Problem (SEE v1)

Momentum top-20 candidates returned `qualifying_matches = 0` while breakout names returned a fixed 25 matches.

**Root cause:** Reference profiles were built from momentum `score_components` (four factors: `volatility_adjusted_momentum`, `volume_expansion`, `trend_quality`, `relative_strength`), but historical analog search always used **breakout_v1** raw factors (eight-factor space). Cosine similarity compared incompatible vectors, so no setup cleared the similarity threshold.

## Solution (SEE v2)

### Strategy-aware profile generation

`app/stock_setup_evidence/strategy_profiles.py` resolves the ranking run’s `strategy_name` to:

| Strategy | Factor space |
|----------|----------------|
| `breakout_v1` | 8 breakout factors |
| `momentum_v1` | 4 momentum factors |

Both **reference** extraction (`extract_reference_profile`) and **historical** normalization (`build_stock_internal_normalized_profiles`) use the same `SeeStrategyConfig` for the originating strategy.

### Validation expectation

After v2, momentum top-20 runs should show:

- `qualifying_matches > 0` for most candidates with sufficient history
- `strategy_name = momentum_v1` on persisted rows
- Match counts that **vary by stock** (threshold retrieval, not fixed N)

### How to verify

```bash
.venv/bin/alembic upgrade head
.venv/bin/python scripts/generate_see_v2_validation_report.py
```

Or run SEE for a momentum ranking run:

```python
StockSetupResearchService(...).run_for_ranking_run(momentum_run_id, limit=20)
```

Inspect `qualifying_matches`, `total_matches`, and `setup_evidence_score` per symbol.

## Non-goals

This change does **not** modify ARGS, TARC, QRC, CRO, prompts, governance scoring, or HTTP API routes.
