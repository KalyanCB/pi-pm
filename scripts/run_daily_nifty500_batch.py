#!/usr/bin/env python3
"""Thin HTTP client for the daily NIFTY 500 batch API."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
API_PATH = "/api/v1/ops/daily-batch/runs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run daily NIFTY 500 batch via API")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--target-date", type=date.fromisoformat, default=None)
    parser.add_argument("--from-date", type=date.fromisoformat, default=None)
    parser.add_argument("--force-from-date", action="store_true")
    parser.add_argument("--force-recompute", action="store_true")
    parser.add_argument("--force-regenerate-rankings", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--portfolio",
        action="store_true",
        help="Run the portfolio/paper-pilot phase (sets phases.portfolio=true). "
        "Paper auto-approve/execute are server-side when HITL off + paper on.",
    )
    parser.add_argument("--assume-session-done", action="store_true", default=True)
    parser.add_argument("--no-assume-session-done", action="store_false", dest="assume_session_done")
    parser.add_argument("--timeout", type=float, default=7200.0)
    parser.add_argument("--poll-run-id", default=None, help="Poll existing run instead of creating")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base = args.base_url.rstrip("/")

    with httpx.Client(base_url=base, timeout=args.timeout) as client:
        if args.poll_run_id:
            response = client.get(f"{API_PATH}/{args.poll_run_id}")
            response.raise_for_status()
            print(json.dumps(response.json(), indent=2, default=str))
            return 0

        payload: dict = {
            "target_date": args.target_date.isoformat() if args.target_date else None,
            "from_date": args.from_date.isoformat() if args.from_date else None,
            "force_from_date": args.force_from_date,
            "force_recompute": args.force_recompute,
            "force_regenerate_rankings": args.force_regenerate_rankings,
            "dry_run": args.dry_run,
            "assume_session_done": args.assume_session_done,
        }
        # Recommendations always run with rankings
        payload.setdefault("phases", {})
        payload["phases"]["recommendations"] = True
        # Portfolio/paper-pilot phase only when explicitly requested
        if args.portfolio:
            payload["phases"]["portfolio"] = True
        response = client.post(API_PATH, json=payload)
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
