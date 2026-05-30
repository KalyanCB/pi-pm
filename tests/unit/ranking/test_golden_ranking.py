from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from app.ranking.engine import RankingEngine
from app.ranking.math_utils import PriceBar
from app.ranking.strategies.momentum_v1 import MomentumV1Strategy
from app.universe.models import StockSnapshot, TradableUniverse, UniverseFilterConfig

STOCK_A = UUID("11111111-1111-1111-1111-111111111111")
STOCK_B = UUID("22222222-2222-2222-2222-222222222222")
STOCK_C = UUID("33333333-3333-3333-3333-333333333333")
BENCH = UUID("44444444-4444-4444-4444-444444444444")
GOLDEN_AS_OF = date(2024, 8, 7)
GOLDEN_INPUTS_HASH = "97a8b26da6fc7a8ee03b67234ea85fb5e54af4b21f46d0d1a49a3b3b25ff91ec"


def _bars(base: int, step: int, vol_base: int = 1_000_000) -> list[PriceBar]:
    start = date(2024, 1, 1)
    return [
        PriceBar(
            date=start + timedelta(days=i),
            close=Decimal(str(base + i * step)),
            volume=vol_base + i * 500,
        )
        for i in range(220)
    ]


class _GoldenLoader:
    def __init__(self) -> None:
        self._data = {
            STOCK_A: _bars(100, 2, 1_000_000),
            STOCK_B: _bars(120, 1, 900_000),
            STOCK_C: _bars(80, 3, 1_100_000),
            BENCH: _bars(90, 1, 500_000),
        }

    def load_series(self, stock_id, as_of_date, source="yahoo"):
        return [bar for bar in self._data[stock_id] if bar.date <= as_of_date]


def _golden_universe() -> TradableUniverse:
    config = UniverseFilterConfig(universe_code="PI_PM_CORE")
    included = (
        StockSnapshot(STOCK_A, "AAA.NS", "A", "NSE", None, "ACTIVE", True),
        StockSnapshot(STOCK_B, "BBB.NS", "B", "NSE", None, "ACTIVE", True),
        StockSnapshot(STOCK_C, "CCC.NS", "C", "NSE", None, "ACTIVE", True),
    )
    return TradableUniverse(
        universe_code="PI_PM_CORE",
        as_of_date=GOLDEN_AS_OF,
        filter_config=config,
        filter_config_hash=config.config_hash(),
        included=included,
        excluded=(),
        exclusion_summary={},
    )


def test_golden_ranking_output():
    engine = RankingEngine(_GoldenLoader())
    strategy = MomentumV1Strategy()
    output = engine.run(_golden_universe(), strategy, "^NSEI", BENCH, GOLDEN_AS_OF)

    assert output.inputs_hash == GOLDEN_INPUTS_HASH
    assert [(s.symbol, s.rank, s.composite_score) for s in output.ranked_stocks] == [
        ("BBB.NS", 1, Decimal("0.65000000")),
        ("AAA.NS", 2, Decimal("0.50000000")),
        ("CCC.NS", 3, Decimal("0.35000000")),
    ]
