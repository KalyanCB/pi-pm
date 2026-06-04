# Committee Design

**Owner:** `app/args/` (per-committee modules + `committee_packet_views.py`)

---

## Committees

| Code | Role | Packet view |
|------|------|-------------|
| TARC | Technical / trend | Isolated technical refs |
| QRC | Quant research | `quant_research_brief` or experimental SQE brief |
| FRC | Fundamental | Fundamental snapshot refs |
| NRCC | News / narrative | News snapshot refs |
| RC | Risk | Risk / concentration refs |
| CRO | Chief research officer | Synthesis, no-trade rules |

---

## Phase 1 problem

~14% effective independence; ~60% evidence overlap; ranking/regime refs cloned across committees ([committee-effectiveness-report.md](../../committee-effectiveness-report.md)).

---

## Phase 2 solution

| Mechanism | Module |
|-----------|--------|
| Prompt isolation | `committee_packet_views.py` |
| Evidence enforcement | `committee_evidence_enforcement.py` |
| contrarian_view | Required in LLM JSON |
| No degraded clones | Committee-specific abstention |

**Result:** ~79% effective independence ([committee-independence-phase2-results.md](../../committee-independence-phase2-results.md)).

---

## Phase 3

Not started — await PO scope after Phase 2 stabilization.

Related: [committee-independence-design.md](../../committee-independence-design.md), [committee-overlap-analysis.md](../../committee-overlap-analysis.md), [consensus-analysis.md](../../consensus-analysis.md).
