# ADR-032: Live Entry Timing & Validation Gate

**Status:** Proposed  
**Date:** 2026-06-05  
**Deciders:** Product Owner (required), Principal Quant Platform Engineer  
**Supersedes:** N/A — clarifies and extends ADR-021, ADR-028, ADR-030  
**Related:** [ADR-021](./ADR-021-Recommendation-Platform-Architecture.md), [01_RECOMMENDATION_ENGINE_PRD.md](../product-next/01_RECOMMENDATION_ENGINE_PRD.md), [13_PO_BACKLOG.md](../product-next/13_PO_BACKLOG.md) (F-OPS-1, S-REC-2.2), [16_WHY_NOT_RECOMMENDED_FRAMEWORK.md](../product-next/16_WHY_NOT_RECOMMENDED_FRAMEWORK.md)

---

## Context

Pi-PM targets a **15–30 trading day swing book** ([15_EXECUTIVE_PRODUCT_STRATEGY.md](../product-next/15_EXECUTIVE_PRODUCT_STRATEGY.md)) with daily ingest → rank → validate → recommend. Implementation matches **R-ENTRY-02**: per-run `validation.status == insufficient_data` → max **WATCH** (`app/recommendation/engine.py:220-224`).

The **validation tail** (~5 sessions for minimum horizon) means the **latest as-of date** almost always blocks **BUY**. Ops expectation (F-OPS-1) is `completed` validation on **T−5**, not **T**. Historical validation feeds **ARGS/QRC only** (`investment_review_packet_builder.py`) — not the recommendation engine.

**Gap:** No governing artifact defined *when* capital may deploy relative to signal freshness. Stakeholders conflate **WATCH** (monitor) with **BUY** (capital). Swing entry windows can close before per-run validation matures.

---

## Problem

| Tension | Today |
|---------|-------|
| Signal freshness | Rankings reflect **T** (momentum/breakout factors) |
| BUY gate | Requires **that ranking_run’s** forward validation `completed` (~T+5 ingest) |
| Human HITL | Queue accepts **BUY** / **EXIT_APPROVED** only — not **WATCH** |
| Paper / live | Execution paths require `action=BUY` + `APPROVED` |

Result: latest day produces a **monitor list**, not an **actionable entry queue**, unless PO accepts **lagged entries** on stale ranking snapshots.

---

## Decision (proposed)

Adopt an explicit **two-lane entry model** and PO-selectable **validation gate mode** for swing deployment.

### 1. Two lanes (product semantics)

| Lane | As-of | Machine action | Human role | Capital |
|------|-------|----------------|------------|---------|
| **Monitor** | **T** (latest) | **WATCH** when tail pending | Research, ARGS, copilot | None |
| **Deploy** | **T−k** matured (k ≥ 5 with F-OPS-1) | **BUY** when gates pass | HITL approve → paper/live | Yes |

Daily batch **always** runs recommendations on **T** (monitor lane). **Deploy lane** is populated by re-running recommendations on ranking runs whose validation has matured, or by a scheduled **T−5** batch window.

### 2. Validation gate modes (PO config — one active)

| Mode | R-ENTRY-02 behaviour | Use when |
|------|----------------------|----------|
| **`per_run_strict`** (default, current code) | `insufficient_data` → WATCH; BUY only when **this** run `completed` | Maximum audit proof; paper pilot proof |
| **`strategy_trust`** (new) | Tail pending caps conviction only; BUY allowed if **strategy/regime historical validation** meets PO threshold **and** rank fresh at **T** | Swing timing priority; requires new engine input + tests |
| **`watch_hitl`** (new) | **WATCH** on tail may enter HITL as **DEFERRED** entry with `VALIDATION_PENDING` flag; human assumes timing risk | Owner discretion; explicit audit |

**PO must sign one mode before live S1.** Default remains **`per_run_strict`** — no engine change until PO approves B or C.

### 3. Freshness guard (all modes)

Any **BUY** or human-approved entry must pass **freshness check** at approval time:

- Re-rank or re-check: symbol still in **top pool on current session T**, **or**
- PO documents acceptance of **lagged snapshot** (deploy lane only).

Prevents buying last week’s breakout after rank has fallen out of pool.

### 4. Non-goals

- ARGS / historical validation **must not** auto-upgrade `action` (ADR-021 unchanged).
- LLM influence on gate or conviction (PO sign-off §1 unchanged).
- Auto-execution without human **APPROVED** (ADR-030 unchanged).

---

## Consequences

### Positive

- Closes documentation gap between swing horizon and validation lag.
- UI can label **Monitor (T)** vs **Deploy (T−k)** without changing ranking math.
- Paper pilot metrics interpretable: entries reflect chosen gate mode.

### Negative / cost

- **`strategy_trust`** or **`watch_hitl`**: PRD + engine + API + mobile changes; new reason codes and audit fields.
- **`per_run_strict`**: latest session remains WATCH-heavy; empty HITL queue on tail days is **expected**, not failure.
- Freshness re-rank adds latency at approval time.

---

## Implementation checklist (if PO accepts)

| Item | Mode |
|------|------|
| `recommendation_config.validation_gate_mode` enum | B / C |
| Engine: split **strategy validation** input from per-run report | B |
| `GET /recommendations/queue?lane=deploy` | All |
| Approve path for `WATCH` + `ENTRY_DEFERRED` + explicit flags | C |
| Freshness check service at `approve()` | All |
| Update `01_RECOMMENDATION_ENGINE_PRD.md` R-ENTRY-01/02 | All |
| Golden tests per mode | All |

**No code change required** if PO reaffirms **`per_run_strict`** — this ADR still records intended T vs T−k semantics.

---

## PO decision required

- [ ] **A.** Reaffirm `per_run_strict` — document T = WATCH monitor, T−5 = deploy (ops only).
- [ ] **B.** Adopt `strategy_trust` — specify historical validation thresholds (regime, IC, min completed runs).
- [ ] **C.** Adopt `watch_hitl` — owner may approve WATCH on tail with signed timing risk.
- [ ] Freshness: **re-rank at approve** vs **accept lagged snapshot** for deploy lane.

**Sign-off:** _________________ Date: _________

---

## References

- [VALIDATION_DESIGN.md](../AI/03_DESIGN/VALIDATION_DESIGN.md) — tail gap
- [daily-nifty500-batch-runbook.md](../daily-nifty500-batch-runbook.md) — T+5 ingest
- `app/recommendation/engine.py` — R-ENTRY-02
- `app/args/validation_status.py` — historical context for QRC only
