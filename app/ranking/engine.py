from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.core.constants import (
    EXCLUSION_FACTOR_COMPUTATION_FAILED,
    EXCLUSION_INSUFFICIENT_STRATEGY_HISTORY,
    NORMALIZATION_METHOD_PERCENTILE,
)
from app.ranking.hashing import build_inputs_hash, serialize_bars
from app.ranking.loader import MarketDataLoader
from app.ranking.models import RankedStock, RankingOutput, quantize_score
from app.ranking.normalizer import percentile_normalize, redistribute_weights
from app.ranking.strategy import RankingStrategy
from app.universe.models import FilterDecision, TradableUniverse

RELATIVE_STRENGTH_FACTOR = "relative_strength"


class RankingEngine:
    def __init__(self, loader: MarketDataLoader) -> None:
        self.loader = loader

    def run(
        self,
        tradable_universe: TradableUniverse,
        strategy: RankingStrategy,
        benchmark_symbol: str,
        benchmark_stock_id: UUID | None,
        as_of_date: date,
    ) -> RankingOutput:
        requirements = strategy.requirements()
        source = tradable_universe.filter_config.market_data_source

        benchmark_series = []
        if benchmark_stock_id is not None:
            benchmark_series = self.loader.load_series(
                benchmark_stock_id, as_of_date, source=source
            )

        benchmark_available = len(benchmark_series) >= requirements.required_history_days
        base_weights = strategy.base_weights()
        excluded_factors: set[str] = set()
        if not benchmark_available:
            excluded_factors.add(RELATIVE_STRENGTH_FACTOR)

        effective_weights = redistribute_weights(base_weights, excluded_factors)

        stock_series: dict[str, list] = {}
        raw_by_stock: dict[str, dict[str, Decimal | None]] = {}
        ranking_exclusions: list[FilterDecision] = []

        for stock in tradable_universe.included:
            series = self.loader.load_series(stock.stock_id, as_of_date, source=source)
            stock_series[stock.symbol] = series

            if len(series) < requirements.required_history_days:
                ranking_exclusions.append(
                    FilterDecision(
                        stock_id=stock.stock_id,
                        symbol=stock.symbol,
                        included=False,
                        reason_code=EXCLUSION_INSUFFICIENT_STRATEGY_HISTORY,
                        reason_detail=(
                            f"Requires {requirements.required_history_days} bars, "
                            f"found {len(series)}"
                        ),
                        metrics={"history_days": len(series)},
                    )
                )
                continue

            bench = benchmark_series if benchmark_available else None
            raw_factors = strategy.compute_raw_factors(stock, series, bench, as_of_date)
            active_factors = {
                name: value
                for name, value in raw_factors.items()
                if name in effective_weights and value is not None
            }
            if len(active_factors) != len(effective_weights):
                ranking_exclusions.append(
                    FilterDecision(
                        stock_id=stock.stock_id,
                        symbol=stock.symbol,
                        included=False,
                        reason_code=EXCLUSION_FACTOR_COMPUTATION_FAILED,
                        reason_detail="One or more required factors could not be computed",
                        metrics={k: str(v) for k, v in raw_factors.items()},
                    )
                )
                continue

            raw_by_stock[stock.symbol] = raw_factors

        normalized_by_factor: dict[str, dict[str, Decimal | None]] = defaultdict(dict)
        for symbol, raw_factors in raw_by_stock.items():
            for factor_name, value in raw_factors.items():
                if factor_name in effective_weights:
                    normalized_by_factor[factor_name][symbol] = value

        normalized_by_stock: dict[str, dict[str, Decimal]] = {}
        for factor_name, values in normalized_by_factor.items():
            normalized = percentile_normalize(values)
            for symbol, norm in normalized.items():
                normalized_by_stock.setdefault(symbol, {})[factor_name] = norm

        ranked: list[RankedStock] = []
        for stock in tradable_universe.included:
            if stock.symbol not in raw_by_stock:
                continue
            factor_scores = strategy.build_factor_scores(
                raw_by_stock[stock.symbol],
                normalized_by_stock[stock.symbol],
                effective_weights,
            )
            composite = strategy.composite_score(factor_scores)
            ranked.append(
                RankedStock(
                    stock_id=stock.stock_id,
                    symbol=stock.symbol,
                    rank=0,
                    composite_score=composite,
                    factor_scores=tuple(factor_scores),
                )
            )

        ranked.sort(key=lambda item: (-item.composite_score, item.symbol))
        ranked_with_rank = tuple(
            RankedStock(
                stock_id=item.stock_id,
                symbol=item.symbol,
                rank=index,
                composite_score=quantize_score(item.composite_score),
                factor_scores=item.factor_scores,
            )
            for index, item in enumerate(ranked, start=1)
        )

        serialized_market_data = {
            symbol: serialize_bars(stock_series[symbol]) for symbol in sorted(stock_series)
        }
        benchmark_payload = serialize_bars(benchmark_series) if benchmark_available else None

        inputs_hash = build_inputs_hash(
            as_of_date=as_of_date,
            universe_code=tradable_universe.universe_code,
            filter_config_hash=tradable_universe.filter_config_hash,
            strategy_name=strategy.name,
            strategy_version=strategy.version,
            benchmark_symbol=benchmark_symbol,
            normalization_method=NORMALIZATION_METHOD_PERCENTILE,
            effective_weights=effective_weights,
            included_symbols=[s.symbol for s in tradable_universe.included],
            market_data=serialized_market_data,
            benchmark_data=benchmark_payload,
        )

        ranking_exclusion_summary: dict[str, int] = {}
        for decision in ranking_exclusions:
            ranking_exclusion_summary[decision.reason_code] = (
                ranking_exclusion_summary.get(decision.reason_code, 0) + 1
            )

        metadata = {
            "filter_config": tradable_universe.filter_config.to_canonical_dict(),
            "universe_stock_count": tradable_universe.stock_count,
            "ranked_stock_count": len(ranked_with_rank),
            "universe_exclusion_summary": tradable_universe.exclusion_summary,
            "ranking_exclusion_summary": ranking_exclusion_summary,
            "benchmark_available": benchmark_available,
            "effective_weights": {k: str(v) for k, v in effective_weights.items()},
            "base_weights": {k: str(v) for k, v in base_weights.items()},
        }
        if not benchmark_available:
            metadata["weight_adjustment_reason"] = "benchmark_data_unavailable"

        return RankingOutput(
            strategy_name=strategy.name,
            strategy_version=strategy.version,
            as_of_date=as_of_date,
            universe_code=tradable_universe.universe_code,
            benchmark_symbol=benchmark_symbol,
            normalization_method=NORMALIZATION_METHOD_PERCENTILE,
            inputs_hash=inputs_hash,
            filter_config_hash=tradable_universe.filter_config_hash,
            ranked_stocks=ranked_with_rank,
            ranking_exclusions=tuple(ranking_exclusions),
            exclusion_summary={
                **tradable_universe.exclusion_summary,
                **ranking_exclusion_summary,
            },
            metadata=metadata,
        )
