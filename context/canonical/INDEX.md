# Canonical Documentation Index

**Self-contained human-authored decisions.** Safe to use without legacy `docs/`.

Regenerate status from code: `uv run python scripts/generate_context.py`

---

## Architecture decisions (`decisions/`)

| ADR | Status | File |
|-----|--------|------|
| ADR-021 | Accepted | [ADR-021-Recommendation-Platform-Architecture.md](decisions/ADR-021-Recommendation-Platform-Architecture.md) |
| ADR-022 | Accepted | [ADR-022-Recommendation-Performance-Framework.md](decisions/ADR-022-Recommendation-Performance-Framework.md) |
| ADR-023 | Accepted | [ADR-023-Investment-Committee-Evolution.md](decisions/ADR-023-Investment-Committee-Evolution.md) |
| ADR-024 | Accepted | [ADR-024-Portfolio-State-Source-Of-Truth.md](decisions/ADR-024-Portfolio-State-Source-Of-Truth.md) |
| ADR-026 | Accepted | [ADR-026-Frontend-Architecture.md](decisions/ADR-026-Frontend-Architecture.md) |
| ADR-027 | Accepted | [ADR-027-Authentication-And-MultiTenant-Architecture.md](decisions/ADR-027-Authentication-And-MultiTenant-Architecture.md) |
| ADR-028 | Accepted | [ADR-028-Paper-Trading-Readiness.md](decisions/ADR-028-Paper-Trading-Readiness.md) |
| ADR-029 | Accepted | [ADR-029-Pilot-Operations.md](decisions/ADR-029-Pilot-Operations.md) |
| ADR-030 | Accepted | [ADR-030-Live-Investing-Architecture.md](decisions/ADR-030-Live-Investing-Architecture.md) |
| ADR-031 | Accepted | [ADR-031-Unified-Execution-Architecture.md](decisions/ADR-031-Unified-Execution-Architecture.md) |
| ADR-032 | **Proposed** | [ADR-032-Live-Entry-Timing-Validation-Gate.md](decisions/ADR-032-Live-Entry-Timing-Validation-Gate.md) |
| ADR-033 | **Proposed** | [ADR-033-Intraday-Exit-Monitor-And-Stop-Override.md](decisions/ADR-033-Intraday-Exit-Monitor-And-Stop-Override.md) |
| ADR-032 impl notes | Reference | [ADR-032-IMPLEMENTATION.md](decisions/ADR-032-IMPLEMENTATION.md) |

---

## Product requirements (`product/`)

| Doc | File |
|-----|------|
| Recommendation engine | [01_RECOMMENDATION_ENGINE_PRD.md](product/01_RECOMMENDATION_ENGINE_PRD.md) |
| Conviction scoring | [02_CONVICTION_SCORING_PRD.md](product/02_CONVICTION_SCORING_PRD.md) |
| Data model | [03_RECOMMENDATION_DATA_MODEL.md](product/03_RECOMMENDATION_DATA_MODEL.md) |
| Lifecycle | [04_RECOMMENDATION_LIFECYCLE.md](product/04_RECOMMENDATION_LIFECYCLE.md) |
| Portfolio engine | [05_PORTFOLIO_ENGINE_PRD.md](product/05_PORTFOLIO_ENGINE_PRD.md) |
| Paper trading | [06_PAPER_TRADING_PRD.md](product/06_PAPER_TRADING_PRD.md) |
| Exit framework | [07_EXIT_DECISION_FRAMEWORK.md](product/07_EXIT_DECISION_FRAMEWORK.md) |
| Investment committee | [08_AI_INVESTMENT_COMMITTEE_PRD.md](product/08_AI_INVESTMENT_COMMITTEE_PRD.md) |
| Mobile app | [09_MOBILE_APP_PRD.md](product/09_MOBILE_APP_PRD.md) |
| Copilot | [10_AI_COPILOT_PRD.md](product/10_AI_COPILOT_PRD.md) |
| HITL execution | [11_HUMAN_IN_LOOP_EXECUTION_PRD.md](product/11_HUMAN_IN_LOOP_EXECUTION_PRD.md) |
| Roadmap 2026–2027 | [12_PRODUCT_ROADMAP_2026_2027.md](product/12_PRODUCT_ROADMAP_2026_2027.md) |
| PO backlog | [13_PO_BACKLOG.md](product/13_PO_BACKLOG.md) |
| Why-not framework | [16_WHY_NOT_RECOMMENDED_FRAMEWORK.md](product/16_WHY_NOT_RECOMMENDED_FRAMEWORK.md) |
| Rec performance | [16_RECOMMENDATION_PERFORMANCE_PRD.md](product/16_RECOMMENDATION_PERFORMANCE_PRD.md) |
| Live HITL (Track I) | [18_HUMAN_IN_LOOP_LIVE_INVESTING_PRD.md](product/18_HUMAN_IN_LOOP_LIVE_INVESTING_PRD.md) |
| Broker adapter | [19_BROKER_ADAPTER_PRD.md](product/19_BROKER_ADAPTER_PRD.md) |
| Risk control | [20_RISK_CONTROL_PRD.md](product/20_RISK_CONTROL_PRD.md) |
| Execution workflow | [21_EXECUTION_WORKFLOW_PRD.md](product/21_EXECUTION_WORKFLOW_PRD.md) |
| Architecture impact | [14_ARCHITECTURE_IMPACT_ANALYSIS.md](product/14_ARCHITECTURE_IMPACT_ANALYSIS.md) |
| Trust dashboard vision | [17_TRUST_DASHBOARD_VISION.md](product/17_TRUST_DASHBOARD_VISION.md) |

