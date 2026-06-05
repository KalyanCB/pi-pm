# Pi-PM Frontend — Component Library

**Track:** D — Frontend Architecture & React Native Web Foundation  
**Version:** 1.0  
**Date:** 2026-06-05

Reusable component inventory for `packages/ui`. All components are **presentational** — they receive typed props and emit events; no direct API calls.

---

## 1. Component Tiers

| Tier | Location | Data fetching |
|------|----------|---------------|
| Atoms | `packages/ui/src/atoms/` | Never |
| Molecules | `packages/ui/src/molecules/` | Never |
| Organisms | `packages/ui/src/organisms/` | Never |
| Screens | `packages/ui/src/screens/` | Via hooks (only tier allowed) |
| Layouts | `apps/*/layouts/` | Never |

---

## 2. Atoms

### `MetricValue`

| Prop | Type | Description |
|------|------|-------------|
| `value` | `number \| string \| null` | Raw API value |
| `format` | `'currency' \| 'percent' \| 'number' \| 'integer'` | Display format only |
| `currency` | `string` | Default `₹` |
| `colorize` | `boolean` | Green/red for signed numbers |
| `size` | `'sm' \| 'md' \| 'lg'` | Typography scale |

**Usage:** NAV, alpha, P&L display. **Never computes** — formats backend value.

**Shared:** ✅ Web + native

---

### `Badge`

| Prop | Type | Description |
|------|------|-------------|
| `label` | `string` | Text |
| `variant` | `'default' \| 'success' \| 'warning' \| 'danger' \| 'info'` | Semantic color |
| `size` | `'sm' \| 'md'` | |

**Shared:** ✅

---

### `ActionBadge`

| Prop | Type | Description |
|------|------|-------------|
| `action` | `Action` | `BUY`, `WATCH`, `EXIT_APPROVED`, etc. |

Maps action enum to fixed colors. No client action logic.

**Shared:** ✅

---

## 3. Molecules

### `ConvictionBadge`

| Prop | Type | Description |
|------|------|-------------|
| `score` | `number` | `conviction_score` from API |
| `band` | `ConvictionBand` | `conviction_band` from API |
| `showScore` | `boolean` | Default true |
| `size` | `'sm' \| 'md' \| 'lg'` | |

Band → color mapping is **display-only** (fixed lookup table, not calculation).

```typescript
// Display map only — thresholds come from API band field
const BAND_COLORS: Record<ConvictionBand, string> = {
  BLOCKED: 'muted',
  LOW: 'warning',
  MEDIUM: 'info',
  HIGH: 'success',
  EXCEPTIONAL: 'accent',
};
```

**Shared:** ✅

---

### `RecommendationCard`

| Prop | Type | Description |
|------|------|-------------|
| `symbol` | `string` | |
| `action` | `Action` | Machine action |
| `rank` | `number \| null` | |
| `convictionScore` | `number` | |
| `convictionBand` | `ConvictionBand` | |
| `reasonCodes` | `string[]` | |
| `committeeAdvisory` | `CommitteeAdvisoryOverlay \| null` | Joined data |
| `onPress` | `() => void` | Navigate to detail |
| `onAskCopilot` | `() => void` | Optional |
| `layout` | `'card' \| 'row'` | Responsive variant |

**Usage:** Dashboard preview, Recommendations list. Desktop uses `row`; mobile uses `card`.

**Shared:** ✅ (layout prop switches density)

---

### `RecommendationReasonList`

| Prop | Type | Description |
|------|------|-------------|
| `reasonCodes` | `string[]` | API `reason_codes` |
| `reasonLabels` | `string[]` | Client i18n map (display only) |
| `maxVisible` | `number` | Collapse overflow |
| `direction` | `'horizontal' \| 'vertical'` | Chip vs list |

**Shared:** ✅

---

### `PortfolioPositionCard`

| Prop | Type | Description |
|------|------|-------------|
| `symbol` | `string \| null` | |
| `quantity` | `number` | |
| `avgCost` | `number` | |
| `marketValue` | `number \| null` | |
| `unrealizedPnl` | `number \| null` | |
| `weightPct` | `number \| null` | From API — not computed |
| `convictionBand` | `string \| null` | |
| `sector` | `string \| null` | |
| `onPress` | `() => void` | |

