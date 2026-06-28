---
generated_at: 2026-06-28T03:28:38Z
git_sha: 6e7db17
git_branch: feat/hybrid-regime-exit
generator: scripts/generate_context.py
stale_after_hours: 24
---

# Platform State

> Auto-generated. Do not edit. Run `uv run python scripts/generate_context.py` to refresh.

| Field | Value |
|-------|-------|
| Git SHA | `6e7db17` |
| Branch | `feat/hybrid-regime-exit` |
| Migration head (latest file) | `20260625` |
| Tests collected | 861 |
| API route handlers | 152 |
| DB tables (models) | 76 |

## Pipeline

```
Market Data → Ranking → Validation → Recommendation Engine → HITL → Execution (Paper/Live)
                                      ↓
                Exit Monitor — T2 daily + T1 intraday scaffold (ADR-033;
                live auto-exec gated OFF, scheduler/broker-stop pending)
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
