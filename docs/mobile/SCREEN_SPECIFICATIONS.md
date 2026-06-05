# Pi-PM Mobile — Screen Specifications

**Track:** B — Mobile Readiness & API Productization  
**Version:** 1.0  
**Date:** 2026-06-05

Per-screen data contracts, UI sections, and backend field bindings. React Native implementation is out of scope; these specs define the **view models** mobile clients should build from API responses.

---

## 1. Conventions

| Term | Meaning |
|------|---------|
| **Screen Model** | TypeScript/interface the RN app constructs from 1+ API calls |
| **Source API** | Backend endpoint providing raw data |
| **Required** | MVP must have; screen blocked without it |
| **Optional** | Enhances UX; graceful empty state if missing |
| **Client join** | Mobile merges multiple API responses |

**Formatting rules:**
- Percentages: backend returns numeric (e.g. `12.5` = 12.5%); mobile appends `%`
- Dates: ISO 8601 strings from API; display in local timezone
- Markdown: committee `narrative` rendered with MD component

---

## 2. Dashboard Screen

**Route:** `/` (tab: Home)  
**Purpose:** One-glance portfolio health + today's action count

### 2.1 Layout Sections

```
┌─────────────────────────────────────┐
│  Reconciliation Banner (if !PASS) │
├─────────────────────────────────────┤
│  NAV Card                           │
│  ₹{nav}  {today_change_pct}         │
│  Alpha {alpha_pct}  Cash {cash_pct} │
├─────────────────────────────────────┤
│  Trust Score  │  Risk Level         │
│  {trust}      │  {risk_level}       │
├─────────────────────────────────────┤
│  Pending Exits ({pending_exits}) →  │
│  Active Positions: {active_positions}│
├─────────────────────────────────────┤
│  Today's BUY ({buy_count}) →        │
│  [symbol cards preview]             │
├─────────────────────────────────────┤
│  Risk Alerts (max 3)                │
└─────────────────────────────────────┘
```

### 2.2 Screen Model: `DashboardScreenModel`

```typescript
interface DashboardScreenModel {
  // Portfolio health
  nav: number | null;
  todayChangePct: number | null;
  alphaPct: number | null;
  cashPct: number | null;
  activePositions: number;
  pendingExits: number;

  // Risk
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'UNKNOWN';
  riskAlerts: RiskAlertChip[];  // max 3 displayed

  // Analytics
  trustScore: number | null;    // 0-1, display as percentage

  // Data health
  reconciliationStatus: 'PASS' | 'WARNING' | 'FAIL' | null;
  isAnalyticsGated: boolean;    // true when reconciliation FAIL

  // Preview strip
  buyCount: number;
  buyPreview: RecommendationCardPreview[];  // top 3

  // Optional
  regimePosture?: string;
  asOfDate: string;
}

interface RiskAlertChip {
  code: string;
  level: string;
  message: string;
}

interface RecommendationCardPreview {
  symbol: string;
  action: 'BUY' | 'WATCH' | 'EXIT_APPROVED';
  convictionBand: string;
  convictionScore: number;
}
```

### 2.3 API Binding

| Field | Source | API field |
|-------|--------|-----------|
| `nav` | `GET /portfolio/dashboard` | `nav` |
| `todayChangePct` | Same | `today_change_pct` |
| `alphaPct` | Same | `alpha_pct` |
| `cashPct` | Same | `cash_pct` |
| `activePositions` | Same | `active_positions` |
| `pendingExits` | Same | `pending_exits` |
| `riskLevel` | Same | `risk_level` |
| `riskAlerts` | Same | `risk_alerts` |
| `reconciliationStatus` | Same | `reconciliation_status` |
| `trustScore` | `GET /analytics/recommendations/trust` | `overall_trust_score` |
| `buyCount` | `GET /recommendations/daily` | `buy_count` |
| `buyPreview` | Same | `strategies[].results[]` (first 3, client-resolved symbols) |

### 2.4 Interactions

| Tap target | Navigation |
|------------|------------|
| Pending exits row | Exits screen |
| Today's BUY | Recommendations (BUY tab) |
| Risk level | Portfolio (Risk section) |
| Trust score | Analytics detail (post-MVP) or tooltip |
| Symbol preview card | Recommendation detail |

