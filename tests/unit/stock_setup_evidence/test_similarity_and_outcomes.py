from datetime import date, timedelta
from decimal import Decimal

from app.ranking.math_utils import PriceBar
from app.stock_setup_evidence.constants import SEE_FACTOR_NAMES_BREAKOUT
from app.stock_setup_evidence.outcomes import aggregate_outcomes, build_setup_outcomes
from app.stock_setup_evidence.scoring import compute_setup_evidence_score
from app.stock_setup_evidence.similarity import select_qualifying_setups, similarity_score


def test_similarity_score_high_for_close_vectors():
    reference = {"volume_surge": 0.9, "trend_quality": 0.8, "relative_strength": 0.7}
    candidate = {"volume_surge": 0.91, "trend_quality": 0.79, "relative_strength": 0.69}
    score = similarity_score(reference, candidate, factor_names=SEE_FACTOR_NAMES_BREAKOUT)
    assert score > 0.99


def test_select_qualifying_setups_no_fixed_cap():
    base = date(2026, 1, 1)
    historical = {
        base + timedelta(days=i): {
            "volume_surge": 0.9 - i * 0.01,
            "trend_quality": 0.8,
            "relative_strength": 0.7,
        }
        for i in range(30)
    }
    reference = {"volume_surge": 0.9, "trend_quality": 0.8, "relative_strength": 0.7}
    qualifying, total = select_qualifying_setups(
        reference,
        historical,
        factor_names=SEE_FACTOR_NAMES_BREAKOUT,
        min_similarity=0.55,
    )
    assert total == 30
    assert len(qualifying) > 25


def test_build_setup_outcomes_and_aggregate_with_ci():
    bars = [
        PriceBar(date=date(2026, 1, d), close=Decimal(100 + d), volume=100)
        for d in range(1, 26)
    ]
    matches = [
        (date(2026, 1, 1), 0.92, {}),
        (date(2026, 1, 2), 0.88, {}),
    ]
    regimes = {
        date(2026, 1, 1): "BEAR_LOW_VOL",
        date(2026, 1, 2): "BEAR_LOW_VOL",
    }
    outcomes = build_setup_outcomes(bars, matches, regimes)
    assert len(outcomes) == 2
    agg = aggregate_outcomes(outcomes, "ALL_REGIMES")
    assert agg.sample_size == 2
    assert agg.win_rate_20d is not None
    assert agg.average_return_20d is not None
    assert agg.standard_deviation_20d is not None
    assert agg.confidence_interval_95_lower_20d is not None
    assert agg.confidence_interval_95_upper_20d is not None


def test_setup_evidence_score_differentiates_quality():
    from app.stock_setup_evidence.outcomes import SetupOutcome

    def _outcomes(ret_20d: float) -> list[SetupOutcome]:
        return [
            SetupOutcome(
                setup_date=date(2026, 1, 1),
                similarity_score=0.9,
                regime_label="BEAR_LOW_VOL",
                return_5d=ret_20d / 4,
                return_20d=ret_20d,
                max_drawdown_20d=0.05,
                max_runup_20d=0.25,
            )
            for _ in range(20)
        ]

    strong = aggregate_outcomes(_outcomes(0.20), "ALL_REGIMES")
    weak = aggregate_outcomes(_outcomes(-0.10), "ALL_REGIMES")
    strong_score = compute_setup_evidence_score({"ALL_REGIMES": strong}, qualifying_matches=20)
    weak_score = compute_setup_evidence_score({"ALL_REGIMES": weak}, qualifying_matches=20)
    assert strong_score > weak_score
