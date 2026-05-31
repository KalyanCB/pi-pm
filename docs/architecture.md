# Pi-PM — System Architecture

**Last updated:** 2026-06-01  
**Migration head:** `20260531_0008`  
**Takeover entry point:** [`HANDOFF.md`](./HANDOFF.md)

Canonical architecture document. Legacy stub: [`architecture.md`](./architecture.md).

---

## 1. Design Principles

1. **Deterministic money logic** — ranking, validation, sizing, and risk gates are auditable code.
2. **LLM isolation** — LLMs assist research; they never rank, size, approve trades, or override risk.
3. **Layered domains** — each package owns one concern; orchestration lives in services.
4. **Idempotent runs** — `inputs_hash` prevents duplicate ranking work.
5. **Research before production** — regime policy (Sprint 8.1) replays history; it does not alter live ranking.

---

## 2. High-Level Pipeline

```
Market Data → Universe Filter → Ranking Engine → Validation
  → Traceability (Sprint 7) → Regime Policy Replay (Sprint 8.1, research only)
```

---

## 3. Regime Policy Replay (Sprint 8.1)

Research-only layer **after** ranking and validation. Reads stored artifacts; never reranks.

```
POST /regime-policy/backtest/run
  → batch_load_scored_returns_by_run() [1 SQL query]
  → validation_horizon_metrics spreads [E1/E2 fast path]
  → For each policy (E1–E4):
       RegimePolicyEngine.evaluate_run()
       RegimePolicyReplayService.replay()
         → ALLOW/BLOCK/REDUCE per day
         → E1/E2 fallback: include day from horizon metrics if snapshot returns missing (8.1.2)
       → compute_pooled_period_metrics() [no O(n²)]
       → bootstrap CI + research_findings
```

**Key packages:** `app/regime_policy/` (engine, replay, metrics, scored_returns_loader), `app/services/regime_policy_service.py`

**Data sources (read-only):**

- `ranking_results` + `ranking_performance_snapshots` (forward returns)
- `ranking_validation_reports.regime_label`
- `validation_horizon_metrics` (precomputed spread/sample_size for E1/E2 fallback)

---

## 4. Layer Responsibilities

| Layer | Package | Must NOT |
|-------|---------|----------|
| API | `app/api/v1/` | Business formulas |
| Services | `app/services/` | Factor math |
| Universe | `app/universe/` | Scoring / ranking |
| Ranking | `app/ranking/` | DB persistence |
| Validation | `app/validation/` | Change ranking |
| Regime policy | `app/regime_policy/` | Rerank, live trading |
| Repositories | `app/db/repositories/` | Domain rules |

See [`domain-boundaries.md`](./domain-boundaries.md).

---

## 5. API Surface (`/api/v1`)

| Router | Sprint |
|--------|--------|
| health, stocks, market-data, rankings, backtest, validation | 1–6 |
| observability | 7 |
| regime-policy | 8.1 |

Full catalog: [`API_REFERENCE.md`](./API_REFERENCE.md)

---

## 6. Testing

**150 tests** as of Sprint 8.1.2. Regime policy: `tests/unit/regime_policy/`, `tests/integration/api/test_regime_policy_api.py`.

---

## Related Documentation

| Doc | Content |
|-----|---------|
| [`HANDOFF.md`](./HANDOFF.md) | Takeover guide, known bugs |
| [`sprint81-regime-aware-trading.md`](./sprint81-regime-aware-trading.md) | Regime backtest runbook |
| [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md) | Tables + migrations |
| [`DECISION_LOG.md`](./DECISION_LOG.md) | ADRs |
