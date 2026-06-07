# Pi-PM Platform Handoff — June 2026

**Last updated:** 2026-06-05  
**Audience:** AI engineers, Product Owners, new contributors  
**Purpose:** Single entry point to continue Pi-PM work without chat context.

**Read this first.** Then follow links for depth. Legacy onboarding: [`HANDOFF.md`](./HANDOFF.md) (Sprint 8.x focus, now points here).

---

## 1. System snapshot

| Item | Value |
|------|-------|
| Repo | `/Users/kalyancb/pi-pm` |
| Remote | `https://github.com/KalyanCB/pi-pm.git` |
| **Active branch** | `feature/see-v2` |
| Base branch | `main` |
| **Migration head** | `20260610_0026` (unified execution) |
| **Tests** | **574 passed** (`pytest tests/ -q`) |
| **Auth** | JWT on all domain routes (`app/api/router.py`); health + login public |
| API | FastAPI @ `/api/v1` |
| DB | PostgreSQL 16 (`pipm` / `pipm`) |

**Recent commits (newest first):**

| Commit | Summary |
|--------|---------|
| `5c75c3c` | chore(docs): remove obsolete logs and duplicate ARGS exports |
| `7852e34` | feat(research): committee phase 2, SQE/QRC, ranking and outcome analytics |
| `cd8e251` | feat(research): stock setup evidence + stronger ARGS packets |
| `04fb536` | feat(args): ARGS Phase 1 research governance workflow |
| `7ff1831` | feat(sprint-8.6): daily NIFTY 500 batch orchestration |

**Non-negotiable:** LLMs never rank securities, size positions, approve trades, or override risk. Money logic is deterministic.

---

## 2. System map

```mermaid
flowchart TB
  subgraph prod [Production pipeline]
    ING[Market data ingest Yahoo]
    UNI[Universe filter NIFTY_500]
    RANK[Ranking breakout_v1 + momentum_v1]
    VAL[Validation IC deciles regime]
    TRACE[Traceability Sprint 7]
    BATCH[Daily batch orchestrator]
  end

  subgraph research [Research layers read-only unless noted]
    REG[Regime policy replay 8.1]
    FIC[Factor IC analytics 8.2]
    EXIT[Exit research 8.3]
    RI[Research intelligence 8.5]
    OA[Outcome attribution]
    RR[Ranking research reports]
  end

  subgraph args [ARGS governance LLM]
    PKT[Investment review packets]
    SEE[SEE v2 setup evidence]
    SQE[SQE stock_quality_evidence]
    COM[5 committees + CRO]
  end

  ING --> UNI --> RANK --> VAL --> TRACE
  BATCH --> ING & RANK & VAL & FIC & EXIT
  RANK --> PKT
  VAL --> PKT
  SEE --> PKT
  SQE --> PKT
  PKT --> COM
  RANK --> OA & RR
```

### What's production vs experimental

