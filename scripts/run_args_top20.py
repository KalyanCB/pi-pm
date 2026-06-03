#!/usr/bin/env python3
"""Run ARGS (top-N) for latest or specified NIFTY_500 ranking runs."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from uuid import UUID

from app.args.llm.registry import CommitteeLlmRegistry
from app.core.config import get_settings
from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_MOMENTUM_V1,
    UNIVERSE_NIFTY_500,
)
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
from app.ranking.loader import MarketDataLoader
from app.services.args_research_run_service import ArgsResearchRunService
from app.services.stock_setup_research_service import StockSetupResearchService


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


def _latest_run_id(db, *, strategy_name: str, as_of_date: date | None) -> UUID:
    repo = RankingRunRepository(db)
    if as_of_date is not None:
        runs = repo.list_completed_in_range(
            as_of_date,
            as_of_date,
            universe_code=UNIVERSE_NIFTY_500,
            strategy_name=strategy_name,
        )
        if not runs:
            raise SystemExit(f"No completed run for {strategy_name} on {as_of_date}")
        return runs[-1].id
    run = repo.get_latest(
        universe_code=UNIVERSE_NIFTY_500,
        strategy_name=strategy_name,
    )
    if run is None:
        raise SystemExit(f"No completed ranking run for {strategy_name}")
    return run.id


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ARGS for top-N on ranking run(s)")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=None)
    parser.add_argument(
        "--strategy",
        choices=("breakout", "momentum", "both"),
        default="both",
    )
    parser.add_argument(
        "--require-completed-validation",
        action="store_true",
        help="Fail if validation status is not 'completed'",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    strategies: list[tuple[str, str]] = []
    if args.strategy in ("breakout", "both"):
        strategies.append((RANKING_STRATEGY_BREAKOUT_V1, "breakout_v1"))
    if args.strategy in ("momentum", "both"):
        strategies.append((RANKING_STRATEGY_MOMENTUM_V1, "momentum_v1"))

    Session = get_session_factory()
    results: list[dict] = []
    with Session() as db:
        service = _build_args_service(db)
        for _const, name in strategies:
            run_id = _latest_run_id(db, strategy_name=name, as_of_date=args.as_of_date)
            run = RankingRunRepository(db).get_by_id(run_id)
            print(f"Running ARGS top_{args.top_n} for {name} as_of={run.as_of_date} run_id={run_id}")
            out = service.run(
                ranking_run_id=run_id,
                top_n=args.top_n,
                require_completed_validation=args.require_completed_validation,
                dry_run=args.dry_run,
            )
            results.append(out)
            print(
                f"  -> research_run_id={out['run_id']} status={out['status']} "
                f"candidates={out['candidates_reviewed']} reports={out.get('governance_reports_issued', 0)}"
            )

    print("\nDone. Export with:")
    for r in results:
        print(f"  .venv/bin/python scripts/export_args_research_run.py {r['run_id']} -o docs/args-{r['run_id']}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
