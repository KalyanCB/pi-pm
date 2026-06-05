from __future__ import annotations

from app.outcome_attribution.constants import REGIME_LABEL_ALL
from app.outcome_attribution.models import RunBenchmark
from app.ranking_research.constants import REGIME_LABELS, RESEARCH_HORIZONS
from app.ranking_research.factor_reliability import build_factor_reliability_segment
from app.ranking_research.models import (
    EnrichedStockObservation,
    RankingResearchConfig,
    RankReliabilityReport,
)
from app.ranking_research.rank_reliability import build_strategy_rank_reliability


class RankReliabilityService:
    def compute(
        self,
        config: RankingResearchConfig,
        observations: list[EnrichedStockObservation],
        benchmarks: list[RunBenchmark],
    ) -> RankReliabilityReport:
        benchmark_by_run = {b.run_id: b for b in benchmarks}
        strategies: list = []
        regime_segments: list = []
        factor_segments: list = []

        for strategy in config.strategy_names:
            seg = build_strategy_rank_reliability(
                strategy_name=strategy,
                regime_label=REGIME_LABEL_ALL,
                observations=observations,
                benchmark_by_run=benchmark_by_run,
            )
            if seg:
                strategies.append(seg)

            for regime in REGIME_LABELS:
                rseg = build_strategy_rank_reliability(
                    strategy_name=strategy,
                    regime_label=regime,
                    observations=observations,
                    benchmark_by_run=benchmark_by_run,
                )
                if rseg:
                    regime_segments.append(rseg)

            for regime in [REGIME_LABEL_ALL, *REGIME_LABELS]:
                for horizon in RESEARCH_HORIZONS:
                    fseg = build_factor_reliability_segment(
                        strategy_name=strategy,
                        regime_label=regime,
                        horizon=horizon,
                        observations=observations,
                    )
                    if fseg and any(r.winner_count > 0 for r in fseg.rows):
                        factor_segments.append(fseg)

        runs_with_20d = len({o.run_id for o in observations if o.returns.get(20) is not None})
        return RankReliabilityReport(
            config=config,
            ranked_run_count=len({o.run_id for o in observations}),
            runs_with_forward_data=runs_with_20d,
            strategies=tuple(strategies),
            regime_segments=tuple(regime_segments),
            factor_segments=tuple(factor_segments),
        )
