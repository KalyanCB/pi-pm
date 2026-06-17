#!/usr/bin/env python3
"""Batch 1 — End-of-Day Ingestion & Signal Generation Pipeline (ADR-034).

Sequence:
  1. Ingest OHLCV for target_date
  2. Ranking (reversal_v1 + all strategies)
  3. Validation backfill (rolling window IC correction)
  4. Recommendations (RCEE → BUY/WATCH/REJECT per stock)
  5. AI Committee (research packets + advisory for reversal_v1 BUYs)

Trigger: 15:45 IST on NSE trading days (via scheduler.py or cron).
Safe to re-run — idempotent at every phase.

Usage:
    uv run python scripts/batch1_eod_pipeline.py
    uv run python scripts/batch1_eod_pipeline.py --target-date 2026-06-08
    uv run python scripts/batch1_eod_pipeline.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import date, timedelta

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BATCH1] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("batch1")

BASE_URL = "http://127.0.0.1:8000"
PRIMARY_STRATEGY = "reversal_v1"
COMMITTEE_TOP_N = 20
TIMEOUT = 7200.0  # 2 hours max for full pipeline


# ── Helpers ──────────────────────────────────────────────────────────────────

def last_trading_day(client: httpx.Client) -> date:
    """Return last date with completed recommendation runs — calendar-safe."""
    resp = client.get("/api/v1/recommendations/dates", params={"strategy_name": PRIMARY_STRATEGY})
    resp.raise_for_status()
    dates = resp.json().get("dates", [])
    if dates:
        return date.fromisoformat(dates[0])
    return date.today() - timedelta(days=1)


def already_completed(client: httpx.Client, target: date) -> bool:
    """Return True if a completed batch run already exists for target_date."""
    resp = client.get("/api/v1/ops/daily-batch/runs")
    if resp.status_code != 200:
        return False
    runs = resp.json() if isinstance(resp.json(), list) else resp.json().get("runs", [])
    for run in runs:
        if run.get("target_date") == target.isoformat() and run.get("status") == "COMPLETED":
            log.info("Batch run already completed for %s — skipping ingest/ranking phases", target)
            return True
    return False


def get_ranking_run_id(client: httpx.Client, target: date) -> str | None:
    """Return the ranking_run_id for target_date + primary strategy."""
    resp = client.get(
        "/api/v1/recommendations/latest",
        params={"as_of_date": target.isoformat(), "strategy_name": PRIMARY_STRATEGY},
    )
    if resp.status_code == 200:
        return resp.json().get("ranking_run_id")
    return None


# ── Phases ───────────────────────────────────────────────────────────────────

def phase_daily_batch(client: httpx.Client, target: date, dry_run: bool) -> dict:
    log.info("Phase 1-4: daily batch → ingest / ranking / validation / recommendations (%s)", target)
    if dry_run:
        log.info("  [dry-run] skipping daily batch POST")
        return {"status": "dry_run", "dry_run": True}

    payload = {
        "target_date": target.isoformat(),
        "assume_session_done": True,
        "phases": {"recommendations": True},
    }
    resp = client.post("/api/v1/ops/daily-batch/runs", json=payload)
    resp.raise_for_status()
    result = resp.json()
    run_id = result.get("run_id") or result.get("id")
    status = result.get("status", "unknown")
    log.info("Batch run %s — status: %s", run_id, status)

    # Poll until completed if async
    if status not in ("COMPLETED", "completed") and run_id:
        log.info("Polling batch run %s ...", run_id)
        for _ in range(120):  # up to 20 min (10s intervals)
            time.sleep(10)
            poll = client.get(f"/api/v1/ops/daily-batch/runs/{run_id}")
            if poll.status_code == 200:
                status = poll.json().get("status", "")
                log.info("  status: %s", status)
                if status in ("COMPLETED", "completed", "FAILED", "failed"):
                    result = poll.json()
                    break

    if status in ("FAILED", "failed"):
        raise RuntimeError(f"Daily batch failed: {result}")
    return result


def phase_exit_monitor(client: httpx.Client, target: date, dry_run: bool) -> dict:
    """Phase 6: T2 EOD exit monitor — generates PENDING exit recommendations for Batch 3."""
    log.info("Phase 6: T2 exit monitor → PENDING exit recs for %s", target)
    if dry_run:
        log.info("  [dry-run] skipping exit monitor POST")
        return {"dry_run": True}

    resp = client.post(
        "/api/v1/portfolio/exits/run",
        params={"as_of_date": target.isoformat()},
    )
    if resp.status_code == 404:
        # Fallback: trigger via daily-batch with portfolio phase only
        log.info("  exits/run not found, triggering via daily-batch portfolio phase")
        payload = {
            "target_date": target.isoformat(),
            "assume_session_done": True,
            "phases": {"portfolio": True, "recommendations": False},
            "portfolio_phases": {
                "exit_monitor": True,
                "paper_trading": False,
                "nav_snapshot": False,
                "reconcile": False,
                "recompute": False,
            },
        }
        resp = client.post("/api/v1/ops/daily-batch/runs", json=payload)

    if resp.status_code not in (200, 201):
        log.warning("Exit monitor call returned %d — %s", resp.status_code, resp.text[:200])
        return {"error": resp.status_code}

    result = resp.json()
    candidates = result.get("generated") or result.get("candidates") or len(result.get("exit_recommendation_ids", []))
    log.info("  Exit monitor generated %s PENDING recommendations", candidates)
    return result


def phase_committee(client: httpx.Client, target: date, ranking_run_id: str, dry_run: bool) -> dict:
    log.info("Phase 5: AI committee review for %s (strategy=%s)", target, PRIMARY_STRATEGY)
    if dry_run:
        log.info("  [dry-run] skipping committee POST")
        return {"dry_run": True}

    payload = {
        "ranking_run_id": ranking_run_id,
        "strategy_name": PRIMARY_STRATEGY,
        "top_n": COMMITTEE_TOP_N,
        "trigger_mode": "on_demand",
        "require_completed_validation": False,
    }
    resp = client.post("/api/v1/investment-committee/review", json=payload)
    resp.raise_for_status()
    result = resp.json()
    run_id = result.get("run_id") or result.get("id")
    packets = len(result.get("packets", []))
    status = result.get("status", "?")
    log.info("Committee run %s — status: %s | packets: %d", run_id, status, packets)

    buys = sum(
        1 for p in result.get("packets", [])
        if (p.get("payload") or {}).get("recommendation", {}).get("action") == "BUY"
    )
    log.info("  BUYs in committee packets: %d / %d", buys, packets)
    return result


# ── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Batch 1 — EOD Pipeline")
    p.add_argument("--base-url", default=BASE_URL)
    p.add_argument("--target-date", type=date.fromisoformat, default=None,
                   help="Override target date (default: today)")
    p.add_argument("--dry-run", action="store_true", help="Skip writes, log plan only")
    p.add_argument("--force", action="store_true", help="Re-run even if batch already completed")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    target = args.target_date or date.today()
    base = args.base_url.rstrip("/")

    log.info("=" * 60)
    log.info("BATCH 1 — EOD Pipeline | target=%s | dry_run=%s", target, args.dry_run)
    log.info("=" * 60)

    with httpx.Client(base_url=base, timeout=TIMEOUT) as client:
        # Guard: already done?
        if not args.force and already_completed(client, target):
            log.info("Nothing to do — batch already completed for %s", target)
            return 0

        # Phase 1-4: ingest → ranking → validation → recommendations
        try:
            batch_result = phase_daily_batch(client, target, args.dry_run)
        except Exception as exc:
            log.error("Daily batch FAILED: %s", exc)
            return 1

        # Phase 5: committee
        ranking_run_id = get_ranking_run_id(client, target)
        if not ranking_run_id:
            log.warning("No ranking_run_id found for %s / %s — skipping committee", target, PRIMARY_STRATEGY)
            return 0

        try:
            committee_result = phase_committee(client, target, ranking_run_id, args.dry_run)
        except Exception as exc:
            log.error("Committee FAILED: %s", exc)
            return 1

        # Phase 6: T2 EOD exit monitor (generates PENDING exit recs for Batch 3)
        try:
            exit_result = phase_exit_monitor(client, target, args.dry_run)
        except Exception as exc:
            log.warning("Exit monitor FAILED (non-fatal): %s", exc)
            exit_result = {"error": str(exc)}

        log.info("=" * 60)
        log.info("BATCH 1 COMPLETE | target=%s", target)
        log.info("  Batch status : %s", batch_result.get("status", "?"))
        log.info("  Committee    : %s", committee_result.get("status", "done"))
        log.info("  Exit monitor : %s", exit_result)
        log.info("  Ready for Batch 3 on next trading day")
        log.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