---

## Phase 1 (`phase1/`)

| Doc | File |
|-----|------|
| G1–G8 research PRD | [PRD.md](phase1/PRD.md) |

---

## PO & strategy (`po/`)

| Doc | File |
|-----|------|
| PO sign-off | [PO_SIGNOFF_2026_06_04.md](po/PO_SIGNOFF_2026_06_04.md) |
| Executive strategy | [15_EXECUTIVE_PRODUCT_STRATEGY.md](po/15_EXECUTIVE_PRODUCT_STRATEGY.md) |

---

## Design references (`design/`)

| Doc | File |
|-----|------|
| Domain boundaries | [domain-boundaries.md](design/domain-boundaries.md) |
| RCEE design | [RCEE_DESIGN.md](design/RCEE_DESIGN.md) |
| Validation design | [VALIDATION_DESIGN.md](design/VALIDATION_DESIGN.md) |
| Copilot intent matrix | [COPILOT_INTENT_MATRIX.md](design/COPILOT_INTENT_MATRIX.md) |

---

## Frontend (`frontend/`)

| Doc | File |
|-----|------|
| Design system | [DESIGN_SYSTEM.md](frontend/DESIGN_SYSTEM.md) |
| Feature integration report | [FEATURE_INTEGRATION_REPORT.md](frontend/FEATURE_INTEGRATION_REPORT.md) |
| Frontend audit matrix | [FRONTEND_AUDIT_REPORT.md](frontend/FRONTEND_AUDIT_REPORT.md) |

---

## Runbooks (`runbooks/`)

| Doc | File |
|-----|------|
| Daily NIFTY 500 batch | [daily-nifty500-batch-runbook.md](runbooks/daily-nifty500-batch-runbook.md) |
| Live trading safety | [LIVE_TRADING_SAFETY_CHECKLIST.md](runbooks/LIVE_TRADING_SAFETY_CHECKLIST.md) |
| Execution runbook | [EXECUTION_RUNBOOK.md](runbooks/EXECUTION_RUNBOOK.md) |
| Paper pilot daily ops | [DAILY_OPS_RUNBOOK.md](runbooks/DAILY_OPS_RUNBOOK.md) |

---

## Gotchas (canonical, root)

[../GOTCHAS.md](../GOTCHAS.md) — validation tail, HITL, exit monitor, anti-patterns.

---

## Generated (from code — do not hand-edit)

| File | Role |
|------|------|
| [../generated/PLATFORM_STATE.md](../generated/PLATFORM_STATE.md) | Live repo state |
| [../generated/IMPLEMENTATION_STATUS.md](../generated/IMPLEMENTATION_STATUS.md) | 70 requirements status |
| [../generated/REQUIREMENTS.rtm.yaml](../generated/REQUIREMENTS.rtm.yaml) | Machine RTM |
| [../generated/GAPS_AND_DEBT.md](../generated/GAPS_AND_DEBT.md) | Deferred work |
| [../generated/API_SCHEMAS.json](../generated/API_SCHEMAS.json) | OpenAPI export |
| [../generated/DATABASE_SCHEMA.md](../generated/DATABASE_SCHEMA.md) | Schema detail |
| [../generated/ENV_CATALOG.md](../generated/ENV_CATALOG.md) | All env flags |
| [../generated/OPS_SCRIPTS.md](../generated/OPS_SCRIPTS.md) | Scripts index |
| [../generated/TEST_MAP.md](../generated/TEST_MAP.md) | Tests by module |
| [../generated/CANONICAL_LINK_CHECK.md](../generated/CANONICAL_LINK_CHECK.md) | Broken link audit |
