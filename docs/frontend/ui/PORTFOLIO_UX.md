# Portfolio UX

## Sections (Tabbed / Scroll)

1. **Overview** — equity, cash %, unrealized P&L, regime posture
2. **Positions** — `PortfolioPositionCard` list
3. **Allocation** — donut from position weights
4. **Performance** — return, alpha, Sharpe + trend sparkline
5. **Attribution** — sector/strategy bars
6. **Risk** — level + alerts (or reconciliation gate message)

## Visualizations

| Chart | Data |
|-------|------|
| Allocation donut | `GET /portfolio/positions` weights |
| Sector exposure | positions grouped by sector |
| Performance trend | `GET /portfolio/nav-history` day_return_pct |
| Attribution bars | `GET /portfolio/attribution` by_sector |
| Cash deployment | summary cash_pct vs deployable |

## Reconciliation Gate

When attribution returns 409:

- Show amber banner
- Positions still visible
- Charts that require analytics show "Gate closed"

## Desktop

Two-column: positions list + allocation chart side-by-side.

## Mobile

Overview cards first, positions below fold.
