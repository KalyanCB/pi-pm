---
generated_at: 2026-06-28T03:28:38Z
generator: scripts/generate_context.py
---

# Requirements Traceability (human view)

| ID | Area | Status | Evidence (verified) |
|----|------|--------|---------------------|
| G1 | ranking | IMPLEMENTED | `app/ranking/engine.py`, `app/api/v1/rankings.py` |
| G2 | validation | IMPLEMENTED | `app/validation/`, `tests/integration/api/test_validation_api.py` |
| G3 | ops | PARTIALLY_IMPLEMENTED | `app/services/daily_batch_service.py`, `app/api/v1/daily_batch.py` |
| G4 | observability | IMPLEMENTED | `app/services/traceability_service.py`, `app/models/platform_traceability.py` |
| G5 | analytics | IMPLEMENTED | `app/factor_analytics/`, `app/api/v1/factor_analytics.py` |
| G6 | investment_committee | IMPLEMENTED | `app/args/`, `app/api/v1/investment_committee.py` |
| G7 | research | IMPLEMENTED | `app/stock_setup_evidence/`, `app/services/stock_setup_research_service.py` |
| G8 | governance | IMPLEMENTED | `context/canonical/design/domain-boundaries.md`, `tests/unit/args/test_qrc_sqe_flag.py` |
| R-ENTRY | recommendation | IMPLEMENTED | `app/recommendation/engine.py`, `tests/unit/recommendation/test_engine.py` |
| R-HOLD | recommendation | IMPLEMENTED | `app/recommendation/engine.py`, `tests/unit/recommendation/test_engine.py` |
| R-EXIT | recommendation | IMPLEMENTED | `app/recommendation/engine.py`, `app/portfolio/exit_monitor/triggers.py` |
| R-ARGS | recommendation | IMPLEMENTED | `app/recommendation/engine.py`, `app/args/` |
| AC-RE-01 | recommendation | IMPLEMENTED | `app/recommendation/engine.py`, `tests/unit/recommendation/test_engine.py` |
| AC-RE-02 | recommendation | IMPLEMENTED | `app/models/recommendation.py`, `app/api/v1/recommendations.py` |
| AC-RE-03 | recommendation | IMPLEMENTED | `app/args/`, `tests/unit/investment_committee/test_advisory.py` |
| AC-RE-04 | recommendation | IMPLEMENTED | `app/recommendation/engine.py`, `tests/unit/recommendation/test_engine.py` |
| AC-RE-05 | recommendation | IMPLEMENTED | `app/recommendation/engine.py`, `tests/unit/recommendation/test_engine.py` |
| AC-RE-06 | recommendation | IMPLEMENTED | `app/api/v1/recommendations.py`, `app/services/recommendation_service.py` |
| AC-RE-07 | recommendation | IMPLEMENTED | `app/args/builders/investment_review_packet_builder.py`, `tests/unit/args/test_packet_builder.py` |
| AC-CS | recommendation | IMPLEMENTED | `app/recommendation/conviction_scorer.py`, `tests/unit/recommendation/test_conviction_scorer.py` |
| AC-LC-01 | lifecycle | PARTIALLY_IMPLEMENTED | `app/services/recommendation_service.py`, `app/api/v1/recommendations.py` |
| AC-LC-02 | lifecycle | IMPLEMENTED | `app/services/portfolio_service.py`, `app/api/v1/portfolio.py` |
| AC-LC-03 | lifecycle | IMPLEMENTED | `app/api/v1/recommendations.py`, `app/api/auth_deps.py` |
| AC-LC-04 | lifecycle | PARTIALLY_IMPLEMENTED | `app/services/traceability_service.py`, `tests/unit/services/test_platform_traceability.py` |
| AC-WNR | recommendation | IMPLEMENTED | `app/recommendation/engine.py`, `app/api/v1/recommendations.py` |
| AC-PE-01 | portfolio | IMPLEMENTED | `app/portfolio/reconciliation/service.py`, `tests/unit/portfolio/test_reconciliation.py` |
| AC-PE-02 | portfolio | IMPLEMENTED | `app/services/portfolio_service.py`, `tests/unit/portfolio/test_position_sizing.py` |
| AC-PE-03 | portfolio | PARTIALLY_IMPLEMENTED | `app/args/builders/investment_review_packet_builder.py`, `tests/unit/args/test_packet_builder.py` |
| AC-PE-04 | portfolio | IMPLEMENTED | `app/services/portfolio_service.py`, `tests/unit/portfolio/test_portfolio_service.py` |
| AC-PT-01 | paper | IMPLEMENTED | `app/services/paper_trade_service.py`, `tests/unit/services/test_paper_trade_lineage.py` |
| AC-PT-02 | paper | IMPLEMENTED | `app/execution/services/execution_service.py`, `tests/unit/execution/test_execution_service.py` |
| AC-PT-03 | paper | IMPLEMENTED | `app/portfolio/reconciliation/service.py`, `tests/unit/portfolio/test_reconciliation.py` |
| AC-PT-04 | paper | IMPLEMENTED | `app/api/v1/portfolio.py`, `tests/unit/portfolio/test_analytics.py` |
| AC-EX | portfolio | IMPLEMENTED | `app/portfolio/exit_monitor/service.py`, `app/api/v1/portfolio.py` |
| AC-HITL-01 | hitl | IMPLEMENTED | `app/execution/services/execution_service.py`, `tests/unit/execution/test_execution_service.py` |
| AC-HITL-02 | hitl | NOT_STARTED | — |
| AC-HITL-03 | hitl | IMPLEMENTED | `app/execution/adapters/paper.py`, `tests/unit/execution/test_execution_service.py` |
| AC-HITL-04 | hitl | PARTIALLY_IMPLEMENTED | `app/args/`, `frontend/packages/ui/src/screens/CommitteeScreen.tsx` |
| AC-HITL-L | hitl | PARTIALLY_IMPLEMENTED | `app/execution/services/execution_service.py`, `app/execution/adapters/zerodha_kite.py` |
| AC-EXEC-01 | execution | IMPLEMENTED | `app/execution/services/execution_service.py`, `tests/unit/execution/test_execution_service.py` |
| AC-EXEC-02 | execution | IMPLEMENTED | `app/execution/services/execution_service.py`, `app/services/paper_trade_service.py` |
| AC-EXEC-03 | execution | IMPLEMENTED | `app/execution/services/execution_service.py`, `app/models/execution.py` |
| AC-EXEC-04 | execution | NOT_STARTED | — |
| AC-EXEC-05 | execution | PARTIALLY_IMPLEMENTED | `app/ops/daily_batch/paper_pilot_ops.py`, `app/execution/adapters/zerodha_kite.py` |
| AC-EXEC-06 | execution | IMPLEMENTED | `app/execution/services/execution_service.py`, `tests/unit/execution/test_execution_service.py` |
| AC-BRK | execution | PARTIALLY_IMPLEMENTED | `app/execution/adapters/zerodha_kite.py`, `tests/unit/execution/test_zerodha_adapter.py` |
| AC-RISK | risk | NOT_STARTED | — |
| K-03 | execution | IMPLEMENTED | `app/api/v1/recommendations.py` |
| K-04 | execution | IMPLEMENTED | `app/execution/services/execution_service.py`, `app/api/v1/execution.py` |
| K-13 | execution | IMPLEMENTED | `app/api/auth_deps.py`, `app/api/v1/execution.py` |
| ADR-027-JWT | auth | IMPLEMENTED | `app/services/auth_service.py`, `app/api/v1/auth.py` |
| ADR-027-TENANCY | auth | PARTIALLY_IMPLEMENTED | `app/api/auth_deps.py`, `tests/integration/api/test_tenant_isolation.py` |
| ADR-028 | pilot | PARTIALLY_IMPLEMENTED | `app/ops/daily_batch/paper_pilot_ops.py`, `tests/unit/ops/test_paper_pilot_ops.py` |
| ADR-029 | pilot | IMPLEMENTED | `app/services/pilot_command_center_service.py`, `app/api/v1/pilot_ops.py` |
| GR-COPILOT | copilot | IMPLEMENTED | `app/copilot/`, `app/api/v1/copilot.py` |
| AC-CP | copilot | PARTIALLY_IMPLEMENTED | `app/services/copilot_service.py`, `tests/unit/copilot/test_copilot_service.py` |
| AC-FE | frontend | PARTIALLY_IMPLEMENTED | `frontend/packages/ui/src/screens/`, `frontend/packages/hooks/src/queries/` |
| AC-MOB | frontend | PARTIALLY_IMPLEMENTED | `frontend/apps/mobile/`, `context/canonical/frontend/FEATURE_INTEGRATION_REPORT.md` |
| FP-FE | frontend | PARTIALLY_IMPLEMENTED | `frontend/packages/ui/`, `context/canonical/frontend/DESIGN_SYSTEM.md` |
| FR-MOB | frontend | PARTIALLY_IMPLEMENTED | `frontend/apps/mobile/`, `context/canonical/frontend/FEATURE_INTEGRATION_REPORT.md` |
| KPI-batch | pilot | PARTIALLY_IMPLEMENTED | `app/api/v1/pilot_ops.py`, `app/services/pilot_command_center_service.py` |
| KPI-recon | pilot | PARTIALLY_IMPLEMENTED | `app/portfolio/reconciliation/service.py`, `tests/unit/portfolio/test_reconciliation.py` |
| KPI-nav | pilot | PARTIALLY_IMPLEMENTED | `app/services/daily_batch_service.py`, `app/services/portfolio_service.py` |
| GO-NOGO-recon | pilot | DOCUMENTED_ONLY | `context/canonical/runbooks/LIVE_TRADING_SAFETY_CHECKLIST.md` |
| RCEE | recommendation | IMPLEMENTED | `app/recommendation/regime_edge_engine.py`, `tests/unit/recommendation/test_regime_edge_engine.py` |
| ADR-033 | portfolio | PARTIALLY_IMPLEMENTED | `app/portfolio/exit_monitor/intraday_service.py`, `app/portfolio/exit_monitor/quote_provider.py` |
| ADR-032 | recommendation | PROPOSED | `context/canonical/decisions/ADR-032-IMPLEMENTATION.md` |
| ADR-030 | execution | PARTIALLY_IMPLEMENTED | `app/execution/adapters/zerodha_kite.py`, `context/canonical/runbooks/LIVE_TRADING_SAFETY_CHECKLIST.md` |
| ADR-031 | execution | IMPLEMENTED | `app/execution/services/execution_service.py`, `app/execution/adapters/paper.py` |
| FP-REC-HIST | frontend | IMPLEMENTED | `frontend/packages/ui/src/atoms/DatePicker.tsx`, `frontend/packages/ui/src/molecules/RecommendationExecutionPanel.tsx` |

Machine-readable: `context/generated/REQUIREMENTS.rtm.yaml`