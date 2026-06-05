#!/usr/bin/env python3
"""Generate paper-trading pilot dashboards (markdown).

Usage:
  python scripts/generate_paper_trading_dashboard.py [--as-of-date YYYY-MM-DD]

Outputs:
  docs/paper-pilot/dashboards/PILOT_DASHBOARD.md
  docs/paper-pilot/dashboards/HEALTH_DASHBOARD.md
  docs/paper-pilot/dashboards/RECONCILIATION_DASHBOARD.md
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from app.db.session import SessionLocal
from app.ops.daily_batch.paper_pilot_ops import PaperPilotOps
from app.portfolio.reconciliation.service import ReconciliationService
from app.services.portfolio_analytics_service import PortfolioAnalyticsService


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    as_of = args.as_of_date
    out_dir = Path("docs/paper-pilot/dashboards")

    with SessionLocal() as db:
        pilot = PaperPilotOps(db)
        health = pilot.health_snapshot(as_of)
        recon_svc = ReconciliationService(db)
        latest_recon = recon_svc.get_latest()
        healthy, reason = recon_svc.is_healthy()

        pilot_md = f"""# Paper Trading Pilot Dashboard

**As of:** {as_of.isoformat()}  
**Generated:** `scripts/generate_paper_trading_dashboard.py`

## Portfolio summary

```json
{json.dumps(health.get("summary", {}), indent=2, default=str)}
```

## Regime limits

| Field | Value |
|-------|-------|
| Can add position | {health["limits"]["can_add_position"]} |
| Slots available | {health["limits"]["slots_available"]} |
| Block reason | {health["limits"].get("block_reason") or "—"} |

## NAV

| Metric | Value |
|--------|-------|
| Total equity | {health["nav"].get("total_equity")} |
| Day return % | {health["nav"].get("day_return_pct")} |
| Alpha % | {health["nav"].get("alpha_pct")} |

## Ops status

| Check | Value |
|-------|-------|
| Reconciliation | {health.get("reconciliation_status") or "—"} |
| Pending exit recs | {health.get("pending_exit_recommendations", 0)} |
| Analytics gate | {"OPEN" if healthy else f"BLOCKED: {reason}"} |
"""
        _write(out_dir / "PILOT_DASHBOARD.md", pilot_md)

        health_md = f"""# Portfolio Health Dashboard

**Date:** {as_of.isoformat()}

## Gate status

- **Reconciliation healthy:** {healthy}
- **Reason:** {reason or "OK"}

## Limits

```json
{json.dumps(health.get("limits", {}), indent=2)}
```

## Pending exits

{health.get("pending_exit_recommendations", 0)} exit recommendation(s) awaiting human confirmation.
"""
        _write(out_dir / "HEALTH_DASHBOARD.md", health_md)

        if latest_recon:
            recon_md = f"""# Reconciliation Dashboard

**Latest report date:** {latest_recon.as_of_date.isoformat()}  
**Status:** {latest_recon.status}

| Field | Value |
|-------|-------|
| Cash (ledger) | ₹{float(latest_recon.cash_from_ledger):,.2f} |
| Market value | ₹{float(latest_recon.market_value_from_positions):,.2f} |
| Computed NAV | ₹{float(latest_recon.computed_nav):,.2f} |
| Reported NAV | ₹{float(latest_recon.reported_nav):,.2f} |
| Discrepancy | {float(latest_recon.discrepancy_pct):.4f}% |

## Checks

```json
{json.dumps(latest_recon.checks or {}, indent=2)}
```

## Warnings

{chr(10).join(f"- {w}" for w in (latest_recon.warnings or [])) or "None"}

## Failures

{chr(10).join(f"- {f}" for f in (latest_recon.failures or [])) or "None"}
"""
        else:
            recon_md = "# Reconciliation Dashboard\n\nNo reconciliation reports yet.\n"
        _write(out_dir / "RECONCILIATION_DASHBOARD.md", recon_md)

        try:
            analytics = PortfolioAnalyticsService(db)
            perf = analytics.get_performance()
            _write(
                out_dir / "PERFORMANCE_SNAPSHOT.json",
                json.dumps(perf, indent=2, default=str),
            )
        except Exception as exc:
            print(f"Performance snapshot skipped: {exc}")


if __name__ == "__main__":
    main()
