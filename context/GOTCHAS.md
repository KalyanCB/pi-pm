# Pi-PM Gotchas & Anti-Patterns

**Canonical** — human-maintained. Read before changing recommendation, batch, exit, or HITL flows.

---

## Validation tail → WATCH not BUY

Per-run forward validation needs ~5 sessions (`insufficient_data` on latest T). **Latest day is usually WATCH-heavy**, not a broken engine. Deploy lane is T−k matured runs (see ADR-032).

**Do not** auto-upgrade WATCH to BUY via ARGS or historical validation.

---

## HITL vs paper auto-execute

| `HITL_ENABLED` | `PAPER_TRADING_ENABLED` | Behaviour |
|----------------|-------------------------|-----------|
| `false` | `true` | Paper pilot auto-approves BUYs; `PaperPilotOps` runs exit monitor + auto-exec |
| `true` | any | Human must approve; **`PaperPilotOps` / exit monitor may be skipped** in daily batch |

Exit monitor API (`POST /portfolio/exits/run`) always works manually regardless.

---

## Exit monitor scope & cadence

- Evaluates **OPEN** positions only (`position_status=OPEN`, `is_current=true`).
- Default cadence: **once daily** post-close using **EOD close** price.
- Stop loss: **−8%** hardcoded in `exit_monitor/service.py` (ADR-033 proposes −8% advisory / −10% auto).
- `stop_loss_price` column exists on `portfolio_positions` (DB) but is **not exposed** on position API or UI yet.
- `confirm_exit` executes paper SELL when paper mode active.
- Rank/regime/time exits are **T2 daily** — not intraday (ADR-033 PROPOSED).

---

## Dual exit paths

1. **Engine** `EXIT_APPROVED` on active positions (rank/regime rules).
2. **Exit monitor** → `portfolio_exit_recommendations` → human confirm.

Replay historically bypassed monitor (fixed in `scripts/replay_paper_trade.py`); old DB rows may lack `portfolio_exit_recommendations`.

---

## Portfolio summary NAV

`get_summary()` uses **`portfolio_nav_history` latest row**, not `portfolio_configs.total_equity` (often ₹1L seed).

---

## Ranking default

Default strategy: **`momentum_v1`** (`app/core/config.py`). Registry also has `breakout_v1`, `reversal_v1`, `low_vol_v1`.

---

## ARGS / committee boundaries

Committee output is stored and displayed — **must not** change `action`, conviction, or sizing. `HIGH_CONCERN` is a flag, not a veto unless human rejects.

---

## Auth defaults

`AUTH_ENABLED` defaults `true` in code; local `.env` may set `false`. JWT secret defaults to `change-me-in-production` — rotate before live.

---

## Live trading guards

`ENABLE_LIVE_TRADING=false` by default. Zerodha adapter returns `not_implemented` for real orders. See `context/canonical/runbooks/LIVE_TRADING_SAFETY_CHECKLIST.md`.

---

## Common agent mistakes

1. Assuming latest recommendations should be BUY — check validation status first.
2. Treating WATCH as entry queue — it's monitor lane only (ADR-032).
3. Editing ranking from ARGS/LLM paths.
4. Auto-selling on exit monitor without checking HITL / paper flags.
5. Using stale `docs/HANDOFF.md` — use `context/generated/PLATFORM_STATE.md`.
