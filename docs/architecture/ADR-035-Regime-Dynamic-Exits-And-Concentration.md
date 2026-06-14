# ADR-035: Regime-Dynamic Stop-Loss, Slot Concentration & Time-Stop Removal

**Status:** PROPOSED — requires PO sign-off (changes PRD §5 exit policy and regime slot limits)
**Date:** 2026-06-10
**Relates to:** ADR-033 (Intraday Exit Monitor & Stop Override), ADR-034 (Recommendation
Trade Levels), PRD §5 (sizing/exits)
**Evidence:** `scripts/backtest_regime_stop.py` (in-memory, no-DB-write harness; deterministic)

---

## Context

Current production policy:

- **Static stops** — `advisory_stop_pct = −8%` (HITL exit), `critical_stop_pct = −10%`
  (auto only when flagged), regime-blind, evaluated vs `avg_cost` (ADR-033).
- **30-day time stop** — engine R-EXIT-04 (`max_holding_days = 30`) and the T2 exit
  monitor's time trigger force-close positions regardless of health.
- **Diffuse concentration** — `regime_slots` allows 6–8 positions; slot budget =
  `deployable / max_positions`.

A 4.4-year walk-forward backtest program (2022-01 → 2026-06, NIFTY-500 BUY signals from
the production recommendation engine, honest frictions: 15 bps/side fees ≈
STT+stamp+charges, 30 bps/side slippage, gap-through stop fills, EOD granularity)
tested each exit/sizing lever in isolation and combination. The market regime series
(`regime_history`, `^NSEI`: BULL/BEAR × LOW/HIGH-vol) switched 46 times in the period;
~half the switches were 1–5-day flickers.

### Lever scoreboard (all under identical honest frictions)

| Lever | Effect on CAGR | Verdict |
|---|---|---|
| Concentration 10 → 4–5 slots | **+5–6pp** | ✅ adopt |
| Remove 30-day time stop | **+3–6pp** | ✅ adopt |
| Regime-dynamic stops (vs flat −8%) | better risk-adjusted; equal return, −5pp DD, fewer trades | ✅ adopt |
| Flat ultra-tight stop (−1% all regimes) | looks best ONLY under optimistic capped fills; collapses under realistic fills (avg loss −1% → −3.4%) | ❌ reject |
| Bear-regime entry gate | −3pp (bear entries with tight stops are profitable) | ❌ reject |
| Trailing stop (−6% from peak) | −5pp; churns winners on routine pullbacks (1107 trades) | ❌ reject |
| Re-entry after stop-out | immediate: −6pp, DD 32%; confirmed: noise; re-entry win-rate = base rate (no selectivity) | ❌ reject |
| Regime debounce (3–5d confirmation) | −5pp; flickers are EARLY-WARNING signal, not noise — debounce delays bear tightening exactly when it matters | ❌ reject |

### Out-of-sample validation (selection metric pre-declared: Calmar)

Tune on 2022-01→2024-06; test blind on 2024-07→2026-06 (bear/chop-heavy hold-out):

| Config on TEST window | CAGR | Max DD | PF |
|---|---|---|---|
| Train-chosen (5/7/2/3 · 4 slots · no time stop) | +9.20% | 33.3% | 1.14 |
| In-sample champion (6/8/2/3 · 5 slots · no time stop) | +9.45% | 29.9% | 1.14 |
| Current-policy baseline (flat −8 · 10 slots · 30d) | +1.42% | 28.0% | 1.03 |

Findings:
1. **The structure transfers OOS**: ~+8pp CAGR over the current-policy baseline at
   similar drawdown, with train-chosen ≈ in-sample champion (the stop-map surface is a
   plateau — exact values are second-order; the structure is what matters).
2. **Absolute returns are regime-dependent**: full-period ~25% CAGR was earned mostly
   in the 2022–23 bull. Honest expectation: **mid-teens full-cycle, ~9–10% in
   bear/chop years**, OOS PF is thin (1.14).
3. **Risk disclosure**: a fully-deployed portfolio entering a bear-heavy window can
   draw down **30%+**. (Full-period DD figures are flattered by the harness's fixed
   slot sizing — see Limitations.)

