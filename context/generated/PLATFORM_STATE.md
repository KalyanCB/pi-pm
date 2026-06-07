---
generated_at: 2026-06-07T03:43:13Z
git_sha: c8171f3
git_branch: feature/copilot-ai
generator: scripts/generate_context.py
stale_after_hours: 24
---

# Platform State

> Auto-generated. Do not edit. Run `uv run python scripts/generate_context.py` to refresh.

| Field | Value |
|-------|-------|
| Git SHA | `c8171f3` |
| Branch | `feature/copilot-ai` |
| Migration head (latest file) | `20260611` |
| Tests collected | 689 |
| API route handlers | 147 |
| DB tables (models) | 70 |

## Pipeline

```
Market Data → Ranking → Validation → Recommendation Engine → HITL → Execution (Paper/Live)
                                      ↓
                              Exit Monitor (daily; ADR-033 intraday PROPOSED)
                                      ↓
                              ARGS / Committee (advisory)
```

## Environment flags (see `.env.example`)

| Flag | Purpose |
|------|---------|
| `HITL_ENABLED` | `false` = paper auto-approve; `true` = human approval required |
| `PAPER_TRADING_ENABLED` | Enables paper pilot execution path |
| `AUTH_ENABLED` | JWT gate on API |

## Key commands

```bash
docker compose -f docker/docker-compose.yml up --build
uv run pytest tests/ -q
uv run python scripts/generate_context.py
uv run python scripts/replay_paper_trade.py   # historical paper replay
```