### 2.5 Empty / Error States

| Condition | Message |
|-----------|---------|
| `nav == null` | "No NAV history. Run daily batch." |
| `reconciliation_status == FAIL` | Banner: "Analytics unavailable — reconciliation failed" |
| `buy_count == 0` | "No BUY recommendations today" |
| `trustScore == null` | Hide trust widget or show "Insufficient outcome data" |

---

## 3. Recommendations Screen

**Route:** `/recommendations` (tab)  
**Purpose:** Daily actionable list by action type

### 3.1 Layout

```
┌─────────────────────────────────────┐
│  [BUY] [WATCH] [EXIT]     as_of_date│
├─────────────────────────────────────┤
│  ┌─ Symbol Card ─────────────────┐  │
│  │ RELIANCE  BUY  HIGH (82)      │  │
│  │ • RANK_TOP_20 • VALIDATED     │  │
│  │ CRO: APPROVE  ⚠ HIGH_CONCERN  │  │
│  └───────────────────────────────┘  │
│  ...                                │
├─────────────────────────────────────┤
│  FAB → HITL Queue ({queue_count})   │
└─────────────────────────────────────┘
```

### 3.2 Screen Model: `RecommendationListScreenModel`

```typescript
interface RecommendationListScreenModel {
  asOfDate: string;
  activeTab: 'BUY' | 'WATCH' | 'EXIT_APPROVED';
  items: RecommendationCardModel[];
  counts: { buy: number; watch: number; exit: number };
  strategyName: string;  // primary strategy filter
}

interface RecommendationCardModel {
  resultId: string;
  stockId: string;
  symbol: string;              // client-resolved
  action: 'BUY' | 'WATCH' | 'EXIT_APPROVED' | 'HOLD' | 'REJECT';
  rank: number | null;
  convictionScore: number;
  convictionBand: 'BLOCKED' | 'LOW' | 'MEDIUM' | 'HIGH' | 'EXCEPTIONAL';
  reasonCodes: string[];
  reasonLabels: string[];      // client-mapped from codes

  // Committee overlay (client join)
  committeeAdvisory: CommitteeAdvisoryOverlay | null;
}

interface CommitteeAdvisoryOverlay {
  croAdvisoryAction: string | null;
  highConcern: boolean;
  highConcernCommittees: string[];
  committeeActions: Record<string, string>;  // code → action
  displayNames: Record<string, string>;
}
```

### 3.3 API Binding

| Tab | API | Filter |
|-----|-----|--------|
| BUY | `GET /recommendations/daily` | `action=BUY` |
| WATCH | `GET /recommendations/daily` | `action=WATCH` |
| EXIT | `GET /recommendations/{run_id}` | `action=EXIT_APPROVED` |
| Committee overlay | `GET /investment-committee/{id}/packets` | Join on `symbol` |
| Symbol | `GET /stocks/{symbol}` or stock lookup cache | `stock_id` → `symbol` |

### 3.4 Reason Code Display

Map `reason_codes` to short labels (client i18n table). Examples:

| Code | Label |
|------|-------|
| `RANK_TOP_20` | Top 20 rank |
| `VALIDATION_PASS` | Validation passed |
| `REGIME_RISK_ON` | Risk-on regime |
| `EXIT_TRIGGER_RANK` | Rank deterioration |

### 3.5 HIGH_CONCERN Treatment

When `committeeAdvisory.highConcern === true`:
- Red/warning badge on card
- Sort option: "Concerns first"
- Tap → Committee detail with `HIGH_CONCERN` filter

---

## 4. Recommendation Detail Screen

**Route:** `/recommendations/:symbol`  
**Purpose:** Full conviction + rationale + committee narrative

### 4.1 Screen Model: `RecommendationDetailScreenModel`

