# Sprint 8.3 Exit Research Backfill — Performance

## Bottleneck analysis

Profiling focus: `alpha_decay_returns()` → `compute_forward_return()` in `app/validation/forward_returns.py`.

For each signal entry the backfill previously:

1. Called `compute_forward_return()` **60 times** (`ALPHA_DECAY_MAX_DAYS`).
2. Each call ran `bars_on_or_before()` (filter + sort) and `[bar for bar in bars if bar.date > entry.date]` (full scan).
3. Cost scales as **O(entries × 60 × bars)** with repeated list comprehensions.

Policy-family simulators (fixed hold, rank, regime, trend) were secondary; alpha decay dominated CPU on large cohorts (e.g. NIFTY_500 multi-year).

## Optimizations

| Change | Location | Effect |
|--------|----------|--------|
| `BarForwardReturnIndex` — one `bars_on_or_before`, one future-bar tuple | `app/workspace_exit_research/forward_returns_index.py` | Amortize bar scans per entry |
| `forward_returns_through(max_days)` — single loop 1..60 | same | Replace 60× helper calls |
| `alpha_decay_returns()` uses index | `policy_simulators.py` | Drop-in for backfill |
| INFO progress + DB columns on `exit_research_runs` | `progress.py`, service, migration `20260605_0013` | Operational visibility |

**Correctness:** `BarForwardReturnIndex.forward_return(n)` matches `compute_forward_return()` for all horizons; regression tests compare every day 1..60 on synthetic and randomized bar paths. Decimal quantization unchanged (`quantize_return`).

## Progress logging (INFO)

Startup:

```
INFO exit_research_startup strategy=breakout_v1 strategy_version=1.0.0 universe=NIFTY_500 start_date=2024-01-01 end_date=2024-12-31 total_entries=237842
```

Every 100 entries with bars:

```
INFO exit_research_progress strategy=breakout_v1 processed=1200 total=237842 pct=0.50 elapsed_sec=180.0 eta_sec=35820.0 rate=6.7_entries_per_sec
```

Policy batches (after entry simulation pass):

```
INFO exit_research_policy_batch family=FIXED_HOLD status=completed entries=235000
```

Alpha decay:

```
INFO exit_research_alpha_decay entries_processed=235000 alpha_points_generated=14100000 alpha_rows_written=0
```

Completion:

```
INFO exit_research_complete strategy=breakout_v1 runtime_sec=36000.0 simulations_generated=... alpha_points_generated=... database_rows_written=... signals_processed=237842
```

## Database progress tracking

Migration `20260605_0013_sprint83_exit_research_progress` adds to `exit_research_runs`:

| Column | Type | Updated |
|--------|------|---------|
| `total_entries` | INTEGER NULL | At cohort load |
| `processed_entries` | INTEGER DEFAULT 0 | Every 100 entries |
| `percent_complete` | NUMERIC(8,4) | Every 100 entries |
| `last_progress_at` | TIMESTAMPTZ | Every 100 entries |
| `elapsed_seconds` | NUMERIC(12,2) | Every 100 entries |

Mid-run commits flush progress so operators can `SELECT` a running row without waiting for completion.

## Benchmark methodology

**Automated (CI-friendly):** `tests/unit/workspace_exit_research/test_forward_returns_benchmark.py`

- 500 synthetic entries × 250 daily bars
- Compare legacy 60× `compute_forward_return` vs `BarForwardReturnIndex.forward_returns_through(60)`
- Assert identical dict outputs and **≥3×** wall-clock speedup

**Measured (500 entries × 250 bars, M1 local, 2026-06-01):**

| Path | Wall time | Speedup |
|------|-----------|---------|
| Legacy 60× `compute_forward_return` | 0.498 s | — |
| `BarForwardReturnIndex.forward_returns_through` | 0.027 s | **18.2×** |

**Full NIFTY_500 backfill:** Not run in CI. Extrapolate: if alpha decay was ~70% of entry-loop time, expect **~3–5×** faster entry processing overall; run `scripts/backfill_sprint83_exit_research.py` on a staging slice to confirm.

**CPU profiling approach (manual):**

```bash
python -m cProfile -o /tmp/exit83.prof scripts/backfill_sprint83_exit_research.py \
  --start-date 2024-06-01 --end-date 2024-06-30 --universe-code NIFTY_500
python -c "import pstats; p=pstats.Stats('/tmp/exit83.prof'); p.sort_stats('cumtime').print_stats(30)"
```

Compare `compute_forward_return` cumulative time before vs after deploy.

## Validation

```bash
pytest tests/ -q
```

Key tests: `test_forward_returns_index.py`, `test_forward_returns_benchmark.py`, `test_exit_research_progress.py`, existing `test_alpha_decay_returns_decimal_values`.
