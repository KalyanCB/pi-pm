# Pi-PM Mobile — DTO Gap Analysis

**Track:** B — Mobile Readiness & API Productization  
**Version:** 1.0  
**Date:** 2026-06-05

Identifies gaps between **existing backend APIs** and **mobile-optimized screen models**. No ranking, validation, recommendation, or portfolio **calculation logic** changes proposed — only new response shapes, joins, and enrichment layers.

---

## 1. Executive Summary

| Category | Count |
|----------|-------|
| ✅ Ready (use as-is) | 18 endpoints |
| ⚠️ Usable with client work | 12 endpoints |
| ❌ Missing DTO / endpoint | 14 gaps |
| 🚫 Production blockers (non-DTO) | 3 (auth, push, sessions) |

**Highest-impact gaps:**
1. `RecommendationResultRead` lacks `symbol` — forces N+1 stock lookups
2. `GET /portfolio/dashboard` incomplete vs `PortfolioDashboardDTO` (no `trust_score`, contributors)
3. No merged recommendation + committee advisory endpoint
4. Committee packets are full JSONB — too heavy for list cards
5. No copilot session history API

---

## 2. Gap Severity Matrix

| ID | Gap | Severity | MVP workaround | Proposed resolution |
|----|-----|----------|----------------|---------------------|
| G-01 | No `symbol` on recommendation results | **P0** | Client cache `stock_id → symbol` | Add `symbol` to `RecommendationResultRead` |
| G-02 | Dashboard missing `trust_score` | **P1** | Second API call | Wire `PortfolioDashboardDTO.trust_score` in dashboard handler |
| G-03 | Dashboard missing contributors | **P2** | Hide section | Complete contributor aggregation in dashboard |
| G-04 | No mobile recommendation aggregate | **P1** | 3-way client join | New `GET /recommendations/mobile/daily` |
| G-05 | Committee packet payload too large | **P1** | Fetch full packet per symbol | New `CommitteeAdvisorySlimRead` in list endpoint |
| G-06 | EXIT_APPROVED not in `/daily` filter | **P1** | Extra run fetch | Add `EXIT_APPROVED` to daily filter + counts |
| G-07 | No `exit_count` on daily response | **P2** | Separate EXIT fetch | Add `exit_approved_count` to `DailyRecommendationsRead` |
| G-08 | Reason codes not human-readable | **P2** | Client i18n map | New `reason_labels: list[str]` enrichment |
| G-09 | No auth / API key middleware | **P0 prod** | Dev proxy | Auth middleware (out of Track B) |
| G-10 | Copilot no session history | **P2** | Audit log substitute | `GET /copilot/sessions/{id}` |
| G-11 | Copilot no async for long queries | **P3** | Loading spinner | `POST /copilot/ask/async` |
| G-12 | No batch stock lookup | **P1** | N+1 `/stocks/{symbol}` | `GET /stocks?ids=uuid,uuid` |
| G-13 | Committee report markdown heavy | **P2** | Render MD client-side | Optional `summary_only=true` query param |
| G-14 | No mobile portfolio summary card | **P2** | Compose from 4 calls | `GET /portfolio/mobile/summary` |
| G-15 | Reconciliation gate opaque on mobile | **P2** | Parse 409 body | Standard error schema `ReconciliationGateError` |
| G-16 | No `as_of_date` on dashboard | **P2** | Infer from nav-history | Add `as_of_date` field |
| G-17 | Position list missing `last_price` | **P3** | Derive from market_value/qty | Add `last_price` field |

---

## 3. Existing DTOs vs Mobile Needs

### 3.1 Recommendations

#### `RecommendationResultRead` (exists)

```python
# app/api/v1/recommendations.py
class RecommendationResultRead(BaseModel):
    id: UUID
    stock_id: UUID          # ❌ mobile needs symbol
    rank: int | None
    composite_score: float | None
    action: str             # ✅ BUY, WATCH, EXIT_APPROVED
    lifecycle_state: str | None
    conviction_score: int     # ✅
    conviction_band: str      # ✅
    conviction_components: dict[str, Any]  # ✅
    reason_codes: list[str] # ✅ (needs labels — G-08)
    recommendation_run_id: UUID
```

