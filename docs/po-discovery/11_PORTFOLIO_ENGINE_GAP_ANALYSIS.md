# Portfolio Engine Gap Analysis

> **⚠️ STALE (2026-06-05):** Portfolio engine and paper execution are **shipped** (`app/portfolio/`, `app/execution/`, 22 `/portfolio/*` APIs).  
> **Current truth:** [`docs/IMPLEMENTATION_SUMMARY.md`](../IMPLEMENTATION_SUMMARY.md), [`docs/audit/PAPER_TRADING_AUDIT.md`](../audit/PAPER_TRADING_AUDIT.md).  
> Remaining gaps: `portfolio_id` on NAV/cash/recon tables, portfolio API integration tests, live Zerodha stub.

**Date:** 2026-06-05 (snapshot before Phase 2 completion)  
**Scope:** Paper trading, portfolio positions, construction, APIs

---

## Executive summary (historical)

At time of writing portfolio capabilities were **schema-only stubs** — **services, APIs, and tests now exist**.

| Layer | Status |
|-------|--------|
| DB schema | **Exists** |
| ORM models | **Exists** |
| Domain package | **Placeholder** |
| Services | **Missing** |
| API routes | **Missing** |
| Tests | **Zero** |
| Batch integration | **Missing** |

**Maturity score:** 12/100 — see [PRODUCT_MATURITY_SCORECARD.md](./PRODUCT_MATURITY_SCORECARD.md)

---

## Data model (implemented)

### PaperTrade

**File:** `app/models/paper_trade.py`  
**Table:** `paper_trades` (since `migrations/versions/20260530_0001_initial_schema.py`)

| Field | Purpose |
|-------|---------|
| `stock_id` | FK to stocks |
| `side` | Buy/sell (4 char) |
| `quantity`, `fill_price`, `fill_quantity` | Execution details |
| `status` | `TradeStatus` enum — `app/core/constants.py` |
| `ranking_run_id` | Optional link to ranking provenance |
| `idempotency_key` | Unique — supports safe retries |
| `metadata` | JSONB extensibility |

### PortfolioPosition

**File:** `app/models/portfolio_position.py`  
**Table:** `portfolio_positions`

| Field | Purpose |
|-------|---------|
| `stock_id` | Holding |
| `quantity`, `avg_cost` | Position economics |
| `market_value`, `weight_pct` | Snapshot fields |
| `as_of`, `is_current` | Temporal + current flag |

---

## Domain packages (stubs)

| Package | File | Content |
|---------|------|---------|
| Portfolio | `app/portfolio/__init__.py` | Docstring: "Deterministic portfolio domain — added in later phases." |
| Execution | `app/execution/__init__.py` | Docstring: "Deterministic execution domain — added in later phases." |
| Risk | `app/risk/__init__.py` | Empty/minimal (**assumption** from glob) |

**No files beyond `__init__.py` in portfolio/execution.**

---

## API gap

| Expected endpoint (hypothetical) | Exists? |
|----------------------------------|---------|
| `POST /paper-trades` | ✗ |
| `GET /portfolio/positions` | ✗ |
| `GET /portfolio/summary` | ✗ |
| `POST /portfolio/rebalance` | ✗ |

**Router scan:** `app/api/router.py` — no portfolio or paper-trade routers.

---

## Integration gaps

| Integration point | Current state |
|-------------------|---------------|
| Ranking → paper buy | No wire; ranking_run_id field unused |
| ARGS CRO → trade | Explicitly not trade approval (PRD G8) |
| Daily batch → portfolio update | No phase |
| Exit research → close position | Analytics only |
| Regime policy → position sizing | Research replay only — `app/regime_policy/replay.py` computes portfolio_return for simulation, not live book |

---

## ARGS portfolio_context (placeholder)

**Builder default:**

```python
# app/args/builders/investment_review_packet_builder.py
"portfolio_context": {"existing_position": False}
```

**RC plugin** references `portfolio_context:*` evidence refs — `app/args/plugins/rc.py`  
**Packet views** pass portfolio block to RC/CRO — `app/args/committee_packet_views.py`  
**Evidence validator** validates portfolio refs — `app/workspace_args/evidence_validator.py`

**Gap:** Without live positions, risk committee context is **synthetic**.

---

## Related research (not portfolio engine)

| Module | Relation |
|--------|----------|
| `app/regime_policy/replay.py` | Simulated equal-weight portfolio returns |
| `app/ranking_research/backtest.py` | `_portfolio_metrics_for_runs` — research backtest |
| Exit research | Policy simulators on historical ranks |

These inform **future** portfolio rules but are not production portfolio services.

---

## PRODUCT_STATUS alignment

From [`docs/AI/01_PRODUCT/PRODUCT_STATUS.md`](../AI/01_PRODUCT/PRODUCT_STATUS.md):

| Item | Status |
|------|--------|
| Paper trading services | Not started ✓ confirmed |
| Portfolio construction | Not started ✓ confirmed |
| Live broker | Out of scope ✓ confirmed |

PLATFORM-HANDOFF: "Paper trading / portfolio — **Stub** — Tables exist; services not implemented" — **verified**.

---

## Blockers to portfolio engine (from roadmap)

| Blocker | Source |
|---------|--------|
| Exit framework at scale | `CURRENT_PRIORITIES.md` P1 |
| Ranking calibration PO sign-off | P0 |
| Product spec for sizing rules | **Unknown** — see [14_PO_QUESTIONS_FOR_FOUNDER.md](./14_PO_QUESTIONS_FOR_FOUNDER.md) |

---

## Minimum viable portfolio engine (hypothetical — not implemented)

For PO planning only (**assumption**, not spec):

1. `PaperTradeService` — create/fill/cancel with idempotency
2. `PortfolioService` — recompute positions from fills
3. `GET /portfolio/positions`, `POST /paper-trades`
4. Feed `portfolio_context` in ARGS from live positions
5. Link exit research thresholds to position monitor job

---

## Test gap

| Area | Tests |
|------|-------|
| paper_trade model | 0 |
| portfolio_position model | 0 |
| trade execution | 0 |

---

## References

- [04_API_CATALOG.md](./04_API_CATALOG.md) — missing APIs section
- [10_RECOMMENDATION_ENGINE_GAP_ANALYSIS.md](./10_RECOMMENDATION_ENGINE_GAP_ANALYSIS.md)
- [03_DOMAIN_MODEL.md](./03_DOMAIN_MODEL.md)
- [`docs/PLATFORM-HANDOFF-2026.md`](../PLATFORM-HANDOFF-2026.md) §2
