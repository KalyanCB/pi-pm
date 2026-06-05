# Pi-PM Frontend — Screen Specifications

**Track:** D — Frontend Architecture & React Native Web Foundation  
**Version:** 1.0  
**Date:** 2026-06-05

Per-screen purpose, user goals, actions, and data dependencies. View models align with [docs/mobile/SCREEN_SPECIFICATIONS.md](../mobile/SCREEN_SPECIFICATIONS.md).

---

## Priority Legend

| Priority | Phase |
|----------|-------|
| **P1** | Phase 2 — core owner workflow |
| **P2** | Phase 3 — committee, analytics, settings |

---

## P1 Screens

### 1. Dashboard

| Attribute | Detail |
|-----------|--------|
| **Route** | `/` |
| **Priority** | P1 |
| **Purpose** | Single-glance portfolio health and today's action summary |

**User goals:**
- Know NAV and today's change immediately
- See if portfolio is within risk tolerance
- Know how many BUY recommendations and pending exits exist
- Detect data health issues (reconciliation)

**Primary actions:**
| Action | API / Navigation |
|--------|------------------|
| Pull to refresh | Refetch dashboard composite |
| Tap pending exits | Navigate to Exit Approval Queue |
| Tap BUY preview | Navigate to Recommendations (BUY tab) |
| Tap risk level | Navigate to Portfolio (risk section) |
| Tap reconciliation banner | Show reconciliation detail modal |

**Data dependencies:**

| Hook | Endpoints |
|------|-----------|
| `useDashboard()` | `GET /portfolio/dashboard` |
| | `GET /analytics/recommendations/trust` |
| | `GET /recommendations/daily?action=BUY` |

**View model:** `DashboardViewModel` — see mobile spec §2.2

**Components:** `TrustScoreCard`, `PortfolioSummaryCard`, `RiskIndicator`, `RecommendationCard` (preview), `ReconciliationBanner`, `MetricStrip`

---

### 2. Recommendations

| Attribute | Detail |
|-----------|--------|
| **Route** | `/recommendations` |
| **Priority** | P1 |
| **Purpose** | Daily machine recommendations by action type with committee overlay |

**User goals:**
- Review all BUY candidates for today
- Monitor WATCH list for promotion/demotion
- Identify EXIT_APPROVED positions
- Spot HIGH_CONCERN committee flags before acting

**Primary actions:**
| Action | API / Navigation |
|--------|------------------|
| Switch BUY/WATCH/EXIT tab | Client filter (Zustand `activeTab`) |
| Sort by conviction/rank | Client sort on API fields |
| Filter HIGH_CONCERN first | Client filter on joined advisory |
| Tap card | Navigate to Recommendation Detail |
| Open HITL queue | Navigate to queue / modal |
| Ask copilot | Open copilot with prefill |

**Data dependencies:**

| Hook | Endpoints |
|------|-----------|
| `useRecommendationCards()` | `GET /recommendations/daily` or `/{run_id}` |
| | `GET /investment-committee/latest` |
| | `GET /investment-committee/{id}/packets` |
| | `GET /stocks/{symbol}` (enrichment) |

**View model:** `RecommendationListViewModel`

**Components:** `RecommendationCard`, `ConvictionBadge`, `RecommendationReasonList`, `CommitteeAdvisoryCard`, `HighConcernBanner`, `ActionTabs`

---

### 2a. Recommendation Detail (sub-screen)

| Attribute | Detail |
|-----------|--------|
| **Route** | `/recommendations/:symbol` |
| **Priority** | P1 |

**User goals:** Understand conviction breakdown, rationale, committee narrative.

**Primary actions:** Copilot shortcut, HITL approve/reject (if queued), navigate to committee.

**Data dependencies:** `useRecommendationDetail()` — detail, why-not, packet, report, symbol analytics.

---

### 3. Portfolio

| Attribute | Detail |
|-----------|--------|
| **Route** | `/portfolio` |
| **Priority** | P1 |
| **Purpose** | Holdings, performance, attribution, and risk exposure |

**User goals:**
- See all open positions with P&L
- Understand performance vs benchmark (alpha from API)
- Review attribution by strategy, conviction, sector
- Monitor risk concentration and alerts

**Primary actions:**
| Action | API / Navigation |
|--------|------------------|
| Switch section tabs | Zustand `portfolioSection` |
| Set date range | Refetch performance/attribution |
| Tap position | Position detail |
| Tap risk alert | Expand alert details |
| Refresh | Invalidate portfolio queries |

**Data dependencies:**

| Hook | Endpoints |
|------|-----------|
| `usePortfolioScreen()` | `GET /portfolio/summary` |
| | `GET /portfolio/positions` |
| | `GET /portfolio/performance` |
| | `GET /portfolio/risk` |
| | `GET /portfolio/attribution` |
| | `GET /portfolio/nav-history` |
| | `GET /portfolio/benchmark` |
| | `GET /portfolio/reconciliation` |

**Gated state:** 409 on performance/risk/attribution → `isGated: true`

**Components:** `PortfolioSummaryCard`, `PortfolioPositionCard`, `DataTable`, `AttributionChart`, `RiskIndicator`, `NavSparkline`, `ReconciliationBanner`

---

### 4. Exit Approval Queue

| Attribute | Detail |
|-----------|--------|
| **Route** | `/exits` |
| **Priority** | P1 |
| **Purpose** | Human confirm/reject for pending portfolio exit recommendations |

