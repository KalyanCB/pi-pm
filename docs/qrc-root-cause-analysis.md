# QRC Root Cause Analysis

## 1. Executive Summary

QRC produced `0.56` for almost every stock because the QRC evidence inputs are effectively identical across the Top 20 packets for run `3fa420d1-9b2d-45f7-a26a-bd47352e2d3d`, and the confidence rubric is deterministic on those inputs.

Observed Top-20 invariants:

- `validation_report_id`: one unique value (`87a91a73-c9a8-4467-b47e-cef47ec78086`)
- validation status: one unique value (`insufficient_data`)
- horizon metrics count: always `0`
- decile metrics count: always `0`
- factor IC rows: always `0`
- exit research rows: always `50` (same row IDs/order)
- strategy regime performance rows: always `0`
- QRC rubric tuple: always `(coverage=0.2, sample=0.9, regime=0.45, exit=0.85)` -> weighted score `0.56`

Conclusion: this is **not** primarily a prompt issue. It is a data-shape and evidence-scope issue with deterministic confidence collapse once upstream evidence is uniform.

## 2. Data Lineage Diagram

```text
Ranking Run (707e3766-fa3f-4570-8525-7a187189c1e5)
  -> RankingCandidateLoader.load(top_n=20)
  -> InvestmentReviewPacketBuilder.build(...)
      -> RankingValidationRepository.get_by_ranking_run_id(...)      [strategy/run-level]
      -> _load_validation_metrics(...) from:
           - validation_horizon_metrics                               [run-level]
           - validation_decile_metrics                                [run-level]
      -> _load_factor_ic(...) from factor_performance_metrics         [strategy/regime/date-level]
      -> _load_exit_research(...) from exit_research_policy_metrics   [strategy/regime-level]
      -> _load_strategy_regime_performance(...) from strategy_regime_performance [strategy/regime-level]
      -> packet payload persisted to investment_review_packets
  -> QRC build_qrc_user_payload(packet.payload, symbol)
  -> QRC diagnostics + confidence rubric
  -> committee_reviews (QRC output + extensions)
```

## 3. Packet Content Analysis

### Five-stock deep inspection

Stocks inspected:

- `HFCL.NS`
- `WOCKPHARMA.NS`
- `THERMAX.NS`
- `LAURUSLABS.NS`
- `TRITURBINE.NS`

Per-stock extracted quant blocks:

- validation block:
  - `status=insufficient_data`
  - `report_id=87a91a73-c9a8-4467-b47e-cef47ec78086`
  - `regime_label=BEAR_LOW_VOL`
- horizon metrics: `[]` (count `0`)
- decile metrics: `[]` (count `0`)
- factor IC metrics: `[]` (count `0`)
- exit research metrics: `50` rows (same first IDs across all inspected stocks:
  `322a99b0-...`, `4749bafa-...`, `2a11841b-...`)
- regime metrics (`strategy_regime_performance`): `[]` (count `0`)

### Top-20 uniqueness test

Across all 20 packets:

- unique `validation_report_id`: `1`
- unique `validation_status`: `1`
- unique `horizon_n`: `1` (all `0`)
- unique `decile_n`: `1` (all `0`)
- unique `factor_ic_n`: `1` (all `0`)
- unique `exit_n`: `1` (all `50`)
- unique `regime_perf_n`: `1` (all `0`)
- unique first exit metric ID: `1`

This confirms QRC sees nearly identical quant evidence across the entire top 20.

## 4. Coverage Matrix

| Stock | Validation | Deciles | Horizons | Factor IC | Exit Research | Regime |
|---|---|---|---|---|---|---|
| HFCL.NS | Available: Yes (`insufficient_data`) / Coverage: 20% / Differentiated: No / Source: `ranking_validation_reports`, `validation_horizon_metrics`, `validation_decile_metrics` | Available: No (0 rows) / Coverage: 0% / Differentiated: No / Source: `validation_decile_metrics` | Available: No (0 rows) / Coverage: 0% / Differentiated: No / Source: `validation_horizon_metrics` | Available: No (0 rows) / Coverage: 0% / Differentiated: No / Source: `factor_performance_metrics` | Available: Yes (50 rows) / Coverage: 100% / Differentiated: No (identical set) / Source: `exit_research_policy_metrics` | Available: Label only / Coverage: partial / Differentiated: No / Source: `strategy_regime_performance` (0 rows), `ranking_validation_reports.regime_label` |
| WOCKPHARMA.NS | Yes / 20% / No / same sources | No / 0% / No / same source | No / 0% / No / same source | No / 0% / No / same source | Yes / 100% / No / same source | Label only / partial / No / same source |
| THERMAX.NS | Yes / 20% / No / same sources | No / 0% / No / same source | No / 0% / No / same source | No / 0% / No / same source | Yes / 100% / No / same source | Label only / partial / No / same source |
| LAURUSLABS.NS | Yes / 20% / No / same sources | No / 0% / No / same source | No / 0% / No / same source | No / 0% / No / same source | Yes / 100% / No / same source | Label only / partial / No / same source |
| TRITURBINE.NS | Yes / 20% / No / same sources | No / 0% / No / same source | No / 0% / No / same source | No / 0% / No / same source | Yes / 100% / No / same source | Label only / partial / No / same source |

