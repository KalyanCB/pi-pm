---
generated_at: 2026-06-28T03:28:38Z
generator: scripts/generate_context.py
---

# Ops & Scripts Index

| Script | Purpose |
|--------|---------|
| `scripts/run_daily_nifty500_batch.py` | Thin HTTP client for the daily NIFTY 500 batch API. |
| `scripts/replay_paper_trade.py` | Pi-PM Paper Trade Replay — Jan 2022 → Jun 2026 |
| `scripts/replay_paper_trade_v2.py` | Pi-PM Paper Trade Replay v2 — Jun 2022 → Jun 2026 |
| `scripts/run_replay.py` | Replay Simulation Framework CLI. |
| `scripts/run_historical_committee_paper_pilot.py` | Replay committee → HITL auto-approve → paper trading day-by-day from a... |
| `scripts/generate_context.py` | Generate AI-friendly context pack under context/generated/. |
| `scripts/generate_pilot_reports.py` | Generate paper trading pilot reports (markdown). |
| `scripts/run_walkforward.py` | Walk-Forward OOS Evaluation CLI. |
| `scripts/backtest_all_strategies.py` | Pi-PM Multi-Strategy Backtest — Simulating live trading from Jan 2022. |
| `scripts/analyze_committee_effectiveness.py` | Read-only committee overlap / uniqueness analysis for ARGS research ru... |
| `scripts/backfill_intraday_fills.py` | Phase 1 — targeted intraday backfill for realistic next-session VWAP f... |
| `scripts/backfill_sprint7_traceability.py` | Sprint 7.1 — backfill traceability tables from persisted ranking/valid... |
| `scripts/backfill_sprint82_factor_analytics.py` | Sprint 8.2 — backfill factor predictive power analytics from ranking t... |
| `scripts/backfill_sprint83_exit_research.py` | Sprint 8.3 — backfill exit research metrics from validated ranking sig... |
| `scripts/backtest_honest.py` | Honest Paper-Trade Backtest |
| `scripts/backtest_inmemory.py` | Pi-PM In-Memory Backtest — no DB writes, pure simulation. |
| `scripts/backtest_regime_stop.py` | Pi-PM In-Memory Backtest with REGIME-DYNAMIC STOP-LOSS — no DB writes. |
| `scripts/backtest_reversal_v1.py` | Backtest: reversal_v1 strategy — Jan 2022 to Jun 2026 |
| `scripts/batch1_eod_pipeline.py` | Batch 1 — End-of-Day Ingestion & Signal Generation Pipeline (ADR-034). |
| `scripts/batch2_intraday_exit.py` | Batch 2 — Intraday Exit Monitor (ADR-035). |
| `scripts/batch3_paper_trade_entry.py` | Batch 3 — Morning Paper Trade Execution (ADR-036). |
| `scripts/cleanup_dups.py` | Delete duplicate rec run results using 10 parallel threads, one rec_ru... |
| `scripts/export_args_research_run.py` | Export a full ARGS research run to markdown (packets, committees, gove... |
| `scripts/fix_canonical_links.py` | Rewrite stale cross-references in context/canonical/ for self-containe... |
| `scripts/generate_outcome_attribution_report.py` | Generate outcome attribution report from ranking runs and forward retu... |
| `scripts/generate_packet_evidence_audit.py` | Generate docs/args-packet-evidence-audit.md from DB source counts and ... |
| `scripts/generate_paper_trading_dashboard.py` | Generate paper-trading pilot dashboards (markdown). |
| `scripts/generate_pi_pm_guide_pdf.py` | Render docs/pi-pm-complete-guide.html to PDF (Mermaid via browser). |
| `scripts/generate_rank_reliability_report.py` | Generate per-rank reliability report (research only, read-only DB). |
| `scripts/generate_rank_reliability_reports.py` | Generate rank reliability + regime + calibration docs (read-only DB). |
| `scripts/generate_ranking_root_cause_reports.py` | Generate all five ranking calibration research docs (read-only DB). |
| `scripts/generate_see_v2_validation_report.py` | Generate SEE v2 validation report for breakout and momentum top-20 run... |
| `scripts/generate_sprint85_research_intelligence.py` | Sprint 8.5 — generate executive research intelligence report pack. |
| `scripts/init_regime_policy_presets.py` | Load Sprint 8.1 E1-E4 regime policy preset configurations. |
| `scripts/kite_token_refresh.py` | Kite Connect daily access token refresh — headless login via Zerodha w... |
| `scripts/load_nifty1000.py` | Bootstrap the NIFTY_1000 universe and ingest OHLCV via batched Yahoo F... |
| `scripts/pipm_service_factory.py` | Shared service wiring for CLI scripts and batch orchestration. |
| `scripts/prune_stale_ranking_runs.py` | Remove duplicate ranking runs, keeping the newest per (universe, strat... |
| `scripts/qrc_sqe_ab_experiment.py` | A/B experiment: legacy QRC brief vs SQE condensation (deterministic me... |
| `scripts/recover_recommendation_results.py` | Recovery script: regenerate recommendation_results from existing ranki... |

## Experiment configs (`configs/`)

- `configs/EXP01_SMOKE_2W.yaml`
- `configs/EXP02_BEAR_3M.yaml`
- `configs/EXP03_REGIME_TRANSITION_6M.yaml`
- `configs/EXP04_1Y_REPLAY.yaml`
- `configs/EXP05_FULL_REPLAY.yaml`
- `configs/EXP05_FULL_REPLAY_NOSIP.yaml`
- `configs/EXP06_RCEE_COMPARISON.yaml`
- `configs/EXP07_STRATEGY_COMPARISON.yaml`
- `configs/EXP08_REVERSAL_FULL_NOSIP.yaml`
- `configs/EXP09_REVERSAL_SIP.yaml`
- `configs/EXP10A_BREAKOUT_ONLY.yaml`
- `configs/EXP10B_BREAKOUT_MOMENTUM.yaml`
- `configs/EXP10C_BREAKOUT_REVERSAL.yaml`
- `configs/EXP10D_ALL_THREE.yaml`
- `configs/EXP11_SLOTS_15.yaml`
- `configs/EXP11_SLOTS_5.yaml`