**Missing for mobile:**
- `symbol: str`
- `stock_name: str | None`
- `sector: str | None`
- `committee_advisory: CommitteeAdvisorySlim | None` (G-04)
- `reason_labels: list[str]` (G-08)

#### `DailyRecommendationsRead` (exists)

**Missing for mobile:**
- `exit_approved_count: int` (G-07)
- `as_of_date` per strategy already present ✅
- Flat `results` option without strategy nesting (mobile cards often single-strategy)

---

### 3.2 Portfolio

#### `PortfolioDashboardDTO` (defined, partially implemented)

```python
# app/portfolio/dtos.py — TARGET shape
@dataclass
class PortfolioDashboardDTO:
    nav: float | None                    # ✅ returned
    today_change_pct: float | None       # ✅ returned
    alpha_pct: float | None              # ✅ returned
    cash_pct: float | None               # ✅ returned
    active_positions: int                # ✅ returned
    pending_exits: int                   # ✅ returned
    risk_level: str                      # ✅ returned
    risk_alerts: list[RiskAlertDTO]      # ✅ returned
    trust_score: float | None            # ❌ NOT returned (G-02)
    top_contributors: list[ContributorDTO]   # ❌ stubbed (G-03)
    worst_contributors: list[ContributorDTO] # ❌ stubbed (G-03)
    reconciliation_status: str | None    # ✅ returned
```

**Implementation gap:** `app/api/v1/portfolio.py` `get_dashboard()` returns a plain dict without `trust_score` or contributors despite `PortfolioDashboardDTO` existing.

**Also missing:**
- `as_of_date: str` (G-16)
- `regime_posture: str | None`

#### `PortfolioSummary` dataclass (exists — adequate)

Mobile can use as-is for portfolio tab summary section.

#### Position `list[dict]` (exists — adequate with G-17)

Returns sufficient fields for position list. Optional `last_price` would simplify display.

---

### 3.3 Investment Committee

#### Packet response `list[dict]` (exists — too heavy)

Full `payload` JSONB includes:
- `evidence_coverage`
- `stock_setup_evidence`
- `stock_quality_evidence`
- `source_lineage`
- ... plus mobile-needed blocks

**Mobile-needed subset (`CommitteePacketSlim`):**

```typescript
interface CommitteePacketSlim {
  packet_id: string;
  symbol: string;
  as_of_date: string;
  recommendation: {
    action: string;
    conviction_score: number;
    conviction_band: string;
    reason_codes: string[];
  };
  committee_advisory: {
    cro_advisory_action: string | null;
    high_concern: boolean;
    high_concern_committees: string[];
    committee_actions: Record<string, string>;
    display_names: Record<string, string>;
  };
  governance_summary: string | null;  // from report join
  governance_confidence: number | null;
}
```

**Proposed endpoint:** `GET /investment-committee/{id}/packets/slim` or `?view=slim`

#### Report `ReportItem` (exists — adequate)

`summary` + `narrative` (markdown) sufficient for detail screen. Optional `?fields=summary` for list performance (G-13).

---

### 3.4 Analytics

#### `TrustMetricsDTO` (exists — adequate)

`overall_trust_score` (0–1) maps directly to dashboard trust widget.

#### `RecommendationSummaryDTO` (exists — adequate)

`top_conviction_buys`, `exit_candidates` useful for dashboard supplements.

**No critical gaps** in analytics DTOs for MVP.

---

### 3.5 Copilot

#### `AskResponse` (exists — adequate for MVP)

```python
class AskResponse(BaseModel):
    answer: str
    citations: list[CitationRead]
    uncited_claims: list[str]
    intent: str
    refused: bool
    model: str | None
    latency_ms: int | None
    query_log_id: str
```

**Missing:**
- `session_id` in response (client generates today)
- `suggested_followups: list[str]` (nice-to-have)
- Session history endpoint (G-10)
- Async job endpoint (G-11)

