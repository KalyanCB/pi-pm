# Experiment Catalog — Replay Simulation Framework

All experiments are defined in `configs/`. Run with:
```
uv run python scripts/run_replay.py configs/<ID>.yaml
uv run python scripts/run_replay.py configs/<ID>.yaml --dry-run  # validate + count days
uv run python scripts/run_replay.py configs/<ID>.yaml --verbose  # day-by-day output
```

---

## EXP01 — Smoke Test 2 Weeks

| Field | Value |
|---|---|
| File | `configs/EXP01_SMOKE_2W.yaml` |
| Mode | `AUTONOMOUS_RCEE` |
| Period | 2026-05-19 → 2026-06-05 |
| Purpose | Quick framework validation on recent 2-week window |
| Strategies | breakout_v1, momentum_v1 |
| Capital | 10,00,000 (no SIP) |
| Expected runtime | < 5 seconds |

---

## EXP02 — Bear Regime 3 Months

| Field | Value |
|---|---|
| File | `configs/EXP02_BEAR_3M.yaml` |
| Mode | `AUTONOMOUS_RCEE` |
| Period | 2026-03-01 → 2026-06-05 |
| Purpose | Portfolio behavior during BEAR_LOW_VOL; validate that RCEE suppresses BUY entries |
| Strategies | breakout_v1, momentum_v1 |
| Capital | 10,00,000 + 1,00,000/month SIP |
| Key hypothesis | RCEE blocks most BUYs in BEAR → cash preservation |

---

## EXP03 — Regime Transition 6 Months

| Field | Value |
|---|---|
| File | `configs/EXP03_REGIME_TRANSITION_6M.yaml` |
| Mode | `AUTONOMOUS_RCEE` |
| Period | 2025-12-01 → 2026-06-05 |
| Purpose | Covers BULL_LOW_VOL BUY phase → BEAR_LOW_VOL WATCH phase transition |
| Strategies | breakout_v1, momentum_v1 |
| Capital | 10,00,000 + 1,00,000/month SIP |
| Key hypothesis | Positions opened in BULL exited by regime trigger in BEAR |

---

## EXP04 — 1 Year Full Replay 2025

| Field | Value |
|---|---|
| File | `configs/EXP04_1Y_REPLAY.yaml` |
| Mode | `AUTONOMOUS_RCEE` |
| Period | 2025-01-01 → 2025-12-31 |
| Purpose | Full 2025 year — mostly BULL_LOW_VOL; primary performance benchmark |
| Strategies | breakout_v1, momentum_v1 |
| Capital | 10,00,000 + 1,00,000/month SIP |

---

## EXP05 — Full Historical Replay

| Field | Value |
|---|---|
| File | `configs/EXP05_FULL_REPLAY.yaml` |
| Mode | `AUTONOMOUS_RCEE` |
| Period | 2022-01-01 → 2026-06-05 |
| Purpose | Complete 4-year simulation across all regimes |
| Strategies | breakout_v1, momentum_v1 |
| Capital | 10,00,000 + 1,00,000/month SIP |
| Expected runtime | 2–5 minutes |

---

## EXP06 — RCEE Comparison (Force Edge)

| Field | Value |
|---|---|
| File | `configs/EXP06_RCEE_COMPARISON.yaml` |
| Mode | `AUTONOMOUS_FORCE_EDGE` |
| Period | 2024-01-01 → 2026-06-05 |
| Purpose | Compare forced-EDGE (no regime blocking) vs EXP05 to quantify RCEE alpha |
| Strategies | breakout_v1, momentum_v1 |
| Capital | 10,00,000 (no SIP, for clean comparison) |
| Key hypothesis | RCEE improves risk-adjusted returns in bear regimes |

---

## EXP07 — Strategy Comparison (breakout only)

| Field | Value |
|---|---|
| File | `configs/EXP07_STRATEGY_COMPARISON.yaml` |
| Mode | `AUTONOMOUS_RCEE` |
| Period | 2024-01-01 → 2026-06-05 |
| Purpose | Run breakout_v1 in isolation; run momentum_v1 separately to isolate strategy alpha |
| Strategies | breakout_v1 (this config); create EXP07b with momentum_v1 to compare |
| Capital | 10,00,000, max 5 positions |

---

## Adding New Experiments

1. Copy any existing YAML from `configs/`
2. Change `experiment_id` (must be unique)
3. Adjust `start_date`, `end_date`, `mode`, `strategies`, `capital`
4. Run `--dry-run` to validate
5. Run without flags to execute and generate reports in `docs/experiments/results/<experiment_id>/`
