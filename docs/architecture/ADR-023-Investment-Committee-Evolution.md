# ADR-023: Investment Committee Evolution (M3.1)

**Status:** Accepted (PO sign-off 2026-06-05)  
**Date:** 2026-06-05  
**Deciders:** Product Owner  
**Supersedes:** N/A — additive to ADR-021, ADR-022  
**Related:** [ADR-021](./ADR-021-Recommendation-Platform-Architecture.md), [ADR-022](./ADR-022-Recommendation-Performance-Framework.md), [08_AI_INVESTMENT_COMMITTEE_PRD.md](../product-next/08_AI_INVESTMENT_COMMITTEE_PRD.md)

---

## Context

ARGS (Automated Research Governance System) is the internal name for the AI committee system. Externally it presents as a set of "research labels" (`supportive/neutral/cautious`) that are not intuitive to an investor. Phase 2 introduced the Recommendation Engine, making it possible to elevate ARGS from a research governance tool into an investor-facing **Investment Committee** that advises on recommendations.

This ADR governs the product-surface elevation — not a rewrite of internals.

---

## Decision

Implement **M3.1 Investment Committee Evolution** as a pure product-surface enhancement:

1. Add `CommitteeAdvisoryAction` enum (`APPROVE/WATCH/REJECT/EXIT_APPROVED/HIGH_CONCERN`)
2. Extend DB models additively (new columns on `committee_reviews`, `cro_reviews`)
3. Shift investor-facing API vocabulary to "Investment Committee" while keeping internal mechanics stable
4. Implement `HIGH_CONCERN` escalation with override logic (not majority voting)
5. Preserve internal ARGS trigger mechanism — ARGS runs are triggered via `POST /research/run` (external API call), not via a `DailyBatchPhase`. The `DailyBatchPhase` enum has no ARGS/research phase and this is unchanged.
6. All committee outputs remain advisory — no influence on conviction or recommendation

---

## Why ARGS becomes Investment Committee externally

ARGS was a developer-facing label for an internal research governance framework. As Pi-PM evolves toward an investor-facing product (mobile app, HITL execution), the language must match how a portfolio owner thinks:

| Internal | External |
|----------|---------|
| ARGS research run | Investment Committee review |
| Committee research label | Committee advisory action |
| CRO synthesis | Committee Chair report |
| `supportive` | APPROVE |
| `cautious` | REJECT |

The underlying five-committee structure, LLM routing, evidence packets, and Phase 2 independence (~79%) remain identical.

---

## Why internal implementation remains stable

Changing internal module names, DB column names, or batch phase names would:
- Break historical observability dashboards
- Invalidate existing lineage records
- Require data migrations with no product value
- Risk introducing bugs in a working, tested system

**Only the presentation layer changes.** `app/args/`, `app/workspace_args/`, and the `DailyBatchPhase` enum are untouched internally. Note: `DailyBatchPhase.RESEARCH` was never part of the enum — ARGS runs are triggered separately via the `/research/run` API endpoint, not as a batch phase.

---

## Why HIGH_CONCERN overrides majority

Risk concerns are not democratic. A single committee raising `HIGH_CONCERN` represents a material governance, fraud, or concentration risk that cannot be diluted by four other committees approving. Example:

```
TARC = APPROVE
FRC  = APPROVE
QRC  = APPROVE
NRCC = APPROVE
RC   = HIGH_CONCERN   ← fraud allegation, regulatory action
```

Majority voting → `APPROVE` (4:1) — **incorrect and dangerous.**
Override logic → `HIGH_CONCERN` — **correct: elevate to human attention.**

**Rule:**
```python
if any(action == HIGH_CONCERN for action in committee_actions):
    cro_advisory_action = HIGH_CONCERN
else:
    cro_advisory_action = majority_vote(committee_actions)
```

The CRO narrative must explain the originating committee, concern reason, and supporting evidence.

---

## Why committee outputs remain advisory

The Recommendation Engine produces deterministic `action` and `conviction_score` from five quantitative inputs. Allowing LLM committee outputs to modify these values would:
- Introduce non-determinism into capital decisions
- Violate PRD G8 (no LLM ranking/sizing)
- Break AC-RE-03 (committee run must not mutate recommendation)
- Make conviction scores non-reproducible

The Investment Committee exists to **surface information** to the human decision maker — not to override the machine.

---

## Why human approval remains mandatory

The system follows: `Ranking → Validation → Recommendation Engine → Investment Committee → Human → Portfolio`

The Investment Committee is positioned before the human, not after. It informs the human's decision. The human retains final authority on all entries and exits per [11_HUMAN_IN_LOOP_EXECUTION_PRD.md](../product-next/11_HUMAN_IN_LOOP_EXECUTION_PRD.md).

---

## Consequences

### Positive
- Investor-friendly language aligns with mobile app (M4) and HITL execution (M3)
- `HIGH_CONCERN` escalation gives the human a clear signal without overriding the machine
- Additive migration means zero downtime, zero data loss
- Committee independence analytics foundation laid for future measurement

### Negative / Constraints
- Old `/research/*` routes kept as deprecated aliases — need eventual sunset
- `CommitteeResearchLabel` kept alongside new enum — two label systems temporarily
- `HIGH_CONCERN` escalation requires LLM prompts to be updated to emit the flag (Phase 3 scope)

### Invariants preserved
- `DailyBatchPhase` enum unchanged (ARGS has no batch phase — triggered via separate API)
- `CommitteeResearchLabel` enum unchanged (backward compat)
- R-ARGS-04: committee outputs cannot mutate `recommendation.action`, `conviction_score`, `conviction_band`
- No LLM involvement in conviction, ranking, or position sizing

---

## References

- [PO Sign-off 2026-06-05 (M3.1)](../product-next/PO_SIGNOFF_2026_06_04.md)
- [08_AI_INVESTMENT_COMMITTEE_PRD.md](../product-next/08_AI_INVESTMENT_COMMITTEE_PRD.md)
- [02_CONVICTION_SCORING_PRD.md](../product-next/02_CONVICTION_SCORING_PRD.md)
- [01_RECOMMENDATION_ENGINE_PRD.md](../product-next/01_RECOMMENDATION_ENGINE_PRD.md)
