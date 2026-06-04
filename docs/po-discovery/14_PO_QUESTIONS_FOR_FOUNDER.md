# PO Questions for Founder

**Date:** 2026-06-05  
**Scope:** Unknowns **not answerable from code or existing docs** — requires founder/PO judgment

Questions exclude items already verified in codebase (see [INDEX.md](./INDEX.md) verified facts).

---

## Product vision

1. **Target user in 12 months:** Research-only quant workspace, or consumer mobile portfolio app? Code supports former; name/branding implies latter.

2. **Is live capital deployment in scope** for Pi-PM v1.0, or permanently research/paper-only per PRD?

3. **Geographic/market expansion** beyond NSE NIFTY 500 — any planned universe (midcap, US ADRs)?

---

## Ranking & recommendations

4. **Ranking v2 promotion bar:** What OOS metrics (monotonicity, Sharpe, max DD) must calibrated ranks meet before replacing `breakout_v1`/`momentum_v1` in production?

5. **Honest user-facing claim:** Is "top-20 pool alpha" sufficient for launch messaging, or is rank-order precision required before any user-facing recommendation?

6. **Buy/hold/exit semantics:** Should ARGS committee labels map to user-visible actions, or remain internal research governance only?

---

## ARGS & AI

7. **`ARGS_QRC_USE_SQE`:** Approve keeping default `false` indefinitely, or set a date/experiment budget to re-evaluate?

8. **Committee Phase 3:** Target independence metric (e.g., 85%+)? Budget for prompt/model changes vs architectural changes?

9. **Live LLM budget:** Expected monthly OpenAI spend for daily top-20 × 2 strategies × 5 committees + CRO?

10. **Mock LLM in staging:** Is `args_llm_provider=mock` acceptable for demo environments, or must staging always use live models?

---

## Portfolio & mobile

11. **Paper trading MVP scope:** Full simulate-fill engine, or manual position entry for ARGS context only?

12. **Position sizing rules:** Equal-weight top-N, volatility-targeted, or fixed notional — who owns the spec?

13. **Mobile priority:** P3 in roadmap — confirm deferral or accelerate? Any existing external mobile repo not in this workspace?

14. **Authentication model:** Single-owner deployment, or multi-user family/office accounts?

---

## Operations & compliance

15. **Production hosting:** Where does daily batch run (local cron, cloud VM, GitHub Actions)? Not defined in repo.

16. **Data licensing:** Yahoo Finance as sole vendor — acceptable for production scale and ToS?

17. **Regulatory framing (India):** Is Pi-PM explicitly non-advisory research tooling? Legal review status **unknown**.

18. **SLA for daily batch:** Required completion time after NSE close?

---

## Organization & process

19. **Branch strategy:** When does `feature/see-v2` merge to `main`? Who approves?

20. **PO authority:** Can PO approve ranking factor changes, or eng-only with research sign-off?

21. **Sprint 8.4 AI research agent:** Still desired? No code exists — prioritize vs portfolio?

22. **Exit research:** Which exit policy winner should drive future portfolio rules, or remain analytics-only?

---

## Business

23. **Monetization:** Personal tool only, or future productization?

24. **Success in 6 months:** What measurable outcome defines Pi-PM "working" for the founder (alpha, ops reliability, ARGS quality, user count)?

---

## Already answered in code (do not re-ask)

| Question | Answer | Evidence |
|----------|--------|----------|
| How many ranking strategies in prod? | 2 | `app/ranking/registry.py` |
| Default QRC SQE flag? | false | `app/core/config.py:79` |
| Committees count? | 5 + CRO | `app/workspace_args/constants.py` |
| Paper trade services exist? | No | `app/portfolio/__init__.py` |
| Test count? | 312 | pytest collect 2026-06-05 |

---

## References

- [13_ROADMAP_RECOMMENDATION.md](./13_ROADMAP_RECOMMENDATION.md)
- [15_EXECUTIVE_SUMMARY.md](./15_EXECUTIVE_SUMMARY.md)
