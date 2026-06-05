# Pi-PM Test Report — Track A Platform Hardening

**Date:** 2026-06-05  
**Environment:** Python 3.13.4, macOS (local validation)

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tests** | 537 |
| **Passed** | 537 |
| **Failed** | 0 |
| **Pass rate** | 100% |
| **Coverage (app/)** | 73% |
| **Duration** | ~62–80 seconds |

---

## Fixes Applied

Seven copilot-related tests were failing before Track A work:

| Test | Root Cause | Fix |
|------|------------|-----|
| `test_refuse_patterns[Place a buy order...]` | Regex required adjacent verb/noun | Allow words between verb and order/trade |
| `test_refuse_patterns[Execute a trade...]` | Same | Same |
| `test_prompt_injection_refused` (intent) | "Ignore all previous instructions" not matched | Allow words between ignore and instructions |
| `test_intent_classification[...selling INFY]` | `sell` didn't match `selling` | Added `sell(ing\|s)?` pattern |
| `test_prompt_injection_refused` (service) | Intent classifier fix | Cascaded from intent fix |
| `test_trade_execution_refused` | Trade regex fix | Cascaded from intent fix |
| `test_ops_intent` | `DailyBatchRun.created_at` doesn't exist | Use `started_at` in retriever |

---

## New Platform Tests

| Test File | Tests Added | Coverage |
|-----------|-------------|----------|
| `tests/test_health.py` | liveness, readiness, DB failure, correlation ID | Health endpoints |
| `tests/test_platform.py` | request ID headers, error_code in responses | Middleware + error handling |

---

## Coverage Highlights

| Module | Coverage |
|--------|----------|
| `app/core/` (platform) | ~95%+ on new files |
| `app/api/v1/health.py` | 100% |
| `app/copilot/intent.py` | High (all classifier paths tested) |
| Overall `app/` | 73% |

Low-coverage areas (pre-existing, not in Track A scope):

- `app/workspace_exit_research/data_cache.py` — 33%
- `app/workspace_args/evidence_validator.py` — 47%
- Integration paths requiring live PostgreSQL + Yahoo

---

## CI Test Command

```bash
pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-report=html -q
```

Artifacts uploaded in GitHub Actions: `coverage.xml`, `htmlcov/`

---

## Known Flaky Test

`tests/unit/workspace_exit_research/test_forward_returns_benchmark.py::test_alpha_decay_benchmark_speedup` — timing-sensitive benchmark; may fail under CPU load. Passes on isolated re-run.

**Recommendation:** Add `@pytest.mark.slow` and exclude from default CI or increase speedup threshold.

---

## Regression Status

All 524 original tests pass plus 13 new platform tests (537 total). No business logic tests modified.