**User goals:**
- Review exit triggers and urgency
- Confirm or reject each pending exit
- Understand why exit was recommended

**Primary actions:**
| Action | API |
|--------|-----|
| Confirm exit | `POST /portfolio/exits/{id}/confirm` |
| Reject exit | `POST /portfolio/exits/{id}/reject` |
| Explain | Copilot `explain_exit` |
| Tap symbol | Position detail or recommendation detail |

**Data dependencies:**

| Hook | Endpoint |
|------|----------|
| `usePendingExits()` | `GET /portfolio/exits` |

**Note:** Distinct from `EXIT_APPROVED` recommendation action — document clearly in UI.

**Components:** `ExitApprovalCard`, `UrgencyBadge`, `TriggerList`

---

### 5. Copilot

| Attribute | Detail |
|-----------|--------|
| **Route** | `/copilot` (full screen mobile) / side panel (desktop) |
| **Priority** | P1 |
| **Purpose** | Grounded natural-language Q&A over Pi-PM data |

**User goals:**
- Ask why a stock is recommended
- Understand portfolio risk and performance in plain language
- Get cited answers traceable to DB records

**Primary actions:**
| Action | API |
|--------|-----|
| Send question | `POST /copilot/ask` |
| Tap citation | Navigate via `citationNavigation` |
| Tap suggested prompt | Pre-fill input |
| View history | `GET /copilot/audit` |

**Data dependencies:** `useAskCopilot()`, `useCopilotStore`, `useCopilotAudit()`

**Components:** `CopilotMessage`, `CitationPanel`, `SuggestedPrompts`, `RefusalBanner`

---

## P2 Screens

### 6. Investment Committee

| Attribute | Detail |
|-----------|--------|
| **Route** | `/committee` |
| **Priority** | P2 |
| **Purpose** | Advisory review packets, committee actions, governance narratives |

**User goals:**
- See latest committee review status
- Filter HIGH_CONCERN symbols
- Read CRO governance narrative per symbol
- Compare machine action vs committee advisory

**Primary actions:**
| Action | API / Navigation |
|--------|------------------|
| Poll while running | `GET /investment-committee/{id}` every 30s |
| Filter HIGH_CONCERN | Client filter |
| Tap symbol | Committee detail |
| Read full report | `GET /{id}/report` |

**Data dependencies:** `useCommitteeScreen()` — latest, packets, report, members

**Components:** `CommitteeAdvisoryCard`, `HighConcernBanner`, `CommitteeActionGrid`, `GovernanceNarrative`, `CommitteeReviewHeader`

---

### 6a. Committee Detail (sub-screen)

| Attribute | Detail |
|-----------|--------|
| **Route** | `/committee/:symbol` |
| **Priority** | P2 |

**Data dependencies:** packet, report, explain endpoints.

---

### 7. Performance Analytics

| Attribute | Detail |
|-----------|--------|
| **Route** | `/analytics` |
| **Priority** | P2 |
| **Purpose** | Recommendation engine trust, calibration, committee effectiveness |

**User goals:**
- Understand overall trust score components
- See conviction band calibration
- Review committee advisory track record

**Primary actions:** Date range filter, drill into band/regime breakdown.

**Data dependencies:**

| Hook | Endpoints |
|------|-----------|
| `useAnalyticsScreen()` | `GET /analytics/recommendations/trust` |
| | `GET /analytics/recommendations/summary` |
| | `GET /analytics/recommendations/conviction` |
| | `GET /analytics/recommendations/committee` |

**Components:** `TrustScoreCard`, `CalibrationChart`, `BandMetricsTable`, `CommitteeEffectivenessTable`

---

### 8. Settings

| Attribute | Detail |
|-----------|--------|
| **Route** | `/settings` |
| **Priority** | P2 |
| **Purpose** | Local preferences and connection config |

**User goals:** Configure API URL (dev), default strategy, theme.

**Primary actions:** Persist to Zustand + AsyncStorage/localStorage.

**Data dependencies:** None (local only). Future: `GET /auth/me`.

**Components:** `SettingsForm`, `ThemeToggle`, `StrategyPicker`

---

## Cross-Screen Modals

| Modal | Trigger | Priority |
|-------|---------|----------|
| HITL Queue | Recommendations FAB | P1 |
| Copilot Panel | Any screen "Ask" button | P1 |
| Reconciliation Detail | Banner tap | P1 |
| Committee Poll Progress | Committee screen | P2 |

---

## Screen → Hook → Component Map

| Screen | Hook | Top-level component |
|--------|------|---------------------|
| Dashboard | `useDashboard` | `DashboardScreen` |
| Recommendations | `useRecommendationCards` | `RecommendationsScreen` |
| Recommendation Detail | `useRecommendationDetail` | `RecommendationDetailScreen` |
| Portfolio | `usePortfolioScreen` | `PortfolioScreen` |
| Exit Queue | `usePendingExits` | `ExitApprovalScreen` |
| Copilot | `useAskCopilot` + store | `CopilotScreen` |
| Committee | `useCommitteeScreen` | `CommitteeScreen` |
| Analytics | `useAnalyticsScreen` | `AnalyticsScreen` |
| Settings | `useSettingsStore` | `SettingsScreen` |

---

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-05 | Initial screen specifications |