**Shared:** ✅

---

### `PortfolioSummaryCard`

| Prop | Type | Description |
|------|------|-------------|
| `totalEquity` | `number` | |
| `cashPct` | `number` | |
| `unrealizedPnl` | `number` | |
| `activePositions` | `number` | |
| `regimePosture` | `string` | |
| `todayChangePct` | `number \| null` | |
| `alphaPct` | `number \| null` | |

**Shared:** ✅

---

### `CommitteeAdvisoryCard`

| Prop | Type | Description |
|------|------|-------------|
| `croAdvisoryAction` | `string \| null` | |
| `committeeActions` | `Record<string, string>` | Code → action |
| `displayNames` | `Record<string, string>` | Code → label |
| `highConcern` | `boolean` | |
| `highConcernCommittees` | `string[]` | |
| `machineAction` | `string` | Shown alongside for comparison |
| `compact` | `boolean` | Single-line vs expanded |

**Rule:** Always show machine action and committee advisory **separately** labeled.

**Shared:** ✅

---

### `HighConcernBanner`

| Prop | Type | Description |
|------|------|-------------|
| `committees` | `string[]` | `high_concern_committees` |
| `displayNames` | `Record<string, string>` | |
| `onPress` | `() => void` | Navigate to committee detail |

**Shared:** ✅

---

### `RiskIndicator`

| Prop | Type | Description |
|------|------|-------------|
| `riskLevel` | `RiskLevel` | From API |
| `alerts` | `RiskAlert[]` | |
| `maxAlerts` | `number` | |
| `onPress` | `() => void` | |

**Shared:** ✅

---

### `TrustScoreCard`

| Prop | Type | Description |
|------|------|-------------|
| `score` | `number \| null` | `overall_trust_score` 0–1 |
| `calibration` | `CalibrationSummary \| null` | Optional breakdown |
| `showBreakdown` | `boolean` | P2 analytics link |

Displays `score * 100` as percentage — **multiplication for display only**, not recalculation of trust.

**Shared:** ✅

---

### `ExitApprovalCard`

| Prop | Type | Description |
|------|------|-------------|
| `symbol` | `string \| null` | |
| `urgency` | `ExitUrgency` | |
| `triggers` | `string[]` | |
| `daysHeld` | `number \| null` | |
| `unrealizedPnlPct` | `number \| null` | |
| `currentRank` | `number \| null` | |
| `onConfirm` | `() => void` | |
| `onReject` | `() => void` | |
| `onExplain` | `() => void` | |
| `isLoading` | `boolean` | Mutation state |

**Shared:** ✅

---

### `CopilotMessage`

| Prop | Type | Description |
|------|------|-------------|
| `role` | `'user' \| 'assistant'` | |
| `content` | `string` | |
| `intent` | `string \| null` | |
| `refused` | `boolean` | |
| `citations` | `Citation[]` | |
| `uncitedClaims` | `string[]` | |
| `onCitationPress` | `(citation: Citation) => void` | |

**Shared:** ✅

---

### `CitationPanel`

| Prop | Type | Description |
|------|------|-------------|
| `citations` | `Citation[]` | |
| `onPress` | `(citation: Citation) => void` | Deep link |

Renders `ref`, `source_table`, `source_field` as tappable chips.

**Shared:** ✅

---

## 4. Organisms

### `MetricStrip`

Horizontal row of `MetricValue` for dashboard header.

| Prop | Type |
|------|------|
| `metrics` | `Array<{ label: string; value; format }>` |

**Shared:** ✅ | **Desktop:** single row | **Mobile:** horizontal scroll

---

### `RecommendationList`

| Prop | Type |
|------|------|
| `items` | `RecommendationCardModel[]` |
| `layout` | `'card' \| 'table'` |
| `onItemPress` | `(symbol: string) => void` |
| `emptyMessage` | `string` |

**Desktop:** `table` layout with `DataTable`  
**Mobile:** `card` layout with `FlashList`

**Shared:** ✅ (layout prop)

---

### `PortfolioPositionsTable`

