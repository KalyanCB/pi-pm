from __future__ import annotations

from datetime import date
from uuid import uuid4

from app.outcome_attribution.models import RunBenchmark
from app.ranking_research.models import EnrichedStockObservation
from app.ranking_research.score_compression import (
    _score_bucket_label,
    build_score_compression_segment,
    compare_score_buckets,
)


def _obs(run_id, score: float, ret20: float) -> EnrichedStockObservation:
    return EnrichedStockObservation(
        run_id=run_id,
        as_of_date=date(2024, 6, 3),
        strategy_name="breakout_v1",
        regime_label="BULL_LOW_VOL",
        stock_id=uuid4(),
        rank=1,
        score=score,
        score_components=None,
        returns={20: ret20, 5: ret20 / 2, 10: ret20, 60: ret20},
    )


def test_score_bucket_label():
    assert _score_bucket_label(0.98) == "score_ge_0.97"
    assert _score_bucket_label(0.93) == "score_0.92_0.94"
    assert _score_bucket_label(0.85) == "score_lt_0.90"


def test_compare_score_buckets_high_wins():
    run_id = uuid4()
    observations = [
        _obs(run_id, 0.98, 0.05),
        _obs(run_id, 0.98, 0.04),
        _obs(run_id, 0.93, 0.01),
        _obs(run_id, 0.93, 0.00),
    ]
    bench = RunBenchmark(
        run_id=run_id,
        as_of_date=date(2024, 6, 3),
        benchmark_symbol="^NSEI",
        returns={20: 0.0},
    )
    seg = build_score_compression_segment(
        strategy_name="breakout_v1",
        regime_label="ALL_REGIMES",
        observations=observations,
        benchmark_by_run={run_id: bench},
    )
    assert seg is not None
    cmp = compare_score_buckets(seg, 20, "score_ge_0.97", "score_0.92_0.94")
    assert cmp is not None
    assert cmp.high_outperforms is True
