from __future__ import annotations

from datetime import date
from uuid import uuid4

from app.outcome_attribution.models import BucketMetrics, RunBenchmark
from app.ranking_research.models import (
    EnrichedStockObservation,
    FactorReliabilityRow,
    FactorReliabilitySegment,
    RankingResearchConfig,
    RankReliabilityReport,
    ScoreCompressionReport,
)
from app.ranking_research.root_cause import build_root_cause_headlines
from app.ranking_research.score_compression import build_score_compression_segment


def _metrics(alpha: float) -> BucketMetrics:
    return BucketMetrics(
        bucket="x",
        horizon=20,
        hit_rate=0.5,
        average_return=alpha,
        alpha=alpha,
        sharpe=0.1,
        max_drawdown=0.05,
        run_count=10,
        observation_count=10,
        status="ok",
    )


def test_build_root_cause_headlines_has_sections():
    per_rank = {r: {20: _metrics(0.01 if r > 5 else -0.01)} for r in range(1, 21)}
    from app.ranking_research.models import (
        DecileMonotonicitySummary,
        MonotonicitySummary,
        StrategyRankReliability,
    )

    seg = StrategyRankReliability(
        strategy_name="breakout_v1",
        regime_label="ALL_REGIMES",
        per_rank=per_rank,
        monotonicity={
            20: MonotonicitySummary(
                horizon=20,
                spearman_correlation=0.5,
                inversion_count=10,
                monotonic=False,
                top5_overconfident=True,
                notes="",
            )
        },
        decile_monotonicity={20: DecileMonotonicitySummary(20, {}, None, 0, False)},
        score_quintiles={20: ()},
        cliffs=(),
        noisy_ranks=(),
    )
    report = RankReliabilityReport(
        config=RankingResearchConfig("NIFTY_500", date(2024, 6, 1), date(2024, 12, 1)),
        ranked_run_count=10,
        runs_with_forward_data=10,
        strategies=(seg,),
        regime_segments=(),
        factor_segments=(
            FactorReliabilitySegment(
                "breakout_v1",
                "ALL_REGIMES",
                20,
                (
                    FactorReliabilityRow("trend_quality", 20, 0.9, 0.95, -0.05, 5, 5, -0.05),
                    FactorReliabilityRow("volume_surge", 20, 0.8, 0.85, -0.05, 5, 5, -0.05),
                ),
            ),
        ),
    )
    run_id = uuid4()
    obs = [
        EnrichedStockObservation(
            run_id=run_id,
            as_of_date=date(2024, 6, 3),
            strategy_name="breakout_v1",
            regime_label="BULL_LOW_VOL",
            stock_id=uuid4(),
            rank=1,
            score=0.98,
            score_components=None,
            returns={20: 0.02, 5: 0.01, 10: 0.01, 60: 0.02},
        )
    ]
    bench = RunBenchmark(run_id, date(2024, 6, 3), "^NSEI", {20: 0.0})
    comp_seg = build_score_compression_segment(
        strategy_name="breakout_v1",
        regime_label="ALL_REGIMES",
        observations=obs,
        benchmark_by_run={run_id: bench},
    )
    compression = ScoreCompressionReport(segments=(comp_seg,) if comp_seg else ())

    h = build_root_cause_headlines(report, compression)
    assert h.why_top20_works
    assert h.why_rank_fails
    assert h.root_causes
    assert h.simplest_fix
