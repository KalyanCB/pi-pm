# Product Requirements Document (PRD)

**Product:** Pi-PM — Personal Intelligence Portfolio Manager  
**Market:** Indian NSE equities (personal / research use)  
**Last synthesized:** 2026-06-04

---

## Problem

Personal investors need reproducible, auditable stock ranking and validation — not black-box LLM picks — plus structured research workflows before any capital deployment.

---

## Goals

| ID | Requirement | Acceptance |
|----|-------------|------------|
| G1 | Deterministic ranking for named strategies | Same inputs → same `ranking_runs` / `ranking_results` |
| G2 | Forward-return validation with regime splits | IC, deciles, `insufficient_data` when tail missing |
| G3 | Full NIFTY 500 daily operations | Batch orchestrator + runbook |
| G4 | Audit traceability | Factor contributions, lineage, observability API |
| G5 | Research analytics | Factor IC, exit research, research intelligence (read-only) |
| G6 | ARGS governance | Investment review packets, 5 committees + CRO, lineage API |
| G7 | Setup evidence (SEE v2) | Strategy-aware analog search on top ranks |
| G8 | Non-goals enforced | No LLM ranking, sizing, or trade approval |

---

## Users

| Persona | Needs |
|---------|--------|
| Owner / quant | Rankings, validation, regime research |
| AI engineer | Handover docs, frozen boundaries |
| PO | ARGS independence, ranking calibration decisions |

---

## Functional scope (shipped)

- Universe filter (`NIFTY_500`, `PI_PM_CORE`)
- Strategies: `momentum_v1`, `breakout_v1`
- Validation horizons: 5/10/20/60 trading days
- Daily batch: ingest → rank → validate → factor/exit hooks
- ARGS Phase 1 + committee Phase 2 independence
- SEE v2 + SQE packet enrichment (observability)

---

## Out of scope (explicit)

- Live broker execution
- LLM-generated rankings
- Automatic promotion of experimental flags (`ARGS_QRC_USE_SQE`)
- Ranking v2 in production without PO gate

---

## Success metrics (research-backed)

| Metric | Current understanding |
|--------|----------------------|
| Top-20 alpha vs benchmark | Positive in multiple segments ([outcome-attribution-report.md](../../outcome-attribution-report.md)) |
| Rank monotonicity | **Fails** — calibration research ongoing |
| Committee effective independence | **~79%** post Phase 2 |
| Validation coverage | Pending on recent tail dates |

---

## References

- [PRODUCT_STATUS.md](./PRODUCT_STATUS.md)
- [args-gap-analysis.md](../../args-gap-analysis.md)
- [PLATFORM-HANDOFF-2026.md](../../PLATFORM-HANDOFF-2026.md)
