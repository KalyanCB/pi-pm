#!/usr/bin/env python3
"""Batch 2 — Intraday Exit Monitor (ADR-035).

Runs every hour during NSE market hours (09:15–15:15 IST).

T1 (IntradayExitMonitorService) — price triggers:
  - EXIT_STOP_LOSS      : unrealized_pct <= advisory_stop_pct (default -1%)
  - EXIT_TRAILING_STOP  : price dropped >5% from peak

T2 (ExitMonitorService) — swing triggers:
  - EXIT_RANK_DROP      : current rank > 40
  - EXIT_TIME           : trading days held > 30
  - EXIT_ALPHA_DECAY    : significant unrealized loss
  - EXIT_REGIME         : regime shift against strategy

Creates portfolio_exit_recommendations (status=PENDING) for each new trigger.
No auto-execution in paper mode — HITL confirmation required (ADR-030).
Dedup: one PENDING row per trigger per position per session.

Usage:
    uv run python scripts/batch2_intraday_exit.py
    uv run python scripts/batch2_intraday_exit.py --dry-run
    uv run python scripts/batch2_intraday_exit.py --date 2026-06-08
"""

from __future__ import annotations

import argparse
import logging
import sys
import os
from datetime import date, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BATCH2] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("batch2")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_engine
from app.models.market_data import MarketData
from app.models.portfolio_position import PortfolioPosition
from app.portfolio.exit_monitor.intraday_service import IntradayExitMonitorService
from app.portfolio.exit_monitor.service import ExitMonitorService
from app.portfolio.exit_monitor.quote_provider import LastCloseQuoteProvider


def get_db() -> Session:
    engine = get_engine()
    return sessionmaker(bind=engine)()


def is_trading_day(db: Session, today: date) -> bool:
    """True if we have market data for today or yesterday (NSE traded recently)."""
    latest = db.scalar(select(func.max(MarketData.date)))
    return latest is not None and latest >= today - timedelta(days=1)


def count_open_positions(db: Session) -> int:
    return db.scalar(
        select(func.count()).select_from(PortfolioPosition).where(
            PortfolioPosition.position_status == "OPEN",
            PortfolioPosition.is_current.is_(True),
        )
    ) or 0


def main() -> int:
    p = argparse.ArgumentParser(description="Batch 2 — Intraday Exit Monitor")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--date", type=date.fromisoformat, default=None)
    args = p.parse_args()
    today = args.date or date.today()

    log.info("=" * 60)
    log.info("BATCH 2 — Intraday Exit Monitor | session=%s | dry_run=%s", today, args.dry_run)
    log.info("=" * 60)

    db = get_db()
    try:
        # Guard: non-trading day
        if not is_trading_day(db, today):
            log.info("Not a trading day (no market data near %s) — skipping", today)
            return 0

        # Guard: no open positions
        n_open = count_open_positions(db)
        if n_open == 0:
            log.info("No open positions — nothing to evaluate")
            return 0
        log.info("Open positions to evaluate: %d", n_open)

        if args.dry_run:
            log.info("[dry-run] would run T1 + T2 exit monitors — skipping writes")
            return 0

        # ── T1: price-based stop triggers ─────────────────────────────────
        log.info("Running T1 intraday price monitor ...")
        quote_provider = LastCloseQuoteProvider(db)
        t1 = IntradayExitMonitorService(db, quote_provider=quote_provider)
        t1_result = t1.run(session_date=today)
        log.info(
            "T1 result: %d new signals | %d severity upgrades | %d auto-executed",
            t1_result.new_recommendations,
            t1_result.severity_upgrades,
            t1_result.auto_executed,
        )

        # ── T2: swing triggers (rank-drop, time-stop, alpha-decay, regime) ─
        log.info("Running T2 swing exit monitor ...")
        t2 = ExitMonitorService(db)
        t2_recs = t2.run(as_of_date=today)
        log.info("T2 result: %d exit signals created", len(t2_recs))
        for rec in t2_recs:
            log.info("  → %s triggers=%s urgency=%s", rec.portfolio_position_id, rec.triggers, rec.urgency)

        # Persist exit signals. The T1/T2 services flush but leave the commit to
        # the caller; without this the recommendations are rolled back on close.
        db.commit()

        total = t1_result.new_recommendations + len(t2_recs)
        log.info("=" * 60)
        log.info("BATCH 2 COMPLETE | positions=%d | signals=%d (T1=%d T2=%d)",
                 n_open, total, t1_result.new_recommendations, len(t2_recs))
        log.info("  Exit signals visible in UI → Recommendations → EXIT tab")
        log.info("=" * 60)

    except Exception as exc:
        log.error("BATCH 2 ERROR: %s", exc, exc_info=True)
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
