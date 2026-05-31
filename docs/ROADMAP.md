# Pi-PM — Roadmap

**Last updated:** 2026-05-31  
**Planning horizon:** Sprints 6.2 – 10

---

## Current Gate

**Sprint 6.1 validation must complete before any new signals or production deployment.**

Five questions must be answered with data (see `docs/sprint61-full-universe-validation-report.md`):

1. Does `breakout_v1` beat random selection?
2. Does top decile outperform bottom decile?
3. Which horizon (5/10/20/60d) works best?
4. What is the historical long-short spread?
5. Is predictive power sufficient for production?

---

## Prioritized Backlog

### P0 — Immediate (Sprint 6.2)

| Item | Description | Depends On |
|------|-------------|------------|
| Complete validation campaign | Run 2024–2025 full-universe campaign locally | Sprint 6.1 API |
| Document findings | Fill success criteria in validation report | Campaign results |
| Strategy comparison | Same date range: `breakout_v1` vs `momentum_v1` | Campaign infra |
| Go/no-go decision | Production readiness for `breakout_v1` | Findings |
| Commit Sprint 6.1 | Merge `feature/sprint6` to `main` | Code review |

### P1 — Near Term (Sprint 7)

| Item | Description | Priority |
|------|-------------|----------|
| Portfolio positions service | Activate `portfolio_positions` table logic | High |
| Position sizing | Deterministic sizing from ranked signals | High |
| Paper trading | `paper_trades` workflow with ranking run linkage | High |
| Daily ranking automation | Scheduled ranking run for `NIFTY_500` | Medium |
| Remaining ERROR symbols | Recover last 4 failed ingest symbols | Low |

### P2 — Medium Term (Sprint 8–9)

| Item | Description | Priority |
|------|-------------|----------|
| Risk gates | Max position size, sector concentration, drawdown limits | High |
| Portfolio rebalancing | Target weights from rankings → trade list | High |
| LLM research agents | Narrative analysis only — no ranking/sizing | Medium |
| Research reports | Populate `research_reports` from LLM agents | Medium |
| LangGraph workflows | Orchestrate research → review → paper trade | Medium |
| Performance analytics | Portfolio return attribution vs benchmark | Medium |

### P3 — Long Term (Sprint 10+)

| Item | Description | Priority |
|------|-------------|----------|
| Live broker integration | Real execution (Zerodha/other) | Future |
| Multi-strategy ensemble | Combine momentum + breakout signals | Future |
| Alternative data | **Explicitly deferred** until validation complete | Blocked |
| Options / commodities | **Out of scope** per project rules | Blocked |
| News / sentiment signals | **Out of scope** until core validated | Blocked |
| Multi-user / auth | Single-user assumption for now | Future |

---

## Sprint Plan

### Sprint 6.2 — Validation Analysis & Go/No-Go (Proposed)

**Duration:** 1 week  
**Branch:** `feature/sprint62-validation-analysis`

**Deliverables:**
- Completed validation report with IC, spread, best horizon
- Side-by-side `breakout_v1` vs `momentum_v1` comparison table
- Decile monotonicity analysis across all horizons
- Written go/no-go recommendation
- Sprint 6.1 code committed and merged

**Exit criteria:**
- All five success criteria answered with numbers
- Stakeholder decision documented in `DECISION_LOG.md`

---

### Sprint 7 — Portfolio Layer (Proposed)

**Duration:** 2 weeks  
**Branch:** `feature/sprint7-portfolio`

**Deliverables:**
- `PortfolioService` — current positions, weights, P&L
- Deterministic position sizing from top-N ranked stocks
- Paper trade creation linked to ranking runs
- API: `GET /portfolio/positions`, `POST /portfolio/rebalance`
- Unit + integration tests

**Design constraints:**
- Sizing is deterministic (e.g. equal-weight top 20, or score-proportional)
- No LLM involvement in sizing
- Risk limits as configurable thresholds

---

### Sprint 8 — Risk Officer (Proposed)

**Duration:** 2 weeks

**Deliverables:**
- `RiskService` — pre-trade checks
- Max single position weight (e.g. 5%)
- Max sector concentration (e.g. 25%)
- Minimum portfolio diversification (e.g. 10 positions)
- Drawdown circuit breaker
- API: `POST /risk/check`, `GET /risk/limits`

---

### Sprint 9 — LLM Research Layer (Proposed)

**Duration:** 2–3 weeks

**Deliverables:**
- Research agent for top-ranked stocks (narrative only)
- `ResearchReport` persistence with model/prompt versioning
- LangGraph workflow: rank → research top 20 → human review
- Strict boundary: agent reads rankings, never modifies them

---

### Sprint 10 — Automation & Monitoring (Proposed)

**Duration:** 2 weeks

**Deliverables:**
- Scheduled daily pipeline: ingest → rank → validate → alert
- Health monitoring dashboard
- Email/Slack alerts on ranking anomalies
- Portfolio performance vs benchmark tracking

---

## Explicitly Deferred

These items are **not planned** until core validation proves predictive power:

| Item | Reason |
|------|--------|
| New ranking signals / factors | Validation gate |
| AI/ML models for ranking | Deterministic principle |
| News / sentiment data | Scope control |
| Options / derivatives | Complexity |
| Commodities / FX | Out of market scope |
| High-frequency / intraday | Daily ranking sufficient |

---

## Technical Debt

| Item | Priority | Sprint |
|------|----------|--------|
| Commit uncommitted Sprint 6.1 code | P0 | 6.2 |
| Docker dev compose: add `--reload` to entrypoint | P1 | 7 |
| README outdated (marks services as "future") | P2 | 7 |
| Postman collection missing Sprint 6.1 endpoints | P2 | 6.2 |
| Rename legacy `docs/architecture.md` vs `ARCHITECTURE.md` | P3 | 7 |
| CI/CD pipeline (GitHub Actions) | P2 | 7 |
| Auth / API keys for production | P3 | 10 |

---

## Success Metrics (Platform-Level)

| Metric | Target | Current |
|--------|--------|---------|
| NIFTY 500 ranked per run | >450 | ~439 |
| ACTIVE data coverage | >95% | ~88% (445/504) |
| Validation IC (20d) | >0.03 | TBD |
| Decile spread (20d) | >2% | TBD |
| Test coverage | >100 tests | 121 |
| API uptime (local) | — | Manual |

---

## Related Documentation

- `docs/PROJECT_MASTER.md` — Current status
- `docs/SPRINT_HISTORY.md` — Completed work
- `docs/DECISION_LOG.md` — Why we chose this path
- `docs/sprint61-full-universe-validation-report.md` — Current sprint runbook
