from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.core.constants import (
    EXCLUSION_DATA_STATUS_NOT_ACTIVE,
    EXCLUSION_INSUFFICIENT_HISTORY,
    EXCLUSION_INSUFFICIENT_TRADED_VALUE,
    EXCLUSION_MIN_PRICE_FAILED,
    EXCLUSION_NO_PRICE_DATA,
    EXCLUSION_NOT_IN_UNIVERSE,
    EXCLUSION_STOCK_INACTIVE,
    DataStatus,
)
from app.db.repositories.universe_repository import UniverseRepository
from app.market_data.cache import MarketDataCache
from app.ranking.math_utils import PriceBar, bars_on_or_before, latest_bar
from app.universe.models import (
    FilterDecision,
    StockSnapshot,
    TradableUniverse,
    UniverseFilterConfig,
)


class UniverseFilterEngine:
    def __init__(
        self,
        universe_repo: UniverseRepository,
        market_data_cache: MarketDataCache,
    ) -> None:
        self.universe_repo = universe_repo
        self.market_data_cache = market_data_cache

    def build_tradable_universe(
        self,
        as_of_date: date,
        config: UniverseFilterConfig,
    ) -> TradableUniverse:
        membership_stocks = self.universe_repo.list_stocks_in_universe(config.universe_code)
        membership_ids = {stock.id for stock in membership_stocks}

        candidate_stocks = self.universe_repo.list_candidate_stocks(config.universe_code)
        included: list[StockSnapshot] = []
        excluded: list[FilterDecision] = []

        for stock in candidate_stocks:
            snapshot = StockSnapshot(
                stock_id=stock.id,
                symbol=stock.symbol,
                name=stock.name,
                exchange=stock.exchange,
                sector=stock.sector,
                data_status=stock.data_status,
                is_active=stock.is_active,
            )

            if stock.id not in membership_ids:
                excluded.append(
                    self._decision(
                        snapshot,
                        EXCLUSION_NOT_IN_UNIVERSE,
                        "Stock is not an active member of the configured universe",
                    )
                )
                continue

            if config.require_stock_active and not stock.is_active:
                excluded.append(
                    self._decision(snapshot, EXCLUSION_STOCK_INACTIVE, "Stock is marked inactive")
                )
                continue

            if config.require_data_status_active and stock.data_status != DataStatus.ACTIVE.value:
                excluded.append(
                    self._decision(
                        snapshot,
                        EXCLUSION_DATA_STATUS_NOT_ACTIVE,
                        f"Stock data_status is {stock.data_status}",
                    )
                )
                continue

            bars = self._load_bars(stock.id, as_of_date, config.market_data_source)
            eligible = bars_on_or_before(bars, as_of_date)

            if len(eligible) < config.min_history_days:
                excluded.append(
                    self._decision(
                        snapshot,
                        EXCLUSION_INSUFFICIENT_HISTORY,
                        f"Requires {config.min_history_days} trading days, found {len(eligible)}",
                        {"history_days": len(eligible)},
                    )
                )
                continue

            latest = latest_bar(bars, as_of_date)
            if latest is None:
                excluded.append(
                    self._decision(
                        snapshot,
                        EXCLUSION_NO_PRICE_DATA,
                        "No price data available on or before as_of_date",
                    )
                )
                continue

            if latest.close < config.min_stock_price:
                excluded.append(
                    self._decision(
                        snapshot,
                        EXCLUSION_MIN_PRICE_FAILED,
                        f"Latest close {latest.close} below minimum {config.min_stock_price}",
                        {"latest_close": str(latest.close)},
                    )
                )
                continue

            avg_volume = self._average_volume(eligible, window=20)
            avg_close = self._average_close(eligible, window=20)
            if avg_volume is None or avg_close is None:
                excluded.append(
                    self._decision(
                        snapshot,
                        EXCLUSION_NO_PRICE_DATA,
                        "Insufficient volume/price data to compute traded value",
                    )
                )
                continue

            avg_traded_value = avg_volume * avg_close
            if avg_traded_value < config.min_avg_daily_traded_value:
                excluded.append(
                    self._decision(
                        snapshot,
                        EXCLUSION_INSUFFICIENT_TRADED_VALUE,
                        (
                            f"Average daily traded value {avg_traded_value} "
                            f"below minimum {config.min_avg_daily_traded_value}"
                        ),
                        {
                            "avg_daily_traded_value": str(avg_traded_value),
                            "avg_volume_20d": str(avg_volume),
                            "avg_close_20d": str(avg_close),
                        },
                    )
                )
                continue

            included.append(snapshot)

        included.sort(key=lambda s: s.symbol)
        exclusion_summary = self._summarize_exclusions(excluded)

        return TradableUniverse(
            universe_code=config.universe_code,
            as_of_date=as_of_date,
            filter_config=config,
            filter_config_hash=config.config_hash(),
            included=tuple(included),
            excluded=tuple(excluded),
            exclusion_summary=exclusion_summary,
        )

    def _load_bars(self, stock_id: UUID, as_of_date: date, source: str) -> list[PriceBar]:
        return self.market_data_cache.load_series(stock_id, as_of_date, source=source)

    def _average_volume(self, bars: list[PriceBar], window: int) -> Decimal | None:
        if len(bars) < window:
            return None
        volumes = [b.volume for b in bars[-window:] if b.volume is not None]
        if not volumes:
            return None
        return Decimal(str(sum(volumes) / len(volumes)))

    def _average_close(self, bars: list[PriceBar], window: int) -> Decimal | None:
        if len(bars) < window:
            return None
        closes = [b.close for b in bars[-window:]]
        return Decimal(str(sum(closes) / len(closes)))

    def _decision(
        self,
        stock: StockSnapshot,
        reason_code: str,
        reason_detail: str,
        metrics: dict[str, str | int | None] | None = None,
    ) -> FilterDecision:
        return FilterDecision(
            stock_id=stock.stock_id,
            symbol=stock.symbol,
            included=False,
            reason_code=reason_code,
            reason_detail=reason_detail,
            metrics=metrics or {},
        )

    def _summarize_exclusions(self, excluded: list[FilterDecision]) -> dict[str, int]:
        summary: dict[str, int] = {}
        for decision in excluded:
            summary[decision.reason_code] = summary.get(decision.reason_code, 0) + 1
        return summary
