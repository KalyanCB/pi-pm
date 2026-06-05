from __future__ import annotations

from datetime import date
from uuid import uuid4

from app.outcome_attribution.models import RunBenchmark
from app.ranking_research.models import EnrichedStockObservation
from app.ranking_research.rank_reliability import (
    _count_alpha_inversions,
    _spearman_correlation,
    build_rank_decile_monotonicity,
    build_strategy_rank_reliability,
)


def _obs(run_id, rank: int, ret20: float) -> EnrichedStockObservation:
    return EnrichedStockObservation(
        run_id=run_id,
        as_of_date=date(2024, 6, 3),
        strategy_name="momentum_v1",
        regime_label="BULL_LOW_VOL",
        stock_id=uuid4(),
        rank=rank,
        score=0.5,
        score_components=None,
        returns={20: ret20, 5: ret20 / 2, 10: ret20, 60: ret20},
    )


def test_spearman_negative_correlation():
    ranks = list(range(1, 11))
    # Higher rank number = lower return → negative correlation with rank
    values = [0.10 - r * 0.01 for r in ranks]
    rho = _spearman_correlation(ranks, values)
    assert rho is not None
    assert rho < 0


def test_alpha_inversions():
    alphas = {1: 0.005, 2: 0.003, 3: 0.008, 4: 0.002}
    assert _count_alpha_inversions(alphas) == 2


def test_build_strategy_rank_reliability_non_monotonic_top5():
    run_id = uuid4()
    observations = [
        _obs(run_id, rank=1, ret20=0.005),
        _obs(run_id, rank=2, ret20=0.004),
        _obs(run_id, rank=7, ret20=0.03),
        _obs(run_id, rank=8, ret20=0.025),
    ]
    benchmarks = [
        RunBenchmark(
            run_id=run_id,
            as_of_date=date(2024, 6, 3),
            benchmark_symbol="^NSEI",
            returns={20: 0.0},
        )
    ]
    seg = build_strategy_rank_reliability(
        strategy_name="momentum_v1",
        regime_label="ALL_REGIMES",
        observations=observations,
        benchmark_by_run={run_id: benchmarks[0]},
    )
    assert seg is not None
    mono = seg.monotonicity[20]
    assert mono.top5_overconfident is True or mono.inversion_count > 0
    dec = build_rank_decile_monotonicity(seg.per_rank, 20)
    assert dec.decile_alphas


def test_build_rank_decile_monotonicity_inverted():
    per_rank = {
        1: {20: type("M", (), {"alpha": 0.01, "status": "ok"})()},
        2: {20: type("M", (), {"alpha": 0.02, "status": "ok"})()},
        3: {20: type("M", (), {"alpha": 0.05, "status": "ok"})()},
        4: {20: type("M", (), {"alpha": 0.06, "status": "ok"})()},
    }
    dec = build_rank_decile_monotonicity(per_rank, 20)
    assert dec.decile_alphas[2] > dec.decile_alphas[1]