| Area | Status | Notes |
|------|--------|-------|
| Daily NIFTY 500 batch | **Production** | `POST /ops/daily-batch`, `scripts/run_daily_nifty500_batch.py` |
| Rankings `breakout_v1` / `momentum_v1` | **Production** | Deterministic; do not change without scoped approval |
| Validation (forward returns, IC, regime) | **Production** | Latest days `insufficient_data` until forward tail ingested |
| Traceability (Sprint 7) | **Production** | Instrumentation only |
| Regime policy / backtest (8.1) | **Research** | Not wired to live trading |
| Factor IC / exit / research intel (8.2–8.5) | **Production APIs** | Read-only analytics over precomputed tables |
| ARGS Phase 1 + committee Phase 2 | **Production** | `/api/v1/research/*`, `scripts/run_args_top20.py` |
| SEE v2 | **Production** | Strategy-aware analog search; migration `20260609_0018` |
| SQE on packets | **Production (observability)** | Enriches packets; does not change committee defaults |
| QRC `quant_research_brief` + `pending_neutral` | **Production** | Deterministic QRC confidence path |
| `ARGS_QRC_USE_SQE` / `qrc_sqe_brief` | **Experimental** | Default **false**; A/B only |
| Outcome attribution | **Production analytics** | Read-only; `app/outcome_attribution/` |
| Ranking calibration research | **Research only** | Non-monotonic ranks; no ranking v2 in prod |
| Committee Phase 3 | **Not started** | Design TBD after Phase 2 results |
| Recommendation engine (Phase 2) | **Production** | `app/recommendation/`, `/api/v1/recommendations/*` (9 routes) |
| Portfolio engine | **Production (partial)** | `app/services/portfolio_service.py`, 22 `/portfolio/*` routes; NAV/cash/recon not multi-tenant |
| Paper execution | **Production** | `ExecutionService` + `PaperExecutionAdapter`; live Zerodha **stub** |
| Pilot command center | **Production** | `/api/v1/pilot/*` (10 read-only routes) |
| JWT auth + multi-tenant | **Production (partial)** | migration `20260610_0025`; analytics routes global |
| Frontend (web + mobile) | **Partial** | `frontend/` — 8 screens live; missing Exit Queue + Analytics |
| Risk controls (AC-RISK) | **Not started** | No pre-trade gates |

**Audit package:** [`docs/audit/Executive_Summary.md`](./audit/Executive_Summary.md) (AUDIT-01, 2026-06-05).

---

## 3. Repo layout

```
pi-pm/
├── app/
│   ├── api/v1/              # HTTP routes (~130 endpoints; see audit/API_AUDIT_REPORT.md)
│   ├── args/                # ARGS committees, graph, LLM plugins, packet views
│   ├── auth/                # JWT helpers, RBAC constants
│   ├── copilot/             # Intent, retriever, citations (explain-only)
│   ├── execution/           # ExecutionService, paper + Zerodha adapters, state machine
│   ├── ops/daily_batch/     # Planner, paper_pilot_ops, traceability
│   ├── ops/pilot/           # Alerting, reporting serializers
│   ├── portfolio/           # Exit monitor, reconciliation, analytics
│   ├── recommendation/      # Engine + conviction scorer (conv_v1.1.0)
│   ├── core/config.py       # Settings + env vars (incl. ARGS_QRC_USE_SQE, JWT)
│   ├── outcome_attribution/ # Rank → forward return attribution (read-only)
│   ├── ranking/             # Deterministic ranking engine (frozen)
│   ├── ranking_research/    # Rank reliability, score compression reports
│   ├── stock_setup_evidence/ # SEE v2 engine
│   ├── validation/          # Forward-return validation (frozen)
│   └── services/            # Orchestration (daily batch, portfolio, auth, pilot, …)
├── frontend/                # RN + RN Web monorepo (apps/web, apps/mobile, packages/*)
├── docs/                    # All operational + research markdown
│   ├── audit/               # AUDIT-01 implementation verification (2026-06-05)
│   └── dailyruns/           # Dated operational run logs (see §10)
├── migrations/versions/     # Alembic (head: 20260610_0026)
├── scripts/                 # CLI wrappers (batch, ARGS, report generators)
└── tests/                   # 574 tests
```

**Data model pointers:** [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md) · [`architecture.md`](./architecture.md) / [`ARCHITECTURE.md`](./ARCHITECTURE.md) · [`API_REFERENCE.md`](./API_REFERENCE.md)

---

## 4. Environment & Docker

### 4.1 Setup