## 5. Root Cause Findings

### A) Is the data genuinely identical?

**Yes, largely for QRC-relevant inputs.**  
The packet builder injects run/strategy/regime scoped quant evidence that is identical for all stocks in this run:

- one shared validation report with no horizon/decile rows
- no factor IC rows for the selected filters
- one shared 50-row exit research slice
- no strategy regime performance rows for this regime

### B) Is packet builder losing stock-level differentiation?

**Partially, by design scope.**  
Builder behavior is consistent with implementation:

- validation and deciles/horizons are loaded by `validation_report_id` (run-level, not stock-level)
- factor IC is loaded by strategy/version/universe/regime/date (not stock-level)
- exit research is loaded by strategy/universe/regime (+ strategy_version filter), then sliced first 50
- regime performance is strategy-level

So differentiation is not being dropped accidentally in serialization; it is mostly absent upstream or not queried at stock level.

### C) Are repositories returning strategy-level evidence instead of stock-level evidence?

**Yes for key QRC sources.**

- `factor_performance_metrics`: strategy/regime/date scope
- `exit_research_policy_metrics`: strategy/universe/regime scope
- `strategy_regime_performance`: strategy/regime scope
- `validation_horizon_metrics` and `validation_decile_metrics`: report-level, not stock-level

### D) Is QRC confidence logic incapable of producing differentiation?

**Conditionally yes.**  
Current rubric in `qrc.py` is deterministic and only uses aggregated diagnostics:

- coverage score
- sample quality label
- regime reliability class
- policies evaluated count

When these inputs are identical, confidence must be identical. In this run, they are identical, so output collapses to `0.56`.

### E) Multiple causes?

**Yes (primary finding).**  
Root cause is multi-factor:

1. Upstream quant evidence is mostly uniform/empty for this ranking run.
2. Repository query scopes are strategy/run level for most QRC evidence.
3. QRC confidence function has no stock-sensitive term once upstream inputs are constant.

## 6. Evidence

- Ranking run `707e3766-fa3f-4570-8525-7a187189c1e5` validation report:
  - `status=insufficient_data`
  - `regime_label=BEAR_LOW_VOL`
  - `validation_horizon_metrics` rows: `0`
  - `validation_decile_metrics` rows: `0`
- Filtered factor performance rows for strategy/version/universe/regime/as_of_date: `0`
- Exit research rows for strategy/version/universe/regime: `120` available; packet injects first `50` into every stock
- Strategy regime performance rows for strategy/version/regime: `0`
- Top-20 QRC review extensions:
  - confidence unique count: `1`
  - rubric tuple unique count: `1`
  - tuple: `(0.2, 0.9, 0.45, 0.85)` -> `0.56`

## 7. Recommended Fixes (No Implementation)

### Highest-impact fix

Introduce stock-sensitive quant evidence into QRC payload (or stock-conditioned quant diagnostics derived from existing quant tables) so confidence has at least one per-stock differentiator.

### Lowest-effort fix

Add one stock-level term to QRC confidence calculation from existing packet fields already differentiated by stock (e.g., ranking component dispersion proxy) while preserving quant evidence caveats.

### Fastest path to QRC confidence dispersion

Add a deterministic stock-level adjustment term in QRC confidence that is available in current packet and bounded by evidence-availability penalties.

### Fastest path to meaningful quant research

Backfill/enable horizon+decile and factor-IC availability for the ranking run so QRC can evaluate actual validation structure instead of missing-data templates.

### Recommended implementation order

1. Ensure non-empty horizon/decile and factor-IC coverage for the target ranking runs.
2. Add stock-sensitive quant differentiator to confidence logic.
3. Replace shared exit-research-only dominance with mixed evidence weighting (validation + IC + exits + regime support).
4. Re-run top-20 validation and verify confidence dispersion and narrative divergence.

## 8. Prioritized Roadmap

1. **P0**: Data availability audit gate before ARGS run (validation/factor IC/regime rows present?).
2. **P0**: Stock-level differentiator in QRC diagnostics.
3. **P1**: Make exit-research contribution conditional on non-missing validation/IC to avoid uniform 0.56 plateau.
4. **P1**: Add observability panel for per-run evidence uniqueness metrics (unique coverage, unique rubric tuples).
5. **P2**: Refine confidence calibration after data coverage is restored.

## 9. Final Verdict

**Why did QRC produce `0.56` confidence for almost every stock?**

Because for this run QRC consumed nearly identical packet evidence for all top-20 symbols (same validation report status, no horizon/decile/factor-IC/regime-performance rows, same exit-research slice), and the current confidence rubric is deterministic over those inputs. With identical inputs, the rubric yields identical output (`0.56`).