#### `AuditLogRead` (exists — partial history)

Usable as MVP copilot history; not a true session model.

---

## 4. Proposed New DTOs (API Productization)

### 4.1 `MobileRecommendationCardRead` (G-04)

**Endpoint:** `GET /api/v1/recommendations/mobile/daily`

```python
class CommitteeAdvisorySlim(BaseModel):
    cro_advisory_action: str | None
    high_concern: bool
    high_concern_committees: list[str]
    committee_actions: dict[str, str]

class MobileRecommendationCardRead(BaseModel):
    result_id: UUID
    symbol: str
    stock_name: str | None
    sector: str | None
    action: str
    rank: int | None
    conviction_score: int
    conviction_band: str
    reason_codes: list[str]
    reason_labels: list[str]
    committee_advisory: CommitteeAdvisorySlim | None
    recommendation_run_id: UUID
    strategy_name: str

class MobileDailyRecommendationsRead(BaseModel):
    as_of_date: date
    strategy_name: str
    committee_review_id: UUID | None
    buy: list[MobileRecommendationCardRead]
    watch: list[MobileRecommendationCardRead]
    exit_approved: list[MobileRecommendationCardRead]
    counts: dict[str, int]  # buy, watch, exit_approved
```

**Backend work:** Read-only join across `recommendation_results`, `stocks`, `investment_review_packets` — no engine logic change.

---

### 4.2 `MobileDashboardRead` (G-02, G-03, G-16)

**Endpoint:** extend `GET /api/v1/portfolio/dashboard` response

```python
class MobileDashboardRead(BaseModel):
    as_of_date: date | None
    nav: float | None
    today_change_pct: float | None
    alpha_pct: float | None
    cash_pct: float | None
    active_positions: int
    pending_exits: int
    risk_level: str
    risk_alerts: list[RiskAlertRead]
    trust_score: float | None           # from TrustMetricsService
    top_contributors: list[ContributorRead]   # max 3
    worst_contributors: list[ContributorRead]  # max 3
    reconciliation_status: str | None
    regime_posture: str | None
    buy_count: int | None               # optional embed
```

**Backend work:** Wire existing `PortfolioDashboardDTO`; call `TrustMetricsService`; fix contributor sort (currently placeholder in handler).

---

### 4.3 `MobilePortfolioSummaryRead` (G-14)

**Endpoint:** `GET /api/v1/portfolio/mobile/summary`

Combines `summary` + `limits` + `reconciliation.status` + latest `performance` headline (if not gated) in one response.

---

### 4.4 `CopilotSessionRead` (G-10)

**Endpoint:** `GET /api/v1/copilot/sessions/{session_id}`

```python
class CopilotMessageRead(BaseModel):
    id: UUID
    role: str  # user | assistant
    content: str
    intent: str | None
    refused: bool
    citations: list[CitationRead]
    created_at: datetime

class CopilotSessionRead(BaseModel):
    session_id: UUID
    messages: list[CopilotMessageRead]
    created_at: datetime
    updated_at: datetime
```

**Backend work:** Query `copilot_query_logs` grouped by `session_id` — no new tables required.

---

### 4.5 Standard error envelope (G-15)

```python
class ApiErrorRead(BaseModel):
    code: str           # RECONCILIATION_GATE, NOT_FOUND, ...
    message: str
    details: dict[str, Any] | None
```

Apply to 409 reconciliation responses for consistent mobile handling.

---

## 5. Client-Side Aggregation (MVP Workarounds)

Until proposed DTOs ship, mobile **must** implement these joins:

### 5.1 Stock ID → Symbol cache

```
On app init or first recommendation fetch:
  1. Collect unique stock_ids from results
  2. For each: GET /stocks/{symbol} OR maintain local id→symbol map
  3. Cache in memory + AsyncStorage (24h TTL)
```

**Cost:** N+1 requests without G-12 batch endpoint.

### 5.2 Recommendation + Committee join

```
1. review = GET /investment-committee/latest
2. packets = GET /investment-committee/{review.run_id}/packets
3. Build Map<symbol, committee_advisory>
4. Merge into recommendation cards
```