```bash
cd /Users/kalyancb/pi-pm
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # edit DATABASE_URL if needed

docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
alembic upgrade head   # → 20260610_0026
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4.2 Key environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+psycopg://pipm:pipm@localhost:5432/pipm` | PostgreSQL connection |
| `RANKING_DEFAULT_UNIVERSE_CODE` | `PI_PM_CORE` | **Use `NIFTY_500` in ops** |
| `RANKING_DEFAULT_BENCHMARK` | `^NSEI` | Must be ingested through target day |
| `RANKING_DEFAULT_STRATEGY` | `momentum_v1` | API default; batch runs both strategies |
| `VALIDATION_HIGH_VOL_THRESHOLD` | `0.20` | Regime vol split |
| `ARGS_LLM_PROVIDER` | `mock` | `mock` \| `openai` \| `openai_compatible` |
| `ARGS_LLM_DEFAULT_MODEL` | `gpt-4o-mini` | Global LLM default |
| `ARGS_LLM_*_PROVIDER/MODEL/API_KEY` | empty | Per-agent overrides (TARC, QRC, CRO, …) |
| `ARGS_LLM_TIMEOUT_SECONDS` | `60` | Increase for slow CRO (180–300 on reruns) |
| **`ARGS_QRC_USE_SQE`** | **`false`** | Experimental QRC SQE brief path |

Full settings: `app/core/config.py` · example: `.env.example`

### 4.3 Docker notes

- Rebuild API after code changes: `docker compose -f docker/docker-compose.yml build api`
- DB health: `GET /api/v1/health` → `"database":"connected"`
- Scripts use `get_session_factory()()` — not `SessionLocal`

---

## 5. Implementation reference — modules

| Module | Path | Purpose | Status |
|--------|------|---------|--------|
| Daily batch planner | `app/ops/daily_batch/batch_planner.py` | Gap detection, `already_current` | Production |
| Daily batch service | `app/services/daily_batch_service.py` | Phase orchestration | Production |
| Ranking engine | `app/ranking/` | Factor strategies, normalize, score | Production (frozen) |
| Validation | `app/validation/` | Forward returns, IC, deciles | Production (frozen) |
| ARGS packet builder | `app/args/builders/investment_review_packet_builder.py` | Deterministic packet JSON | Production |
| Committee packet views | `app/args/committee_packet_views.py` | Phase 2 per-committee evidence slices | Production |
| Committee evidence enforcement | `app/args/committee_evidence_enforcement.py` | Allowlist + repair retry | Production |
| QRC plugin | `app/args/plugins/qrc.py` | Quant committee | Production |
| QRC SQE brief (flagged) | `app/args/plugins/qrc_sqe_brief.py` | Experimental LLM payload | Experimental |
| Quant research brief | `app/args/plugins/quant_research_brief.py` | Deterministic QRC confidence | Production |
| SQE enricher | `app/args/plugins/stock_quality_evidence.py` | A–F sections on packet | Production (observability) |
| SEE v2 | `app/stock_setup_evidence/` | Strategy-aware analog search | Production |
| Outcome attribution | `app/outcome_attribution/` | Rank bucket → forward alpha | Production analytics |
| Ranking research | `app/ranking_research/` | Non-monotonic rank analysis | Research |
| Committee effectiveness | `app/args/analytics/committee_effectiveness.py` | Independence metrics | Research tooling |
| Recommendation engine | `app/recommendation/engine.py`, `conviction_scorer.py` | BUY/WATCH/HOLD/EXIT rules | Production |
| Recommendation service | `app/services/recommendation_service.py` | Run, approve, reject | Production |
| Portfolio service | `app/services/portfolio_service.py` | Positions, cash, recompute | Production (partial tenant) |
| Paper pilot ops | `app/ops/daily_batch/paper_pilot_ops.py` | Auto-approve/execute flags | Production |
| Execution service | `app/execution/services/execution_service.py` | Unified paper + live stub | Production (paper) |
| Auth service | `app/services/auth_service.py` | JWT, refresh rotation, RBAC | Production |
| Pilot command center | `app/services/pilot_command_center_service.py` | Dashboards, alerts, KPIs | Production |
| Copilot service | `app/services/copilot_service.py` | Explain-only Q&A | Production |

---

## 6. Scripts index

