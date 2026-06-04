# SEE (Stock Setup Evidence) Design

**Status:** Production (SEE v2) · **Owner:** `app/stock_setup_evidence/`

---

## Purpose

Strategy-aware analog search and setup scoring for top-ranked names — enriches ARGS packets, does not alter rankings.

---

## SEE v2 highlights

- Separate factor profiles for `breakout_v1` vs `momentum_v1`
- Migration `20260609_0018` — metrics on research runs
- API: `POST /api/v1/research/stock-setup/runs/{ranking_run_id}/generate`

---

## Docs

| Doc | Link |
|-----|------|
| Momentum support | [see-v2-momentum-support.md](../../see-v2-momentum-support.md) |
| Validation report | [see-v2-validation-report.md](../../see-v2-validation-report.md) |
| Stock setup research migration | `20260608_0017` |

---

## Scripts

`scripts/generate_see_v2_validation_report.py`

Legacy design: [stock-quality-evidence-design.md](../../stock-quality-evidence-design.md) (SQE adjacent).
