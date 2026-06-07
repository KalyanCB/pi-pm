# Mobile Readiness Assessment

> **⚠️ STALE (2026-06-05):** Mobile app exists at `frontend/apps/mobile/` (Expo, shared packages with web).  
> **Current truth:** [`frontend/docs/FEATURE_INTEGRATION_REPORT.md`](../../frontend/docs/FEATURE_INTEGRATION_REPORT.md), [`docs/audit/FRONTEND_AUDIT_REPORT.md`](../audit/FRONTEND_AUDIT_REPORT.md).  
> Remaining gaps: `/exits`, `/analytics` screens; HITL queue UX.

**Date:** 2026-06-05 (snapshot before frontend integration)  
**Finding (historical):** No mobile application codebase existed at audit time — **now implemented**.

---

## Readiness summary

| Dimension | Score | Notes |
|-----------|-------|-------|
| Backend API surface | 65/100 | Rich read APIs; missing portfolio, auth, push |
| Auth / user model | 0/100 | No auth middleware |
| Mobile-optimized payloads | 40/100 | Some aggregates; many ops endpoints |
| Real-time / push | 0/100 | Polling only |
| Offline / cache strategy | 0/100 | Not designed |
| Overall mobile readiness | **8/100** | API-only backend |

---

## Hypothetical mobile screens vs backend

Mapping **typical** consumer portfolio app screens to current APIs/models. Status based on code evidence.

| Screen | User need | API / data available | Gap |
|--------|-----------|----------------------|-----|
| Home / dashboard | Portfolio value, day P&L | ✗ No portfolio API | **Blocker** |
| Watchlist | Track symbols | Partial — `GET /stocks/{symbol}` | No watchlist entity |
| Market movers / rankings | Today's top picks | ✓ `GET /rankings/latest`, `/top` | No push; no "buy" label |
| Stock detail | Price, chart, rank history | ✓ stocks + market-data | Rank history needs multiple run fetches |
| Research card | ARGS stance | ✓ `/research/latest`, `/packet` | LLM output heavy; not mobile-tuned |
| Validation proof | "Why trust this rank?" | Partial — validation per run | Tail `insufficient_data` on recent dates |
| Factor breakdown | Score reconstruction | ✓ observability score-reconstruction | Complex JSON |
| Regime indicator | Market regime | ✓ `/observability/regime/current` | ✓ |
| Exit alert | Sell signal | ✗ Exit reports are batch analytics | **Blocker** |
| Paper trade confirm | Simulated buy | ✗ No paper trade API | **Blocker** |
| Settings | Universe, strategy prefs | Partial — env/config server-side | No user prefs API |
| Notifications | Rank change, exit | ✗ | **Blocker** |
| Auth / login | Secure access | ✗ | **Blocker** |

---

## API suitability for mobile clients

### Ready (with caveats)

| Endpoint group | Mobile use | Caveat |
|----------------|------------|--------|
| `/rankings/*` | Top lists | Large payloads; pagination limited |
| `/stocks/*` | Symbol lookup | |
| `/validation/summary` | Trust metrics | Aggregated, not per-stock mobile card |
| `/observability/regime/current` | Regime badge | |
| `/research/{id}/explain` | Research summary | Text-heavy |

### Not ready

| Gap | Impact |
|-----|--------|
| No OAuth/API keys | Cannot ship public mobile app |
| No `/portfolio/*` | Core screen blocked |
| No WebSocket/SSE | Battery-heavy polling |
| No image/chart CDN | Client must render charts |
| Ops endpoints exposed same as read | Security model undefined |

---

## Data model gaps for mobile

| Entity needed | Exists? |
|---------------|---------|
| User | ✗ |
| Device / push token | ✗ |
| Watchlist | ✗ |
| Alert rule | ✗ |
| Portfolio snapshot | Table only — no API |
| Recommendation record | ✗ |

---

## ARGS on mobile

| Consideration | Detail |
|---------------|--------|
| Payload size | Full packets JSONB — may need mobile DTO |
| LLM latency | Committee runs minutes — async job + poll pattern required |
| Label semantics | supportive/neutral/cautious ≠ buy/sell/hold |

**Existing pattern:** Poll `GET /research/{run_id}` until complete — suitable for mobile **if** auth added.

---

## Minimum backend work for MVP mobile (**assumption**)

Not implemented; PO planning estimate:

1. Auth (JWT or API key per user)
2. Portfolio + paper trade APIs
3. Mobile-specific DTOs (slim ranking top, slim research summary)
4. User watchlist CRUD
5. Optional: push via **unknown** provider — not in code

---

## Discrepancies

| Item | Note |
|------|------|
| PRD personas | Owner/quant/PO — no "mobile consumer" persona |
| Product name "Portfolio Manager" | Implies mobile/end-user — **engineering is research platform** |

---

## References

- [04_API_CATALOG.md](./04_API_CATALOG.md)
- [11_PORTFOLIO_ENGINE_GAP_ANALYSIS.md](./11_PORTFOLIO_ENGINE_GAP_ANALYSIS.md)
- [10_RECOMMENDATION_ENGINE_GAP_ANALYSIS.md](./10_RECOMMENDATION_ENGINE_GAP_ANALYSIS.md)
