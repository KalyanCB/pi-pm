# Investor Experience PRD — Track UI-X

## Product Positioning

**Pi-PM is:** Portfolio Manager + Investment Committee + AI Copilot + Decision Support System.

**Pi-PM is not:** Zerodha, Groww, Robinhood.

## Primary User Journey

```
Login → Portfolio Health → Today's Recommendations → Committee Concerns → Copilot Q&A → Approve/Reject
```

**Success:** First-time user completes this loop in **≤10 minutes** without documentation.

## Core Questions the UI Must Answer

| Screen | Questions |
|--------|-----------|
| Dashboard | How is my portfolio? What should I buy/sell? Can I trust today? What needs attention? |
| Recommendations | Why this symbol? How confident? Committee concerns? What action? |
| Committee | Who flagged HIGH_CONCERN? What did each committee say? |
| Copilot | Why recommended / not? Why exit? What's the evidence? |
| Portfolio | Where am I allocated? What's performing? What's the risk? |

## Feature Scope (UI-X)

| Phase | Deliverable |
|-------|-------------|
| 1 | Design system docs + token implementation |
| 2 | Information architecture + navigation |
| 3 | Dashboard experience + visualizations |
| 4 | Recommendation list + detail + trust indicators |
| 5 | Committee overview + HIGH_CONCERN priority |
| 6 | Copilot first-class (side panel desktop, full screen mobile) |
| 7 | Portfolio overview + charts |
| 8 | Responsive layouts |
| 9 | Approval workflow UX |
| 10 | Trust & explainability framework |

## Out of Scope

- Backend business logic changes
- Mock data
- Retail trading patterns (order tickets, watchlists, social)

## Personas

**Portfolio Owner** — reviews daily recommendations, approves entries/exits, consults committee advisory.

**Viewer** — read-only access to health, recommendations, committee, copilot.

## Non-Functional

- Dark-first, high information density
- Accessible (WCAG-oriented contrast + labels)
- Shared codebase: web + mobile via Expo
