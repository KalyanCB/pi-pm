---
generated_at: 2026-06-28T03:28:38Z
git_sha: 6e7db17
git_branch: feat/hybrid-regime-exit
---

# Pi-PM Agent Context

**Universal entry point** for Cursor, Claude Code, Devin, and human developers.

## 1. What this system is

Personal Intelligence Portfolio Manager — deterministic **ingest → rank → validate → recommend → HITL → paper/live execution** for Indian NSE swing book (~15–30 sessions).

## 2. Non-negotiables (PO sign-off)

1. Deterministic ranking is sacred — same inputs → same outputs.
2. Validation tail is sacred — do not fake `completed` status.
3. LLMs **must not** influence ranking, conviction, sizing, or trade approval.
4. Human approves entries and exits — ADR-033 critical-stop **auto-override is gated OFF by default** (`AUTO_EXIT_ON_CRITICAL_STOP=false`); needs PO sign-off (A–G) before any live auto-exec.
5. ARGS / committee is **advisory** — cannot change `action`.

## 3. Session bootstrap (load in order)

| Depth | File | When |
|-------|------|------|
| **L0** | `context/generated/PLATFORM_STATE.md` | Always — branch, tests, migration |
| **L0b** | `context/GOTCHAS.md` | Before batch/HITL/exit changes |
| **L1** | `context/generated/IMPLEMENTATION_STATUS.md` | Feature work — designed/planned/done/gaps |
| **L2** | `context/generated/REQUIREMENTS.rtm.yaml` | Traceability, audits |
| **L3** | `context/generated/GAPS_AND_DEBT.md` | What's left off |
| **L4** | `context/canonical/INDEX.md` | ADRs & PRDs (self-contained) |
| **L4b** | `context/GOTCHAS.md` | Batch/HITL/exit anti-patterns |
| **L5** | `context/generated/API_SCHEMAS.json` | API contracts |
| **L5** | `context/generated/DATABASE_SCHEMA.md` | Schema detail |
| **L5** | `context/generated/ENV_CATALOG.md` | All env flags |
| **L5** | `context/generated/OPS_SCRIPTS.md` | Batch/replay scripts |
| **L5** | `context/generated/CANONICAL_LINK_CHECK.md` | Broken link report |

**If `git_sha` below ≠ current `git rev-parse --short HEAD`, run:**
```bash
uv run python scripts/generate_context.py
```

## 4. Live snapshot

| Field | Value |
|-------|-------|
| git_sha | `6e7db17` |
| branch | `feat/hybrid-regime-exit` |
| migration_head | `20260625` |
| tests_collected | 861 |
| proposed_items | 1 |
| not_started_items | 3 |
| partial_items | 20 |

| ID | Capability | Status |
|----|------------|--------|
| G1 | Deterministic ranking | IMPLEMENTED |
| G2 | Forward-return validation | IMPLEMENTED |
| G3 | NIFTY 500 daily batch | PARTIALLY_IMPLEMENTED |
| G4 | Audit traceability | IMPLEMENTED |
| G5 | Research analytics | IMPLEMENTED |
| G6 | ARGS governance | IMPLEMENTED |
| G7 | Stock Setup Evidence Engine v2 | IMPLEMENTED |
| G8 | No LLM ranking/sizing/approval | IMPLEMENTED |
| R-ENTRY | Entry rules (R-ENTRY-01..06) | IMPLEMENTED |
| R-HOLD | Hold active positions (R-HOLD-01) | IMPLEMENTED |
| R-EXIT | Exit triggers (R-EXIT-01..04) | IMPLEMENTED |
| R-ARGS | ARGS boundaries (R-ARGS-01..04) | IMPLEMENTED |

## 5. Do not use for truth

- Legacy `docs/HANDOFF.md`, `docs/PLATFORM-HANDOFF-2026.md` — **stale**, being replaced by `context/`.
- Sprint reports, `docs/dailyruns/`, experiment result dumps — **archive only**.
- Always prefer `context/generated/` over hand-written status docs.

## 6. Key areas — quick orientation

| Area | Implemented | Next |
|------|-------------|------|
| Recommendation engine | Engine + APIs + UI history | ADR-032 gate modes (PO decision) |
| Exit monitor | Daily OPEN positions, UI EXIT tab | ADR-033 intraday + notifications |
| Paper trading | Replay + auto when HITL off | Backfill exit_recommendations in old DB |
| Live execution | Paper adapter + Zerodha stub | S1 broker orders, risk gates |
| Frontend | Dashboard, Recs, Portfolio, Committee, Copilot | /analytics, push alerts |

## 7. Commands

```bash
docker compose -f docker/docker-compose.yml up --build
uv run pytest tests/ -q
uv run python scripts/generate_context.py
```

## 8. Agent rules

- Cite requirement IDs (`R-EXIT`, `ADR-033`) and file paths from `REQUIREMENTS.rtm.yaml`.
- Check `status` before assuming a feature exists.
- Do not infer implementation from PRD prose alone.
- Minimize scope; match existing code conventions.