| Script | Command | When to use |
|--------|---------|-------------|
| Daily batch | `python scripts/run_daily_nifty500_batch.py --assume-session-done` | Normal daily delta (ingest → rank → validate → IC → exit) |
| Daily batch dry-run | `python scripts/run_daily_nifty500_batch.py --dry-run` | Plan only; inspect `ranking_gaps` |
| Daily batch force day | `python scripts/run_daily_nifty500_batch.py --from-date 2026-06-04 --target-date 2026-06-04 --force-from-date --force-regenerate-rankings` | Reprocess a specific date |
| ARGS top-20 | `ARGS_QRC_USE_SQE=false python scripts/run_args_top20.py --as-of-date 2026-06-04` | Run committees for latest ranking runs |
| Export ARGS run | `python scripts/export_args_research_run.py <run_id> -o docs/dailyruns/.../args-breakout.md` | Markdown export for PO review |
| Outcome attribution | `python scripts/generate_outcome_attribution_report.py` | Regenerate [`outcome-attribution-report.md`](./outcome-attribution-report.md) |
| Ranking research (5 reports) | `python scripts/generate_ranking_root_cause_reports.py` | All rank/factor/regime/compression/root-cause docs |
| SEE v2 validation | `python scripts/generate_see_v2_validation_report.py` | Regenerate [`see-v2-validation-report.md`](./see-v2-validation-report.md) |
| Committee effectiveness | `python scripts/analyze_committee_effectiveness.py --as-of 2026-06-02 --strategy breakout_v1` | Independence metrics for a run |
| QRC SQE A/B | `python scripts/qrc_sqe_ab_experiment.py` | Experimental flag comparison |
| Re-ingest symbols | `python scripts/reingest_symbols_since.py --since 2026-06-01 --symbols-file symbols.txt` | Fix stale/error symbols; include `^NSEI` |
| Traceability backfill | `python scripts/backfill_sprint7_traceability.py --all` | Populate Sprint 7 tables |
| Factor IC backfill | `python scripts/backfill_sprint82_factor_analytics.py --universe-code NIFTY_500 --start-date 2024-01-01 --end-date 2025-05-30` | Historical factor analytics |
| Exit research backfill | `python scripts/backfill_sprint83_exit_research.py …` | Historical exit simulation |
| Research intelligence | `python scripts/generate_sprint85_research_intelligence.py …` | Executive report pack |
| Regime presets | `python scripts/init_regime_policy_presets.py` | Load E1–E4 policy configs |
| Tests | `pytest tests/ -q` | Full suite (574 tests) |
| ARGS unit tests | `pytest tests/unit/args tests/integration/args -q` | ARGS-only |

---

## 7. Phase 1 infra (daily batch + rankings + validation + ARGS)

### 7.1 Daily batch

- **API:** `POST /api/v1/ops/daily-batch/runs`
- **Phases (default):** ingest → rankings (both strategies) → validation → factor IC → exit research
- **Strategies:** `breakout_v1:1.0.0`, `momentum_v1:1.0.0` on `NIFTY_500`
- **Runbook:** [`daily-nifty500-batch-runbook.md`](./daily-nifty500-batch-runbook.md)

**Known operational issues:**

| Issue | Detail | Mitigation |
|-------|--------|------------|
| **Ranking gaps skip** | Rankings phase runs only when `any(ranking_gaps)`. Full batch exits early when `already_current=true` (no gaps, no ingest need). Dry-run may show gaps that a non-force run won't re-rank. | Use `force_from_date: true` + `force_regenerate_rankings: true` for explicit reprocess (see [`dailyruns/04-jun-2026/02-rankings.md`](./dailyruns/04-jun-2026/02-rankings.md)). |
| **`^NSEI` remediation** | Without benchmark bars through target day, trading-day resolver won't rank that date. | Always ingest `^NSEI` with universe; included in batch ingest when configured. |
| **Validation insufficient tail** | Dates from **~2026-05-27** onward show `insufficient_data` until ≥5 forward trading days exist. | Ingest later sessions; re-run validation phase. Expected for same-day as-of (see [`dailyruns/04-jun-2026/03-validation.md`](./dailyruns/04-jun-2026/03-validation.md)). |
| **Factor IC / exit `metrics_written: 0`** | Downstream phases need `validation status=completed`. | Wait for forward tail; or backfill older completed window. |

