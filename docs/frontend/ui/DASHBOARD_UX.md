# Dashboard UX

## Purpose

Answer five questions in one viewport:

1. How is my portfolio performing?
2. What should I buy?
3. What should I sell?
4. Can I trust today's recommendations?
5. Is anything requiring attention?

## Layout (Desktop)

```
┌─ Portfolio Summary (NAV · Return · Alpha · Cash) ─────────────┐
├─ Trust + Risk + Pilot Health ──────────────────────────────────┤
├─ NAV Trend │ Alpha Trend │ Trust Trend ─────────────────────────┤
├─ Pending Exits │ Committee Alerts │ Today's Recs Summary ────────┤
└─ Allocation Donut │ Recommendation Distribution ───────────────┘
```

## Layout (Mobile)

Single column, priority order:

1. NAV + today change
2. Trust score + risk badge
3. Pending exits (tappable)
4. BUY count / HIGH_CONCERN count
5. Sparkline (collapsed)
6. Committee alert banner if any

## Components

| Component | Data Source |
|-----------|-------------|
| `PortfolioSummaryCard` | `/portfolio/dashboard` + `/portfolio/summary` |
| `NavTrendCard` | `/portfolio/nav-history` |
| `AlphaCard` | dashboard `alpha_pct` + nav-history |
| `CashCard` | dashboard `cash_pct` |
| `RiskCard` | dashboard `risk_level` + alerts |
| `TrustScoreCard` | `/analytics/recommendations/trust` + `/pilot/dashboard/trust` |
| `PendingExitCard` | dashboard `pending_exits` |
| `PilotHealthCard` | `/pilot/dashboard/health` |
| `RecommendationSummaryCard` | `/pilot/dashboard/recommendations` → `today` |

## Interactions

- Pending exits → `/recommendations` (EXIT tab)
- Committee alerts → `/committee`
- BUY summary → `/recommendations` (BUY tab)
- Trust card → expands calibration/stability/reliability

## Empty / Error States

- Reconciliation warning inline (amber)
- Analytics gate closed → muted charts with explanation
- Loading: skeleton cards, not spinners alone
