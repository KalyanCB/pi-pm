# Copilot Intent Matrix

**Track:** Pi-PM Copilot & Explainability  
**Date:** 2026-06-05  
**Constraint:** Copilot **explains** decisions; it **never creates** ranks, convictions, recommendations, or trades.

---

## Intent catalogue

| Intent | Investor question examples | Primary corpus | Lineage IDs |
|--------|---------------------------|----------------|-------------|
| `why_recommended` | "Why was RELIANCE recommended?" | `recommendation_results` (BUY/WATCH) | `recommendation_run_id`, `recommendation_id` |
| `why_not_recommended` | "Why was INFY not recommended?" | `recommendation_results` + `reason_codes` | `recommendation_run_id`, `recommendation_id` |
| `explain_exit` | "Why EXIT_APPROVED on SBIN?" | `recommendation_results` (EXIT_APPROVED) | `recommendation_id`, `portfolio_position_id` |
| `explain_conviction` | "Why is conviction 81?" | `recommendation_results.conviction_*` | `recommendation_run_id`, `recommendation_id` |
| `explain_committee` | "What did QRC say about HDFC?" | `committee_reviews`, `cro_reviews` | `committee_review_id`, `packet_id` |
| `explain_portfolio` | "What is my portfolio exposure?" | `portfolio_configs`, `portfolio_positions`, `portfolio_nav_history` | `portfolio_position_id`, `recommendation_id` |
| `explain_risk` | "What are the risks on HDFC?" | `reason_codes`, `high_concern` committees, `portfolio_exit_recommendations` | `committee_review_id`, `portfolio_position_id` |
| `explain_performance` | "How did recommendations perform?" | `recommendation_outcomes`, `portfolio_nav_history` | `recommendation_id`, outcome IDs |
| `explain_rank` | "Why is ITC rank 2?" | `ranking_results`, `ranking_runs` | `ranking_run_id` |
| `explain_validation` | "Is momentum_v1 validated?" | `ranking_validation_reports` | `ranking_run_id`, validation report ID |
| `ops_status` | "Did yesterday's batch pass?" | `daily_batch_runs` | batch `run_id` |
| `refused` | "Place a buy order", "Pick best stock" | — | — |

---

## Classification order (deterministic)

1. **Refuse patterns** — trade execution, stock picking, override, injection, sizing, prediction
2. **Why-not** before **why-recommended** (shared "recommend" stem)
3. **Exit** before generic rank patterns
4. **Committee / portfolio / risk / performance** before rank fallback
5. **Symbol fallback** → `explain_rank` if ticker detected
6. **Default** → `ops_status`

Implementation: `app/copilot/intent.py`

---

## Hard refuse catalogue

| Pattern class | User gets |
|---------------|-----------|
| Trade execution | "Use the HITL approval queue." |
| Ungrounded stock pick | "See GET /recommendations/daily." |
| Override deterministic layer | "Not permitted." |
| Prompt injection | "Request refused." |
| Position sizing | "Portfolio Engine handles sizing." |
| Market prediction | "Not in the corpus." |

---

## Supplementary intents (investor UX)

Rank and validation intents support **research review** without duplicating the Recommendation Engine. They read upstream tables only — no writes, no recompute.

---

## Future channel mapping (no architecture change)

| Channel | Same intents | Notes |
|---------|--------------|-------|
| Mobile copilot | All 12 | Thin client → `POST /api/v1/copilot/ask` |
| Voice assistant | All 12 | STT → same classifier; TTS reads cited answer |
| Portfolio coaching | `explain_portfolio`, `explain_risk`, `explain_performance`, `explain_exit` | Session `session_id` groups coaching turns |

---

## Test coverage

| File | Tests |
|------|-------|
| `tests/unit/copilot/test_intent.py` | Refuse, classify, entities, injection |
| `tests/unit/copilot/test_lineage.py` | Lineage ref structure |
| `tests/unit/copilot/test_citations.py` | GR-01 citation parsing |
| `tests/unit/copilot/test_copilot_service.py` | AC-CP-01..04 service flow |

**Status:** 50 copilot unit tests passing.
