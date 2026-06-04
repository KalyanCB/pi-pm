from __future__ import annotations

from datetime import date
from uuid import uuid4

from app.outcome_attribution.models import RunBenchmark
from app.ranking_research.backtest import run_calibrated_backtest
from app.ranking_research.calibration import build_calibration_tables
from app.ranking_research.models import EnrichedStockObservation, RankingResearchConfig


def _obs(run_id, rank: int, ret20: float, score: float) -> EnrichedStockObservation:
    return EnrichedStockObservation(
        run_id=run_id,
        as_of_date=date(2024, 6, 3),
        strategy_name="breakout_v1",
        regime_label="BULL_LOW_VOL",
        stock_id=uuid4(),
        rank=rank,
        score=score,
        score_components={"trend_quality": {"normalized": "0.5"}},
        returns={5: ret20 / 2, 10: ret20, 20: ret20, 60: ret20},
    )


def test_backtest_produces_metrics():
    run_id = uuid4()
    observations = [
        _obs(run_id, rank=r, ret20=0.10 - r * 0.01, score=1.0 - r * 0.04)
        for r in range(1, 26)
    ]
    benchmarks = [
        RunBenchmark(
            run_id=run_id,
            as_of_date=date(2024, 6, 3),
            benchmark_symbol="^NSEI",
            returns={5: 0.0, 10: 0.0, 20: 0.01, 60: 0.0},
        )
    ]
    config = RankingResearchConfig(
        universe_code="NIFTY_500",
        start_date=date(2024, 6, 1),
        end_date=date(2024, 12, 31),
        strategy_names=("breakout_v1",),
    )
    tables = build_calibration_tables(observations, benchmarks)
    report = run_calibrated_backtest(config, observations, benchmarks, tables=tables)

    assert len(report.production) == 4
    assert len(report.calibrated) == 4
    prod_20 = next(m for m in report.production if m.horizon == 20)
    assert prod_20.run_count >= 1
    assert prod_20.alpha is not None
    assert report.verdict in {"promising", "mixed", "insufficient"}