### 7.2 Rankings

- **breakout_v1:** 8 factors, 252-day history — alpha research strongest in `BULL_LOW_VOL` @ 20d
- **momentum_v1:** 4 factors, 201-day history
- Typical coverage: ~460–470 ranked / ~500 universe (exclusions for liquidity, history, errors)

### 7.3 Validation

- Horizons: 5 / 10 / 20 / 60 trading days
- Regime: `{BULL|BEAR}_{LOW_VOL|HIGH_VOL}` via MA200 + vol threshold
- **`pending_neutral`:** When current run is `insufficient_data`, QRC uses neutral informational score (0.50) and historical completed validations for context — see `app/args/plugins/quant_payload.py`

### 7.4 ARGS (Phase 1)

- **API:** `/api/v1/research/*` (6 endpoints)
- **Flow:** ranking run → packets → parallel committees (TARC, FRC, QRC, NRCC, RC) → CRO → governance reports
- **CLI:** `scripts/run_args_top20.py`
- **Docs:** [`args-implementation-plan.md`](./args-implementation-plan.md) · [`args-gap-analysis.md`](./args-gap-analysis.md) · [`aics-ai-investment-committee-architecture.md`](./aics-ai-investment-committee-architecture.md)

**Default LLM:** `mock` — set `ARGS_LLM_PROVIDER=openai` + API key for live committees.

---

## 8. SEE v2 — stock setup evidence

**Problem (v1):** Momentum SEE returned 0 qualifying matches because analog search used breakout factor space.

**Solution (v2):** Strategy-aware profiles in `app/stock_setup_evidence/strategy_profiles.py` — breakout (8 factors) vs momentum (4 factors).

| Migration | `20260609_0018` |
|-----------|-----------------|
| New columns | `strategy_name`, `engine_version`, `total_matches`, `qualifying_matches`, `setup_evidence_score` on `stock_setup_research` |
| Extended metrics | `standard_deviation_20d`, win rates on `stock_setup_research_metrics` |

**Docs:** [`see-v2-momentum-support.md`](./see-v2-momentum-support.md) · [`see-v2-validation-report.md`](./see-v2-validation-report.md)

**Verify:**

```bash
python scripts/generate_see_v2_validation_report.py
```

---

## 9. QRC & SQE

### 9.1 QRC (production path)

- **Confidence:** Deterministic from `build_quant_research_brief()` — not LLM output
- **Pending validation:** `current_run_validation: pending_neutral` when forward horizons unavailable; historical completed validations supply context
- **Root cause (fixed context):** Uniform quant evidence across top-20 caused 0.56 collapse — see [`qrc-root-cause-analysis.md`](./qrc-root-cause-analysis.md), [`qrc-evidence-model-redesign.md`](./qrc-evidence-model-redesign.md)

### 9.2 SQE Phase 2 (packet observability)

- **`stock_quality_evidence`** attached to every packet (sections A–F)
- Does **not** change QRC/TARC/CRO prompts or weights by default
- **Doc:** [`sqe-phase2-implementation-report.md`](./sqe-phase2-implementation-report.md) · design: [`stock-quality-evidence-design.md`](./stock-quality-evidence-design.md)

### 9.3 Experimental: `ARGS_QRC_USE_SQE`

| Setting | Behavior |
|---------|----------|
| `ARGS_QRC_USE_SQE=false` (default) | Legacy `quant_research_brief` only |
| `ARGS_QRC_USE_SQE=true` + packet has SQE | Adds `qrc_sqe_brief`, SQE prompt, `qrc_evidence_mode: sqe_experiment` |