**Cost:** 2 extra requests per recommendations screen load.

### 5.3 Dashboard trust score

```
Parallel with dashboard:
  trust = GET /analytics/recommendations/trust
  dashboard.trustScore = trust.overall_trust_score
```

**Cost:** 1 extra request (acceptable for MVP).

---

## 6. Fields Available Today (No Gap)

| Screen need | API field | Status |
|-------------|-----------|--------|
| BUY / WATCH actions | `RecommendationResultRead.action` | ✅ |
| EXIT_APPROVED | `action` on run results | ✅ (extra fetch) |
| Conviction | `conviction_score`, `conviction_band`, `conviction_components` | ✅ |
| Rationale | `reason_codes` | ✅ |
| Committee advisory | `payload.committee_advisory` | ✅ (heavy) |
| HIGH_CONCERN | `high_concern`, `high_concern_committees` | ✅ |
| Committee report | `ReportItem.narrative` | ✅ |
| Committee actions | `committee_actions` map | ✅ |
| NAV | `dashboard.nav` | ✅ |
| Alpha | `dashboard.alpha_pct` | ✅ |
| Cash | `dashboard.cash_pct` | ✅ |
| Risk | `dashboard.risk_level`, `/risk` | ✅ |
| Trust Score | `TrustMetricsDTO.overall_trust_score` | ✅ (separate call) |
| Pending Exits | `dashboard.pending_exits`, `/exits` | ✅ |
| Positions | `/portfolio/positions` | ✅ |
| Allocation | `/portfolio/allocation`, position `weight_pct` | ✅ |
| Attribution | `AttributionReport` buckets | ✅ |
| Performance | `PerformanceMetrics` | ✅ (gated) |
| Copilot Q&A | `AskResponse` | ✅ |
| Citations | `CitationRead` | ✅ |

---

## 7. Implementation Priority (Backend Track B Follow-up)

| Priority | Gap ID | Effort | Impact |
|----------|--------|--------|--------|
| P0 | G-01 Add symbol to recommendation results | S | Eliminates N+1 |
| P0 | G-04 Mobile daily aggregate endpoint | M | Single-call recommendations screen |
| P1 | G-02 Wire trust_score in dashboard | S | Single-call dashboard |
| P1 | G-05 Slim committee packets | M | Faster committee list |
| P1 | G-06 EXIT_APPROVED in daily filter | S | Simpler EXIT tab |
| P1 | G-12 Batch stock lookup | S | Performance |
| P2 | G-03 Dashboard contributors | M | Dashboard completeness |
| P2 | G-08 Reason code labels | S | UX polish |
| P2 | G-10 Copilot sessions | M | Chat history |
| P2 | G-14 Mobile portfolio summary | S | Fewer portfolio calls |
| P3 | G-11 Copilot async | L | Long query UX |
| Prod | G-09 Auth | L | Production blocker |

**Effort:** S = <1 day, M = 1–3 days, L = >3 days

---

## 8. Explicit Non-Goals

These are **out of scope** per Track B constraints:

| Item | Reason |
|------|--------|
| Changing conviction formula | Logic modification forbidden |
| Changing recommendation actions | Logic modification forbidden |
| Changing portfolio NAV calculation | Logic modification forbidden |
| Changing committee LLM prompts | ARGS logic |
| New ranking/validation endpoints | Out of mobile MVP scope |
| Push notification infrastructure | Post-MVP |
| User/watchlist entities | Post-MVP |

---

## 9. Acceptance Checklist

| Criterion | Status |
|-----------|--------|
| Every screen maps to backend APIs | ✅ See MOBILE_API_MAPPING.md |
| DTOs identified (existing + proposed) | ✅ This document |
| Missing APIs documented | ✅ Section 2, 4, 7 |
| No backend logic modifications in Track B | ✅ Proposed changes are read-layer only |
| Mobile MVP scope clearly defined | ✅ MOBILE_PRD.md §5 |

---

## 10. Revision History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-05 | Initial DTO gap analysis |
