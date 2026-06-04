# Research Summary

Index of existing research markdown under `docs/`. Regenerate ranking suite via `python scripts/generate_ranking_root_cause_reports.py`.

---

## Outcome & ranking

| Document | Topic |
|----------|-------|
| [outcome-attribution-report.md](../../outcome-attribution-report.md) | Rank buckets vs forward returns — **partial** verdict |
| [ranking-calibration-root-cause.md](../../ranking-calibration-root-cause.md) | Why top-20 works but order fails |
| [rank-reliability-report.md](../../rank-reliability-report.md) | Spearman vs alpha |
| [factor-reliability-report.md](../../factor-reliability-report.md) | Factor predictive power |
| [regime-rank-reliability-report.md](../../regime-rank-reliability-report.md) | By regime |
| [score-compression-analysis.md](../../score-compression-analysis.md) | Composite clustering |
| [calibrated-ranking-research.md](../../calibrated-ranking-research.md) | Isotonic design |
| [calibrated-ranking-backtest.md](../../calibrated-ranking-backtest.md) | Backtest methodology |

**Headline:** Rankings **generate alpha**; **rank ordering not calibrated**.

---

## Committee & ARGS

| Document | Topic |
|----------|-------|
| [committee-effectiveness-report.md](../../committee-effectiveness-report.md) | Phase 1 ~14% independence |
| [committee-independence-design.md](../../committee-independence-design.md) | Phase 2 design |
| [committee-independence-phase2-results.md](../../committee-independence-phase2-results.md) | **~79%** independence |
| [committee-overlap-analysis.md](../../committee-overlap-analysis.md) | Overlap deep dive |
| [consensus-analysis.md](../../consensus-analysis.md) | Cross-committee patterns |
| [args-value-validation-report.md](../../args-value-validation-report.md) | ARGS value prop |
| [args-packet-evidence-audit.md](../../args-packet-evidence-audit.md) | Evidence coverage |

**Headline:** Committee independence **Phase 2 complete**; Phase 3 not started.

---

## QRC / SQE

| Document | Topic |
|----------|-------|
| [qrc-root-cause-analysis.md](../../qrc-root-cause-analysis.md) | Uniform quant evidence |
| [qrc-evidence-model-redesign.md](../../qrc-evidence-model-redesign.md) | Redesign proposal |
| [qrc-information-compression-analysis.md](../../qrc-information-compression-analysis.md) | Token/payload |
| [qrc-sqe-ab-test-report.md](../../qrc-sqe-ab-test-report.md) | **ARGS_QRC_USE_SQE** A/B |
| [qrc-sqe-live-openai-evaluation.md](../../qrc-sqe-live-openai-evaluation.md) | Live OpenAI eval |
| [quant-metrics-forensic-analysis.md](../../quant-metrics-forensic-analysis.md) | Forensic quant metrics |
| [tarc-qrc-upgrade-validation.md](../../tarc-qrc-upgrade-validation.md) | TARC/QRC upgrade |

**Headline:** **`ARGS_QRC_USE_SQE=false`** production default.

---

## SEE

| Document | Topic |
|----------|-------|
| [see-v2-momentum-support.md](../../see-v2-momentum-support.md) | Strategy profiles |
| [see-v2-validation-report.md](../../see-v2-validation-report.md) | Top-20 SEE scores |

---

## Dated ARGS exports

`args-breakout-2026-06-*.md`, `args-momentum-2026-06-*.md`, `args-legacy-*`, `args-sqe-*` — historical run exports.

---

## Daily ops research logs

[docs/dailyruns/04-jun-2026/](../../dailyruns/04-jun-2026/) — prerequisites through best bets (2026-06-04).

---

## Scripts → reports

| Script | Output |
|--------|--------|
| `generate_outcome_attribution_report.py` | outcome-attribution |
| `generate_ranking_root_cause_reports.py` | five ranking reports |
| `generate_rank_reliability_report.py` | rank-reliability |
| `analyze_committee_effectiveness.py` | committee metrics |
| `qrc_sqe_ab_experiment.py` | A/B artifacts |
