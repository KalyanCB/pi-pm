# Portfolio Engine — Product Requirements

**Version:** Phase 2.0  
**Date:** 2026-06-05  
**Baseline:** Schema-only today — [11_PORTFOLIO_ENGINE_GAP_ANALYSIS.md](../po-discovery/11_PORTFOLIO_ENGINE_GAP_ANALYSIS.md) (12/100 maturity)

---

## 1. Purpose

Manage **dynamic capital**, **regime-based position count**, **per-name allocation**, **risk limits**, and **cash** for the swing book. Feeds truthful `portfolio_context` into ARGS and position-aware recommendations ([01](../product/01_RECOMMENDATION_ENGINE_PRD.md)).

**Out of scope v1:** Live broker execution (integration points only — [11](../product/11_HUMAN_IN_LOOP_EXECUTION_PRD.md)).

---

## 2. Goals

| ID | Goal |
|----|------|
| PG-1 | Reconcile positions from paper (then live) fills |
| PG-2 | Enforce max concurrent swings by regime |
| PG-3 | Allocate capital by conviction band within slots |
| PG-4 | Maintain explicit cash buffer |
| PG-5 | Block BUY when limits breached |

---

## 3. Capital model

| Concept | Definition | Default (PO tunable) |
|---------|------------|------------------------|
| `total_equity` | Cash + mark-to-market positions | Owner input / config |
| `deployable_capital` | `total_equity * deploy_pct` | 85% |
| `cash_floor` | Minimum cash % | 15% |
| `reserve_capital` | Not deployable (fees buffer) | 2% |

**Cash allowed:** New BUYs only if `cash_available ≥ slot_allocation`.

---

## 4. Regime-based position count

Uses `regime_policy_decisions` + current regime ([REGIME_DESIGN.md](../AI/03_DESIGN/REGIME_DESIGN.md)) — **does not** rerank.

| Regime bucket | Max ACTIVE positions | Max new BUY/day |
|---------------|----------------------|-----------------|
| Risk-on | 8 | 2 |
| Neutral | 6 | 1 |
| Defensive | 4 | 0 (WATCH only) |
| Crisis | 2 | 0; prefer EXIT_APPROVED review |

PO signs off table after exit research backfill ([po-discovery 13](../po-discovery/13_ROADMAP_RECOMMENDATION.md) P1.1).

---

## 5. Allocation rules (deterministic)

Within deployable capital:

```
slot_budget = deployable_capital / max_active_slots
position_notional = slot_budget * conviction_weight
```

| conviction_band | weight |
|-----------------|--------|
| EXCEPTIONAL | 1.15 (cap single name 18% NAV) |
| HIGH | 1.0 |
| MEDIUM | 0.75 |
| LOW | 0 (no new BUY) |

**Quality over quantity:** If eligible BUYs > slots, take highest `conviction_score` until slots filled; remainder `WATCH`.

**Single-name limit:** `weight_pct` ≤ 18% NAV.

**Sector limit (v1):** Max 30% NAV per GICS sector — requires sector on `stocks` metadata (verify ingest).

---

## 6. Integration points

| Consumer | Data supplied |
|----------|---------------|
| Recommendation Engine | `slots_available`, `existing_position`, sector headroom |
| ARGS packet | `portfolio_context: { existing_position, weight_pct, sector_exposure, cash_pct }` |
| Paper trading | Target `quantity` from `position_notional` / last close |
| Mobile dashboard | NAV, day P&L, allocation chart |

**Today:** [`portfolio_context: {existing_position: false}`](../../app/args/builders/investment_review_packet_builder.py) — **must** be replaced.

---

## 7. APIs (proposed)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/portfolio/summary` | NAV, cash, deployable |
| GET | `/api/v1/portfolio/positions` | Current `is_current=true` |
| GET | `/api/v1/portfolio/limits` | Regime slots, headroom |
| POST | `/api/v1/portfolio/config` | Owner equity / deploy_pct |
| POST | `/api/v1/portfolio/recompute` | Admin rebuild from fills |

---

## 8. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC-PE-01 | Sum of position market values + cash = total_equity within 0.1% |
| AC-PE-02 | BUY blocked when ACTIVE count ≥ regime max |
| AC-PE-03 | ARGS packet `portfolio_context` matches DB for symbol under review |
| AC-PE-04 | Recompute idempotent from `paper_trades` ledger |

---

## 9. Dependencies

| Dependency | Milestone |
|------------|-----------|
| Paper trading PRD | M2 |
| Recommendation lifecycle | M2 |
| Regime policy PO table | M2 |
| `portfolio_positions` ORM | Exists — [`portfolio_position.py`](../../app/models/portfolio_position.py) |

---

## 10. Future position sizing (not MVP)

MVP sizing remains conviction-weighted slot budget (§5). PO approved documenting a **future** multi-factor formula for post-M2 research — **do not implement** until backtest + sign-off.

```
position_size ∝ conviction × volatility_adjustment × liquidity_adjustment × regime_adjustment
```

| Factor | Role (future) |
|--------|----------------|
| `conviction` | Band weight from deterministic conviction only |
| `volatility` | Reduce notional for high ATR names |
| `liquidity` | Cap vs ADV participation |
| `regime` | Scale deployable slice in defensive/crisis |

**Guardrail:** No LLM input to any factor. Committee `HIGH_CONCERN` may warn in UI but does not enter formula.

---

## 11. References

- [11_PORTFOLIO_ENGINE_GAP_ANALYSIS.md](../po-discovery/11_PORTFOLIO_ENGINE_GAP_ANALYSIS.md)
- [PO_SIGNOFF_2026_06_04.md](../po/PO_SIGNOFF_2026_06_04.md)
- [app/portfolio/__init__.py](../../app/portfolio/__init__.py) (stub)
- [regime_policy/replay.py](../../app/regime_policy/replay.py) (simulation only today)
