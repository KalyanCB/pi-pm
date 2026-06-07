#!/usr/bin/env python3
"""Batch 3 — Morning Paper Trade Execution (ADR-036).

Runs once per trading day at 09:15 IST (market open).
Picks up last trading day's reversal_v1 BUY recommendations and executes
paper trades for each eligible CANDIDATE or APPROVED signal.

Signal selection (N-1 → N entry):
  - as_of_date = last completed recommendation run date  (N-1 signal)
  - entry date = today (N execution)
  - action     = BUY
  - lifecycle  = CANDIDATE or APPROVED  (REJECTED is the only hard block)

Eligibility guards:
  - Position already open for this stock  → skip
  - Portfolio full (MAX_SLOTS = 10)       → stop processing
  - No market data for today yet          → warn but proceed (uses last close)

Idempotent — re-running on same day produces no duplicate trades.

Usage:
    uv run python scripts/batch3_paper_trade_entry.py
    uv run python scripts/batch3_paper_trade_entry.py --dry-run
    uv run python scripts/batch3_paper_trade_entry.py --date 2026-06-09
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BATCH3] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("batch3")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_engine
from app.models.portfolio_position import PortfolioPosition
from app.models.recommendation import RecommendationResult, RecommendationRun
from app.models.paper_trade import PaperTrade
from app.services.paper_trade_service import PaperTradeService
from app.services.portfolio_service import PortfolioService

PRIMARY_STRATEGY = "reversal_v1"
MAX_SLOTS = 10
PORTFOLIO_ID = UUID("00000000-0000-4000-8000-000000000010")

# lifecycle states that are eligible for paper trade execution
ELIGIBLE_STATES = {"CANDIDATE", "APPROVED", "ACTIVE", None}
# REJECTED is the hard block — never trade a rejected recommendation


def get_db() -> Session:
    engine = get_engine()
    return sessionmaker(bind=engine)()


def last_trading_day(db: Session) -> date | None:
    """Return the most recent completed recommendation run date for primary strategy."""
    result = db.scalar(
        select(func.max(RecommendationRun.as_of_date)).where(
            RecommendationRun.strategy_name == PRIMARY_STRATEGY,
            RecommendationRun.status == "completed",
        )
    )
    return result


def get_buy_signals(db: Session, signal_date: date) -> list[RecommendationResult]:
    """Return ranked BUY results for signal_date, filtering out REJECTED."""
    # Deduplicate runs: pick the latest run for signal_date
    run = db.scalar(
        select(RecommendationRun).where(
            RecommendationRun.as_of_date == signal_date,
            RecommendationRun.strategy_name == PRIMARY_STRATEGY,
            RecommendationRun.status == "completed",
        ).order_by(RecommendationRun.created_at.desc())
    )
    if run is None:
        return []

    results = db.scalars(
        select(RecommendationResult).where(
            RecommendationResult.recommendation_run_id == run.id,
            RecommendationResult.action == "BUY",
        ).order_by(RecommendationResult.rank.asc())
    ).all()

    # Filter out REJECTED; keep CANDIDATE, APPROVED, ACTIVE, None
    eligible = [r for r in results if r.lifecycle_state not in ("REJECTED",)]
    rejected = len(results) - len(eligible)
    if rejected:
        log.info("  Filtered %d REJECTED signals — will not trade", rejected)
    return eligible


def already_has_position(db: Session, stock_id: UUID) -> bool:
    """True if an OPEN position exists for this stock."""
    return db.scalar(
        select(func.count()).select_from(PortfolioPosition).where(
            PortfolioPosition.stock_id == stock_id,
            PortfolioPosition.position_status == "OPEN",
            PortfolioPosition.is_current.is_(True),
        )
    ) > 0


def trade_already_executed(db: Session, rec_id: UUID) -> bool:
    """Idempotency: check if paper trade already exists for this recommendation."""
    idem_key = f"pilot-entry:{rec_id}"
    return db.scalar(
        select(func.count()).select_from(PaperTrade).where(
            PaperTrade.idempotency_key == idem_key,
        )
    ) > 0


def count_open_positions(db: Session) -> int:
    return db.scalar(
        select(func.count()).select_from(PortfolioPosition).where(
            PortfolioPosition.position_status == "OPEN",
            PortfolioPosition.is_current.is_(True),
        )
    ) or 0


def execute_entries(
    db: Session,
    signals: list[RecommendationResult],
    entry_date: date,
    dry_run: bool,
) -> dict:
    portfolio_svc = PortfolioService(db, portfolio_id=PORTFOLIO_ID)
    paper_svc = PaperTradeService(db, portfolio_service=portfolio_svc)

    open_count = count_open_positions(db)
    entries: list[str] = []
    skipped: list[dict] = []

    for rec in signals:
        # Portfolio full guard
        if open_count >= MAX_SLOTS:
            log.info("  Portfolio full (%d/%d slots) — stopping", open_count, MAX_SLOTS)
            skipped.append({"rec_id": str(rec.id), "reason": "portfolio_full"})
            break

        # Already held guard
        if already_has_position(db, rec.stock_id):
            log.info("  %s — already OPEN position, skip", rec.stock_id)
            skipped.append({"rec_id": str(rec.id), "reason": "already_held"})
            continue

        # Idempotency guard
        if trade_already_executed(db, rec.id):
            log.info("  rec %s — trade already executed today, skip", rec.id)
            skipped.append({"rec_id": str(rec.id), "reason": "already_traded"})
            continue

        log.info(
            "  Rank %s | rec=%s | lifecycle=%s",
            rec.rank, rec.id, rec.lifecycle_state,
        )

        if dry_run:
            log.info("  [dry-run] would execute BUY paper trade for rec %s", rec.id)
            entries.append(f"dry:{rec.id}")
            open_count += 1
            continue

        try:
            trade = paper_svc.execute_entry(
                recommendation_result_id=rec.id,
                as_of_date=entry_date,
                idempotency_key=f"pilot-entry:{rec.id}",
            )
            db.commit()
            entries.append(str(trade.id))
            open_count += 1
            log.info(
                "  ✅ BUY executed | trade=%s | fill=%.2f | qty=%s",
                trade.id, float(trade.fill_price or 0), trade.quantity,
            )
        except Exception as exc:
            db.rollback()
            log.error("  ❌ Failed to execute entry for rec %s: %s", rec.id, exc)
            skipped.append({"rec_id": str(rec.id), "reason": str(exc)})

    return {
        "entries": entries,
        "skipped": skipped,
        "entries_count": len(entries),
        "skipped_count": len(skipped),
        "open_positions_after": open_count,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Batch 3 — Paper Trade Entry")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--date", type=date.fromisoformat, default=None,
                   help="Override entry date (default: today)")
    args = p.parse_args()
    entry_date = args.date or date.today()

    log.info("=" * 60)
    log.info("BATCH 3 — Paper Trade Entry | entry_date=%s | dry_run=%s", entry_date, args.dry_run)
    log.info("=" * 60)

    db = get_db()
    try:
        # Find last trading day's signals (N-1)
        signal_date = last_trading_day(db)
        if signal_date is None:
            log.warning("No completed recommendation runs found — nothing to trade")
            return 0

        if signal_date >= entry_date:
            log.warning(
                "Signal date %s is not before entry date %s — check batch ordering",
                signal_date, entry_date,
            )

        log.info("Signal date (N-1): %s | Entry date (N): %s", signal_date, entry_date)
        log.info("Strategy: %s", PRIMARY_STRATEGY)

        # Load BUY signals
        signals = get_buy_signals(db, signal_date)
        if not signals:
            log.info("No eligible BUY signals for %s — nothing to trade", signal_date)
            return 0

        log.info("Eligible BUY signals: %d", len(signals))
        for s in signals:
            log.info("  Rank %s | rec=%s | lifecycle=%s", s.rank, s.id, s.lifecycle_state)

        # Current portfolio state
        open_before = count_open_positions(db)
        slots_free = MAX_SLOTS - open_before
        log.info("Portfolio: %d/%d slots used | %d free", open_before, MAX_SLOTS, slots_free)

        if slots_free == 0:
            log.info("Portfolio full — no entries possible today")
            return 0

        # Execute entries
        result = execute_entries(db, signals, entry_date, args.dry_run)

        log.info("=" * 60)
        log.info("BATCH 3 COMPLETE")
        log.info("  Entries executed : %d", result["entries_count"])
        log.info("  Skipped          : %d", result["skipped_count"])
        log.info("  Open positions   : %d / %d", result["open_positions_after"], MAX_SLOTS)
        if result["skipped"]:
            for s in result["skipped"]:
                log.info("  Skip: rec=%s reason=%s", s["rec_id"], s["reason"])
        log.info("=" * 60)

    except Exception as exc:
        log.error("BATCH 3 ERROR: %s", exc, exc_info=True)
        db.rollback()
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
