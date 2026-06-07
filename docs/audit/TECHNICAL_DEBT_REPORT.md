# Technical Debt Report

**Audit:** AUDIT-01  
**Date:** 2026-06-05  
**Method:** Code search, test gaps, architecture drift synthesis  
**Note:** Zero `TODO`/`FIXME` in `app/` or `frontend/` — debt is structural, not annotated

---

## P0 — Blocks pilot / production

| ID | Item | Area | Evidence | Impact |
|----|------|------|----------|--------|
| TD-P0-01 | Default JWT secret in config | Security | `config.py:83` | Token forgery if undeployed |
| TD-P0-02 | Batch cron script lacks auth | Ops | `run_daily_nifty500_batch.py:77` | Documented unattended path broken |
| TD-P0-03 | No risk pre-trade gates | Execution | AC-RISK not implemented | Live trading unsafe |
| TD-P0-04 | No E2E pilot lifecycle test | QA | TEST_COVERAGE_AUDIT | Regression undetected |
| TD-P0-05 | Multi-tenant gaps on NAV/cash/recon | DB/Auth | 6 tables without `portfolio_id` | Data leak in multi-portfolio |

---

## P1 — Significant quality / completeness gaps

| ID | Item | Area | Evidence |
|----|------|------|----------|
| TD-P1-01 | No portfolio API integration tests | QA | `tests/integration/api/` |
| TD-P1-02 | No recommendations API integration tests | QA | same |
| TD-P1-03 | No execution API integration tests | QA | same |
| TD-P1-04 | Zerodha live adapter stub only | Execution | `zerodha_kite.py` |
| TD-P1-05 | RBAC permissions only on execution routes | Auth | `auth/constants.py` vs route deps |
| TD-P1-06 | `paper_trades` no portfolio_id | DB | `paper_trade.py` |
| TD-P1-07 | Portfolio analytics APIs not scoped | API | `portfolio.py:257-488` |
| TD-P1-08 | Kill switch not automated | Ops | 90_DAY_EXECUTION_PLAN manual only |
| TD-P1-09 | External alerting not wired | Ops | ALERTING_FRAMEWORK curl-only |
| TD-P1-10 | HIGH_CONCERN soft-block missing (live) | HITL | AC-HITL-L03 |
| TD-P1-11 | Approval audit CSV export missing | Compliance | AC-HITL-02 |
| TD-P1-12 | Stale authoritative docs (RTM, API catalog) | Docs | ARCHITECTURE_DRIFT |
| TD-P1-13 | Frontend Exit Queue screen missing | Frontend | `/exits` route absent |
| TD-P1-14 | Copilot retriever no portfolio scope | Security | security review |
| TD-P1-15 | No login rate limiting | Security | security review |

---

## P2 — Moderate — should fix before scale

| ID | Item | Area | Evidence |
|----|------|------|----------|
| TD-P2-01 | Deprecated `/research/*` still mounted | API | `router.py:69-71` |
| TD-P2-02 | `research_reports` orphan model | DB | no repository |
| TD-P2-03 | Frontend Analytics screen missing | Frontend | `/analytics` |
| TD-P2-04 | HITL queue API unwired in frontend | Frontend | `getQueue` unused |
| TD-P2-05 | Exit confirm/reject hooks unused | Frontend | `useConfirmExit` |
| TD-P2-06 | Citation deep links unwired | Frontend | CitationPanel |
| TD-P2-07 | Copilot golden Q&A fixture suite missing | QA | AC-CP-01 |
| TD-P2-08 | Committee not in daily batch | Ops | OPERATIONAL_GAP |
| TD-P2-09 | ARGS prompt `get_or_create_stub` | Committee | `args_prompt_version_repository.py:16` |
| TD-P2-10 | Portfolio dashboard attribution placeholder | API | `portfolio.py:531` sector placeholder |
| TD-P2-11 | HS256 vs RS256 deferred | Security | ADR-027 |
| TD-P2-12 | No pull-to-refresh mobile | UX | frontend audit |
| TD-P2-13 | Tablet breakpoint unused | UX | `useBreakpoint.ts` |
| TD-P2-14 | Test count stale in 4+ docs | Docs | 312/386 vs 574 |
| TD-P2-15 | Mock LLM fallback in copilot | Copilot | `copilot_service.py:155` |

---

## P3 — Low — cleanup / polish

| ID | Item | Area | Evidence |
|----|------|------|----------|
| TD-P3-01 | Committee stub plugins unused | Code | `*_stub.py` not in registry |
| TD-P3-02 | `services/__init__.py` stale docstring | Code | "placeholders" |
| TD-P3-03 | Settings not in mobile TabBar | UX | TabBar 5 items |
| TD-P3-04 | WCAG 2.1 AA not verified | UX | NFR-03 |
| TD-P3-05 | Copilot p95 latency not measured | Perf | AC-CP-04 |
| TD-P3-06 | `ranking_performance` placeholder snapshots | Ranking | `create_placeholder_snapshots` |
| TD-P3-07 | No ADR-025 in sequence | Docs | jumps 024→026 |
| TD-P3-08 | InsecureKeyLengthWarning in test JWT | QA | pytest warnings |

---

## Feature Flags / Workarounds

| Flag / workaround | Location | Purpose |
|-------------------|----------|---------|
| `auth_enabled` / `auth_bypass_for_tests` | `config.py`, `auth_deps.py` | Dev/test bypass |
| `pilot_auto_approve` / `pilot_auto_execute` | daily batch schema | Unattended pilot |
| `enable_live_trading` | config + Zerodha adapter | Live gate (default false) |
| `EXPO_PUBLIC_AUTH_BYPASS` | frontend authStore | Frontend dev bypass |
| `get_or_create_stub` prompts | ARGS repo | Missing prompt versions |
| Mock LLM in copilot | copilot_service | Missing API key fallback |
| Ranking placeholder snapshots | ranking_performance_repo | Missing perf data |

---

## Temporary Implementations

| Item | Nature | Path to proper fix |
|------|--------|-------------------|
| Zerodha adapter | Contract stub | Implement Kite Connect per AC-BRK |
| Portfolio attribution contributors | Sector placeholder | Symbol-level from analytics service |
| ARGS packet portfolio_context | Placeholder at build time | Post-committee population |
| Single global NAV table | Single-tenant shortcut | Add portfolio_id migration |

---

## Debt Ranking Summary

| Priority | Count | Est. effort |
|----------|-------|-------------|
| P0 | 5 | 2–3 sprints |
| P1 | 15 | 3–4 sprints |
| P2 | 15 | 2–3 sprints |
| P3 | 8 | 1 sprint |

---

*Top 20 for Executive Summary drawn from P0 + highest-impact P1 items.*
