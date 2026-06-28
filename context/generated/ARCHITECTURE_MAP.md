---
generated_at: 2026-06-28T03:28:38Z
generator: scripts/generate_context.py
---

# Architecture Map

## Backend modules (`app/`)

| Module | Responsibility |
|--------|----------------|
| `ranking/` | Deterministic factor ranking (momentum_v1, breakout_v1, reversal_v1, low_vol_v1) |
| `validation/` | Forward-return IC, deciles, insufficient_data tail |
| `recommendation/` | BUY/WATCH/EXIT/HOLD engine, conviction, RCEE |
| `portfolio/` | Positions, sizing, exit monitor, reconciliation, NAV |
| `execution/` | Unified ExecutionService, paper + Zerodha adapters |
| `args/` | Investment committee packets, LLM agents (advisory only) |
| `copilot/` | Grounded investor Q&A |
| `ops/` | Daily batch, paper pilot, HITL gate, pilot alerting |
| `replay/` | Experiment replay engine (configs in `configs/`) |
| `api/v1/` | FastAPI routers |

## Domain boundaries

- **Ranking/Validation** never call LLM for scores.
- **Recommendation engine** sets `action`; committee cannot mutate it.
- **Exit monitor** creates recommendations; human confirms (except paper auto, or ADR-033 critical-stop auto-exec when `AUTO_EXIT_ON_CRITICAL_STOP=true` — OFF by default).
- **ExecutionService** is the only path from APPROVED → position change.

## Canonical decisions

Self-contained under `context/canonical/` — see `context/canonical/INDEX.md`.

## Gotchas

See `context/GOTCHAS.md` before changing validation, HITL, exit monitor, or batch flows.