## Decision

Adopt the **structural combination** for the paper pilot, behind config flags
(defaults preserve current behaviour until PO sign-off):

### D1. Regime-dynamic stop-loss
- New setting `regime_stop_map` keyed by regime label, defaults:
  `BULL_LOW_VOL: −6%, BULL_HIGH_VOL: −8%, BEAR_LOW_VOL: −2%, BEAR_HIGH_VOL: −3%`,
  fallback −4% when no regime is resolvable.
- The stop threshold is resolved at **evaluation time** from the latest
  `regime_history` row (`^NSEI`) — i.e. re-evaluated daily, **no debounce** (tested
  and rejected). A regime flip retoggles the stop for all open positions.
- `portfolio_positions.stop_loss_price` becomes **dynamic**: refreshed by
  mark-to-market / exit monitor rather than frozen at entry.
- ADR-034 pre-trade levels (`stop_advisory/critical` on recommendations) must use the
  **same map** so displayed and enforced stops agree.

### D2. Remove the 30-day time stop
- `EngineConfig.max_holding_days` becomes configurable; default **disabled**.
- T2 exit monitor time trigger disabled by the same flag.
- The rank-drop exit (rank > 40) remains the structural exit for decaying names —
  in the final backtest it produced 42% of exits and ALL top-5 winners exited via
  rank-drop after 56–107-day holds (impossible under the 30-day rule).

### D3. Concentration: 4–5 position slots
- `regime_slots.max_positions = 5` (PO may choose 4; OOS shows them equivalent).
- Cap interactions MUST be resolved at the same time (see Open Decisions): slot
  budget becomes ~17% of equity (0.85/5); EXCEPTIONAL sizing (×1.15) → 19.6% breaches
  the 18% `single_name_cap_pct`; two same-sector slots breach the 30% `sector_cap_pct`.

### Explicitly NOT adopted (tested, rejected)
Trailing stops; bear-regime entry gate; stop-out re-entry/watchlist; regime debounce;
flat tight stops. Recorded here so they are not re-proposed without new evidence.

## Open decisions (PO sign-off required)

| # | Decision | Options |
|---|---|---|
| 1 | Two-tier mapping | Map regime stops to the **advisory** tier with critical = advisory −2pp; or collapse to a single tier for paper pilot |
| 2 | Buys in defensive/crisis regimes | Backtest entered in bear (profitable, tight stops); current policy sets `max_buy_per_day = 0` in defensive. Align or keep gate? (Keeping the gate diverges from the evidence base.) |
| 3 | Time-stop removal vs PRD §5 | Confirm PRD amendment |
| 4 | Cap raises | `single_name_cap_pct` 0.18 → ~0.22; `sector_cap_pct` 0.30 → ~0.40; or keep caps and accept sizing clamps |
| 5 | Stop execution latency | Backtest exits same-day EOD; production T2 + HITL adds ≥1 day drift. Extend auto-exec (ADR-033 pattern) to regime stops in paper mode, or measure the drift first |

## Consequences

**Positive**
- OOS-validated ~+8pp CAGR over current policy at similar drawdown; fewer trades
  (less friction); winners allowed to compound (avg win +17% vs +14.5%).
- Stops become consistent end-to-end: recommendation display (ADR-034), exit monitor,
  and engine all read one regime-keyed map.
- All rejected levers documented with evidence — guardrail against future re-tuning.

**Negative / risks**
- **30%+ drawdown potential** for fresh capital in bear-heavy windows; PF thin (1.14)
  OOS — sizing of real capital must respect this, not the in-sample 14% DD.
- Concentration quadruples single-name accident exposure vs 10+ slots (gap risk
  through any stop).
- Regime-flip retoggles can fire a burst of stops in one session (operationally:
  up to all open positions in a day).
- Dynamic `stop_loss_price` complicates broker GTC-stop placement (ADR-033 TODO) —
  stops must be re-placed when the regime flips.

## Implementation sketch (no code in this ADR)

