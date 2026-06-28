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

- Evaluates **OPEN** positions only (`position_status=OPEN`, `is_current=true`). Some API
  descriptions say "ACTIVE" loosely — the canonical status string is **`OPEN`**.
- **Two-tier monitor (ADR-033, scaffolding IMPLEMENTED):**
  - **T2 daily swing** — `exit_monitor/service.py` (`ExitMonitorService`), `monitor_tier=DAILY`.
    Once daily post-close on **EOD close**. Triggers: rank drop, alpha decay, regime, time,
    stop loss, trailing, concentration, liquidity. **Never auto-executes.**
  - **T1 intraday price monitor** — `exit_monitor/intraday_service.py`
    (`IntradayExitMonitorService`), `monitor_tier=INTRADAY`. Price triggers only
    (`EXIT_STOP_LOSS`, `EXIT_TRAILING_STOP`) via an injected `QuoteProvider`
    (`LastCloseQuoteProvider` default; Kite live = TODO).
- **Stop loss is NOT hardcoded** anymore. Sourced from `Settings`:
  `ADVISORY_STOP_PCT` (default **−8%**) and `CRITICAL_STOP_PCT` (default **−10%**). PRD-07
  cites −6% — code/config default is −8%; PO confirms one value at ADR-033 sign-off.
- **Critical-stop auto-exec is OFF by default** (`AUTO_EXIT_ON_CRITICAL_STOP=false`). When on,
  T1 auto-sells via `PaperTradeService` with audit `actor_id=system`,
  `reason=AUTO_EXIT_RISK_OVERRIDE`. Entries are **never** auto-bypassed.
- Still pending for ADR-033 (see RTM `ADR-033`): live Kite `QuoteProvider`, intraday scheduler
  (1–5 min NSE session), notification delivery wiring, broker GTC stop at entry, and **PO
  sign-off (A–G)**.
- `stop_loss_price` column exists on `portfolio_positions` (DB) but is **not exposed** on
  position API or UI yet.
- `confirm_exit` (`POST /portfolio/exits/{exit_id}/confirm`) executes paper SELL when paper
  mode active.

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

## Execution realism: fill precedence & cost stack

`PaperTradeService._fill_price` resolves the fill in **this precedence** (all default OFF →
legacy same-bar close fill, byte-identical):

1. **`REALISTIC_FILLS_ENABLED`** — next-session **VWAP** (first `VWAP_WINDOW_MINUTES`) from
   `market_data_intraday`, plus a **square-root market-impact** cost
   (`IMPACT_SPREAD_BPS/2 + IMPACT_COEFF_BPS·√(order_value/ADV)`). See
   `app/services/intraday_fill_service.py`. **Falls back** to (2) then (3) when intraday
   data for the next session is missing.
2. **`NEXT_OPEN_FILLS_ENABLED`** — next trading day's OPEN ± `COST_SLIPPAGE_BPS`.
3. **Legacy** — `fill_date` close ± `COST_SLIPPAGE_BPS` (default 5 bps).

**Gotchas:**
- **Statutory charges are separate** from slippage — STT/stamp/exchange/SEBI/GST/brokerage
  live in `_leg_cost` under **`TRANSACTION_COSTS_ENABLED`** (P-24), *not* in the fill price.
  They **compose** with realistic fills automatically. Don't double-count STT in slippage.
- Realistic fills need an **intraday backfill first**: `scripts/backfill_intraday_fills.py`
  (targeted to traded symbols' entry/exit windows). Needs the **Kite historical add-on**.
- Per-trade fill diagnostics (`vwap`, `impact_bps`, `participation_pct`) land in
  `paper_trades.metadata_["fill_model"]` — only when a realistic quote was produced.
- The hardcoded `"slippage_bps": 5.0` in trade metadata is **legacy/cosmetic** — trust
  `fill_model.impact_bps` for the realistic path.

---

## Common agent mistakes

1. Assuming latest recommendations should be BUY — check validation status first.
2. Treating WATCH as entry queue — it's monitor lane only (ADR-032).
3. Editing ranking from ARGS/LLM paths.
4. Auto-selling on exit monitor without checking HITL / paper flags.
5. Using stale `docs/HANDOFF.md` — use `context/generated/PLATFORM_STATE.md`.