**Docs:** [`qrc-sqe-ab-test-report.md`](./qrc-sqe-ab-test-report.md) · [`qrc-sqe-live-openai-evaluation.md`](./qrc-sqe-live-openai-evaluation.md) · [`qrc-information-compression-analysis.md`](./qrc-information-compression-analysis.md)

---

## 10. Committee Phase 2

**Shipped:** Independence validators, per-committee packet views, `contrarian_view`, degraded-clone elimination.

| Component | Path |
|-----------|------|
| Packet views | `app/args/committee_packet_views.py` |
| Evidence enforcement | `app/args/committee_evidence_enforcement.py` |
| Contrarian view | Stored in `committee_reviews.extensions.contrarian_view` |

**Results (2026-06-02 re-run):**

| Metric | Phase 1 | Phase 2 | Target |
|--------|---------|---------|--------|
| Effective independence | **~14%** | **~79%** | ≥40% |
| Evidence overlap | ~60% | ~0% | <30% |
| Strict independence packet rate | 0% | 100% | >20% |

**Docs:** [`committee-effectiveness-report.md`](./committee-effectiveness-report.md) (Phase 1 diagnosis) · [`committee-independence-phase2-results.md`](./committee-independence-phase2-results.md) · [`committee-independence-design.md`](./committee-independence-design.md)

**Remaining gaps:** QRC evidence-validation failures on some symbols (bad `historical_validation_context` refs before resolver fix); RC abstention when scope validation fails.

---

## 11. Outcome attribution

**Question:** Does higher rank → better forward outcomes?

**Verdict (`partial`):** Top buckets beat benchmark on average, but rank gradient is **not monotonic** — selective alpha, not uniform ordering.

| Module | `app/outcome_attribution/` |
|--------|---------------------------|
| Report | [`outcome-attribution-report.md`](./outcome-attribution-report.md) |
| Regenerate | `python scripts/generate_outcome_attribution_report.py` |

Window in latest report: 2024-06-01 → 2026-06-03 · 988 ranking runs · strategies: breakout_v1, momentum_v1.

---

## 12. Ranking research (non-monotonic ranks)

**Finding:** Inverted Spearman(rank, α) at 20d — ranks 6–10 and 11–20 often beat ranks 1–5. Root causes: score compression, anticorrelated factors.

| Report | Path |
|--------|------|
| Root cause summary | [`ranking-calibration-root-cause.md`](./ranking-calibration-root-cause.md) |
| Rank reliability | [`rank-reliability-report.md`](./rank-reliability-report.md) |
| Factor reliability | [`factor-reliability-report.md`](./factor-reliability-report.md) |
| Regime rank reliability | [`regime-rank-reliability-report.md`](./regime-rank-reliability-report.md) |
| Score compression | [`score-compression-analysis.md`](./score-compression-analysis.md) |

**Regenerate all five:**

```bash
python scripts/generate_ranking_root_cause_reports.py \
  --start-date 2024-06-01 \
  --end-date 2026-06-04
```

**Research-only proposed fixes:** isotonic rank calibration, top-quintile score shrink — see root-cause doc. **Not in production ranking engine.**

---

## 13. Daily runs pattern

Operational runs are logged under **`docs/dailyruns/<DD-mon-YYYY>/`**:

| File | Content |
|------|---------|
| `00-prerequisites.md` | Docker, API health, DB |
| `01-ingestion.md` | Batch ingest stats, `^NSEI` check |
| `02-rankings.md` | Run IDs, ranking_gaps, phase results |
| `03-validation.md` | Per-run validation status |
| `04-factor-ic.md` | Factor IC phase |
| `05-exit-research.md` | Exit research phase |
| `06-regime.md` | Regime observability |
| `07-research-intelligence.md` | Sprint 8.5 (if run) |
| `08-args.md` | ARGS commands, research run IDs |
| `args-breakout.md` / `args-momentum.md` | Full packet exports |
| `09-best-bets.md` | PO-facing top picks + caveats |

