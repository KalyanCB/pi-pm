# Pi-PM — Roadmap

**Last updated:** 2026-06-01  
**Takeover:** `docs/HANDOFF.md`

---

## Current Gate

**Sprint 8.1 regime backtest must complete and results documented** before Sprint 8.2 factor analytics or any live policy integration.

Key research question: Does E2 or E3 beat E1 on **2025 holdout** with statistical significance?

Fill results in: `docs/sprint81-results-template.md`

---

## Completed (Do Not Re-Implement)

| Sprint | Deliverable |
|--------|-------------|
| 6.1 | Full-universe validation |
| 7 | Traceability tables + observability API |
| 7.1 | Backfill + ensure on reuse paths |
| 8.1 | Regime policy replay + backtest API |

---

## Prioritized Backlog

### P0 — Immediate (Sprint 8.1 wrap-up)

| Item | Description |
|------|-------------|
| Run regime backtest on production validation data | POST `/regime-policy/backtest/run` |
| Document results | `sprint81-results-template.md` |
| Merge `feature/sprint8` | After review |

### P1 — Sprint 8.2 (Planned)

| Item | Description |
|------|-------------|
| Factor predictive power analytics | Per-factor IC by regime/horizon |
| `factor_performance_metrics` table | Backfill from existing data |
| No new technical indicators | Until factor IC proven |

### P2 — Sprint 8.3 (Design complete; implementation next)

| Item | Description |
|------|-------------|
| Exit research workspace (`workspace_exit_research`) | Given signal entry, which exit behaviors preserved edge? |
| Five policy families | Fixed hold, alpha decay, rank deterioration, regime transition, trend failure |
| Design doc | `docs/sprint83-exit-research-design.md` |

### P3 — Sprint 8.4 (Planned)

| Item | Description |
|------|-------------|
| AI research agent | Hypothesis → experiment → report (reads exit/factor/regime metrics) |
| Human approval checkpoints | No autonomous production changes |

### P4 — Sprint 8.5 (Conditional)

| Item | Description |
|------|-------------|
| Regime-specific factor weights | Only if 8.2 supports it |

### Deferred

| Item | Reason |
|------|--------|
| Portfolio / paper trading | After research gate |
| Live broker | Future |
| New ranking factors | Blocked until 8.2 |
| LLM ranking/sizing | Never |

---

## Sprint Plan (Updated)

### Sprint 8.2 — Factor Predictive Power (Next)

- Per-factor Spearman IC across horizons and regimes
- Backfill from `ranking_factor_contributions` + forward returns
- APIs under `/api/v1/analytics/factors`

### Sprint 8.3 — Exit Research Workspace

- Isolated `workspace_exit_research` (read-only upstream)
- Five dashboards: policy comparison, alpha decay, rank deterioration, regime transition, trend failure
- Stratified metrics with n≥30 rule; holdout-first reporting
- **Design:** `docs/sprint83-exit-research-design.md`

### Sprint 8.4 — AI Research Agent

- Read validation + factor + regime + exit metrics
- Generate hypotheses and experiment proposals
- Human approval before any writes

### Sprint 8.5 — Regime-Specific Models (Conditional)

- Only if 8.2 identifies regime-differential factor IC
- Walk-forward validation required

---

## Technical Debt

| Item | Priority |
|------|----------|
| Full-universe campaign O(n²) aggregation | P1 |
| Async campaign + progress API (Sprint 6.2) | P1 |
| Postman collection for observability + regime-policy | P2 |
| CI/CD (GitHub Actions) | P2 |
| `strategy_regime_performance` auto-refresh | P2 |

---

## Related Documentation

- `docs/HANDOFF.md`
- `docs/SPRINT_HISTORY.md`
- `docs/DECISION_LOG.md`