| Area | Change |
|---|---|
| `app/core/config.py` | `regime_stop_map` (JSON), `time_stop_enabled: bool = False`, flag to enable the whole policy |
| `exit_monitor/service.py`, `intraday_service.py` | resolve regime → stop% at evaluation time |
| `app/recommendation/engine.py` | `max_holding_days` configurable/off |
| `app/services/portfolio_service.py` | `_DEFAULT_REGIME_SLOTS` → 5; mark-to-market refreshes `stop_loss_price` |
| `PortfolioConfig` (active row + migration) | slots, cap percentages |
| `app/recommendation/trade_levels.py` | stops from `regime_stop_map` |
| Tests | per-regime stop resolution; flip-day retoggle; cap interactions; time-stop flag |

## Rollout plan

1. ✅ **DONE (2026-06-10)** — Land changes **flag-off** (current behaviour unchanged):
   `app/portfolio/regime_stops.py` (resolver), settings block in `app/core/config.py`,
   T2/T1 monitors, engine R-EXIT-04 gate, dynamic `stop_loss_price` in
   `mark_to_market`, ADR-034 levels wired to the resolver;
   `tests/unit/portfolio/test_regime_stops.py` (14 tests).
2. Fix the harness slot-sizing artifact (scale slot budget with NAV) and re-run the
   OOS protocol — affects both return and DD estimates.
3. **Shadow paper run**: enable flags in paper pilot only; compare realized
   exits/NAV against backtest expectations for ≥4 weeks (tracking error report).
4. Walk-forward re-validation (yearly expanding-window re-tune) before any live
   consideration.
5. PO sign-off on Open Decisions 1–5 → promote.

## DB-replay findings (2026-06-10, `scripts/replay_paper_trade_v3.py`)

A full through-the-database replay (₹1 Cr, 2022-01→2026-06, fees 15 bps + slippage
30 bps) **reproduced the harness result almost exactly** (+168.9% vs +168.8%, CAGR
+24.97%, DD 14.13%, PF 1.69) — but only after isolating two production T2 defects
that destroyed earlier replay attempts:

1. **`EXIT_REGIME` trigger churn** — `check_regime_change` fires for every position
   every day while the posture is defensive; in 2022's bear this forced near-daily
   exit→re-enter cycles at ~90 bps round trip, driving NAV from ₹1 Cr to ₹13 K
   (−99.9%). The trigger must be made one-shot/stateful (fire on transition, not
   level) or excluded from auto-execution.
2. **`_get_current_rank` cross-strategy misfire** — it reads the stock's rank from
   the single latest completed ranking run of ANY strategy; a breakout_v1 position
   scored against a reversal_v1 run gets a garbage rank → `EXIT_RANK_DROP` fires
   the day after entry. Even with EXIT_REGIME filtered, this churned NAV −98.7%.
   It must use the best (MIN) rank across strategies for the as_of date — the
   validated basis.

Until both are fixed, the T2 monitor's rank/regime triggers MUST NOT auto-execute
under the ADR-035 config. Also fixed during the replay: missing index on
`recommendation_results.portfolio_position_id` (migration `20260611_0029`) — without
it, position deletes/wipes take minutes due to per-row FK scans.

## Limitations of the evidence

- EOD granularity; long-only; fills at close ± slippage; no intraday stop fills.
- Harness uses **fixed slot allocation from starting capital** (does not compound
  position size with NAV) — flatters late-period DD and dilutes late-period returns;
  the OOS test window (fresh capital, fully deployed) is the more honest risk read.
- Single hold-out window; one historical path; 2024-07→2026-06 is bear/chop-heavy
  (conservative for returns, realistic for risk).
- Production exit triggers not modelled (alpha decay, regime-defensive exit, edge
  degraded, liquidity/concentration) will create tracking differences vs backtest.

## Alternatives considered

1. **Keep static −8/−10 stops** — baseline OOS: +1.4% CAGR, PF 1.03. Rejected.
2. **Tighten stops globally** (flat −1%) — artifact of optimistic fill assumptions;
   rejected under realistic fills.
3. **Trailing / debounce / re-entry / bear-gate** — each tested and net-negative
   (see scoreboard). Rejected with evidence.
4. **Tune stop values further** — the response surface is a plateau (±1pp); further
   tuning is curve-fitting. Structure adopted, values left at 6/8/2/3.
