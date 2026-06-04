# Step 08 — ARGS (2026-06-04)

**Command (both strategies):**

```bash
cd /Users/kalyancb/pi-pm
ARGS_QRC_USE_SQE=false .venv/bin/python scripts/run_args_top20.py --as-of-date 2026-06-04
```

`ARGS_QRC_USE_SQE=false` per operational request (no SQE path for QRC).

## Research runs

| Strategy | Ranking run | ARGS research run | Status | Export |
|----------|-------------|-------------------|--------|--------|
| breakout_v1 | `1ffc946f-4e09-4700-a89e-974b41b853bd` | `48a517f5-e5f5-4709-a7d9-5b27e60427b0` | completed | [args-breakout.md](./args-breakout.md) |
| momentum_v1 | `8c4109d4-0f83-4cf4-8bf3-f2c1cf0c7d30` | `8e93bbde-cdf3-4a3e-86c6-e610c449f3b5` | completed | [args-momentum.md](./args-momentum.md) |

## Export commands used

```bash
.venv/bin/python scripts/export_args_research_run.py 48a517f5-e5f5-4709-a7d9-5b27e60427b0 -o docs/dailyruns/04-jun-2026/args-breakout.md
.venv/bin/python scripts/export_args_research_run.py 8e93bbde-cdf3-4a3e-86c6-e610c449f3b5 -o docs/dailyruns/04-jun-2026/args-momentum.md
```

## Operational notes

- First combined run: breakout completed; momentum hit `httpx.ReadTimeout` on `cro_aggregate` (60s default) before persisting a `research_runs` row.
- Momentum eventually completed (`8e93bbde-…`, ~7m). Retries hit `UniqueViolation` on `stock_setup_research` for partial SEE rows — no production code changes; exports are from the completed run.
- For slow CRO calls, consider `ARGS_LLM_TIMEOUT_SECONDS` / `ARGS_LLM_CRO_TIMEOUT_SECONDS` (e.g. 180–300) on reruns.
- Validation for 2026-06-04 remains `insufficient_data`; ARGS ran with default `require_completed_validation=false`.