```typescript
interface RecommendationDetailScreenModel {
  symbol: string;
  asOfDate: string;
  strategyName: string;

  // Machine recommendation
  action: string;
  rank: number | null;
  compositeScore: number | null;
  convictionScore: number;
  convictionBand: string;
  convictionComponents: ConvictionComponents;
  reasonCodes: string[];

  // Committee
  committeeAdvisory: CommitteeAdvisoryOverlay | null;
  governanceSummary: string | null;
  governanceNarrative: string | null;  // markdown
  governanceConfidence: number | null;

  // Supplementary
  symbolAnalytics: SymbolAnalyticsSummary | null;
  whyNot: WhyNotPayload | null;  // if WATCH/REJECT
}

interface ConvictionComponents {
  rankQuality: number;
  validation: number;
  icFactor: number;
  regime: number;
  exitHealth: number;
  configVersion: string;
}

interface SymbolAnalyticsSummary {
  winRate: number | null;
  avgAlphaPct: number | null;
  lastAction: string | null;
  closedOutcomes: number;
}
```

### 4.2 API Binding

| Section | API |
|---------|-----|
| Core | `GET /recommendations/{run_id}/stocks/{symbol}` |
| Why-not | `GET /recommendations/why-not/{symbol}` (conditional) |
| Committee packet | `GET /investment-committee/{id}/packets?symbol={symbol}` |
| Narrative | `GET /investment-committee/{id}/report` → match `symbol` |
| Analytics | `GET /analytics/recommendations/symbol/{symbol}` |

### 4.3 Actions

| Action | Behavior |
|--------|----------|
| "Ask Copilot" | Navigate to Copilot with `question: "Why is {symbol} recommended?"` |
| "View Committee" | Navigate to Committee detail for symbol |
| Approve (if in queue) | `POST /recommendations/{result_id}/approve` |

---

## 5. HITL Queue Screen

**Route:** `/recommendations/queue`  
**Purpose:** Human-in-the-loop entry approvals

### 5.1 Screen Model

```typescript
interface HitlQueueScreenModel {
  items: HitlQueueItem[];
}

interface HitlQueueItem {
  resultId: string;
  stockId: string;
  symbol: string;          // client-resolved
  action: string;
  convictionScore: number;
  convictionBand: string;
  reasonCodes: string[];
  recommendationRunId: string;
}
```

### 5.2 API Binding

| Operation | API |
|-----------|-----|
| List | `GET /recommendations/queue` |
| Approve | `POST /recommendations/{result_id}/approve` |
| Reject | `POST /recommendations/{result_id}/reject` |

---

## 6. Portfolio Screen

**Route:** `/portfolio` (tab)  
**Purpose:** Positions, performance, attribution, risk

### 6.1 Sub-sections (scroll or tabs)

1. **Summary** — equity, cash, P&L, regime
2. **Positions** — open holdings
3. **Performance** — return metrics
4. **Attribution** — breakdown charts
5. **Risk** — exposure, alerts

### 6.2 Screen Model: `PortfolioScreenModel`

```typescript
interface PortfolioScreenModel {
  summary: PortfolioSummaryModel;
  limits: RegimeLimitsModel;
  positions: PositionRowModel[];
  performance: PerformanceModel | null;   // null if gated
  attribution: AttributionModel | null;
  risk: RiskModel | null;
  navHistory: NavHistoryPoint[];
  benchmark: BenchmarkModel | null;
  reconciliation: ReconciliationModel;
  isGated: boolean;
}

interface PortfolioSummaryModel {
  totalEquity: number;
  deployableCapital: number;
  cashAvailable: number;
  cashPct: number;
  marketValue: number;
  unrealizedPnl: number;
  activePositions: number;
  regimePosture: string;
}

interface PositionRowModel {
  id: string;
  symbol: string | null;
  quantity: number;
  avgCost: number;
  marketValue: number | null;
  unrealizedPnl: number | null;
  weightPct: number | null;
  convictionBand: string | null;
  strategyName: string | null;
  sector: string | null;
  positionStatus: 'OPEN' | 'CLOSED';
}

interface PerformanceModel {
  totalReturnPct: number | null;
  cagrPct: number | null;
  alphaPct: number | null;
  sharpeRatio: number | null;
  maxDrawdownPct: number | null;
  winRate: number | null;
  tradingDays: number;
}

interface AttributionModel {
  byStrategy: AttributionBucket[];
  byConvictionBand: AttributionBucket[];
  bySector: AttributionBucket[];
  byCommitteeAdvisory: AttributionBucket[];
  totalAlphaPct: number | null;
}

interface AttributionBucket {
  label: string;
  count: number;
  totalReturnPct: number | null;
  avgAlphaPct: number | null;
  winRate: number | null;
  contributionPct: number | null;
}

interface RiskModel {
  riskLevel: string;
  grossExposurePct: number | null;
  cashPct: number | null;
  largestPositionPct: number | null;
  sectorExposures: Record<string, number>;
  alerts: RiskAlertChip[];
}

interface NavHistoryPoint {
  asOfDate: string;
  totalEquity: number;
  dayReturnPct: number | null;
  alphaPct: number | null;
}
```

