from datetime import date
from unittest.mock import MagicMock

from app.backtest.ranking_replayer import RankingReplayer
from app.models.ranking_run import RankingRun
from app.schemas.backtest import GenerateRankingsRequest
from app.services.ranking_service import RankingRunOutcome


def test_ranking_replayer_tracks_created_and_reused():
    run = MagicMock(spec=RankingRun)
    ranking_service = MagicMock()
    ranking_service.run_ranking_with_outcome.side_effect = [
        RankingRunOutcome(run, False),
        RankingRunOutcome(run, True),
    ]

    replayer = RankingReplayer(ranking_service)
    request = GenerateRankingsRequest(
        universe_code="PI_PM_CORE",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 2),
    )
    result = replayer.generate(
        request,
        [date(2025, 1, 2), date(2025, 1, 3)],
        universe_code="PI_PM_CORE",
        strategy_name="momentum_v1",
        strategy_version="1.0.0",
        benchmark_symbol="^NSEI",
    )

    assert result.trading_days_total == 2
    assert result.runs_created == 1
    assert result.runs_reused == 1
    assert result.runs_failed == 0
    assert ranking_service.run_ranking_with_outcome.call_count == 2
