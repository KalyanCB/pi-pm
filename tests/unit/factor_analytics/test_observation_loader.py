from decimal import Decimal
from uuid import uuid4

from app.factor_analytics.observation_loader import compute_factor_percentile_ranks


def test_factor_percentile_ranks_spread():
    ids = [uuid4() for _ in range(5)]
    values = [(ids[i], Decimal(str(i))) for i in range(5)]
    ranks = compute_factor_percentile_ranks(values)
    assert ranks[ids[0]] == 0.0
    assert ranks[ids[4]] == 100.0
    assert ranks[ids[2]] == 50.0


def test_factor_percentile_single_stock():
    stock_id = uuid4()
    ranks = compute_factor_percentile_ranks([(stock_id, Decimal("1.0"))])
    assert ranks[stock_id] == 100.0


def test_factor_percentile_empty():
    assert compute_factor_percentile_ranks([]) == {}