### 6.3 API Binding

| Section | API |
|---------|-----|
| Summary | `GET /portfolio/summary` |
| Limits | `GET /portfolio/limits` |
| Positions | `GET /portfolio/positions` |
| Performance | `GET /portfolio/performance` |
| Attribution | `GET /portfolio/attribution` |
| Risk | `GET /portfolio/risk` |
| NAV chart | `GET /portfolio/nav-history` |
| Benchmark | `GET /portfolio/benchmark` |
| Reconciliation | `GET /portfolio/reconciliation` |

### 6.4 Gated State (409)

When `GET /portfolio/performance` returns 409:
- Set `isGated: true`
- Show `performance`, `attribution`, `risk` as unavailable
- Display reconciliation status prominently

---

## 7. Pending Exits Screen

**Route:** `/portfolio/exits`  
**Purpose:** Review and confirm exit recommendations

### 7.1 Screen Model

```typescript
interface PendingExitsScreenModel {
  items: PendingExitModel[];
}

interface PendingExitModel {
  id: string;
  symbol: string | null;
  status: 'PENDING' | 'CONFIRMED' | 'REJECTED' | 'EXPIRED';
  urgency: 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL';
  triggers: string[];
  triggerDetails: Record<string, unknown>;
  currentRank: number | null;
  daysHeld: number | null;
  unrealizedPnlPct: number | null;
  asOfDate: string;
}
```

### 7.2 API Binding

| Operation | API |
|-----------|-----|
| List | `GET /portfolio/exits` |
| Confirm | `POST /portfolio/exits/{id}/confirm` |
| Reject | `POST /portfolio/exits/{id}/reject?reason=` |
| Explain | `POST /copilot/ask` — "Why exit {symbol}?" |

### 7.3 Urgency Visual Scale

| Urgency | Color tier |
|---------|------------|
| CRITICAL | Red |
| HIGH | Orange |
| NORMAL | Default |
| LOW | Muted |

---

## 8. Committee Screen

**Route:** `/committee` (tab)  
**Purpose:** Investment committee advisory review

### 8.1 Sub-views

1. **Review list** — latest review header
2. **Symbol list** — packets with advisory badges
3. **Symbol detail** — full packet + narrative
4. **HIGH_CONCERN** — filtered list

### 8.2 Screen Model

```typescript
interface CommitteeScreenModel {
  review: CommitteeReviewHeader;
  symbols: CommitteeSymbolModel[];
  highConcernCount: number;
  members: CommitteeMembersModel;
}

interface CommitteeReviewHeader {
  reviewId: string;
  status: string;
  asOfDate: string;
  universeCode: string;
  strategyName: string;
  candidatesReviewed: number;
  governanceReportsIssued: number;
}

interface CommitteeSymbolModel {
  symbol: string;
  packetId: string;
  recommendation: PacketRecommendation;
  advisory: CommitteeAdvisoryOverlay;
  governanceSummary: string | null;
  governanceConfidence: number | null;
}

interface PacketRecommendation {
  action: string;
  convictionScore: number;
  convictionBand: string;
  reasonCodes: string[];
}

interface CommitteeMembersModel {
  committees: { code: string; displayName: string; role: string }[];
  chair: { code: string; displayName: string; role: string };
  advisoryActions: string[];
  escalationRule: string;
}
```

### 8.3 API Binding

| Section | API |
|---------|-----|
| Header | `GET /investment-committee/latest` |
| Packets | `GET /investment-committee/{id}/packets` |
| Report | `GET /investment-committee/{id}/report` |
| Explain | `GET /investment-committee/{id}/explain` |
| Members | `GET /investment-committee/committees/members` |

### 8.4 Advisory Action Display

