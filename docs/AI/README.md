# Pi-PM AI Documentation Package

**Start here:** [12_HANDOVER/AI_AGENT_HANDOVER.md](./12_HANDOVER/AI_AGENT_HANDOVER.md)

This tree supplements legacy docs under [`docs/`](../README.md). Nothing here replaces production code; it indexes and synthesizes existing material for AI engineers and new contributors.

---

## Handover (read first)

| Doc | Description |
|-----|-------------|
| [**AI_AGENT_HANDOVER.md**](./12_HANDOVER/AI_AGENT_HANDOVER.md) | Primary takeover guide |
| [PROJECT_STATE_2026_06_04.md](./12_HANDOVER/PROJECT_STATE_2026_06_04.md) | Snapshot as of 2026-06-04 |
| [DOCUMENTATION_COMPLETENESS_REPORT.md](./12_HANDOVER/DOCUMENTATION_COMPLETENESS_REPORT.md) | Coverage % by area |
| [DOCUMENT_INVENTORY.md](./09_HANDOVER/DOCUMENT_INVENTORY.md) | Full doc/code inventory |

Legacy entry points (still authoritative for depth): [PLATFORM-HANDOFF-2026.md](../PLATFORM-HANDOFF-2026.md), [HANDOFF.md](../HANDOFF.md).

---

## Package map

| Section | Index |
|---------|--------|
| Executive | [00_EXECUTIVE_SUMMARY/PROJECT_OVERVIEW.md](./00_EXECUTIVE_SUMMARY/PROJECT_OVERVIEW.md) |
| Product | [01_PRODUCT/PRD.md](./01_PRODUCT/PRD.md), [PRODUCT_STATUS.md](./01_PRODUCT/PRODUCT_STATUS.md) |
| Architecture | [02_ARCHITECTURE/](./02_ARCHITECTURE/) |
| Design | [03_DESIGN/](./03_DESIGN/) |
| Implementation | [04_IMPLEMENTATION/](./04_IMPLEMENTATION/) |
| Research | [05_RESEARCH/RESEARCH_SUMMARY.md](./05_RESEARCH/RESEARCH_SUMMARY.md) |
| Operations | [06_OPERATIONS/](./06_OPERATIONS/) |
| API | [07_API/](./07_API/) |
| Data model | [08_DATA_MODEL/](./08_DATA_MODEL/) |
| Testing | [09_TESTING/](./09_TESTING/) |
| Decisions | [10_DECISIONS/ARCHITECTURAL_DECISIONS.md](./10_DECISIONS/ARCHITECTURAL_DECISIONS.md) |
| Roadmap | [11_ROADMAP/CURRENT_PRIORITIES.md](./11_ROADMAP/CURRENT_PRIORITIES.md) |
| Handover | [12_HANDOVER/](./12_HANDOVER/) |

---

## Non-negotiables

1. LLMs never rank securities, size positions, approve trades, or override risk.
2. Ranking and validation logic are **frozen** unless explicitly scoped.
3. Default universe is `PI_PM_CORE` — ops use **`NIFTY_500`**.
4. **`ARGS_QRC_USE_SQE=false`** (production default).
5. Committee **Phase 3** not started; Phase 2 independence ~79% effective.
