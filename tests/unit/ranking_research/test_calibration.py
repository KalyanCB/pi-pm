from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from app.outcome_attribution.models import RunBenchmark
from app.ranking_research.calibration import (
    CalibrationWeights,
    build_calibration_tables,
    compute_calibrated_score,
)
from app.ranking_research.models import EnrichedStockObservation


def _obs(
    *,
    run_id,
    rank: int,
    ret20: float,
    score: float = 0.5,
    regime: str = "BULL_LOW_VOL",
    strategy: str = "momentum_v1",
    components: dict | None = None,
) -> EnrichedStockObservation:
    return EnrichedStockObservation(
        run_id=run_id,
        as_of_date=date(2024, 6, 3),
        strategy_name=strategy,
        regime_label=regime,
        stock_id=uuid4(),
        rank=rank,
        score=score,
        score_components=components
        or {
            "volume_expansion": {"normalized": "0.8"},
            "trend_quality": {"normalized": "0.7"},
        },
        returns={5: ret20 / 2, 10: ret20 * 0.75, 20: ret20, 60: ret20},
    )


def test_build_calibration_tables_and_score():
    run_a = uuid4()
    observations = [
        _obs(run_id=run_a, rank=1, ret20=0.10, score=0.9),
        _obs(run_id=run_a, rank=5, ret20=0.02, score=0.5),
        _obs(run_id=run_a, rank=15, ret20=-0.01, score=0.2),
    ]
    benchmarks = [
        RunBenchmark(
            run_id=run_a,
            as_of_date=date(2024, 6, 3),
            benchmark_symbol="^NSEI",
            returns={20: 0.01},
        )
    ]
    tables = build_calibration_tables(observations, benchmarks)
    assert "momentum_v1" in tables.historical_rank_alpha
    assert tables.historical_rank_alpha["momentum_v1"][1] > tables.historical_rank_alpha["momentum_v1"][15]

    score = compute_calibrated_score(
        raw_score=0.5,
        rank=5,
        strategy_name="momentum_v1",
        regime_label="BULL_LOW_VOL",
        score_components=observations[1].score_components,
        tables=tables,
    )
    assert isinstance(score, float)


def test_calibration_weights_defaults():
    w = CalibrationWeights()
    assert w.raw_score == pytest.approx(1.0)
    assert w.regime_reliability == pytest.approx(0.15)
