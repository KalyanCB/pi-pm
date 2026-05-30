from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal

from app.ranking.math_utils import PriceBar


def build_inputs_hash(
    as_of_date: date,
    universe_code: str,
    filter_config_hash: str,
    strategy_name: str,
    strategy_version: str,
    benchmark_symbol: str,
    normalization_method: str,
    effective_weights: dict[str, Decimal],
    included_symbols: list[str],
    market_data: dict[str, list[tuple[str, str, str | None]]],
    benchmark_data: list[tuple[str, str]] | None,
) -> str:
    payload = {
        "as_of_date": as_of_date.isoformat(),
        "universe_code": universe_code,
        "filter_config_hash": filter_config_hash,
        "strategy_name": strategy_name,
        "strategy_version": strategy_version,
        "benchmark_symbol": benchmark_symbol,
        "normalization_method": normalization_method,
        "effective_weights": {k: str(v) for k, v in sorted(effective_weights.items())},
        "included_symbols": sorted(included_symbols),
        "market_data": {k: market_data[k] for k in sorted(market_data)},
        "benchmark_data": benchmark_data,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def serialize_bars(bars: list[PriceBar]) -> list[tuple[str, str, str | None]]:
    return [
        (b.date.isoformat(), str(b.close), str(b.volume) if b.volume is not None else None)
        for b in bars
    ]
