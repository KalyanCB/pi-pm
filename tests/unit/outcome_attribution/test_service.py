from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from app.outcome_attribution.models import (
    OutcomeAttributionConfig,
    RunBenchmark,
    StockObservation,
)
from app.outcome_attribution.service import OutcomeAttributionService


def _obs(
    *,
    run_id: UUID,
    as_of: date,
    strategy: str,
    rank: int,
    ret20: float,
    regime: str = "BULL_LOW_VOL",
) -> StockObservation:
    return StockObservation(
        run_id=run_id,
        as_of_date=as_of,
        strategy_name=strategy,
        regime_label=regime,
        rank=rank,
        returns={5: ret20 / 2, 10: ret20 * 0.75, 20: ret20, 60: ret20 * 1.5},
    )


def test_service_rank_gradient_breakout():
    run_a = uuid4()
    run_b = uuid4()
    observations = [
        _obs(run_id=run_a, as_of=date(2024, 6, 3), strategy="breakout_v1", rank=1, ret20=0.08),
        _obs(run_id=run_a, as_of=date(2024, 6, 3), strategy="breakout_v1", rank=6, ret20=0.04),
        _obs(run_id=run_a, as_of=date(2024, 6, 3), strategy="breakout_v1", rank=15, ret20=0.01),
        _obs(run_id=run_b, as_of=date(2024, 6, 4), strategy="breakout_v1", rank=2, ret20=0.06),
        _obs(run_id=run_b, as_of=date(2024, 6, 4), strategy="breakout_v1", rank=8, ret20=0.03),
        _obs(run_id=run_b, as_of=date(2024, 6, 4), strategy="breakout_v1", rank=18, ret20=-0.01),
    ]
    benchmarks = [
        RunBenchmark(
            run_id=run_a, as_of_date=date(2024, 6, 3), benchmark_symbol="^NSEI", returns={20: 0.01}
        ),
        RunBenchmark(
            run_id=run_b, as_of_date=date(2024, 6, 4), benchmark_symbol="^NSEI", returns={20: 0.01}
        ),
    ]
    config = OutcomeAttributionConfig(
        universe_code="NIFTY_500",
        start_date=date(2024, 6, 1),
        end_date=date(2024, 12, 31),
        strategy_names=("breakout_v1",),
    )
    report = OutcomeAttributionService().compute(config, observations, benchmarks)
    all_segment = next(s for s in report.segments if s.regime_label == "ALL_REGIMES")
    top5 = all_segment.horizons[20]["top_5"]
    top10 = all_segment.horizons[20]["top_10"]
    top20 = all_segment.horizons[20]["top_20"]

    assert top5.alpha is not None and top5.alpha > 0
    assert top10.alpha is not None and top10.alpha > 0
    assert top5.alpha >= top10.alpha >= top20.alpha
    assert report.verdict in {"yes_with_caveats", "partial"}


def test_service_rank_bands_monotonic():
    run_id = uuid4()
    observations = [
        _obs(run_id=run_id, as_of=date(2024, 7, 1), strategy="momentum_v1", rank=r, ret20=ret)
        for r, ret in [(1, 0.10), (3, 0.08), (7, 0.04), (9, 0.03), (12, 0.01), (19, -0.02)]
    ]
    benchmarks = [
        RunBenchmark(
            run_id=run_id,
            as_of_date=date(2024, 7, 1),
            benchmark_symbol="^NSEI",
            returns={20: 0.005},
        )
    ]
    config = OutcomeAttributionConfig(
        universe_code="NIFTY_500",
        start_date=date(2024, 6, 1),
        end_date=date(2024, 12, 31),
        strategy_names=("momentum_v1",),
    )
    report = OutcomeAttributionService().compute(config, observations, benchmarks)
    segment = report.segments[0]
    band_1_5 = segment.rank_bands[20]["rank_1_5"]
    band_6_10 = segment.rank_bands[20]["rank_6_10"]
    band_11_20 = segment.rank_bands[20]["rank_11_20"]

    assert band_1_5.average_return > band_6_10.average_return > band_11_20.average_return
