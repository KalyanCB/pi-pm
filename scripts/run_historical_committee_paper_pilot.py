#!/usr/bin/env python3
"""Replay committee → HITL auto-approve → paper trading day-by-day from a start date.

Usage:
  python scripts/run_historical_committee_paper_pilot.py --clean-only
  python scripts/run_historical_committee_paper_pilot.py --from-date 2025-06-01
  python scripts/run_historical_committee_paper_pilot.py --from-date 2025-06-01 --to-date 2025-06-30
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date
from uuid import UUID

from sqlalchemy import text

from app.args.llm.registry import CommitteeLlmRegistry
from app.core.config import get_settings
from app.db.repositories.args_prompt_version_repository import ArgsPromptVersionRepository
from app.db.repositories.committee_review_repository import CommitteeReviewRepository
from app.db.repositories.cro_review_repository import CroReviewRepository
from app.db.repositories.governance_research_report_repository import (
    GovernanceResearchReportRepository,
)
from app.db.repositories.investment_review_packet_repository import (
    InvestmentReviewPacketRepository,
)
from app.db.repositories.llm_execution_record_repository import LlmExecutionRecordRepository
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_result_repository import RankingResultRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.research_run_repository import ResearchRunRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.stock_setup_research_repository import StockSetupResearchRepository
from app.db.session import get_session_factory
from app.market_data.cache import MarketDataCache
from app.ops.daily_batch.paper_pilot_ops import DEFAULT_PORTFOLIO_ID, PaperPilotOps
from app.ops.hitl.gate import HITLGate
from app.ranking.loader import MarketDataLoader
from app.services.args_research_run_service import ArgsResearchRunService
from app.services.portfolio_service import PortfolioService
from app.services.stock_setup_research_service import StockSetupResearchService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_EQUITY = 9_000_000.0
UNLIMITED_SLOTS = {"max_positions": 9999, "max_buy_per_day": 9999}


def _build_args_service(db) -> ArgsResearchRunService:
    settings = get_settings()
    lineage_repo = RunLineageRepository(db)
    market_data_repo = MarketDataRepository(db)
    cache = MarketDataCache(market_data_repo)
    stock_setup = StockSetupResearchService(
        db,
        research_repo=StockSetupResearchRepository(db),
        stock_repo=StockRepository(db),
        lineage_repo=lineage_repo,
        market_data_loader=MarketDataLoader(cache),
    )
    return ArgsResearchRunService(
        db,
        research_run_repo=ResearchRunRepository(db),
        packet_repo=InvestmentReviewPacketRepository(db),
        committee_review_repo=CommitteeReviewRepository(db),
        cro_review_repo=CroReviewRepository(db),
        governance_report_repo=GovernanceResearchReportRepository(db),
        lineage_repo=lineage_repo,
        prompt_repo=ArgsPromptVersionRepository(db),
        llm_record_repo=LlmExecutionRecordRepository(db),
        ranking_run_repo=RankingRunRepository(db),
        ranking_result_repo=RankingResultRepository(db),
        validation_repo=RankingValidationRepository(db),
        stock_repo=StockRepository(db),
        stock_setup_service=stock_setup,
        llm_registry=CommitteeLlmRegistry.from_settings(settings),
    )


def clean_portfolio_and_trades(db, *, from_date: date) -> None:
    """Remove portfolio/trade/approval state from from_date onward (full ledger reset)."""
    logger.info("Cleaning portfolio & trade data from %s", from_date)

    # Execution chain
    db.execute(text("DELETE FROM execution_audit"))
    db.execute(text("DELETE FROM execution_events"))
    db.execute(text("DELETE FROM execution_orders"))

    db.execute(text("DELETE FROM paper_trades"))
    db.execute(text("DELETE FROM portfolio_exit_recommendations"))
    db.execute(text("DELETE FROM recommendation_outcomes"))
    db.execute(text("DELETE FROM recommendation_approvals"))

    db.execute(text("DELETE FROM portfolio_cash_ledger"))
    db.execute(text("DELETE FROM portfolio_nav_history"))
    db.execute(text("DELETE FROM portfolio_positions"))

    # Reset recommendation lifecycle for replay window
    db.execute(
        text("""
            UPDATE recommendation_results res
            SET lifecycle_state = 'CANDIDATE',
                portfolio_position_id = NULL
            FROM recommendation_runs rr
            WHERE res.recommendation_run_id = rr.id
              AND rr.as_of_date >= :from_date
        """),
        {"from_date": from_date},
    )

    # Committee / ARGS (re-run fresh)
    db.execute(text("DELETE FROM governance_research_report_evidence"))
    db.execute(text("DELETE FROM governance_research_reports"))
    db.execute(text("DELETE FROM committee_reviews"))
    db.execute(text("DELETE FROM cro_reviews"))
    db.execute(text("DELETE FROM investment_review_packets"))
    db.execute(text("DELETE FROM research_runs"))
    db.execute(text("DELETE FROM llm_execution_records"))

    db.commit()
    logger.info("Clean complete")


def configure_portfolio(db, *, equity: float) -> None:
    ps = PortfolioService(db, portfolio_id=DEFAULT_PORTFOLIO_ID)
    slots = {
        posture: dict(UNLIMITED_SLOTS)
        for posture in ("risk_on", "neutral", "defensive", "crisis")
    }
    ps.upsert_config(
        equity,
        deploy_pct=0.85,
        cash_floor_pct=0.15,
        reserve_pct=0.02,
        regime_slots=slots,
        notes=f"Historical replay — equity ₹{equity:,.0f}, unlimited position slots",
    )
    db.commit()
    logger.info("Portfolio config: equity=%.0f, unlimited slots", equity)


def _trading_days(db, *, from_date: date, to_date: date) -> list[date]:
    rows = db.execute(
        text("""
            SELECT DISTINCT as_of_date
            FROM recommendation_runs
            WHERE status = 'completed'
              AND as_of_date >= :from_date
              AND as_of_date <= :to_date
            ORDER BY as_of_date
        """),
        {"from_date": from_date, "to_date": to_date},
    ).fetchall()
    return [r[0] for r in rows]


def _rec_runs_with_buys(db, trading_day: date) -> list[tuple[UUID, UUID, str, int]]:
    """Return (rec_run_id, ranking_run_id, strategy_name, buy_count) for runs with BUYs."""
    rows = db.execute(
        text("""
            SELECT rr.id, rr.ranking_run_id, rr.strategy_name,
                   COUNT(*) FILTER (WHERE res.action = 'BUY') AS buy_count
            FROM recommendation_runs rr
            JOIN recommendation_results res ON res.recommendation_run_id = rr.id
            WHERE rr.as_of_date = :d AND rr.status = 'completed'
            GROUP BY rr.id, rr.ranking_run_id, rr.strategy_name
            HAVING COUNT(*) FILTER (WHERE res.action = 'BUY') > 0
            ORDER BY rr.strategy_name
        """),
        {"d": trading_day},
    ).fetchall()
    return [(r[0], r[1], r[2], int(r[3])) for r in rows]


def run_day(
    db,
    *,
    trading_day: date,
    args_service: ArgsResearchRunService,
    pilot: PaperPilotOps,
    gate: HITLGate,
    top_n: int,
    skip_committee: bool,
    committee_delay: float,
) -> dict:
    stats: dict = {
        "date": trading_day.isoformat(),
        "committee_runs": 0,
        "committee_errors": 0,
        "approvals": 0,
        "entries": 0,
        "exits": 0,
        "skipped": 0,
    }

    if not skip_committee:
        for _rec_id, ranking_run_id, strategy, buy_count in _rec_runs_with_buys(db, trading_day):
            try:
                out = args_service.run(
                    ranking_run_id=ranking_run_id,
                    top_n=top_n,
                    require_completed_validation=False,
                    dry_run=False,
                )
                stats["committee_runs"] += 1
                logger.info(
                    "  committee %s %s: run_id=%s candidates=%s",
                    trading_day,
                    strategy,
                    out.get("run_id"),
                    out.get("candidates_reviewed"),
                )
            except Exception as exc:
                stats["committee_errors"] += 1
                logger.warning("  committee %s %s failed: %s", trading_day, strategy, exc)
            if committee_delay > 0:
                time.sleep(committee_delay)
        db.commit()

    hitl = gate.auto_approve_buys(db, trading_day, max_slots=9999)
    stats["approvals"] = hitl.get("approved_count", 0)
    db.commit()

    result = pilot.run(
        trading_day,
        recompute=True,
        exit_monitor=True,
        paper_trading=True,
        nav_snapshot=True,
        reconcile=True,
        pilot_auto_approve=True,
        pilot_auto_execute=True,
    )
    db.commit()

    pt = result.get("paper_trading", {})
    stats["entries"] = pt.get("entries_count", 0)
    stats["exits"] = pt.get("exits_count", 0)
    stats["skipped"] = len(pt.get("skipped", []))
    return stats


def _ensure_dev_user(db) -> None:
    uid = "00000000-0000-4000-8000-000000000001"
    pid = str(DEFAULT_PORTFOLIO_ID)
    if db.execute(text("SELECT COUNT(*) FROM users")).scalar():
        return
    import uuid

    db.execute(
        text("""
            INSERT INTO users (id, email, password_hash, display_name, is_active, is_superuser, created_at, updated_at)
            VALUES (:id, 'dev@pipm.local', 'dev-bypass', 'Dev Owner', true, true, now(), now())
        """),
        {"id": uid},
    )
    db.execute(
        text("""
            INSERT INTO user_portfolio_memberships (id, user_id, portfolio_id, role, created_at, updated_at)
            VALUES (:mid, :uid, :pid, 'owner', now(), now())
        """),
        {"mid": str(uuid.uuid4()), "uid": uid, "pid": pid},
    )
    db.commit()
    logger.info("Seeded dev user for execution FK")


def main() -> int:
    parser = argparse.ArgumentParser(description="Historical committee + paper pilot replay")
    parser.add_argument("--from-date", type=date.fromisoformat, default=date(2025, 6, 1))
    parser.add_argument("--to-date", type=date.fromisoformat, default=None)
    parser.add_argument("--equity", type=float, default=DEFAULT_EQUITY)
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Committee reviews top-N ranked stocks (5 = BUY pool size)",
    )
    parser.add_argument(
        "--committee-delay",
        type=float,
        default=3.0,
        help="Seconds to pause between committee runs (rate-limit safety)",
    )
    parser.add_argument("--clean-only", action="store_true")
    parser.add_argument("--skip-clean", action="store_true")
    parser.add_argument("--skip-committee", action="store_true")
    args = parser.parse_args()

    gate = HITLGate.from_settings()
    if gate.hitl_enabled:
        logger.error("HITL_ENABLED must be false for auto-replay")
        return 1
    if not gate.paper_trading_enabled:
        logger.error("PAPER_TRADING_ENABLED must be true")
        return 1

    Session = get_session_factory()
    with Session() as db:
        if not args.skip_clean:
            clean_portfolio_and_trades(db, from_date=args.from_date)
        _ensure_dev_user(db)
        configure_portfolio(db, equity=args.equity)

        if args.clean_only:
            print("Clean + portfolio config done.")
            return 0

        to_date = args.to_date
        if to_date is None:
            row = db.execute(
                text("SELECT MAX(as_of_date) FROM recommendation_runs WHERE status='completed'")
            ).fetchone()
            to_date = row[0]

        days = _trading_days(db, from_date=args.from_date, to_date=to_date)
        logger.info("Replay %d trading days: %s → %s", len(days), days[0], days[-1])

        args_service = _build_args_service(db)
        pilot = PaperPilotOps(db)

        totals = {"committee": 0, "entries": 0, "exits": 0, "errors": 0}
        started = time.perf_counter()

        for i, d in enumerate(days, 1):
            logger.info("Day %d/%d: %s", i, len(days), d)
            try:
                stats = run_day(
                    db,
                    trading_day=d,
                    args_service=args_service,
                    pilot=pilot,
                    gate=gate,
                    top_n=args.top_n,
                    skip_committee=args.skip_committee,
                    committee_delay=args.committee_delay,
                )
                totals["committee"] += stats["committee_runs"]
                totals["entries"] += stats["entries"]
                totals["exits"] += stats["exits"]
                totals["errors"] += stats["committee_errors"]
                logger.info(
                    "  -> committee=%d approvals=%d entries=%d exits=%d skipped=%d",
                    stats["committee_runs"],
                    stats["approvals"],
                    stats["entries"],
                    stats["exits"],
                    stats["skipped"],
                )
            except Exception as exc:
                db.rollback()
                logger.exception("Day %s failed: %s", d, exc)
                totals["errors"] += 1

        elapsed = time.perf_counter() - started
        pos = db.execute(
            text(
                "SELECT COUNT(*) FROM portfolio_positions WHERE is_current=true AND position_status='OPEN'"
            )
        ).scalar()
        trades = db.execute(text("SELECT COUNT(*) FROM paper_trades")).scalar()
        sells = db.execute(
            text("SELECT COUNT(*) FROM paper_trades WHERE side = 'SELL'")
        ).scalar()
        committee = db.execute(text("SELECT COUNT(*) FROM committee_reviews")).scalar()

        print("\n=== REPLAY COMPLETE ===")
        print(f"Days processed: {len(days)}")
        print(f"Committee runs: {totals['committee']} (reviews in DB: {committee})")
        print(f"Paper entries: {totals['entries']} | exits: {totals['exits']}")
        print(f"Trades in DB: {trades} (SELL: {sells})")
        print(f"Open positions: {pos}")
        print(f"Errors: {totals['errors']}")
        print(f"Elapsed: {elapsed / 60:.1f} min")

    return 0


if __name__ == "__main__":
    sys.exit(main())