**Latest example:** [`dailyruns/04-jun-2026/`](./dailyruns/04-jun-2026/) — as-of 2026-06-04, regime BEAR_LOW_VOL.

---

## 14. PO section

### 14.1 Decisions needed

| Decision | Options | Current state | Docs |
|----------|---------|---------------|------|
| **SQE default for QRC?** | Keep legacy brief vs enable `ARGS_QRC_USE_SQE=true` | Default **false**; SQE on packets for observability only | [`qrc-sqe-ab-test-report.md`](./qrc-sqe-ab-test-report.md) |
| **Ranking v2 calibration?** | Ship isotonic/shrink in engine vs continue research | Research only; prod ranking unchanged | [`ranking-calibration-root-cause.md`](./ranking-calibration-root-cause.md) |
| **Committee Phase 3?** | Prompt tuning, QRC ref resolver hardening, CRO timeout UX | Phase 2 shipped (~79% independence) | [`committee-independence-phase2-results.md`](./committee-independence-phase2-results.md) |
| **Daily batch auto-ARGS?** | Wire ARGS post-rank in batch vs on-demand | On-demand only | [`args-implementation-plan.md`](./args-implementation-plan.md) §2 |

### 14.2 Validated facts (with doc links)

| Fact | Evidence |
|------|----------|
| `breakout_v1` alpha mainly in `BULL_LOW_VOL` @ 20d | [`HANDOFF.md`](./HANDOFF.md) §5 · [`regime-rank-reliability-report.md`](./regime-rank-reliability-report.md) |
| Rank ordering within top-20 is non-monotonic | [`outcome-attribution-report.md`](./outcome-attribution-report.md) · [`ranking-calibration-root-cause.md`](./ranking-calibration-root-cause.md) |
| Phase 1 committee effective independence ~14% | [`committee-effectiveness-report.md`](./committee-effectiveness-report.md) |
| Phase 2 independence ~79% (target ≥40%) | [`committee-independence-phase2-results.md`](./committee-independence-phase2-results.md) |
| QRC 0.56 collapse was data-shape not prompt | [`qrc-root-cause-analysis.md`](./qrc-root-cause-analysis.md) |
| SEE v2 fixes momentum zero-match bug | [`see-v2-momentum-support.md`](./see-v2-momentum-support.md) · [`see-v2-validation-report.md`](./see-v2-validation-report.md) |
| Latest-day validation `insufficient_data` is expected | [`daily-nifty500-batch-runbook.md`](./daily-nifty500-batch-runbook.md) · [`dailyruns/04-jun-2026/03-validation.md`](./dailyruns/04-jun-2026/03-validation.md) |
| ARGS does not emit trade actions | [`args-gap-analysis.md`](./args-gap-analysis.md) · ADR-001 in [`DECISION_LOG.md`](./DECISION_LOG.md) |

---

## 15. AI engineer quickstart

### 15.1 First hour checklist

```bash
git checkout feature/see-v2 && git pull
alembic upgrade head                    # → 20260610_0026
pytest tests/ -q                        # expect 574 passed
curl http://127.0.0.1:8000/api/v1/health
```

### 15.2 Run daily pipeline for a date

```bash
# Plan
python scripts/run_daily_nifty500_batch.py --dry-run --target-date 2026-06-04

# Execute (force if reprocessing)
python scripts/run_daily_nifty500_batch.py \
  --target-date 2026-06-04 \
  --from-date 2026-06-04 \
  --force-from-date \
  --force-regenerate-rankings
```

Log steps under `docs/dailyruns/<date-folder>/` following the Jun-4 template.

### 15.3 Run ARGS

```bash
# Production path (legacy QRC brief)
ARGS_QRC_USE_SQE=false \
ARGS_LLM_PROVIDER=openai \
ARGS_LLM_OPENAI_API_KEY=sk-... \
ARGS_LLM_CRO_TIMEOUT_SECONDS=300 \
python scripts/run_args_top20.py --as-of-date 2026-06-04

# Export
python scripts/export_args_research_run.py <research_run_id> \
  -o docs/dailyruns/04-jun-2026/args-breakout.md
```

