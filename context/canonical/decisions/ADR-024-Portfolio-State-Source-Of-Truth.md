# ADR-024: Portfolio State as Source of Truth (M2.2)

**Status:** Accepted  
**Date:** 2026-06-05  
**Deciders:** Product Owner, Engineering Lead  
**Supersedes:** N/A — hardens ADR-021 portfolio layer  
**Related:** [ADR-021](./ADR-021-Recommendation-Platform-Architecture.md), [ADR-022](./ADR-022-Recommendation-Performance-Framework.md), [05_PORTFOLIO_ENGINE_PRD.md](../product/05_PORTFOLIO_ENGINE_PRD.md)

---

## Context

The MVP Portfolio Engine (M2.1) established capital allocation, regime slots, and paper trade simulation. However, it lacks:

1. **Reconciliation** — no daily verification that Cash + Positions = NAV
2. **Exit automation** — no service evaluating ACTIVE positions for exit triggers
3. **Analytics** — no return, risk, or attribution metrics derived from the portfolio ledger
4. **Benchmarking** — no comparison against NIFTY 500 / NIFTY 50
5. **NAV history** — no time-series of portfolio value for performance tracking

Without these, Pi-PM cannot answer: *"What do I own, how is it performing, and what should I do next?"*

---

## Decision

**The portfolio state (positions + cash ledger + NAV history) is the operational source of truth.** Recommendations are advisory artifacts that inform portfolio decisions but do not control them.

### Canonical lineage

```
Recommendation
  → Approval (human confirms)
    → Paper Trade (fill simulation)
      → Position (opened from fill)
        → Cash Ledger entry (capital deployed)
          → NAV History snapshot (daily)
            → Outcome (closed with P&L)
```

Every step is persisted and traceable. No portfolio state is inferred — it is always derived from recorded events.

### New entities

| Entity | Table | Role |
|--------|-------|------|
| `PortfolioNavHistory` | `portfolio_nav_history` | Daily NAV snapshot |
| `CashLedger` | `portfolio_cash_ledger` | Append-only cash movement log |
| `PortfolioReconciliationReport` | `portfolio_reconciliation_reports` | Daily recon result |
| `ExitRecommendation` | `portfolio_exit_recommendations` | Machine exit triggers for human confirmation |

### Exit automation (advisory only)

The Exit Monitor evaluates ACTIVE positions daily against 8 triggers. It **writes `ExitRecommendation` rows**. It does **not** execute trades or mutate positions. A human must confirm via `POST /portfolio/trades/exit` (or reject).

### Reconciliation as a hard gate

Before any analytics are served, the latest reconciliation must be `PASS` or `WARNING`. A `FAIL` status blocks `/performance`, `/attribution`, `/risk`, and `/benchmark` endpoints with a 409 response explaining the discrepancy.

### Analytics are read-only projections

All portfolio analytics (return, alpha, drawdown, Sharpe, attribution) are computed from immutable ledger records. They never write back to positions, recommendations, or the conviction formula.

---

## Why portfolio state, not recommendation state

| Concern | Solution |
|---------|---------|
| Recommendation may be CANDIDATE but never filled | Only filled positions count in NAV |
| Multiple recommendations for same symbol over time | Position ledger has single current record |
| Conviction score may change on re-run | Position records the conviction at entry, immutably |
| ARGS advisory may evolve | Portfolio analytics use `committee_advisory` at entry (denormalised on outcome) |

---

## Invariants

1. `SUM(cash_ledger.amount) + SUM(open_positions.market_value) = total_equity` (within tolerance)
2. Every `PortfolioPosition` traces to a `PaperTrade` which traces to a `RecommendationApproval`
3. `ExitRecommendation` never auto-executes — requires human `POST /portfolio/trades/exit`
4. No analytics metric feeds back into conviction or recommendation engine
5. All analytics are deterministic: same DB state → same output

---

## Consequences

### Positive
- Portfolio can be fully audited from ledger events without re-running recommendations
- NAV history enables CAGR, drawdown, and Sharpe computation
- Reconciliation provides a daily health gate before relying on analytics
- Exit automation closes the loop from research exit signals to actionable human decisions

### Negative / constraints
- More tables = more migration complexity
- Analytics are retrospective — need closed outcomes to be meaningful
- Reconciliation may fail during early paper trading when data is sparse

---

## References

- [05_PORTFOLIO_ENGINE_PRD.md](../product/05_PORTFOLIO_ENGINE_PRD.md)
- [06_PAPER_TRADING_PRD.md](../product/06_PAPER_TRADING_PRD.md)
- [07_EXIT_DECISION_FRAMEWORK.md](../product/07_EXIT_DECISION_FRAMEWORK.md)
- [ADR-021](./ADR-021-Recommendation-Platform-Architecture.md)
