#!/usr/bin/env python3
"""Pi-PM Batch Scheduler — IST-aware, no external dependencies.

Schedules three daily batch jobs (ADR-034, ADR-035, ADR-036):

  Batch 1 — EOD Pipeline         : 15:45 IST (Mon–Fri)
  Batch 2 — Intraday Exit Monitor : every hour 09:15–15:15 IST (Mon–Fri)
  Batch 3 — Paper Trade Entry     : 09:15 IST (Mon–Fri)

Run order on a trading day:
  09:15 → Batch 2 scan #1 (exits on existing positions)
  09:15 → Batch 3 entries (N-1 signal → N execution)
  10:15 → Batch 2 scan #2
  ...   → Batch 2 (hourly)
  15:15 → Batch 2 scan #7 (final intraday)
  15:45 → Batch 1 (ingest → rank → validate → recommend → committee)

Usage:
    uv run python scripts/scheduler.py            # run scheduler (blocking)
    uv run python scripts/scheduler.py --dry-run  # log schedule without executing
    uv run python scripts/scheduler.py --once batch1   # run batch1 once now and exit
    uv run python scripts/scheduler.py --once batch2
    uv run python scripts/scheduler.py --once batch3
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, date, timezone, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCHEDULER] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scheduler")

# IST = UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable  # same interpreter that runs this scheduler

# ── Batch definitions ─────────────────────────────────────────────────────────

BATCH1_SCRIPT = os.path.join(SCRIPTS_DIR, "batch1_eod_pipeline.py")
BATCH2_SCRIPT = os.path.join(SCRIPTS_DIR, "batch2_intraday_exit.py")
BATCH3_SCRIPT = os.path.join(SCRIPTS_DIR, "batch3_paper_trade_entry.py")

# Batch 2 runs at these IST hours (on the :15 of each hour)
BATCH2_HOURS_IST = [9, 10, 11, 12, 13, 14, 15]  # 09:15 → 15:15


def ist_now() -> datetime:
    return datetime.now(IST)


def is_weekday(dt: datetime) -> bool:
    return dt.weekday() < 5  # Mon=0 … Fri=4


def run_script(script: str, extra_args: list[str] | None = None, dry_run: bool = False) -> int:
    cmd = [PYTHON, script] + (extra_args or [])
    if dry_run:
        cmd.append("--dry-run")
    log.info("Executing: %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            log.error("Script exited with code %d: %s", result.returncode, script)
        return result.returncode
    except Exception as exc:
        log.error("Failed to launch %s: %s", script, exc)
        return 1


# ── Schedule state ────────────────────────────────────────────────────────────

class _JobTracker:
    """Track which jobs have fired today to avoid duplicate runs."""

    def __init__(self) -> None:
        self._fired: dict[str, date] = {}

    def should_fire(self, job_id: str, session_date: date) -> bool:
        return self._fired.get(job_id) != session_date

    def mark_fired(self, job_id: str, session_date: date) -> None:
        self._fired[job_id] = session_date

    def reset_if_new_day(self, session_date: date) -> None:
        # Remove stale entries from previous days
        stale = [k for k, v in self._fired.items() if v < session_date]
        for k in stale:
            del self._fired[k]


# ── Main loop ─────────────────────────────────────────────────────────────────

def scheduler_loop(dry_run: bool) -> None:
    tracker = _JobTracker()
    log.info("Scheduler started (IST-aware) | dry_run=%s", dry_run)
    log.info("Batch 3 + Batch 2/1st : 09:15 IST Mon–Fri")
    log.info("Batch 2 (hourly)      : 09:15–15:15 IST Mon–Fri")
    log.info("Batch 1               : 15:45 IST Mon–Fri")

    while True:
        now = ist_now()
        today = now.date()
        tracker.reset_if_new_day(today)

        if is_weekday(now):
            h, m = now.hour, now.minute

            # ── Batch 3: 09:15 IST ──────────────────────────────────────
            if h == 9 and 15 <= m < 25:
                job_id = f"batch3:{today}"
                if tracker.should_fire(job_id, today):
                    log.info("▶ Firing Batch 3 (paper trade entry) — %s IST", now.strftime("%H:%M"))
                    run_script(BATCH3_SCRIPT, dry_run=dry_run)
                    tracker.mark_fired(job_id, today)

            # ── Batch 2: every hour :15 from 09:15 to 15:15 ─────────────
            if h in BATCH2_HOURS_IST and 15 <= m < 25:
                job_id = f"batch2:{today}:{h}"
                if tracker.should_fire(job_id, today):
                    log.info("▶ Firing Batch 2 (exit monitor) scan #%d — %s IST",
                             BATCH2_HOURS_IST.index(h) + 1, now.strftime("%H:%M"))
                    run_script(BATCH2_SCRIPT, dry_run=dry_run)
                    tracker.mark_fired(job_id, today)

            # ── Batch 1: 15:45 IST ──────────────────────────────────────
            if h == 15 and 45 <= m < 55:
                job_id = f"batch1:{today}"
                if tracker.should_fire(job_id, today):
                    log.info("▶ Firing Batch 1 (EOD pipeline) — %s IST", now.strftime("%H:%M"))
                    run_script(BATCH1_SCRIPT, dry_run=dry_run)
                    tracker.mark_fired(job_id, today)

        # Sleep until the next minute boundary
        sleep_secs = 60 - now.second
        time.sleep(sleep_secs)


def run_once(batch: str, dry_run: bool) -> int:
    """Run a single batch immediately and exit."""
    mapping = {
        "batch1": BATCH1_SCRIPT,
        "batch2": BATCH2_SCRIPT,
        "batch3": BATCH3_SCRIPT,
    }
    script = mapping.get(batch)
    if not script:
        log.error("Unknown batch: %s. Choose batch1, batch2, or batch3.", batch)
        return 1
    log.info("Running %s once (dry_run=%s) ...", batch, dry_run)
    return run_script(script, dry_run=dry_run)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="Pi-PM Batch Scheduler")
    p.add_argument("--dry-run", action="store_true",
                   help="Pass --dry-run to all batch scripts (no DB writes)")
    p.add_argument("--once", metavar="BATCH",
                   choices=["batch1", "batch2", "batch3"],
                   help="Run a specific batch once and exit")
    args = p.parse_args()

    if args.once:
        return run_once(args.once, args.dry_run)

    try:
        scheduler_loop(args.dry_run)
    except KeyboardInterrupt:
        log.info("Scheduler stopped by user")
    return 0


if __name__ == "__main__":
    sys.exit(main())
