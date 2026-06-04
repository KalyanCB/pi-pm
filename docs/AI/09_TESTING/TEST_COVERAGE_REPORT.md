# Test Coverage Report

**Collected:** 2026-06-04 · **Command:** `pytest --collect-only -q`  
**Total tests:** **312**

---

## By subsystem (file-based estimate)

| Subsystem | Test files | ~Tests | Coverage quality |
|-----------|------------|--------|------------------|
| ARGS / governance | 18 | ~55 | Strong — packets, committees, QRC flag |
| Ranking | 12 | ~30 | Strong — engine, factors, golden |
| Validation | 8 | ~25 | Strong — stats, regimes, API |
| Factor analytics | 8 | ~25 | Strong — engine, backfill |
| Exit research | 6 | ~22 | Good — simulators, phases |
| Regime policy | 5 | ~14 | Good — engine, replay |
| Services | 10 | ~35 | Good — orchestration |
| Integration API | 9 | ~35 | Good — HTTP contracts |
| Ranking research | 5 | ~10 | Moderate — report logic |
| Outcome attribution | 2 | ~11 | Good |
| SEE | 2 | ~5 | Moderate |
| Stock / market / universe | 6 | ~20 | Good |
| Ops / daily batch | 2 | ~4 | Light |
| Health | 1 | 1 | Smoke only |
| Backtest | 2 | ~4 | Light |
| Providers | 1 | ~5 | Moderate |

---

## Integration vs unit

| Layer | Path | Files |
|-------|------|-------|
| Unit | `tests/unit/` | ~85 |
| Integration | `tests/integration/` | ~9 |
| Root | `tests/test_health.py` | 1 |

---

## What tests prove

- Deterministic ranking outputs (golden tests)
- Validation IC/regime math
- ARGS packet schema and evidence enforcement
- `ARGS_QRC_USE_SQE` respects default false
- API status codes and core payloads
- Regime replay does not hang on pooled metrics path

---

## Not covered (see TEST_GAPS.md)

- End-to-end daily batch in CI
- Live OpenAI committee calls
- Paper trading / portfolio
- Full exit backfill at NIFTY_500 scale
- Browser / UI (none)

---

## Running

```bash
pytest tests/ -q
pytest tests/unit/args/ -q
pytest tests/integration/api/ -q
```