| Prop | Type |
|------|------|
| `positions` | `PositionRowModel[]` |
| `onRowPress` | `(symbol: string) => void` |
| `sortColumn` | `string` |
| `sortDirection` | `'asc' \| 'desc'` |
| `onSort` | `(column: string) => void` |

Sort operates on **API-provided fields only**.

**Shared:** ✅ | **Platform-specific:** `DataTable.web.tsx` / `DataTable.native.tsx`

---

### `AttributionBreakdown`

| Prop | Type |
|------|------|
| `buckets` | `AttributionBucket[]` |
| `title` | `string` |
| `variant` | `'bar' \| 'table'` |

**Shared:** ✅

---

### `CopilotChat`

| Prop | Type |
|------|------|
| `messages` | `CopilotMessageModel[]` |
| `suggestedPrompts` | `string[]` |
| `onSend` | `(question: string) => void` |
| `onCitationPress` | `(citation: Citation) => void` |
| `isLoading` | `boolean` |
| `inputValue` | `string` |
| `onInputChange` | `(text: string) => void` |

**Shared:** ✅

---

### `ReconciliationBanner`

| Prop | Type |
|------|------|
| `status` | `'WARNING' \| 'FAIL'` |
| `discrepancyPct` | `number` |
| `onPress` | `() => void` |

**Shared:** ✅

---

### `NavSparkline`

| Prop | Type |
|------|------|
| `data` | `NavHistoryPoint[]` | API series |
| `height` | `number` |

Renders chart from API points. **Does not compute returns** — uses `day_return_pct` when overlay needed.

**Shared:** ✅ | Chart renderer may use `.web.tsx` (SVG) vs `.native.tsx` (Skia)

---

## 5. Screens (Hook-connected)

| Screen | Hooks used | Key organisms |
|--------|------------|---------------|
| `DashboardScreen` | `useDashboard` | MetricStrip, TrustScoreCard, RecommendationList (preview) |
| `RecommendationsScreen` | `useRecommendationCards` | RecommendationList, ActionTabs |
| `PortfolioScreen` | `usePortfolioScreen` | PortfolioSummaryCard, PortfolioPositionsTable, AttributionBreakdown |
| `ExitApprovalScreen` | `usePendingExits` | ExitApprovalCard list |
| `CopilotScreen` | `useAskCopilot`, `useCopilotStore` | CopilotChat |
| `CommitteeScreen` | `useCommitteeScreen` | CommitteeAdvisoryCard list, GovernanceNarrative |

---

## 6. Shared vs Platform-Specific

| Component | Shared | Platform-specific |
|-----------|--------|-------------------|
| ConvictionBadge | ✅ | — |
| RecommendationCard | ✅ | `layout` prop |
| DataTable | Interface shared | `.web.tsx` / `.native.tsx` |
| Sidebar | — | `apps/web/layouts/Sidebar.web.tsx` |
| TabBar | — | `apps/mobile/layouts/TabBar.native.tsx` |
| CopilotPanel | — | `.web.tsx` (side panel) / full screen mobile |
| NavSparkline | Interface shared | Chart impl per platform |
| MarkdownRenderer | ✅ | `react-native-markdown-display` |

---

## 7. Storybook Catalog

Each molecule+ component gets a Storybook story with:

- Default state
- Loading skeleton
- Empty state
- HIGH_CONCERN variant
- Reconciliation gated variant

```
packages/ui/.storybook/
├── RecommendationCard.stories.tsx
├── ConvictionBadge.stories.tsx
├── TrustScoreCard.stories.tsx
└── ...
```

---

## 8. Component Composition Example

```
DashboardScreen
├── ReconciliationBanner (conditional)
├── MetricStrip
│   ├── MetricValue (nav)
│   ├── MetricValue (todayChange)
│   ├── MetricValue (alpha)
│   └── MetricValue (cash)
├── HStack
│   ├── TrustScoreCard
│   └── RiskIndicator
├── SectionHeader ("Pending Exits")
├── ExitApprovalCard (summary row → navigates)
├── SectionHeader ("Today's BUY")
└── RecommendationList (preview, max 3)
```

---

## 9. Revision History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-05 | Initial component library |
