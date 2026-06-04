# Repository Structure

```
pi-pm/
├── app/
│   ├── api/v1/              # 14 HTTP routers
│   ├── args/                # Committees, graph, LLM plugins, packets
│   ├── backtest/            # Historical ranking replay
│   ├── core/                # config, exceptions, logging
│   ├── db/                  # session, repositories
│   ├── factor_analytics/    # IC engine
│   ├── models/              # SQLAlchemy ORM (22 modules)
│   ├── ops/daily_batch/     # Planner, phases, trace
│   ├── outcome_attribution/ # Read-only analytics
│   ├── providers/           # Yahoo client
│   ├── ranking/             # Strategies, factors, engine
│   ├── ranking_research/    # Report generators (non-prod)
│   ├── regime_policy/       # Engine, replay, metrics
│   ├── schemas/             # Pydantic v2 DTOs
│   ├── services/            # Orchestration
│   ├── stock_setup_evidence/ # SEE v2
│   ├── universe/            # Filters, NIFTY loader
│   ├── validation/          # Forward returns, IC
│   └── workspace_exit_research/  # Exit simulators
├── docs/                    # Legacy + research markdown
│   ├── AI/                  # This handover package
│   └── dailyruns/           # Dated ops logs
├── docker/                  # Dockerfile, compose
├── migrations/versions/     # Alembic 0001 → 0018
├── scripts/                 # 28 CLI utilities
├── tests/                   # unit + integration (312)
├── alembic.ini
├── pyproject.toml
└── README.md
```

---

## Branching

| Branch | Role |
|--------|------|
| `main` | Stable baseline |
| `feature/see-v2` | Active: SEE v2, ARGS research, committee Phase 2 |

---

## Config entry points

| File | Purpose |
|------|---------|
| `app/core/config.py` | `Settings` from env |
| `.env.example` | Template |
| `docker/docker-compose.yml` | Postgres + API |

---

## Where not to edit (without scope)

| Path | Reason |
|------|--------|
| `app/ranking/strategies/*` | Frozen factor definitions |
| `app/validation/*` core metrics | Frozen unless validation sprint |
| `migrations/versions/*` (old) | Immutable history — add new revision only |

---

## Related

- [CODE_MAP.md](../04_IMPLEMENTATION/CODE_MAP.md)
- [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md) — this file
