#!/usr/bin/env python3
"""Generate paper trading pilot reports (markdown).

Usage:
  python scripts/generate_pilot_reports.py daily [--as-of-date YYYY-MM-DD]
  python scripts/generate_pilot_reports.py weekly
  python scripts/generate_pilot_reports.py monthly
  python scripts/generate_pilot_reports.py final [--pilot-start YYYY-MM-DD] [--pilot-end YYYY-MM-DD]
  python scripts/generate_pilot_reports.py all
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from app.db.session import SessionLocal
from app.services.pilot_command_center_service import PilotCommandCenterService


def _render_report(report: dict) -> str:
    lines = [
        f"# Pilot {report['report_type'].title()} Report",
        "",
        f"**Period:** {report['period_start']} → {report['period_end']}",
        f"**Generated for:** {report['generated_for']}",
        "",
        "## Sections",
        "",
        "```json",
        json.dumps(report.get("sections", {}), indent=2, default=str),
        "```",
        "",
        "## Alerts",
        "",
    ]
    for alert in report.get("alerts", []):
        lines.append(f"- **{alert.get('severity', '').upper()}** `{alert.get('code')}`: {alert.get('message')}")
    if not report.get("alerts"):
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "report_type",
        choices=["daily", "weekly", "monthly", "final", "all"],
    )
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--pilot-start", type=date.fromisoformat, default=None)
    parser.add_argument("--pilot-end", type=date.fromisoformat, default=None)
    args = parser.parse_args()

    out_dir = Path("docs/paper-pilot/reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    types = (
        ["daily", "weekly", "monthly", "final"]
        if args.report_type == "all"
        else [args.report_type]
    )

    with SessionLocal() as db:
        svc = PilotCommandCenterService(db)
        for rtype in types:
            report = svc.get_report(
                rtype,
                as_of_date=args.as_of_date,
                pilot_start=args.pilot_start,
                pilot_end=args.pilot_end,
            )
            path = out_dir / f"{rtype.upper()}_REPORT_{args.as_of_date.isoformat()}.md"
            path.write_text(_render_report(report), encoding="utf-8")
            print(f"Wrote {path}")

        # Also refresh command center snapshot
        cc = svc.get_command_center(args.as_of_date)
        cc_path = out_dir / f"COMMAND_CENTER_{args.as_of_date.isoformat()}.json"
        cc_path.write_text(json.dumps(cc, indent=2, default=str), encoding="utf-8")
        print(f"Wrote {cc_path}")


if __name__ == "__main__":
    main()
