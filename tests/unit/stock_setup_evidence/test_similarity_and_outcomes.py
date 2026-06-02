from datetime import date
from decimal import Decimal

from app.ranking.math_utils import PriceBar
from app.stock_setup_evidence.outcomes import aggregate_outcomes, build_setup_outcomes
from app.stock_setup_evidence.similarity import similarity_score


def test_similarity_score_high_for_close_vectors():
    reference = {"volume_surge": 0.9, "trend_quality": 0.8, "relative_strength": 0.7}
    candidate = {"volume_surge": 0.91, "trend_quality": 0.79, "relative_strength": 0.69}
    score = similarity_score(reference, candidate)
    assert score > 0.99


def test_build_setup_outcomes_and_aggregate():
    bars = [
        PriceBar(date=date(2026, 1, 1), close=Decimal("100"), volume=100),
        PriceBar(date=date(2026, 1, 2), close=Decimal("101"), volume=100),
        PriceBar(date=date(2026, 1, 3), close=Decimal("102"), volume=100),
        PriceBar(date=date(2026, 1, 4), close=Decimal("103"), volume=100),
        PriceBar(date=date(2026, 1, 5), close=Decimal("104"), volume=100),
        PriceBar(date=date(2026, 1, 6), close=Decimal("106"), volume=100),
        PriceBar(date=date(2026, 1, 7), close=Decimal("108"), volume=100),
        PriceBar(date=date(2026, 1, 8), close=Decimal("110"), volume=100),
        PriceBar(date=date(2026, 1, 9), close=Decimal("112"), volume=100),
        PriceBar(date=date(2026, 1, 10), close=Decimal("114"), volume=100),
        PriceBar(date=date(2026, 1, 11), close=Decimal("116"), volume=100),
        PriceBar(date=date(2026, 1, 12), close=Decimal("118"), volume=100),
        PriceBar(date=date(2026, 1, 13), close=Decimal("120"), volume=100),
        PriceBar(date=date(2026, 1, 14), close=Decimal("122"), volume=100),
        PriceBar(date=date(2026, 1, 15), close=Decimal("124"), volume=100),
        PriceBar(date=date(2026, 1, 16), close=Decimal("126"), volume=100),
        PriceBar(date=date(2026, 1, 17), close=Decimal("128"), volume=100),
        PriceBar(date=date(2026, 1, 18), close=Decimal("130"), volume=100),
        PriceBar(date=date(2026, 1, 19), close=Decimal("132"), volume=100),
        PriceBar(date=date(2026, 1, 20), close=Decimal("134"), volume=100),
        PriceBar(date=date(2026, 1, 21), close=Decimal("136"), volume=100),
        PriceBar(date=date(2026, 1, 22), close=Decimal("138"), volume=100),
        PriceBar(date=date(2026, 1, 23), close=Decimal("140"), volume=100),
        PriceBar(date=date(2026, 1, 24), close=Decimal("142"), volume=100),
        PriceBar(date=date(2026, 1, 25), close=Decimal("144"), volume=100),
    ]
    matches = [
        (date(2026, 1, 1), 0.92, {"a": 0.1}),
        (date(2026, 1, 2), 0.88, {"a": 0.1}),
    ]
    regimes = {
        date(2026, 1, 1): "BEAR_LOW_VOL",
        date(2026, 1, 2): "BEAR_LOW_VOL",
    }
    outcomes = build_setup_outcomes(bars, matches, regimes)
    assert len(outcomes) == 2
    agg = aggregate_outcomes(outcomes, "ALL_REGIMES")
    assert agg.occurrence_count == 2
    assert agg.win_rate_20d is not None
    assert agg.avg_return_20d is not None
    assert agg.avg_similarity_score is not None
