# Test Gaps

Honest gaps relative to production risk. **312 tests** do not imply full E2E or operational coverage.

---

## High priority gaps

| Gap | Risk | Mitigation today |
|-----|------|------------------|
| No automated daily batch E2E test | Regressions in phase orchestration | Manual runbook + `dailyruns/` logs |
| No CI pipeline in repo | Drift on `main` | Local `pytest` before merge |
| Limited daily batch unit tests | Planner edge cases | Dry-run script |
| No load test on full-universe validation | O(n²) regressions | Documented warnings in HANDOFF |

---

## Medium priority gaps

| Gap | Notes |
|-----|-------|
| Live LLM committees | Mock provider in tests only |
| OpenAI integration | Manual scripts + dated MD exports |
| Exit research full NIFTY_500 backfill | Progress tests exist; not full scale |
| Research intelligence report content | Thin API integration |
| Paper trading / portfolio | No services → no tests |
| SEE v2 production analog quality | Unit math only; validation MD manual |
| Docker compose smoke | Not in pytest |

---

## Low priority / acceptable

| Gap | Notes |
|-----|-------|
| PDF guide generator | `generate_pi_pm_guide_pdf.py` untested |
| Recovery scripts | Ad-hoc ops |
| Ranking research report MD | Logic tested; not file output |

---

## Recommended additions (documentation only — not implemented)

1. Integration test: mini daily batch on `PI_PM_CORE` fixture DB  
2. GitHub Actions: `pytest` + `alembic check`  
3. Contract test: OpenAPI snapshot vs [API_REFERENCE.md](../07_API/API_REFERENCE.md)  
4. Regression: rank monotonicity metric on synthetic uncompressed scores  

See [TEST_COVERAGE_REPORT.md](./TEST_COVERAGE_REPORT.md).
