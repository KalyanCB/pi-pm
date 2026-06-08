# Mobile App — Product Requirements

**Version:** Phase 2.0 MVP  
**Date:** 2026-06-05  
**Readiness baseline:** 8/100 — [12_MOBILE_READINESS_ASSESSMENT.md](../po-discovery/12_MOBILE_READINESS_ASSESSMENT.md)

**Platform:** iOS + Android (React Native or Flutter — engineering choice; **no mobile repo today**).

---

## 1. Purpose

Owner-facing **swing trading OS** mobile client: review recommendations, ARGS advisory, approve entries/exits, monitor paper book. Quality over quantity — not a high-frequency trading UI.

---

## 2. Personas

| Persona | Needs |
|---------|-------|
| Owner | Approve BUY/EXIT, view conviction, portfolio |
| PO (read-only) | Audit queue depth, regime badge |

---

## 3. Five screens

### Screen 1 — Home / Portfolio

**Stories**

- As owner, I see total equity, cash %, day P&L, and ACTIVE position count.
- As owner, I see regime badge and max slots.

**APIs**

- `GET /api/v1/portfolio/summary` (new)
- `GET /api/v1/observability/regime/current` (exists)

**Models**

- `PortfolioSummaryDTO`, `RegimeBadgeDTO`

```
+----------------------------------+
|  Pi-PM          [Regime: Neutral]|
|  Equity ₹12.4L    Day P&L +0.8% |
|  Cash 18%    Active 5/6 slots   |
+----------------------------------+
|  [Approval Queue (2)]            |
|  [Today's Ideas]                 |
+----------------------------------+
|  Positions (scroll)              |
|  RELIANCE  +4.2%  HOLD           |
|  INFY      -1.1%  HOLD           |
+----------------------------------+
```

---

### Screen 2 — Approval Queue

**Stories**

- As owner, I see all `CANDIDATE` BUY and `EXIT_APPROVED` with conviction band.
- As owner, I approve/reject/defer with note.

**APIs**

- `GET /api/v1/recommendations/queue`
- `POST /api/v1/recommendations/{id}/approve`
- `POST /api/v1/recommendations/{id}/reject`

**Models**

- `ApprovalQueueItemDTO` — action, conviction, validation badge, ARGS advisory summary

```
+----------------------------------+
|  Queue                    [2]  |
+----------------------------------+
| BUY  TATASTEEL  Conv 78 HIGH     |
|      Validation ✓  ARGS APPROVE  |
|      [Approve] [Reject] [Detail] |
+----------------------------------+
| EXIT HDFCBANK  Rank drop -15     |
|      [Confirm Exit] [Defer]      |
+----------------------------------+
```

---

### Screen 3 — Today's Ideas (Rankings + Recommendations)

**Stories**

- As owner, I browse top pool with BUY/WATCH labels (not raw rank hype).
- As owner, I open stock detail.

**APIs**

- `GET /api/v1/recommendations/latest?strategy=momentum_v1`
- `GET /api/v1/rankings/latest` (fallback)

**Models**

- `RecommendationCardDTO` — symbol, action, conviction_band, rank (de-emphasized)

```
+----------------------------------+
|  Ideas     [Momentum v1 ▼]     |
+----------------------------------+
| 01 WATCH  SBIN   Conv 52 MED     |
| 02 BUY    ITC    Conv 81 HIGH    |
| 03 WATCH  ...                    |
+----------------------------------+
```

---

### Screen 4 — Stock Detail

**Stories**

- As owner, I see recommendation, conviction breakdown, validation status, ARGS advisory.
- As owner, I trigger ARGS explain (async poll).

**APIs**

- `GET /api/v1/recommendations/{run_id}/stocks/{symbol}`
- `GET /api/v1/stocks/{symbol}`
- `GET /api/v1/research/latest?symbol=` (poll pattern)
- `GET /api/v1/research/{id}/advisory` (slim)

**Gaps from po-discovery:** Per-stock validation card, chart CDN — client renders sparkline from `market_data` API.

```
+----------------------------------+
|  ITC                    BUY HIGH |
|  Conviction 81  [||||||||--]     |
|  Rank #2 (pool)  Valid ✓ 20d IC  |
+----------------------------------+
|  ARGS: APPROVE (CRO)             |
|  "Technical setup supportive..." |
|  [Full research]                   |
+----------------------------------+
|  [Approve trade]  (if CANDIDATE) |
+----------------------------------+
```

---

### Screen 5 — Research & Settings

**Stories**

- As owner, I read governance report markdown summary.
- As owner, I set equity, deploy %, notifications (future).

**APIs**

- `GET /api/v1/research/{id}/explain`
- `POST /api/v1/portfolio/config`
- `GET /api/v1/watchlist` (new CRUD — optional)

```
+----------------------------------+
|  Research                        |
|  Latest ARGS run 2026-06-04      |
|  [Governance summary]            |
+----------------------------------+
|  Settings                        |
|  Total equity [________]         |
|  Strategy default [Momentum ▼]   |
|  Paper mode [ON]                 |
+----------------------------------+
```

---

## 4. Cross-cutting requirements

| Area | Requirement |
|------|-------------|
| Auth | JWT or API key — **blocker** (0/100 today) |
| Polling | ARGS job status — no WebSocket v1 |
| Copy | Never equate ARGS `supportive` with BUY |
| Offline | Read-only cache of last recommendations 24h |
| Push | P3 — rank/exit alerts |

---

## 5. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC-MOB-01 | Five screens navigable with paper portfolio seed data |
| AC-MOB-02 | Approval updates queue within 2s of API success |
| AC-MOB-03 | No LLM ranking displayed |
| AC-MOB-04 | Validation `insufficient_data` shows warning badge |

---

## 6. Backend dependencies (M4)

| Dependency | Milestone |
|------------|-----------|
| Recommendation APIs | M1 |
| Portfolio APIs | M2 |
| Auth | M3 |
| Slim DTOs | M4 |

---

## 7. References

- [12_MOBILE_READINESS_ASSESSMENT.md](../po-discovery/12_MOBILE_READINESS_ASSESSMENT.md)
- [04_API_CATALOG.md](../po-discovery/04_API_CATALOG.md)
