# Governance Design

Pi-PM governance = **deterministic quant core** + **ARGS human-in-the-loop research** + **explicit PO gates** for anything that touches rankings or default LLM paths.

---

## Layers

| Layer | Governance |
|-------|------------|
| Ranking / validation | Frozen; versioned strategies; no LLM |
| Traceability | Append-only style records; lineage API |
| Regime / exit / factor | Research tables; read-only analytics APIs |
| ARGS | Evidence allowlists, committee isolation, CRO no-trade fields |
| Feature flags | `ARGS_QRC_USE_SQE` — default false, PO sign-off for global enable |
| Experiments | `experiment_runs` via observability API |

---

## Non-negotiables (ADR-001)

LLMs never: rank, size, approve trades, override risk.

See [ARCHITECTURAL_DECISIONS.md](../10_DECISIONS/ARCHITECTURAL_DECISIONS.md).

---

## Audit artifacts

- `run_lineage_records`
- ARGS `/research/{id}/lineage`
- Daily run logs: `docs/dailyruns/<date>/`
- Packet evidence audit: [args-packet-evidence-audit.md](../../args-packet-evidence-audit.md)

---

## PO decision log (open)

| Decision | Doc |
|----------|-----|
| Ranking v2 | [ranking-calibration-root-cause.md](../../ranking-calibration-root-cause.md) |
| QRC SQE default | [qrc-sqe-ab-test-report.md](../../qrc-sqe-ab-test-report.md) |
| Committee Phase 3 | [committee-independence-design.md](../../committee-independence-design.md) |