| Action | Badge |
|--------|-------|
| `APPROVE` | Green |
| `WATCH` | Yellow |
| `REJECT` | Red |
| `EXIT_APPROVED` | Orange |
| `HIGH_CONCERN` | Red + escalation icon |

**Rule:** Machine `payload.recommendation.action` and committee `cro_advisory_action` may differ — show both with labels "Engine" vs "Committee".

---

## 9. Committee Detail Screen

**Route:** `/committee/:symbol`  
**Purpose:** Full governance narrative for one symbol

### 9.1 Screen Model

```typescript
interface CommitteeDetailScreenModel {
  symbol: string;
  narrative: string;           // markdown from report
  summary: string;
  confidence: number | null;
  committeeReviews: CommitteeReviewRow[];
  croRationale: string | null;
  dissentSummary: string | null;
  packet: CommitteeSymbolModel;
}

interface CommitteeReviewRow {
  committeeCode: string;
  displayName: string;
  findings: string[];
  confidence: number | null;
  advisoryAction: string;
}
```

### 9.2 API Binding

| Field | API |
|-------|-----|
| `narrative`, `summary` | `GET /{id}/report` → `reports[]` match symbol |
| `committeeReviews` | `GET /{id}/explain` → `committee_reviews[]` |
| `croRationale` | `GET /{id}/explain` → `cro_reviews[]` |
| `packet` | `GET /{id}/packets?symbol={symbol}` |

---

## 10. Copilot Screen

**Route:** `/copilot` (tab or modal)  
**Purpose:** Grounded Q&A

### 10.1 Layout

```
┌─────────────────────────────────────┐
│  Suggested prompts (chips)          │
├─────────────────────────────────────┤
│  [Chat messages]                    │
│  User: Why is INFY a BUY?           │
│  Copilot: INFY conviction is 78...  │
│  [citation: rec_results/abc123]     │
├─────────────────────────────────────┤
│  [Input field]              [Send]  │
└─────────────────────────────────────┘
```

### 10.2 Screen Model

```typescript
interface CopilotScreenModel {
  messages: CopilotMessage[];
  sessionId: string | null;
  suggestedPrompts: string[];
}

interface CopilotMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  refused?: boolean;
  citations?: CitationModel[];
  uncitedClaims?: string[];
  latencyMs?: number;
}

interface CitationModel {
  ref: string;
  sourceTable: string | null;
  sourceField: string | null;
  sourceValue: string | null;
}
```

### 10.3 Suggested Prompts (by context)

| Context | Prompts |
|---------|---------|
| Dashboard | "What is my portfolio risk today?" |
| Recommendation | "Why is {symbol} a {action}?" |
| Portfolio | "Explain my performance this month" |
| Committee | "What did the committee say about {symbol}?" |
| Exit | "Why should I exit {symbol}?" |

### 10.4 API Binding

| Operation | API |
|-----------|-----|
| Ask | `POST /copilot/ask` |
| History | `GET /copilot/audit?limit=20` |

### 10.5 Citation Navigation

| `source_table` | Deep link |
|----------------|-----------|
| `recommendation_results` | Recommendation detail |
| `investment_review_packets` | Committee detail |
| `portfolio_positions` | Portfolio positions |
| `portfolio_exit_recommendations` | Pending exits |

---

## 11. Global Components

### 11.1 Reconciliation Banner

Shown on Dashboard + Portfolio when `reconciliation_status !== 'PASS'`.

```typescript
interface ReconciliationBannerModel {
  status: 'WARNING' | 'FAIL';
  discrepancyPct: number;
  message: string;
}
```

Source: `GET /portfolio/reconciliation`

### 11.2 Regime Badge

```typescript
interface RegimeBadgeModel {
  label: string;       // e.g. "risk_on"
  posture: string;     // risk_on | neutral | defensive | crisis
}
```

Source: `GET /portfolio/summary` → `regime_posture` or `GET /observability/regime/current`

### 11.3 Loading Strategy

| Screen | Strategy |
|--------|----------|
| Dashboard | Parallel fetch; skeleton cards |
| Recommendations | Stale-while-revalidate by `as_of_date` |
| Committee (running) | Poll 30s with progress indicator |
| Copilot | Single request; spinner until `latency_ms` returned |

---

## 12. Revision History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-05 | Initial screen specifications |
