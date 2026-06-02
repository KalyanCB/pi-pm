# ARGS packet evidence audit

Generated: 2026-06-02 14:09 UTC

## Scope

Evidence ingestion into `InvestmentReviewPacket` (no prompt or committee logic changes).

## Source table counts

| Table | Row count |
|-------|-----------|
| `factor_performance_metrics` | 936 |
| `factor_daily_metrics` | 12,120 |
| `strategy_regime_performance` | 8 |
| `research_intelligence_reports` | 18 |
| `research_intelligence_runs` | 2 |
| `exit_research_policy_metrics` | 560 |
| `ranking_run_as_of` | 2026-06-02 |
| `ranking_run_strategy` | breakout_v1/1.0.0 |

## Packet coverage

- Research run audited: `8cc023c1-ef76-4f28-bced-3452d16c1d19`
- Ranking run: `b8e993e4-a049-4f3a-bcd0-29574a0f7e47`
- Packets analyzed: **20**

Persisted packets reflect the builder version at ARGS run time. Use **Post-fix builder sample** (with `--rebuild-sample`) to verify current ingestion without re-running ARGS.

| Field | Populated % |
|-------|-------------|
| `quant_evidence.factor_ic` | 100.0% |
| `quant_evidence.exit_research` | 100.0% |
| `quant_evidence.factor_daily` | 100.0% |
| `regime.strategy_regime_performance` | 100.0% |
| `research_context.notes` | 100.0% |
| `historical_validation_context` | 100.0% |

### Evidence coverage score (0–100)

- Average: **80.0**
- Min: 80
- Max: 80

### Evidence confidence distribution

- Unique values: 1
- Distribution: `{"0.95": 20}`

## Missing evidence (typical)

- `validation.horizon_metrics (current run)` (20 sample packets)

## Persisted packets (sample)

```json
[
  {
    "symbol": "NEULANDLAB.NS",
    "evidence_coverage_score": 80,
    "evidence_confidence": 0.95,
    "factor_ic_rows": 256,
    "exit_research_rows": 100,
    "factor_daily_rows": 8,
    "regime_rows": 4,
    "research_notes": 5,
    "historical_validations": 12,
    "missing": [
      "validation.horizon_metrics (current run)"
    ]
  },
  {
    "symbol": "TATATECH.NS",
    "evidence_coverage_score": 80,
    "evidence_confidence": 0.95,
    "factor_ic_rows": 256,
    "exit_research_rows": 100,
    "factor_daily_rows": 8,
    "regime_rows": 4,
    "research_notes": 5,
    "historical_validations": 12,
    "missing": [
      "validation.horizon_metrics (current run)"
    ]
  },
  {
    "symbol": "ATGL.NS",
    "evidence_coverage_score": 80,
    "evidence_confidence": 0.95,
    "factor_ic_rows": 256,
    "exit_research_rows": 100,
    "factor_daily_rows": 8,
    "regime_rows": 4,
    "research_notes": 5,
    "historical_validations": 12,
    "missing": [
      "validation.horizon_metrics (current run)"
    ]
  },
  {
    "symbol": "WELCORP.NS",
    "evidence_coverage_score": 80,
    "evidence_confidence": 0.95,
    "factor_ic_rows": 256,
    "exit_research_rows": 100,
    "factor_daily_rows": 8,
    "regime_rows": 4,
    "research_notes": 5,
    "historical_validations": 12,
    "missing": [
      "validation.horizon_metrics (current run)"
    ]
  },
  {
    "symbol": "AIAENG.NS",
    "evidence_coverage_score": 80,
    "evidence_confidence": 0.95,
    "factor_ic_rows": 256,
    "exit_research_rows": 100,
    "factor_daily_rows": 8,
    "regime_rows": 4,
    "research_notes": 5,
    "historical_validations": 12,
    "missing": [
      "validation.horizon_metrics (current run)"
    ]
  }
]
```

## Post-fix builder sample (not persisted)

One packet rebuilt with current `InvestmentReviewPacketBuilder` for the same ranking run:

```json
{
  "symbol": "HFCL.NS",
  "evidence_coverage_score": 80,
  "evidence_confidence": 0.95,
  "factor_ic_rows": 256,
  "exit_research_rows": 100,
  "factor_daily_rows": 8,
  "regime_rows": 4,
  "research_notes": 5,
  "historical_validations": 12,
  "missing": [
    "validation.horizon_metrics (current run)"
  ]
}
```

## Confidence calculation path

1. **Packet build** (`InvestmentReviewPacketBuilder`): loads factor IC (latest window with `as_of_date_end <= ranking as_of`), exit research, regime performance, research intelligence, historical completed validations, factor daily for `ranking_run_id`.
2. **Coverage score** (`score_packet_evidence`): weighted 0–100 across validation (current + historical), factor IC, factor daily, regime, exit research, research notes.
3. **Evidence confidence** (`derive_evidence_confidence`): `coverage_score/100` plus bonuses for completed validation, historical validations, |IC|, regime rows, exit rows, research notes (clamped 0.15–0.95).
4. **Governance confidence** (`derive_governance_confidence` at persist): `0.6 * evidence_confidence + 0.4 * committee_avg` when committee scores exist; else evidence confidence only. Stored on `cro_reviews` and `governance_research_reports` (CRO LLM default 0.75 is not used at persist).

## Loader fixes applied

- Factor IC: `list_metrics_covering_as_of` (no longer exact `as_of_date_end == ranking as_of`).
- Exit research: `list_policy_metrics_covering_as_of`.
- Research context: latest `research_intelligence_reports` run → `notes` + compact `reports`.
- Historical validation: `list_completed_with_runs` lookback for QRC context when current run is `insufficient_data`.
