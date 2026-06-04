# Test Coverage Assessment

**Date:** 2026-06-05  
**Command:** `pytest tests/ --collect-only -q` (via `.venv`)  
**Result:** **312 tests collected**

---

## Summary by area

| Area | Count | % of total |
|------|-------|------------|
| unit/args | 63 | 20.2% |
| unit/services | 42 | 13.5% |
| integration/api | 36 | 11.5% |
| unit/factor_analytics | 27 | 8.7% |
| unit/ranking | 25 | 8.0% |
| unit/workspace_exit_research | 25 | 8.0% |
| unit/validation | 16 | 5.1% |
| unit/core | 14 | 4.5% |
| unit/regime_policy | 14 | 4.5% |
| unit/outcome_attribution | 11 | 3.5% |
| unit/ranking_research | 10 | 3.2% |
| integration/args | 5 | 1.6% |
| unit/providers | 5 | 1.6% |
| unit/stock_setup_evidence | 5 | 1.6% |
| unit/backtest | 4 | 1.3% |
| unit/ops | 4 | 1.3% |
| unit/universe | 4 | 1.3% |
| unit/market_data | 1 | 0.3% |
| root (health) | 1 | 0.3% |
| **Total** | **312** | **100%** |

---

## Coverage by product domain

| Domain | Unit | Integration | Assessment |
|--------|------|-------------|------------|
| Ranking engine | 25 + factors | 6 (rankings API) | **Strong** — golden + factor tests |
| Validation | 16 | 7 + 4 (full-universe) | **Strong** |
| ARGS / committees | 63 | 5 | **Strong** — mock LLM only |
| Factor analytics | 27 | 4 | **Good** |
| Exit research | 25 | 2 (shared) | **Good** — simulators well tested |
| Daily batch | 1 (planner) + service tests partial | 0 E2E | **Weak** |
| Regime policy | 14 | 4 | **Moderate** |
| SEE v2 | 5 | 1 | **Thin** |
| Outcome attribution | 11 | 0 | **Moderate** — no API |
| Ranking research | 10 | 0 | **Moderate** — research scripts |
| Portfolio / paper trade | 0 | 0 | **None** |
| Market data cache | 1 | 6 (ingest API) | **Moderate** |
| Research intelligence | 0 dedicated | 2 (exit_and_research) | **Thin** |
| Observability / traceability | 8 (sprint71) + 3 platform | 0 dedicated | **Moderate** |

---

## Integration API test files

| File | Focus |
|------|-------|
| `tests/integration/api/test_rankings_api.py` | 6 tests |
| `tests/integration/api/test_validation_api.py` | 7 tests |
| `tests/integration/api/test_market_data_api.py` | 6 tests |
| `tests/integration/api/test_factor_analytics_api.py` | 4 tests |
| `tests/integration/api/test_regime_policy_api.py` | 4 tests |
| `tests/integration/api/test_full_universe_validation_api.py` | 4 tests |
| `tests/integration/api/test_backtest_api.py` | 2 tests |
| `tests/integration/api/test_exit_and_research_api.py` | 2 tests |
| `tests/integration/api/test_stock_setup_research_api.py` | 1 test |

**Gap:** No integration tests for `/ops/daily-batch`, `/observability`, `/research` (except args module).

---

## ARGS test highlights

| File | Tests | Covers |
|------|-------|--------|
| `test_committee_evidence_enforcement.py` | 8 | Evidence repair |
| `test_committee_effectiveness.py` | 8 | Independence metrics |
| `test_committee_packet_views.py` | 5 | Phase 2 views |
| `test_qrc_sqe_flag.py` | 2 | `ARGS_QRC_USE_SQE` |
| `test_workflow_mock_llm.py` | 1 | LangGraph workflow |
| `integration/args/test_research_api.py` | 1 | Research HTTP |

---

## Golden / regression tests

| File | Purpose |
|------|---------|
| `tests/unit/ranking/test_golden_ranking.py` | Ranking hash stability |
| `tests/unit/validation/test_golden_validation.py` | Validation hash stability |
| `tests/unit/args/test_packet_schema.py` | Golden packet fixture |

---

## Documented gaps (aligned with code)

From [`docs/AI/09_TESTING/TEST_GAPS.md`](../AI/09_TESTING/TEST_GAPS.md):

| Priority | Gap | Confirmed |
|----------|-----|-----------|
| High | No daily batch E2E | ✓ Only `test_daily_batch_planner.py` (1 test) |
| High | No CI pipeline | ✓ No `.github/workflows` with pytest |
| High | Limited batch unit tests | ✓ |
| Medium | Live LLM committees untested in CI | ✓ Mock only |
| Medium | Paper trading — no tests | ✓ No services |
| Medium | Docker compose smoke | ✓ Not in pytest |
| Medium | Research intelligence content | ✓ Thin |

---

## Recommended test additions (documentation only)

1. Mini daily batch integration on fixture DB (`PI_PM_CORE`)
2. GitHub Actions: `pytest` + `alembic check`
3. OpenAPI contract snapshot vs [04_API_CATALOG.md](./04_API_CATALOG.md)
4. `/research/run` happy path integration with mock LLM
5. Observability lineage integration test

---

## Discrepancies

| Source | Note |
|--------|------|
| HANDOVER "312 passed" | Collect-only confirms 312 tests exist; execution assumed green per handover |
| `docs/AI/09_TESTING/TEST_COVERAGE_REPORT.md` | May predate SEE v2 / ARGS Phase 2 tests |

---

## References

- [`docs/AI/09_TESTING/TEST_GAPS.md`](../AI/09_TESTING/TEST_GAPS.md)
- [`docs/AI/09_TESTING/TEST_SCENARIO_CATALOG.md`](../AI/09_TESTING/TEST_SCENARIO_CATALOG.md)
- `tests/conftest.py` — shared fixtures
