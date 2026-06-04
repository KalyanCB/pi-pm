# Architectural Decisions

Synthesized from [DECISION_LOG.md](../../DECISION_LOG.md) and platform handoff PO items.

---

## Accepted ADRs (legacy log)

| ID | Decision | Status |
|----|----------|--------|
| ADR-001 | Deterministic core; LLMs never rank/size/approve | Accepted |
| ADR-002 | PostgreSQL system of record | Accepted |
| ADR-003 | Yahoo Finance primary data | Accepted (caveats) |
| ADR-004+ | See [DECISION_LOG.md](../../DECISION_LOG.md) | Various |

---

## 2026 research / product decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Ranking calibration v2 | **Hold** — no prod deploy | Non-monotonic ranks; compression root cause documented |
| ARGS_QRC_USE_SQE | **Default false** | A/B: legacy brief sufficient; SQE observability only on packets |
| Committee Phase 2 | **Shipped** | Independence ~79% vs ~14% |
| Committee Phase 3 | **Not started** | Await PO scope |
| Regime policy | **Research API only** | Not live trading |
| SQE on packets | **Ship** without QRC cutover | Enriches packets; no committee default change |
| Outcome attribution | **Read-only analytics** | Informs PO; does not auto-change weights |

---

## Pending PO decisions

1. Criteria to promote ranking calibration / isotonic v2  
2. Criteria to set `ARGS_QRC_USE_SQE=true` globally  
3. Committee Phase 3 mandate (evidence rules, voting, CRO binding)  
4. Exit research → portfolio construction gate  

Track in [CURRENT_PRIORITIES.md](../11_ROADMAP/CURRENT_PRIORITIES.md).

---

## Anti-patterns (rejected)

| Pattern | Why rejected |
|---------|--------------|
| LLM ranking | Non-auditable |
| Policy changing factor weights | Breaks attribution |
| Pooling 100k rows via full horizon metrics | O(n²) production incident |
| Global SQE QRC without experiment | PO requires A/B evidence |

Full ADR text: [../../DECISION_LOG.md](../../DECISION_LOG.md).