### 15.4 Regenerate research reports

```bash
python scripts/generate_ranking_root_cause_reports.py
python scripts/generate_outcome_attribution_report.py
python scripts/generate_see_v2_validation_report.py
python scripts/analyze_committee_effectiveness.py --as-of 2026-06-02 --strategy breakout_v1
```

### 15.5 Test commands

```bash
pytest tests/ -q                                    # full suite
pytest tests/unit/args tests/integration/args -q  # ARGS
pytest tests/unit/ops/ -q                         # daily batch planner
pytest tests/unit/ranking_research/ -q            # ranking research
```

### 15.6 Feature flags

| Flag | Location | Default |
|------|----------|---------|
| `ARGS_QRC_USE_SQE` | `app/core/config.py` | `false` |
| `ARGS_LLM_*` per agent | env / config | empty → global default |
| `require_completed_validation` | ARGS API / `--require-completed-validation` | API default `true`; CLI default `false` |
| Daily batch `force_*` | request body / CLI | all `false` except `assume_session_done` |

### 15.7 Do not

1. Change ranking/validation formulas without explicit scope
2. Enable `ARGS_QRC_USE_SQE` globally without PO sign-off
3. Treat ARGS committee rank as factor rank (they diverge — see best-bets caveats)
4. Expect same-day validation `completed` without forward bars
5. Use `SessionLocal` in scripts
6. Pool 100k+ rows through `compute_full_horizon_metrics` (O(n²))

---

## 16. Known limitations (summary)

1. **Validation tail pending** from ~2026-05-27 — forward horizons block `completed` status
2. **Rank non-monotonic** within top-20 — documented; no prod fix yet
3. **QRC evidence validation** occasional failures on historical refs (Phase 2 residual)
4. **CRO timeout** at 60s default on large runs — increase env timeout
5. **Packet size** grows ~2× with SQE object (observability cost)
6. **Mock LLM default** — production demos need OpenAI keys
7. **No daily batch → ARGS hook** — manual or scripted post-step
8. **Paper trading / portfolio** — not implemented

---

## 17. Recommended next steps

| Priority | Action | Owner |
|----------|--------|-------|
| P0 | Ingest forward sessions; re-validate tail from 2026-05-27 | Ops |
| P0 | PO decision: `ARGS_QRC_USE_SQE` promotion criteria | PO |
| P1 | Walk-forward OOS test for ranking v2 calibration (research) | Research |
| P1 | Committee Phase 3: QRC ref resolver + CRO reliability | Engineering |
| P2 | Wire optional ARGS step into daily batch (Phase 2 ARGS plan) | Engineering |
| P2 | Fill [`sprint81-results-template.md`](./sprint81-results-template.md) if regime backtest rerun | Research |
| P3 | Portfolio / paper trading (ROADMAP) | Future sprint |

---

## 18. Documentation index

Full index with one-line descriptions: [`docs/README.md`](./README.md)

**Historical / sprint docs preserved** — not deleted. ARGS/QRC/SQE evolution tracked across multiple dated reports; use README to navigate.

---

## 19. Takeover checklist

- [ ] On branch `feature/see-v2`, migration `20260610_0026`
- [ ] `pytest` → 574 passed
- [ ] Docker + API health OK
- [ ] Read this doc + [`daily-nifty500-batch-runbook.md`](./daily-nifty500-batch-runbook.md)
- [ ] Review latest daily run: [`dailyruns/04-jun-2026/`](./dailyruns/04-jun-2026/)
- [ ] PO decisions in §14.1 acknowledged
- [ ] Before ranking changes: read [`ranking-calibration-root-cause.md`](./ranking-calibration-root-cause.md)
- [ ] Before ARGS changes: read [`args-gap-analysis.md`](./args-gap-analysis.md) + run ARGS tests
