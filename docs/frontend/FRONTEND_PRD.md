# Pi-PM Frontend — Product Requirements Document

**Track:** D — Frontend Architecture & React Native Web Foundation  
**Version:** 1.0  
**Date:** 2026-06-05  
**Constraint:** Architecture and blueprint only — **no UI implementation** in Track D.

---

## 1. Product Vision

Pi-PM frontend is the **owner's operational console** for a deterministic investment platform. It is not a retail broker. The aesthetic and information density target **Bloomberg Terminal Lite**: data-first, advisory-aware, citation-grounded.

```
Portfolio Manager + Recommendation Engine + Investment Committee + AI Copilot
```

The frontend surfaces backend truth — it never invents conviction, allocation, alpha, or risk.

---

## 2. Target Platforms

| Platform | Priority | Delivery |
|----------|----------|----------|
| Responsive web (desktop-first) | **P0** | Phase 1–3 |
| Tablet web | P0 | Responsive breakpoints |
| Mobile web | P1 | Same codebase, stacked layouts |
| Android native | P2 | Phase 4 |
| iOS native | P2 | Phase 4 |

---

## 3. User Persona

| Persona | Description | Primary tasks |
|---------|-------------|---------------|
| **Owner** | Single portfolio operator | Morning dashboard, review BUY/WATCH/EXIT, approve HITL, confirm exits, committee review, copilot Q&A |

**Future personas** (auth-ready, not MVP): Research reviewer (read-only), Ops admin.

---

## 4. Design Principles

| ID | Principle |
|----|-----------|
| FP-01 | **Backend is truth** — display API fields; no client-side financial math |
| FP-02 | **Advisory separation** — machine `action` and committee `cro_advisory_action` shown distinctly |
| FP-03 | **Density over decoration** — tables, badges, monospace numbers; minimal animation |
| FP-04 | **Gated honesty** — reconciliation FAIL hides performance sections with explicit banner |
| FP-05 | **Citation-first copilot** — every numeric claim links to source record |
| FP-06 | **One codebase** — shared components; layout adapters per breakpoint |

---

## 5. MVP Screen Priority

### P1 (Phase 2)

| # | Screen | Purpose |
|---|--------|---------|
| 1 | Dashboard | Portfolio health at a glance |
| 2 | Recommendations | BUY / WATCH / EXIT_APPROVED daily lists |
| 3 | Portfolio | Positions, performance, attribution, risk |
| 4 | Exit Approval Queue | Pending exit confirm/reject |
| 5 | Copilot | Grounded Q&A |

### P2 (Phase 3)

| # | Screen | Purpose |
|---|--------|---------|
| 6 | Investment Committee | Advisory packets, HIGH_CONCERN, narratives |
| 7 | Performance Analytics | Trust score, conviction calibration, committee effectiveness |
| 8 | Settings | API URL, default strategy, theme (local prefs) |

---

## 6. Functional Requirements

### 6.1 Dashboard (P1)

- Display NAV, daily change, alpha, cash %, risk level, trust score, pending exits
- Reconciliation status banner when not PASS
- BUY preview strip linking to Recommendations
- Risk alert chips (max 3 on mobile, expandable on desktop)

### 6.2 Recommendations (P1)

- Tab/filter: BUY, WATCH, EXIT_APPROVED
- Cards: symbol, action, conviction band/score, reason codes, committee advisory overlay
- HIGH_CONCERN visual treatment
- Drill-down to detail (conviction components, narrative, copilot shortcut)
- HITL queue access (approve/reject)

### 6.3 Portfolio (P1)

- Summary, positions table, performance metrics, attribution buckets, risk panel
- NAV history chart (client renders from API series — no client alpha calc)
- 409 gate handling when reconciliation FAIL

### 6.4 Exit Approval Queue (P1)

- List pending exits with urgency, triggers, P&L %
- Confirm / reject actions
- Copilot explain shortcut

### 6.5 Copilot (P1)

- Free-text Q&A with citations
- Contextual suggested prompts per screen
- Refusal display for out-of-scope questions

### 6.6 Investment Committee (P2)

- Latest review status with poll while running
- Symbol list with committee actions map
- HIGH_CONCERN filter
- Governance narrative (markdown)

### 6.7 Performance Analytics (P2)

- Trust score breakdown (calibration, stability, reliability)
- Recommendation quality summary
- Committee effectiveness metrics

### 6.8 Settings (P2)

- API base URL (dev)
- Default strategy name
- Theme preference (dark default — terminal aesthetic)

---

## 7. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Initial dashboard load | ≤ 2s on broadband (3 parallel API calls) |
| NFR-02 | TypeScript strict | 100% typed API responses |
| NFR-03 | Accessibility | WCAG 2.1 AA on web (contrast, keyboard nav) |
| NFR-04 | Breakpoints | 375px, 768px, 1024px, 1440px |
| NFR-05 | Error recovery | Retry + toast; no white screen |
| NFR-06 | Bundle | Route-level code splitting per screen |

---

## 8. Out of Scope (Track D & MVP)

| Item | Reason |
|------|--------|
| Full UI implementation | Track D is architecture only |
| Auth implementation | Backend blocker; architecture prepared |
| Push notifications | No backend infrastructure |
| Real-time WebSocket | Polling for committee runs |
| Charting library selection | Phase 2 implementation decision |
| Broker integration | Paper trade only via API |
| Client-side financial calculations | Governance violation |

---

## 9. Success Metrics

| Metric | Definition |
|--------|------------|
| Architecture completeness | All 13 Track D deliverables published |
| API coverage | 100% P1 screens mapped to endpoints |
| Component reuse | ≥80% screen UI from `packages/ui` |
| Platform parity | Shared components render on web + native Storybook |

---

## 10. Related Documents

| Document | Purpose |
|----------|---------|
| [FRONTEND_ARCHITECTURE.md](./FRONTEND_ARCHITECTURE.md) | System design overview |
| [SCREEN_SPECIFICATIONS.md](./SCREEN_SPECIFICATIONS.md) | Per-screen detail |
| [docs/mobile/](../mobile/) | Backend API contracts (Track B) |
| [ADR-026](../architecture/ADR-026-Frontend-Architecture.md) | Architecture decision record |

---

## 11. Revision History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-05 | Initial frontend PRD — Track D |
